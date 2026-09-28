#!/usr/bin/env python3
"""Probe known/candidate static paths on testasp.vulnweb.com and record REAL status codes."""
import http.client, sys, json, os, socket

HOST = "testasp.vulnweb.com"
UA = "Mozilla/5.0 (X11; Linux x86_64) Chrome/124.0"

CANDIDATES = [
    # site own
    "/styles.css", "/login.css", "/main.js", "/forum.js",
    "/Images/logo.gif", "/Images/", "/favicon.ico",
    "/html/about.html", "/html/", "/Templates/MainTemplate.dwt.asp", "/Templates/",
    "/_vti_cnf/Default.asp", "/_vti_cnf/styles.css", "/_vti_inf.html",
    "/web.config", "/global.asa", "/Templatize.asp", "/dsn.asp", "/rss.asp", "/atom.asp",
    "/forms.asp", "/post.asp", "/reply.asp", "/showpost.asp", "/profile.asp", "/admin.asp",
    # tiny_mce package (v2.0RC4 typical layout)
    "/jscripts/tiny_mce/tiny_mce.js", "/jscripts/tiny_mce/tiny_mce_src.js",
    "/jscripts/tiny_mce/tiny_mce_gzip.php", "/jscripts/tiny_mce/tiny_mce_gzip.js",
    "/jscripts/tiny_mce/tiny_mce_popup.js", "/jscripts/tiny_mce/tiny_mce_dev.js",
    "/jscripts/tiny_mce/license.txt", "/jscripts/tiny_mce/readme.txt",
    "/jscripts/tiny_mce/changelog.txt", "/jscripts/tiny_mce/index.php",
    "/jscripts/tiny_mce/docs/index.html", "/jscripts/tiny_mce/docs/",
    "/jscripts/tiny_mce/examples/index.html", "/jscripts/tiny_mce/examples/",
    "/jscripts/tiny_mce/langs/en.js", "/jscripts/tiny_mce/langs/",
    "/jscripts/tiny_mce/themes/advanced/editor_template.js",
    "/jscripts/tiny_mce/themes/advanced/editor_template_src.js",
    "/jscripts/tiny_mce/themes/advanced/langs/en.js",
    "/jscripts/tiny_mce/themes/advanced/css/editor_content.css",
    "/jscripts/tiny_mce/themes/advanced/css/editor_ui.css",
    "/jscripts/tiny_mce/themes/advanced/css/editor_popup.css",
    "/jscripts/tiny_mce/themes/advanced/images/opacity.png",
    "/jscripts/tiny_mce/themes/simple/editor_template.js",
    "/jscripts/tiny_mce/themes/default/editor_template.js",
    "/jscripts/tiny_mce/plugins/table/editor_plugin.js",
    "/jscripts/tiny_mce/plugins/table/editor_plugin_src.js",
    "/jscripts/tiny_mce/plugins/contextmenu/editor_plugin.js",
    "/jscripts/tiny_mce/plugins/flash/editor_plugin.js",
    "/jscripts/tiny_mce/plugins/emotions/editor_plugin.js",
    "/jscripts/tiny_mce/plugins/fullscreen/editor_plugin.js",
    "/jscripts/tiny_mce/plugins/insertdatetime/editor_plugin.js",
    "/jscripts/tiny_mce/plugins/advlink/editor_plugin.js",
    "/jscripts/tiny_mce/plugins/advimage/editor_plugin.js",
    "/jscripts/tiny_mce/plugins/advhr/editor_plugin.js",
    "/jscripts/tiny_mce/plugins/paste/editor_plugin.js",
    "/jscripts/tiny_mce/plugins/_template/editor_plugin.js",
    "/jscripts/tiny_mce/plugins/",
]

def head(path):
    c = http.client.HTTPConnection(HOST, 80, timeout=15)
    try:
        c.request("GET", path, headers={"User-Agent": UA, "Range": "bytes=0-0"})
        r = c.getresponse()
        body = r.read(600)
        return r.status, r.getheader("Content-Type"), r.getheader("Content-Length"), len(body)
    except Exception as e:
        return "ERR", str(e), "", 0
    finally:
        c.close()

res = []
for p in CANDIDATES:
    st, ct, cl, bl = head(p)
    res.append({"path": p, "status": st, "content_type": ct, "content_length": cl})
    print(f"{str(st):>5}  {str(ct)[:35]:<35} len={str(cl):<8} {p}")

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "path_probe.json")
json.dump(res, open(out, "w"), indent=1)
print("\nsaved ->", out)
