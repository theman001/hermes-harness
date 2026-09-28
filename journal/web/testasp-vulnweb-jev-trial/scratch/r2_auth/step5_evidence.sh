#!/usr/bin/env bash
# r2_auth step 5: consolidated evidence capture (no new state-changing requests)
cd "$(dirname "$0")" || exit 1
OUT=evidence_headers.txt
: > "$OUT"
for f in hdr_s1_admin_comment hdr_s2_tautology hdr_s6_quote_syntaxerr hdr_c1_bogus hdr_c2_empty \
         hdr_r0_returl_bogus hdr_r1_sqli_plus_returl hdr_r5_logout_returl hdr_o1_default_loggedin hdr_o2_default_anon; do
  { echo "===== $f ====="; cat "$f.txt" | tr -d '\r'; echo; } >> "$OUT"
done

echo "### authenticated-form presence (bypass session vs anon) ###"
for pair in "body_o1_default_loggedin.html:body_o2_default_anon.html:Default.asp" \
            "body_o3_showforum_loggedin.html:body_o4_showforum_anon.html:showforum.asp"; do
  L=${pair%%:*}; rest=${pair#*:}; A=${rest%%:*}; P=${rest#*:}
  echo "-- $P"
  printf "   loggedin : logout_menu=%s tfSubject_form=%s textarea=%s bytes=%s\n" \
    "$(grep -c 'logout' $L)" "$(grep -c 'name=\"tfSubject\"' $L)" "$(grep -c -i 'textarea' $L)" "$(stat -c%s $L)"
  printf "   anon     : logout_menu=%s tfSubject_form=%s textarea=%s bytes=%s\n" \
    "$(grep -c 'logout' $A)" "$(grep -c 'name=\"tfSubject\"' $A)" "$(grep -c -i 'textarea' $A)" "$(stat -c%s $A)"
done

echo
echo "### unescaped reflection check (session uname echoed raw) ###"
grep -o "logout admin'-- " body_o1_default_loggedin.html | head -2
grep -o 'logout[^<]*' body_o3_showforum_loggedin.html | head -2
