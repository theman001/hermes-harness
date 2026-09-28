#!/bin/bash
# Round 4: widened extension scan + /_vti_cnf/ file-existence oracle enumeration
set -u
cd /home/taeuk/projects/llm-abliteration/hermes-harness/journal/web/testasp-vulnweb-full/scratch/round4
WL=/tmp/full/wordlists
MERGED=merged_wl.txt
BASE=http://testasp.vulnweb.com

echo "=== START $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# ---- Scan B1: /_vti_cnf/ oracle (primary path) --------------------------------
# every hit named <name>.<ext> means the ORIGINAL /<name>.<ext> existed at publish time
ffuf -u "$BASE/_vti_cnf/FUZZ" -w "$MERGED" \
     -e ".asp,.txt,.inc,.html,.dwt,.dwt.asp,.css,.js" \
     -mc 200 -t 150 -s -o oracle_core.json -of json
echo "=== B1 oracle_core done $(date -u +%H:%M:%SZ) rc=$?"

# ---- Scan A: root, widened extension set ------------------------------------
EXTS=".asp,.txt,.inc,.bak,.config,.log,.old,.zip,.xml,.asa,.aspx,.ashx,.asmx,.axd,.svc,.dwt,.css,.js,.ini"
ffuf -u "$BASE/FUZZ" -w "$MERGED" -e "$EXTS" \
     -mc 200,204,301,302,307,401,403 -t 150 -s -o root_widened.json -of json
echo "=== A root_widened done $(date -u +%H:%M:%SZ) rc=$?"

# ---- Scan B2: oracle asset extensions (images/static) ------------------------
ffuf -u "$BASE/_vti_cnf/FUZZ" -w "$MERGED" \
     -e ".gif,.jpg,.png,.ico,.zip,.xml,.config,.bak,.old,.log,.asa,.svc,.axd,.aspx" \
     -mc 200 -t 150 -s -o oracle_assets.json -of json
echo "=== B2 oracle_assets done $(date -u +%H:%M:%SZ) rc=$?"

echo "=== ALL DONE $(date -u +%Y-%m-%dT%H:%M:%SZ)"
