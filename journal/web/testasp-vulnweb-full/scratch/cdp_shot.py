"""CDP 직접 구동 스크린샷/렌더 드라이버 (환경 워크어라운드).

배경(2026-09-23 실측): 이 환경의 Google Chrome for Testing 152.0.7977.8 은
HTTPS-Upgrade 계열 기능 때문에 **외부 평문 HTTP 사이트를 ERR_BLOCKED_BY_CLIENT 로
차단**한다(HTTPS 는 정상, 127.0.0.1 HTTP 도 정상). Chrome 을
`--disable-features=HttpsUpgrades,HttpsFirstModeV2,HttpsFirstBalancedMode` 로 띄우면
정상 로드된다. 다만 이 Chrome 빌드에서는 `--screenshot=` 플래그가 아무 파일도 만들지
않으므로(구식 플래그 제거), CDP `Page.captureScreenshot` 를 직접 쓴다.
browser_exec(browser-use 하네스)는 chrome 플래그를 넘길 방법이 없어 이 경로가 필요하다.

사용:
  python3 cdp_shot.py <outdir> <url> [<url> ...]
  python3 cdp_shot.py <outdir> --eval "<js>" <url>     # DOM 추출도 함께
"""
from __future__ import annotations

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
PORT = 9333
FLAGS = [
    "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
    "--disable-features=HttpsUpgrades,HttpsFirstModeV2,HttpsFirstBalancedMode",
    "--window-size=1280,900", "--hide-scrollbars", "--no-first-run",
    "--disable-background-networking", "--disable-sync", "--no-default-browser-check",
    "--remote-allow-origins=*",
]


def _launch(profile: str) -> subprocess.Popen:
    return subprocess.Popen(
        [CHROME, *FLAGS, f"--remote-debugging-port={PORT}", f"--user-data-dir={profile}",
         "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def _wait_devtools(timeout: float = 30.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version", timeout=2) as r:
                return json.load(r)
        except Exception:
            time.sleep(0.4)
    raise RuntimeError("devtools endpoint never came up")


def _new_tab(url: str = "about:blank") -> dict:
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/json/new?{url}", method="PUT")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


class Page:
    def __init__(self, ws_url: str):
        self.ws = websocket.create_connection(ws_url, timeout=30)
        self._id = 0

    def send(self, method: str, **params):
        self._id += 1
        self.ws.send(json.dumps({"id": self._id, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self._id:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    def wait_load(self, timeout: float = 25.0) -> bool:
        """Page.loadEventFired 까지 대기. 이미 지나갔으면 짧게 반환."""
        deadline = time.time() + timeout
        self.ws.settimeout(1.0)
        try:
            while time.time() < deadline:
                try:
                    msg = json.loads(self.ws.recv())
                except Exception:
                    continue
                if msg.get("method") == "Page.loadEventFired":
                    return True
        finally:
            self.ws.settimeout(30)
        return False


def render(ws_url: str, url: str, png_path: str, eval_js: str | None = None) -> dict:
    p = Page(ws_url)
    out: dict = {}
    p.send("Page.enable")
    nav = p.send("Page.navigate", url=url)
    out["nav"] = nav
    time.sleep(1.5)
    out["loaded"] = p.wait_load()
    time.sleep(1.5)  # 렌더 안정화
    if eval_js:
        r = p.send("Runtime.evaluate", expression=eval_js, returnByValue=True)
        out["eval"] = r.get("result", {}).get("value")
    shot = p.send("Page.captureScreenshot", format="png", captureBeyondViewport=True)
    with open(png_path, "wb") as f:
        import base64
        f.write(base64.b64decode(shot["data"]))
    out["png"] = png_path
    out["bytes"] = os.path.getsize(png_path)
    try:
        out["url_after"] = p.send("Runtime.evaluate", expression="location.href",
                                  returnByValue=True)["result"]["value"]
        out["title"] = p.send("Runtime.evaluate", expression="document.title",
                              returnByValue=True)["result"]["value"]
    except Exception:
        pass
    p.ws.close()
    return out


def main() -> int:
    args = sys.argv[1:]
    if len(args) < 2:
        print(__doc__)
        return 2
    outdir = args[0]
    eval_js = None
    if "--eval" in args:
        i = args.index("--eval")
        eval_js = args[i + 1]
        args = args[:i] + args[i + 2:]
    urls = args[1:]
    os.makedirs(outdir, exist_ok=True)

    profile = tempfile.mkdtemp(prefix="cdp-shot-")
    proc = _launch(profile)
    try:
        ver = _wait_devtools()
        print("browser:", ver.get("Browser"), "| protocol:", ver.get("Protocol-Version"))
        for u in urls:
            tab = _new_tab("about:blank")
            name = u.rstrip("/").split("/")[-1].split("?")[0] or "index"
            name = name.replace(".asp", "") or "index"
            png = os.path.join(outdir, f"shot_{name}.png")
            try:
                info = render(tab["webSocketDebuggerUrl"], u, png, eval_js)
                print(json.dumps({"url": u, **info}, ensure_ascii=False)[:400])
            except Exception as e:
                print(f"{u} -> ERROR {type(e).__name__}: {e}")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(profile, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
