# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Safe writes (03 S68, 04 S13, 07 S23): a file is written whole or not at
all. The swap Windows refuses (antivirus, indexer) is tried again and then
fails cleanly, never written in place; device map templates and the adjusted
photo cache go through the same safe writer (AUD-FILES-03/07/08)."""

from __future__ import annotations

import sys

sys.path.append(".")

import json
import pathlib
import zipfile

import pytest
from PySide6 import QtCore, QtGui

from gremlin import clock
from gremlin.modules import module_file, store
from gremlin.ui import hardware_profile

NODES = json.dumps([{"id": "b1", "kind": "btn", "hwId": 1}])


@pytest.fixture
def no_wait(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    waits: list[float] = []
    monkeypatch.setattr(clock, "sleep", waits.append)
    return waits


def _refuse_swaps(monkeypatch: pytest.MonkeyPatch, times: int | None) -> list[str]:
    """os.replace refuses `times` times (None: always); returns the temp names."""
    real = module_file.os.replace
    seen: list[str] = []

    def replace(src: object, dst: object) -> None:
        seen.append(str(src))
        if times is None or len(seen) <= times:
            raise PermissionError(32, "in use by another program")
        real(src, dst)

    monkeypatch.setattr(module_file.os, "replace", replace)
    return seen


def _no_direct_write(monkeypatch: pytest.MonkeyPatch, path: pathlib.Path) -> None:
    """Writing the real file in place cuts it short and fails (a crash)."""
    real = pathlib.Path.write_bytes

    def write_bytes(self: pathlib.Path, data: bytes) -> int:
        if self == path:
            real(self, data[: len(data) // 2])
            raise OSError(28, "No space left on device")
        return real(self, data)

    monkeypatch.setattr(pathlib.Path, "write_bytes", write_bytes)


def test_a_refused_swap_is_tried_again_and_the_file_is_whole(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, no_wait: list[float]
) -> None:
    path = tmp_path / "x.json"
    path.write_bytes(b'{"old": 1}')
    seen = _refuse_swaps(monkeypatch, 2)
    _no_direct_write(monkeypatch, path)
    module_file.write_bytes(path, b'{"new": 2}')
    assert path.read_bytes() == b'{"new": 2}'
    assert len(seen) == 3
    assert no_wait and all(0 < w <= 1 for w in no_wait)
    assert list(tmp_path.iterdir()) == [path]


def test_a_swap_refused_always_raises_and_leaves_the_file_as_it_was(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, no_wait: list[float]
) -> None:
    path = tmp_path / "x.json"
    path.write_bytes(b'{"old": 1}')
    _refuse_swaps(monkeypatch, None)
    _no_direct_write(monkeypatch, path)
    with pytest.raises(OSError):
        module_file.write_bytes(path, b'{"new": 2}')
    assert path.read_bytes() == b'{"old": 1}'
    # No temporary copy is left behind; the waits are bounded.
    assert list(tmp_path.iterdir()) == [path]
    assert sum(no_wait) < 2


def test_temporary_names_are_unique(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, no_wait: list[float]
) -> None:
    path = tmp_path / "x.json"
    seen = _refuse_swaps(monkeypatch, 0)
    module_file.write_bytes(path, b"1")
    module_file.write_bytes(path, b"2")
    assert len(set(seen)) == 2
    assert all(name.endswith(".tmp") for name in seen)


# --- device map templates (AUD-FILES-07) -----------------------------------


@pytest.fixture
def profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> hardware_profile.HardwareProfile:
    monkeypatch.setattr(store, "folder", lambda: tmp_path / "maps")
    return hardware_profile.HardwareProfile()


def _crash_mid_write(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every write stops half way (a crash or a full disk)."""
    real_bytes = pathlib.Path.write_bytes
    real_text = pathlib.Path.write_text

    def write_bytes(self: pathlib.Path, data: bytes) -> int:
        real_bytes(self, data[: len(data) // 2])
        raise OSError(28, "No space left on device")

    def write_text(self: pathlib.Path, data: str, *a: object, **k: object) -> int:
        real_text(self, data[: len(data) // 2], encoding="utf-8")
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(pathlib.Path, "write_bytes", write_bytes)
    monkeypatch.setattr(pathlib.Path, "write_text", write_text)


def _template_path(
    profile: hardware_profile.HardwareProfile, name: str
) -> pathlib.Path:
    path = profile._template_file(name)
    assert path is not None
    return path


def test_a_template_save_cut_short_keeps_the_old_template(
    profile: hardware_profile.HardwareProfile, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert profile.saveTemplate("Evo", NODES, "VKB EVO R")
    path = _template_path(profile, "Evo")
    before = path.read_bytes()
    with monkeypatch.context() as m:
        _crash_mid_write(m)
        more = json.dumps(
            [{"id": f"b{i}", "kind": "btn", "hwId": i} for i in range(40)]
        )
        assert not profile.saveTemplate("Evo", more, "VKB EVO R")
    assert path.read_bytes() == before
    assert [p.name for p in path.parent.iterdir()] == [path.name]


def test_a_template_rename_cut_short_keeps_the_old_template(
    profile: hardware_profile.HardwareProfile, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert profile.saveTemplate("One", NODES, "x")
    old = _template_path(profile, "One")
    with monkeypatch.context() as m:
        _crash_mid_write(m)
        assert not profile.renameTemplate("One", "Two")
    assert json.loads(old.read_text(encoding="utf-8"))["name"] == "One"
    assert [p.name for p in old.parent.iterdir()] == [old.name]


def test_a_template_import_cut_short_leaves_no_half_template(
    profile: hardware_profile.HardwareProfile,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    assert profile.saveTemplate("Shared", NODES, "x")
    out = tmp_path / "shared.json"
    url = QtCore.QUrl.fromLocalFile(str(out)).toString()
    assert profile.exportTemplate("Shared", url)
    folder = _template_path(profile, "Shared").parent
    with monkeypatch.context() as m:
        _crash_mid_write(m)
        assert profile.importTemplate(url) == ""
    assert [p.name for p in folder.iterdir()] == [
        _template_path(profile, "Shared").name
    ]


def test_a_template_export_cut_short_keeps_the_old_file(
    profile: hardware_profile.HardwareProfile,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    assert profile.saveTemplate("Shared", NODES, "x")
    out = tmp_path / "shared.gtemplate"
    out.write_bytes(b"the user's old file")
    url = QtCore.QUrl.fromLocalFile(str(out)).toString()
    with monkeypatch.context() as m:
        _crash_mid_write(m)
        assert not profile.exportTemplate("Shared", url)
    assert out.read_bytes() == b"the user's old file"
    assert profile.exportTemplate("Shared", url)
    # One ".gtemplate" file (07 S80, S110): template.json and its pictures.
    with zipfile.ZipFile(out) as zf:
        assert json.loads(zf.read("template.json"))["name"] == "Shared"


# --- adjusted picture cache (AUD-FILES-08; a picture's look, 07 S43) ---------


def test_a_cut_short_cache_file_is_not_reused(
    profile: hardware_profile.HardwareProfile, tmp_path: pathlib.Path
) -> None:
    src = tmp_path / "photo.png"
    image = QtGui.QImage(20, 10, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtGui.QColor("#FF0000"))
    image.save(str(src))
    url = QtCore.QUrl.fromLocalFile(str(src)).toString()
    first = profile.adjustedPhotoUrl(url, {"grey": True})
    cached = pathlib.Path(QtCore.QUrl(first).toLocalFile())
    whole = cached.read_bytes()
    cached.write_bytes(whole[: len(whole) // 2])
    again = profile.adjustedPhotoUrl(url, {"grey": True})
    assert not QtGui.QImage(QtCore.QUrl(again).toLocalFile()).isNull()
    assert pathlib.Path(QtCore.QUrl(again).toLocalFile()).read_bytes() == whole


def test_the_cache_is_written_through_the_safe_writer(
    profile: hardware_profile.HardwareProfile,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    src = tmp_path / "photo.png"
    image = QtGui.QImage(20, 10, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtGui.QColor("#00FF00"))
    image.save(str(src))
    url = QtCore.QUrl.fromLocalFile(str(src)).toString()
    with monkeypatch.context() as m:
        _crash_mid_write(m)
        assert profile.adjustedPhotoUrl(url, {"grey": True}) == ""
    cache = tmp_path / "maps" / "cache"
    assert not [p for p in cache.rglob("*") if p.is_file()]
