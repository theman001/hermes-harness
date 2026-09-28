#!/usr/bin/env python3
import subprocess, os, time
BASE="http://testasp.vulnweb.com"
OUT="/home/taeuk/projects/llm-abliteration/hermes-harness/journal/web/testasp-vulnweb-jev-trial/scratch/recon_vti"
B=os.path.join(OUT,"vti_cnf_dump"); os.makedirs(B,exist_ok=True)
UA="Mozilla/5.0 recon"
pages=["Default.asp","Search.asp","Login.asp","Register.asp","showforum.asp","showthread.asp",
       "Templatize.asp","logout.asp","DB.asp","styles.css"]
log=[]
for p in pages:
    url=BASE+"/_vti_cnf/"+p
    f=os.path.join(B,p.replace("/","_")+".txt")
    for i in range(3):
        r=subprocess.run(["curl","-sS","--path-as-is","-m","25","-A",UA,"-D","-","-o",f,url],
                         capture_output=True,text=True,timeout=40)
        if os.path.exists(f) and os.path.getsize(f)>0: break
        time.sleep(1)
    hdr=r.stdout
    body=open(f,encoding="utf-8",errors="replace").read() if os.path.exists(f) else ""
    print("\n"+"="*100)
    print("URL: %s" % url)
    for line in hdr.split("\n"):
        if line.lower().startswith(("http/","content-type","content-length","last-modified","etag","x-aspnet","x-powered")):
            print("  "+line.strip())
    print("-"*100)
    print(body)
    log.append((url,body))
with open(os.path.join(OUT,"ALL_VTI_CNF_DUMP.txt"),"w") as fh:
    for u,b in log:
        fh.write("\n===== %s =====\n%s\n" % (u,b))
print("\n\n########## AGGREGATED LEAK TERMS ##########")
import re
allt="\n".join(b for _,b in log)
for kw in ["vti_author","vti_cachedsvcrellinks","vti_backlinkinfo","vti_cachedlinkinfo",
           "vti_timelastmodified","vti_sourcecontrol","vti_sourcecontrolversion",
           "vti_sourcecontrolcookie","vti_username","vti_syncwith","vti_metatags","vti_title"]:
    hits=[l for l in allt.split("\n") if l.startswith(kw+":")]
    if hits:
        print("\n%s:" % kw)
        for h in hits: print("   "+h)
