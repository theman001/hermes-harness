# testasp.vulnweb.com — directory/file recon: NEW paths (ffuf)

Scope: http://testasp.vulnweb.com only (IIS 8.5 / ASP.NET, case-insensitive). Recon only, no exploit attempts.
Baseline: nonexistent path = `404` with body length `1245`; directory without trailing slash = `301` to `/dir/`;
existing directory with trailing slash = `403` (directory listing denied). 404 (len 1245) filtered with `-fc 404`.

## Commands run (all raw output in this directory)

F1  `ffuf -u http://testasp.vulnweb.com/FUZZ -w ../raft-small.txt -e .asp,.aspx -rate 100 -t 35 -timeout 15 -fc 404 -s -of json -o root_raft_asp.json` (129k reqs)
F2  per-directory: `ffuf -u http://testasp.vulnweb.com/<DIR>/FUZZ -w ../common.txt -e .asp,.aspx,.txt,.inc,.htm,.html -rate 110 -t 35 -timeout 15 -fc 404 -s -of json -o <DIR>_common.json` for DIR in `_vti_cnf, Templates, HTML, T`
F3  same but `-e .asp,.aspx,.txt,.inc` for DIR in `jscripts, Images, avatars, aspnet_client, cgi-bin`
F4  `ffuf -u .../_vti_cnf/FUZZ -w ../common.txt -e .asp,.aspx,.css,.js,.htm,.html,.txt` → `vticnf_common_ext.json`
F5  `ffuf -u .../Templates/FUZZ -w ../common.txt -e .dwt,.dwt.asp,.tpl,.html,.htm,.txt,.asp` → `Templates_common_ext.json`
F6  `ffuf -u .../cgi-bin/FUZZ -w ../common.txt -e .txt,.pl,.cgi,.exe,.dll` → `cgibin_common_ext.json`
F7  `ffuf -u .../jscripts/tiny_mce/FUZZ -w ../common.txt -e .js,.htm,.html` → `tiny_mce_common.json`
F8  `ffuf -u .../Images/_vti_cnf/FUZZ -w ../common.txt -e .gif,.jpg,.png` → `images_vticnf_common_ext.json`
F9  `ffuf -u .../t/FUZZ -w ../common.txt -e .txt,.html,.htm,.asp` → `t_common_ext.json`
Runners: run_scanA_root_raft.sh, run_scanB_dirsA.sh, run_scanC_dirsB.sh, run_scanF1.sh, run_scanF2.sh, run_scanH.sh

## NEW paths (not in the already-discovered list)

| path | status | len | note |
|---|---|---|---|
| /shownews.asp | 500 | 1208 | **unlinked orphan ASP page**; /_vti_cnf/shownews.asp metadata has empty backlinkinfo → nothing links to it; 500 without params (same 1208-byte error as templatize.asp). Highest-interest find. |
| /_vti_cnf/Default.asp | 200 | 926 | FrontPage metadata: leaks file list + backlinks + subweb name `acuforum` |
| /_vti_cnf/Search.asp | 200 | 926 | metadata |
| /_vti_cnf/Login.asp | 200 | 772 | metadata |
| /_vti_cnf/register.asp | 200 | 778 | metadata |
| /_vti_cnf/showthread.asp | 200 | 882 | metadata; references ./jscripts/tiny_mce/tiny_mce.js |
| /_vti_cnf/showforum.asp | 200 | 861 | metadata |
| /_vti_cnf/templatize.asp | 200 | 930 | metadata |
| /_vti_cnf/logout.asp | 200 | 338 | metadata |
| /_vti_cnf/DB.asp | 200 | 338 | metadata (mirrors 0-byte /DB.asp) |
| /_vti_cnf/styles.css | 200 | 404 | metadata |
| /_vti_cnf/shownews.asp | 200 | 338 | metadata — confirms shownews.asp is a real deployed file (402 bytes on disk) |
| /Images/_vti_cnf/ | 403 | 1233 | nested metadata dir (exists) |
| /Images/_vti_cnf/logo.gif | 200 | 286 | metadata |
| /Images/logo.gif | 200 | 4933 | site logo (referenced by every page) |
| /styles.css | 200 | 3390 | site stylesheet |
| /avatars/noavatar.gif | 200 | 950 | placeholder avatar (also /avatars/ is a dir) |
| /HTML/About.html | 200 | 1995 | **the item rendered by Templatize.asp?item=html/about.html** (case-insensitive) |
| /Templates/MainTemplate.dwt.asp | 200 | 2488 | Dreamweaver template processed by ASP; contains `<link href="../styles.css">`, `../Images/logo.gif`; confirmed by direct GET |
| /cgi-bin/test.txt | 200 | 3 | file readable inside otherwise-403 /cgi-bin/ |
| /t/fit.txt | 200 | 64 | exists in /t/ (contents: repeated md5-looking hex) |
| /t/xss.html | 200 | 33 | exists in /t/ (contents: `<script>prompt(98589956)</script>` — artifact left by a previous tester) |
| /jscripts/tiny_mce/ | 403 | 1233 | tinyMCE tree (dir) |
| /jscripts/tiny_mce/tiny_mce.js | 200 | 132342 | tinyMCE main script |
| /jscripts/tiny_mce/tiny_mce_popup.js | 200 | 6835 | tinyMCE popup |
| /jscripts/tiny_mce/blank.htm | 200 | 213 | tinyMCE blank page |
| /jscripts/tiny_mce/langs/en.js | 200 | 1650 | tinyMCE lang |
| /jscripts/tiny_mce/utils/validate.js | 200 | 1719 | |
| /jscripts/tiny_mce/utils/form_utils.js | 200 | 6029 | |
| /jscripts/tiny_mce/utils/mctabs.js | 200 | 1836 | |
| /jscripts/tiny_mce/themes/simple/editor_template.js | 200 | 5727 | |
| /jscripts/tiny_mce/themes/ , /utils/ , /langs/ , /_vti_cnf/ | 403 | 1233 | dirs (exist, listing denied) |
| /aspnet_client/system_web/ | 403 | 1233 | dir exists |
| /aspnet_client/system_web/2_0_50727/ | 403 | 1233 | ASP.NET 2.0 client-script dir exists (contents not identified — no known filenames returned 200) |

Also present but already in parent's ffuf_dirs.json: /robots.txt (200, 13 bytes = `User-agent: *`).

## Notes / negatives
- Root-level raft-small sweep with `.asp/.aspx` (43k words x3): the ONLY new file is /shownews.asp — strong evidence there are no other root-level ASP pages.
- Curated ~110-name probe for admin/include/backup/config names (admin.asp, conn.asp, config.asp, web.config, global.asa, *.mdb, *.zip, inc/, includes/, ...) at root AND via the `/_vti_cnf/<name>` oracle: **all 404** — no obvious admin/backup/config file found.
- `/Templates/`, `/HTML/`, `/T/`, `/avatars/`, `/aspnet_client/` scans with common.txt + extensions returned nothing beyond the items above.
- `/cgi-bin/` exists but directory listing is 403; only `/cgi-bin/test.txt` is readable.
- FrontPage metadata oracle: `/_vti_cnf/<filename>` returns 200 iff the file existed in the FrontPage web (all files date to 2007). Useful for cheap existence checks of the deployed tree.
- Server methods: `OPTIONS /` → `Allow: OPTIONS, TRACE, GET, HEAD, POST`; `TRACE /` → 501 (not enabled). No PUT/DELETE advertised.
- Metadata of every page shows subweb name `acuforum` and mtime 05 Oct 2007, FrontPage 4.0.2.8912.
