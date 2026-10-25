"""Browser smoke test: game page and companion window load cleanly and travel works everywhere.

Dev-only: pip install -r engine/requirements-dev.txt && python -m playwright install chromium
Run:      python engine/tests/browser/smoke_test.py

Fails on any console error, page error, failed request or HTTP status >= 400 in either window.
Allowed: the hand-downloaded Dot Pad SDK may be missing, and speech requests that the page itself
aborts when a newer line replaces them (GameSpeech cancellation, net::ERR_ABORTED on /api/speech). Travels to every location through the F1 map
using the page's own "Objects nearby" buttons, which send the same pointer input as the pad.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from url_check import OPTIONAL, WEB, free_port, resolve, ROOT  # noqa: E402

import subprocess  # noqa: E402
import time  # noqa: E402
import urllib.request  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402

def cancelled_speech(request):
    return request.url.split("?")[0].endswith(("/api/speech", "/api/speech/cancel")) and "ERR_ABORTED" in (request.failure or "")


# Every texture sheet in the companion's asset registry must actually load (they may live in feature folders).
TEXTURES = {resolve("/static/spectator", path) for path in
            json.loads((WEB / "spectator/visual-assets.json").read_text(encoding="utf-8"))["textures"].values()}
LOCATIONS = [("farm", "Farm"), ("town", "Village"), ("mine", "Mine"), ("fishing", "Fishing lake"), ("home", "Home")]


def main():
    port = free_port()
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "engine.server.main:app", "--host", "127.0.0.1",
                               "--port", str(port), "--log-level", "warning"], cwd=ROOT)
    base = f"http://127.0.0.1:{port}"
    problems = []
    loaded = set()
    try:
        for _ in range(150):
            try:
                urllib.request.urlopen(base + "/openapi.json", timeout=1)
                break
            except OSError:
                time.sleep(0.2)
        urllib.request.urlopen(urllib.request.Request(base + "/api/reset", data=b"{}", method="POST",
                                                      headers={"Content-Type": "application/json"}))
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context()

            def watch(page, name):
                page.on("console", lambda msg: msg.type == "error" and not OPTIONAL.search(msg.location.get("url", ""))
                        and problems.append(f"{name} console: {msg.text} ({msg.location.get('url')})"))
                page.on("pageerror", lambda err: problems.append(f"{name} page error: {err}"))
                page.on("requestfailed", lambda req: None if OPTIONAL.search(req.url) or cancelled_speech(req)
                        else problems.append(f"{name} request failed: {req.url} ({req.failure})"))
                page.on("response", lambda res: None if res.status < 400 or OPTIONAL.search(res.url)
                        else problems.append(f"{name} HTTP {res.status}: {res.url}"))
                page.on("response", lambda res: res.status == 200 and loaded.add(res.url.removeprefix(base).split("?")[0]))

            page = context.new_page()
            watch(page, "game")
            page.goto(base + "/")
            page.wait_for_selector("#show-visual:not([disabled])", timeout=20000)
            with context.expect_page() as popup_info:
                page.click("#show-visual")
            popup = popup_info.value
            watch(popup, "companion")
            popup.wait_for_load_state("load")
            popup.wait_for_timeout(1500)
            if not popup.query_selector("canvas"):
                problems.append("companion: no canvas rendered")
            for texture in sorted(TEXTURES - loaded):
                problems.append(f"companion texture not loaded: {texture}")

            def state():
                return page.evaluate("fetch('/api/state').then(r => r.json()).then(s => s.page)")

            for location, label in LOCATIONS:
                page.keyboard.press("F1")
                page.wait_for_function("document.getElementById('page-text').textContent === 'Map'", timeout=10000)
                button = page.locator("#object-list button", has_text=re.compile(rf"^{re.escape(label)}")).first
                button.click()
                for _ in range(50):
                    if state() == location:
                        break
                    page.wait_for_timeout(100)
                else:
                    problems.append(f"travel to {location} did not arrive (page {state()})")
                page.wait_for_timeout(300)
                print(f"arrived: {location}")
            popup.wait_for_timeout(500)
            browser.close()
    finally:
        server.terminate()
        server.wait(10)
    for problem in problems:
        print("PROBLEM", problem)
    print("smoke test:", "FAILED" if problems else "passed")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
