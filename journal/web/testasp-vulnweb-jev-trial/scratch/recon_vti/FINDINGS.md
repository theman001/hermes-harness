# testasp.vulnweb.com — FrontPage / DreamWeaver / IIS legacy artifact recon

TARGET: http://testasp.vulnweb.com  (IIS 8.5, ASP.NET 2.0.50727, classic ASP forum "acuforum")
SCOPE: recon only. No injection/auth-bypass payloads.
DATE: 2026-09-28 (UTC)
RAW OUTPUT: recon_vti/ (probe_paths.py, reprobe.py, map.py, quirks.py, dump_cnf.py, ALL_VTI_CNF_DUMP.txt, map_output.txt, quirks_output.txt, bodies/)

---

## 1. THE BIG ONE — FrontPage metadata served for EVERY page

FrontPage `_vti_cnf` metadata files are directly downloadable, and on this host they are stored
**at `/_vti_cnf/<original-filename>` (exactly the source file name, NOT `<name>.cnf`)**.
The `<name>.cnf` form is 404 — the plain-name form is 200. IIS also resolves `/_vti_cnf/` to
`/_vti_cnf/Default.asp` (default-document).

| path | status | size | leaks |
|---|---|---|---|
| `/_vti_cnf/` (→ `/_vti_cnf/Default.asp`) | 200 | 926 | full cnf for home page |
| `/_vti_cnf/Default.asp` | 200 | 926 | vti_cachedsvcrellinks → **internal web-root folder name `acuforum/`** |
| `/_vti_cnf/Search.asp` | 200 | 926 | same + filesize 4303 |
| `/_vti_cnf/Login.asp` | 200 | 772 | title "acuforum login", filesize 3681 |
| `/_vti_cnf/Register.asp` | 200 | 778 | title "acuforum register", filesize 3888 |
| `/_vti_cnf/showforum.asp` | 200 | 861 | **leaks `acuforum/jscripts/tiny_mce/tiny_mce.js`**, filesize 6897 |
| `/_vti_cnf/showthread.asp` | 200 | 882 | same, filesize 6250 |
| `/_vti_cnf/Templatize.asp` | 200 | 930 | filesize 2510 |
| `/_vti_cnf/logout.asp` | 200 | 338 | filesize 225 |
| `/_vti_cnf/DB.asp` (also `db.asp`) | 200 | 338 | filesize 284 → confirms DB include file exists |
| `/_vti_cnf/styles.css` | 200 | 404 | served as text/css, filesize 3390 |
| **`/_vti_cnf/shownews.asp`** | **200** | **338** | **NEW unlinked file** — `/shownews.asp` itself returns **500**, filesize 402, `vti_backlinkinfo`/`vti_cachedlinkinfo` **empty** (orphaned/hidden page) |

Complete set of root files that have FrontPage metadata (verified by wordlist scan, case-insensitive):
`default.asp, search.asp, login.asp, register.asp, showforum.asp, showthread.asp, shownews.asp,
templatize.asp, logout.asp, db.asp, styles.css` — **`shownews.asp` is the only one not reachable by
crawling the site** (`Default.asp`/menu never link it; its own request errors 500).

Fields present: `vti_encoding` (utf8-nl), `vti_timelastmodified` / `vti_cacheddtm`
(**05 Oct 2007 10:01:19**), `vti_extenderversion` (**4.0.2.8912** = FrontPage 2002 / STS extender),
`vti_filesize`, `vti_cachedlinkinfo`, `vti_cachedsvcrellinks`, `vti_cachedtitle`, `vti_title`,
`vti_cachedbodystyle`, `vti_cachedhasbots/hastheme/hasborder`, `vti_metatags`, `vti_backlinkinfo`.
**No `vti_author` / `vti_sourcecontrol*` / username field is exposed.**

Reproduce:
```
curl -sS 'http://testasp.vulnweb.com/_vti_cnf/'                       # 200, 926 B
curl -sS 'http://testasp.vulnweb.com/_vti_cnf/showforum.asp'          # 200, 861 B
curl -sS 'http://testasp.vulnweb.com/_vti_cnf/DB.asp'                 # 200, 338 B
```

