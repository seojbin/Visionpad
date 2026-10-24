"""Every URL the game page and the companion window request must answer 200.

    python tests/browser/url_check.py --record   # write tests/browser/recorded-urls.txt from the web tree
    python tests/browser/url_check.py            # start a server, check recorded + currently referenced URLs

URLs come from a static scan of web/ (HTML, JS, JSON, CSS): quoted asset paths, /static/ and /api/
references, the GameAudio sound list and the texture paths in the companion's asset registry.
The Dot Pad SDK (gitignored, downloaded by hand) is reported but not required.
"""
import argparse
import json
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from posixpath import dirname, join, normpath

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
RECORDED = Path(__file__).with_name("recorded-urls.txt")
OPTIONAL = re.compile(r"/vendor/DotPadSDK-")
QUOTED = re.compile(r"""['"`]([^'"`\s<>]*?\.(?:json|js|mjs|css|png|mp3|html)(?:\?[^'"`\s<>]*)?)['"`]""")
API_GET = ("/api/state", "/api/speech/voices", "/openapi.json")


def served_url(path):
    """URL of a file under web/ (game.html is also served at '/')."""
    return "/static/" + path.relative_to(WEB).as_posix()


def resolve(base_dir, ref):
    ref = ref.split("#")[0]
    if ref.startswith(("http://", "https://", "data:")) or "${" in ref:
        return None
    if ref.startswith("/"):
        return ref
    path, _, query = ref.partition("?")
    url = normpath(join(base_dir, path))
    return url + ("?" + query if query else "")


def scan():
    urls = {"/"} | set(API_GET)
    for path in sorted(WEB.rglob("*")):
        if path.suffix not in (".html", ".js", ".mjs", ".json", ".css") or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        base = "/static" if path == WEB / "game.html" else dirname(served_url(path))
        for ref in QUOTED.findall(text):
            url = resolve(base, ref)
            if url and (url.startswith("/static/") or url == "/"):
                urls.add(url)
        # GameAudio builds shared sound URLs from a name list and a template (feature sounds are quoted).
        for names, template in re.findall(r"\[((?:'[\w-]+',?\s*)+)\]\.map\(n => \[n, (?:\w+\[n\] \|\| )?`([^`]+)`\]\)", text):
            for name in re.findall(r"'([\w-]+)'", names):
                urls.add(template.replace("${n}", name))
        if path.name == "visual-assets.json":
            for texture in json.loads(text).get("textures", {}).values():
                urls.add(resolve(dirname(served_url(path)), texture))
    return sorted(urls)


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def fetch(base, url):
    try:
        with urllib.request.urlopen(base + url, timeout=10) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


def check(urls):
    port = free_port()
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "visionpad.app.main:app", "--host", "127.0.0.1",
                               "--port", str(port), "--log-level", "warning"], cwd=ROOT)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(150):
            try:
                urllib.request.urlopen(base + "/openapi.json", timeout=1)
                break
            except OSError:
                time.sleep(0.2)
        failures, optional = [], []
        for url in urls:
            status = fetch(base, url)
            if status != 200:
                (optional if OPTIONAL.search(url) else failures).append((url, status))
        return failures, optional
    finally:
        server.terminate()
        server.wait(10)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--record", action="store_true", help="Record the current URL list as the reference")
    args = parser.parse_args()
    current = scan()
    if args.record:
        RECORDED.write_text("\n".join(current) + "\n", encoding="utf-8")
        print(f"Recorded {len(current)} URLs in {RECORDED.relative_to(ROOT)}")
        return 0
    recorded = RECORDED.read_text(encoding="utf-8").split() if RECORDED.exists() else []
    urls = sorted(set(recorded) | set(current))
    failures, optional = check(urls)
    for url, status in optional:
        print(f"optional  {status}  {url}  (Dot Pad SDK not downloaded)")
    for url, status in failures:
        print(f"FAIL      {status}  {url}")
    print(f"{len(urls)} URLs checked ({len(recorded)} recorded, {len(set(current) - set(recorded))} new): "
          f"{len(failures)} failed, {len(optional)} optional missing")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
