# Round 4 — nuclei + nikto scan & per-item curl reproduction

- Target: `http://testasp.vulnweb.com` (44.238.29.244) — Acunetix intentional-vuln site, own_system / authorized
- Date: 2026-09-23 (UTC)
- Raw artifacts: `journal/web/testasp-vulnweb-full/scratch/round4/`
- Templates: **local only** (`/home/taeuk/nuclei-templates`, 13,742 YAML). `-update-templates` **skipped** (time).
- Nuclei v3.11.1, Nikto 2.6.1

## (a) Commands executed

```bash
# 1. nuclei — tech/IIS/ASP tags
nuclei -u http://testasp.vulnweb.com -tags iis,asp,aspnet,microsoft \
       -severity info,low,medium,high,critical -no-color -stats -silent \
       -o nuclei-tags-iis-asp.txt                     # 75 templates, EXIT=0

# 2. nuclei — exposures + misconfiguration dirs
nuclei -u http://testasp.vulnweb.com \
       -t /home/taeuk/nuclei-templates/http/exposures/ \
       -t /home/taeuk/nuclei-templates/http/misconfiguration/ \
       -no-color -stats -silent -o nuclei-exp-misconfig.txt   # EXIT=0

# 3. nikto full
nikto -h http://testasp.vulnweb.com -maxtime 600 -nointeractive \
      -output nikto-full.txt -Format txt             # EXIT=0, hit 600s maxtime

# 4. consolidated per-item reproduction
./verify_round4.sh > verify-consolidated.txt
```

## (b) What the scanners reported

**nuclei #1 (tags iis,asp,aspnet,microsoft)** — 6 matches
`microsoft-iis-version` ×1; `iis-shortname-detect` ×5

**nuclei #2 (exposures + misconfiguration)** — 18 lines
`cookies-without-secure`, `cookies-without-httponly`, `missing-cookie-samesite-strict`,
`http-missing-security-headers` ×9, `iis-shortname-detect` ×4

**nikto** — self-reported `13 items reported` (file contains 15 `+ ` lines; 2 are `Target Host`/`Target Port` metadata). Terminated by `Host maximum execution time of 600 seconds`; `No CGI Directories found … CGI tests skipped`

## (c) Verdict table — every item re-tested with curl

| # | Scanner | Reported item | curl reproduction | Verdict |
|---|---|---|---|---|
| 1 | nuclei | `microsoft-iis-version` | `Server: Microsoft-IIS/8.5` | **REAL** |
| 2 | nuclei | `iis-shortname-detect` ×9 (both scans) | `Images*~1*/a.aspx`, `Templates*~1*/a.aspx`, `aspnet_client*~1*/a.aspx`, and garbage `zzzznotreal9*~1*/a.aspx`, `q7w8e9r0t1*~1*/a.aspx` **all return identical 400/48B** | **FALSE POSITIVE** — IIS 8.5 rejects `*` outright; zero discrimination |
| 3 | nuclei | `cookies-without-secure` | `Set-Cookie: ASPSESSIONIDAABTRDTB=…; path=/` — no `Secure` | **REAL** |
| 4 | nuclei | `cookies-without-httponly` | same cookie — no `HttpOnly` | **REAL** |
| 5 | nuclei | `missing-cookie-samesite-strict` | same cookie — no `SameSite` | **REAL** |
| 6 | nuclei | `http-missing-security-headers` ×9 | all 9 confirmed absent (CSP, HSTS, XFO, XCTO, RP, PP, COEP, COOP, CORP) | **REAL** |
| 7 | nikto | `[999990] OPTIONS Allowed: OPTIONS,TRACE,GET,HEAD,POST` | `Allow: OPTIONS, TRACE, GET, HEAD, POST` | **REAL (header) / MISLEADING (TRACE)** — see #9 |
| 8 | nikto | `[999985] OPTIONS Public: …TRACE…` | `Public: OPTIONS, TRACE, GET, HEAD, POST` | **REAL (header) / MISLEADING** — see #9 |
| 9 | nikto | TRACE implied enabled | `curl -X TRACE` → **501**; raw netcat → `HTTP/1.1 501 Not Implemented` | **FALSE POSITIVE** — advertised but **not implemented** |
| 10 | nikto | `[000287] /index.aspx` exists | `/index.aspx` → **404** (1505B); `/nonexistent-xyz.aspx` → 404 (1515B), also emits `X-AspNet-Version: 2.0.50727` | **FALSE POSITIVE** (page). The *header* claim is real but fires on **any** `.aspx` 404 → not evidence the page exists |
| 11 | nikto | `[600376] Microsoft-IIS/8.5 may be outdated` | banner confirmed | **REAL (info)** |
| 12 | nikto | `[750537] /: Default IIS server content` | `/` returns `<title>acuforum forums</title>` (Acunetix forum app) | **FALSE POSITIVE** |
| 13 | nikto | `[999979] /aspnet_client: RFC-1918 IP in Location` | Host-less HTTP/1.0 → `Location: http://10.0.0.14/aspnet_client/` (3/3 runs) | **REAL** |
| 14 | nikto | `[999988] /aspnet_client: internal IP via HTTP/1.0 (CVE-2000-0649)` | same as #13 | **REAL** (duplicate of #13) |
| 15 | nikto | `[013587] missing: strict-transport-security` | absent | **REAL** |
| 16 | nikto | `[013587] missing: referrer-policy` | absent | **REAL** |
| 17 | nikto | `[013587] missing: content-security-policy` | absent | **REAL** |
| 18 | nikto | `[013587] missing: x-content-type-options` | absent | **REAL** |
| 19 | nikto | `[013587] missing: permissions-policy` | absent | **REAL** |
| 20 | nikto | `x-powered-by header: ASP.NET` | `X-Powered-By: ASP.NET` | **REAL (info)** |

