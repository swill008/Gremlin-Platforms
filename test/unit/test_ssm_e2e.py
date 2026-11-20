# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Screen Saver Mode end to end (12 S1-S20), through the real program:
the two timers (Screen saver, Power off displays; contract-4) fire in
order, each with its own typed wait, ✕ and problem; the order warning;
keeping the displays off answers Windows' display-ON reports and the window
shows the count (S20).

A journey (test/journeys/_harness.py): the program built off-screen in its
own process with a temporary USERPROFILE. Only the Windows edge is faked:

- every method of gremlin.screen_saver_mode.WindowsApi is replaced on the
  class itself (so whatever instance manager() holds, nothing reaches
  Windows: no screen saver is started, no display is powered off);
- InputClock.start/stop/listening are replaced (no raw input is
  registered); input is given with the real InputClock.note_input;
- the module's clock is a stepped one (the test moves the time);
- Windows' display-ON reports are given with the real
  ScreenSaverMode.on_display_state (no power notification is registered);
- device_disable.manager() is the real DeviceDisabler (journal in the
  temporary home) with its Windows edge faked: the launcher (no
  ShellExecuteExW, no elevation), the pipe listener and the helper's
  answers (no helper process, no pnputil) and the device status reader;
  the model, the core's hooks and the program's start are the real ones
  (S21-S27);
- hid_report_scan.scan, power_requests.list_requests and
  power_requests.set_ignored are fakes (no HID read, no powercfg, no
  elevation); power_requests.split is the real one (Programs and System
  each keep their half of their own check).

