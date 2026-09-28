#!/usr/bin/env bash
# r2_auth step 1: baseline + controls (no SQLi yet)
cd "$(dirname "$0")" || exit 1
U=http://testasp.vulnweb.com
set -x

# B1: baseline GET Login.asp, fresh cookie jar (creates ASPSESSIONID)
curl -sS -i --max-time 20 -c cj_baseline.txt -D hdr_b1_get_login.txt -o body_b1_get_login.html \
  "$U/Login.asp"

# B2: GET Login.asp WITH the baseline cookie jar (session continuity check)
curl -sS -i --max-time 20 -b cj_baseline.txt -c cj_baseline.txt -D hdr_b2_get_login_2nd.txt -o body_b2_get_login_2nd.html \
  "$U/Login.asp"

# C1: control POST valid-format but bogus creds, fresh jar
curl -sS -i --max-time 20 -c cj_c1.txt -D hdr_c1_bogus.txt -o body_c1_bogus.html \
  -X POST --data-urlencode "tfUName=nosuchuser_zzz" --data-urlencode "tfUPass=nosuchpass_zzz" \
  "$U/Login.asp"

# C2: control POST both empty (should NOT reach SQL at all)
curl -sS -i --max-time 20 -c cj_c2.txt -D hdr_c2_empty.txt -o body_c2_empty.html \
  -X POST -d "tfUName=&tfUPass=" \
  "$U/Login.asp"

# C3: control POST only password empty (short-circuit)
curl -sS -i --max-time 20 -c cj_c3.txt -D hdr_c3_passonly.txt -o body_c3_passonly.html \
  -X POST -d "tfUName=admin&tfUPass=" \
  "$U/Login.asp"
