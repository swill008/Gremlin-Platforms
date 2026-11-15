# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Stand-ins for gremlin.screen_saver_mode, gremlin.hid_report_scan and
gremlin.power_requests (12 S1-S15), for test_ssm_ui.py and ssm_ui_smoke.py:
the window's tests never listen to the keyboard or mouse, read HID devices,
run powercfg or ask for administrator rights."""

from __future__ import annotations

import sys
import threading
import types
from dataclasses import dataclass, field, replace
from typing import Any, Callable


@dataclass
class Settings:
    enabled: bool = False
    action: str = "power_off"
    wait_override_s: int = 0
    hold_fullscreen: bool = True


@dataclass
class Status:
    enabled: bool = False
    listening: bool = False
    idle_s: float = 0.0
    windows_idle_s: float = 0.0
    wait_s: int = 0
    windows_wait_s: int = 0
    wait_from_windows: bool = True
    hold: str = ""
    hold_program: str = ""
    fired: bool = False
    problem: str = ""
    remaining_s: float = 0.0


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


@dataclass
class RequestsResult:
    ok: bool
    error: str
    programs: list[ProgramRequest] = field(default_factory=list)


class FakeManager:
    """Windows' times: screen saver 10 min, display off 5 min."""

    WAITS = {"screen_saver": 600, "power_off": 300}

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
        windows = self.WAITS.get(s.action, 0)
        wait = s.wait_override_s or windows
        st = Status(
            enabled=s.enabled,
            listening=s.enabled,
            windows_wait_s=windows,
            wait_s=wait,
            wait_from_windows=not s.wait_override_s,
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
        self.ignores: list[tuple[str, bool]] = []
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
                    "RustDesk.exe", "C:\\RustDesk\\RustDesk.exe", ["Display"], False
                ),
                ProgramRequest(
                    "chrome.exe", "C:\\Chrome\\chrome.exe", ["Display", "System"], True
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
    core.ACTION_SCREEN_SAVER = "screen_saver"  # type: ignore[attr-defined]
    core.ACTION_POWER_OFF = "power_off"  # type: ignore[attr-defined]
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
        name: str, ignored: bool, runner: Callable | None = None
    ) -> tuple[bool, str]:
        calls.ignores.append((name, ignored))
        return calls.ignore_answer

    power.ProgramRequest = ProgramRequest  # type: ignore[attr-defined]
    power.RequestsResult = RequestsResult  # type: ignore[attr-defined]
    power.list_requests = list_requests  # type: ignore[attr-defined]
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