Run twice with the same home: run 2 is a restart (the settings carry over).
"""

from __future__ import annotations

import pathlib
import sys
import time
import types
from typing import Any

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test" / "journeys"))
from _harness import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    Journey,
    run_journey,
)

_GROUP = ("global", "screen-saver-mode")
_NAMES = (
    "enabled",
    "screen-saver-on",
    "screen-saver-wait-s",
    "power-off-on",
    "power-off-wait-s",
    "hold-fullscreen",
)
_WARNING = "Power off comes at or before the screen saver: the screen saver won't show."
_WAKES = (
    "Windows turned the displays back on 3 times: devices that never go quiet "
    "(see Refresh Devices)."
)

# A driver's request as powercfg names it (the user's PC, 2026-11-15).
_DRIVER = "USB Audio 2.0 (USB\\VID_0DB0&PID_CD0E&MI_00\\9&9c4d365&0&0000)"
_DRIVER_DETAIL = "An audio stream is currently in use."

# +-------------------------------------------------------------------------
# | Script side (the child process)

# What the fake Windows reports and what was asked of it.
W: dict[str, Any] = {
    "screen_saver_path": "",
    "screen_saver_wait_s": 120,
    "display_off_wait_s": 600,
    "windows_idle_s": 0.5,
    "display_required": False,
    "fullscreen_busy": False,
    "screen_saver_running": False,
    "locked": False,
    "can_listen": True,
    "power_off": 0,
    "screen_saver": [],
    "clock_starts": 0,
    "clock_stops": 0,
    "scans": 0,
    "request_lists": 0,
    "requests_ok": True,
    "ignore_ok": True,
    "ignored": [],
    "ticks": 0,
    "foreground_program": "",
    "device_names": {},
    "name_lookups": [],
    # Wake PC (S28-S31): the keyboards and mice Windows lists, as
    # (physical id, name, kinds), and each raw input handle's physical id.
    "input_devices": [],
    "physical_ids": {},
    "input_device_reads": 0,
    # The device disabler's Windows edge (S21-S27).
    "helper_answer": [True, ""],
    "helper_starts": 0,
    "helper_ops": [],
    "disabled": [],
    "enable_requests": [],
    "status": {},
    "calls": {},
}
_VKB = r"HID\VID_231D&PID_0200"
_PD = r"HID\VID_352F&PID_0100"
_HELPER_TEXT = "Devices can't be disabled: the helper isn't running"
NOW = [5000.0]

# Wake PC (S28-S31): three physical devices; the Steam Controller has a
# keyboard part and a mouse part (two raw input handles, one row).
_G915 = r"USB\VID_046D&PID_C33E\0001"
_STEAM = r"USB\VID_28DE&PID_1142\0002"
_VIPER = r"USB\VID_1532&PID_0078\0003"
# The G915 has two keyboard handles: 0x5151 is used before S18, so S18's
# name lookup of 0x5150 is still its first.
_KEY_G915, _KEY_G915_2 = 0x5150, 0x5151
_STEAM_KEYS, _STEAM_MOUSE, _MOUSE_VIPER = 0x6000, 0x6001, 0x7000
W["input_devices"] = [
    (_G915, "Logitech G915", ("keyboard",)),
    (_STEAM, "Steam Controller", ("keyboard", "mouse")),
    (_VIPER, "Razer Viper", ("mouse",)),
]
W["physical_ids"] = {
    _KEY_G915: _G915,
    _KEY_G915_2: _G915,
    _STEAM_KEYS: _STEAM,
    _STEAM_MOUSE: _STEAM,
    _MOUSE_VIPER: _VIPER,
}
_WAITING = "Waiting: tick at least one keyboard or mouse on Wake PC."
_WAKE_KEY = "wake-pc"


def _install_fakes() -> None:
    import importlib

    ssm = importlib.import_module("gremlin.screen_saver_mode")
    api = ssm.WindowsApi
    api.screen_saver_path = lambda self: W["screen_saver_path"]
    api.screen_saver_wait_s = lambda self: W["screen_saver_wait_s"]
    api.display_off_wait_s = lambda self: W["display_off_wait_s"]
    api.windows_idle_s = lambda self: W["windows_idle_s"]
    api.display_required = lambda self: W["display_required"]
    api.fullscreen_busy = lambda self: W["fullscreen_busy"]
    api.screen_saver_running = lambda self: W["screen_saver_running"]
    api.locked = lambda self: W["locked"]
    api.foreground_program = lambda self: W["foreground_program"]

    def device_name(self: Any, handle: Any) -> str:  # noqa: ANN401
        W["name_lookups"].append(handle)
        return W["device_names"].get(handle, "")

    api.device_name = device_name

    def input_devices(self: Any) -> list:  # noqa: ANN401
        W["input_device_reads"] += 1
        return [
            ssm.InputDevice(physical_id=i, name=n, kinds=tuple(k))
            for i, n, k in W["input_devices"]
        ]

    api.input_devices = input_devices
    api.device_physical_id = lambda self, handle: W["physical_ids"].get(handle, "")

    def start_screen_saver(self: Any, path: str) -> bool:  # noqa: ANN401
        W["screen_saver"].append(path)
        return True

    def power_off_displays(self: Any) -> None:  # noqa: ANN401
        W["power_off"] += 1

    api.start_screen_saver = start_screen_saver
    api.power_off_displays = power_off_displays

    clk = ssm.InputClock

    def start(self: Any) -> bool:  # noqa: ANN401
        W["clock_starts"] += 1
        self._ssm_test_on = bool(W["can_listen"])
        return self._ssm_test_on

    def stop(self: Any) -> None:  # noqa: ANN401
        W["clock_stops"] += 1
        self._ssm_test_on = False

    clk.start = start
    clk.stop = stop
    clk.listening = lambda self: (
        bool(getattr(self, "_ssm_test_on", False)) and bool(W["can_listen"])
    )

    # The stepped clock, only for Screen Saver Mode (the rest of the program
    # keeps the real time).
    stepped = types.SimpleNamespace(
        monotonic=lambda: NOW[0], now=time.time, sleep=time.sleep
    )
    if isinstance(getattr(ssm, "clock", None), types.ModuleType):
        ssm.clock = stepped
    if callable(getattr(ssm, "monotonic", None)):
        ssm.monotonic = stepped.monotonic

    tick = ssm.ScreenSaverMode.tick

    def counted_tick(self: Any) -> None:  # noqa: ANN401
        W["ticks"] += 1
        tick(self)

    ssm.ScreenSaverMode.tick = counted_tick
    _install_scan_fakes()


def _install_scan_fakes() -> None:
    """The scans' fakes, in their modules and wherever a module imported
    them by name (the window's model)."""
    import importlib

    scan_mod = importlib.import_module("gremlin.hid_report_scan")
    req_mod = importlib.import_module("gremlin.power_requests")
    if getattr(scan_mod.scan, "_ssm_fake", False):
        originals = _install_scan_fakes.originals  # type: ignore[attr-defined]
    else:
        originals = {
            "scan": scan_mod.scan,
            "list_requests": req_mod.list_requests,
            "set_ignored": req_mod.set_ignored,
        }
        _install_scan_fakes.originals = originals  # type: ignore[attr-defined]

    def scan(seconds: float = 4.0, should_stop: Any = None) -> list:  # noqa: ANN401
        W["scans"] += 1
        return [
            scan_mod.DeviceRate(
                "VKBSim NXT SEM THQ FSM.GA", "HID\\VID_231D&PID_0200", 0x01, 0x04, 250.0
            ),
            scan_mod.DeviceRate(
                "PD200X Microphone (buttons)",
                "HID\\VID_352F&PID_0100",
                0x0C,
                0x01,
                62.0,
            ),
        ]

    def list_requests(runner: Any = None) -> Any:  # noqa: ANN401
        W["request_lists"] += 1
        if not W["requests_ok"]:
            return req_mod.RequestsResult(
                False, "Administrator rights were refused.", []
            )
        return req_mod.RequestsResult(
            True,
            "",
            [
                # Display and System: in Programs only, "also keeps the PC
                # awake" (contract-3, user 4 a).
                req_mod.ProgramRequest(
                    "RustDesk.exe",
                    "C:\\Program Files\\RustDesk\\RustDesk.exe",
                    ["Display", "System"],
                    False,
                    also_awake=True,
                ),
                req_mod.ProgramRequest(
                    "chrome.exe",
                    "C:\\Program Files\\Google\\chrome.exe",
                    ["Display"],
                    False,
                ),
                # A driver's request (S14 widened): named as powercfg names it.
                req_mod.ProgramRequest(
                    name=_DRIVER,
                    path="",
                    kinds=["System"],
                    ignored=False,
                    kind="DRIVER",
                    detail=_DRIVER_DETAIL,
                ),
            ],
        )

    def set_ignored(
        name: str,
        ignored: bool,
        kind: str = "PROCESS",
        runner: Any = None,  # noqa: ANN401
    ) -> tuple[bool, str]:
        W["ignored"].append([name, ignored, kind])
        if not W["ignore_ok"]:
            return False, "Administrator rights were refused."
        return True, ""

    fakes = {"scan": scan, "list_requests": list_requests, "set_ignored": set_ignored}
    for fake in fakes.values():
        fake._ssm_fake = True  # type: ignore[attr-defined]
    for module in list(sys.modules.values()):
        for name, original in originals.items():
            try:
                if getattr(module, name, None) is original:
                    setattr(module, name, fakes[name])
            except Exception:
                pass


def _cfg(name: str) -> Any:  # noqa: ANN401
    from gremlin.config import Configuration

    return Configuration().value(*_GROUP, name)


def _type_wait(
    j: Journey,
    window: Any,  # noqa: ANN401
    text: str,
    name: str = "ssmOffWaitBox",
) -> None:
    """Types a wait time (minutes) in a timer's box and leaves it."""
    box = j.item(window, name)
    assert box is not None, "no wait box"
    box.setProperty("text", text)
    j.ev("editingFinished(); true", box)
    j.settle()


def _start_as_main_does() -> None:
    """What joystick_gremlin.main() does before app.exec() (a journey builds
    the app without main()): Screen Saver Mode follows its saved settings."""
    import gremlin.ui.screen_saver_mode_model as model

    model.start()


def _mgr() -> Any:  # noqa: ANN401
    from gremlin import screen_saver_mode

    return screen_saver_mode.manager()


def _status() -> dict:
    import dataclasses

    return dataclasses.asdict(_mgr().status())


def _texts(j: Journey, window: Any) -> list[str]:  # noqa: ANN401
    found = []
    for item in j.walk(window.contentItem()):
        text = item.property("text")
        if isinstance(text, str) and text and item.isVisible():
            found.append(text)
    return found


def _text(j: Journey, window: Any, name: str) -> str:  # noqa: ANN401
    item = j.item(window, name)
    if item is None:
        return f"<no item {name}>"
    if not item.isVisible():
        return ""
    texts = [
        str(i.property("text"))
        for i in j.walk(item)
        if isinstance(i.property("text"), str) and i.property("text")
    ]
    return " ".join(texts)


def _flip(j: Journey, item: Any, on: bool) -> None:  # noqa: ANN401
    """A user's click on a switch, check box or radio button: the checked
    state changes, then toggled() and clicked() as Qt sends them."""
    assert item is not None, "no switch"
    if bool(item.property("checked")) != on:
        j.ev("toggle(); toggled(); clicked(); true", item)
    j.settle()


def _at(seconds: float) -> None:
    NOW[0] = seconds


def _input(j: Journey, own: bool = False) -> None:
    """Keyboard or mouse input (own: sent by Gremlin itself), through the
    real InputClock.note_input, then the window's next update."""
    _input_clock().note_input(own=own)


def _input_clock() -> Any:  # noqa: ANN401
    from gremlin import screen_saver_mode

    mgr = screen_saver_mode.manager()
    for value in vars(mgr).values():
        if isinstance(value, screen_saver_mode.InputClock):
            return value
    raise AssertionError("manager() holds no InputClock")


def _window(j: Journey) -> Any:  # noqa: ANN401
    from PySide6 import QtQuick

    def find() -> Any:  # noqa: ANN401
        for w in j.app.topLevelWindows():
            if (
                isinstance(w, QtQuick.QQuickWindow)
                and w.objectName() == "screenSaverModeWindow"
                and w.isVisible()
            ):
                return w
        return None

    return j.wait_until(find, "the Screen Saver Mode window", 15)


def _section(j: Journey, name: str, work: Any) -> None:  # noqa: ANN401
    """Runs one part of the story; a part that stops is recorded and the
    next part still runs (each spec statement gets its own result)."""
    import traceback

    try:
        work()
    except BaseException as exc:  # noqa: BLE001
        j.out[f"err:{name}"] = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"


def _device_input(handle: int, kind: str, press: bool = False) -> None:
    """Keyboard or mouse input from a device (its raw input handle): a key
    down or button down when press, else a key up or a mouse move."""
    _input_clock().note_input(source=handle, kind=kind, press=press)


def _no_wake_hold() -> str:
    from gremlin import screen_saver_mode

    return getattr(screen_saver_mode, "HOLD_NO_WAKE_DEVICE", "no_wake_device")


def _wake_saved() -> list[dict]:
    return list(_cfg(_WAKE_KEY) or [])


def _ticked() -> list[str]:
    return sorted(str(r["id"]) for r in _wake_saved() if r.get("ticked"))


def _how(physical_id: str) -> Any:  # noqa: ANN401
    for row in _wake_saved():
        if row.get("id") == physical_id:
            return [bool(row.get("ticked")), row.get("how", "")]
    return None


def _wake_tab(j: Journey, w: Any, open_: bool) -> None:  # noqa: ANN401
    """The user picks the Wake PC tab (open_) or the Settings tab."""
    tabs = j.item(w, "ssmTabs")
    assert tabs is not None, "no ssmTabs"
    tabs.setProperty("currentIndex", 1 if open_ else 0)
    j.settle()


def _wake_texts(j: Journey, w: Any) -> str:  # noqa: ANN401
    view = j.item(w, "ssmWakeList")
    return " ".join(_texts_in(j, view)) if view is not None else "<no ssmWakeList>"


def _wake_lit(j: Journey, w: Any) -> list[list[str]]:  # noqa: ANN401
    """S33: [name, note] of each Wake PC row shown lit (its highlight)."""
    view = j.item(w, "ssmWakeList")
    if view is None:
        return [["<no ssmWakeList>", ""]]
    lit = []
    for row in _walk_list(j, view):
        if row.objectName() != "ssmWakeRow":
            continue
        parts = {i.objectName(): i for i in j.walk(row)}
        light = parts.get("ssmWakeRowHighlight")
        if light is not None and light.isVisible():
            lit.append(
                [
                    str(parts["ssmWakeName"].property("text")),
                    str(parts["ssmWakeNote"].property("text")),
                ]
            )
    return sorted(lit)


def _wake_count(j: Journey, w: Any) -> int:  # noqa: ANN401
    view = j.item(w, "ssmWakeList")
    return int(view.property("count") or 0) if view is not None else -1


def _flush() -> None:
    from gremlin import deferred_write, history

    deferred_write.flush_all()
    history.flush()


def story_first(j: Journey) -> None:
    out = j.out
    _install_scan_fakes()  # the model may have been imported since
    _start_as_main_does()
    out["startCfg"] = {n: _cfg(n) for n in _NAMES}
    out["startClockStarts"] = W["clock_starts"]

    win: dict = {}

    def s1() -> None:
        j.ev('Commands.trigger("tools.screenSaverMode"); true')
        win["w"] = _window(j)
        _install_scan_fakes()
        out["s1Open"] = True
        names = [
            "ssmEnabled",
            "ssmSaverOn",
            "ssmSaverWaitBox",
            "ssmSaverWaitClear",
            "ssmSaverWindowsWait",
            "ssmSaverProblem",
            "ssmOffOn",
            "ssmOffWaitBox",
            "ssmOffWaitClear",
            "ssmOffWindowsWait",
            "ssmOffProblem",
            "ssmOrderWarning",
            "ssmSaverCountdown",
            "ssmOffCountdown",
            "ssmWakeCount",
            "ssmHoldFullscreen",
            "ssmListening",
            "ssmIdleText",
            "ssmWindowsIdleText",
            "ssmHoldText",
            "ssmProblemText",
            "ssmRefreshDevices",
            "ssmRefreshPrograms",
            "ssmDeviceList",
            "ssmProgramList",
            "ssmProgramsMessage",
            "ssmSectionDevices",
            "ssmSectionPrograms",
            "ssmSectionSystem",
            "ssmRefreshSystem",
            "ssmSystemList",
            "ssmSystemMessage",
            "ssmLastReset",
        ]
        out["s1Missing"] = [n for n in names if j.item(win["w"], n) is None]
        # The one Action choice and its single wait box are gone.
        out["s1Old"] = [
            n
            for n in (
                "ssmActionScreenSaver",
                "ssmActionPowerOff",
                "ssmWaitBox",
                "ssmWaitClear",
                "ssmWindowsWait",
            )
            if j.item(win["w"], n) is not None
        ]

    _section(j, "s1", s1)
    w = win.get("w")
    if w is None:
        return

    def s2_on() -> None:
        sw = j.item(w, "ssmEnabled")
        out["s2SwitchAtStart"] = bool(sw.property("checked"))
        out["s2TicksWhileOff"] = _timer_ticks(j)
        _at(5000.0)
        _flip(j, sw, True)
        j.await_value(lambda: _cfg("enabled"), True)
        out["s2CfgOn"] = _cfg("enabled")
        out["s2MgrOn"] = j.await_value(lambda: _mgr().settings().enabled, True)
        out["s2ClockStarted"] = W["clock_starts"]
        out["s2Listening"] = _status()["listening"]
        out["s2TicksWhileOn"] = _timer_ticks(j)
        out["s9ListeningText"] = j.await_value(
            lambda: _text(j, w, "ssmListening"), "Listening to the keyboard and mouse"
        )
        out["s9OnlyWhileOpen"] = any(
            "only while gremlin" in t.lower() for t in _texts(j, w)
        )

    _section(j, "s2on", s2_on)

    def s31() -> None:
        # On, nothing ticked on Wake PC (S29: all start unticked): neither
        # timer runs and the status line says why.
        W["display_off_wait_s"] = 300
        W["screen_saver_path"] = "C:\\Windows\\System32\\Mystify.scr"
        W["power_off"] = 0
        W["screen_saver"].clear()
        out["s31SavedAtFirst"] = _wake_saved()
        _at(5010.0)
        _input(j)
        _at(5320.0)  # past both waits (screen saver 2 min, power off 5 min)
        _mgr().tick()
        out["s31Hold"] = _status()["hold"]
        out["s31Fired"] = [len(W["screen_saver"]), W["power_off"]]
        out["s31Text"] = j.await_value(lambda: _WAITING in _texts(j, w), True)
        W["screen_saver_path"] = ""

    _section(j, "s31", s31)

    def s28_s30() -> None:
        tabs = [
            n
            for n in ("ssmTabs", "ssmTabSettings", "ssmTabWake")
            if j.item(w, n) is None
        ]
        out["s28MissingTabs"] = tabs
        reads = W["input_device_reads"]
        _wake_tab(j, w, True)
        out["s28Rows"] = j.await_value(lambda: _wake_count(j, w), 3, timeout=10)
        out["s28Reads"] = W["input_device_reads"] - reads
        # The rows' texts can land a frame after the row count under load
        # (SSM-E2E-SHOWN-FLAKE): wait for all three names, then read.
        names = ("Logitech G915", "Steam Controller", "Razer Viper")
        j.await_value(
            lambda: all(n in _wake_texts(j, w) for n in names), True, timeout=10
        )
        shown = _wake_texts(j, w)
        out["s28Shown"] = [
            "Allow this device to wake the PC" in " ".join(_texts(j, w)),
            "Logitech G915" in shown,
            "Steam Controller" in shown,
            "Razer Viper" in shown,
            "Input sent by programs (RustDesk, remote desktop) always counts."
            in " ".join(_texts(j, w)),
        ]
        ticks = [
            i
            for i in _walk_list(j, j.item(w, "ssmWakeList"))
            if i.objectName() == "ssmWakeTick"
        ]
        out["s29Ticks"] = [len(ticks), sum(bool(t.property("checked")) for t in ticks)]
        # S30: mouse movement and key ups never tick.
        _at(5410.0)
        _device_input(_STEAM_MOUSE, "mouse")
        _device_input(_STEAM_KEYS, "keyboard")
        _mgr().tick()
        j.QTest.qWait(300)
        _mgr().tick()
        out["s30MoveTicked"] = _ticked()
        # A key press on the keyboard, a button click on the mouse: ticked,
        # saved, each with how it was ticked.
        _device_input(_KEY_G915_2, "keyboard", press=True)
        _mgr().tick()
        out["s30Key"] = j.await_value(lambda: _how(_G915), [True, "key"])
        _device_input(_MOUSE_VIPER, "mouse", press=True)
        _mgr().tick()
        out["s30Click"] = j.await_value(lambda: _how(_VIPER), [True, "click"])
        out["s30Ticked"] = _ticked()
        out["s30Notes"] = j.await_value(
            lambda: [
                "ticked when you pressed a key" in _wake_texts(j, w),
                "ticked when you clicked" in _wake_texts(j, w),
            ],
            [True, True],
        )
        # S33: the presses above lit their rows; they go about 2 s after
        # the last input (real time).
        out["s33FadedAfterPresses"] = j.await_value(
            lambda: _wake_lit(j, w), [], timeout=8
        )
        # S33: mouse movement lights its row (in use now) without ticking it.
        _at(5420.0)
        _device_input(_STEAM_MOUSE, "mouse")
        _mgr().tick()
        out["s33MoveLit"] = j.await_value(
            lambda: _wake_lit(j, w), [["Steam Controller", "in use now"]]
        )
        out["s33MoveTicked"] = _ticked()
        out["s33Faded"] = j.await_value(lambda: _wake_lit(j, w), [], timeout=8)
        # A press lights a row too; a ticked row keeps its note before it.
        _at(5421.0)
        _device_input(_KEY_G915_2, "keyboard", press=True)
        _mgr().tick()
        out["s33PressLit"] = j.await_value(
            lambda: _wake_lit(j, w),
            [["Logitech G915", "ticked when you pressed a key · in use now"]],
        )
        _mgr().tick()
        out["s31HoldAfterTick"] = _status()["hold"]
        _wake_tab(j, w, False)
        out["s31TextAfterTick"] = j.await_value(lambda: _WAITING in _texts(j, w), False)
        # Tab closed: detection stops (S30), the mode keeps listening.
        _device_input(_STEAM_KEYS, "keyboard", press=True)
        _mgr().tick()
        j.QTest.qWait(300)
        _mgr().tick()
        out["s30ClosedTicked"] = _ticked()
        out["s30ClosedListening"] = _status()["listening"]
        # S33: nothing lights while the tab is closed.
        _at(5430.0)
        _device_input(_STEAM_MOUSE, "mouse")
        _mgr().tick()
        j.QTest.qWait(300)
        _mgr().tick()
        out["s33ClosedLit"] = "in use now" in _wake_texts(j, w)

    _section(j, "s28", s28_s30)

    def s3_wake() -> None:
        # S3/S28: an unticked device's input doesn't restart the idle clock;
        # program input and a ticked device's input do.
        W["display_off_wait_s"] = 300
        W["power_off"] = 0
        _at(5500.0)
        _input(j)
        _at(5600.0)
        _device_input(_STEAM_MOUSE, "mouse")
        _device_input(_STEAM_KEYS, "keyboard", press=True)
        _mgr().tick()
        out["s3UntickedIdle"] = round(_status()["idle_s"])
        _at(5800.0)
        _mgr().tick()
        out["s3UntickedFired"] = W["power_off"]
        _at(5850.0)
        _device_input(_KEY_G915_2, "keyboard")
        _mgr().tick()
        st = _status()
        out["s3TickedIdle"] = [round(st["idle_s"]), st["keeping_off"]]
        _at(5900.0)
        _device_input(_MOUSE_VIPER, "mouse")
        _mgr().tick()
        out["s3TickedMoveIdle"] = round(_status()["idle_s"])
        _at(5950.0)
        _input(j)
        _mgr().tick()
        out["s3ProgramIdle"] = round(_status()["idle_s"])
        W["power_off"] = 0
        W["display_off_wait_s"] = 600

    _section(j, "s3wake", s3_wake)

    def s5() -> None:
        # Both timers are on at first; power off follows Windows' display-off
        # time, the screen saver Windows' screen saver wait.
        s = _mgr().settings()
        out["s4Default"] = [s.screen_saver_on, s.power_off_on]
        W["display_off_wait_s"] = 600
        _at(6000.0)
        _input(j)
        _mgr().tick()
        st = _status()
        out["s5Wait"] = [
            st["off_wait_s"],
            st["off_windows_wait_s"],
            st["off_from_windows"],
        ]
        out["s5WindowsWaitText"] = j.await_value(
            lambda: _text(j, w, "ssmOffWindowsWait"),
            "Windows' display-off time (10 min)",
        )
        # No screen saver chosen yet: Windows has no screen saver wait.
        out["s5SaverWindowsWaitText"] = j.await_value(
            lambda: _text(j, w, "ssmSaverWindowsWait"),
            "Windows' screen saver wait (never)",
        )
        # Windows' time changes: followed at the next countdown, no restart.
        W["display_off_wait_s"] = 900
        _at(6100.0)
        _input(j)
        _mgr().tick()
        out["s5Followed"] = _status()["off_wait_s"]
        # A typed time replaces it: 7 min typed in the power off row only.
        _type_wait(j, w, "7")
        out["s5OverrideCfg"] = _cfg("power-off-wait-s")
        out["s5OtherRow"] = _cfg("screen-saver-wait-s")
        out["s5OverrideMgr"] = j.await_value(
            lambda: _mgr().settings().power_off_wait_s, 420
        )
        _at(6200.0)
        _input(j)
        _mgr().tick()
        st = _status()
        out["s5Override"] = [st["off_wait_s"], st["off_from_windows"]]
        _at(6200.0 + 419)
        _mgr().tick()
        out["s5OverrideBefore"] = W["power_off"]
        _at(6200.0 + 420)
        _mgr().tick()
        out["s5OverrideFired"] = W["power_off"]
        # Cleared in the window: Windows' time again.
        j.click(j.item(w, "ssmOffWaitClear"))
        j.settle()
        out["s5ClearedCfg"] = j.await_value(lambda: _cfg("power-off-wait-s"), 0)
        _at(7000.0)
        _input(j)
        _mgr().tick()
        st = _status()
        out["s5Cleared"] = [st["off_wait_s"], st["off_from_windows"]]

    _section(j, "s5", s5)

    def s6_s3() -> None:
        W["display_off_wait_s"] = 300
        W["power_off"] = 0
        _at(10000.0)
        _input(j)
        _at(10299.0)
        _mgr().tick()
        out["s6Before"] = W["power_off"]
        _at(10300.0)
        _mgr().tick()
        out["s6At"] = W["power_off"]
        out["s6Fired"] = _status()["off_fired"]
        for t in (10301.0, 10600.0, 11000.0):
            _at(t)
            _mgr().tick()
        out["s6Once"] = W["power_off"]
        # Input restarts the clock; the next idle period fires again.
        _at(11001.0)
        _input(j)
        _mgr().tick()
        out["s6Reset"] = [_status()["off_fired"], W["power_off"]]
        _at(11301.0)
        _mgr().tick()
        out["s6Again"] = W["power_off"]
        # S3: Gremlin's own input does not count.
        W["power_off"] = 0
        _at(12000.0)
        _input(j)
        _at(12200.0)
        _input(j, own=True)
        _mgr().tick()
        out["s3OwnIdle"] = round(_status()["idle_s"])
        _at(12300.0)
        _mgr().tick()
        out["s3OwnFired"] = W["power_off"]
        # Other input does.
        W["power_off"] = 0
        _at(13000.0)
        _input(j)
        _at(13200.0)
        _input(j)
        _at(13300.0)
        _mgr().tick()
        out["s3OtherHeld"] = W["power_off"]
        out["s9IdleText"] = _text(j, w, "ssmIdleText")
        out["s9WindowsIdleText"] = _text(j, w, "ssmWindowsIdleText")

    _section(j, "s6", s6_s3)

    def holds(flag: str, value_key: str) -> None:
        W["display_off_wait_s"] = 300
        W["power_off"] = 0
        base = {"fullscreen": 20000.0, "display": 30000.0, "locked": 40000.0}[value_key]
        _at(base)
        _input(j)
        W[flag] = True
        if value_key == "fullscreen":
            W["foreground_program"] = "StarCitizen.exe"
        _at(base + 400)
        _mgr().tick()
        st = _status()
        # Still held at base + 500, when it ends.
        _at(base + 500)
        _mgr().tick()
        out[f"{value_key}Held"] = [W["power_off"], st["hold"]]
        out[f"{value_key}HoldText"] = j.await_value(
            lambda: _text(j, w, "ssmHoldText"), "__never__", timeout=2.5
        )
        W[flag] = False
        W["foreground_program"] = ""
        _at(base + 501)
        _mgr().tick()
        out[f"{value_key}AfterEnd"] = W["power_off"]
        _at(base + 500 + 299)
        _mgr().tick()
        out[f"{value_key}BeforeWait"] = W["power_off"]
        _at(base + 500 + 300)
        _mgr().tick()
        out[f"{value_key}AfterWait"] = W["power_off"]

    _section(j, "s7", lambda: holds("fullscreen_busy", "fullscreen"))
    _section(j, "s15", lambda: holds("display_required", "display"))
    _section(j, "s11", lambda: holds("locked", "locked"))

    def s7_off() -> None:
        # The hold switched off: full screen no longer holds the action.
        _flip(j, j.item(w, "ssmHoldFullscreen"), False)
        out["s7OffCfg"] = j.await_value(lambda: _cfg("hold-fullscreen"), False)
        out["s7OffMgr"] = j.await_value(
            lambda: _mgr().settings().hold_fullscreen, False
        )
        W["power_off"] = 0
        W["fullscreen_busy"] = True
        _at(50000.0)
        _input(j)
        _at(50300.0)
        _mgr().tick()
        out["s7OffFired"] = W["power_off"]
        W["fullscreen_busy"] = False

    _section(j, "s7off", s7_off)

    def s8() -> None:
        # No screen saver chosen: only that row says so and does nothing;
        # power off still works (S8, contract-4).
        W["screen_saver_path"] = ""
        W["screen_saver_wait_s"] = 120
        W["display_off_wait_s"] = 300
        W["power_off"] = 0
        W["screen_saver"].clear()
        _at(60000.0)
        _input(j)
        _at(60500.0)
        _mgr().tick()
        st = _status()
        out["s8Problem"] = [st["saver_problem"], st["off_problem"]]
        out["s8Started"] = [list(W["screen_saver"]), W["power_off"]]
        out["s8Text"] = j.await_value(
            lambda: _text(j, w, "ssmSaverProblem"),
            "No screen saver is chosen in Windows.",
        )
        out["s8OffRowText"] = _text(j, w, "ssmOffProblem")
        # A screen saver chosen: the two timers fire in order, each once.
        W["screen_saver_path"] = "C:\\Windows\\System32\\Mystify.scr"
        W["power_off"] = 0
        _at(61000.0)
        _input(j)
        _mgr().tick()
        st = _status()
        out["s8Waits"] = [st["saver_wait_s"], st["off_wait_s"]]
        out["s8SaverWindowsWait"] = j.await_value(
            lambda: _text(j, w, "ssmSaverWindowsWait"),
            "Windows' screen saver wait (2 min)",
        )
        out["s8Countdowns"] = j.await_value(
            lambda: [_text(j, w, "ssmSaverCountdown"), _text(j, w, "ssmOffCountdown")],
            ["Screen saver in 2 min", "Power off displays in 5 min"],
        )
        _at(61119.0)
        _mgr().tick()
        out["s8Before"] = [list(W["screen_saver"]), W["power_off"]]
        _at(61120.0)
        _mgr().tick()
        out["s8SaverFired"] = [list(W["screen_saver"]), W["power_off"]]
        out["s8SaverDone"] = j.await_value(
            lambda: _text(j, w, "ssmSaverCountdown").startswith("Screen saver done."),
            True,
        )
        _at(61299.0)
        _mgr().tick()
        out["s8OffBefore"] = W["power_off"]
        _at(61300.0)
        _mgr().tick()
        out["s8OffFired"] = [list(W["screen_saver"]), W["power_off"]]
        _at(61600.0)
        _mgr().tick()
        out["s8Once"] = [len(W["screen_saver"]), W["power_off"]]

        # Typed waits per row; power off typed shorter: the order warning.
        _type_wait(j, w, "3", "ssmSaverWaitBox")
        out["s8SaverTypedCfg"] = j.await_value(lambda: _cfg("screen-saver-wait-s"), 180)
        out["s8NoWarning"] = j.await_value(lambda: _text(j, w, "ssmOrderWarning"), "")
        _type_wait(j, w, "2", "ssmOffWaitBox")
        out["s8OffTypedCfg"] = j.await_value(lambda: _cfg("power-off-wait-s"), 120)
        out["s8Warning"] = j.await_value(
            lambda: _text(j, w, "ssmOrderWarning"), _WARNING
        )
        _flush()  # its own save, so History has the typed waits (S10)
        # Both still work: power off first, then the screen saver.
        W["power_off"] = 0
        W["screen_saver"].clear()
        _at(62000.0)
        _input(j)
        _mgr().tick()
        st = _status()
        out["s8TypedWaits"] = [
            st["saver_wait_s"],
            st["off_wait_s"],
            st["saver_from_windows"],
            st["off_from_windows"],
        ]
        _at(62120.0)
        _mgr().tick()
        out["s8OffFirst"] = [len(W["screen_saver"]), W["power_off"]]
        _at(62180.0)
        _mgr().tick()
        out["s8SaverAfter"] = [len(W["screen_saver"]), W["power_off"]]
        # ✕ on each row: Windows' times again.
        j.click(j.item(w, "ssmSaverWaitClear"))
        j.settle()
        j.click(j.item(w, "ssmOffWaitClear"))
        j.settle()
        out["s8ClearedCfg"] = j.await_value(
            lambda: [_cfg("screen-saver-wait-s"), _cfg("power-off-wait-s")], [0, 0]
        )
        _at(63000.0)
        _input(j)
        _mgr().tick()
        st = _status()
        out["s8Cleared"] = [
            st["saver_wait_s"],
            st["off_wait_s"],
            st["saver_from_windows"],
            st["off_from_windows"],
        ]
        out["s8ClearedWarning"] = j.await_value(
            lambda: _text(j, w, "ssmOrderWarning"), ""
        )
        # A timer switched off: only the other one fires.
        _flip(j, j.item(w, "ssmSaverOn"), False)
        out["s8SaverOffCfg"] = j.await_value(lambda: _cfg("screen-saver-on"), False)
        out["s8SaverOffMgr"] = j.await_value(
            lambda: _mgr().settings().screen_saver_on, False
        )
        _flush()  # its own save, so History has the change (S10)
        W["power_off"] = 0
        W["screen_saver"].clear()
        _at(64000.0)
        _input(j)
        _at(64400.0)
        _mgr().tick()
        out["s8SaverOffFired"] = [len(W["screen_saver"]), W["power_off"]]
        out["s8SaverOffCountdown"] = j.await_value(
            lambda: _text(j, w, "ssmSaverCountdown"), ""
        )
        _flip(j, j.item(w, "ssmSaverOn"), True)
        out["s8SaverBackCfg"] = j.await_value(lambda: _cfg("screen-saver-on"), True)

    _section(j, "s8", s8)

    def s20() -> None:
        # Keeping the displays off: each display-ON report Windows sends
        # without keyboard or mouse input is answered with one power-off;
        # the window counts them (S6, S20).
        W["display_off_wait_s"] = 300
        W["screen_saver_path"] = ""
        W["power_off"] = 0
        _at(65000.0)
        _input(j)
        _at(65300.0)
        _mgr().tick()
        st = _status()
        out["s20Keeping"] = [st["keeping_off"], st["wakes"], W["power_off"]]
        # S27: Refresh Devices not pressed yet: nothing to disable.
        out["s20Disabled"] = list(W["disabled"])
        out["s20Starts"] = W["helper_starts"]
        for at in (65302.0, 65304.0, 65306.0):
            _at(at)
            _mgr().on_display_state(True)
            _mgr().on_display_state(False)
        _mgr().tick()
        st = _status()
        out["s20Wakes"] = [st["keeping_off"], st["wakes"], W["power_off"]]
        out["s20Text"] = j.await_value(lambda: _text(j, w, "ssmWakeCount"), _WAKES)
        # Input ends it; the count of the last idle period stays shown and
        # an ON report is no longer answered.
        _at(65400.0)
        _input(j)
        _mgr().tick()
        _at(65401.0)
        _mgr().on_display_state(True)
        st = _status()
        out["s20AfterInput"] = [st["keeping_off"], st["wakes"], W["power_off"]]
        j.QTest.qWait(1200)
        out["s20TextAfter"] = _text(j, w, "ssmWakeCount")
        W["screen_saver_path"] = "C:\\Windows\\System32\\Mystify.scr"

    _section(j, "s20", s20)

    def never() -> None:
        # Windows never turns the display off and no time is typed: nothing.
        W["display_off_wait_s"] = 0
        W["power_off"] = 0
        _at(70000.0)
        _input(j)
        _at(90000.0)
        _mgr().tick()
        out["neverProblem"] = [_status()["off_problem"], W["power_off"]]
        out["neverText"] = j.await_value(
            lambda: _text(j, w, "ssmOffProblem"),
            "Windows never turns the display off: type a time to use this timer.",
        )
        W["display_off_wait_s"] = 300

    _section(j, "never", never)

    def s9_not_listening() -> None:
        # The keyboard and mouse can't be listened to: said, nothing is done.
        W["can_listen"] = False
        W["power_off"] = 0
        _at(80000.0)
        _input(j)
        _at(80400.0)
        _mgr().tick()
        st = _status()
        out["s9NotListening"] = [st["listening"], st["problem"], W["power_off"]]
        out["s9NotListeningText"] = j.await_value(
            lambda: _text(j, w, "ssmListening"), "__never__", timeout=2.5
        )
        W["can_listen"] = True

    _section(j, "s9", s9_not_listening)

    def s12() -> None:
        devices = j.item(w, "ssmDeviceList")
        out["s12EmptyAtFirst"] = [int(devices.property("count") or 0), W["scans"]]
        j.click(j.item(w, "ssmRefreshDevices"))
        out["s12Count"] = j.await_value(
            lambda: int(devices.property("count") or 0), 2, timeout=10
        )
        j.settle()
        shown = " ".join(_texts_in(j, devices))
        out["s12Rows"] = [
            "VKBSim NXT SEM THQ FSM.GA" in shown,
            "250" in shown,
            "PD200X Microphone (buttons)" in shown,
        ]
        out["s12Scans"] = W["scans"]
        out["s12Description"] = any(
            "Devices that never go quiet and keep Windows' idle time at 0" in t
            for t in _texts(j, w)
        )

    _section(j, "s12", s12)

    def s13_s14() -> None:
        programs = j.item(w, "ssmProgramList")
        system = j.item(w, "ssmSystemList")
        # Refused: said, nothing else.
        W["requests_ok"] = False
        j.click(j.item(w, "ssmRefreshPrograms"))
        out["s13Refused"] = j.await_value(
            lambda: (
                "Administrator rights were refused."
                in _text(j, w, "ssmProgramsMessage")
            ),
            True,
            timeout=10,
        )
        out["s13RefusedCount"] = int(programs.property("count") or 0)
        W["requests_ok"] = True
        lists_before = W["request_lists"]
        j.click(j.item(w, "ssmRefreshPrograms"))
        out["s13Count"] = j.await_value(
            lambda: int(programs.property("count") or 0), 2, timeout=10
        )
        j.settle()
        # One check (one administrator prompt) for one press; System empty.
        out["s13Lists"] = W["request_lists"] - lists_before
        out["s13SystemCount"] = int(system.property("count") or 0)
        texts = _texts_in(j, programs)
        shown = " ".join(texts)
        out["s13Rows"] = [
            "RustDesk.exe" in shown,
            "chrome.exe" in shown,
            _DRIVER not in shown,
        ]
        out["s13AlsoAwake"] = [
            str(i.property("text"))
            for i in _walk_list(j, programs)
            if i.objectName() == "ssmAlsoAwake" and i.isVisible()
        ]
        out["s13Description"] = any(
            "Programs keeping the display on. These hold Screen Saver Mode off" in t
            for t in _texts(j, w)
        )

        def switch(view: Any, n: int) -> Any:  # noqa: ANN401
            # The rows are built again when the list changes: found each time.
            found = [
                i for i in _walk_list(j, view) if i.objectName() == "ssmIgnoreSwitch"
            ]
            from PySide6 import QtCore

            found.sort(key=lambda i: i.mapToItem(view, QtCore.QPointF(0, 0)).y())
            return found[n] if len(found) > n else None

        out["s14Switches"] = len(
            [i for i in _walk_list(j, programs) if i.objectName() == "ssmIgnoreSwitch"]
        )
        _flip(j, switch(programs, 0), True)
        j.await_value(lambda: len(W["ignored"]), 1, timeout=10)
        out["s14Asked"] = list(W["ignored"])
        out["s14On"] = j.await_value(
            lambda: bool(
                switch(programs, 0) and switch(programs, 0).property("checked")
            ),
            True,
        )
        out["s14ProgramsMessage"] = j.await_value(
            lambda: _text(j, w, "ssmProgramsMessage"),
            "chrome.exe is ignored: it no longer keeps the display on.",
        )
        # Refused: the switch goes back and the window says so.
        W["ignore_ok"] = False
        _flip(j, switch(programs, 1), True)
        j.await_value(lambda: len(W["ignored"]), 2, timeout=10)
        out["s14Asked2"] = list(W["ignored"])
        out["s14RefusedBack"] = j.await_value(
            lambda: bool(
                switch(programs, 1) and switch(programs, 1).property("checked")
            ),
            False,
        )
        out["s14RefusedText"] = j.await_value(
            lambda: (
                "Administrator rights were refused."
                in _text(j, w, "ssmProgramsMessage")
            ),
            True,
        )
        W["ignore_ok"] = True

        # S17: Refresh System, its own check, fills only the System list.
        lists_before = W["request_lists"]
        j.click(j.item(w, "ssmRefreshSystem"))
        out["s17Count"] = j.await_value(
            lambda: int(system.property("count") or 0), 1, timeout=10
        )
        j.settle()
        out["s17Lists"] = W["request_lists"] - lists_before
        out["s17ProgramsCount"] = int(programs.property("count") or 0)
        texts = _texts_in(j, system)
        out["s14DriverRow"] = [
            _DRIVER in texts,
            "(driver)" in texts,
            _DRIVER_DETAIL in texts,
        ]
        out["s17Description"] = any(
            "Programs, drivers and services keeping the PC awake." in t
            for t in _texts(j, w)
        )
        # The driver's row has the switch too and passes its kind on.
        _flip(j, switch(system, 0), True)
        j.await_value(lambda: len(W["ignored"]), 3, timeout=10)
        out["s14Driver"] = W["ignored"][-1]
        out["s14DriverOn"] = j.await_value(
            lambda: bool(switch(system, 0) and switch(system, 0).property("checked")),
            True,
        )
        out["s17Message"] = j.await_value(
            lambda: _text(j, w, "ssmSystemMessage"),
            f"{_DRIVER} is ignored: it no longer keeps the PC awake.",
        )
        # The Programs message is still its own.
        out["s17ProgramsMessage"] = _text(j, w, "ssmProgramsMessage")

    _section(j, "s13", s13_s14)

    def s18() -> None:
        # Program input (no device handle): named as sent by a program.
        _at(90000.0)
        for _ in range(3):
            _input_clock().note_input()
        _mgr().tick()
        out["s18Program"] = j.await_value(
            lambda: _text(j, w, "ssmLastReset"),
            "last reset by: input sent by a program, 3 times a minute",
            timeout=3,
        )
        # A keyboard: its name, looked up once per device handle.
        W["device_names"] = {0x5150: "Logitech G915"}
        W["name_lookups"].clear()
        _at(90010.0)
        for _ in range(5):
            _input_clock().note_input(source=0x5150, kind="keyboard")
            _mgr().tick()
        out["s18Keyboard"] = j.await_value(
            lambda: _text(j, w, "ssmLastReset"),
            "last reset by: Logitech G915 (keyboard), just now",
            timeout=3,
        )
        j.QTest.qWait(1200)  # the window's polls look it up too
        out["s18Lookups"] = list(W["name_lookups"])

    _section(j, "s18", s18)

    def s21_s26() -> None:
        dd = _dis()
        # S27: the Refresh result is saved; S25: a filled list (mode and
        # Power off displays on) starts the helper.
        out["s27Saved"] = _cfg("devices")
        out["s25Running"] = j.await_value(dd.helper_running, True, timeout=10)
        out["s25StartsAfterRefresh"] = W["helper_starts"]
        out["s26HiddenWhileRunning"] = j.await_value(
            lambda: _text(j, w, "ssmHelperMessage"), ""
        )
        # S21: the power-off timer fires: the saved list is disabled first.
        W["display_off_wait_s"] = 300
        W["screen_saver_path"] = ""
        W["power_off"] = 0
        W["disabled"] = []
        W["enable_requests"] = []
        _at(200000.0)
        _input(j)
        _mgr().tick()
        _at(200300.0)
        _mgr().tick()
        _idle()
        # The power-off waits for the devices (S21, to-do 142): the next
        # tick after they are done sends it.
        _at(200301.0)
        _mgr().tick()
        journal = dd.journal().entries
        out["s21Disabled"] = [list(W["disabled"]), W["power_off"]]
        out["s21Ops"] = list(W["helper_ops"])
        out["s22Journal"] = {i: e.get("state") for i, e in journal.items()}
        # S23: the first counted input re-enables what the journal lists.
        _at(200310.0)
        _input(j)
        _mgr().tick()
        _idle()
        out["s23Enabled"] = list(W["enable_requests"])
        out["s23Journal"] = {i: e.get("state") for i, e in dd.journal().entries.items()}
        # S26: refused: said, not asked again until Try again.
        dd.stop_helper()
        W["helper_answer"] = [False, ""]
        starts = W["helper_starts"]
        _flip(j, j.item(w, "ssmOffOn"), False)
        j.await_value(lambda: _cfg("power-off-on"), False)
        _flip(j, j.item(w, "ssmOffOn"), True)
        j.await_value(lambda: _cfg("power-off-on"), True)
        out["s26Text"] = j.await_value(
            lambda: _text(j, w, "ssmHelperMessage").startswith(_HELPER_TEXT),
            True,
            timeout=10,
        )
        out["s26TryAgainShown"] = bool(
            j.item(w, "ssmHelperTryAgain").property("visible")
        )
        _flip(j, j.item(w, "ssmOffOn"), False)
        _flip(j, j.item(w, "ssmOffOn"), True)
        j.await_value(lambda: _cfg("power-off-on"), True)
        j.QTest.qWait(300)
        out["s26StartsAfterRefusal"] = W["helper_starts"] - starts
        # Power off on, the helper not running: nothing disabled (S26).
        W["disabled"] = []
        _at(201000.0)
        _input(j)
        _mgr().tick()
        _at(201300.0)
        _mgr().tick()
        _idle()
        out["s26DisabledWithout"] = list(W["disabled"])
        _at(201310.0)
        _input(j)
        _mgr().tick()
        # Try again: asked once more; accepted, the message goes.
        W["helper_answer"] = [True, ""]
        j.click(j.item(w, "ssmHelperTryAgain"))
        out["s26TryAgainRunning"] = j.await_value(dd.helper_running, True, timeout=10)
        out["s26TryAgainStarts"] = W["helper_starts"] - starts
        out["s26TextAfter"] = j.await_value(lambda: _text(j, w, "ssmHelperMessage"), "")
        # S23: a device plugged in again retries what is still to be enabled.
        arrivals = W["calls"].get("on_device_arrival", 0)
        from gremlin import event_handler

        event_handler.EventListener().device_change_event.emit()
        out["s23Arrivals"] = W["calls"].get("on_device_arrival", 0) - arrivals
        W["screen_saver_path"] = "C:\\Windows\\System32\\Mystify.scr"

    _section(j, "s21", s21_s26)

    def s10() -> None:
        _flush()
        from gremlin import history

        entries = history.entries("settings")
        mine = [
            e
            for e in entries
            if any(k.startswith("global/screen-saver-mode/") for k in _entry_keys(e))
        ]
        out["s10Entries"] = [str(e.get("title", "")) for e in mine]
        out["s10Keys"] = sorted({k for e in mine for k in _entry_keys(e)})

    _section(j, "s10", s10)

    def leave_for_restart() -> None:
        # Left for run 2: on, the screen saver timer off, power off with a
        # typed 7 min, hold off.
        _type_wait(j, w, "7")
        _flip(j, j.item(w, "ssmSaverOn"), False)
        j.await_value(lambda: _cfg("screen-saver-on"), False)
        out["leftCfg"] = {n: _cfg(n) for n in _NAMES}
        # S24: as after a crash, the journal still has the VKB disabled.
        _idle()
        journal = _dis().journal()
        journal.set(_VKB, "VKBSim NXT SEM THQ FSM.GA", "disabled")
        journal.save()
        _flush()

    _section(j, "leave", leave_for_restart)


def _entry_keys(entry: dict) -> list[str]:
    keys: list[str] = []
    for value in entry.values():
        if isinstance(value, dict):
            keys += [str(k) for k in value.get("keys", [])]
            keys += [str(k) for k in value if str(k).startswith("global/")]
    return keys


def _texts_in(j: Journey, item: Any) -> list[str]:  # noqa: ANN401
    found = []
    for child in j.walk(item):
        text = child.property("text")
        if isinstance(text, str) and text:
            found.append(text)
    # A ListView's rows are under its contentItem.
    content = item.property("contentItem")
    if content is not None and content is not item:
        for child in j.walk(content):
            text = child.property("text")
            if isinstance(text, str) and text:
                found.append(text)
    return found


def _walk_list(j: Journey, view: Any) -> list:  # noqa: ANN401
    """A ListView's items, its rows (under contentItem) too, each once."""
    found = list(j.walk(view))
    content = view.property("contentItem")
    if content is not None and content is not view:
        found += list(j.walk(content))
    import shiboken6

    once: dict[int, Any] = {}
    for item in found:
        once.setdefault(shiboken6.getCppPointer(item)[0], item)
    return list(once.values())


def _timer_ticks(j: Journey) -> int:
    """How many ticks the program's own 1 s timer ran in 2.5 s."""
    before = W["ticks"]
    j.QTest.qWait(2500)
    return W["ticks"] - before


def story_restart(j: Journey) -> None:
    out = j.out
    _install_scan_fakes()
    _start_as_main_does()
    out["cfg"] = {n: _cfg(n) for n in _NAMES}
    out["clockStartedAtStart"] = W["clock_starts"]
    # S24: recovery at start; S25: the helper is started at start (mode and
    # Power off displays on, saved list not empty).
    out["recoveries"] = W["calls"].get("recover_at_start", 0)
    # The helper started (recovery and S25 share one start) and the VKB was
    # enabled again before anything else.
    out["helperRunningAtStart"] = j.await_value(_dis().helper_running, True, timeout=10)
    out["recoveredEnable"] = j.await_value(
        lambda: list(W["enable_requests"]), [[_VKB]], timeout=10
    )
    _idle()
    out["recoveredJournal"] = _dis().journal().state(_VKB)
    out["helperStartsAtStart"] = W["helper_starts"]

    def mgr() -> None:
        s = _mgr().settings()
        out["mgr"] = [
            s.enabled,
            s.screen_saver_on,
            s.screen_saver_wait_s,
            s.power_off_on,
            s.power_off_wait_s,
            s.hold_fullscreen,
        ]
        out["ticking"] = _timer_ticks(j) > 0

    _section(j, "mgr", mgr)

    def wake() -> None:
        # S28: the ticks carry over and reach the core at program start.
        out["wakeTicked"] = _ticked()
        _mgr().tick()
        out["wakeHold"] = _status()["hold"]
        _at(8000.0)
        _input(j)
        _at(8100.0)
        _device_input(_STEAM_MOUSE, "mouse")
        _mgr().tick()
        out["wakeUntickedIdle"] = round(_status()["idle_s"])
        _at(8150.0)
        _device_input(_KEY_G915, "keyboard")
        _mgr().tick()
        out["wakeTickedIdle"] = round(_status()["idle_s"])
        # The G915 unplugged: its row stays, ticked, shown not connected.
        W["input_devices"] = [d for d in W["input_devices"] if d[0] != _G915]
        j.ev('Commands.trigger("tools.screenSaverMode"); true')
        w = _window(j)
        _wake_tab(j, w, True)
        out["wakeRows"] = j.await_value(lambda: _wake_count(j, w), 3, timeout=10)
        out["wakeNotConnected"] = j.await_value(
            lambda: [
                "Logitech G915" in _wake_texts(j, w),
                "not connected" in _wake_texts(j, w),
            ],
            [True, True],
        )
        ticks = [
            i
            for i in _walk_list(j, j.item(w, "ssmWakeList"))
            if i.objectName() == "ssmWakeTick"
        ]
        out["wakeShownTicked"] = sum(bool(t.property("checked")) for t in ticks)
        _wake_tab(j, w, False)
        out["wakeTickedAfterOpen"] = _ticked()

    _section(j, "wake", wake)

    def window() -> None:
        j.ev('Commands.trigger("tools.screenSaverMode"); true')
        w = _window(j)
        out["switchOn"] = bool(j.item(w, "ssmEnabled").property("checked"))
        out["holdSwitch"] = bool(j.item(w, "ssmHoldFullscreen").property("checked"))
        out["rows"] = [
            bool(j.item(w, "ssmSaverOn").property("checked")),
            bool(j.item(w, "ssmOffOn").property("checked")),
            str(j.item(w, "ssmSaverWaitBox").property("text")),
            str(j.item(w, "ssmOffWaitBox").property("text")),
        ]
        # S27: the saved list fills the Devices list.
        view = j.item(w, "ssmDeviceList")
        out["savedShown"] = int(view.property("count") or 0)
        j.await_value(
            lambda: "PD200X Microphone (buttons)" in " ".join(_texts_in(j, view)),
            True,
        )
        out["savedRows"] = " ".join(_texts_in(j, view))
        # Off: the clock stops, the timer stops, nothing fires (S2); what
        # is pending is re-enabled (S23, lead 2026-11-15).
        enables = W["calls"].get("enable_pending", 0)
        _flip(j, j.item(w, "ssmEnabled"), False)
        out["offCfg"] = j.await_value(lambda: _cfg("enabled"), False)
        out["offStops"] = W["clock_stops"]
        out["offEnables"] = W["calls"].get("enable_pending", 0) - enables
        out["offListening"] = _status()["listening"]
        out["offTicks"] = _timer_ticks(j)
        W["power_off"] = 0
        _at(5000.0)
        _input(j)
        _at(99999.0)
        _mgr().tick()
        out["offFired"] = W["power_off"]
        _flush()

    _section(j, "window", window)


class _Process:
    """The helper's process (never started)."""

    def running(self) -> bool:
        return True

    def close(self) -> None:
        return None


class _Conn:
    """The helper's end of the pipe: answers as the helper does and moves
    the fake Windows status; nothing reaches pnputil."""

    def __init__(self) -> None:
        self._answer: dict = {}

    def send(self, req: dict) -> None:
        op, ids = req["op"], list(req.get("ids", []))
        W["helper_ops"].append([op, ids])
        if op == "disable":
            W["disabled"].append(ids)
        if op == "enable":
            W["enable_requests"].append(ids)
        for i in ids:
            W["status"][i] = "disabled" if op == "disable" else "enabled"
        self._answer = {"ok": True, "results": {i: "done" for i in ids}}

    def poll(self, timeout: float = 0.0) -> bool:
        return True

    def recv(self) -> dict:
        return self._answer

    def close(self) -> None:
        return None


class _Listener:
    """The pipe's listening end: accept() returns once the launcher ran
    (bounded), close() wakes it."""

    def __init__(self, address: str, authkey: bytes) -> None:
        import threading

        self.launched = threading.Event()
        self.closed = False
        W["listener"] = self

    def accept(self) -> _Conn:
        self.launched.wait(30.0)
        if self.closed or not self.launched.is_set():
            raise OSError("closed")
        return _Conn()

    def close(self) -> None:
        self.closed = True
        self.launched.set()


def _launcher(file: str, parameters: str) -> _Process:
    """ShellExecuteExW "runas" stand-in: no process, no elevation."""
    import gremlin.device_disable as dd

    W["helper_starts"] += 1
    ok, _error = W["helper_answer"]
    if not ok:
        raise dd.Refused()
    W["listener"].launched.set()
    return _Process()


def _install_disabler_fake() -> None:
    """The real device_disable.DeviceDisabler with its Windows edge faked
    (launcher, pipe listener, device status): manager() returns it before
    the program is built, so the start's recovery uses it too."""
    import gremlin.device_disable as dd

    disabler = dd.DeviceDisabler(
        launcher=_launcher,
        listener_factory=_Listener,
        status_reader=lambda i: W["status"].get(i, "enabled"),
        connect_timeout_s=20.0,
    )
    for name in ("enable_pending", "recover_at_start", "on_device_arrival"):
        real = getattr(disabler, name)

        def counted(real: Any = real, name: str = name) -> None:  # noqa: ANN401
            W["calls"][name] = W["calls"].get(name, 0) + 1
            real()

        setattr(disabler, name, counted)
    dd._manager = disabler  # noqa: SLF001
    dd.manager = lambda: disabler
    W["disabler"] = disabler
    if len(sys.argv) > 1 and sys.argv[1] == "2":
        # Run 1 left the VKB "disabled" (as after a crash): Windows has it so.
        W["status"][_VKB] = "disabled"


def _dis() -> Any:  # noqa: ANN401
    return W["disabler"]


def _idle() -> None:
    assert _dis().wait_idle(10.0), "the disabler stayed busy"


def _before_start(j: Journey) -> None:
    _install_disabler_fake()
    _install_fakes()


def main() -> None:
    which = sys.argv[1] if len(sys.argv) > 1 else "1"
    Journey(_before_start).run(story_first if which == "1" else story_restart)


# +-------------------------------------------------------------------------
# | Pytest side

_PROGRAM_FILES = [
    ROOT / "gremlin" / "screen_saver_mode.py",
    ROOT / "gremlin" / "hid_report_scan.py",
    ROOT / "gremlin" / "power_requests.py",
    ROOT / "gremlin" / "device_disable.py",
    ROOT / "qml" / "WindowScreenSaverMode.qml",
]


@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory) -> list[dict]:
    missing = [str(p.relative_to(ROOT)) for p in _PROGRAM_FILES if not p.exists()]
    assert not missing, f"Screen Saver Mode not built: {missing}"
    home = tmp_path_factory.mktemp("ssm_e2e")
    return [run_journey(__file__, home, n) for n in ("1", "2")]


