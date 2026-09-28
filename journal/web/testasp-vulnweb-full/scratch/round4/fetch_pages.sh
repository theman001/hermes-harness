#!/usr/bin/env bash
# round4 static-collection: fetch pages + headers verbatim
# usage: bash fetch_pages.sh
set -u
BASE="http://testasp.vulnweb.com"
OUT="$(cd "$(dirname "$0")" && pwd)/../pages"
mkdir -p "$OUT"
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

fetch() {
  local slug="$1" path="$2"
  echo "=== $slug  <- $path"
  curl -sS -m 40 -D "$OUT/${slug}.headers.txt" -o "$OUT/${slug}.body" \
       -A "$UA" "$BASE$path"
  echo "   status: $(head -1 "$OUT/${slug}.headers.txt" | tr -d '\r')  bytes: $(wc -c < "$OUT/${slug}.body")"
}

fetch root            /
fetch Default.asp     /Default.asp
fetch login.asp       /login.asp
fetch register.asp    /register.asp
fetch search.asp      /search.asp
fetch db.asp          /db.asp
fetch logInput.asp    /logInput.asp
fetch showthread.asp  /showthread.asp
fetch showforum.asp   /showforum.asp
fetch logout.asp      /logout.asp
fetch Templatize.asp  /Templatize.asp
fetch robots.txt      /robots.txt
