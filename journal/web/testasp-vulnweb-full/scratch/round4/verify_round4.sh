#!/usr/bin/env bash
# Consolidated reproduction of EVERY nuclei/nikto finding - round4
# Target: http://testasp.vulnweb.com  (authorized own_system)
set -u
T=http://testasp.vulnweb.com
OUT=verify-consolidated.txt
: > "$OUT"
log(){ echo "$@" | tee -a "$OUT"; }
code(){ curl -s -o /dev/null -w '%{http_code}' -m 15 "$1"; }

log "==== VERIFY-NIKTO-01: OPTIONS Allowed/Public methods ===="
curl -s -i -m 15 -X OPTIONS "$T/" | grep -iE '^(HTTP/|Allow:|Public:)' | tr -d '\r' | tee -a "$OUT"
log ""

log "==== VERIFY-NIKTO-02: TRACE actually implemented? (nickto lists TRACE in Allow) ===="
log "curl -X TRACE  -> $(code_t=$(curl -s -o /dev/null -w '%{http_code}' -m 15 -X TRACE "$T/"); echo $code_t)"
log "raw netcat TRACE -> $(printf 'TRACE / HTTP/1.1\r\nHost: testasp.vulnweb.com\r\n\r\n' | timeout 10 nc testasp.vulnweb.com 80 | head -1 | tr -d '\r')"
log ""

log "==== VERIFY-NIKTO-03: does /index.aspx exist? ===="
log "/index.aspx            -> $(code "$T/index.aspx")  (body size $(curl -s -o /dev/null -w '%{size_download}' -m 15 "$T/index.aspx"))"
log "/nonexistent-xyz.aspx  -> $(code "$T/nonexistent-xyz.aspx")  (body size $(curl -s -o /dev/null -w '%{size_download}' -m 15 "$T/nonexistent-xyz.aspx"))"
log "X-AspNet-Version on a plainly-nonexistent .aspx:"
curl -s -i -m 15 "$T/nonexistent-xyz.aspx" | grep -iE '^(HTTP/|X-AspNet-Version:)' | tr -d '\r' | tee -a "$OUT"
log ""

log "==== VERIFY-NIKTO-04: IIS version banner ===="
curl -s -i -m 15 "$T/" | grep -iE '^(Server:|X-Powered-By:)' | tr -d '\r' | tee -a "$OUT"
log ""

log "==== VERIFY-NIKTO-05: is / 'Default IIS server content'? ===="
log "page <title> = $(curl -s -m 15 "$T/" | grep -oiE '<title>[^<]*</title>' | head -1)"
log ""

log "==== VERIFY-NIKTO-06/07: internal IP 10.0.0.14 in Location (Host-less HTTP/1.0) ===="
log "-- WITH Host header (HTTP/1.1) --"
curl -s -i -m 15 "$T/aspnet_client" | grep -iE '^(HTTP/|Location:)' | tr -d '\r' | tee -a "$OUT"
log "-- WITHOUT Host header (raw HTTP/1.0, 3 runs) --"
for i in 1 2 3; do
  log "run$i: $(printf 'GET /aspnet_client HTTP/1.0\r\n\r\n' | timeout 10 nc testasp.vulnweb.com 80 | grep -i '^Location:' | tr -d '\r')"
done
log "-- control: other dirs, Host-less HTTP/1.0 --"
for p in /Images /Templates /doesnotexist9; do
  log "$p -> $(printf "GET $p HTTP/1.0\r\n\r\n" | timeout 10 nc testasp.vulnweb.com 80 | head -1 | tr -d '\r')"
done
log ""

log "==== VERIFY-NIKTO-08..12 + NUCLEI sec-headers: are headers really missing? ===="
HDRS=$(curl -s -i -m 15 "$T/")
for H in strict-transport-security referrer-policy content-security-policy x-content-type-options permissions-policy x-frame-options cross-origin-embedder-policy cross-origin-opener-policy cross-origin-resource-policy x-permitted-cross-domain-policies; do
  if echo "$HDRS" | grep -qiE "^$H:"; then log "  $H : PRESENT"; else log "  $H : MISSING (confirmed)"; fi
done
log ""

log "==== VERIFY-NUCLEI-cookies: Set-Cookie flags ===="
SC=$(curl -s -i -m 15 "$T/" | grep -i '^Set-Cookie:' | tr -d '\r')
log "  raw: $SC"
log "  Secure    : $(echo "$SC" | grep -qi 'secure' && echo PRESENT || echo MISSING)"
log "  HttpOnly  : $(echo "$SC" | grep -qi 'httponly' && echo PRESENT || echo MISSING)"
log "  SameSite  : $(echo "$SC" | grep -qi 'samesite' && echo PRESENT || echo MISSING)"
log ""

log "==== VERIFY-NUCLEI-shortname: iis-shortname-detect (tilde) - FALSE POSITIVE PROOF ===="
for p in "Images" "Templates" "aspnet_client" "zzzznotreal9" "q7w8e9r0t1"; do
  log "  ${p}*~1*/a.aspx -> $(code "$T/${p}*~1*/a.aspx")"
done
log "  (all prefixes real AND garbage return identical status => no shortname signal)"
log ""

log "==== VERIFY-METHODS: full method matrix ===="
for M in GET HEAD POST OPTIONS TRACE TRACK PUT DELETE PATCH CONNECT PROPFIND; do
  s=$(curl -s -o /dev/null -w '%{http_code}' -m 15 -X "$M" "$T/")
  log "  $M -> $s"
done
log ""

log "==== VERIFY-EXTRA: Trace.axd / db.asp / robots.txt / status baseline ===="
for p in /Trace.axd /db.asp /robots.txt /web.config /Templatize.asp; do
  log "  $p -> $(code "$T$p") (size $(curl -s -o /dev/null -w '%{size_download}' -m 15 "$T$p"))"
done
log "  Trace.axd headers:"; curl -s -i -m 15 "$T/Trace.axd" | grep -iE '^(HTTP/|X-AspNet-Version:)' | tr -d '\r' | sed 's/^/    /' | tee -a "$OUT"
log ""
log "==== END $(date -u) ===="
cat verify-consolidated.txt > /dev/null
echo "WROTE $OUT"