def _v(out: dict, section: str, key: str) -> Any:  # noqa: ANN401
    if key not in out:
        pytest.fail(
            f"The journey never reached {key!r} (part {section}).\n"
            f"Part error: {out.get(f'err:{section}', '(none)')}\n"
            f"Journey error: {out.get('error', '(none)')}\n{out.get('traceback', '')}\n"
            f"--- stderr\n{out.get('_stderr', '')}"
        )
    return out[key]


def test_s1_tools_screen_saver_mode_opens_the_window(runs: list[dict]) -> None:
    first = runs[0]
    assert _v(first, "s1", "s1Open") is True
    assert _v(first, "s1", "s1Missing") == []
    assert _v(first, "s1", "s1Old") == []


def test_s2_off_at_first_no_listening_and_no_timer(runs: list[dict]) -> None:
    first = runs[0]
    assert first["startCfg"]["enabled"] is False
    assert first["startClockStarts"] == 0, "the input clock started while off"
    assert _v(first, "s2on", "s2SwitchAtStart") is False
    assert _v(first, "s2on", "s2TicksWhileOff") == 0, "a timer ticks while off"


def test_s2_switching_on_writes_the_setting_and_starts_listening(
    runs: list[dict],
) -> None:
    first = runs[0]
    assert _v(first, "s2on", "s2CfgOn") is True
    assert _v(first, "s2on", "s2MgrOn") is True
    assert _v(first, "s2on", "s2ClockStarted") >= 1
    assert _v(first, "s2on", "s2Listening") is True
    assert _v(first, "s2on", "s2TicksWhileOn") >= 1, "no 1 s timer while on"


