#!/bin/bash
# Scan F1/F5: extension-aware file enumeration (common.txt)
cd /home/taeuk/projects/llm-abliteration/hermes-harness/journal/web/testasp-vulnweb-jev-trial/scratch
FFUF=/home/taeuk/go/bin/ffuf
echo "### F1 /_vti_cnf (metadata oracle, with extensions)" > recon_dirs/scanF1.log
$FFUF -u "http://testasp.vulnweb.com/_vti_cnf/FUZZ" -w common.txt \
  -e .asp,.aspx,.css,.js,.htm,.html,.txt \
  -rate 110 -t 35 -timeout 15 -fc 404 -s \
  -of json -o recon_dirs/vticnf_common_ext.json >> recon_dirs/scanF1.log 2>&1
echo "EXIT_F1=$?" >> recon_dirs/scanF1.log
echo "### F5 /Templates (with extensions)" >> recon_dirs/scanF1.log
$FFUF -u "http://testasp.vulnweb.com/Templates/FUZZ" -w common.txt \
  -e .dwt,.dwt.asp,.tpl,.html,.htm,.txt,.asp \
  -rate 110 -t 35 -timeout 15 -fc 404 -s \
  -of json -o recon_dirs/Templates_common_ext.json >> recon_dirs/scanF1.log 2>&1
echo "EXIT_F5=$?" >> recon_dirs/scanF1.log
echo "DONE_F1F5" >> recon_dirs/scanF1.log