### What `vti_cachedsvcrellinks` reveals (internal paths)
```
vti_cachedsvcrellinks:VX|FQUS|acuforum/styles.css NHHS|http://www.acunetix.com/ \
  FSUS|acuforum/Images/logo.gif FHUS|acuforum/Templatize.asp FHUS|acuforum/Default.asp \
  FHUS|acuforum/Search.asp FSUS|acuforum/jscripts/tiny_mce/tiny_mce.js
vti_backlinkinfo:VX|acuforum/login.asp acuforum/register.asp acuforum/search.asp \
  acuforum/default.asp acuforum/showthread.asp acuforum/showforum.asp acuforum/templatize.asp
```
→ **web root directory name on disk = `acuforum`** (the site root maps to a folder called `acuforum`;
`http://testasp.vulnweb.com/acuforum/` itself is 404, so it is a physical dir name, not a virtual path).
→ internal sub-paths confirmed: `Images/`, `jscripts/tiny_mce/`.

## 2. Other `_vti_cnf` directories (case-insensitive FS: /Images == /images)

| path | status | note |
|---|---|---|
| `/Images/_vti_cnf/` (= `/images/_vti_cnf/`) | 403 | dir exists, listing denied |
| `/Images/_vti_cnf/logo.gif` | 200 | 286 B FrontPage image marker (image/gif) |
| `/jscripts/tiny_mce/_vti_cnf/` | 403 | dir exists |
| `/jscripts/tiny_mce/_vti_cnf/tiny_mce.js` | 200 | 180 B marker (application/javascript) |
| `/Templates/_vti_cnf/`, `/html/_vti_cnf/`, `/jscripts/_vti_cnf/`, `/t/_vti_cnf/`, `/_vti_cnf/zzz/`, `/nonexist/_vti_cnf/` | 404 | do not exist |

403-vs-404 baseline verified: `/random_nonexistent_dir_xyz/` = 404, so every 403 above is a real directory.
Reproduce:
```
curl -sS -o /dev/null -w '%{http_code} %{size_download}\n' 'http://testasp.vulnweb.com/Images/_vti_cnf/logo.gif'
curl -sS -o /dev/null -w '%{http_code} %{size_download}\n' 'http://testasp.vulnweb.com/jscripts/tiny_mce/_vti_cnf/tiny_mce.js'
```

## 3. DreamWeaver template + app surface

| path | status | size | note |
|---|---|---|---|
| `/Templates/MainTemplate.dwt.asp` | 200 | 2488 | **DW template source served raw** (`TemplateBeginEditable`), links `../styles.css`, `../Images/logo.gif`, `Templatize.asp?item=html/about.html` |
| `/Templates/MAINTEMPLATE.DWT.ASP` (any case) | 200 | 2488 | IIS case-insensitive |
| `/Templates/` | 403 | 1233 | listing denied |
| `/Templates` | 301 | 160 | → `/Templates/` |
| `/Templates/*.dwt.asp` other names (Default, template, Main, header, footer, menu, login, …) | 404 | | none besides MainTemplate |
| `/Default.asp` | 200 | 3538 | leaks `<!-- InstanceBegin template="/Templates/MainTemplate.dwt.asp" ... -->` |
| `/Search.asp` | 200 | 2809 | |
| `/Login.asp` = `/login.asp` | 200 | 3194 | |
| `/Register.asp` = `/register.asp` | 200 | 3617 | |
| `/showforum.asp`, `/showthread.asp`, `/logout.asp` | 302 | 132 | `Location: Default.asp` (need params) |
| `/Templatize.asp` (no params) | **500** | 1208 | Server error — template include fails without `item` |
| `/Templatize.asp?item=html/about.html` | 200 | 4594 | site's own menu link; confirms `html/` is the item include root |
| `/DB.asp` = `/db.asp` | **200** | **0** | exists, executed by ASP (session cookie set), emits nothing — pure include |
| `/styles.css` | 200 | 3390 | |
| `/Images/logo.gif` | 200 | 4933 | real logo (vs 286 B cnf marker) |
| `/html/` | 403 | 1233 | exists |
| `/html/about.html` | 200 | 1995 | |
| `/jscripts/` | 403 | 1233 | exists |
| `/jscripts/tiny_mce/` | 403 | 1233 | exists |
| `/jscripts/tiny_mce/tiny_mce.js` | 200 | 132342 | TinyMCE (old, served as application/javascript) |
| `/robots.txt` | 200 | 13 | body = `User-agent: *` (Last-Modified 2019-05-06) |

