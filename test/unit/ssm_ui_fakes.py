# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Stand-ins for gremlin.screen_saver_mode, gremlin.hid_report_scan,
gremlin.power_requests and gremlin.device_disable (12 S1-S27, contract-4
and contract-5's APIs), for test_ssm_ui.py and ssm_ui_smoke.py: the
window's tests never listen to the keyboard or mouse, read HID devices,
run powercfg, start the device helper, disable or enable a device or ask
for administrator rights. Wake PC (contract-6): the keyboards and mice are
a list here, presses are sent by the test (press())."""

from __future__ import annotations

import sys
import threading
import types
from dataclasses import dataclass, field, replace
from typing import Any, Callable

# A driver's request as powercfg names it (the user's PC, 2026-11-15).
DRIVER_NAME = "USB Audio 2.0 (USB\\VID_0DB0&PID_CD0E&MI_00\\9&9c4d365&0&0000)"
DRIVER_DETAIL = "An audio stream is currently in use."


@dataclass
class Settings:
    enabled: bool = False
    screen_saver_on: bool = True
    screen_saver_wait_s: int = 0
    power_off_on: bool = True
    power_off_wait_s: int = 0
    hold_fullscreen: bool = True


@dataclass
class Status:
    enabled: bool = False
    listening: bool = False
    idle_s: float = 0.0
    windows_idle_s: float = 0.0
    saver_wait_s: int = 0
    saver_windows_wait_s: int = 0
    saver_from_windows: bool = True
    saver_fired: bool = False
    saver_remaining_s: float = 0.0
    off_wait_s: int = 0
    off_windows_wait_s: int = 0
    off_from_windows: bool = True
    off_fired: bool = False
    off_remaining_s: float = 0.0
    keeping_off: bool = False
    wakes: int = 0
    hold: str = ""
    hold_program: str = ""
    problem: str = ""  # "" | "not_listening"
    saver_problem: str = ""  # "" | "no_screen_saver" | "windows_never"
    off_problem: str = ""  # "" | "windows_never"
    last_reset_by: str = ""
    last_reset_kind: str = ""  # "keyboard" | "mouse" | "program" | ""
    last_reset_age_s: float = 0.0
    program_input_per_min: int = 0


@dataclass
class DeviceRate:
    name: str
    instance_id: str
    usage_page: int
    usage: int
    reports_per_s: float


@dataclass(frozen=True)
class PresentDevice:
    instance_id: str
    path: str = ""
    description: str = ""


@dataclass
class ProgramRequest:
    name: str
    path: str
    kinds: list[str]
    ignored: bool
    kind: str = "PROCESS"  # "PROCESS" | "DRIVER" | "SERVICE"
    detail: str = ""
    also_awake: bool = False  # Display plus System, Awaymode or Execution
    override_types: list[str] = field(default_factory=list)


_AWAKE_KINDS = ("System", "Awaymode", "Execution")


def split(programs: list) -> tuple[list, list]:
    """power_requests.split's rules (contract-3): Display callers go in
    Programs; System, Awaymode or Execution without Display in System;
    ignored callers not asking now by their override types. Not-ignored
    first, then by name."""
    display: list = []
    system: list = []
    for row in programs:
        if "Display" in row.kinds:
            display.append(row)
        elif any(k in row.kinds for k in _AWAKE_KINDS):
            system.append(row)
        elif row.ignored and not row.kinds:
            (display if "DISPLAY" in row.override_types else system).append(row)

    def order(row: ProgramRequest) -> tuple[bool, str, str]:
        return (row.ignored, row.name.lower(), row.kind)

    return sorted(display, key=order), sorted(system, key=order)


HOLD_NO_WAKE_DEVICE = "no_wake_device"


@dataclass(frozen=True)
class InputDevice:
    physical_id: str
    name: str
    kinds: tuple[str, ...]


# Two keyboards and mice Windows reports (the user's PC, 2026-11-16).
INPUT_DEVICES = [
    InputDevice(r"USB\VID_046D&PID_C33F\1", "Logitech G815", ("keyboard",)),
    InputDevice(r"USB\VID_28DE&PID_1102\2", "Steam Controller", ("keyboard", "mouse")),
]


@dataclass
class RequestsResult:
    ok: bool
    error: str
    programs: list[ProgramRequest] = field(default_factory=list)


class FakeManager:
    """Windows' times: screen saver 10 min, display off 5 min."""

    SAVER_WINDOWS_S = 600
    OFF_WINDOWS_S = 300

    def __init__(self) -> None:
        self._settings = Settings()
        self.applied: list[Settings] = []
        self.extra: dict[str, Any] = {}
        self.shut = False
        self.before_power_off: Callable[[], Any] | None = None
        self.after_input: Callable[[], None] | None = None
        # Wake PC (contract-6): every set_wake_devices call, the press
        # listener, and the detection calls.
        self.wake_sets: list[list[str]] = []
        self.press_listener: Callable[[str, str], None] | None = None
        self.detection: list[str] = []
        self.detecting = False
        # In use now (contract-7, S33): the activity listener.
        self.activity_listener: Callable[[str], None] | None = None

    def set_wake_devices(self, physical_ids: Any) -> None:  # noqa: ANN401
        self.wake_sets.append(list(physical_ids))

    def set_press_listener(self, listener: Callable[[str, str], None] | None) -> None:
        self.press_listener = listener

    def set_activity_listener(self, listener: Callable[[str], None] | None) -> None:
        self.activity_listener = listener

    def activity(self, physical_id: str) -> None:
        """Any keyboard or mouse input from a device (movement too), as the
        core reports it (main thread), only while a listener is set."""
        if self.activity_listener is not None:
            self.activity_listener(physical_id)

    def start_detection(self) -> bool:
        self.detection.append("start")
        self.detecting = True
        return True

    def stop_detection(self) -> None:
        self.detection.append("stop")
        self.detecting = False

    def press(self, physical_id: str, kind: str) -> None:
        """A key or button down from a device, as the core reports it
        (main thread), only while a listener is set."""
        if self.press_listener is not None:
            self.press_listener(physical_id, kind)

    def set_device_hooks(
        self,
        before_power_off: Callable[[], Any] | None,
        after_input: Callable[[], None] | None,
    ) -> None:
        self.before_power_off = before_power_off
        self.after_input = after_input

    def apply(self, settings: Settings) -> None:
        self._settings = replace(settings)
        self.applied.append(replace(settings))

    def settings(self) -> Settings:
        return replace(self._settings)

    def status(self) -> Status:
        s = self._settings
        st = Status(
            enabled=s.enabled,
            listening=s.enabled,
            saver_windows_wait_s=self.SAVER_WINDOWS_S,
            saver_wait_s=s.screen_saver_wait_s or self.SAVER_WINDOWS_S,
            saver_from_windows=not s.screen_saver_wait_s,
            off_windows_wait_s=self.OFF_WINDOWS_S,
            off_wait_s=s.power_off_wait_s or self.OFF_WINDOWS_S,
            off_from_windows=not s.power_off_wait_s,
        )
        for key, value in self.extra.items():
            setattr(st, key, value)
        return st

    def tick(self) -> None:
        return None

    def shutdown(self) -> None:
        self.shut = True


HELPER_TEXT = "Devices can't be disabled: the helper isn't running"


class FakeDisabler:
    """device_disable.DeviceDisabler's API (contract-5); records the calls.
    start_helper answers with `answer` at once, or holds the callback
    when `hold` is set (the user still at the confirmation)."""

    def __init__(self) -> None:
        self.running = False
        self.answer: tuple[bool, str] = (True, "")
        self.hold = False
        self.waiting: Callable[[bool, str], None] | None = None
        self.starts = 0
        self.stops = 0
        self.disabled: list[list[tuple[str, str]]] = []
        self.enables = 0
        self.arrivals = 0
        self.recoveries = 0
        self.idle = True  # no disable job queued or running

    def wait_idle(self, timeout: float) -> bool:
        return self.idle

    def helper_running(self) -> bool:
        return self.running

    def start_helper(self, on_done: Callable[[bool, str], None]) -> None:
        self.starts += 1
        if self.hold:
            self.waiting = on_done
            return
        self.finish(*self.answer, on_done=on_done)

    def finish(
        self, ok: bool, error: str = "", on_done: Callable | None = None
    ) -> None:
        done = on_done or self.waiting
        self.waiting = None
        self.running = bool(ok)
        if done is not None:
            done(bool(ok), str(error))

    def stop_helper(self) -> None:
        self.stops += 1
        self.running = False

    def disable(self, devices: list[tuple[str, str]]) -> None:
        self.disabled.append(list(devices))

    def enable_pending(self) -> None:
        self.enables += 1

    def recover_at_start(self) -> None:
        self.recoveries += 1

    def on_device_arrival(self) -> None:
        self.arrivals += 1

    def status_text(self) -> str:
        return "" if self.running else HELPER_TEXT


class Calls:
    """What the fake checks were asked, and what they answer."""

    def __init__(self) -> None:
        self.scans: list[float] = []
        self.lists = 0
        self.ignores: list[tuple[str, bool, str]] = []
        self.devices = [
            DeviceRate(
                "PD200X Microphone (buttons)", "HID\\VID_1&PID_2\\1", 12, 1, 18.4
            ),
            DeviceRate("VKBSim NXT SEM THQ FSM.GA", "HID\\VID_3&PID_4\\1", 1, 4, 13.0),
        ]
        # The HID devices connected now: (name, instance id); None = the ones
        # a Refresh Devices finds. name_reads: the ids whose name was read.
        self.present: list[tuple[str, str]] | None = None
        self.present_reads = 0
        self.name_reads: list[str] = []
        self.unreadable_names = False
        self.requests = RequestsResult(
            True,
            "",
            [
                ProgramRequest(
                    "RustDesk.exe",
                    "C:\\RustDesk\\RustDesk.exe",
                    ["Display", "System"],
                    False,
                    also_awake=True,
                ),
                ProgramRequest(
                    "chrome.exe",
                    "C:\\Chrome\\chrome.exe",
                    ["Display"],
                    True,
                    detail="a video is playing",
                ),
                ProgramRequest(
                    DRIVER_NAME,
                    "",
                    ["System"],
                    False,
                    kind="DRIVER",
                    detail=DRIVER_DETAIL,
                ),
                ProgramRequest(
                    "claude.exe",
                    "C:\\Claude\\claude.exe",
                    ["Execution"],
                    False,
                    detail="Electron",
                ),
                # Ignored, not asking now: placed by its override types.
                ProgramRequest(
                    "FxSound Audio Enhancer",
                    "",
                    [],
                    True,
                    kind="DRIVER",
                    override_types=["SYSTEM"],
                ),
            ],
        )
        self.ignore_answer: tuple[bool, str] = (True, "")
        # Set by a test to hold a check open (the busy text); bounded wait.
        self.gate: threading.Event | None = None
        self.disabler = FakeDisabler()
        # Wake PC: what WindowsApi.input_devices answers, and the threads
        # it was read on.
        self.input_devices: list[InputDevice] = list(INPUT_DEVICES)
        self.input_reads: list[str] = []

    def connected(self) -> list[tuple[str, str]]:
        if self.present is not None:
            return list(self.present)
        return [(d.name, d.instance_id) for d in self.devices]

    def _wait_gate(self) -> None:
        if self.gate is not None:
            self.gate.wait(5.0)


def install(target: Any = None) -> tuple[FakeManager, Calls]:  # noqa: ANN401
    """Puts the three stand-ins in sys.modules (and on the gremlin package).
    target: a pytest MonkeyPatch (undone after the test) or None (a
    subprocess)."""
    import gremlin

    manager = FakeManager()
    calls = Calls()

    core = types.ModuleType("gremlin.screen_saver_mode")
    core.Settings = Settings  # type: ignore[attr-defined]
    core.Status = Status  # type: ignore[attr-defined]
    core.manager = lambda: manager  # type: ignore[attr-defined]
    core.hold_now = lambda: ("", "")  # type: ignore[attr-defined]
    core.HOLD_NO_WAKE_DEVICE = HOLD_NO_WAKE_DEVICE  # type: ignore[attr-defined]
    core.InputDevice = InputDevice  # type: ignore[attr-defined]

    class WindowsApi:
        def input_devices(self) -> list[InputDevice]:
            calls.input_reads.append(threading.current_thread().name)
            calls._wait_gate()
            return list(calls.input_devices)

    core.WindowsApi = WindowsApi  # type: ignore[attr-defined]

    scan_mod = types.ModuleType("gremlin.hid_report_scan")

    def scan(
        seconds: float = 4.0, should_stop: Callable[[], bool] | None = None
    ) -> list:
        calls.scans.append(seconds)
        calls._wait_gate()
        return list(calls.devices)

    def present() -> list[PresentDevice]:
        calls.present_reads += 1
        return [PresentDevice(i) for _n, i in calls.connected()]

    def device_name(device: PresentDevice) -> str:
        calls.name_reads.append(device.instance_id)
        if calls.unreadable_names:
            return ""
        return dict((i, n) for n, i in calls.connected())[device.instance_id]

    scan_mod.PresentDevice = PresentDevice  # type: ignore[attr-defined]
    scan_mod.present = present  # type: ignore[attr-defined]
    scan_mod.device_name = device_name  # type: ignore[attr-defined]
    scan_mod.DeviceRate = DeviceRate  # type: ignore[attr-defined]
    scan_mod.scan = scan  # type: ignore[attr-defined]

    power = types.ModuleType("gremlin.power_requests")

    def list_requests(runner: Callable | None = None) -> RequestsResult:
        calls.lists += 1
        calls._wait_gate()
        return calls.requests

    def set_ignored(
        name: str,
        ignored: bool,
        kind: str = "PROCESS",
        runner: Callable | None = None,
    ) -> tuple[bool, str]:
        calls.ignores.append((name, ignored, kind))
        return calls.ignore_answer

    power.ProgramRequest = ProgramRequest  # type: ignore[attr-defined]
    power.RequestsResult = RequestsResult  # type: ignore[attr-defined]
    power.list_requests = list_requests  # type: ignore[attr-defined]
    power.split = split  # type: ignore[attr-defined]
    power.set_ignored = set_ignored  # type: ignore[attr-defined]

    disable_mod = types.ModuleType("gremlin.device_disable")
    disable_mod.DeviceDisabler = FakeDisabler  # type: ignore[attr-defined]
    disable_mod.manager = lambda: calls.disabler  # type: ignore[attr-defined]

    for name, mod in (
        ("screen_saver_mode", core),
        ("hid_report_scan", scan_mod),
        ("power_requests", power),
        ("device_disable", disable_mod),
    ):
        if target is None:
            sys.modules[f"gremlin.{name}"] = mod
            setattr(gremlin, name, mod)
        else:
            target.setitem(sys.modules, f"gremlin.{name}", mod)
            target.setattr(gremlin, name, mod, raising=False)
    return manager, calls
