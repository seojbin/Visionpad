"""Run every test suite: Python, Node and the browser checks.

    python tools/run_tests.py                     # everything
    python tools/run_tests.py --no-browser        # skip the URL check and the Playwright smoke test
    python tools/run_tests.py --feature fishing   # one feature's tests plus the shared guards

Known failures are marked in the tests themselves (unittest.expectedFailure, node:test todo) with
their reason, and are listed at the end. The run passes when nothing else fails and no known
failure starts passing (that is a behaviour change too: remove its marker).

Tests live in engine/tests/ (shared) and game/<name>/tests/ (one feature). A feature's tests are its
tests folder plus the shared test files named in the Tests row of its README.
The registry and save-compatibility tests run with every feature. Browser checks run with
--feature only when --browser is given.
"""
import argparse
import importlib.util
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ROOT / "game"
GUARDS = ("engine/tests/python/core/test_registry.py", "engine/tests/python/saves/test_save_compat.py")
BROWSER = ("engine/tests/browser/url_check.py", "engine/tests/browser/smoke_test.py")
TEST_FILE = re.compile(r"`((?:engine|game)/[\w/]*tests/[\w/]+\.(?:py|cjs|mjs))`")
TAP = re.compile(r"\s*(not ok|ok) \d+ - (.*?)(?: # (TODO|SKIP)\b ?(.*))?\s*$")


def feature_tests(name):
    readme = FEATURES / name / "README.md"
    if not readme.is_file():
        raise SystemExit(f"Unknown feature {name!r}: {readme.relative_to(ROOT)} does not exist.")
    row = next((line for line in readme.read_text(encoding="utf-8").splitlines() if line.startswith("| Tests |")), "")
    files = set(TEST_FILE.findall(row))
    files.update(test_files(FEATURES / name / "tests"))
    return sorted(files)


def test_files(*folders):
    """Every test_*.py / test_*.cjs / test_*.mjs under the folders, relative to the repository root."""
    return sorted(path.relative_to(ROOT).as_posix() for folder in folders if folder.is_dir()
                  for path in folder.rglob("test_*.*") if path.suffix in (".py", ".cjs", ".mjs"))


def all_test_files():
    return test_files(ROOT / "engine/tests", *sorted(FEATURES.glob("*/tests")))


def run_python(files, report):
    print("== Python", flush=True)
    sys.path.insert(0, str(ROOT))
    loader = unittest.TestLoader()
    if files is None:
        files = [path for path in all_test_files() if path.endswith(".py")]
    suite = loader.loadTestsFromNames([path.removesuffix(".py").replace("/", ".") for path in files])
    result = unittest.TextTestRunner(verbosity=2, stream=sys.stdout).run(suite)
    report["ok"] += result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped) \
        - len(result.expectedFailures) - len(result.unexpectedSuccesses)
    report["expected"] += [f"python {test.id()}" for test, _ in result.expectedFailures]
    report["problems"] += [f"python FAIL {test.id()}" for test, _ in result.failures]
    report["problems"] += [f"python ERROR {test.id()}" for test, _ in result.errors]
    report["problems"] += [f"python unexpected success (remove its known-failure marker) {test.id()}"
                           for test in result.unexpectedSuccesses]
    report["skipped"] += [f"python {test.id()}: {why}" for test, why in result.skipped]


def run_node(files, report):
    print("== Node", flush=True)
    node = shutil.which("node")
    if not node:
        report["problems"].append("node: Node.js is not installed; Node tests were not run")
        return
    if files is None:
        files = [path for path in all_test_files() if path.endswith((".cjs", ".mjs"))]
    if not files:
        return
    # Explicit file names instead of a glob: node --test globs need Node 21+.
    run = subprocess.run([node, "--test", "--test-reporter=tap", *files], cwd=ROOT,
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    found = failed = 0
    for line in run.stdout.splitlines():
        match = TAP.match(line)
        if not match:
            continue
        found += 1
        status, name, directive, reason = match.groups()
        name = name.replace("\\\\", "/").replace("\\", "/").rsplit("/", 1)[-1] if name.startswith("tests") else name
        print(f"{status if not directive else directive.lower():6} {name}" + (f"  ({reason})" if reason else ""))
        if directive == "TODO":
            if status == "not ok":
                report["expected"].append(f"node {name}: {reason}")
            else:
                report["problems"].append(f"node unexpected success (remove its todo marker) {name}")
        elif directive == "SKIP":
            report["skipped"].append(f"node {name}: {reason}")
        elif status == "ok":
            report["ok"] += 1
        else:
            failed += 1
            report["problems"].append(f"node FAIL {name}")
    if (run.returncode and not failed) or not found:
        print(run.stdout[-4000:], run.stderr[-4000:])
        report["problems"].append(f"node exited with {run.returncode}")


def run_browser(report):
    print("== Browser", flush=True)
    for script in BROWSER:
        if script.endswith("smoke_test.py") and importlib.util.find_spec("playwright") is None:
            report["problems"].append(f"{script}: playwright is not installed (requirements-dev.txt); not run")
            continue
        if subprocess.run([sys.executable, script], cwd=ROOT).returncode:
            report["problems"].append(f"{script}: FAIL")
        else:
            report["ok"] += 1


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--feature", action="append", help="run one feature's tests (repeatable)")
    browser = parser.add_mutually_exclusive_group()
    browser.add_argument("--no-browser", action="store_true", help="skip the URL check and smoke test")
    browser.add_argument("--browser", action="store_true", help="with --feature: also run the browser checks")
    args = parser.parse_args()

    python_files = node_files = None
    if args.feature:
        own = {name: feature_tests(name) for name in args.feature}
        for name in [name for name, tests in own.items() if not tests]:
            print(f"{name}: its README lists no test files; only the shared guards run. Run the full suite too.")
        files = sorted(set(GUARDS).union(*own.values()))
        python_files = [path for path in files if path.endswith(".py")]
        node_files = [path for path in files if path.endswith((".cjs", ".mjs"))]
        print("Test files:", *files, sep="\n  ")

    report = {"ok": 0, "expected": [], "skipped": [], "problems": []}
    run_python(python_files, report)
    run_node(node_files, report)
    if not args.no_browser and (not args.feature or args.browser):
        run_browser(report)

    print(f"\n{report['ok']} passed, {len(report['expected'])} known failures, {len(report['skipped'])} skipped, "
          f"{len(report['problems'])} problems")
    for title, key in (("Known failures (marked in the tests):", "expected"), ("Skipped:", "skipped"),
                       ("PROBLEMS:", "problems")):
        if report[key]:
            print(title, *report[key], sep="\n  ")
    if report["problems"]:
        return 1
    print("All green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
