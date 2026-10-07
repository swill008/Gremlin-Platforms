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


# | Python display strings (GL-018): the Configuration list text built in
# | binding_catalog.py and the result lines Python hands to the screens
# | (Auto Mapper, GL-228). The QML check above can't see them.

# Words for what an input does (glossary D2, D11): "action(s)", and an
# input with none shows "No actions".
_ACTION_WORDS = [
    (r"(?i)\bmappings?\b", "action / actions"),
    (r"(?i)\bassignments?\b", "action / actions"),
    (r"^(Empty|Sequence)$", "No actions / the action's name"),
]

_LOG_CALLS = {"debug", "info", "warning", "error", "exception", "critical", "trace"}


_SCOPES = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


def _python_strings(path: Path) -> list[tuple[str, int, str]]:
    """Text a Python file can put on screen: string literals and f-strings
    ({} for each value), leaving out docstrings and log lines."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    skip: set[int] = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if (
            isinstance(node, _SCOPES)
            and body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
        ):
            skip.add(id(body[0].value))
        if isinstance(node, ast.Call):
            name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
            if name in _LOG_CALLS:
                skip.update(id(sub) for sub in ast.walk(node))
        if isinstance(node, ast.JoinedStr):
            skip.update(id(part) for part in node.values)
    where = path.relative_to(_ROOT).as_posix()
    out = []
    for node in ast.walk(tree):
        if id(node) in skip:
            continue
        if isinstance(node, ast.JoinedStr):
            text = "".join(
                str(part.value) if isinstance(part, ast.Constant) else "{}"
                for part in node.values
            )
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            text = node.value
        else:
            continue
        if text and _reads_as_text(text):
            out.append((where, node.lineno, text))
    return out


def _catalog_strings() -> list[tuple[str, int, str]]:
    return _python_strings(_ROOT / "gremlin" / "ui" / "binding_catalog.py")


def _result_strings() -> list[tuple[str, int, str]]:
    return _python_strings(_ROOT / "gremlin" / "auto_mapper.py")


def _word_hits(strings: list[tuple[str, int, str]]) -> list[str]:
    hits = []
    for where, line, text in strings:
        for pattern, instead in _REPLACED + _ACTION_WORDS:
            if re.search(pattern, text):
                hits.append(f"{where}:{line}: {text[:70]!r} -> use {instead}")
    return hits


def test_the_check_reads_the_python_display_text() -> None:
    catalog = [text for _f, _l, text in _catalog_strings()]
    assert "All types" in catalog and "No actions" in catalog
    results = [text for _f, _l, text in _result_strings()]
    assert any(text.startswith("Made {} ") for text in results)
    assert "No input module selected" in results


def test_configuration_list_text_uses_the_glossary_words() -> None:
    assert _word_hits(_catalog_strings()) == []


def test_configuration_list_type_names_are_the_action_names() -> None:
    from gremlin.plugin_manager import PluginManager
    from gremlin.ui import binding_catalog

    tags = PluginManager().tag_map
    names = binding_catalog.type_filter_names()
    named = [
        (tag, name)
        for (_key, tag), name in zip(binding_catalog._TYPE_FILTERS, names, strict=True)
        if tag
    ]
    assert named, "the Type box names no action"
    wrong = {tag: name for tag, name in named if name != tags[tag].name}
    assert wrong == {}


def test_auto_mapper_result_uses_the_glossary_words() -> None:
    assert _word_hits(_result_strings()) == []
