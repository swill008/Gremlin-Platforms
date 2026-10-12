# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""util.path_key / same_path / is_inside: the one "same file?" and "inside
this folder?" rule (Windows: case and slashes don't matter), and no module
keeping its own copy (audit 2026-10-12 LEFTOVERS section 6)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from gremlin import util

ROOT = Path(__file__).resolve().parents[2]


def test_case_and_separators_are_the_same_file(tmp_path: Path) -> None:
    f = tmp_path / "Profile.XML"
    f.write_text("x")
    other = str(f).upper().replace("\\", "/")
    assert util.same_path(f, other)
    assert util.path_key(f) == util.path_key(other)


def test_dot_dot_and_relative_parts_resolve(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    assert util.same_path(tmp_path / "a" / ".." / "x.xml", tmp_path / "x.xml")


def test_missing_files_still_compare(tmp_path: Path) -> None:
    gone = tmp_path / "nope" / "Gone.xml"
    assert util.same_path(gone, str(gone).lower())
    assert not util.same_path(gone, tmp_path / "nope" / "other.xml")


@pytest.mark.parametrize("empty", [None, ""])
def test_none_or_empty_is_never_the_same(empty: str | None, tmp_path: Path) -> None:
    assert not util.same_path(empty, tmp_path)
    assert not util.same_path(tmp_path, empty)
    assert not util.same_path(empty, empty)


def test_is_inside(tmp_path: Path) -> None:
    folder = tmp_path / "Lib"
    assert util.is_inside(folder, folder)
    assert util.is_inside(folder / "Sub" / "f.json", str(folder).lower())
    assert util.is_inside(str(folder / "x").upper(), folder)
    assert not util.is_inside(tmp_path / "Library" / "f", folder)
    assert not util.is_inside(tmp_path, folder)
    assert not util.is_inside(folder / ".." / "other", folder)


def test_is_inside_a_drive_root() -> None:
    root = Path(Path.cwd().anchor)
    assert util.is_inside(root / "x" / "y", root)


MODULES = {
    "gremlin/library_copy.py": "util.same_path",
    "gremlin/library_profiles.py": "util.same_path",
    "gremlin/ui/backend.py": "util.same_path",
    "gremlin/ui/history_model.py": "util.same_path",
    "gremlin/mode_manager.py": "util.same_path",
    "gremlin/device_library.py": "util.is_inside",
}
_PRIVATE = re.compile(
    r"^def (_same_path|_same|_same_file|_path_key|_same_key|_inside)\(", re.M
)


@pytest.mark.parametrize("rel", sorted(MODULES))
def test_modules_use_the_shared_rule(rel: str) -> None:
    text = (ROOT / rel).read_text(encoding="utf-8")
    assert MODULES[rel] in text
    assert not _PRIVATE.search(text), f"{rel} keeps its own path comparison"
    assert ".resolve() ==" not in text


def test_history_model_uses_is_inside() -> None:
    text = (ROOT / "gremlin/ui/history_model.py").read_text(encoding="utf-8")
    assert "util.is_inside" in text
