#!/bin/bash
# Scan B: recursive-ish scan inside high-value directories (common.txt + extensions)
cd /home/taeuk/projects/llm-abliteration/hermes-harness/journal/web/testasp-vulnweb-jev-trial/scratch
FFUF=/home/taeuk/go/bin/ffuf
for d in _vti_cnf Templates HTML T; do
  echo "===== DIR $d =====" >> recon_dirs/dirs_A.log
  $FFUF -u "http://testasp.vulnweb.com/$d/FUZZ" -w common.txt \
    -e .asp,.aspx,.txt,.inc,.htm,.html \
    -rate 110 -t 35 -timeout 15 -fc 404 -s \
    -of json -o "recon_dirs/${d}_common.json" >> recon_dirs/dirs_A.log 2>&1
  echo "EXIT_${d}=$?" >> recon_dirs/dirs_A.log
done
