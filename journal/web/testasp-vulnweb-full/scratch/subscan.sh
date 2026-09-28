#!/bin/bash
# Sub-directory enumeration for testasp.vulnweb.com (root dirs found by ffuf/gobuster)
cd /tmp/full/sub5
mkdir -p subdirs
WL=/tmp/full/wordlists/quickhits.txt
EXTS=".asp,.txt,.inc,.config,.log,.old,.zip,.xml,.asa"
for d in images templates jscripts html avatars T aspnet_client _vti_cnf cgi-bin; do
  echo "--- $d start $(date -u +%H:%M:%S)"
  ffuf -u "http://testasp.vulnweb.com/${d}/FUZZ" -w "$WL" -e "$EXTS" \
    -mc 200,204,301,302,307,401,403 -t 150 -s \
    -o "/tmp/full/sub5/subdirs/${d}.json" -of json > "/tmp/full/sub5/subdirs/${d}.log" 2>&1
  echo "--- $d done $(date -u +%H:%M:%S) rc=$?"
done
echo "ALL SUBDIR SCANS DONE $(date -u +%H:%M:%S)"
