# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Help → Save Diagnostics… (01 S132, D-01-DIAG-ZIP): one zip with the logs,
the settings, the device list and the versions; the open profile only when
ticked; the user's name in folder paths replaced by <user>; a failure names
the file, the folder and the reason (07 Q19); written on a worker while the
window stays responsive. A made-up user in a temp folder, never the real
one."""

from __future__ import annotations

import json
import os
import pathlib
import stat
import threading
import zipfile
from collections.abc import Iterator
from types import SimpleNamespace

import pytest
from PySide6 import QtCore

from gremlin import diagnostics, threads
from gremlin.ui import diagnostics as ui_diagnostics

WAIT_MS = 10000
NAME = "Pat Tester"


@pytest.fixture
def home(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
    """A made-up user: USERPROFILE ...\\Users\\Pat Tester, its data folder,
    logs, settings and two devices from the input side."""
    from gremlin import util
    from gremlin.modules import hardware, registry

    home = tmp_path / "Users" / NAME
    data = home / "Gremlin Platforms"
    logs = data / "logs"
    logs.mkdir(parents=True)
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("USERNAME", NAME)
    monkeypatch.setattr(util, "userprofile_path", lambda: str(data))
    monkeypatch.setattr(util, "logs_dir", lambda: logs)
    (logs / "system.log").write_text(
        f"2026-10-07 10:00:00 Loaded {home}\\Gremlin Platforms\\profiles\\a.xml\n"
        f"2026-10-07 10:00:01 Read {home.as_posix()}/Desktop/x.txt\n",
        encoding="utf-8",
    )
    (logs / "logs.txt").write_text(f"READ | Profile | load | {home}\\a.xml | ok\n")
    (logs / f"{NAME} notes.log").write_text("kept\n", encoding="utf-8")
    (data / "configuration.json").write_text(
        json.dumps({"global": {"files": {"profiles-folder": str(home / "P")}}}),
        encoding="utf-8",
    )
    stick = SimpleNamespace(
        name="pJoy Pro", device_guid="{0F0E0D0C-0000-0000-0000-000000000001}",
        is_virtual=False, vendor_id=0x044F, product_id=0xB10A,
        axis_count=6, button_count=32, hat_count=1,
    )
    vjoy = SimpleNamespace(
        name="vJoy Device", device_guid="{0F0E0D0C-0000-0000-0000-000000000002}",
        is_virtual=True, vendor_id=0x1234, product_id=0xBEAD,
        axis_count=8, button_count=128, hat_count=4,
    )
    monkeypatch.setattr(hardware, "devices", lambda: [stick, vjoy])
    monkeypatch.setattr(
        hardware, "device_connected",
        lambda guid: str(guid).strip("{}").upper().endswith("1"),
    )
    modules = [
        SimpleNamespace(
            name="pJoy Pro", bound_guid="0F0E0D0C-0000-0000-0000-000000000001",
            is_output=False, path=data / "modules" / "pjoy.json", slug="pjoy",
        ),
        SimpleNamespace(
            name="Old Pedals", bound_guid="0F0E0D0C-0000-0000-0000-0000000000FF",
            is_output=False, path=data / "modules" / "pedals.json", slug="pedals",
        ),
        SimpleNamespace(
            name="vJoy 1", bound_guid="", is_output=True,
            path=data / "modules" / "vjoy1.json", slug="vjoy1",
        ),
    ]
    monkeypatch.setattr(registry, "modules", lambda: modules)
    return home


@pytest.fixture
def open_profile(home: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> object:
    """A real open profile, saved under a name with the user's name in it,
    whose text names a script in the user's folder."""
    from gremlin import shared_state
    from gremlin.profile import Profile

    profile = Profile()
    profile.fpath = home / "Gremlin Platforms" / "profiles" / f"{NAME} flight.xml"
    real = profile._xml_text
    monkeypatch.setattr(
        profile, "_xml_text",
        lambda: real().replace("<profile", f"<!-- {home}\\s.py -->\n<profile", 1),
    )
    monkeypatch.setattr(shared_state, "current_profile", profile)
    return profile


