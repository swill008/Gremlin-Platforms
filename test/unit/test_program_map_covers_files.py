# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Change control: the program map stays whole. Every program file is
named in the "## 2. Files" section of at least one page in
claude/program-map/, so each file has a page (and a spec) that owns it.
See the change control section of .claude/CLAUDE.md.

A file counts as named when a page's Files section has its repo path, or
a backticked name that ends the path (`ActionNode.qml`, `ui/util.py`), or
a backticked pattern that matches it (`qml/rig_*.js`). A folder named
there (`qml/help/`, `action_plugins/play_sound/`, `dill/`) covers the
files in it. The "Leftovers" list on page 09 names files that have no
page yet, so it does not count. Pure file reading; no Qt."""

from __future__ import annotations

import ast
import fnmatch
import re
from collections import defaultdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_MAP = _ROOT / "claude" / "program-map"
_FILES_HEADING = re.compile(r"^## 2\. Files\b.*$", re.MULTILINE)
_NEXT_HEADING = re.compile(r"^## ", re.MULTILINE)
_LEFTOVERS = re.compile(r"^\*\*Leftovers\b.*?(?=^\*\*|\Z)", re.MULTILINE | re.DOTALL)
_TICKED = re.compile(r"`([^`\n]+)`")
# A backticked name that looks like a path: a file with an extension or a
# folder ending in "/" (so `*` or `osc/connection/*` cover nothing).
_PATHLIKE = re.compile(r"^[\w.*-]+(/[\w.*-]+)*(\.\w+|/)$")


def _files_sections() -> str:
    parts = []
    for page in sorted(_MAP.glob("*.md")):
        text = page.read_text(encoding="utf-8")
        found = _FILES_HEADING.search(text)
        if not found:
            continue
        rest = text[found.end():]
        end = _NEXT_HEADING.search(rest)
        parts.append(_LEFTOVERS.sub("", rest[:end.start()] if end else rest))
    return "\n".join(parts)


def _is_trivial_init(path: Path) -> bool:
    """An __init__.py with nothing but a docstring and imports."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return False
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            continue
        return False
    return True


def _rel(path: Path) -> str:
    return path.relative_to(_ROOT).as_posix()


def _program_units() -> list[tuple[str, list[str]]]:
    """(unit, names that cover it). A unit is a file or a folder."""
    units: list[tuple[str, list[str]]] = []

    def file_unit(path: Path, *folders: str) -> None:
        units.append((_rel(path), [_rel(path), *folders]))

    qml = _ROOT / "qml"
    for path in sorted([*qml.glob("*.qml"), *qml.glob("*.js")]):
        file_unit(path)
    for path in sorted((qml / "help").glob("*.js")):
        file_unit(path, "qml/help/")
    # The Input Tester's window (D-02-INPUT-TESTER).
    for path in sorted((qml / "tester").glob("*.qml")):
        file_unit(path, "qml/tester/")

    for path in sorted((_ROOT / "gremlin").rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        if path.name == "__init__.py" and _is_trivial_init(path):
            continue
        file_unit(path)

    plugins = _ROOT / "action_plugins"
    for path in sorted(plugins.glob("*.py")):
        if path.name == "__init__.py" and _is_trivial_init(path):
            continue
        file_unit(path)
    for folder in sorted(p for p in plugins.iterdir() if p.is_dir()):
        if folder.name == "__pycache__":
            continue
        name = _rel(folder) + "/"
        units.append((name, [name, name + "__init__.py"]))

    units.append(("joystick_gremlin.py", ["joystick_gremlin.py"]))
    units.append(("input_tester.py", ["input_tester.py"]))
    units.append(("dill/", ["dill/"]))
    units.append(("vigem/", ["vigem/"]))
    return units


def _covered(names: list[str], text: str, ticked: list[str]) -> bool:
    for name in names:
        if name in text:
            return True
        is_folder = name.endswith("/")
        parts = name.rstrip("/").split("/")
        for token in ticked:
            if token.endswith("/") != is_folder:
                continue
            want = token.rstrip("/").split("/")
            if len(want) > len(parts):
                continue
            tail = parts[-len(want):]
            if all(fnmatch.fnmatchcase(p, w) for p, w in zip(tail, want)):
                return True
    return False


def test_every_program_file_is_on_a_map_page() -> None:
    text = _files_sections()
    ticked = [t for t in (m.strip() for m in _TICKED.findall(text))
              if _PATHLIKE.match(t)]
    missing: dict[str, list[str]] = defaultdict(list)
    for unit, names in _program_units():
        if not _covered(names, text, ticked):
            folder = unit.rstrip("/").rpartition("/")[0] or "(top level)"
            missing[folder].append(unit)
    if missing:
        count = sum(len(v) for v in missing.values())
        lines = [
            f"{count} program files are not named in the '## 2. Files' "
            "section of any claude/program-map page. Add each to the page "
            "that owns it:"
        ]
        for folder in sorted(missing):
            lines.append(f"\n{folder}/ ({len(missing[folder])})")
            lines.extend(f"  - {unit}" for unit in missing[folder])
        raise AssertionError("\n".join(lines))
