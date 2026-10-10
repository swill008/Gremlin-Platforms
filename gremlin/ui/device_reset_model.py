# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Reset Devices window (D-02-RESET-DEVICES): the physical USB game
controllers with a tick each, the warning lines, and Reset, which runs
gremlin.device_reset.reset on a worker thread so the window stays live.

HidHide checks a device only when a program opens it; a device restart
makes every program open it again."""

from __future__ import annotations

import logging

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import device_reset

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1

WARNING = (
    "The ticked USB devices will be reset. Center your sticks before you "
    "press Reset: while a device restarts, the program keeps its axes where they "
    "were and releases its buttons."
)
PERMISSION = "Windows may ask for administrator permission."


def game_line(exe: str) -> str:
    return f"{exe} is running and will lose these devices for a moment."


def profile_device_names() -> list[str]:
    """Names of the devices the open profile has actions on."""
    try:
        from gremlin import shared_state

        profile = shared_state.current_profile
    except Exception:
        return []
    if profile is None:
        return []
    names: list[str] = []
    try:
        known = profile.device_database.devices
        for dev_id, items in profile.inputs.items():
            if not any(getattr(i, "action_sequences", None) for i in items):
                continue
            info = known.get(dev_id)
            if info is not None and info.name:
                names.append(str(info.name))
        from gremlin.device_initialization import joystick_devices

        used = set(profile.inputs)
        for dev in joystick_devices():
            if getattr(dev, "device_guid", None) in used and dev.name:
                names.append(str(dev.name))
    except Exception:
        logging.getLogger("system").exception(
            "Reset Devices: profile devices not read"
        )
    return names


def _kind(outcome: str) -> str:
    """Result colour: ok, warn or bad."""
    return {"ok": "ok", "restart": "warn", "not_found": "warn",
            "declined": "warn"}.get(outcome, "bad")


@ta.QmlElement
class ResetDevicesModel(QtCore.QObject):
    """Rows, ticks and results of one Reset Devices window."""

    changed = QtCore.Signal()
    _finished = QtCore.Signal(list)

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._rows: list[dict] = []
        self._devices: list[device_reset.ResetDevice] = []
        self._games: list[str] = []
        self._running = False
        self._done = False
        self._generation = 0
        self._finished.connect(self._take_results)

    def _bump(self) -> None:
        self._generation += 1
        self.changed.emit()

    @QtCore.Slot("QVariant")
    def load(self, context: object) -> None:
        """context from HidHideModel.resetContext(): hiddenIds, games,
        names (instance id -> Gremlin name) and known (not plugged in)."""
        to_variant = getattr(context, "toVariant", None)
        ctx = to_variant() if callable(to_variant) else context
        ctx = ctx if isinstance(ctx, dict) else {}
        try:
            devices = device_reset.list_devices(
                ctx.get("hiddenIds") or [],
                profile_device_names(),
                known=ctx.get("known") or [],
                gremlin_names=ctx.get("names") or {},
            )
        except Exception:
            logging.getLogger("system").exception("Reset Devices: device list failed")
            devices = []
        plugged = {(d.vid, d.pid) for d in devices if d.plugged}
        # A device the program knows that is plugged in under another id is
        # listed once, as the plugged-in one.
        self._devices = [
            d for d in devices if d.plugged or (d.vid, d.pid) not in plugged
        ]
        self._rows = [
            {
                "usbId": d.usb_id,
                "name": d.name,
                "windowsName": d.windows_name,
                "vidPid": f"{d.vid:04X} · {d.pid:04X}",
                "plugged": d.plugged,
                "hidden": d.hidden,
                "inProfile": d.in_profile,
                # Ticked at start: exactly the hidden devices, every time.
                "ticked": bool(d.plugged and d.hidden),
                "result": "" if d.plugged else "not plugged in",
                "resultKind": "",
            }
            for d in self._devices
        ]
        try:
            games = ctx.get("games") or []
            self._games = list(device_reset.running_listed_games(games))
        except Exception:
            logging.getLogger("system").exception(
                "Reset Devices: running games not read"
            )
            self._games = []
        self._running = False
        self._done = False
        self._bump()

    @QtCore.Property(int, notify=changed)
    def generation(self) -> int:
        return self._generation

    @QtCore.Property(int, notify=changed)
    def rowCount(self) -> int:  # noqa: N802 - QML name
        return len(self._rows)

    @QtCore.Slot(int, result="QVariant")
    def rowAt(self, index: int) -> dict:  # noqa: N802 - QML name
        if 0 <= index < len(self._rows):
            return dict(self._rows[index])
        return {}

    @QtCore.Slot(int, bool)
    def setTicked(self, index: int, on: bool) -> None:  # noqa: N802 - QML name
        if self._running or self._done or not 0 <= index < len(self._rows):
            return
        row = self._rows[index]
        if not row["plugged"]:
            return
        row["ticked"] = bool(on)
        self._bump()

    @QtCore.Property(str, constant=True)
    def warningText(self) -> str:  # noqa: N802 - QML name
        return WARNING

    @QtCore.Property(str, constant=True)
    def permissionText(self) -> str:  # noqa: N802 - QML name
        return PERMISSION

    @QtCore.Property(list, notify=changed)
    def gameLines(self) -> list:  # noqa: N802 - QML name
        return [game_line(g) for g in self._games]

    @QtCore.Property(int, notify=changed)
    def tickedCount(self) -> int:  # noqa: N802 - QML name
        return sum(1 for r in self._rows if r["plugged"] and r["ticked"])

    @QtCore.Property(int, notify=changed)
    def pluggedCount(self) -> int:  # noqa: N802 - QML name
        return sum(1 for r in self._rows if r["plugged"])

    @QtCore.Property(str, notify=changed)
    def summary(self) -> str:
        return f"{self.tickedCount} of {self.pluggedCount} plugged-in devices ticked"

    @QtCore.Property(bool, notify=changed)
    def running(self) -> bool:
        return self._running

    @QtCore.Property(bool, notify=changed)
    def done(self) -> bool:
        return self._done

    @QtCore.Slot()
    def startReset(self) -> None:  # noqa: N802 - QML name
        """Resets the ticked devices on a worker; the window stays live."""
        if self._running or self._done:
            return
        chosen = [
            d for d, r in zip(self._devices, self._rows, strict=True)
            if r["plugged"] and r["ticked"]
        ]
        if not chosen:
            return
        self._running = True
        for row in self._rows:
            if row["plugged"] and row["ticked"]:
                row["result"] = "resetting…"
                row["resultKind"] = ""
        self._bump()

        def work() -> None:
            # reset() waits a bounded time (60 s for Windows, 10 s a device).
            try:
                done = device_reset.reset(chosen)
                results = [
                    {"usbId": r.usb_id, "text": r.text, "kind": _kind(r.outcome)}
                    for r in done
                ]
                # system.log, Trace HIDHIDE lines and expected.json.
                try:
                    from gremlin import device_reset_log

                    device_reset_log.report(done, chosen)
                except Exception:
                    logging.getLogger("system").exception("Reset Devices: not logged")
            except Exception as exc:
                logging.getLogger("system").exception("Reset Devices failed")
                results = [
                    {"usbId": d.usb_id, "text": f"failed: {exc}", "kind": "bad"}
                    for d in chosen
                ]
            try:
                self._finished.emit(results)
            except RuntimeError:
                pass  # the window was closed

        from gremlin import threads

        threads.start("Reset Devices", work)

    @QtCore.Slot(list)
    def _take_results(self, results: list) -> None:
        by_id = {str(r["usbId"]).upper(): r for r in results}
        for row in self._rows:
            hit = by_id.get(str(row["usbId"]).upper())
            if hit is not None:
                row["result"] = hit["text"]
                row["resultKind"] = hit["kind"]
        self._running = False
        self._done = True
        self._bump()