def _read(path: pathlib.Path) -> dict[str, str]:
    with zipfile.ZipFile(path) as zf:
        return {n: zf.read(n).decode("utf-8") for n in zf.namelist()}


def _save(include: bool, dest: pathlib.Path) -> tuple[bool, str]:
    return diagnostics.save(diagnostics.collect(include), dest)


def test_the_zip_holds_logs_settings_devices_and_versions(
    home: pathlib.Path, open_profile: object, tmp_path: pathlib.Path
) -> None:
    dest = tmp_path / "out" / "diag.zip"
    dest.parent.mkdir()
    ok, message = _save(False, dest)
    assert ok, message
    assert message == f"Diagnostics saved to {dest}."
    files = _read(dest)
    assert set(files) == {
        "README.txt", "versions.json", "devices.json",
        "settings/configuration.json",
        "logs/system.log", "logs/logs.txt", "logs/(user) notes.log",
    }
    versions = json.loads(files["versions.json"])
    assert versions["version"] and versions["windows"]
    assert versions["program"].startswith("Gremlin-Platforms")
    found = json.loads(files["devices.json"])
    assert [(d["name"], d["kind"], d["connected"]) for d in found["devices"]] == [
        ("pJoy Pro", "Game controller", True), ("vJoy Device", "vJoy device", True),
    ]
    assert found["devices"][0]["id"] == "0F0E0D0C-0000-0000-0000-000000000001"
    modules = {m["name"]: m for m in found["modules"]}
    assert modules["pJoy Pro"]["connected"] is True
    assert modules["Old Pedals"]["connected"] is False
    assert modules["vJoy 1"]["kind"] == "Output module"
    assert "Loaded" in files["logs/system.log"]
    assert "profile" not in " ".join(files)
    assert "not included" in files["README.txt"]
    # Nothing left beside the zip.
    assert sorted(p.name for p in dest.parent.iterdir()) == ["diag.zip"]


def test_the_user_name_is_replaced_everywhere(
    home: pathlib.Path, open_profile: object, tmp_path: pathlib.Path
) -> None:
    dest = tmp_path / "diag.zip"
    assert _save(True, dest)[0]
    files = _read(dest)
    for name, text in files.items():
        assert NAME.lower() not in name.lower(), name
        assert NAME.lower() not in text.lower(), (name, text)
    system = files["logs/system.log"]
    assert "\\Users\\<user>\\Gremlin Platforms\\profiles\\a.xml" in system
    assert "/Users/<user>/Desktop/x.txt" in files["logs/system.log"]
    # JSON's doubled backslashes too.
    assert "Users\\\\<user>\\\\P" in files["settings/configuration.json"]


def test_scrub_leaves_other_words_alone() -> None:
    names = ["Al"]
    text = "C:\\Users\\Al\\x Altitude C:/Users/al\nAl said"
    assert diagnostics.scrub(text, names) == (
        "C:\\Users\\<user>\\x Altitude C:/Users/<user>\nAl said"
    )


def test_the_profile_only_when_ticked(
    home: pathlib.Path, open_profile: object, tmp_path: pathlib.Path
) -> None:
    left_out = tmp_path / "without.zip"
    put_in = tmp_path / "with.zip"
    assert _save(False, left_out)[0]
    assert _save(True, put_in)[0]
    assert not [n for n in _read(left_out) if n.startswith("profile/")]
    files = _read(put_in)
    assert "<profile" in files["profile/(user) flight.xml"]
    assert "\\Users\\<user>\\s.py" in files["profile/(user) flight.xml"]
    assert "not included" not in files["README.txt"]


