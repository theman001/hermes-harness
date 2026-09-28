#!/usr/bin/env python3
import os, subprocess, time, re
BASE="http://testasp.vulnweb.com"
OUT="/home/taeuk/projects/llm-abliteration/hermes-harness/journal/web/testasp-vulnweb-jev-trial/scratch/recon_vti"
B=os.path.join(OUT,"bodies"); os.makedirs(B,exist_ok=True)
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) recon"
def get(p,tries=3):
    for i in range(tries):
        cmd=["curl","-sS","--path-as-is","-m","25","-A",UA,"-o","/dev/stdout",
             "-w","\n@@@%{http_code}\t%{size_download}\t%{content_type}\t%{redirect_url}","-D","/dev/stderr",BASE+p]
        try:
            r=subprocess.run(cmd,capture_output=True,text=True,timeout=40)
            out=r.stdout
            if "@@@" in out:
                body,_,metric=out.rpartition("\n@@@")
                return metric.strip(), body, r.stderr
        except Exception: pass
        time.sleep(1)
    return "ERR", "", ""

print("########## CONTENT DUMPS ##########")
for p in ["/robots.txt","/Templates/MainTemplate.dwt.asp","/Templates","/trace.axd","/images/_vti_cnf/","/aspnet_client/","/Default.asp"]:
    m,body,hdr = get(p)
    print("\n===== %s  -> %s =====" % (p,m))
    print("---- headers ----")
    print(hdr.strip()[:600])
    print("---- body (%d bytes shown, first 1600) ----" % len(body))
    print(body[:1600])
