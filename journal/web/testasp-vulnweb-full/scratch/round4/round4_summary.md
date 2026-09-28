# Round 4 — widened extension scan + /_vti_cnf/ file-existence oracle (testasp.vulnweb.com)

Scope: http://testasp.vulnweb.com only (44.238.29.244, IIS 8.5 + classic ASP).
All work dir: journal/web/testasp-vulnweb-full/scratch/round4/

## (a) Commands executed

```bash
# wordlists
cat common.txt quickhits.txt raft-small-words.txt | sed 's/\r$//' | sort -u > merged_wl.txt   # 42,508 lines
cat common.txt quickhits.txt                        | sed 's/\r$//' | sort -u > small_wl.txt    # 6,659 lines

# S1 root, widened extension set, FULL match codes (the required rescan)
ffuf -u http://testasp.vulnweb.com/FUZZ -w merged_wl.txt \
     -e ".asp,.txt,.inc,.bak,.config,.log,.old,.zip,.xml,.asa,.aspx,.ashx,.asmx,.axd,.svc,.dwt,.dwt.asp,.css,.js,.ini" \
     -mc 200,204,301,302,307,400,401,403,405,500,501,502,503 -t 150 -s -o root_widened_full.json -of json

# B1 root oracle — task-specified oracle run (raft wordlist)
ffuf -u http://testasp.vulnweb.com/_vti_cnf/FUZZ -w merged_wl.txt \
     -e ".asp,.txt,.inc,.html,.dwt,.dwt.asp,.css,.js" -mc 200 -t 150 -s -o oracle_core.json -of json

# S2/S3 PER-DIRECTORY oracles (NEW surfaces discovered this round)
ffuf -u http://testasp.vulnweb.com/images/_vti_cnf/FUZZ             -w small_wl.txt -e ".gif,.jpg,.png,.ico,.swf,.css,.js,.asp" -mc 200 -o oracle_images.json -of json
ffuf -u http://testasp.vulnweb.com/jscripts/tiny_mce/_vti_cnf/FUZZ  -w small_wl.txt -e ".js,.css,.htm,.html,.txt,.gif,.jpg,.png" -mc 200 -o oracle_tinymce.json -of json

# S5/S6 root oracle, non-web + .htm/.ini extensions
ffuf -u http://testasp.vulnweb.com/_vti_cnf/FUZZ -w small_wl.txt -e ".zip,.xml,.config,.bak,.old,.log,.asa,.svc,.axd,.aspx,.ini,.mdb,.sql" -mc 200 -o oracle_root_extra.json -of json
ffuf -u http://testasp.vulnweb.com/_vti_cnf/FUZZ -w merged_wl.txt -e ".htm,.ini" -mc 200 -o oracle_root_htm_ini.json -of json

# legacy FrontPage/IIS paths + dot files: dotcheck.txt / dotcheck_results.txt (curl loop)
# targeted app-name probe (103 names x {oracle, live}): appnames.txt / appnames_results.txt
# oracle-vs-live cross-check: oracle_vs_live.txt
```

Runner scripts: run_s1.sh, run_lean.sh, run_round4.sh, run_round4_v2.sh. Logs: s1.log, lean.log, run_round4.log.
Oracle sanity proof: random misses return `404 1245`, real files return `200` — the oracle has no false positives.

## (b) Request volume & new locations

~1.68M HTTP requests total (ffuf 1,468,351 completed + ~213k from two aborted partial runs + ~340 curl probes).

**NEW (not in any earlier round):**
| Location | Evidence | Note |
|---|---|---|
| `/shownews.asp` | oracle 200 / live **500** (1208B) | orphan ASP that exists & errors; not linked from any page. Found by oracle, confirmed independently by the S1 `-mc 500` scan |
| `/Templates/MainTemplate.dwt.asp` | 200, 2488B | real FrontPage template file (dir was known, file was not) |
| `/html/about.html` | 200, 1995B | content page behind `Templatize.asp?item=html/about.html` |
| `/styles.css` | 200, 3390B | site stylesheet (HTML-referenced, previously only implied) |
| `/Images/logo.gif` | 200, 4933B | site logo asset |
| `/images/_vti_cnf/` | 403 (1233B = dir exists) | **NEW per-directory existence oracle** |
| `/jscripts/tiny_mce/_vti_cnf/` | 403 (1233B = dir exists) | **NEW per-directory existence oracle** |

