# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Companion setup check (09 S144, OX4): line by line, what Bitfocus
Companion needs from OSC's settings, each OK or what to change.

Only reads OSC's module file and the runtime's state; never changes either.
OscCompanionCheck runs it for the Output tab of OSC's Module Setup."""

from __future__ import annotations

from typing import Any, Callable

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import osc_device_file as osc_file

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1

# Companion's OSC listen port as it ships; the user may change it there.
COMPANION_DEFAULT_PORT = osc_file.COMPANION_PORT

Line = dict[str, Any]
Holder = Callable[[int, str], "tuple[str, int] | None"]


def _line(label: str, ok: bool, fix: str = "", warn: bool = False) -> Line:
    return {"label": label, "ok": ok, "warn": warn, "fix": fix}


def _runtime_open() -> bool:
    try:
        from gremlin.osc import OscRuntime  # noqa: PLC0415  lazy: keeps imports light

        return bool(OscRuntime().is_open())
    except Exception:  # noqa: BLE001  no runtime: the port isn't ours
        return False


def _port_holder(port: int, host: str) -> tuple[str, int] | None:
    try:
        from gremlin.osc import port_holder  # noqa: PLC0415

        return port_holder(port, host)
    except Exception:  # noqa: BLE001
        return None


def check(
    server: dict | None = None,
    targets: list[dict] | None = None,
    feedback: list[dict] | None = None,
    is_open: Callable[[], bool] | None = None,
    holder: Holder | None = None,
) -> list[Line]:
    """The check's lines, {label, ok, warn, fix}: ok False is a fault,
    ok True with warn True is worth a look. Arguments default to OSC's file,
    OscRuntime().is_open and gremlin.osc.port_holder."""
    server = osc_file.read_server() if server is None else server
    targets = osc_file.read_targets() if targets is None else targets
    feedback = osc_file.read_feedback() if feedback is None else feedback
    is_open = _runtime_open if is_open is None else is_open
    holder = _port_holder if holder is None else holder

    lines: list[Line] = []
    if server.get("enabled", True):
        lines.append(_line("OSC is on.", True))
    else:
        lines.append(_line(
            "OSC is off.", False,
            "Tick \"Listen for OSC messages\" on the Server tab."))

    port = int(server.get("port") or 0)
    host = str(server.get("host") or "")
    if is_open():
        lines.append(_line(f"Port {port} is open for OSC messages.", True))
    else:
        held = holder(port, host)
        if held is not None:
            lines.append(_line(
                f"Port {port} is in use by {held[0]} (PID {held[1]}).", False,
                "Close that program, or choose another port on the Server "
                "tab and send to it from Companion."))
        else:
            lines.append(_line(
                f"Port {port} is free. It opens while a profile with OSC "
                "inputs runs or the OSC Monitor is shown.", True))

    if server.get("output_enabled", True):
        lines.append(_line("OSC output is on.", True))
    else:
        lines.append(_line(
            "OSC output is off.", False,
            "Tick \"OSC output\" above."))

    target = osc_file.find_companion_target(targets)
    if target is None:
        lines.append(_line(
            "There is no Companion target.", False,
            "Click Add Companion."))
    else:
        name = str(target.get("name") or "Companion")
        there = f"{target.get('host')}:{target.get('port')}"
        lines.append(_line(f"Target {name} ({there}) is ready.", True))
        tport = target.get("port")
        if tport == COMPANION_DEFAULT_PORT:
            lines.append(_line(
                f"Target {name}'s port is {tport}, Companion's OSC listen "
                f"port ({COMPANION_DEFAULT_PORT} by default).", True))
        else:
            lines.append(_line(
                f"Target {name}'s port is {tport}, not {COMPANION_DEFAULT_PORT}.",
                True,
                "It must match Companion's OSC listen port "
                f"({COMPANION_DEFAULT_PORT} by default; Companion's Settings › "
                "OSC). If you didn't change it there, click Add Companion.",
                warn=True))

    if feedback:
        if server.get("feedback_enabled", True):
            lines.append(_line("Feedback is on.", True))
        else:
            lines.append(_line(
                f"Feedback is off, so its {len(feedback)} row(s) send nothing.",
                False,
                "Tick \"Send feedback to OSC devices\" on the Feedback tab."))
    return lines


@ta.QmlElement
class OscCompanionCheck(QtCore.QObject):
    """Runs check() for QML: run() fills lines."""

    linesChanged = QtCore.Signal()

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._lines: list[Line] = []

    @QtCore.Property(list, notify=linesChanged)
    def lines(self) -> list[Line]:
        return self._lines

    @QtCore.Slot()
    def run(self) -> None:
        self._lines = check()
        self.linesChanged.emit()
