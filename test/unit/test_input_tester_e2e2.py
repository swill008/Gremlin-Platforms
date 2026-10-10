# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Input Tester end to end, part 2 (D-02-INPUT-TESTER addendum 2026-10-10):
the restart banner when Gremlin changes HidHide after the tester started,
tester.log (its lines, an access-denied HID open, rotation at 1 MB, nothing
written in plain mode), the HidHide page's "restart it" warning for a game
started before the change, Save Diagnostics with the tester files, and
follow input.

The tester runs as the real input_tester.main() in its own process (fake
dill, no Steam/XInput, a faked HID scan, its restart starter recorded instead
of run); Gremlin runs in this process with HidHide's control device faked
below its public calls. Everything in a temp user folder.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import textwrap
import time
import uuid
import zipfile
from collections.abc import Iterator
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

_REPO = pathlib.Path(__file__).resolve().parents[2]
_TEST_DIR = _REPO / "test"

_LEFT = {
    "name": "Left stick",
    "windows_name": "VKBsim Gladiator EVO L",
    "vid": 0x231D,
    "pid": 0x0201,
    "guid": "{22222222-0000-0000-0000-000000000001}",
    "instance": r"HID\VID_231D&PID_0201\7&LEFT&0&0000",
}
_PEDALS = {
    "name": "Pedals",
    "windows_name": "MFG Crosswind V2",
    "vid": 0x16D0,
    "pid": 0x0A38,
    "guid": "{22222222-0000-0000-0000-000000000003}",
    "instance": r"HID\VID_16D0&PID_0A38\7&PEDALS&0&0000",
}
_STICKS = [_LEFT, _PEDALS]
_TESTER_EXE = r"C:\Program Files\Gremlin Platforms\Gremlin Input Tester.exe"
_GAME = r"D:\StarCitizen\LIVE\Bin64\StarCitizen.exe"
_DENIED_PATH = (
    r"\\?\hid#vid_231d&pid_0201#7&left&0&0000"
    r"#{4d1e55b2-f16f-11cf-88cb-001111000030}"
)
_TIME = r"\d\d:\d\d:\d\d\.\d\d\d"