def test_s2_switching_off_stops_everything(runs: list[dict]) -> None:
    second = runs[1]
    assert _v(second, "window", "offCfg") is False
    assert _v(second, "window", "offStops") >= 1
    assert _v(second, "window", "offListening") is False
    assert _v(second, "window", "offTicks") == 0, "the timer still ticks while off"
    assert _v(second, "window", "offFired") == 0, "off, but the action was done"


def test_s3_gremlins_own_input_does_not_count_other_input_does(
    runs: list[dict],
) -> None:
    first = runs[0]
    assert _v(first, "s6", "s3OwnIdle") == 200
    assert _v(first, "s6", "s3OwnFired") == 1
    assert _v(first, "s6", "s3OtherHeld") == 0


def test_s4_both_timers_are_on_at_first(runs: list[dict]) -> None:
    first = runs[0]
    assert first["startCfg"]["screen-saver-on"] is True
    assert first["startCfg"]["power-off-on"] is True
    assert first["startCfg"]["screen-saver-wait-s"] == 0
    assert first["startCfg"]["power-off-wait-s"] == 0
    assert _v(first, "s5", "s4Default") == [True, True]


def test_s5_windows_time_is_used_and_followed(runs: list[dict]) -> None:
    first = runs[0]
    assert _v(first, "s5", "s5Wait") == [600, 600, True]
    assert _v(first, "s5", "s5WindowsWaitText") == "Windows' display-off time (10 min)"
    assert _v(first, "s5", "s5SaverWindowsWaitText") == (
        "Windows' screen saver wait (never)"
    )
    assert _v(first, "s5", "s5Followed") == 900


