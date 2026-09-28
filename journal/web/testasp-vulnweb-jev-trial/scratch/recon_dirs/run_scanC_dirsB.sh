#!/bin/bash
# Scan C: scan inside asset/other directories (common.txt + extensions)
cd /home/taeuk/projects/llm-abliteration/hermes-harness/journal/web/testasp-vulnweb-jev-trial/scratch
FFUF=/home/taeuk/go/bin/ffuf
for d in jscripts Images avatars aspnet_client cgi-bin; do
  echo "===== DIR $d =====" >> recon_dirs/dirs_B.log
  $FFUF -u "http://testasp.vulnweb.com/$d/FUZZ" -w common.txt \
    -e .asp,.aspx,.txt,.inc \
    -rate 110 -t 35 -timeout 15 -fc 404 -s \
    -of json -o "recon_dirs/${d}_common.json" >> recon_dirs/dirs_B.log 2>&1
  echo "EXIT_${d}=$?" >> recon_dirs/dirs_B.log
done
