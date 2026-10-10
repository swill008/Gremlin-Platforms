# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Input Tester end to end (D-02-INPUT-TESTER), across both programs.

Gremlin writes tester/expected.json for a known setup; the real tester
program (input_tester.py's main, off-screen, in its own process, with a fake
dill and no Steam/XInput/HID of the PC) reads it, shows Pass/Fail and writes
result.json; Gremlin reads that back and, tracing with the HidHide row, puts
"Input Tester: Fail" in the trace. Everything runs in a temp user folder;
HidHide's control device is faked below its public calls; no real driver,
no real process other than the tester the test starts itself.
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
from collections.abc import Iterator
from types import SimpleNamespace

import pytest

_REPO = pathlib.Path(__file__).resolve().parents[2]
_TEST_DIR = _REPO / "test"

# Three sticks: two on HidHide's hidden list, one not.
_LEFT = {
    "name": "Left stick",
    "windows_name": "VKBsim Gladiator EVO L",
    "vid": 0x231D,
    "pid": 0x0201,
    "guid": "{11111111-0000-0000-0000-000000000001}",
    "instance": r"HID\VID_231D&PID_0201\7&LEFT&0&0000",
}
_RIGHT = {
    "name": "Right stick",
    "windows_name": "VKBsim Gladiator EVO R",
    "vid": 0x231D,
    "pid": 0x0200,
    "guid": "{11111111-0000-0000-0000-000000000002}",
    "instance": r"HID\VID_231D&PID_0200\7&RIGHT&0&0000",
}
_PEDALS = {
    "name": "Pedals",
    "windows_name": "MFG Crosswind V2",
    "vid": 0x16D0,
    "pid": 0x0A38,
    "guid": "{11111111-0000-0000-0000-000000000003}",
    "instance": r"HID\VID_16D0&PID_0A38\7&PEDALS&0&0000",
}
_VJOY1 = {
    "name": "vJoy Device",
    "windows_name": "vJoy Device",
    "vid": 0x1234,
    "pid": 0xBEAD,
    "guid": "{11111111-0000-0000-0000-0000000000F1}",
}
_STICKS = [_LEFT, _RIGHT, _PEDALS]
_HIDDEN = [_LEFT, _RIGHT]
_TESTER_EXE = r"C:\Program Files\Gremlin Platforms\Gremlin Input Tester.exe"


def _stick_entry(stick: dict, expect: str) -> dict:
    return {
        "name": stick["name"],
        "windows_name": stick["windows_name"],
        "vid": stick["vid"],
        "pid": stick["pid"],
        "guid": stick["guid"],
        "instance_ids": [stick.get("instance", "")],
        "feeds": ["vJoy 1"] if stick is _RIGHT else [],
        "expect": expect,
    }


def _expected(
    cloak: bool = True,
    mode: str = "block",
    apps: list[str] | None = None,
) -> dict:
    """expected.json as Gremlin writes it (contract item 5) for the setup."""
    apps = [_TESTER_EXE] if apps is None else apps
    on_list = _TESTER_EXE in apps
    hides = cloak and (on_list if mode == "block" else not on_list)
    return {
        "version": 1,
        "written": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "tester_path": _TESTER_EXE,
        "hidhide": {
            "present": True,
            "cloak": cloak,
            "mode": mode,
            "tester_on_list": on_list,
            "apps": apps,
        },
        "sticks": [
            _stick_entry(s, "hidden" if hides and s in _HIDDEN else "visible")
            for s in _STICKS
        ],
        "vjoy": [
            {
                "id": 1,
                "guid": _VJOY1["guid"],
                "fed_by": ["Right stick"],
                "used": True,
                "expect": "visible",
            }
        ],
        "xbox": [],
    }


