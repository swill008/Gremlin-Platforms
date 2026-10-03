# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""On-screen text keeps to claude/glossary.md: words it replaced do not come
back. Checks every string a user can read in the QML and JavaScript, and the
Options descriptions registered in Python."""

from __future__ import annotations

import ast
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]

# (pattern, what to use instead). Case-sensitive unless (?i).
_REPLACED = [
    (r"\bUnmapped\b", "No actions"),
    (r"\bNot bound\b", "No actions"),
    (r"(?i)\btoggle active\b", "Run / Stop"),
    (r"\bNot Running\b", "Stopped"),
    (r"\bExecuting mode\b|\bConfiguring mode\b", "Mode"),
    (r"\bDisplay Editor\b|\bShow Editor\b|\bView Settings\b", "Appearance"),
    (r"(?i)\bconfigure (input|output) module\b", "Module Setup"),
    # Not "Hardware Hide device…" (the HidHide window's own settings).
    (r"\bHidden devices\b|(?<!Hardware )\bHide device\b", "Hide Card / Hidden Cards"),
    (r"(?i)\bcolours?\b", "color (US spelling)"),
    (r"HiDHide", "HidHide"),
    (r"(?i)please choose a file", "a title saying what the picker does"),
    (r"(?i)a fatal error occurred", "Error"),
    (r"(?i)clear module settings", "Reset Card Layout"),
    (r"(?i)\bstub card", "card without a module"),
    (r"\bDILL\b", "Windows"),
    (r"(?i)activate gremlin|toggle gremlin|activate the profile", "run the profile"),
    (r"(?i)\bcentre\b", "center (US spelling)"),
    (r"(?i)\b(display|output) look\b", "Appearance"),
    (r"(?i)\baction sequences?\b", "action"),
    (r"\bDest\b|\bdest-claimed\b", "output"),
    # The program's name: Gremlin-Platforms in titles, "the program" in text.
    (
        r"\bGremlin\b(?![- ]Platforms)(?<!Joystick Gremlin)",
        "Gremlin-Platforms / the program",
    ),
]

# A string literal in QML / JavaScript (double or single quotes).
_LITERAL = re.compile(r'"((?:[^"\\\n]|\\.)*)"|\'((?:[^\'\\\n]|\\.)*)\'')
_COMMENT = re.compile(r"^\s*(//|\*|/\*)")


def _reads_as_text(s: str) -> bool:
    """Keys, ids, file names and code stay out: text has a space, or starts
    with a capital letter and is not an identifier-like token."""
    if " " in s:
        return True
    # A single word like "Center" or "Colors" is a label (menus, choices).
    if re.fullmatch(r"[A-Z][a-z]+…?", s):
        return True
    return bool(s[:1].isupper()) and not re.fullmatch(r"[A-Za-z0-9_.:/-]+", s)


def _qml_strings() -> list[tuple[str, int, str]]:
    files = sorted(
        list((_ROOT / "qml").glob("*.qml"))
        + list((_ROOT / "qml").glob("*.js"))
        + list((_ROOT / "action_plugins").glob("*/*.qml"))
        + list((_ROOT / "theme").rglob("*.qml"))
    )
    out = []
    for path in files:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if _COMMENT.match(line) or line.lstrip().startswith("import "):
                continue
            for m in _LITERAL.finditer(line):
                text = m.group(1) if m.group(1) is not None else m.group(2)
                if text and _reads_as_text(text):
                    out.append((path.relative_to(_ROOT).as_posix(), number, text))
    return out


def _option_descriptions() -> list[tuple[str, int, str]]:
    """String arguments of every *.register(...) call: Options titles and
    descriptions shown in the Options window."""
    files = [_ROOT / "joystick_gremlin.py", *sorted((_ROOT / "gremlin").rglob("*.py"))]
    files += sorted((_ROOT / "action_plugins").glob("*/__init__.py"))
    out = []
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "register"
            ):
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        if _reads_as_text(arg.value):
                            where = path.relative_to(_ROOT).as_posix()
                            out.append((where, arg.lineno, arg.value))
    return out


def _hits(strings: list[tuple[str, int, str]]) -> list[str]:
    hits = []
    for where, line, text in strings:
        for pattern, instead in _REPLACED:
            if re.search(pattern, text):
                hits.append(f"{where}:{line}: {text[:70]!r} -> use {instead}")
    return hits


def test_the_check_reads_the_ui() -> None:
    # The checks below must really be looking at the program's text.
    strings = _qml_strings()
    assert len(strings) > 1500
    assert any("Module Setup" in text for _f, _l, text in strings)
    assert len(_option_descriptions()) > 40


def test_on_screen_text_uses_the_glossary_words() -> None:
    assert _hits(_qml_strings()) == []


def test_options_descriptions_use_the_glossary_words() -> None:
    assert _hits(_option_descriptions()) == []
