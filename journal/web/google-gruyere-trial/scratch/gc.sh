#!/bin/bash
# proxied curl helper: gc.sh <outfile> <url> [extra curl args...]
OUT="$1"; shift
URL="$1"; shift
exec curl -s -x http://127.0.0.1:8080 --cacert /home/taeuk/.mitmproxy/mitmproxy-ca-cert.pem \
  -c /home/taeuk/projects/llm-abliteration/hermes-harness/journal/web/google-gruyere-trial/scratch/gruyere.cookies \
  -b /home/taeuk/projects/llm-abliteration/hermes-harness/journal/web/google-gruyere-trial/scratch/gruyere.cookies \
  -m 40 "$@" "$URL" -o "$OUT" -w "status=%{http_code} url=%{url_effective} redirect=%{redirect_url}\n"
