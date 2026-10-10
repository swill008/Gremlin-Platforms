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
from gremlin.device_reset_log import BACK as BACK_TEXT

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


XBOX_VID = 0x045E
XBOX_NOTE = "Xbox pads can't be restarted live: unplug and plug back in"


def _new_row(d: device_reset.ResetDevice) -> dict:
    """A row as listed: ticked when hidden, except Xbox pads (02 S145)."""
    xbox = d.vid == XBOX_VID
    return {
        "usbId": d.usb_id,
        "name": d.name,
        "windowsName": d.windows_name,
        "vidPid": f"{d.vid:04X} · {d.pid:04X}",
        "hidden": d.hidden,
        "inProfile": d.in_profile,
        "ticked": bool(d.hidden and not xbox),
        "note": XBOX_NOTE if xbox else "",
        "result": "",
        "resultKind": "",
        # Internal: plugged in now; reset running; what its result waits
        # for ("notback" or "restart", 02 S144 RW3); seen gone since.
        "present": True,
        "busy": False,
        "awaitBack": "",
        "away": False,
    }


_INTERNAL = ("present", "busy", "awaitBack", "away")


def _await_back(outcome: str, back_after: float | None) -> str:
    if outcome == "restart":
        return "restart"
    return "notback" if outcome == "ok" and back_after is None else ""


@ta.QmlElement
class ResetDevicesModel(QtCore.QObject):
    """Rows, ticks and results of one Reset Devices window. While the
    window is open the rows follow plug/unplug (02 S144)."""

    changed = QtCore.Signal()
    _finished = QtCore.Signal(list)

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._rows: list[dict] = []
        self._devices: list[device_reset.ResetDevice] = []
        self._games: list[str] = []
        self._hidden: list[str] = []
        self._names: dict[str, str] = {}
        self._running = False
        self._done = False
        self._generation = 0
        self._connected = False
        self._finished.connect(self._take_results)

    def _bump(self) -> None:
        self._generation += 1
        self.changed.emit()

    def _list(self) -> list[device_reset.ResetDevice] | None:
        """The plugged-in devices now; None when they can't be read."""
        try:
            return device_reset.list_devices(
                self._hidden, profile_device_names(), gremlin_names=self._names
            )
        except Exception:
            logging.getLogger("system").exception("Reset Devices: device list failed")
            return None

    def _follow(self, on: bool) -> None:
        """Connects to (or lets go of) the program's device-change signal."""
        if on == self._connected:
            return
        try:
            from gremlin import event_handler

            signal = event_handler.EventListener().device_change_event
            if on:
                signal.connect(self._device_change)
            else:
                signal.disconnect(self._device_change)
            self._connected = on
        except Exception:
            logging.getLogger("system").debug(
                "Reset Devices: device change hook failed", exc_info=True
            )

    @QtCore.Slot("QVariant")
    def load(self, context: object) -> None:
        """context from HidHideModel.resetContext(): hiddenIds, games and
        names (instance id -> Gremlin name)."""
        to_variant = getattr(context, "toVariant", None)
        ctx = to_variant() if callable(to_variant) else context
        ctx = ctx if isinstance(ctx, dict) else {}
        self._hidden = [str(h) for h in ctx.get("hiddenIds") or []]
        self._names = {str(k): str(v) for k, v in (ctx.get("names") or {}).items()}
        self._devices = self._list() or []
        self._rows = [_new_row(d) for d in self._devices]
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
        self._follow(True)
        self._bump()

    @QtCore.Slot()
    def detach(self) -> None:
        """The window closed: stop following device changes."""
        self._follow(False)

    @QtCore.Slot()
    def _device_change(self) -> None:
        """A device came or went: unplugged rows go (unless a reset or its
        result waits on them), new ones come in (02 S144)."""
        devices = self._list()
        if devices is None:
            return
        fresh = {d.usb_id.upper(): d for d in devices}
        pairs: list[tuple[device_reset.ResetDevice, dict]] = []
        for dev, row in zip(self._devices, self._rows, strict=True):
            now = fresh.pop(dev.usb_id.upper(), None)
            if now is None:
                if row["busy"] or row["awaitBack"]:
                    row["present"] = False
                    row["away"] = True
                    pairs.append((dev, row))
                continue
            row["present"] = True
            row["hidden"] = now.hidden
            if row["awaitBack"] == "notback" or (row["awaitBack"] and row["away"]):
                self._back(now, row)
            pairs.append((now, row))
        pairs += [(d, _new_row(d)) for d in fresh.values()]
        pairs.sort(key=lambda p: (p[0].name or p[0].usb_id).casefold())
        self._devices = [p[0] for p in pairs]
        self._rows = [p[1] for p in pairs]
        self._bump()

    @staticmethod
    def _back(dev: device_reset.ResetDevice, row: dict) -> None:
        """RW3: a device not back after its reset was plugged back in."""
        row["result"] = BACK_TEXT
        row["resultKind"] = "ok"
        row["awaitBack"] = ""
        row["away"] = False
        try:
            from gremlin import device_reset_log

            device_reset_log.report_back(dev)
        except Exception:
            logging.getLogger("system").exception("Reset Devices: not logged")

    @QtCore.Property(int, notify=changed)
    def generation(self) -> int:
        return self._generation

    @QtCore.Property(int, notify=changed)
    def rowCount(self) -> int:  # noqa: N802 - QML name
        return len(self._rows)

    @QtCore.Slot(int, result="QVariant")
    def rowAt(self, index: int) -> dict:  # noqa: N802 - QML name
        if 0 <= index < len(self._rows):
            return {k: v for k, v in self._rows[index].items() if k not in _INTERNAL}
        return {}

    @QtCore.Slot(int, bool)
    def setTicked(self, index: int, on: bool) -> None:  # noqa: N802 - QML name
        if self._running or self._done or not 0 <= index < len(self._rows):
            return
        self._rows[index]["ticked"] = bool(on)
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
        return sum(1 for r in self._rows if r["present"] and r["ticked"])

    @QtCore.Property(int, notify=changed)
    def pluggedCount(self) -> int:  # noqa: N802 - QML name
        return sum(1 for r in self._rows if r["present"])

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
            if r["present"] and r["ticked"]
        ]
        if not chosen:
            return
        self._running = True
        for row in self._rows:
            if row["present"] and row["ticked"]:
                row["result"] = "resetting…"
                row["resultKind"] = ""
                row["busy"] = True
        self._bump()

        def work() -> None:
            # reset() waits a bounded time (60 s for Windows, 10 s a device).
            try:
                done = device_reset.reset(chosen)
                results = [
                    {
                        "usbId": r.usb_id,
                        "text": r.text,
                        "kind": _kind(r.outcome),
                        "awaitBack": _await_back(r.outcome, r.back_after),
                    }
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
                row["awaitBack"] = str(hit.get("awaitBack") or "")
                row["away"] = False
            row["busy"] = False
        # A gone row stays to show its result; the next device change
        # drops it unless the result waits for it (02 S144 RW2a/RW3).
        self._running = False
        self._done = True
        self._bump()