## 4. IIS leftovers / controls

| path | status | size | note |
|---|---|---|---|
| `/trace.axd` | **403** | 2062 | exists; header **`X-AspNet-Version: 2.0.50727`**; "trace settings prevent viewing remotely" |
| `/aspnet_client/` | 403 | 1233 | exists |
| `/aspnet_client/system_web/` | 403 | 1233 | exists |
| `/aspnet_client/system_web/2_0_50727/` | 403 | 1233 | ASP.NET 2.0 client dir present |
| `/aspnet_client/system_web/4_0_30319/` | 404 | 1245 | not present |
| `/elmah.axd` | 404 | 1504 | ASP.NET-style 404 (different body size) |
| `/glimpse.axd` | 404 | 1506 | idem |
| `/iisstart.htm`, `/iisstart.png`, `/welcome.png`, `/_vti_inf.html`, `/_vti_bin/shtml.exe`, `/_vti_pvt/`, `/_private/`, `/_derived/`, `/_borders/`, `/_fpclass/`, `/web.config`, `/global.asa`, `/global.asax`, `/bin/`, `/App_Data/`, `/App_Code/`, `/favicon.ico`, `/index.asp`, `/index.html`, all `*.bak|.old|~|.txt|.orig` variants | 404 | 1245 | generic IIS 404 body `404 - File or directory not found.` |

## 5. Case / extension quirks (IIS 8.5 on this host)

Baseline: nonexistent = **404 / 1245 B**; generic 404 text = `404 - File or directory not found.`

