#!/bin/bash
# Round 4 - lean oracle suite: per-directory _vti_cnf oracles + root oracle extra extensions
set -u
cd /home/taeuk/projects/llm-abliteration/hermes-harness/journal/web/testasp-vulnweb-full/scratch/round4
BASE=http://testasp.vulnweb.com
cat /tmp/full/wordlists/common.txt /tmp/full/wordlists/quickhits.txt | sed 's/\r$//' | grep -v '^$' | sort -u > small_wl.txt

echo "=== S2 START $(date -u +%H:%M:%SZ)"
ffuf -u "$BASE/images/_vti_cnf/FUZZ" -w small_wl.txt \
     -e ".gif,.jpg,.png,.ico,.swf,.css,.js,.asp" -mc 200 -t 150 -s -o oracle_images.json -of json
echo "=== S2 DONE $(date -u +%H:%M:%SZ) rc=$?"

echo "=== S3 START $(date -u +%H:%M:%SZ)"
ffuf -u "$BASE/jscripts/tiny_mce/_vti_cnf/FUZZ" -w small_wl.txt \
     -e ".js,.css,.htm,.html,.txt,.gif,.jpg,.png" -mc 200 -t 150 -s -o oracle_tinymce.json -of json
echo "=== S3 DONE $(date -u +%H:%M:%SZ) rc=$?"

echo "=== S5 START $(date -u +%H:%M:%SZ)"
ffuf -u "$BASE/_vti_cnf/FUZZ" -w small_wl.txt \
     -e ".zip,.xml,.config,.bak,.old,.log,.asa,.svc,.axd,.aspx,.ini,.mdb,.sql" -mc 200 -t 150 -s -o oracle_root_extra.json -of json
echo "=== S5 DONE $(date -u +%H:%M:%SZ) rc=$?"

echo "=== S6 START $(date -u +%H:%M:%SZ)"
ffuf -u "$BASE/_vti_cnf/FUZZ" -w merged_wl.txt -e ".htm,.ini" -mc 200 -t 150 -s -o oracle_root_htm_ini.json -of json
echo "=== S6 DONE $(date -u +%H:%M:%SZ) rc=$?"

echo "=== LEAN ALL DONE $(date -u +%Y-%m-%dT%H:%M:%SZ)"
