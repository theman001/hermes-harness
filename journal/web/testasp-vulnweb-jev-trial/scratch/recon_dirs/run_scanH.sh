#!/bin/bash
# Scan H: /t/ directory contents (common.txt + txt/html/asp)
cd /home/taeuk/projects/llm-abliteration/hermes-harness/journal/web/testasp-vulnweb-jev-trial/scratch
FFUF=/home/taeuk/go/bin/ffuf
echo "### H /t/" > recon_dirs/scanH.log
$FFUF -u "http://testasp.vulnweb.com/t/FUZZ" -w common.txt \
  -e .txt,.html,.htm,.asp \
  -rate 110 -t 35 -timeout 15 -fc 404 -s \
  -of json -o recon_dirs/t_common_ext.json >> recon_dirs/scanH.log 2>&1
echo "EXIT_H=$?" >> recon_dirs/scanH.log
echo "DONE_H" >> recon_dirs/scanH.log
