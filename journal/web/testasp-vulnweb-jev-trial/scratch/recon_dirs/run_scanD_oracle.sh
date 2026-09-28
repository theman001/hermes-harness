#!/bin/bash
# Scan D: enumerate FrontPage-tracked filenames via /_vti_cnf/ oracle (bare raft-small words)
cd /home/taeuk/projects/llm-abliteration/hermes-harness/journal/web/testasp-vulnweb-jev-trial/scratch
FFUF=/home/taeuk/go/bin/ffuf
$FFUF -u "http://testasp.vulnweb.com/_vti_cnf/FUZZ" -w raft-small.txt \
  -rate 100 -t 35 -timeout 15 -fc 404 -s \
  -of json -o recon_dirs/vticnf_oracle_raft.json > recon_dirs/scanD.log 2>&1
echo "EXIT_D=$?" >> recon_dirs/scanD.log
# Scan E: image filenames via /Images/_vti_cnf/ oracle
$FFUF -u "http://testasp.vulnweb.com/Images/_vti_cnf/FUZZ" -w common.txt \
  -rate 100 -t 35 -timeout 15 -fc 404 -s \
  -of json -o recon_dirs/images_vticnf_oracle.json >> recon_dirs/scanD.log 2>&1
echo "EXIT_E=$?" >> recon_dirs/scanD.log
# Scan G: cgi-bin contents (scripts/files)
$FFUF -u "http://testasp.vulnweb.com/cgi-bin/FUZZ" -w common.txt \
  -e .txt,.pl,.cgi,.exe,.dll -rate 100 -t 35 -timeout 15 -fc 404 -s \
  -of json -o recon_dirs/cgibin_common.json >> recon_dirs/scanD.log 2>&1
echo "EXIT_G=$?" >> recon_dirs/scanD.log
