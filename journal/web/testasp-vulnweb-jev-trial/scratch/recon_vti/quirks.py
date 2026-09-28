#!/usr/bin/env python3
import subprocess, time
BASE="http://testasp.vulnweb.com"
UA="Mozilla/5.0 recon"
def st(p,tries=2):
    for i in range(tries):
        try:
            r=subprocess.run(["curl","-sS","--path-as-is","-m","20","-A",UA,"-o","/dev/null",
                "-w","%{http_code}\t%{size_download}\t%{content_type}\t%{redirect_url}",BASE+p],
                capture_output=True,text=True,timeout=30)
            o=r.stdout.strip()
            if not o.startswith("000"): return o
        except Exception: pass
        time.sleep(0.7)
    return "000\t0\t-\t-"

quirks=[
 # baselines
 "/Default.asp","/styles.css","/html/about.html","/Templates/MainTemplate.dwt.asp","/DB.asp",
 # trailing dot / space
 "/Default.asp.","/Default.asp ","/styles.css.","/styles.css ",
 # encoded space / dot
 "/Default.asp%20","/Default.asp%20.","/Default.asp%2e","/styles.css%20",
 # NTFS ADS
 "/Default.asp::$DATA","/styles.css::$DATA","/Templates/MainTemplate.dwt.asp::$DATA",
 "/html/about.html::$DATA","/Default.asp::$data","/styles.css:.txt","/styles.css::$index_allocation",
 # trailing slash
 "/Default.asp/","/styles.css/","/Templates/MainTemplate.dwt.asp/","/html/about.html/",
 # null byte
 "/Default.asp%00","/Default.asp%00.txt","/Default.asp%00.jpg","/styles.css%00","/styles.css%00.gif",
 # double encode / dotdot
 "/Default.asp%2520","/%2e%2e/Default.asp","/acuforum/%2e%2e/Default.asp","/html/%2e%2e/Default.asp",
 "/%2e/Default.asp","/Default.asp%2f","/Default.asp%5c",
 # backslash / semicolon
 "/Default.asp\\","/..\\Default.asp","/Default.asp;.txt","/Default.asp;.asp","/Default.asp;",
 # case
 "/DEFAULT.ASP","/SeArCh.AsP","/STYLES.CSS",
 # misc
 "/Default.asp%23","/Default.asp%3f","/Default.asp%3b",
]
print("%-8s %-7s %-44s %s" % ("STATUS","SIZE","PATH","CT/REDIR"))
print("-"*105)
for p in quirks:
    o=st(p); f=o.split("\t")
    extra=(f[2] if len(f)>2 else "")
    if len(f)>3 and f[3]: extra += " -> "+f[3]
    print("%-8s %-7s %-44s %s" % (f[0], f[1] if len(f)>1 else "?", p, extra))

print("\n########## HTTP METHODS ##########")
for target in ["/","/Default.asp","/Templates/","/_vti_cnf/","/html/about.html","/Search.asp"]:
    for m in ["OPTIONS","TRACE","PUT","DELETE","PATCH","PROPFIND","DEBUG","HEAD"]:
        try:
            r=subprocess.run(["curl","-sS","--path-as-is","-m","20","-A",UA,"-X",m,"-o","/dev/null",
                "-D","-",BASE+target],capture_output=True,text=True,timeout=30)
            head=r.stdout.split("\n")
            first=head[0].strip() if head else "?"
            allow=[l.strip() for l in head if l.lower().startswith(("allow:","public:"))]
            print("%-9s %-22s %s   %s" % (m,target,first," | ".join(allow)))
        except Exception as e:
            print("%-9s %-22s ERR %s" % (m,target,e))
    print("-"*90)