def test_s5_a_typed_time_replaces_it_until_cleared(runs: list[dict]) -> None:
    first = runs[0]
    assert _v(first, "s5", "s5OverrideCfg") == 420
    assert _v(first, "s5", "s5OverrideMgr") == 420
    assert _v(first, "s5", "s5OtherRow") == 0, "typing in one row changed the other"
    assert _v(first, "s5", "s5Override") == [420, False]
    assert _v(first, "s5", "s5OverrideBefore") == 0
    assert _v(first, "s5", "s5OverrideFired") == 1
    assert _v(first, "s5", "s5ClearedCfg") == 0
    assert _v(first, "s5", "s5Cleared") == [900, True]


def test_s6_the_action_is_done_once_per_idle_period(runs: list[dict]) -> None:
    first = runs[0]
    assert _v(first, "s6", "s6Before") == 0
    assert _v(first, "s6", "s6At") == 1
    assert _v(first, "s6", "s6Fired") is True
    assert _v(first, "s6", "s6Once") == 1
    assert _v(first, "s6", "s6Reset") == [False, 1]
    assert _v(first, "s6", "s6Again") == 2


@pytest.mark.parametrize(
    ("part", "key", "hold", "words"),
    [
        ("s7", "fullscreen", "fullscreen", "full"),
        (
            "s15",
            "display",
            "display_request",
            "On hold: a program is keeping the display on",
        ),
        ("s11", "locked", "locked", ""),
    ],
    ids=["s7_full_screen", "s15_display_flag", "s11_locked"],
)
def test_s7_s11_s15_a_hold_waits_and_the_countdown_starts_again(
    runs: list[dict], part: str, key: str, hold: str, words: str
) -> None:
    first = runs[0]
    assert _v(first, part, f"{key}Held") == [0, hold]
    if words:
        assert words.lower() in _v(first, part, f"{key}HoldText").lower()
    if key == "fullscreen":
        # S19: the program in front is named.
        assert "full-screen program is in front (StarCitizen.exe)" in _v(
            first, part, f"{key}HoldText"
        )
    # Ended: idle counted from the end of the hold.
    assert _v(first, part, f"{key}AfterEnd") == 0
    assert _v(first, part, f"{key}BeforeWait") == 0
    assert _v(first, part, f"{key}AfterWait") == 1


