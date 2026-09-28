#!/bin/bash
# Round 4 (v2): widened-extension root scan with FULL match codes (incl. 500 = existing-but-erroring ASP)
#   + per-directory FrontPage _vti_cnf oracles (/images/, /jscripts/tiny_mce/)
set -u
cd /home/taeuk/projects/llm-abliteration/hermes-harness/journal/web/testasp-vulnweb-full/scratch/round4
BASE=http://testasp.vulnweb.com
MERGED=merged_wl.txt
SMALL=small_wl.txt
MC="200,204,301,302,307,400,401,403,405,500,501,502,503"
cat /tmp/full/wordlists/common.txt /tmp/full/wordlists/quickhits.txt | sed 's/\r$//' | grep -v '^$' | sort -u > $SMALL

echo "=== START $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# ---- S1: root, widened extension set, full match codes -----------------------
EXTS=".asp,.txt,.inc,.bak,.config,.log,.old,.zip,.xml,.asa,.aspx,.ashx,.asmx,.axd,.svc,.dwt,.dwt.asp,.css,.js,.ini"
ffuf -u "$BASE/FUZZ" -w "$MERGED" -e "$EXTS" -mc "$MC" -t 150 -s -o root_widened_full.json -of json
echo "=== S1 root_widened_full done $(date -u +%H:%M:%SZ) rc=$?"

# ---- S2: /images/ file-existence oracle -------------------------------------
ffuf -u "$BASE/images/_vti_cnf/FUZZ" -w "$MERGED" \
     -e ".gif,.jpg,.png,.ico,.swf,.asp,.css,.js,.txt,.html,.inc,.zip" \
     -mc 200 -t 150 -s -o oracle_images.json -of json
echo "=== S2 oracle_images done $(date -u +%H:%M:%SZ) rc=$?"

# ---- S3: /jscripts/tiny_mce/ file-existence oracle --------------------------
ffuf -u "$BASE/jscripts/tiny_mce/_vti_cnf/FUZZ" -w "$MERGED" \
     -e ".js,.css,.htm,.html,.txt,.gif,.jpg,.png,.asp,.inc" \
     -mc 200 -t 150 -s -o oracle_tinymce.json -of json
echo "=== S3 oracle_tinymce done $(date -u +%H:%M:%SZ) rc=$?"

# ---- S5: root oracle, non-web extensions (small high-signal wordlist) -------
ffuf -u "$BASE/_vti_cnf/FUZZ" -w "$SMALL" \
     -e ".zip,.xml,.config,.bak,.old,.log,.asa,.svc,.axd,.aspx,.ini,.db,.mdb,.sql" \
     -mc 200 -t 150 -s -o oracle_root_extra.json -of json
echo "=== S5 oracle_root_extra done $(date -u +%H:%M:%SZ) rc=$?"

echo "=== ALL DONE $(date -u +%Y-%m-%dT%H:%M:%SZ)"
