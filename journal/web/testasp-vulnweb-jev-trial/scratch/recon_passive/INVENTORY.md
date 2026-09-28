# testasp.vulnweb.com — passive endpoint/param inventory

Sources: gau (wayback+otx+urlscan+cc providers), Wayback CDX, urlscan.io search API, Common Crawl index.
Scope: testasp.vulnweb.com only. GET-only live probes, no payloads.

## Raw files
| file | content |
|---|---|
| gau_raw.txt | 1098 lines gau output (983 unique chained URIs, ~90% pollution) |
| cdx_raw2.txt | 980 rows Wayback CDX (original,timestamp,statuscode) |
| urlscan.json | urlscan search (100 of 166 results; no API key → capped at 100) |
| cc_raw2.txt | Common Crawl CC-MAIN-2024-33 (6 URLs; other crawls 504) |
| live_check.txt | live curl status/size for 36 paths |
| live_showthread_ids.txt | live curl status/size for showthread id sweep |
| paths.txt | deduped path → sources |
| clean_paths.json | filtered distinct paths |

## (a) Unique paths with source

### Real application pages (interesting)
| path | sources | live (code / bytes) |
|---|---|---|
| / | cc,gau,urlscan,wayback | 200 / 3538 |
| /Default.asp | cc,gau,urlscan,wayback | 200 / 3538 |
| /Login.asp | gau,wayback | 200 / 3194 |
| /Register.asp | cc,gau,wayback | 200 / 3617 |
| /Search.asp (+ /search.asp) | gau,urlscan,wayback | 200 / 2809 |
| /logout.asp | gau,wayback | 302 / 132 |
| /Templatize.asp | gau,wayback | 200 (no param) |
| /Templates/MainTemplate.dwt.asp | gau,wayback | 200 / 2488 |
| /showforum.asp | gau,wayback | 302 / 132 (needs id) |
| /showthread.asp | cc,gau,urlscan,wayback | 302 / 132 (needs id) |
| /admin | gau,wayback | **404** |
| /session | gau,wayback | **404** |
| /Acunetix | gau,wayback | **404** |
| /t/fit.txt | gau,urlscan,wayback | 200 / 64 |
| /t/dot.gif | gau,wayback | 200 / 43 |
| /t/xss.html | gau,urlscan,wayback | 200 / 33 |
| /t/xss.js | gau,wayback | 200 / 27 |
| /campaign/adidas-x16 | gau,wayback | **404** |
| /1, /123, /16/2026, /9/2005 | gau,wayback | 404 / 301 |

### Static assets
/styles.css (200/3390), /rpb.png (200/40), /Images/logo.gif (200/4933),
/avatars/noavatar.gif (200/950), /robots.txt (200/13),
/favicon.ico (404), /logo.gif (404), /avatars/0..3 (404), /T (301)

### Paths seen only in wayback/gau, NOT live today
/admin, /session, /Acunetix, /campaign/adidas-x16, /logo.gif,
/avatars/0..3, /favicon.ico, /1, /123, /16/2026, /9/2005, /t/fit.txt?<wayback pollution>

## (b) Distinct query parameters

### Real application parameters
| param | example URL | live |
|---|---|---|
| id | http://testasp.vulnweb.com/showthread.asp?id=44 | 200 (id=1,2,3) / **500 (id>=5, 44,100)** |
| id | http://testasp.vulnweb.com/showforum.asp?id=1 | 200 / 3077 |
| RetURL | http://testasp.vulnweb.com/Login.asp?RetURL=/Default.asp | 200 / 3192 |
| RetURL | http://testasp.vulnweb.com/Register.asp?RetURL=/Search.asp | 200 |
| tfSearch | http://testasp.vulnweb.com/Search.asp?tfSearch=test | **500 / 1208** |
| tfsearch (case variant) | http://testasp.vulnweb.com/Search.asp?tfsearch=a | **500 / 1208** |
| item | http://testasp.vulnweb.com/Templatize.asp?item=html/about.html | 200 / 4594 |
| XNYy | Login.asp?RetURL=/showforum.asp?id=1&XNYy=3116 AND 1=1 UNION ALL SELECT ... | scanner-injected, not an app param |

