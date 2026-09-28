#!/bin/bash
# Red round4: per-directory FrontPage _vti_cnf file-existence oracles
#   /images/_vti_cnf/  and  /jscripts/tiny_mce/_vti_cnf/  (+ root oracle, non-web extensions)
set -u
cd /home/taeuk/projects/llm-abliteration/hermes-harness/journal/web/testasp-vulnweb-full/scratch/round4
BASE=http://testasp.vulnweb.com
SMALL=small_wl.txt          # 7321 high-signal words (common.txt + quickhits.txt)
MERGED=merged_wl.txt        # 42508 words (raft-small-words + above)

echo "=== R4RED START $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# O1: /images/ file-existence oracle (front page metadata folder exists -> 403)
ffuf -u "$BASE/images/_vti_cnf/FUZZ" -w "$SMALL" \
     -e ".gif,.jpg,.png,.ico,.swf,.css,.js,.asp" -mc 200 -t 100 -s \
     -o r4red_oracle_images.json -of json
echo "=== O1 oracle_images done $(date -u +%H:%M:%SZ) rc=$?"

# O2: /jscripts/tiny_mce/ file-existence oracle
ffuf -u "$BASE/jscripts/tiny_mce/_vti_cnf/FUZZ" -w "$SMALL" \
     -e ".js,.css,.htm,.html,.txt,.gif,.jpg" -mc 200 -t 100 -s \
     -o r4red_oracle_tinymce.json -of json
echo "=== O2 oracle_tinymce done $(date -u +%H:%M:%SZ) rc=$?"

# O3: root oracle with non-web extensions (config/backup/archive class)
ffuf -u "$BASE/_vti_cnf/FUZZ" -w "$SMALL" \
     -e ".zip,.xml,.config,.bak,.old,.log,.asa,.svc,.axd,.aspx,.ini,.db,.mdb,.sql,.inc" -mc 200 -t 100 -s \
     -o r4red_oracle_root_extra.json -of json
echo "=== O3 oracle_root_extra done $(date -u +%H:%M:%SZ) rc=$?"

# O4: /images/ oracle with the full raft wordlist, image extensions only (deeper pass)
ffuf -u "$BASE/images/_vti_cnf/FUZZ" -w "$MERGED" \
     -e ".gif,.jpg,.png,.ico" -mc 200 -t 100 -s \
     -o r4red_oracle_images_raft.json -of json
echo "=== O4 oracle_images_raft done $(date -u +%H:%M:%SZ) rc=$?"

echo "=== R4RED ALL DONE $(date -u +%Y-%m-%dT%H:%M:%SZ)"