def test_s7_hold_off_switched_off_full_screen_does_not_hold(runs: list[dict]) -> None:
    first = runs[0]
    assert first["startCfg"]["hold-fullscreen"] is True
    assert _v(first, "s7off", "s7OffCfg") is False
    assert _v(first, "s7off", "s7OffMgr") is False
    assert _v(first, "s7off", "s7OffFired") == 1


def test_s8_no_screen_saver_chosen_does_nothing_and_says_so(runs: list[dict]) -> None:
    first = runs[0]
    assert _v(first, "s8", "s8Problem") == ["no_screen_saver", ""]
    # Only the screen saver row stops; power off still fires.
    assert _v(first, "s8", "s8Started") == [[], 1]
    assert _v(first, "s8", "s8Text") == "No screen saver is chosen in Windows."
    assert _v(first, "s8", "s8OffRowText") == ""


def test_s4_s6_the_two_timers_fire_in_order_each_once(runs: list[dict]) -> None:
    first = runs[0]
    path = "C:\\Windows\\System32\\Mystify.scr"
    assert _v(first, "s8", "s8Waits") == [120, 300]
    assert _v(first, "s8", "s8SaverWindowsWait") == "Windows' screen saver wait (2 min)"
    assert _v(first, "s8", "s8Countdowns") == [
        "Screen saver in 2 min",
        "Power off displays in 5 min",
    ]
    assert _v(first, "s8", "s8Before") == [[], 0]
    assert _v(first, "s8", "s8SaverFired") == [[path], 0]
    assert _v(first, "s8", "s8SaverDone") is True
    assert _v(first, "s8", "s8OffBefore") == 0
    assert _v(first, "s8", "s8OffFired") == [[path], 1]
    assert _v(first, "s8", "s8Once") == [1, 1]