Notable historical payload values (evidence of past fuzzing, NOT params):
- Search.asp?tfSearch="><script>alert('xss')</script>, ...<script src="http://sc0rn.com/cfy.js">
- Search.asp?tfSearch=>xss.report/c/dusheeno
- showforum.asp?id=0+and+1=1--[True]
- Login.asp?RetURL=/showforum.asp?id=1)(()(.,,'"

### Pollution-derived params (from wayback junk appended to /t/fit.txt? and /t/xss.html?)
NOT parameters of this application — they are the query string of *other* sites' URLs
that got concatenated onto testasp URLs by a scanner/form loop and archived:
q, ei, rt, vm, bvm, did, sid, ssid, st, at, shr, hl, ict, ned, pz,
chl, chs, choe, chld, utm_source, utm_medium, utm_campaign, wr_id, id_menu

## (c) Still live today (GET, http://testasp.vulnweb.com)
200: /, /Default.asp, /Login.asp[?RetURL=...], /Register.asp, /Search.asp (paramless),
/search.asp, /Templatize.asp?item=..., /Templates/MainTemplate.dwt.asp,
/showthread.asp?id=1|2|3, /showforum.asp?id=1, /t/fit.txt, /t/dot.gif, /t/xss.html,
/t/xss.js, /robots.txt, /styles.css, /rpb.png, /Images/logo.gif, /avatars/noavatar.gif
302: /logout.asp, /showforum.asp (no id), /showthread.asp (no id)
301: /T
500: /Search.asp?tfSearch=<anything non-empty>, /showthread.asp?id>=5
404: /admin, /session, /Acunetix, /campaign/adidas-x16, /avatars/0..3, /favicon.ico,
/logo.gif, /1, /123

## (d) Exact commands
```
mkdir -p .../recon_passive && cd .../recon_passive

# 1 gau
/home/taeuk/go/bin/gau --threads 5 testasp.vulnweb.com > gau_raw.txt

# 2 wayback CDX
curl -s 'http://web.archive.org/cdx/search/cdx?url=testasp.vulnweb.com*&output=text&fl=original,timestamp,statuscode&collapse=urlkey&limit=2000' -o cdx_raw2.txt

# 3 urlscan.io (no key -> 100 result cap; &size=1000 ignored without key)
curl -s 'https://urlscan.io/api/v1/search/?q=domain:testasp.vulnweb.com' -o urlscan.json

# 4 common crawl (CC-MAIN-2024-33 worked; 2024-51/2025-30 returned 504)
curl -s 'http://index.commoncrawl.org/CC-MAIN-2024-33-index?url=testasp.vulnweb.com%2F*&output=json&limit=500' -o cc_raw2.txt

# 5 live cross-check (GET, no payload)
curl -s -o /dev/null -m 15 -w '%{http_code} %{size_download} %{content_type}' 'http://testasp.vulnweb.com/PATH'
```

## Notes / caveats
- gau output is ~90% wayback link-pollution anchored on /t/fit.txt and /t/xss.html —
  filtered by requiring ^/[A-Za-z0-9_./%-]+$ and no embedded "http".
- Internet Archive CDX first attempt returned the "Temporarily Offline" page; retry succeeded.
- urlscan.io without an API key caps at 100 results (166 total available); no request-level
  (`.asp` list) data exposes without the full result API.
- No .asp path beyond the set above was found in any passive source.
- The two live 500s (/Search.asp?tfSearch=<non-empty> and /showthread.asp?id>=5) return the
  **generic IIS "500 - Internal server error" page** (identical 1208-byte body, no stack/DB
  detail) — they are unhandled exceptions, NOT confirmed SQL error leakage. Treat as
  "input reaches a handler" signal only.