def test_a_failure_names_the_file_folder_and_reason(
    home: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    missing = tmp_path / "gone" / "diag.zip"
    ok, message = _save(False, missing)
    assert not ok
    assert message == (
        f"Diagnostics not saved. diag.zip could not be written to "
        f"{missing.parent}: the folder does not exist."
    )
    locked = tmp_path / "locked.zip"
    locked.write_bytes(b"old")
    os.chmod(locked, stat.S_IREAD)
    try:
        ok, message = _save(False, locked)
    finally:
        os.chmod(locked, stat.S_IWRITE | stat.S_IREAD)
    assert not ok
    assert message == (
        f"Diagnostics not saved. locked.zip could not be written to "
        f"{tmp_path}: the file is read-only or open in another program."
    )
    assert locked.read_bytes() == b"old"
    assert not list(tmp_path.glob("*.part"))


class _SlowWrite:
    """diagnostics.write_zip held until released, to check the window."""

    def __init__(self) -> None:
        self._real = diagnostics.write_zip
        self.entered = threading.Event()
        self.release = threading.Event()
        self.thread: threading.Thread | None = None

    def __call__(self, plan: diagnostics.Plan, dest: pathlib.Path) -> None:
        self.thread = threading.current_thread()
        self.entered.set()
        # Bounded: a failing test never leaves the worker waiting.
        self.release.wait(WAIT_MS / 1000)
        self._real(plan, dest)


@pytest.fixture
def slow(monkeypatch: pytest.MonkeyPatch) -> Iterator[_SlowWrite]:
    writer = _SlowWrite()
    monkeypatch.setattr(diagnostics, "write_zip", writer)
    yield writer
    writer.release.set()
    if writer.thread is not None:
        writer.thread.join(WAIT_MS / 1000)


def test_written_on_a_worker_while_the_window_stays_responsive(
    qtbot: object, home: pathlib.Path, slow: _SlowWrite, tmp_path: pathlib.Path
) -> None:
    diag = ui_diagnostics.Diagnostics()
    dest = tmp_path / "diag.zip"
    url = QtCore.QUrl.fromLocalFile(str(dest)).toString()
    announced: list[tuple[bool, str, threading.Thread]] = []
    diag.saved.connect(
        lambda ok, msg: announced.append((ok, msg, threading.current_thread()))
    )

    assert diag.saveAsync(url, False)
    assert diag.busy
    assert slow.entered.wait(WAIT_MS / 1000)
    assert slow.thread is not None and slow.thread is not threading.main_thread()
    assert slow.thread.name.startswith(threads.PREFIX)
    # One at a time.
    assert not diag.saveAsync(url, False)
    ticked: list[bool] = []
    QtCore.QTimer.singleShot(0, lambda: ticked.append(True))
    qtbot.waitUntil(lambda: bool(ticked), timeout=WAIT_MS)  # type: ignore[attr-defined]
    assert diag.busy and not announced and not dest.exists()

    with qtbot.waitSignal(diag.saved, timeout=WAIT_MS) as blocker:  # type: ignore[attr-defined]
        slow.release.set()
    assert blocker.args == [True, f"Diagnostics saved to {dest}."]
    assert announced[0][2] is threading.main_thread()
    assert not diag.busy
    assert diag.message == f"Diagnostics saved to {dest}."
    assert "devices.json" in _read(dest)


def test_the_save_dialog_starts_on_the_desktop(home: pathlib.Path) -> None:
    diag = ui_diagnostics.Diagnostics()
    desktop = diagnostics.desktop_folder()
    assert desktop.name == "Desktop"
    assert QtCore.QUrl(diag.desktopUrl).toLocalFile() == desktop.as_posix()
    suggested = pathlib.Path(QtCore.QUrl(diag.defaultFileUrl()).toLocalFile())
    assert suggested.parent == desktop
    assert suggested.name.startswith("Gremlin-Platforms diagnostics ")
    assert suggested.suffix == ".zip"


def test_the_stand_in_modules_answer_the_file_lookup(home: pathlib.Path) -> None:
    """A Home model left by an earlier test may refresh while these tests
    run and look a device's file up through the stand-in modules (CI run
    37853647126: AttributeError 'slug' in module_model._refresh_inplace)."""
    from gremlin.modules import store

    assert store.slug_for("Some stick", "{0F0E0D0C-0000-0000-0000-0000000000AA}")
