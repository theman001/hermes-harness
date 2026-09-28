# Scanner recon summary — testasp.vulnweb.com

Date (UTC): 2026-09-28 ~07:16–07:22
Target: http://testasp.vulnweb.com (44.238.29.244, ec2-44-238-29-244.us-west-2.compute.amazonaws.com)
Scope: single hostname only. No exploitation, no fuzzing payloads.

## Commands run
1. `/usr/bin/nmap -Pn -sV -p 80,443,8080,8000 --version-intensity 5 testasp.vulnweb.com -oN nmap.txt`
2. `/home/taeuk/.local/bin/nikto -host http://testasp.vulnweb.com -maxtime 240 -nointeractive -output nikto.txt -Format txt`
3. `/home/taeuk/go/bin/nuclei -u http://testasp.vulnweb.com -tags tech,exposure,misconfig -severity info,low,medium -rl 60 -timeout 10 -silent -stats -o nuclei.txt`
   (intrusive/fuzz/dos tags NOT used)
4. Supplemental verification: curl header probes, raw-socket HTTP/1.0 probes, 40-request sequential rate-limit probe.

## Ports / service (nmap)
- 80/tcp   open     http   Microsoft IIS httpd 8.5  (OS: Windows, cpe:/o:microsoft:windows)
- 443/tcp  filtered https
- 8000/tcp filtered http-alt
- 8080/tcp filtered http-proxy
- rDNS: ec2-44-238-29-244.us-west-2.compute.amazonaws.com

## Findings grouped by severity

### MEDIUM+
- (none confirmed by safe templates) — no medium/high CVE template matched.

### LOW
- **Internal IP disclosure** (nikto 999979/999988, CVE-2000-0649): request `/aspnet_client` **without a Host header** → `301` with `Location: http://10.0.0.14/aspnet_client/`. REPRODUCED via raw socket (with a Host header it returns the public name, so it only leaks when Host is absent/unknown).
- **Information disclosure — version headers**: `Server: Microsoft-IIS/8.5` on every response; `X-Powered-By: ASP.NET`; `X-AspNet-Version: 2.0.50727` leaked on app-vhost 404s (e.g. `GET /index.aspx`).
- **Outdated/legacy platform** (nikto 600376): IIS 8.5 outdated vs current; ASP.NET 2.0.50727 (EOL) in use.
- **Dreamweaver/FrontPage artifacts exposed** (verifies nuclei `tech-detect:dreamweaver`):
  - `GET /Templates/MainTemplate.dwt.asp` → **200** (2488 b) — Dreamweaver template served
  - `GET /_vti_cnf/` → **200** (926 b) — FrontPage config dir accessible
  - `GET /Templatize.asp` → **500** (server error, 1208 b)
  - `GET /Templates/` → 403; `/_vti_bin/`, `/_vti_inf.html` → 404
- **Cookie flags** (nuclei): `ASPSESSIONIDCCCTQDSA` set without `Secure`, without `HttpOnly`, without `SameSite`.

### INFO
- **Technology**: Microsoft-IIS 8.5, ASP.NET, Dreamweaver, classic ASP forum app ("acuforum", Acunetix demo).
- **OPTIONS / : `Allow: OPTIONS, TRACE, GET, HEAD, POST`** — TRACE advertised, **but an actual `TRACE /` returns `501 Not Implemented`** → TRACE is NOT actually enabled (nikto 999990/999985 is misleading here; verified by hand).
- **Default IIS content at /**: without a Host header, `GET /` returns the generic "IIS Windows Server" welcome page (200, 701 b) — the acuforum app is bound as a **name-based vhost**; Host header controls which content is served.
- **Missing security headers** (both nikto 013587 and nuclei): Strict-Transport-Security, Content-Security-Policy, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, X-Permitted-Cross-Domain-Policies, Cross-Origin-Embedder/Opener/Resource-Policy.
- **Nuclei `waf-detect:aspgeneric`** — generic ASP.NET fingerprint only, **not evidence of a real WAF** (see rate-limit section).
- **403s seen**: `/aspnet_client/`, `/aspnet_client/system_web/`, `/Templates/` (directory access denied).
- Live pages found: `/` 200, `/default.asp` 200, `/login.asp` 200. 404s: `/index.aspx`, `/default.aspx`, `/forum/default.asp`, `/news.asp`, `/tutorials.asp`, `/about.asp`.

## Rate-limit / WAF observations
- **No WAF or rate limiting observed.** 40 sequential requests to `/` → 40× HTTP 200, zero 429/403 bursts, latency min/avg/max 0.298/0.336/0.380 s, ~3 req/s.
- nuclei sustained ~60 req/s (its `-rl 60` cap) across ~4.5k requests with **no 429 and no throttling**; RPS stayed flat 56–64.
- **Caveat**: nikto terminated early at its own 240 s limit ("Host maximum execution time of 240 seconds reached", 13 items) — nikto's coverage was **incomplete**, not blocked by the target.
- nuclei reported **19 request errors out of ~4.5k** (≈0.4%) — consistent with transient timeouts, not a block (no status-code errors surfaced).

## What the tools could NOT tell us
- Full nikto sweep did not finish (240 s cap) — CGI/dir-brute coverage incomplete.
- No medium/high-severity CVE matched by info/misconfig templates; **injection classes (SQLi, XSS, file-inclusion) were deliberately NOT tested** — they need intrusive/fuzzing templates which were out of scope for this round.
- 443/8000/8080 are `filtered` — no TLS service reachable to fingerprint.
- No directory listing (403 on dirs), so directory contents not enumerable via that vector.
- `Templatize.asp` returns 500 but the error body/SQL detail was not expanded this round.
- Host-header semantics mean any later scan **must send a correct Host** or it will hit the wrong (default IIS) site.