def test_s5_typed_waits_per_row_and_the_order_warning(runs: list[dict]) -> None:
    first = runs[0]
    assert _v(first, "s8", "s8SaverTypedCfg") == 180
    assert _v(first, "s8", "s8NoWarning") == ""
    assert _v(first, "s8", "s8OffTypedCfg") == 120
    assert _v(first, "s8", "s8Warning") == _WARNING
    assert _v(first, "s8", "s8TypedWaits") == [180, 120, False, False]
    # Both still work: power off first, the screen saver after.
    assert _v(first, "s8", "s8OffFirst") == [0, 1]
    assert _v(first, "s8", "s8SaverAfter") == [1, 1]


def test_s5_clearing_each_row_goes_back_to_windows_time(runs: list[dict]) -> None:
    first = runs[0]
    assert _v(first, "s8", "s8ClearedCfg") == [0, 0]
    assert _v(first, "s8", "s8Cleared") == [120, 300, True, True]
    assert _v(first, "s8", "s8ClearedWarning") == ""


def test_s4_a_timer_switched_off_does_nothing_the_other_still_fires(
    runs: list[dict],
) -> None:
    first = runs[0]
    assert _v(first, "s8", "s8SaverOffCfg") is False
    assert _v(first, "s8", "s8SaverOffMgr") is False
    assert _v(first, "s8", "s8SaverOffFired") == [0, 1]
    assert _v(first, "s8", "s8SaverOffCountdown") == ""
    assert _v(first, "s8", "s8SaverBackCfg") is True


def test_s6_s20_keeping_the_displays_off_and_the_wake_count(
    runs: list[dict],
) -> None:
    first = runs[0]
    assert _v(first, "s20", "s20Keeping") == [True, 0, 1]
    # Three display-ON reports: three re-sends, counted.
    assert _v(first, "s20", "s20Wakes") == [True, 3, 4]
    assert _v(first, "s20", "s20Text") == _WAKES
    # Input ended it: no more re-sends; the last period's count stays shown.
    assert _v(first, "s20", "s20AfterInput") == [False, 3, 4]
    assert _v(first, "s20", "s20TextAfter") == _WAKES


def test_s5_windows_never_and_no_typed_time_does_nothing(runs: list[dict]) -> None:
    first = runs[0]
    assert _v(first, "never", "neverProblem") == ["windows_never", 0]
    assert _v(first, "never", "neverText") == (
        "Windows never turns the display off: type a time to use this timer."
    )


def test_s9_status_line(runs: list[dict]) -> None:
    first = runs[0]
    assert "Listening to the keyboard and mouse" in _v(first, "s2on", "s9ListeningText")
    assert _v(first, "s2on", "s9OnlyWhileOpen") is True
    assert _v(first, "s6", "s9IdleText").strip()
    assert _v(first, "s6", "s9WindowsIdleText").strip()


def test_s9_not_listening_is_said_and_nothing_is_done(runs: list[dict]) -> None:
    first = runs[0]
    assert _v(first, "s9", "s9NotListening") == [False, "not_listening", 0]
    text = _v(first, "s9", "s9NotListeningText")
    assert text and "Listening to the keyboard and mouse" != text


def test_s10_setting_changes_go_into_history_by_their_shown_names(
    runs: list[dict],
) -> None:
    first = runs[0]
    keys = _v(first, "s10", "s10Keys")
    assert "global/screen-saver-mode/enabled" in keys
    for name in ("screen-saver-on", "screen-saver-wait-s", "power-off-wait-s"):
        assert f"global/screen-saver-mode/{name}" in keys, keys
    assert not any(k.endswith(("/action", "/wait-override-s")) for k in keys), keys
    titles = " | ".join(_v(first, "s10", "s10Entries"))
    # Named as the window shows them (contract-4).
    assert "Changed Screen Saver Mode" in titles, titles
    assert "Hold off during full-screen programs" in titles, titles
    assert "Screen saver wait" in titles, titles
    assert "Power off wait" in titles, titles
    assert "Changed Screen saver" in titles or ", Screen saver," in titles, titles


def test_s12_refresh_devices_lists_the_devices_that_never_go_quiet(
    runs: list[dict],
) -> None:
    first = runs[0]
    assert _v(first, "s12", "s12EmptyAtFirst") == [0, 0]
    assert _v(first, "s12", "s12Count") == 2
    assert _v(first, "s12", "s12Rows") == [True, True, True]
    assert _v(first, "s12", "s12Scans") == 1
    assert _v(first, "s12", "s12Description") is True


_SAVED = [
    ["VKBSim NXT SEM THQ FSM.GA", _VKB],
    ["PD200X Microphone (buttons)", _PD],
]


def test_s27_refresh_devices_result_is_saved(runs: list[dict]) -> None:
    first = runs[0]
    saved = _v(first, "s21", "s27Saved")
    assert [[d["name"], d["instance_id"]] for d in saved] == _SAVED
    # Before the first Refresh Devices nothing is disabled.
    assert _v(first, "s20", "s20Disabled") == []


def test_s25_a_refresh_that_fills_the_list_starts_the_helper(
    runs: list[dict],
) -> None:
    first = runs[0]
    # Not before the list was filled (S27 empty), then once.
    assert _v(first, "s20", "s20Starts") == 0
    assert _v(first, "s21", "s25Running") is True
    assert _v(first, "s21", "s25StartsAfterRefresh") == 1
    assert _v(first, "s21", "s26HiddenWhileRunning") == ""