Known-file rediscovery only (no novelty): Default/Login/LogOut/Register/Search/db/showforum/showthread/logout.asp, robots.txt, Templates, jscripts, _vti_cnf/, etc.

**Behavioural leads (not exploited this round):**
* `/search.asp?tfSearch=<non-empty>` → **500**, while `/search.asp` and `?tfSearch=` (empty) → 200. Unhandled exception on any search input — prime SQLi candidate for the exploit round.
* `/Templatize.asp?item=../Default.asp` → **500** while `?item=html/about.html` → 200. Path-handling error on traversal-shaped input.

**Methodological finding:** existing-but-erroring ASPs answer **500** (IIS page, 1208B), not 404. The `-mc 200,204,301,302,307,401,403` set used in earlier rounds silently misses this entire existence class (this is exactly how `shownews.asp` is provable). Scans must include `500`.

## (c) Files confirmed by the oracle (publish-time index)

Root `/_vti_cnf/`: `Default.asp` (926B), `Login.asp` (772B), `LogOut.asp` (338B), `Register.asp` (778B), `Search.asp` (926B), `ShowForum.asp` (861B), `ShowThread.asp` (882B), `DB.asp` (338B), **`shownews.asp`** (338B), `styles.css` (404B), `Templatize.asp` (930B — found by direct request; ffuf wordlists contain no "templatize" entry).
`/images/_vti_cnf/`: `logo.gif` (286B) — and nothing else.
`/jscripts/tiny_mce/_vti_cnf/`: `tiny_mce.js` (180B) — and nothing else.
Oracle enumeration over `.zip .xml .config .bak .old .log .asa .svc .axd .aspx .ini .mdb .sql` → **0 hits**; over `.htm .ini` (full raft) → **0 hits**.

## (d) Oracle-only files (in the index, missing from the original path)

**None.** Every oracle entry resolves live — see `oracle_vs_live.txt`.
Asymmetry runs the other way: two live files are **absent from the oracle** (created after the last FrontPage publish): `/logInput.asp` (200, 0B) and `/robots.txt` (200, 13B).

## (e) Negative results

* No `.bak .old .zip .log .config .xml .asa .svc .ini .htm .mdb .sql` file anywhere at root (root scan 850,160 reqs + oracle over same extensions).
* No `.git/` `.svn/` `.env` `.htaccess` `.htpasswd` `web.config` `web.config.bak` `global.asa` — all `404 1245`.
* Legacy FrontPage/IIS: `_vti_pvt/ _vti_bin/ _vti_inf.html _vti_log/ _vti_txt/ _vti_script/ _vti_map/ _vti_aut/ _vti_adm/ _vti_usr/ _vti_htm/ _derived/ _borders/ _private/ _themes/ MSOffice/ _mem_bin/ scripts/ msadc/ iisadmpwd/ iishelp/ AdminScripts/ Inetsrv/ _layouts/ App_Data/ App_Code/ Bin/` → all `404`; only `/aspnet_client/system_web/` exists (403).
* Per-directory `_vti_cnf` exists **only** under `/`, `/images/`, `/jscripts/tiny_mce/` — `Templates/ html/ avatars/ T/ cgi-bin/ aspnet_client/` → 404.
* IIS 8.3 short-name (tilde) enumeration: `/d*~1*/.asp`, `/DEFAUL~1.ASP`, `/shownews~1.asp`, … → all `404`. Not vulnerable.
* `*.axd` family is a trap: **any** path ending in `trace.axd` (even `/xyz123notreal/trace.axd`) returns `403 2062` (blanket IIS rule). The S1 hit `/actuator/trace.axd` is a wordlist artifact, not a finding. Other `.axd` hits were `400` (48B) artifacts of junk wordlist entries.
* 103 targeted app-name guesses (`news addnews editnews post reply topic forum user member profile admin config upload rss print contact archive …` × {oracle, live}) → only `shownews.asp`.
* Oracle gap (wordlist limitation): app-specific names such as `templatize`/`logInput` are absent from raft/common/quickhits, so a pure ffuf oracle run under-reports. Cross-check oracle hits with direct requests.
* `/shownews.asp`, `/Templatize.asp`, `/search.asp?tfSearch=x` all 500 — file existence must be judged by 404-vs-500, never by 200.