**Score: 14 REAL / 5 FALSE POSITIVE (by item), or 12 REAL / 3 FP grouping the duplicates (#13/#14, and #7/#8 "misleading").**

## (d) Newly confirmed this round (emphasis)

1. **Internal IP disclosure `10.0.0.14` — REAL, reproducible 5/5.** Requires a **Host-less HTTP/1.0** request to `/aspnet_client` (301 → `Location: http://10.0.0.14/aspnet_client/`). With a normal `Host:` header it returns the correct public hostname, so a naive HTTP/1.1-only check misses it. Specific to `/aspnet_client` (a genuinely existing directory — control dirs return 404).
2. **`iis-shortname-detect` is a false positive on this target** (9 hits across both nuclei runs). Proven by discriminative control: real directories (`Images`, `Templates`, `aspnet_client`) and garbage names (`zzzznotreal9`, `q7w8e9r0t1`) all return the identical `400/48B` — IIS 8.5 rejects `*` before any 8.3 resolution, so there is no shortname signal.
3. **TRACE false positive re-confirmed** (round 2/3 carry-over): OPTIONS *advertises* `TRACE` in both `Allow:` and `Public:`, but the method itself returns **501 Not Implemented** (verified via both curl and raw netcat). XST is **not** exploitable.
4. **`/index.aspx` false positive re-confirmed** (round 2 carry-over): **404**. The `X-AspNet-Version: 2.0.50727` banner is emitted on *any* `.aspx` request including nonexistent ones, because the ASP.NET handler owns the `.aspx` extension — a plain 404 leaks the banner, which is what fooled nikto into flagging the path.
5. **PUT is not exploitable:** without `Content-Length` → `411` from **`Server: Microsoft-HTTPAPI/2.0`** (http.sys, pre-IIS); *with* a body → **404** and the file is **not created** (`GET /pwned-round4-test.txt` → 404). No WebDAV write.
6. **Session cookie `ASPSESSIONIDAABTRDTB` carries no `HttpOnly`/`Secure`/`SameSite`** — confirms nuclei's JS-based cookie checks with direct header inspection.
7. **`/db.asp` → `200` with `Content-Length: 0`** (empty 200, distinct from the app's normal pages) — flagged for follow-up, not a scanner finding.
8. **`/Trace.axd` → 403** but still emits `X-AspNet-Version: 2.0.50727`; consistent with round-2 app-wide handler behavior.

## Caveats

- nikto hit `-maxtime 600` and **did not complete** its full test set (CGI/dir brute-force skipped: `No CGI Directories found … CGI tests skipped`). A longer `-maxtime` run may surface more items.
- `-update-templates` was **not** run; results reflect the local template snapshot only.
- Method matrix: GET 200, HEAD 200, POST 411 (without CL) / 200 (with CL), OPTIONS 200, TRACE 501, TRACK 405, PUT 411→404, DELETE 405, PATCH 405, CONNECT 405, PROPFIND 405.
