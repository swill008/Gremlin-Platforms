# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""device_library.setup_wires (01 S157, gap SEARCH-LIB-PRIVATE): a saved
setup's bindings/wires.json, or why it can't be read."""

from __future__ import annotations

import json
import pathlib
import sys
import zipfile

sys.path.append(".")

import pytest

from gremlin import device_library

_WIRES = {"modes": [{"name": "Default", "lines": [], "inputs": []}], "actions": []}


def _zip(path: pathlib.Path, parts: dict[str, object]) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name, value in parts.items():
            zf.writestr(name, json.dumps(value))


@pytest.fixture
def library(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> pathlib.Path:
    doc = {
        "devices": [
            {
                "key": "dev1",
                "setups": [
                    {"key": "good", "file": "good.gmap"},
                    {"key": "bare", "file": "bare.gmap"},
                    {"key": "bad", "file": "bad.gmap"},
                    {"key": "wrong", "file": "wrong.gmap"},
                ],
            }
        ]
    }
    monkeypatch.setattr(device_library, "folder", lambda: tmp_path)
    monkeypatch.setattr(device_library, "_read", lambda: doc)
    head = {"device": "Stick", "id": "name:Stick"}
    _zip(tmp_path / "good.gmap", {"gmap.json": head, "bindings/wires.json": _WIRES})
    _zip(tmp_path / "bare.gmap", {"gmap.json": head})
    (tmp_path / "bad.gmap").write_bytes(b"not a zip")
    _zip(
        tmp_path / "wrong.gmap",
        {"gmap.json": head, "bindings/wires.json": {"modes": "x"}},
    )
    return tmp_path


def test_saved_setup_returns_its_wires(library: pathlib.Path) -> None:
    assert device_library.setup_wires("good") == _WIRES


def test_setup_without_bindings_returns_empty(library: pathlib.Path) -> None:
    assert device_library.setup_wires("bare") == {}


@pytest.mark.parametrize("key", ["missing", "bad", "wrong"])
def test_unreadable_setup_returns_a_reason(library: pathlib.Path, key: str) -> None:
    got = device_library.setup_wires(key)
    assert isinstance(got, str)
    assert got
