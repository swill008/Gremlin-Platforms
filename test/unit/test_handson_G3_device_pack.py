# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Pack, hands-on fixes (08 S106 D-08-PACK-START, 08 S107
D-08-PACK-BG).

S106: the device list marks a device whose module file can't be read
"(file damaged)" and says which devices can be exported, so the window opens
on the first one that can. S107: exportPackAsync returns at once and the zip
is built and written on a program thread; packExporting is True until
packExported(result) is announced on the main thread; one export at a time;
a failure names the file, the folder and why (Q19)."""

from __future__ import annotations

import io
import json
import threading
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6 import QtCore

from gremlin import threads
from gremlin.modules import store
from gremlin.ui import device_pack, hardware_profile
from test.unit import test_stage1_modules
from test.unit.test_stage1_history_pack import _url, new_profile
from test.unit.test_stage1_modules import (
    map_button,
    stick_doc,
    stick_uid,
    vjoy_doc,
    write_module,
)

_app = test_stage1_modules._app
folder = test_stage1_modules.folder

WAIT_MS = 10000


def _rows() -> dict[str, dict]:
    hw = hardware_profile.HardwareProfile()
    return {r["name"]: r for r in json.loads(hw.packDevices())["devices"]}


def _damage(name: str) -> Path:
    """The module file of a known device, written as text that isn't JSON."""
    row = store.match_known_device(name)
    assert row is not None
    path = store.path_for(name, str(row.get("guid") or ""))
    path.write_text("{ not json", encoding="utf-8")
    return path


# --- S106 -------------------------------------------------------------------


