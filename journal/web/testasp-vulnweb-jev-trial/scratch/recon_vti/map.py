#!/usr/bin/env python3
import os, subprocess, time
BASE="http://testasp.vulnweb.com"
OUT="/home/taeuk/projects/llm-abliteration/hermes-harness/journal/web/testasp-vulnweb-jev-trial/scratch/recon_vti"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) recon"
def st(p,tries=2):
    for i in range(tries):
        try:
            r=subprocess.run(["curl","-sS","--path-as-is","-m","20","-A",UA,"-o","/dev/null",
                "-w","%{http_code}\t%{size_download}\t%{content_type}\t%{redirect_url}",BASE+p],
                capture_output=True,text=True,timeout=30)
            o=r.stdout.strip()
            if not o.startswith("000"): return o
        except Exception: pass
        time.sleep(0.8)
    return "000\t0\t-\t-"

groups = {
 "APP PAGES (root)": ["/Default.asp","/Search.asp","/Login.asp","/login.asp","/Register.asp","/register.asp",
    "/showforum.asp","/showthread.asp","/Templatize.asp","/logout.asp","/DB.asp","/db.asp","/styles.css",
    "/Images/logo.gif","/Images/","/images/","/html/","/html/about.html","/about.html"],
 "DIR/403-vs-404 BASELINE": ["/zzz/","/_vti_cnf/zzz/","/zzz/_vti_cnf/","/nonexist_abc/_vti_cnf/",
    "/images/_vti_cnf/","/Images/_vti_cnf/","/html/_vti_cnf/","/Templates/_vti_cnf/","/t/_vti_cnf/",
    "/scripts/_vti_cnf/","/acuforum/_vti_cnf/","/_vti_cnf/","/_private/","/_derived/","/_overlay/",
    "/_borders/","/_fpclass/","/_vti_bin/_vti_aut/","/_vti_pvt/","/aspnet_client/system_web/2_0_50727/",
    "/aspnet_client/system_web/4_0_30319/","/Templates/","/Templates"],
 "TEMPLATES DIR": ["/Templates/MainTemplate.dwt.asp","/Templates/mainTemplate.dwt.asp","/Templates/Maintemplate.dwt.asp",
    "/Templates/MAINTEMPLATE.DWT.ASP","/Templates/MainTemplate.dwt.asp.bak","/Templates/Default.dwt.asp",
    "/Templates/default.dwt.asp","/Templates/template.dwt.asp","/Templates/acuforum.dwt.asp","/Templates/menu.dwt.asp",
    "/Templates/header.dwt.asp","/Templates/footer.dwt.asp","/Templates/sidebar.dwt.asp","/Templates/index.dwt.asp",
    "/Templates/about.dwt.asp","/Templates/search.dwt.asp","/Templates/login.dwt.asp","/Templates/showforum.dwt.asp",
    "/Templates/showthread.dwt.asp","/Templates/Templatize.dwt.asp","/Templates/Main.dwt.asp",
    "/Templates/main.dwt.asp","/Templates/MainTemplate.dwt.asp ","/Templates/MainTemplate.dwt",
    "/Templates/MainTemplate.asp","/Templates/MainTemplate.dwt.asp/","/Templates/MainTemplate.dwt.asp::$DATA"],
 "MISC LEFTOVERS": ["/iisstart.htm","/iisstart.png","/welcome.png","/trace.axd","/elmah.axd","/glimpse.axd",
    "/_vti_inf.html","/_vti_bin/shtml.exe","/web.config","/global.asa","/global.asax","/favicon.ico",
    "/sitemap.xml","/crossdomain.xml","/clientaccesspolicy.xml","/Default.asp.bak","/Default.asp.old",
    "/Default.asp~","/Default.asp.txt","/Default.asp.orig","/Search.asp.bak","/Templatize.asp.bak",
    "/Templatize.asp.old","/Templatize.asp.txt","/Templatize.asp.orig","/Templatize.asp~","/login.asp.bak",
    "/index.asp","/index.html","/default.html","/readme.txt","/LICENSE.txt","/CHANGELOG.txt"],
}
for g,paths in groups.items():
    print("\n########## %s ##########" % g)
    print("%-8s %-7s %-52s %s" % ("STATUS","SIZE","PATH","CT/REDIR"))
    print("-"*110)
    for p in paths:
        o=st(p); f=o.split("\t")
        extra=f[2] if len(f)>2 else ""
        if len(f)>3 and f[3]: extra += " -> "+f[3]
        print("%-8s %-7s %-52s %s" % (f[0], f[1] if len(f)>1 else "?", p, extra))
