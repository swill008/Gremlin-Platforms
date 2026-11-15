# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Stand-ins for gremlin.screen_saver_mode, gremlin.hid_report_scan and
gremlin.power_requests (12 S1-S20, contract-4's API), for test_ssm_ui.py
and ssm_ui_smoke.py: the window's tests never listen to the keyboard or
mouse, read HID devices, run powercfg or ask for administrator rights."""

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

    scan_mod = types.ModuleType("gremlin.hid_report_scan")

    def scan(
        seconds: float = 4.0, should_stop: Callable[[], bool] | None = None
    ) -> list:
        calls.scans.append(seconds)
        calls._wait_gate()
        return list(calls.devices)

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

    for name, mod in (
        ("screen_saver_mode", core),
        ("hid_report_scan", scan_mod),
        ("power_requests", power),
    ):
        if target is None:
            sys.modules[f"gremlin.{name}"] = mod
            setattr(gremlin, name, mod)
        else:
            target.setitem(sys.modules, f"gremlin.{name}", mod)
            target.setattr(gremlin, name, mod, raising=False)
    return manager, calls