def _write_json(path: pathlib.Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp-test")
    tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
    os.replace(tmp, path)


# The tester's process. Like test_input_tester_e2e's, plus: the HID scan
# gives one access-denied path; the model's properties are written to
# control/state.json every 100 ms; control/call.json calls a model slot; a
# restart's start is recorded in control/started.json instead of run.
_WRAPPER = textwrap.dedent(
    r'''
    import json, os, pathlib, subprocess, sys, uuid
    repo, test_dir, control = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3])
    sys.path[:0] = [repo, test_dir]
    import vjoy_guard
    vjoy_guard.install()
    import dill
    import fake_hardware

    setup = json.loads((control / "setup.json").read_text(encoding="utf-8"))

    def summary(dev):
        raw = dill.GUID.from_uuid(uuid.UUID(dev["guid"])).ctypes
        out = dill._DeviceSummary()
        out.device_guid = raw
        out.vendor_id = dev["vid"]
        out.product_id = dev["pid"]
        out.joystick_id = 0
        out.name = dev["windows_name"].encode()
        out.axis_count = 3
        out.button_count = 16
        out.hat_count = 1
        for i in range(8):
            out.axis_map[i] = dill._AxisMap(
                linear_index=i + 1, axis_index=i + 1 if i < 3 else 0
            )
        return out

    fake = fake_hardware.FakeDill([summary(d) for d in setup["devices"]])
    dill.DILL._dll = fake
    dill.DILL._dill_initialized = False

    from gremlin.input_tester import devices, steam
    steam.process_names = lambda: []
    steam.steam_running = lambda: False
    devices.xinput_devices = lambda: []
    devices.xinput_state = lambda pad: None

    # HID: the real scan, with Windows faked below it: each listed path's
    # open is refused with error 5, as HidHide refuses a hidden device.
    import ctypes
    class FakeKernel32:
        def CreateFileW(self, *a):
            ctypes.set_last_error(5)
            return ctypes.c_void_p(-1).value
        def CloseHandle(self, handle):
            return True
    devices._hid_libs = lambda: (None, None, FakeKernel32())
    denied = [d["path"] for d in setup.get("denied", [])]
    devices._hid_paths = lambda setup_, hid: list(denied)

    import input_tester
    from PySide6 import QtCore, QtGui
    from gremlin.input_tester import model as tester_model

    # A restart is recorded, never run (the model's starter hook).
    started = control / "started.json"
    tester_model.set_starter(
        lambda args: started.write_text(json.dumps(list(args)), encoding="utf-8")
    )

    holder = {}
    real_build = input_tester.build_engine
    def build(*a, **k):
        engine, model = real_build(*a, **k)
        holder["model"] = model
        return engine, model
    input_tester.build_engine = build

    names = ["staleBanner", "rows", "hidSkipped", "logSources", "logSource",
             "logLines", "logNote", "compareMode", "verdict"]
    def state(model):
        out = {}
        for name in names:
            try:
                value = getattr(model, name)
                json.dumps(value)
            except Exception as error:
                out.setdefault("_errors", {})[name] = repr(error)
                continue
            out[name] = value
        return out

    real_exec = QtGui.QGuiApplication.exec
    def exec_with_control(*args):
        timer = QtCore.QTimer()
        clock = QtCore.QElapsedTimer()
        clock.start()
        def tick():
            model = holder.get("model")
            if model is not None:
                call = control / "call.json"
                if call.exists():
                    name = json.loads(call.read_text(encoding="utf-8"))
                    call.unlink()
                    getattr(model, name)()
                tmp = control / "state.tmp"
                try:
                    tmp.write_text(json.dumps(state(model)), encoding="utf-8")
                    os.replace(tmp, control / "state.json")
                except OSError:
                    pass  # the test is reading it: next tick
            if (control / "quit").exists() or clock.elapsed() > 60000:
                QtGui.QGuiApplication.quit()
        timer.timeout.connect(tick)
        timer.start(100)
        return real_exec()
    QtGui.QGuiApplication.exec = exec_with_control
    QtGui.QGuiApplication.exec_ = exec_with_control

    sys.argv = ["input_tester.py"] + setup["args"]
    code = input_tester.main()
    print("EXIT", code, flush=True)
    sys.exit(code)
    '''
)

_WRAPPER_FILES = {"setup.json", "tester_wrapper.py", "state.json", "state.tmp", "quit",
                  "call.json", "started.json"}


class _Tester:
    """The real tester program in its own process."""

    def __init__(
        self,
        home: pathlib.Path,
        control: pathlib.Path,
        devices: list[dict],
        args: list[str] | None = None,
        denied: list[dict] | None = None,
        temp: pathlib.Path | None = None,
    ) -> None:
        self.gremlin_dir = home / "Gremlin Platforms"
        self.control = control
        control.mkdir(parents=True, exist_ok=True)
        for name in ("quit", "state.json", "call.json", "started.json"):
            (control / name).unlink(missing_ok=True)
        args = ["--gremlin-dir", str(self.gremlin_dir)] if args is None else args
        self.args = args
        _write_json(
            control / "setup.json",
            {"devices": devices, "args": args, "denied": denied or []},
        )
        script = control / "tester_wrapper.py"
        script.write_text(_WRAPPER, encoding="utf-8")
        env = dict(os.environ)
        env.update(
            USERPROFILE=str(home),
            APPDATA=str(home / "AppData" / "Roaming"),
            LOCALAPPDATA=str(home / "AppData" / "Local"),
            QT_QPA_PLATFORM="offscreen",
            QML_DISABLE_DISK_CACHE="1",
            GREMLIN_OFFLINE="1",
            PYTHONUNBUFFERED="1",
            PYTHONDONTWRITEBYTECODE="1",
        )
        if temp is not None:
            env.update(TEMP=str(temp), TMP=str(temp))
        env.pop("GREMLIN_REAL_VJOY", None)
        self.proc = subprocess.Popen(
            [sys.executable, str(script), str(_REPO), str(_TEST_DIR), str(control)],
            cwd=str(control),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self.output = ""

    def state(self, until=lambda s: True, timeout: float = 30.0) -> dict:  # noqa: ANN001
        """The model's properties once until(state) holds."""
        deadline = time.monotonic() + timeout
        last: dict = {}
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                self.stop()
                pytest.fail(f"The tester ended early:\n{self.output}")
            try:
                last = json.loads((self.control / "state.json").read_text("utf-8"))
            except (OSError, ValueError):
                last = {}
            if last and until(last):
                return last
            time.sleep(0.1)
        self.stop()
        pytest.fail(f"Not reached (last state {last}):\n{self.output}")

    def call(self, slot: str) -> None:
        _write_json(self.control / "call.json", slot)  # type: ignore[arg-type]

    def wait_exit(self, timeout: float = 20.0) -> int:
        try:
            self.output, _ = self.proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.stop()
            pytest.fail(f"The tester didn't quit:\n{self.output}")
        return self.proc.returncode

    def stop(self) -> None:
        (self.control / "quit").touch()
        try:
            self.output, _ = self.proc.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.output, _ = self.proc.communicate()
            pytest.fail(f"The tester didn't end:\n{self.output}")


@pytest.fixture
def home(tmp_path: pathlib.Path) -> pathlib.Path:
    folder = tmp_path / "home"
    (folder / "Gremlin Platforms" / "tester").mkdir(parents=True)
    return folder


def _tester_log(home: pathlib.Path) -> pathlib.Path:
    return home / "Gremlin Platforms" / "tester" / "tester.log"


def _wait_text(path: pathlib.Path, want: str, timeout: float = 15.0) -> str:
    deadline = time.monotonic() + timeout
    text = ""
    while time.monotonic() < deadline:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            text = ""
        if want in text:
            return text
        time.sleep(0.1)
    pytest.fail(f"{want!r} not in {path}:\n{text}")


# --- Gremlin's side ------------------------------------------------------------


class _HidHide:
    """HidHide's control device (faked below hidhide_driver's public calls)."""

    def __init__(self) -> None:
        self.cloak = True
        self.inverse = True  # Block list
        self.apps = [_TESTER_EXE]
        self.devices = [_LEFT["instance"]]

    def open(self) -> object:
        from gremlin import hidhide_driver as drv

        return drv._opened("handle", 0)

    def ioctl(
        self, handle: object, code: int, inn: bytes | None = None, out: int = 0
    ) -> tuple[bool, bytes]:
        from gremlin import hidhide_driver as drv

        if code == drv.IOCTL_GET_ACTIVE:
            return True, bytes([self.cloak])
        if code == drv.IOCTL_GET_INVERSE:
            return True, bytes([self.inverse])
        if code == drv.IOCTL_GET_WHITELIST:
            return True, drv._encode_multi_sz(self.apps)
        if code == drv.IOCTL_GET_BLACKLIST:
            return True, drv._encode_multi_sz(self.devices)
        return False, b""


def _gremlin_stick(stick: dict) -> SimpleNamespace:
    import dill

    return SimpleNamespace(
        device_guid=dill.GUID.from_uuid(uuid.UUID(stick["guid"])),
        vendor_id=stick["vid"],
        product_id=stick["pid"],
        name=stick["windows_name"],
        is_virtual=False,
    )


@pytest.fixture
def gremlin_side(
    home: pathlib.Path, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[SimpleNamespace]:
    """Gremlin with two sticks (the left one hidden), Block list with the
    tester on it; launch() starts the real tester program on its folder."""
    from gremlin import (
        device_initialization,
        hidhide_watch,
        input_monitor,
        input_tester_link,
        trace,
        util,
    )
    from gremlin import hidhide_driver as drv
    from gremlin.ui import hidhide as hh
    from gremlin.ui import trace_model

    fake = _HidHide()
    names = {uuid.UUID(s["guid"]): s["name"] for s in _STICKS}
    monkeypatch.setattr(util, "logs_dir", lambda: tmp_path / "logs")
    monkeypatch.setattr(util, "data_folder", lambda: str(home / "Gremlin Platforms"))
    monkeypatch.setattr(drv, "_open_control", fake.open)
    monkeypatch.setattr(drv, "_close", lambda handle: None)
    monkeypatch.setattr(drv, "_ioctl", fake.ioctl)
    monkeypatch.setattr(
        drv,
        "list_hid_devices",
        lambda gaming_only: [
            {
                "instanceId": s["instance"],
                "instanceIds": [s["instance"]],
                "name": s["windows_name"],
            }
            for s in _STICKS
        ],
    )
    monkeypatch.setattr(
        device_initialization,
        "physical_devices",
        lambda: [_gremlin_stick(s) for s in _STICKS],
    )
    monkeypatch.setattr(device_initialization, "vjoy_devices", lambda: [])
    monkeypatch.setattr(input_monitor, "device_name", lambda uid: names[uid])
    monkeypatch.setattr(trace_model, "targets", lambda uid: {})
    monkeypatch.setattr(hh, "_hidhide_managed", lambda: True)
    monkeypatch.setattr(hh, "_load_links", lambda: {})
    monkeypatch.setattr(
        input_tester_link, "_expected_tester_path", lambda: pathlib.Path(_TESTER_EXE)
    )
    monkeypatch.setattr(
        input_tester_link, "tester_path", lambda: pathlib.Path(_TESTER_EXE)
    )

    testers: list[_Tester] = []
    state = SimpleNamespace(hidhide=fake, testers=testers, run=0)

    def start(exe: str, args: list[str]) -> subprocess.Popen:
        state.run += 1
        tester = _Tester(
            home, tmp_path / f"ctl{state.run}", [*_STICKS], args=args
        )
        testers.append(tester)
        return tester.proc

    input_tester_link._reset_for_tests()
    input_tester_link.set_starter(start)
    trace._reset_for_tests()
    if hidhide_watch._on_change in trace._hooks:
        trace._hooks.remove(hidhide_watch._on_change)
    hidhide_watch.stop()
    hidhide_watch._reset()
    drv.take_program_marks()
    trace.set_hidhide(True)  # the watch runs while tracing with the HidHide row
    trace.set_enabled(True)
    yield state
    for tester in testers:
        if tester.proc.poll() is None:
            tester.stop()
    input_tester_link._reset_for_tests()
    if hidhide_watch._on_change in trace._hooks:
        trace._hooks.remove(hidhide_watch._on_change)
    trace.set_enabled(False)
    hidhide_watch.stop()
    hidhide_watch._reset()
    trace.set_hidhide(False)
    trace._reset_for_tests()


def _read_expected(home: pathlib.Path) -> dict:
    path = home / "Gremlin Platforms" / "tester" / "expected.json"
    return json.loads(path.read_text(encoding="utf-8"))


# (1) HidHide changed after the tester started -> banner -> restart -> none ---


def test_hidhide_changed_after_the_tester_started_banner_then_restart_clears_it(
    gremlin_side: SimpleNamespace, home: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    from gremlin import hidhide_watch, input_tester_link

    hidhide_watch.check()
    assert input_tester_link.launch() == ""
    (tester,) = gremlin_side.testers
    first = tester.state(lambda s: "staleBanner" in s)
    assert first["staleBanner"] == ""
    started = datetime.now()
    time.sleep(1.2)  # the change is a whole second after the start

    # Pedals added to the hidden list in HidHide's own window: the watch sees it.
    gremlin_side.hidhide.devices = [_LEFT["instance"], _PEDALS["instance"]]
    hidhide_watch.check()
    expected = _read_expected(home)
    assert "hidhide_changed_at" in expected, expected
    changed_at = datetime.fromisoformat(expected["hidhide_changed_at"])
    assert changed_at > started - timedelta(seconds=1)
    assert changed_at >= started.replace(microsecond=0)
    what = expected.get("hidhide_change") or "settings"

    banner = tester.state(lambda s: bool(s.get("staleBanner")), timeout=15)[
        "staleBanner"
    ]
    assert banner == (
        f"HidHide changed after this tester started ({what}, "
        f"{changed_at.strftime('%H:%M:%S')}). HidHide only checks devices when "
        "they're opened, so what you see may be out of date."
    )
    log = _wait_text(_tester_log(home), "HidHide changed after this tester started")
    assert "HidHide changed after this tester started" in log

    # Restart tester: the same program with the same args, then it quits.
    tester.call("restartTester")
    assert tester.wait_exit() == 0 or "EXIT" in tester.output
    cmd = json.loads((tester.control / "started.json").read_text("utf-8"))
    assert cmd[-2:] == tester.args, cmd
    assert any(
        os.path.normcase(c) in (os.path.normcase(sys.executable),)
        or c.endswith(".py")
        for c in cmd
    ), cmd

    # The new tester (started after the change) has no banner.
    fresh = _Tester(home, tmp_path / "ctl-restart", [*_STICKS], args=cmd[-2:])
    try:
        now = fresh.state(lambda s: "staleBanner" in s and s.get("rows"))
        time.sleep(1.5)  # a file poll or two
        now = fresh.state()
        assert now["staleBanner"] == ""
    finally:
        fresh.stop()


def test_gremlin_page_edit_writes_the_change_and_what_it_was(
    gremlin_side: SimpleNamespace, home: pathlib.Path
) -> None:
    from gremlin import input_tester_link

    assert input_tester_link.launch() == ""
    (tester,) = gremlin_side.testers
    tester.state(lambda s: "staleBanner" in s)
    time.sleep(1.2)
    input_tester_link.hidhide_changed("program list")  # a HidHide page edit
    expected = _read_expected(home)
    assert expected["hidhide_change"] == "program list"
    banner = tester.state(lambda s: bool(s.get("staleBanner")), timeout=15)
    assert banner["staleBanner"].startswith(
        "HidHide changed after this tester started (program list, "
    )


def test_a_change_before_the_tester_started_shows_no_banner(
    gremlin_side: SimpleNamespace, home: pathlib.Path
) -> None:
    from gremlin import input_tester_link

    input_tester_link.hidhide_changed("cloak")
    time.sleep(1.1)
    assert input_tester_link.launch() == ""
    assert _read_expected(home)["hidhide_change"] == "cloak"
    (tester,) = gremlin_side.testers
    tester.state(lambda s: "staleBanner" in s and s.get("rows"))
    time.sleep(1.5)
    assert tester.state()["staleBanner"] == ""


# (2) tester.log --------------------------------------------------------------


def _doc() -> dict:
    return {
        "version": 1,
        "written": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "tester_path": _TESTER_EXE,
        "hidhide": {
            "present": True,
            "cloak": True,
            "mode": "block",
            "tester_on_list": True,
            "apps": [_TESTER_EXE],
        },
        "sticks": [
            {
                "name": s["name"],
                "windows_name": s["windows_name"],
                "vid": s["vid"],
                "pid": s["pid"],
                "guid": s["guid"],
                "instance_ids": [s["instance"]],
                "feeds": [],
                "expect": "hidden" if s is _LEFT else "visible",
            }
            for s in _STICKS
        ],
        "vjoy": [],
        "xbox": [],
    }


def test_tester_log_has_the_start_directinput_and_access_denied_lines(
    home: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    import re

    _write_json(home / "Gremlin Platforms" / "tester" / "expected.json", _doc())
    denied = {"path": _DENIED_PATH, "name": "", "vid": 0x231D, "pid": 0x0201}
    tester = _Tester(home, tmp_path / "ctl", [_PEDALS], denied=[denied])
    try:
        text = _wait_text(_tester_log(home), "access denied (5)")
        text = _wait_text(_tester_log(home), "values read ok")
        state = tester.state(lambda s: s.get("hidSkipped"))
    finally:
        tester.stop()
    lines = text.splitlines()
    assert all(re.match(_TIME + "  ", line) for line in lines if line), lines
    # Start: the exe, compare mode, when Gremlin wrote expected.json; then
    # HidHide's state as Gremlin gave it.
    assert sys.executable in lines[0] and "compared with Gremlin" in lines[0], lines
    assert re.search(r"expected devices \(written \d\d:\d\d:\d\d\)", text), text
    assert "HidHide (from Gremlin): cloak on · Block list" in text
    assert any(
        "DirectInput" in line and _PEDALS["windows_name"] in line and "listed" in line
        for line in lines
    ), text
    assert any(
        "DirectInput" in line and "values read ok" in line for line in lines
    ), text
    hid = [ln for ln in lines if ln[14:].startswith("HID ") and _DENIED_PATH in ln]
    assert hid, text
    refused = "access denied (5): refused, HidHide is hiding it from this program"
    assert refused in hid[0]
    (skip,) = state["hidSkipped"]
    assert skip["denied"] is True
    assert skip["label"] == "left out: access denied (hidden from this program)"
    assert "invalid index" not in text.lower()


def test_tester_log_rotates_at_one_megabyte(
    home: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    _write_json(home / "Gremlin Platforms" / "tester" / "expected.json", _doc())
    log = _tester_log(home)
    old = ("00:00:00.000  old line " + "x" * 90 + "\n") * (1024 * 1024 // 113 + 1)
    log.write_text(old, encoding="utf-8")
    assert log.stat().st_size >= 1024 * 1024 - 200
    tester = _Tester(home, tmp_path / "ctl", [_PEDALS])
    try:
        _wait_text(log, "values read ok")
    finally:
        tester.stop()
    older = log.with_name("tester.log.1")
    assert older.is_file()
    assert "old line" in older.read_text(encoding="utf-8")
    assert "old line" not in log.read_text(encoding="utf-8")
    assert log.stat().st_size < 1024 * 1024
    assert not log.with_name("tester.log.2").exists()


def _snapshot(*folders: pathlib.Path) -> dict[str, tuple[int, int]]:
    out = {}
    for folder in folders:
        for p in folder.rglob("*"):
            # The wrapper's own files, and dill_debug.log: the DirectInput
            # reader DLL's log in its working folder, not a tester file.
            skip = _WRAPPER_FILES | {"dill_debug.log"}
            if p.is_file() and not (p.parent.name.startswith("ctl") and p.name in skip):
                out[str(p)] = (p.stat().st_size, p.stat().st_mtime_ns)
    return out


def test_plain_mode_keeps_the_log_in_memory_and_writes_no_file(
    home: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    temp = tmp_path / "temp"
    temp.mkdir()
    control = tmp_path / "ctl"
    control.mkdir()
    before = _snapshot(home, temp, control)
    tester = _Tester(home, control, [_PEDALS], args=[], temp=temp)
    try:
        tester.call("reloadLog")
        state = tester.state(
            lambda s: s.get("logSource") == "tester" and s.get("logLines")
        )
    finally:
        tester.stop()
    after = _snapshot(home, temp, control)
    assert after == before, sorted(set(after) ^ set(before))
    assert [s["id"] for s in state["logSources"]] == ["tester", "dill"]
    assert any("DirectInput" in line["text"] for line in state["logLines"])
    assert state["logNote"] == "Kept in this window only (not opened from Gremlin)"


# (3) The HidHide page: restart a game started before the change ------------


def test_hidhide_page_warns_about_a_game_started_before_the_change(
    gremlin_side: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, qapp: object
) -> None:
    from gremlin import input_tester_link, process_paths
    from gremlin.ui import hidhide as hh

    game_start = datetime(2026, 10, 10, 9, 15, 0)
    running = [(_GAME, game_start), (r"C:\Windows\explorer.exe", game_start)]
    monkeypatch.setattr(
        process_paths, "running_programs", lambda names=None: list(running)
    )
    model = hh.HidHideModel()
    # The tester counts only when it is on the list (02 S118, like a game).
    model._games = [
        {"name": "Star Citizen", "path": _GAME},
        {"name": "Gremlin Input Tester", "path": _TESTER_EXE},
    ]
    model.setPageOpen(True)
    assert model.staleGameWarnings == []  # no change made or seen yet
    assert model.staleTesterWarning == ""
    model.setPageOpen(False)

    input_tester_link.record_hidhide_change(
        "program list", datetime(2026, 10, 10, 9, 40, 0)
    )
    running.append((_TESTER_EXE, datetime(2026, 10, 10, 9, 20, 0)))
    model.setPageOpen(True)
    assert model.staleGameWarnings == [
        "StarCitizen.exe was started (09:15) before the last HidHide change "
        "(09:40): restart it so the change applies. HidHide only checks "
        "devices when a program opens them."
    ]
    assert model.staleTesterWarning == (
        "Gremlin Input Tester was started (09:20) before the last HidHide "
        "change (09:40): restart it so the change applies. Restart Input "
        "Tester opens a new one; close the old window."
    )
    model.setPageOpen(False)

    # Restart Input Tester starts a fresh one (the old one is never closed).
    assert model.restartInputTester() == ""
    assert len(gremlin_side.testers) == 1

    # Started after the change: nothing to say.
    running[:] = [(_GAME, datetime(2026, 10, 10, 9, 45, 0))]
    model.setPageOpen(True)
    assert model.staleGameWarnings == []
    assert model.staleTesterWarning == ""
    model.setPageOpen(False)


# (4) Save Diagnostics -------------------------------------------------------


def test_save_diagnostics_includes_the_tester_files(
    home: pathlib.Path, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin import diagnostics, util

    data = home / "Gremlin Platforms"
    logs = data / "logs"
    logs.mkdir()
    (logs / "system.log").write_text("hello\n", encoding="utf-8")
    tester = data / "tester"
    files = {
        "tester.log": "04:05:00.000  Gremlin Input Tester started\n",
        "tester.log.1": "04:00:00.000  older\n",
        "expected.json": '{"version": 1}',
        "result.json": '{"verdict": "pass"}',
    }
    for name, text in files.items():
        (tester / name).write_text(text, encoding="utf-8", newline="")
    monkeypatch.setattr(util, "logs_dir", lambda: logs)
    monkeypatch.setattr(util, "userprofile_path", lambda: str(data))
    monkeypatch.setattr(util, "data_folder", lambda: str(data))
    monkeypatch.setattr(diagnostics, "devices", lambda: {})
    monkeypatch.setattr(diagnostics, "versions", lambda: {})
    dest = tmp_path / "diag.zip"
    ok, message = diagnostics.save(diagnostics.collect(False), dest)
    assert ok, message
    with zipfile.ZipFile(dest) as zf:
        names = zf.namelist()
        for name, text in files.items():
            hits = [n for n in names if n.replace("\\", "/").endswith(f"tester/{name}")]
            assert hits, (name, names)
            assert zf.read(hits[0]).decode("utf-8") == text


# (5) Follow input ------------------------------------------------------------


def test_moving_a_stick_on_another_device_selects_it_but_not_in_all_devices_view(
    qapp: object,
) -> None:
    from gremlin.input_tester import devices
    from gremlin.input_tester.model import InputTesterModel

    def dev(key: str, name: str) -> devices.SeenDevice:
        return devices.SeenDevice(
            key=key, kind="directinput", name=name, vid=1, pid=2,
            guid=key[3:], axes=2, buttons=4, hats=1, axis_ids=[1, 2],
        )

    a = dev("di:{A0000000-0000-0000-0000-000000000001}", "Stick A")
    b = dev("di:{B0000000-0000-0000-0000-000000000002}", "Stick B")
    values = {
        a.key: devices.LiveValues([0.0, 0.0], [False] * 4, [-1]),
        b.key: devices.LiveValues([0.0, 0.0], [False] * 4, [-1]),
    }
    now = [0.0]
    model = InputTesterModel(
        None,
        snapshot=lambda: [a, b],
        poll=lambda d: values[d.key],
        hid_list=lambda: [],
        steam_running=lambda: False,
        clock=lambda: now[0],
        start_timers=False,
    )
    followed: list[str] = []
    model.inputFollowed.connect(followed.append)
    assert model.followInput is True
    model.selectedKey = a.key
    model.tick()

    def move(key: str, x: float, at: float) -> None:
        now[0] = at
        old = values[key]
        values[key] = devices.LiveValues([x, old.axes[1]], old.buttons, old.hats)
        model.tick()

    move(b.key, 0.03, 1.0)  # jitter: stays on A
    assert model.selectedKey == a.key
    move(b.key, 0.5, 2.0)  # a real move on B
    assert model.selectedKey == b.key
    assert followed == [b.key]
    move(a.key, 0.5, 2.5)  # within 1 s of the switch: held on B
    assert model.selectedKey == b.key

    # The All devices view: nothing switches.
    model.allDevicesShown = True
    move(a.key, 0.9, 5.0)
    assert model.selectedKey == b.key
    model.allDevicesShown = False
    move(a.key, 0.0, 8.0)
    assert model.selectedKey == a.key
