# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Home cards show the last input without re-reading the module file for
every input event (hundreds a second while a stick moves), yet still follow
a newer save of the module."""

from __future__ import annotations

import json
import os
import pathlib
import types
from collections.abc import Callable

import pytest

from gremlin.modules import store
from gremlin.ui import module_model


@pytest.fixture
def setup(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[pathlib.Path, list[str], list[float], Callable[[], dict]]:
    path = tmp_path / "stick.json"
    path.write_text(json.dumps({"claim": {"buttons": [1, 2]}}), encoding="utf-8")
    reads = []
    real_load = module_model._load_module_doc

    def counting_load(name: str, guid: str = "") -> dict:
        reads.append(name)
        return real_load(name, guid)

    monkeypatch.setattr(store, "folder", lambda: tmp_path)
    monkeypatch.setattr(store, "slug_for", lambda name, guid="": "stick")
    monkeypatch.setattr(module_model, "_load_module_doc", counting_load)
    clock = [100.0]
    monkeypatch.setattr(module_model.clock, "monotonic", lambda: clock[0])
    model = types.SimpleNamespace(
        _source_claims={},
        _CLAIM_CHECK_S=module_model.ModuleListModel._CLAIM_CHECK_S,
    )
    row = types.SimpleNamespace(slug="stick", raw_name="Stick", name="Stick", guid="")

    def claim() -> dict:
        return module_model.ModuleListModel._source_claim(model, row)

    return path, reads, clock, claim


def test_many_events_read_the_file_once(setup: tuple) -> None:
    _path, reads, clock, claim = setup
    for _ in range(500):
        assert claim()["buttons"] == [1, 2]
        clock[0] += 0.002  # 500 events a second
    # One read, then only a cheap look at the file's date now and then.
    assert len(reads) == 1


def test_a_newer_save_is_picked_up(setup: tuple) -> None:
    path, reads, clock, claim = setup
    assert claim()["buttons"] == [1, 2]
    path.write_text(json.dumps({"claim": {"buttons": [1, 2, 3]}}), encoding="utf-8")
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 10_000_000))
    clock[0] += 0.1
    assert claim()["buttons"] == [1, 2]  # not looked at yet
    clock[0] += 1.0
    assert claim()["buttons"] == [1, 2, 3]
    assert len(reads) == 2