| request | status | size | deviation |
|---|---|---|---|
| `/Default.asp` | 200 | 3538 | — |
| `/Default.asp.` | 404 | 1245 | no trailing-dot bypass |
| `/Default.asp ` / `/Default.asp%20` / `/Default.asp%20.` | 404 | 1245 | no trailing-space bypass |
| `/Default.asp::$DATA`, `/styles.css::$DATA`, `/Templates/MainTemplate.dwt.asp::$DATA`, `/html/about.html::$DATA`, `/Default.asp::$data`, `/styles.css:.txt`, `/styles.css::$index_allocation` | 404 | 1245 | **no NTFS ADS / source disclosure** |
| `/Default.asp/`, `/styles.css/`, `/Templates/MainTemplate.dwt.asp/`, `/html/about.html/` | 404 | 1245 | no path-info/script-path bypass |
| `/Default.asp%00`, `/Default.asp%00.txt`, `/Default.asp%00.jpg`, `/styles.css%00`, `/styles.css%00.gif` | **400** | 324 | ⚠ deviation: null byte → 400 (text/html; charset=us-ascii), IIS rejects before routing |
| `/Default.asp%2520` | 404 | 1245 | double-encode no effect |
| `/%2e%2e/Default.asp` | **403** | 312 | ⚠ `..` at root → 403 (canonicalization check) |
| `/..\Default.asp` | **403** | 312 | ⚠ backslash form, same |
| `/acuforum/%2e%2e/Default.asp`, `/html/%2e%2e/Default.asp`, `/%2e/Default.asp` | **200** | 3538 | ⚠ `..` inside a subpath is normalized → resolves to `/Default.asp` (same size 3538). No escape beyond root observed. |
| `/Default.asp%2f`, `/Default.asp%5c`, `/Default.asp\` | 404 | 1245 | — |
| `/Default.asp;.txt`, `/Default.asp;.asp`, `/Default.asp;` | 404 | 1245 | no semicolon bypass |
| `/Default.asp%23`, `%3f`, `%3b` | 404 | 1245 | — |
| `/DEFAULT.ASP`, `/SeArCh.AsP`, `/STYLES.CSS` | 200 (3538/2809/3390) | — | ⚠ full case-insensitive filesystem |

Reproduce:
```
curl -sS --path-as-is -o /dev/null -w '%{http_code} %{size_download}\n' 'http://testasp.vulnweb.com/Default.asp%00'
curl -sS --path-as-is -o /dev/null -w '%{http_code} %{size_download}\n' 'http://testasp.vulnweb.com/%2e%2e/Default.asp'
curl -sS --path-as-is -o /dev/null -w '%{http_code} %{size_download}\n' 'http://testasp.vulnweb.com/html/%2e%2e/Default.asp'
```

## 6. HTTP methods on `/` (and `/Default.asp`, `/Search.asp`, `/html/about.html`, `/Templates/`, `/_vti_cnf/`)

| method | status | note |
|---|---|---|
| OPTIONS | **200** | `Allow: OPTIONS, TRACE, GET, HEAD, POST` / `Public: OPTIONS, TRACE, GET, HEAD, POST` |
| TRACE | **501** | Not Implemented — TRACE disabled (no XST) |
| PUT | **411** | Length Required, `Server: Microsoft-HTTPAPI/2.0` (kernel HTTP.sys, not IIS) → no WebDAV PUT |
| DELETE | 405 | `Allow: GET, HEAD, OPTIONS, TRACE` |
| PATCH / PROPFIND / DEBUG | 405 | `Allow: GET, HEAD, OPTIONS, TRACE` → **no WebDAV module** |
| HEAD | 200 | same as GET |

Reproduce:
```
curl -sS -X OPTIONS -D - -o /dev/null 'http://testasp.vulnweb.com/'
curl -sS -X TRACE   -D - -o /dev/null 'http://testasp.vulnweb.com/'
```

## 6b. App parameter inventory (from rendered pages — recon, no payloads sent)

- `Default.asp` — forum index. Forum rows link to `showforum.asp?id=N`:
  `id=0` "Acunetix Web Vulnerability Scanner" (6 threads/6 posts, last 2026-09-28 07:16),
  `id=1` "Weather" (1/1, last 2005-11-09), `id=2` "Miscellaneous" (0/0).
- `showforum.asp?id=N` and `showthread.asp?…` → 302 to `Default.asp` when params are absent/bad.
- `Templatize.asp?item=<path>` — template/include endpoint; `item=html/about.html` is the site's own link and returns 200.
- `Search.asp` — form `frmSearch` (action="" → POST to self), input `name=tfSearch`.
- `Login.asp` — form fields `tfUName`, `tfUPass` (ids same); `RetURL` param on `./Login.asp?RetURL=…`.
- `Register.asp` — form `frmRegister`, fields `tfEmail`, `tfRName`, `tfUName`, `tfUPass` (ids same).
- `logout.asp`, `DB.asp` — no output.

## 7. Bruteforce results (raft-small.txt, 43,007 words)

- `/Templates/FUZZ` + `.dwt.asp` → **only `maintemplate.dwt.asp`** (= MainTemplate.dwt.asp). No other DW template.
- `/_vti_cnf/FUZZ` (bare, no extension) → only the already-known pages (case variants of
  default/search/login/register/logout/db/styles). The cnf set exactly mirrors the real file set — no extra files.
- `/_vti_cnf/FUZZ` + `.cnf` → nothing (the `.cnf`-suffixed naming does **not** exist here).

---

## Why this matters (for later exploitation planning)
- `/_vti_cnf/<page>` gives a **complete authored file inventory** of the root (names + on-disk sizes + 2007 timestamps), incl. `DB.asp` (a DB include whose existence is only visible this way) and `showforum/showthread` sizes.
- Reveals two working include roots that are otherwise unguessable: **`html/`** (Templatize `item=` target that returns 200) and **`jscripts/tiny_mce/`**.
- Physical web-root folder name `acuforum` leaked → useful for absolute-path disclosure / error-message correlation.
- ASP.NET **2.0.50727** confirmed via `X-AspNet-Version` on `/trace.axd`, matching the `/aspnet_client/system_web/2_0_50727/` directory → old .NET runtime with known CVEs (e.g. padding oracle class) is present, though the app itself is classic ASP.
- `/Templatize.asp` is a confirmed template-include endpoint (500 without `item`, 200 + rendered file with it) — the `html/about.html` path is the documented, benign value.
- Hardened against the usual IIS tricks: no ADS, no trailing dot/space, no `;` bypass, `..` above root = 403. Only deviations: `%00` → 400, and `..` inside a subpath normalizes (unreachable beyond root).
