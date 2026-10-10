# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""D-02-RESET-DEVICES end to end: the real program off-screen (stand-in home
folder, fake hardware, a fake HidHide driver, a fake USB device list and a
fake device_reset runner), the HidHide page opened from the Tools menu and
the Reset Devices window driven by real mouse clicks: exactly the hidden
devices ticked, vJoy and Xbox pads never listed, the warning and the
running-game line, declined permission (nothing reset), then a reset with a
result per row, system.log and Trace HIDHIDE lines, a running tester's
expected.json written again (no HidHide change recorded). The real runner
(pnputil through an elevated process) is never reached: it is replaced by
a tripwire before anything starts.

This file runs itself as the script part:
    python test/unit/test_device_reset_e2e.py <work folder>
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys

import pytest

_HERE = pathlib.Path(__file__).parent

LIVE = r"D:\StarCitizen\LIVE\Bin64\StarCitizen.exe"
TESTER_NAME = "Gremlin Input Tester.exe"

# The fake USB game devices (HidHide gaming-only list).
EVO_R = r"USB\VID_231D&PID_0200\9&AAC4F3F&0&2"
EVO_L = r"USB\VID_231D&PID_3201\9&1D65FFE4&0&3"
THQ = r"USB\VID_231D&PID_2234\7&2BDEAFD4&0&1"
GONE = r"USB\VID_1551&PID_0001\5&C0FFEE&0&4"
PEDALS = r"USB\VID_1209&PID_5678\6&BEEF&0&5"
VJOY = r"ROOT\HIDCLASS\0000"
XBOX = r"USB\VID_045E&PID_028E\1&2D595CA7&0&01"

HID = {
    EVO_R: r"HID\VID_231D&PID_0200\8&AAA&0&0000",
    EVO_L: r"HID\VID_231D&PID_3201\8&BBB&0&0000",
    THQ: r"HID\VID_231D&PID_2234&MI_00\8&CCC&0&0000",
    GONE: r"HID\VID_1551&PID_0001\8&DDD&0&0000",
    PEDALS: r"HID\VID_1209&PID_5678\8&EEE&0&0000",
    VJOY: r"HID\HIDCLASS&COL01\1&2D595CA7&0&0000",
    XBOX: r"HID\VID_045E&PID_028E&IG_00\8&FFF&0&0000",
}
HIDDEN_USB = [EVO_R, EVO_L, THQ, GONE]
# pnputil answers per device: ok, ok, 3010; GONE is absent before the reset
# (never sent to the runner: "not found").
CODES = {EVO_R: 0, EVO_L: 0, THQ: 3010}


# Object names in qml/DialogResetDevices.qml and qml/DialogHardwareHide.qml.
PAGE_BUTTON = "hidHideResetDevices"
WIN_TITLE = "Reset Devices"
N_WARNING = "resetDevicesWarning"
N_GAME = "resetDevicesGame"
N_TICK = "resetDevicesTick"
N_NAME = "resetDevicesName"
N_USB = "resetDevicesUsbId"
N_RESULT = "resetDevicesResult"
N_COUNT = "resetDevicesCount"
N_CANCEL = "resetDevicesCancel"
N_RESET = "resetDevicesReset"
N_CLOSE = "resetDevicesClose"


