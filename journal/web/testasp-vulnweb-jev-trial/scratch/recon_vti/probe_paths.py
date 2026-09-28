#!/usr/bin/env python3
import os, subprocess, re, json, sys

BASE = "http://testasp.vulnweb.com"
OUT  = "/home/taeuk/projects/llm-abliteration/hermes-harness/journal/web/testasp-vulnweb-jev-trial/scratch/recon_vti"
BODIES = os.path.join(OUT, "bodies")
os.makedirs(BODIES, exist_ok=True)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) recon"

# known pages (from vti_backlinkinfo + task)
pages = ["Default.asp","default.asp","Search.asp","search.asp","Login.asp","login.asp",
         "Register.asp","register.asp","showforum.asp","showthread.asp",
         "Templatize.asp","templatize.asp","logout.asp","Logout.asp",
         "DB.asp","db.asp","styles.css","Images/logo.gif"]

paths = []
# 1) _vti_cnf for each known page at root
for p in pages:
    paths.append("/_vti_cnf/%s.cnf" % p)
# 1b) same under acuforum (internal root revealed by vti_cachedsvcrellinks)
for p in pages:
    paths.append("/acuforum/_vti_cnf/%s.cnf" % p)
# 1c) alternative casing / dirs
for d in ["Templates","templates","html","images","Images","t","scripts","_private","_vti_txt","_vti_pvt","_vti_bin","_vti_script","_vti_log","_vti_cnf","acuforum","about","inc","includes","forum","asp","data"]:
    paths.append("/%s/_vti_cnf/" % d)
for d in ["Templates","html","images","t","scripts","_private","inc","includes"]:
    paths.append("/acuforum/%s/_vti_cnf/" % d)
    paths.append("/_vti_cnf/%s/" % d)

# 2) DreamWeaver templates
tpl = ["MainTemplate.dwt.asp","template.dwt.asp","Template.dwt.asp","main.dwt.asp",
       "Main.dwt.asp","Default.dwt.asp","default.dwt.asp","MainTemplatize.dwt.asp",
       "acuforum.dwt.asp","MainTemplate.dwt","MainTemplate.dwt.asp.bak",
       "MainTemplate.dwt.asp.old","MainTemplate.dwt.asp~"]
for t in tpl:
    paths.append("/Templates/%s" % t)
    paths.append("/Templates/_vti_cnf/%s.cnf" % t)
    paths.append("/acuforum/Templates/%s" % t)

# 2b) FrontPage / IIS leftovers
leftovers = [
 "/iisstart.htm","/iisstart.png","/iisstart.asp","/welcome.png","/welcome.gif",
 "/trace.axd","/elmah.axd","/elmah.axd/detail","/glimpse.axd",
 "/aspnet_client/","/aspnet_client/system_web/","/aspnet_client/system_web/4_0_30319/",
 "/aspnet_client/system_web/2_0_50727/","/aspnet_client/system_web/4_0_30319/crystalreportviewers13/",
 "/bin/","/bin/Default.asp","/App_Data/","/App_Code/","/App_GlobalResources/","/App_Themes/",
 "/web.config","/Web.config","/web.config.bak","/web.config.old","/web.config.txt","/web.config.orig",
 "/global.asa","/Global.asa","/global.asa.bak","/global.asax","/global.asax.cs",
 "/Default.asp.bak","/Default.asp.old","/Default.asp~","/Default.asp.orig","/Default.asp.txt",
 "/Default.asp.save","/Default.asp.bak.txt","/Default.asp.#","/Default.asp.swp",
 "/index.asp","/index.html","/index.htm","/default.html","/default.htm",
 "/acuforum/Default.asp","/acuforum/","/acuforum/web.config","/acuforum/global.asa",
 "/robots.txt","/sitemap.xml","/favicon.ico","/phpinfo.php",
 "/_vti_pvt/","/_vti_pvt/service.pwd","/_vti_pvt/authors.pwd","/_vti_pvt/administrators.pwd",
 "/_vti_inf.html","/_vti_bin/","/_vti_bin/shtml.exe","/_vti_bin/_vti_aut/author.dll",
 "/_vti_bin/_vti_adm/admin.dll","/_vti_text/","/_vti_script/","/_vti_log/",
 "/_private/","/_private/","/MB/","/_derived/","/_overlay/","/_borders/","/_fpclass/",
 "/_vti_cnf/_vti_cnf/","/_vti_cnf/styles.css.cnf","/_vti_cnf/Images/logo.gif.cnf",
 "/_vti_cnf/Templates/MainTemplate.dwt.asp.cnf",
 "/crossdomain.xml","/clientaccesspolicy.xml","/.git/config","/.svn/entries","/.hg/",
 "/LICENSE.txt","/README.txt","/readme.txt","/CHANGELOG.txt","/TODO.txt","/notes.txt",
 "/backup.zip","/backup.rar","/site.zip","/www.zip","/db.zip","/database.zip",
 "/App_Data/database.mdb","/database.mdb","/acuforum/database.mdb","/db.mdb","/data.mdb",
 "/acuforum.mdb","/acuforum/db.mdb","/acuforum/data.mdb","/App_Data/acuforum.mdb",
 "/test.asp","/info.asp","/debug.asp","/errors.asp","/error.asp","/err.asp",
 "/cdosys.asp","/upload.asp","/fileupload.asp","/image.asp",
]
paths += leftovers

# 3) IIS case/extension quirks
quirks = ["/Default.asp.","/Default.asp ","/Default.asp%20","/Default.asp%20.","/Default.asp::$DATA",
          "/Default.asp/","/Default.asp%00","/Default.asp%00.txt","/default.asp::%24DATA",
          "/acuforum/Default.asp.","/acuforum/Default.asp::$DATA","/acuforum/Default.asp/",
          "/acuforum/Default.asp%20","/_vti_cnf/Default.asp.cnf::$DATA","/. /Default.asp",
          "/Default.asp.;","/styles.css::$DATA","/acuforum/styles.css::$DATA",
          "%2e/Default.asp","/acuforum/%2e%2e/Default.asp"]

# dedupe preserve order
seen=set(); P=[]
for p in paths+quirks:
    if p not in seen:
        seen.add(p); P.append(p)

def sanitize(p):
    return re.sub(r'[^A-Za-z0-9._-]','_',p.strip('/')) or 'root'

results=[]
for p in P:
    url = BASE + p
    body_file = os.path.join(BODIES, sanitize(p))
    cmd = ["curl","-sS","--path-as-is","-m","25","-A",UA,
           "-o",body_file,"-w","%{http_code}\t%{size_download}\t%{content_type}\t%{redirect_url}",
           url]
    try:
        r = subprocess.run(cmd,capture_output=True,text=True,timeout=40)
        out = r.stdout.strip()
    except Exception as e:
        out = "ERR\t0\t-\t-"
    parts = out.split("\t")
    code = parts[0] if parts else "ERR"
    size = parts[1] if len(parts)>1 else "0"
    ctype= parts[2] if len(parts)>2 else "-"
    redir= parts[3] if len(parts)>3 else ""
    results.append({"path":p,"url":url,"status":code,"size":size,"ctype":ctype,"redirect":redir,"body":body_file})

with open(os.path.join(OUT,"enum_results.json"),"w") as f:
    json.dump(results,f,indent=1)

interesting=[r for r in results if r["status"] not in ("404","ERR")]
print("TOTAL PROBED: %d   NON-404: %d" % (len(results), len(interesting)))
print("-"*100)
for r in interesting:
    print("%-8s %-7s %-70s %s" % (r["status"], r["size"], r["path"], r["ctype"]))
