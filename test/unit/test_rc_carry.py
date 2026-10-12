# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Favourites are a program setting (07 S137, D-07-RIGHTCLICK 3a): after
adding favourites in the real Device Mapping Editor window (☆ in the right-click menu
and in the menu bar) and saving the map, the module file, an Export (.gmap)
and the Export / Import Device window's .gmap hold none of them; the
program's settings do."""

from __future__ import annotations

import pytest

from test.unit.test_rc_e2e import run_smoke

FAVS = ["edit.cut", "bringToFront", "hide"]


@pytest.fixture(scope="module")
def seen(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_smoke(tmp_path_factory.mktemp("rc_carry"), "carry")


def _step(seen: dict, name: str) -> dict:
    res = seen.get(name)
    assert isinstance(res, dict), f"{name}: {res!r}"
    assert "error" not in res or name in ("carry-gmap",), res.get("traceback") or res
    return res


def _clean(text: str) -> None:
    assert "favourite" not in text.lower()
    for cid in ("edit.duplicate", "edit.cut"):
        assert cid not in text


def test_favourites_were_added(seen: dict) -> None:
    res = _step(seen, "carry-add")
    assert res["favs"] == FAVS, res


def test_module_file_has_none(seen: dict) -> None:
    res = _step(seen, "carry-module")
    assert res["saved"], "the map was not saved"
    _clean(res["text"])


def test_export_has_none(seen: dict) -> None:
    res = _step(seen, "carry-gmap")
    assert res["error"] == "", res
    assert res["files"]
    for text in res["files"].values():
        _clean(text)


def test_device_pack_has_none(seen: dict) -> None:
    res = _step(seen, "carry-pack")
    assert res["done"].get("ok"), res["done"]
    assert res["files"]
    for text in res["files"].values():
        _clean(text)


def test_the_program_setting_holds_them(seen: dict) -> None:
    res = _step(seen, "carry-setting")
    assert res["stored"] == FAVS
