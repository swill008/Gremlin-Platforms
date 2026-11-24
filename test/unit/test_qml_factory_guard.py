# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""QML makes our Python types only through ModelFactory.create (plan
claude/plans/memory-qml-factory.md, section 2 "Guard", answer 4a).

PySide6 never frees the Python wrapper of an object QML instantiates
(PYSIDE-1407, gap PYSIDE-WRAPPERS on program map page 01). A QML file that
declares one of our ``@ta.QmlElement`` types as ``TypeName {`` brings that
leak back; this test fails on it. Declarations not converted yet are listed
in STAGE2_PENDING as (file, type) pairs; the list may only shrink: a pair
that no longer appears in its file fails too, so it is taken off.
"""

from __future__ import annotations

import importlib
import pathlib
import re

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_PY_FOLDERS = ("gremlin", "action_plugins", "theme")
_QML_FOLDERS = ("qml", "action_plugins", "theme")
_DECORATED = re.compile(r"@ta\.QmlElement\s*\n(?:\s*@.*\n)*\s*class\s+(\w+)")
_CREATE = re.compile(r"""ModelFactory\.create\(\s*["'](\w+)["']""")

# Declarations still to convert, (QML file, type): empty since stage 2 of
# the plan. Never add entries; a new type is made with ModelFactory.create.
STAGE2_PENDING: frozenset[tuple[str, str]] = frozenset()


def _registered() -> dict[str, str]:
    """Every ta.QmlElement class name and the module that defines it."""
    out: dict[str, str] = {}
    for folder in _PY_FOLDERS:
        for path in (_ROOT / folder).rglob("*.py"):
            text = path.read_text("utf-8", "replace")
            module = ".".join(path.relative_to(_ROOT).with_suffix("").parts)
            module = module.removesuffix(".__init__")
            for name in _DECORATED.findall(text):
                out[name] = module
    return out


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"(?m)^\s*//.*$", "", text)
    return re.sub(r"(?m)\s//[^\"'\n]*$", "", text)


def _qml_files() -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for folder in _QML_FOLDERS:
        files.extend(sorted((_ROOT / folder).rglob("*.qml")))
    return files


def _declarations(names: set[str]) -> set[tuple[str, str]]:
    """(file, type) for every `TypeName {` of a registered type."""
    pattern = re.compile(r"(?<![\w.])(" + "|".join(sorted(names)) + r")\s*\{")
    found: set[tuple[str, str]] = set()
    for path in _qml_files():
        text = _strip_comments(path.read_text("utf-8", "replace"))
        rel = path.relative_to(_ROOT).as_posix()
        for match in pattern.finditer(text):
            found.add((rel, match.group(1)))
    return found


def factory_made() -> list[str]:
    """Types QML makes only through the factory: used in a
    ModelFactory.create call and declared nowhere (test_leaks.py counts
    their shells)."""
    used: set[str] = set()
    for path in _qml_files():
        text = _strip_comments(path.read_text("utf-8", "replace"))
        used.update(_CREATE.findall(text))
    pending = {name for _, name in STAGE2_PENDING}
    return sorted(used - pending)


def test_the_scan_finds_the_registered_types() -> None:
    names = _registered()
    assert len(names) > 100, sorted(names)
    assert "HardwareLayoutModel" in names


def test_no_qml_file_declares_a_registered_type() -> None:
    found = _declarations(set(_registered()))
    new = sorted(found - STAGE2_PENDING)
    assert new == [], (
        'Make these with ModelFactory.create("TypeName", parent, props) '
        "(claude/plans/memory-qml-factory.md, section 2): " + repr(new)
    )


def test_the_pending_list_only_holds_what_is_still_declared() -> None:
    found = _declarations(set(_registered()))
    gone = sorted(STAGE2_PENDING - found)
    assert gone == [], "Converted: take these off STAGE2_PENDING: " + repr(gone)


def test_converted_types_are_uncreatable_in_qml() -> None:
    """Answer 4a: a type QML gets only from the factory is registered
    uncreatable, so a new `TypeName {}` fails at load; a type still
    declared somewhere can't be."""
    from gremlin.ui import model_factory

    only = set(model_factory.FACTORY_ONLY)
    assert sorted(set(factory_made()) - only) == []
    pending = {name for _, name in STAGE2_PENDING}
    assert sorted(only & pending) == []


def test_every_factory_call_names_a_registered_type() -> None:
    names = _registered()
    used: dict[str, list[str]] = {}
    for path in _qml_files():
        text = _strip_comments(path.read_text("utf-8", "replace"))
        for name in _CREATE.findall(text):
            used.setdefault(name, []).append(path.relative_to(_ROOT).as_posix())
    unknown = {name: files for name, files in used.items() if name not in names}
    assert unknown == {}
    # The registry ta.QmlElement fills holds them once their module loads.
    from gremlin.ui import type_aliases as ta

    for name in sorted(used):
        importlib.import_module(names[name])
        assert ta.QML_TYPES.get(name) is not None, name
