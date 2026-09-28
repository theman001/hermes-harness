#!/bin/bash
# Scan F2/F3/F4: cgi-bin, tiny_mce, image-metadata enumeration (common.txt)
cd /home/taeuk/projects/llm-abliteration/hermes-harness/journal/web/testasp-vulnweb-jev-trial/scratch
FFUF=/home/taeuk/go/bin/ffuf
echo "### F2 /cgi-bin" > recon_dirs/scanF2.log
$FFUF -u "http://testasp.vulnweb.com/cgi-bin/FUZZ" -w common.txt \
  -e .txt,.pl,.cgi,.exe,.dll \
  -rate 110 -t 35 -timeout 15 -fc 404 -s \
  -of json -o recon_dirs/cgibin_common_ext.json >> recon_dirs/scanF2.log 2>&1
echo "EXIT_F2=$?" >> recon_dirs/scanF2.log
echo "### F3 /jscripts/tiny_mce" >> recon_dirs/scanF2.log
$FFUF -u "http://testasp.vulnweb.com/jscripts/tiny_mce/FUZZ" -w common.txt \
  -e .js,.htm,.html \
  -rate 110 -t 35 -timeout 15 -fc 404 -s \
  -of json -o recon_dirs/tiny_mce_common.json >> recon_dirs/scanF2.log 2>&1
echo "EXIT_F3=$?" >> recon_dirs/scanF2.log
echo "### F4 /Images/_vti_cnf" >> recon_dirs/scanF2.log
$FFUF -u "http://testasp.vulnweb.com/Images/_vti_cnf/FUZZ" -w common.txt \
  -e .gif,.jpg,.png \
  -rate 110 -t 35 -timeout 15 -fc 404 -s \
  -of json -o recon_dirs/images_vticnf_common_ext.json >> recon_dirs/scanF2.log 2>&1
echo "EXIT_F4=$?" >> recon_dirs/scanF2.log
echo "DONE_F2F4" >> recon_dirs/scanF2.log