def _write_json(path: pathlib.Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp-test")
    tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
    os.replace(tmp, path)


# The tester's own process: fake dill (the sticks the test says this
# process sees), no Steam unless asked, no XInput pads or HID list of this PC.
# It quits when the control file says so (or after 60 s).
_WRAPPER = textwrap.dedent(
    r'''
    import json, os, pathlib, sys, uuid
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
    steam.process_names = lambda: ["steam.exe"] if setup.get("steam") else []
    steam.steam_running = lambda: bool(setup.get("steam"))
    devices.xinput_devices = lambda: []
    devices.xinput_state = lambda pad: None
    devices.hid_devices = lambda: []
    import input_tester

    from PySide6 import QtCore, QtGui
    real_exec = QtGui.QGuiApplication.exec

    def exec_with_control(*args):
        timer = QtCore.QTimer()
        started = QtCore.QElapsedTimer()
        started.start()
        def tick():
            if (control / "quit").exists() or started.elapsed() > 60000:
                loaded = sorted(m for m in sys.modules if m.startswith("gremlin"))
                print("MODULES " + json.dumps(loaded), flush=True)
                QtGui.QGuiApplication.quit()
        timer.timeout.connect(tick)
        timer.start(100)
        return real_exec()
    QtGui.QGuiApplication.exec = exec_with_control
    QtGui.QGuiApplication.exec_ = exec_with_control

    sys.argv = ["input_tester.py"] + setup["args"]
    sys.exit(input_tester.main())
    '''
)


class _Tester:
    """The tester program running on a Gremlin folder, in its own process."""

    def __init__(
        self,
        home: pathlib.Path,
        control: pathlib.Path,
        devices: list[dict],
        steam: bool = False,
        args: list[str] | None = None,
    ) -> None:
        self.gremlin_dir = home / "Gremlin Platforms"
        self.result = self.gremlin_dir / "tester" / "result.json"
        self.control = control
        control.mkdir(parents=True, exist_ok=True)
        (control / "quit").unlink(missing_ok=True)
        args = ["--gremlin-dir", str(self.gremlin_dir)] if args is None else args
        _write_json(
            control / "setup.json",
            {"devices": devices, "steam": steam, "args": args},
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
        )
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

    def wait_result(self, verdict: str, timeout: float = 30.0) -> dict:
        """result.json once it holds this verdict."""
        deadline = time.monotonic() + timeout
        last: dict | None = None
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                self.stop()
                pytest.fail(f"The tester ended early:\n{self.output}")
            try:
                last = json.loads(self.result.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                last = None
            if last and last.get("verdict") == verdict:
                return last
            time.sleep(0.1)
        self.stop()
        pytest.fail(f"No {verdict!r} result (last {last}):\n{self.output}")

    def stop(self) -> list[str]:
        """Ends the tester; the gremlin modules it had loaded."""
        (self.control / "quit").touch()
        try:
            self.output, _ = self.proc.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.output, _ = self.proc.communicate()
            pytest.fail(f"The tester didn't end:\n{self.output}")
        for line in self.output.splitlines():
            if line.startswith("MODULES "):
                return json.loads(line[len("MODULES ") :])
        return []


@pytest.fixture
def home(tmp_path: pathlib.Path) -> pathlib.Path:
    folder = tmp_path / "home"
    (folder / "Gremlin Platforms" / "tester").mkdir(parents=True)
    return folder


def _seen(*sticks: dict) -> list[dict]:
    return [*sticks, _VJOY1]


def _row(result: dict, name: str) -> dict:
    rows = [r for r in result["rows"] if r["name"] == name]
    assert rows, f"no row {name!r} in {result['rows']}"
    return rows[0]


# --- the tester against Gremlin's expected.json ---------------------------


def test_a_should_be_hidden_stick_the_tester_sees_is_a_fail(
    home: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    _write_json(home / "Gremlin Platforms" / "tester" / "expected.json", _expected())
    tester = _Tester(home, tmp_path / "ctl", _seen(_RIGHT, _PEDALS))
    result = tester.wait_result("fail")
    tester.stop()
    assert _row(result, "Right stick")["verdict"] == "bad"
    assert _row(result, "Right stick")["seen"] is True
    assert _row(result, "Left stick")["verdict"] == "ok"  # hidden, not seen
    assert _row(result, "Left stick")["seen"] is False
    assert _row(result, "Pedals")["verdict"] == "ok"  # visible, seen
    assert "should be hidden" in result["summary"]


def test_hidden_sticks_the_tester_does_not_see_are_a_pass(
    home: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    _write_json(home / "Gremlin Platforms" / "tester" / "expected.json", _expected())
    tester = _Tester(home, tmp_path / "ctl", _seen(_PEDALS))
    result = tester.wait_result("pass")
    tester.stop()
    sticks = [r for r in result["rows"] if r["kind"] == "stick"]
    assert {r["name"]: r["verdict"] for r in sticks} == {
        "Left stick": "ok",
        "Right stick": "ok",
        "Pedals": "ok",
    }


def test_cloak_turned_off_while_the_tester_runs_flips_it_to_pass(
    home: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    expected = home / "Gremlin Platforms" / "tester" / "expected.json"
    _write_json(expected, _expected())
    tester = _Tester(home, tmp_path / "ctl", _seen(_LEFT, _RIGHT, _PEDALS))
    tester.wait_result("fail")
    time.sleep(1.1)  # a newer mtime than the first file
    _write_json(expected, _expected(cloak=False))
    result = tester.wait_result("pass", timeout=15)
    tester.stop()
    assert _row(result, "Right stick")["expect"] == "visible"
    assert _row(result, "Right stick")["verdict"] == "ok"


# --- Steam -----------------------------------------------------------------


def test_steam_running_and_not_on_the_block_list_is_said(
    home: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    _write_json(home / "Gremlin Platforms" / "tester" / "expected.json", _expected())
    tester = _Tester(home, tmp_path / "ctl", _seen(_PEDALS), steam=True)
    result = tester.wait_result("pass")  # Steam is a warning, not a fail
    tester.stop()
    assert result["steam"] == {"running": True, "on_list": False}


def test_steam_on_the_block_list_or_not_running_is_quiet(
    home: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    steam_exe = r"C:\Program Files (x86)\Steam\steam.exe"
    _write_json(
        home / "Gremlin Platforms" / "tester" / "expected.json",
        _expected(apps=[_TESTER_EXE, steam_exe]),
    )
    tester = _Tester(home, tmp_path / "ctl", _seen(_PEDALS), steam=True)
    result = tester.wait_result("pass")
    tester.stop()
    assert result["steam"] == {"running": True, "on_list": True}


def test_the_steam_line_in_the_tester_window() -> None:
    """The amber line itself: Block list without Steam on it."""
    from gremlin.input_tester import compare

    assert compare.compare(_expected(), [], True).steam_warning == (
        "Steam is running and can see your sticks: Steam Input may pass them to games."
    )
    assert compare.compare(_expected(), [], False).steam_warning == ""
    steam_exe = r"C:\Program Files (x86)\Steam\steam.exe"
    listed = _expected(apps=[_TESTER_EXE, steam_exe])
    assert compare.compare(listed, [], True).steam_warning == ""


# --- what the tester leaves behind -------------------------------------------


def _snapshot(folder: pathlib.Path) -> dict[str, tuple[int, int]]:
    return {
        str(p.relative_to(folder)): (p.stat().st_size, p.stat().st_mtime_ns)
        for p in folder.rglob("*")
        if p.is_file()
    }


def test_the_tester_writes_only_result_json_and_never_loads_gremlin_config(
    home: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    _write_json(home / "Gremlin Platforms" / "tester" / "expected.json", _expected())
    before = _snapshot(home)
    tester = _Tester(home, tmp_path / "ctl", _seen(_RIGHT, _PEDALS))
    tester.wait_result("fail")
    modules = tester.stop()
    after = _snapshot(home)
    changed = sorted(k for k in after if before.get(k) != after[k])
    gone = sorted(k for k in before if k not in after)
    # Addendum 2026-10-10 item 2: result.json and tester.log only.
    assert changed == [
        str(pathlib.Path("Gremlin Platforms", "tester", "result.json")),
        str(pathlib.Path("Gremlin Platforms", "tester", "tester.log")),
    ]
    assert gone == []
    assert modules, f"the tester didn't report its modules:\n{tester.output}"
    assert "gremlin.input_tester" in modules
    assert "gremlin.config" not in modules


def test_the_tester_opened_on_its_own_has_no_verdict(
    home: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    before = _snapshot(home)
    tester = _Tester(home, tmp_path / "ctl", _seen(_RIGHT), args=[])
    time.sleep(3)
    assert tester.proc.poll() is None, "the plain tester ended on its own"
    tester.stop()
    assert _snapshot(home) == before  # no compare, nothing written


# --- Gremlin and the tester together ------------------------------------------


class _HidHide:
    """HidHide's control device (faked below hidhide_driver's public calls)."""

    def __init__(self) -> None:
        self.cloak = True
        self.inverse = True  # Block list
        self.apps = [_TESTER_EXE]
        self.devices = [s["instance"] for s in _HIDDEN]

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
        return False, b""  # the tester flow never writes HidHide


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
    """Gremlin with the setup: 3 sticks, 2 hidden, Block list with the tester
    on it, cloak on, vJoy 1 fed by the right stick; tracing with the HidHide
    row. launch() starts the real tester program on the Gremlin folder."""
    import dill
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
    monkeypatch.setattr(
        device_initialization,
        "vjoy_devices",
        lambda: [
            SimpleNamespace(
                device_guid=dill.GUID.from_uuid(uuid.UUID(_VJOY1["guid"])),
                vjoy_id=1,
                vendor_id=0x1234,
                product_id=0xBEAD,
                name="vJoy Device",
                is_virtual=True,
            )
        ],
    )
    monkeypatch.setattr(input_monitor, "device_name", lambda uid: names[uid])
    right = uuid.UUID(_RIGHT["guid"])
    # The profile: the right stick's X axis goes to vJoy 1.
    monkeypatch.setattr(
        trace_model,
        "targets",
        lambda uid: {("axis", 1): "→ vJoy 1 X"} if uid == right else {},
    )
    monkeypatch.setattr(hh, "_hidhide_managed", lambda: True)
    monkeypatch.setattr(hh, "_load_links", lambda: {})
    monkeypatch.setattr(
        input_tester_link, "_expected_tester_path", lambda: pathlib.Path(_TESTER_EXE)
    )
    monkeypatch.setattr(
        input_tester_link, "tester_path", lambda: pathlib.Path(_TESTER_EXE)
    )

    testers: list[_Tester] = []
    state = SimpleNamespace(hidhide=fake, sees=[_PEDALS], testers=testers)

    def start(exe: str, args: list[str]) -> subprocess.Popen:
        tester = _Tester(home, tmp_path / "ctl", _seen(*state.sees), args=args)
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
    trace.set_hidhide(True)
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


def _tester_lines(want: str, timeout: float = 10.0) -> list[tuple[str, bool]]:
    """The trace's HIDHIDE "Input Tester: …" lines, once one holds want."""
    from gremlin import trace

    deadline = time.monotonic() + timeout
    while True:
        found = [
            (line[3], line[4])
            for line in trace.lines()
            if line[2] == trace.HIDHIDE and line[3].startswith("Input Tester:")
        ]
        if any(want in text for text, _ in found) or time.monotonic() > deadline:
            return found
        time.sleep(0.1)


def _read_expected(home: pathlib.Path) -> dict:
    path = home / "Gremlin Platforms" / "tester" / "expected.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_gremlin_expects_the_hidden_sticks_and_the_tester_fails_on_one_it_sees(
    gremlin_side: SimpleNamespace, home: pathlib.Path
) -> None:
    from gremlin import hidhide_watch, input_tester_link

    gremlin_side.sees = [_RIGHT, _PEDALS]  # the right stick gets through
    hidhide_watch.check()
    assert input_tester_link.launch() == ""
    expected = _read_expected(home)
    assert expected["hidhide"]["mode"] == "block"
    assert expected["hidhide"]["cloak"] is True
    assert expected["hidhide"]["tester_on_list"] is True
    assert {s["name"]: s["expect"] for s in expected["sticks"]} == {
        "Left stick": "hidden",
        "Right stick": "hidden",
        "Pedals": "visible",
    }
    right = next(s for s in expected["sticks"] if s["name"] == "Right stick")
    assert right["feeds"] == ["vJoy 1"]
    assert expected["vjoy"][0]["fed_by"] == ["Right stick"]

    (tester,) = gremlin_side.testers
    result = tester.wait_result("fail")
    assert _row(result, "Right stick")["verdict"] == "bad"
    assert _row(result, "Left stick")["verdict"] == "ok"
    last = input_tester_link.last_result()
    assert last is not None and last["verdict"] == "fail"
    lines = _tester_lines("Fail")
    assert (f"Input Tester: Fail · {result['summary']}", True) in lines


def test_cloak_turned_off_in_hidhide_while_the_tester_runs_turns_it_to_pass(
    gremlin_side: SimpleNamespace, home: pathlib.Path
) -> None:
    from gremlin import hidhide_watch, input_tester_link

    gremlin_side.sees = [_LEFT, _RIGHT, _PEDALS]
    hidhide_watch.check()
    assert input_tester_link.launch() == ""
    (tester,) = gremlin_side.testers
    tester.wait_result("fail")
    time.sleep(1.1)  # expected.json's next write gets a newer mtime
    gremlin_side.hidhide.cloak = False  # turned off in the HidHide window
    hidhide_watch.check()  # the 5 s watch sees it
    expected = _read_expected(home)
    assert expected["hidhide"]["cloak"] is False
    assert {s["expect"] for s in expected["sticks"]} == {"visible"}
    result = tester.wait_result("pass", timeout=15)
    assert _row(result, "Right stick")["expect"] == "visible"
    lines = _tester_lines("Pass")
    assert any(text.startswith("Input Tester: Pass") and not w for text, w in lines)