# --- the pytest part --------------------------------------------------------------


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("reset_home")
    (home / "Gremlin Platforms").mkdir()
    work = tmp_path_factory.mktemp("reset_work")
    proc = subprocess.run(
        [sys.executable, str(pathlib.Path(__file__)), str(work)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
        cwd=str(_HERE.parents[1]),
        env={
            **os.environ,
            "USERPROFILE": str(home),
            "QT_QPA_PLATFORM": "offscreen",
            "PYTHONUNBUFFERED": "1",
        },
    )
    results: dict = {"log": proc.stdout[-4000:] + proc.stderr[-4000:]}
    for line in proc.stdout.splitlines():
        if line.startswith("RESULT "):
            _tag, name, value = line.split(" ", 2)
            results[name] = json.loads(value)
    assert "done" in proc.stdout, results["log"]
    assert results.get("open") is True, results["log"]
    return results


def _ids(rows: list[dict]) -> set[str]:
    return {r["usb"].upper() for r in rows}


def _row(rows: list[dict], usb: str) -> dict:
    found = [r for r in rows if usb.upper() in r["usb"].upper()]
    assert len(found) == 1, (usb, rows)
    return found[0]


def test_the_page_button_opens_the_reset_devices_window(run: dict) -> None:
    assert run["window"] is True, run["log"]


def test_vjoy_and_xbox_pads_are_never_listed(run: dict) -> None:
    rows = run["first"]["rows"]
    listed = _ids(rows)
    assert VJOY.upper() not in listed and XBOX.upper() not in listed, rows
    assert {u.upper() for u in [*HIDDEN_USB, PEDALS]} <= listed, rows


def test_exactly_the_hidden_devices_are_ticked(run: dict) -> None:
    for state in (run["first"], run["second"]):
        ticked = {r["usb"].upper() for r in state["rows"] if r["ticked"]}
        assert ticked == {u.upper() for u in HIDDEN_USB}, state["rows"]
        assert state["count"] == ["4 of 5 plugged-in devices ticked"]
        assert state["reset"] == ["Reset 4 Devices"]


def test_the_warning_and_the_running_game_line(run: dict) -> None:
    first = run["first"]
    # The wording may still change (the user decides): the window must show the
    # model's text exactly, and that text must keep the approved points.
    from gremlin.ui.device_reset_model import WARNING as shown_text

    assert first["warning"] == [shown_text], first["warning"]
    for point in (
        "The ticked USB devices will be reset.",
        "Center your sticks before you press Reset",
        "keeps its axes where they were and releases its buttons.",
    ):
        assert point in shown_text, shown_text
    assert first["game"] == [
        "StarCitizen.exe is running and will lose these devices for a moment."
    ]


def test_declined_permission_resets_nothing(run: dict) -> None:
    res = run["declined"]
    assert res["clicked"] is True
    assert res["runnerCalls"] == 1 and res["reset"] == []
    for usb in (EVO_R, EVO_L, THQ):
        assert _row(res["rows"], usb)["result"] == "permission declined"
    assert _row(res["rows"], GONE)["result"] == "not found"
    assert _row(res["rows"], PEDALS)["result"] in ("", "—")


def test_reset_shows_each_rows_result(run: dict) -> None:
    res = run["reset"]
    assert res["clicked"] is True
    assert sorted(i.upper() for i in res["runnerIds"]) == sorted(
        u.upper() for u in (EVO_R, EVO_L, THQ)
    )
    for usb in (EVO_R, EVO_L):
        text = _row(res["rows"], usb)["result"]
        assert re.fullmatch(r"reset ✓ · back after \d+\.\d s", text), text
    assert _row(res["rows"], THQ)["result"] == "needs a Windows restart"
    assert _row(res["rows"], GONE)["result"] == "not found"
    assert _row(res["rows"], PEDALS)["result"] in ("", "—")
    assert res["close"] is True  # the Reset button became Close


def test_system_log_has_one_line_per_device(run: dict) -> None:
    lines = run["reset"]["syslog"]
    for usb, want in (
        (EVO_R, "reset"), (EVO_L, "reset"), (THQ, "needs a Windows restart"),
        (GONE, "not found"),
    ):
        mine = [ln for ln in lines if usb.upper() in ln["msg"].upper()]
        assert len(mine) == 1, (usb, lines)
        assert mine[0]["level"] == "INFO" and want in mine[0]["msg"], mine


def test_trace_has_a_hidhide_line_per_device(run: dict) -> None:
    lines = run["reset"]["trace"]
    for usb, want in (
        (EVO_R, "reset ✓"), (EVO_L, "reset ✓"), (THQ, "needs a Windows restart"),
        (GONE, "not found"),
    ):
        mine = [t for t in lines if usb.upper() in t.upper() and want in t]
        assert len(mine) == 1, (usb, lines)
    declined = [t for t in run["declined"]["trace"] if "permission declined" in t]
    assert len(declined) == 3, run["declined"]["trace"]


def test_a_running_testers_expected_json_is_written_again(run: dict) -> None:
    res = run["reset"]
    assert res["expected"] is True
    assert res["changeBefore"] == res["changeAfter"]  # not a HidHide change


def test_the_real_runner_is_never_reached(run: dict) -> None:
    assert run["realRunner"] == 0


def test_the_real_runner_is_not_reached_in_this_test_process() -> None:
    from gremlin import device_reset

    calls: list = []

    def fake(ids: list[str]) -> dict[str, int]:
        calls.append(list(ids))
        return {i: 0 for i in ids}

    real = _real_runner(device_reset)
    tripped: list = []
    original = getattr(device_reset, real)
    setattr(device_reset, real, lambda *a, **k: tripped.append(a) or {})
    device_reset.set_runner(fake)
    try:
        if hasattr(device_reset, "set_presence"):
            device_reset.set_presence(lambda _id: True)
        out = device_reset.reset([EVO_R])
    finally:
        device_reset.set_runner(None)
        if hasattr(device_reset, "set_presence"):
            device_reset.set_presence(None)
        setattr(device_reset, real, original)
    assert calls == [[EVO_R]] and tripped == []
    assert [r.outcome for r in out] == ["ok"]


def _real_runner(module: object) -> str:
    """The name of the module's real (elevated pnputil) runner."""
    if callable(getattr(module, "_real_runner", None)):
        return "_real_runner"
    raise AssertionError("device_reset has no _real_runner to guard")


# --- the script part -------------------------------------------------------------


def _main() -> None:  # noqa: C901, PLR0915
    import importlib.util
    import logging
    import time

    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    root = pathlib.Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root))
    spec = importlib.util.spec_from_file_location(
        "fake_hardware", root / "test" / "fake_hardware.py"
    )
    assert spec and spec.loader
    fake_hardware = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fake_hardware)
    fake_hardware.install()

    import gremlin.ui.update_model as um

    um.UpdateModel.startup = lambda self, *a, **k: None

    import shiboken6
    from PySide6 import QtCore, QtQuick, QtTest

    from gremlin import device_reset, hidhide_driver, process_paths, trace
    from gremlin import input_tester_link as link
    from gremlin.ui import hidhide as hh

    work = pathlib.Path(sys.argv[1])
    left = QtCore.Qt.MouseButton.LeftButton
    nomod = QtCore.Qt.KeyboardModifier.NoModifier

    def result(name: str, value: object) -> None:
        print(f"RESULT {name} {json.dumps(value)}", flush=True)

    # The real runner: a tripwire, before anything can reach it.
    real_calls: list = []
    real_name = _real_runner(device_reset)
    setattr(device_reset, real_name, lambda *a, **k: real_calls.append(a) or {})

    # A fake HidHide driver: never the real one.
    class Driver:
        active = True
        inverse = True
        blacklist = [HID[u] for u in HIDDEN_USB]
        whitelist: list[str] = []

    drv = Driver()

    def _set(name: str, value: object) -> bool:
        setattr(drv, name, value)
        return True

    hid_rows = []
    for usb, hid in HID.items():
        vid_pid = re.search(r"VID_(\w{4})&PID_(\w{4})", hid)
        vid, pid = (vid_pid.group(1), vid_pid.group(2)) if vid_pid else ("1234", "BEAD")
        hid_rows.append({
            "hid_id": hid,
            "usb_id": usb,
            "bus_id": usb,
            "bus_desc": (
                "Virtual Gamepad Emulation Bus" if usb == XBOX
                else "vJoy Device" if usb == VJOY else "USB Input Device"
            ),
            "name": {
                EVO_R: "VKBsim Gladiator EVO R", EVO_L: "VKBsim Gladiator EVO OT L",
                THQ: "VKBSim NXT SEM THQ", GONE: "MFG Crosswind",
                PEDALS: "Example pedals", VJOY: "vJoy Device",
                XBOX: "Controller (XBOX 360 For Windows)",
            }[usb],
            "windows_name": "USB Input Device",
            "vid": int(vid, 16),
            "pid": int(pid, 16),
        })
    hh_rows = [
        {"instanceId": r["hid_id"], "instanceIds": [r["hid_id"]], "name": r["name"]}
        for r in hid_rows
    ]
    fakes = {
        "driver_present": lambda: True,
        "driver_version": lambda: "1.5",
        "get_active": lambda: drv.active,
        "set_active": lambda on: _set("active", on),
        "get_inverse": lambda: drv.inverse,
        "set_inverse": lambda on: _set("inverse", on),
        "get_blacklist": lambda: list(drv.blacklist),
        "set_blacklist": lambda ids: _set("blacklist", list(ids)),
        "get_whitelist": lambda: list(drv.whitelist),
        "set_whitelist": lambda paths: _set("whitelist", list(paths)),
        "list_hid_devices": lambda gaming_only=False: list(hh_rows),
        "read_state": lambda: None,
        "_full_image_name": lambda path: path,
        "_gremlin_exe": lambda: r"C:\Gremlin\joystick_gremlin.exe",
    }
    for name, fake in fakes.items():
        for mod in (hidhide_driver, hh):
            if hasattr(mod, name):
                setattr(mod, name, fake)

    device_reset.set_enumerator(lambda: [dict(r) for r in hid_rows])
    reset_at: list[float] = []

    def present(instance_id: str) -> bool:
        if instance_id.upper() in (GONE.upper(), HID[GONE].upper()):
            return False  # unplugged after the window opened: "not found"
        return not reset_at or time.monotonic() > reset_at[-1] + 0.3

    device_reset.set_presence(present)

    runner_calls: list[list[str]] = []
    reset_ids: list[str] = []
    decline = [True]

    def runner(ids: list[str]) -> dict[str, int]:
        runner_calls.append(list(ids))
        if decline[0]:
            raise device_reset.Cancelled()
        reset_ids.extend(ids)
        reset_at.append(time.monotonic())
        codes = {u.upper(): c for u, c in CODES.items()}
        return {i: codes.get(i.upper(), 1) for i in ids}

    device_reset.set_runner(runner)

    # The game is running; the tester too.
    now = __import__("datetime").datetime.now()
    programs = [(LIVE, now), (r"C:\Windows\explorer.exe", now)]
    process_paths.running_programs = lambda *_a: list(programs)
    process_paths.running_images = lambda: [p for p, _s in programs]
    link.tester_path = lambda: work / "new" / TESTER_NAME  # type: ignore[assignment]
    link.running = lambda: True  # type: ignore[assignment]

    hh._ensure_options()
    hh._save_games([{"name": "Star Citizen", "path": LIVE}])
    hh._mark_managed()
    hh._save_list_mode(True)

    # system.log lines, as the "system" logger gets them.
    syslog: list[dict] = []

    class Grab(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            syslog.append({"level": record.levelname, "msg": record.getMessage()})

    import joystick_gremlin

    def wait_until(check, timeout: float = 10.0):  # noqa: ANN001, ANN202
        deadline = time.monotonic() + timeout
        while True:
            value = check()
            if value or time.monotonic() > deadline:
                return value
            QtTest.QTest.qWait(20)

    def items(item: QtQuick.QQuickItem) -> list:
        found = [item]
        for c in item.childItems():
            found += items(c)
        return found

    def named(win: QtQuick.QQuickWindow, name: str) -> list:
        return [i for i in items(win.contentItem()) if i.objectName() == name]

    def shown(win: QtQuick.QQuickWindow, name: str) -> list[str]:
        return [str(i.property("text")) for i in named(win, name) if i.isVisible()]

    def click(win: QtQuick.QQuickWindow, name: str) -> bool:
        found = [i for i in named(win, name) if i.isVisible() and i.isEnabled()]
        if not found:
            return False
        it = found[0]
        QtTest.QTest.qWait(150)
        p = it.mapToScene(QtCore.QPointF(it.width() / 2, it.height() / 2)).toPoint()
        QtTest.QTest.mouseClick(win, left, nomod, p)
        QtTest.QTest.qWait(50)
        return True

    def window(title: str):  # noqa: ANN202
        win = wait_until(lambda: next(
            (w for w in app.topLevelWindows()
             if isinstance(w, QtQuick.QQuickWindow) and w.isVisible()
             and w.title() == title),
            None,
        ))
        if win is None:
            return None
        return shiboken6.wrapInstance(
            shiboken6.getCppPointer(win)[0], QtQuick.QQuickWindow
        )

    def rows(win: QtQuick.QQuickWindow) -> list[dict]:
        """One dict per visible row, read in order from the row's parts."""
        ticks = [i for i in named(win, N_TICK) if i.isVisible()]
        usbs = [i for i in named(win, N_USB) if i.isVisible()]
        names = [i for i in named(win, N_NAME) if i.isVisible()]
        results = [i for i in named(win, N_RESULT) if i.isVisible()]
        out = []
        for n, usb in enumerate(usbs):
            full = usb.property("usbId") or usb.property("text")
            out.append({
                "usb": str(full),
                "name": str(names[n].property("text")) if n < len(names) else "",
                "ticked": (
                    bool(ticks[n].property("checked")) if n < len(ticks) else None
                ),
                "tickable": bool(ticks[n].isEnabled()) if n < len(ticks) else None,
                "result": str(results[n].property("text")) if n < len(results) else "",
            })
        return out

    def settled(win: QtQuick.QQuickWindow, n: int) -> bool:
        """n rows show a final result (not blank, not "resetting…")."""
        done = [r for r in rows(win)
                if r["result"].strip() not in ("", "—")
                and not r["result"].startswith("resetting")]
        return len(done) >= n

    def state(win: QtQuick.QQuickWindow) -> dict:
        return {
            "rows": rows(win),
            "warning": shown(win, N_WARNING),
            "game": shown(win, N_GAME),
            "count": shown(win, N_COUNT),
            "reset": shown(win, N_RESET),
        }

    sys.stdout.reconfigure(encoding="utf-8")
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    logging.getLogger("system").addHandler(Grab())
    logging.getLogger("system").setLevel(logging.DEBUG)
    trace.set_hidhide(True)
    trace.set_enabled(True)

    root_obj = wait_until(lambda: app.engine.rootObjects())[0]
    item = next(
        (o for o in root_obj.findChildren(QtCore.QObject)
         if "ThemedMenuItem" in o.metaObject().className()
         and o.property("command") == "tools.hidhide"),
        None,
    )
    page = None
    if item is not None:
        QtCore.QMetaObject.invokeMethod(item, "triggered")
        page = window("HidHide")
    result("open", page is not None)
    if page is None:
        print("done", flush=True)
        os._exit(0)
    page.resize(900, 900)
    QtTest.QTest.qWait(300)

    def open_reset() -> QtQuick.QQuickWindow | None:
        if not click(page, PAGE_BUTTON):
            return None
        win = window(WIN_TITLE)
        if win is not None:
            wait_until(lambda: rows(win), 5)
            QtTest.QTest.qWait(200)
        return win

    try:
        # First open: declined at Windows' permission prompt.
        win = open_reset()
        result("window", win is not None)
        if win is None:
            raise SystemExit
        result("first", state(win))
        clicked = click(win, N_RESET)
        wait_until(lambda: settled(win, 4), 15)
        QtTest.QTest.qWait(200)
        result("declined", {
            "clicked": clicked,
            "runnerCalls": len(runner_calls),
            "reset": list(reset_ids),
            "rows": rows(win),
            "trace": [
                line[3] for line in trace.lines() if line[2] == trace.HIDHIDE
            ],
        })
        trace.clear_view()
        if not click(win, N_CLOSE) and not click(win, N_RESET):
            click(win, N_CANCEL)
        wait_until(lambda: not win.isVisible(), 3)

        # Second open: ticked again; Reset with permission given.
        decline[0] = False
        expected = link.expected_file()
        if expected.is_file():
            expected.unlink()
        change_before = link.last_hidhide_change()
        syslog.clear()
        win = open_reset()
        if win is None:
            raise SystemExit
        result("second", state(win))
        clicked = click(win, N_RESET)
        wait_until(lambda: settled(win, 4), 30)
        QtTest.QTest.qWait(300)
        change_after = link.last_hidhide_change()
        result("reset", {
            "clicked": clicked,
            "runnerIds": runner_calls[-1] if len(runner_calls) > 1 else [],
            "rows": rows(win),
            "close": bool(shown(win, N_CLOSE)) or shown(win, N_RESET) == ["Close"],
            "syslog": [ln for ln in syslog if "USB\\" in ln["msg"].upper()],
            "trace": [
                line[3] for line in trace.lines() if line[2] == trace.HIDHIDE
            ],
            "expected": wait_until(lambda: expected.is_file(), 5) or False,
            "changeBefore": None if change_before is None else str(change_before),
            "changeAfter": None if change_after is None else str(change_after),
        })
    except SystemExit:
        pass
    finally:
        result("realRunner", len(real_calls))
        print("done", flush=True)
        os._exit(0)


if __name__ == "__main__":
    _main()
