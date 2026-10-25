"""Run every test suite and compare each result with docs/refactor/BASELINE.md.

    python tools/run_tests.py                     # Python, Node and browser checks (everything)
    python tools/run_tests.py --no-browser        # skip the URL check and the Playwright smoke test
    python tools/run_tests.py --feature fishing   # one feature's tests plus the shared guards

Known failures listed in BASELINE.md are expected. The run passes only when every result equals
its baseline entry (tests not listed there must pass) and the browser checks pass. A test that
starts passing is also reported: that is a behaviour change too.

A feature's tests are the test files named in the Tests row of visionpad/features/<name>/README.md
plus any tests/python/<name>/ and tests/js/<name>/ folder. The registry, root-alias and
save-compatibility tests run with every feature. Browser checks run with --feature only when
--browser is given.
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
BASELINE = ROOT / "docs/refactor/BASELINE.md"
FEATURES = ROOT / "visionpad/features"
GUARDS = ("tests/python/core/test_registry.py", "tests/python/core/test_root_aliases.py",
          "tests/python/saves/test_save_compat.py")
BROWSER = ("tests/browser/url_check.py", "tests/browser/smoke_test.py")
TEST_FILE = re.compile(r"`(tests/[\w/]+\.(?:py|cjs|mjs))`")


def baseline():
    """{key: 'ok' | 'FAIL' | 'ERROR'} from the BASELINE.md tables (Python: Class.test, Node: file + name)."""
    results = {}
    for line in BASELINE.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and cells[2].startswith("test_") and cells[3] in ("ok", "FAIL", "ERROR"):
            results[f"python {cells[1]}.{cells[2]}"] = cells[3]
        elif len(cells) >= 3 and re.fullmatch(r"test_\w+\.(cjs|mjs)", cells[0]) and cells[2] in ("ok", "FAIL"):
            results[f"node {cells[0]} {cells[1].removeprefix('↳ ')}"] = cells[2]
    return results


def feature_tests(name):
    readme = FEATURES / name / "README.md"
    if not readme.is_file():
        raise SystemExit(f"Unknown feature {name!r}: {readme.relative_to(ROOT)} does not exist.")
    row = next((line for line in readme.read_text(encoding="utf-8").splitlines() if line.startswith("| Tests |")), "")
    files = set(TEST_FILE.findall(row))
    for folder in (ROOT / "tests/python" / name, ROOT / "tests/js" / name):
        files.update(path.relative_to(ROOT).as_posix() for path in folder.rglob("test_*.*") if folder.is_dir())
    return sorted(files)


def run_python(files):
    print("== Python", flush=True)
    sys.path.insert(0, str(ROOT))
    loader = unittest.TestLoader()
    if files is None:
        suite = loader.discover(str(ROOT / "tests/python"), top_level_dir=str(ROOT))
    else:
        suite = loader.loadTestsFromNames([path.removesuffix(".py").replace("/", ".") for path in files])
    # Collected before the run: a suite drops its tests as they finish.
    outcomes = {test.id(): "ok" for test in iter_tests(suite)}
    result = unittest.TextTestRunner(verbosity=2, stream=sys.stdout).run(suite)
    for test, _ in result.failures:
        outcomes[test.id()] = "FAIL"
    for test, _ in result.errors:
        outcomes[test.id()] = "ERROR"
    return {f"python {'.'.join(key.split('.')[-2:])}": value for key, value in outcomes.items()}


def iter_tests(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from iter_tests(item)
        else:
            yield item


def run_node(files):
    print("== Node", flush=True)
    node = shutil.which("node")
    if not node:
        print("Node.js is not installed; Node tests were not run.")
        return None
    if files is None:
        files = sorted(path.relative_to(ROOT).as_posix() for path in (ROOT / "tests/js").rglob("test_*.*")
                       if path.suffix in (".cjs", ".mjs"))
    outcomes = {}
    # One run per file: BASELINE keys Node results by file name, which TAP does not repeat per test.
    # Explicit file names also avoid node --test globs, which need Node 21+.
    for path in files:
        file = Path(path).name
        run = subprocess.run([node, "--test", "--test-reporter=tap", path], cwd=ROOT,
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
        found = 0
        for line in run.stdout.splitlines():
            match = re.match(r"\s*(not ok|ok) \d+ - (.*?)\s*$", line)
            if not match:
                continue
            found += 1
            name = match.group(2).replace("\\\\", "/").replace("\\", "/")
            # A file that fails to load is reported under its path; BASELINE names it by file.
            name = file if name.endswith("/" + file) or name == file else name
            status = "ok" if match.group(1) == "ok" else "FAIL"
            print(f"{status:5} {file}: {name}")
            outcomes[f"node {file} {name}"] = status
        if run.returncode and not found:
            print(run.stdout[-4000:], run.stderr[-4000:])
            outcomes[f"node {file} {file}"] = "FAIL"
    return outcomes


def run_browser():
    print("== Browser", flush=True)
    outcomes = {}
    for script in BROWSER:
        if script.endswith("smoke_test.py") and importlib.util.find_spec("playwright") is None:
            print("playwright is not installed (requirements-dev.txt); smoke test not run.")
            outcomes[f"browser {script}"] = "not run"
            continue
        code = subprocess.run([sys.executable, script], cwd=ROOT).returncode
        outcomes[f"browser {script}"] = "ok" if code == 0 else "FAIL"
    return outcomes


def compare(results, expected, full_run):
    problems = []
    for key, got in sorted(results.items()):
        if key.startswith("browser "):
            if got != "ok":
                problems.append(f"{key}: {got}")
            continue
        want = expected.get(key, "ok")
        if got != want:
            problems.append(f"{key}: {got}, baseline {want}" + ("" if key in expected else " (not in baseline)"))
    if full_run:
        problems += [f"{key}: not run, baseline {want}" for key, want in sorted(expected.items()) if key not in results]
    return problems


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
    results = run_python(python_files)
    node = run_node(node_files)
    if node is None:
        results["node (Node.js missing)"] = "FAIL"
    else:
        results.update(node)
    if not args.no_browser and (not args.feature or args.browser):
        results.update(run_browser())

    problems = compare(results, baseline(), full_run=not args.feature)
    counts = {status: sum(value == status for value in results.values()) for status in ("ok", "FAIL", "ERROR")}
    print(f"\n{len(results)} results: {counts['ok']} ok, {counts['FAIL']} FAIL, {counts['ERROR']} ERROR")
    if problems:
        print("Differences from docs/refactor/BASELINE.md:", *problems, sep="\n  ")
        return 1
    print("All results match docs/refactor/BASELINE.md (known failures included).")
    return 0

if __name__ == "__main__":
    sys.exit(main())
