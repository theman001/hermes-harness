#!/bin/bash
# Scan A: root-level, raft-small.txt restricted to .asp/.aspx
cd /home/taeuk/projects/llm-abliteration/hermes-harness/journal/web/testasp-vulnweb-jev-trial/scratch
FFUF=/home/taeuk/go/bin/ffuf
$FFUF -u http://testasp.vulnweb.com/FUZZ -w raft-small.txt -e .asp,.aspx \
  -rate 100 -t 35 -timeout 15 -fc 404 -s \
  -of json -o recon_dirs/root_raft_asp.json > recon_dirs/root_raft_asp.log 2>&1
echo "EXIT_A=$?" >> recon_dirs/root_raft_asp.log
