# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Pack Import never lets an unexpected error out of the importPack
slot (07 S104 batch, AD8 audit): a failure while the pack is read or applied
comes back as {"ok": False, "error": "This file can't be read (...)."} and
is logged, instead of an exception into QML."""

from __future__ import annotations

import json
import logging
import zipfile
from pathlib import Path

import pytest

from gremlin.ui import device_pack, hardware_profile


def _pack(tmp_path: Path) -> Path:
    pack = tmp_path / "pack.zip"
    with zipfile.ZipFile(pack, "w") as z:
        z.writestr("pack.json", "{}")
    return pack


def _import(pack: Path, selection: str) -> dict:
    cls = hardware_profile.HardwareProfile
    done = cls.importPack(cls.__new__(cls), pack.as_uri(), "Stick", selection)
    return json.loads(done)


def test_apply_zip_raising_comes_back_as_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def boom(*_a: object, **_k: object) -> dict:
        raise ValueError("bad member")

    monkeypatch.setattr(device_pack, "apply_zip", boom)
    monkeypatch.setattr(hardware_profile, "_autosave_before_pack", lambda *a, **k: "")
    with caplog.at_level(logging.ERROR, logger="system"):
        done = _import(_pack(tmp_path), json.dumps({"items": []}))
    assert done == {"ok": False, "error": "This file can't be read (bad member)."}
    logged = [r for r in caplog.records if r.exc_info]
    assert logged and "bad member" in str(logged[0].exc_info[1])


def test_describe_zip_raising_comes_back_as_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_a: object, **_k: object) -> dict:
        raise KeyError("sections")

    monkeypatch.setattr(device_pack, "describe_zip", boom)
    done = _import(_pack(tmp_path), "")
    assert done["ok"] is False
    assert done["error"].startswith("This file can't be read (")
