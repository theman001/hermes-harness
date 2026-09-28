#!/bin/bash
# Round 4 - S1: root scan, widened extension set, FULL match codes (incl. 500 = existing-but-erroring ASP)
set -u
cd /home/taeuk/projects/llm-abliteration/hermes-harness/journal/web/testasp-vulnweb-full/scratch/round4
BASE=http://testasp.vulnweb.com
MC="200,204,301,302,307,400,401,403,405,500,501,502,503"
EXTS=".asp,.txt,.inc,.bak,.config,.log,.old,.zip,.xml,.asa,.aspx,.ashx,.asmx,.axd,.svc,.dwt,.dwt.asp,.css,.js,.ini"
echo "=== S1 START $(date -u +%Y-%m-%dT%H:%M:%SZ)"
ffuf -u "$BASE/FUZZ" -w merged_wl.txt -e "$EXTS" -mc "$MC" -t 150 -s -o root_widened_full.json -of json
echo "=== S1 DONE $(date -u +%Y-%m-%dT%H:%M:%SZ) rc=$?"
