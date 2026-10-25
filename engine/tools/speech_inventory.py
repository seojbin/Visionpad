"""Collect speech expressions from game code without running game actions."""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def game_code():
    """The Python files the running game uses: engine/ without its tests, tools, launcher and tracking, and game/ without tests."""
    skip = {"tests", "tools", "launcher", "tracking"}
    for path in [*ROOT.glob("engine/**/*.py"), *ROOT.glob("game/**/*.py")]:
        if not skip & set(path.relative_to(ROOT).parts[1:-1]):
            yield path


def collect():
    entries = []
    for path in sorted(game_code()):
        if path.relative_to(ROOT).as_posix() == "engine/services/speech.py":
            continue
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        nodes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.keyword) and node.arg == "tts":
                nodes.append(node.value)
            elif isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id in ("text", "narration") for target in node.targets):
                nodes.append(node.value)
            elif isinstance(node, ast.Dict):
                nodes.extend(value for key, value in zip(node.keys, node.values) if isinstance(key, ast.Constant) and key.value == "tts")
            elif isinstance(node, ast.FunctionDef) and node.name == "get_object_tts":
                nodes.extend(item.value for item in ast.walk(node) if isinstance(item, ast.Return) and item.value is not None)
        seen = set()
        for node in nodes:
            if not isinstance(node, (ast.Constant, ast.JoinedStr)):
                continue
            if isinstance(node, ast.Constant) and not isinstance(node.value, str):
                continue
            key = (node.lineno, node.col_offset)
            if key in seen:
                continue
            seen.add(key)
            entries.append({"source": path.relative_to(ROOT).as_posix(), "line": node.lineno,
                            "kind": "fixed" if isinstance(node, ast.Constant) else "dynamic",
                            "text": node.value if isinstance(node, ast.Constant) else ast.get_source_segment(source, node)})
    return sorted(entries, key=lambda entry: (entry["source"], entry["line"]))


if __name__ == "__main__":
    entries = collect()
    target = ROOT / "output" / "audio" / "speech-catalog.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"scope": "Speech literals and templates; variable-only expressions and browser-authored messages are not expanded.", "entries": entries}, indent=2), encoding="utf-8")
    print(f"Collected {len(entries)} source-backed expressions into {target.relative_to(ROOT)}")