def test_s21_s23_power_off_disables_the_saved_list_and_input_enables(
    runs: list[dict],
) -> None:
    first = runs[0]
    disabled, power_off = _v(first, "s21", "s21Disabled")
    assert disabled == [[_VKB, _PD]]
    assert power_off == 1
    assert _v(first, "s21", "s22Journal") == {_VKB: "disabled", _PD: "disabled"}
    assert _v(first, "s21", "s23Enabled") == [[_VKB, _PD]]
    assert _v(first, "s21", "s23Journal") == {_VKB: "enabled", _PD: "enabled"}
    assert _v(first, "s21", "s23Arrivals") == 1


def test_s26_refused_is_said_not_asked_again_until_try_again(
    runs: list[dict],
) -> None:
    first = runs[0]
    assert _v(first, "s21", "s26Text") is True
    assert _v(first, "s21", "s26TryAgainShown") is True
    assert _v(first, "s21", "s26StartsAfterRefusal") == 1
    assert _v(first, "s21", "s26DisabledWithout") == []
    assert _v(first, "s21", "s26TryAgainRunning") is True
    assert _v(first, "s21", "s26TryAgainStarts") == 2
    assert _v(first, "s21", "s26TextAfter") == ""


def test_restart_s24_s25_s27_recovery_helper_and_saved_list(
    runs: list[dict],
) -> None:
    second = runs[1]
    assert second["recoveries"] == 1
    assert second["helperRunningAtStart"] is True
    assert second["recoveredEnable"] == [[_VKB]]
    assert second["recoveredJournal"] == "enabled"
    assert second["helperStartsAtStart"] == 1
    assert _v(second, "window", "savedShown") == 2
    rows = _v(second, "window", "savedRows")
    assert "VKBSim NXT SEM THQ FSM.GA" in rows
    assert "PD200X Microphone (buttons)" in rows
    # Switching the mode off re-enables what is pending (lead 2026-11-15).
    assert _v(second, "window", "offEnables") == 1


def test_s13_refresh_programs_refused_is_said(runs: list[dict]) -> None:
    first = runs[0]
    assert _v(first, "s13", "s13Refused") is True
    assert _v(first, "s13", "s13RefusedCount") == 0


def test_s13_refresh_programs_lists_the_display_half(runs: list[dict]) -> None:
    first = runs[0]
    assert _v(first, "s13", "s13Count") == 2
    assert _v(first, "s13", "s13Lists") == 1, "one press, one elevated check"
    assert _v(first, "s13", "s13SystemCount") == 0, "Programs filled System too"
    assert _v(first, "s13", "s13Rows") == [True, True, True]
    assert _v(first, "s13", "s13AlsoAwake") == ["also keeps the PC awake"]
    assert _v(first, "s13", "s13Description") is True


def test_s14_ignore_this_program_calls_set_ignored(runs: list[dict]) -> None:
    first = runs[0]
    assert _v(first, "s13", "s14Switches") == 2
    # The Programs rows by name (power_requests.split): chrome.exe first.
    assert _v(first, "s13", "s14Asked") == [["chrome.exe", True, "PROCESS"]]
    assert _v(first, "s13", "s14On") is True
    assert _v(first, "s13", "s14ProgramsMessage") == (
        "chrome.exe is ignored: it no longer keeps the display on."
    )


def test_s17_refresh_system_runs_its_own_check_and_fills_its_list(
    runs: list[dict],
) -> None:
    first = runs[0]
    assert _v(first, "s13", "s17Count") == 1
    assert _v(first, "s13", "s17Lists") == 1, "one press, one elevated check"
    assert _v(first, "s13", "s17ProgramsCount") == 2, "System changed Programs"
    assert _v(first, "s13", "s17Description") is True
    assert _v(first, "s13", "s17Message") == (
        f"{_DRIVER} is ignored: it no longer keeps the PC awake."
    )
    assert "Administrator rights were refused." in _v(
        first, "s13", "s17ProgramsMessage"
    )


def test_s14_a_drivers_row_has_the_switch_and_passes_its_kind(
    runs: list[dict],
) -> None:
    """S14 widened (user, 28 a): the USB Audio driver's row (in System, S17)
    shows its name, "(driver)" and the detail line, and its switch calls
    set_ignored with kind "DRIVER"."""
    first = runs[0]
    assert _v(first, "s13", "s14DriverRow") == [True, True, True]
    assert _v(first, "s13", "s14Driver") == [_DRIVER, True, "DRIVER"]
    assert _v(first, "s13", "s14DriverOn") is True


def test_s14_refused_switch_goes_back_and_is_said(runs: list[dict]) -> None:
    first = runs[0]
    assert _v(first, "s13", "s14Asked2")[-1] == ["RustDesk.exe", True, "PROCESS"]
    assert _v(first, "s13", "s14RefusedBack") is False
    assert _v(first, "s13", "s14RefusedText") is True


def test_s18_last_reset_by_names_the_source(runs: list[dict]) -> None:
    first = runs[0]
    assert _v(first, "s18", "s18Program") == (
        "last reset by: input sent by a program, 3 times a minute"
    )
    assert _v(first, "s18", "s18Keyboard") == (
        "last reset by: Logitech G915 (keyboard), just now"
    )
    # Looked up once per device handle, never per input.
    assert _v(first, "s18", "s18Lookups") == [0x5150]


def test_restart_the_settings_carry_over(runs: list[dict]) -> None:
    first, second = runs
    left = _v(first, "leave", "leftCfg")
    assert left == {
        "enabled": True,
        "screen-saver-on": False,
        "screen-saver-wait-s": 0,
        "power-off-on": True,
        "power-off-wait-s": 420,
        "hold-fullscreen": False,
    }
    assert second["cfg"] == left
    assert _v(second, "mgr", "mgr") == [True, False, 0, True, 420, False]


def test_restart_s2_on_listens_from_program_start(runs: list[dict]) -> None:
    second = runs[1]
    assert second["clockStartedAtStart"] >= 1
    assert _v(second, "mgr", "ticking") is True
    assert _v(second, "window", "switchOn") is True
    assert _v(second, "window", "holdSwitch") is False
    assert _v(second, "window", "rows") == [False, True, "", "7"]


def test_s2_program_start_follows_the_saved_settings() -> None:
    # The journey calls what main() calls; main() must call it before exec().
    text = (ROOT / "joystick_gremlin.py").read_text(encoding="utf-8")
    body = text[text.index("def main(") :]
    start = body.find("gremlin.ui.screen_saver_mode_model.start()")
    assert 0 < start < body.index("app.exec()")


def test_s29_s31_nothing_ticked_waits_and_says_so(runs: list[dict]) -> None:
    first = runs[0]
    assert _v(first, "s31", "s31SavedAtFirst") == []
    assert _v(first, "s31", "s31Hold") == "no_wake_device"
    assert _v(first, "s31", "s31Fired") == [0, 0], "a timer ran with nothing ticked"
    assert _v(first, "s31", "s31Text") is True, "no Waiting line"


def test_s28_the_wake_pc_tab_lists_every_device_unticked(runs: list[dict]) -> None:
    first = runs[0]
    assert _v(first, "s28", "s28MissingTabs") == []
    assert _v(first, "s28", "s28Rows") == 3, "one row per physical device"
    assert _v(first, "s28", "s28Reads") >= 1
    assert _v(first, "s28", "s28Shown") == [True, True, True, True, True]
    assert _v(first, "s28", "s29Ticks") == [3, 0], "a device started ticked"


def test_s30_a_press_ticks_and_saves_movement_does_not(runs: list[dict]) -> None:
    first = runs[0]
    assert _v(first, "s28", "s30MoveTicked") == [], "a move or key up ticked"
    assert _v(first, "s28", "s30Key") == [True, "key"]
    assert _v(first, "s28", "s30Click") == [True, "click"]
    assert _v(first, "s28", "s30Ticked") == sorted([_G915, _VIPER])
    assert _v(first, "s28", "s30Notes") == [True, True]
    assert _v(first, "s28", "s31HoldAfterTick") != "no_wake_device"
    assert _v(first, "s28", "s31TextAfterTick") is False


def test_s33_rows_light_up_in_use_now_without_ticking(runs: list[dict]) -> None:
    first = runs[0]
    assert _v(first, "s28", "s33FadedAfterPresses") == []
    assert _v(first, "s28", "s33MoveLit") == [["Steam Controller", "in use now"]]
    assert _v(first, "s28", "s33MoveTicked") == sorted([_G915, _VIPER])
    assert _v(first, "s28", "s33Faded") == [], "the highlight stayed"
    assert _v(first, "s28", "s33PressLit") == [
        ["Logitech G915", "ticked when you pressed a key · in use now"]
    ]
    assert _v(first, "s28", "s33ClosedLit") is False, "lit with the tab closed"


def test_s30_detection_only_while_the_tab_is_open(runs: list[dict]) -> None:
    first = runs[0]
    assert _v(first, "s28", "s30ClosedTicked") == sorted([_G915, _VIPER])
    assert _v(first, "s28", "s30ClosedListening") is True


def test_s3_s28_only_ticked_devices_and_programs_reset_the_idle_clock(
    runs: list[dict],
) -> None:
    first = runs[0]
    assert _v(first, "s3wake", "s3UntickedIdle") == 100, "an unticked device counted"
    assert _v(first, "s3wake", "s3UntickedFired") == 1
    assert _v(first, "s3wake", "s3TickedIdle") == [0, False]
    assert _v(first, "s3wake", "s3TickedMoveIdle") == 0
    assert _v(first, "s3wake", "s3ProgramIdle") == 0


def test_restart_s28_the_ticks_carry_over_and_count(runs: list[dict]) -> None:
    second = runs[1]
    assert _v(second, "wake", "wakeTicked") == sorted([_G915, _VIPER])
    assert _v(second, "wake", "wakeHold") != "no_wake_device"
    assert _v(second, "wake", "wakeUntickedIdle") == 100
    assert _v(second, "wake", "wakeTickedIdle") == 0


def test_restart_s28_an_unplugged_ticked_device_keeps_its_tick(
    runs: list[dict],
) -> None:
    second = runs[1]
    assert _v(second, "wake", "wakeRows") == 3
    assert _v(second, "wake", "wakeNotConnected") == [True, True]
    assert _v(second, "wake", "wakeShownTicked") == 2
    assert _v(second, "wake", "wakeTickedAfterOpen") == sorted([_G915, _VIPER])


def test_the_journeys_had_no_errors(runs: list[dict]) -> None:
    for out in runs:
        assert "error" not in out, out.get("traceback")
        assert out.get("_errors") == []


if __name__ == "__main__":
    main()
