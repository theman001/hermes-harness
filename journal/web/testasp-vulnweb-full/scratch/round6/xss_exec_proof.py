"""Round 6 — 저장형 XSS 실제 실행 증거 수집 (CDP).

showthread.asp?id=0 에 저장된 <img src=x onerror=alert(1)> 가 브라우저에서 **실제로 실행**되는지
Page.javascriptDialogOpening 이벤트로 확인하고, 같은 페이지에서 document.cookie 가 JS 로
읽히는지(= 세션 쿠키에 HttpOnly 없음 → 세션 탈취 가능)도 함께 측정한다.

전제: 이 환경의 Chrome for Testing 152 는 HTTPS-Upgrade 기능 때문에 평문 HTTP 타겟을
ERR_BLOCKED_BY_CLIENT 로 막으므로 --disable-features 로 비활성화해야 한다(scratch/cdp_shot.py 주석 참조).

사용: .venv/bin/python xss_exec_proof.py <outdir> <url>
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

import websocket

CHROME = "/home/taeuk/.cache/ms-playwright/chromium-1237/chrome-linux64/chrome"
PORT = 9334
FLAGS = [
    "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
    "--disable-features=HttpsUpgrades,HttpsFirstModeV2,HttpsFirstBalancedMode",
    "--window-size=1280,900", "--hide-scrollbars", "--no-first-run",
    "--disable-background-networking", "--disable-sync", "--no-default-browser-check",
    "--remote-allow-origins=*",
]


def wait_devtools(timeout=30.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version", timeout=2) as r:
                return json.load(r)
        except Exception:
            time.sleep(0.4)
    raise RuntimeError("devtools endpoint never came up")


def new_tab():
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/json/new?about:blank", method="PUT")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


class Page:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=30)
        self._id = 0
        self.events = []

    def send(self, method, **params):
        self._id += 1
        self.ws.send(json.dumps({"id": self._id, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self._id:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})
            self.events.append(msg)

    def pump(self, seconds):
        """이벤트 루프를 seconds 동안 돌리며 이벤트를 수집."""
        self.ws.settimeout(0.5)
        end = time.time() + seconds
        try:
            while time.time() < end:
                try:
                    self.events.append(json.loads(self.ws.recv()))
                except Exception:
                    pass
        finally:
            self.ws.settimeout(30)


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print(__doc__)
        return 2
    outdir, url = args[0], args[1]
    os.makedirs(outdir, exist_ok=True)

    profile = tempfile.mkdtemp(prefix="cdp-xss-")
    proc = subprocess.Popen([CHROME, *FLAGS, f"--remote-debugging-port={PORT}",
                             f"--user-data-dir={profile}", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    result = {}
    try:
        ver = wait_devtools()
        result["browser"] = ver.get("Browser")
        tab = new_tab()
        p = Page(tab["webSocketDebuggerUrl"])
        p.send("Page.enable")
        p.send("Runtime.enable")
        p.send("Network.enable")
        p.send("Page.navigate", url=url)
        p.pump(6.0)  # 로드 + onerror 발화 대기

        dialogs = [e["params"] for e in p.events
                   if e.get("method") == "Page.javascriptDialogOpening"]
        result["dialogs"] = dialogs
        result["dialog_count"] = len(dialogs)

        # 다이얼로그가 열려 있으면 닫아준다(안 닫으면 이후 evaluate 가 막힌다)
        for _ in dialogs:
            try:
                p.send("Page.handleJavaScriptDialog", accept=True)
            except Exception:
                pass

        result["url_after"] = p.send("Runtime.evaluate", expression="location.href",
                                     returnByValue=True)["result"].get("value")
        result["cookie_via_js"] = p.send(
            "Runtime.evaluate", expression="document.cookie", returnByValue=True
        )["result"].get("value")
        result["cookie_readable"] = bool(result["cookie_via_js"])
        result["img_present"] = p.send(
            "Runtime.evaluate",
            expression="!!document.querySelector(\"img[onerror]\")",
            returnByValue=True,
        )["result"].get("value")
        result["img_onerror_attr"] = p.send(
            "Runtime.evaluate",
            expression="(document.querySelector('img[onerror]')||{}).getAttribute && "
                       "document.querySelector('img[onerror]').getAttribute('onerror')",
            returnByValue=True,
        )["result"].get("value")

        shot = p.send("Page.captureScreenshot", format="png", captureBeyondViewport=True)
        png = os.path.join(outdir, "xss_proof.png")
        with open(png, "wb") as f:
            f.write(base64.b64decode(shot["data"]))
        result["png"] = png
        result["png_bytes"] = os.path.getsize(png)

        # 콘솔/예외 로그도 남긴다
        result["console"] = [e["params"] for e in p.events
                             if e.get("method") in ("Runtime.consoleAPICalled",
                                                    "Runtime.exceptionThrown")]
        p.ws.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(profile, ignore_errors=True)

    print(json.dumps(result, ensure_ascii=False, indent=2)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