def test_s106_a_damaged_file_is_listed_and_marked(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_module(folder, "pjoy_pro", stick_doc())
    new_profile(monkeypatch)  # has seen "Gone Stick" (listed before pJoy Pro)
    _damage("Gone Stick")
    rows = _rows()
    gone = rows["Gone Stick"]
    assert gone["hasFile"] and gone["damaged"]
    assert gone["canExport"] is False
    assert gone["label"] == "Gone Stick (file damaged)"
    good = rows["pJoy Pro"]
    assert good["canExport"] is True and not good["damaged"]
    assert good["label"] == "pJoy Pro"


def test_s106_a_device_without_a_file_cannot_be_exported(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    new_profile(monkeypatch)
    rows = _rows()
    assert rows["pJoy Pro"]["canExport"] is False
    assert not rows["pJoy Pro"]["damaged"]
    assert rows["pJoy Pro"]["label"] == "pJoy Pro"


# --- S107 -------------------------------------------------------------------


class _SlowWriter:
    """device_pack.write_pack held until released: where it ran."""

    def __init__(self) -> None:
        self.entered = threading.Event()
        self.release = threading.Event()
        self.thread: threading.Thread | None = None
        self.calls = 0
        self._real = device_pack.write_pack

    def __call__(self, *args: object, **kwargs: object) -> object:
        self.calls += 1
        self.thread = threading.current_thread()
        self.entered.set()
        # Bounded: a failing test never leaves the worker waiting.
        self.release.wait(WAIT_MS / 1000)
        return self._real(*args, **kwargs)  # type: ignore[arg-type]


@pytest.fixture
def slow(monkeypatch: pytest.MonkeyPatch) -> Iterator[_SlowWriter]:
    writer = _SlowWriter()
    monkeypatch.setattr(device_pack, "write_pack", writer)
    yield writer
    writer.release.set()
    if writer.thread is not None:
        writer.thread.join(WAIT_MS / 1000)


@pytest.fixture
def stick(folder: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (folder / "pjoy_pro").mkdir()
    (folder / "pjoy_pro" / "photo.png").write_bytes(b"a photo")
    write_module(folder, "pjoy_pro", stick_doc(image="pjoy_pro/photo.png"))
    write_module(folder, "vjoy_1", vjoy_doc())
    profile = new_profile(monkeypatch)
    map_button(profile, stick_uid(), 1, 1)


def _pack_threads() -> list[str]:
    return [n for n in threads.running() if "device pack" in n.lower()]


def test_s107_export_runs_in_the_background(
    qtbot: object, stick: None, slow: _SlowWriter, tmp_path: Path
) -> None:
    hw = hardware_profile.HardwareProfile()
    target = tmp_path / "p.zip"
    changes: list[bool] = []
    hw.packExportingChanged.connect(lambda: changes.append(hw.packExporting))
    announced: list[tuple[dict, threading.Thread]] = []
    hw.packExported.connect(
        lambda raw: announced.append((json.loads(raw), threading.current_thread()))
    )

    started = json.loads(hw.exportPackAsync("pJoy Pro", _url(target), "{}"))
    assert started == {"ok": True, "started": True}
    assert hw.packExporting
    assert slow.entered.wait(WAIT_MS / 1000)
    assert slow.thread is not None
    assert slow.thread is not threading.main_thread()
    assert slow.thread.name.startswith(threads.PREFIX)
    # The main thread keeps running Qt events (a timer fires) meanwhile.
    ticks: list[int] = []
    timer = QtCore.QTimer()
    timer.setInterval(5)
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start()
    qtbot.waitUntil(lambda: len(ticks) >= 3, timeout=WAIT_MS)  # type: ignore[attr-defined]
    timer.stop()
    assert hw.packExporting
    assert not announced
    assert not target.exists()
    # One at a time: a second Export is refused while this one runs.
    busy = json.loads(hw.exportPackAsync("pJoy Pro", _url(tmp_path / "q.zip"), "{}"))
    assert busy["ok"] is False and busy.get("busy") is True

    with qtbot.waitSignal(hw.packExported, timeout=WAIT_MS):  # type: ignore[attr-defined]
        slow.release.set()
    result, where = announced[0]
    assert where is threading.main_thread()
    assert result["ok"], result
    assert result["path"] == str(target)
    assert result["folderUrl"] == target.parent.as_uri()
    assert result["device"] == "pJoy Pro"
    assert result["sizeText"]
    assert not hw.packExporting
    assert changes == [True, False]
    assert slow.calls == 1
    assert not (tmp_path / "q.zip").exists()
    with zipfile.ZipFile(target) as zf:
        assert {"map.json", "wires.json", "photo.png"} <= set(zf.namelist())
    qtbot.waitUntil(lambda: not _pack_threads(), timeout=WAIT_MS)  # type: ignore[attr-defined]


def test_s107_a_write_failure_names_file_folder_and_reason(
    qtbot: object, stick: None, tmp_path: Path
) -> None:
    hw = hardware_profile.HardwareProfile()
    # A folder already has the pack's name: it can't be written.
    target = tmp_path / "p.zip"
    target.mkdir()
    with qtbot.waitSignal(hw.packExported, timeout=WAIT_MS) as blocker:  # type: ignore[attr-defined]
        started = json.loads(hw.exportPackAsync("pJoy Pro", _url(target), "{}"))
        assert started["ok"]
    result = json.loads(blocker.args[0])
    assert result["ok"] is False
    assert result["error"] == (
        f"Export failed. p.zip could not be written to {target.parent}: "
        "a folder has that name."
    )
    assert not hw.packExporting


def test_s107_a_refusal_is_told_at_once_and_starts_nothing(
    folder: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    new_profile(monkeypatch)
    _damage("Gone Stick")
    hw = hardware_profile.HardwareProfile()
    told = json.loads(hw.exportPackAsync("Gone Stick", _url(tmp_path / "g.zip"), "{}"))
    assert told["ok"] is False
    assert "is damaged" in told["error"] and "Start Fresh" in told["error"]
    assert not hw.packExporting
    inside = json.loads(
        hw.exportPackAsync("Gone Stick", _url(folder / "x.zip"), "{}")
    )
    assert inside["ok"] is False
    assert not hw.packExporting


def test_s107_the_profile_is_read_on_the_main_thread(
    qtbot: object, stick: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The wires come from the open profile: they are read before the worker
    starts, never on it."""
    seen: list[threading.Thread] = []
    real = device_pack._collect_wires

    def spy(*args: object, **kwargs: object) -> dict:
        seen.append(threading.current_thread())
        return real(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(device_pack, "_collect_wires", spy)
    hw = hardware_profile.HardwareProfile()
    with qtbot.waitSignal(hw.packExported, timeout=WAIT_MS) as blocker:  # type: ignore[attr-defined]
        json.loads(hw.exportPackAsync("pJoy Pro", _url(tmp_path / "m.zip"), "{}"))
    assert json.loads(blocker.args[0])["ok"]
    assert seen and all(t is threading.main_thread() for t in seen)


def test_s107_the_sync_export_still_writes_the_same_pack(
    stick: None, tmp_path: Path
) -> None:
    hw = hardware_profile.HardwareProfile()
    done = json.loads(hw.exportPack("pJoy Pro", _url(tmp_path / "s.zip"), "{}"))
    assert done["ok"], done
    data, info = device_pack.assemble("pJoy Pro", hw._resolve_existing)  # type: ignore[misc]
    assert info["device"] == "pJoy Pro"
    with zipfile.ZipFile(tmp_path / "s.zip") as zf:
        assert set(zf.namelist()) == set(zipfile.ZipFile(io.BytesIO(data)).namelist())
