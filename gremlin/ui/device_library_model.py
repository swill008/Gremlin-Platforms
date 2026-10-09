# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Device Library window's model (10 Device Library): the only thing its
QML talks to.

It reads the Library through its owner (gremlin.device_library) and runs
Copy, Swap and Change vJoy Output through theirs (library_copy,
library_swap, library_profiles). Undo and Redo walk through this session's
Library actions (library_undo, S53). One change runs at a time and the window
shows it is busy (section 6). Results come back as result(map).

Threads (section 6, program thread rules): the owners run on the main
thread, which owns the open profile, the device lists, the module files'
registry and the settings. Inside library_profiles.responsive() their file
work (reading and writing saved profiles, and what the owners hand to
library_profiles.background()) runs on a program thread while the event
loop keeps going. Only work that reads nothing the main thread owns runs
wholly on a program thread: the saved profiles' scan and the size measure.
"""

from __future__ import annotations

import contextlib
import json
import logging
import types
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6 import QtCore

from gremlin.ui.util import to_local_path

# The parts a saved setup can hold, in the order they are shown (contract
# PARTS), with their labels.
PARTS = ["setup", "button_map", "appearance", "calibration", "bindings"]
PART_LABELS = {
    "setup": "Setup",
    "button_map": "Button Map",
    "appearance": "Appearance",
    "calibration": "Calibration",
    "bindings": "Bindings",
}
# The longer labels in a saved setup's details (S11).
_HOLDS_LABELS = {
    "setup": "Setup (claims, friendly names)",
    "button_map": "Button Map and photo",
    "appearance": "Appearance",
    "calibration": "Calibration",
    "setup_damaged": "Setup (damaged file, kept as is)",
}
STATE_LABELS = {
    "connected": "Connected",
    "not_connected": "Not connected",
    "deleted": "Deleted",
    "builtin": "Built-in input",
}
FILTERS = ["connected", "not_connected", "deleted", "autosaves"]

# A replan waits this long for the ticks to settle (section 6).
_PLAN_SETTLE_MS = 150

# How long a Remove from Library's History group waits for its end.
_GROUP_LIMIT_MS = 60_000

# Changes that are not steps for Undo (S53): Undo and Redo themselves.
_NOT_STEPS = ("undo", "redo")

_BUSY_TEXT = "Another change is still running: wait for it to finish."


def _real_api() -> types.SimpleNamespace:
    """The owners the model calls (imported when first used)."""
    from gremlin import device_library as library
    from gremlin import history, library_copy, library_profiles, library_swap
    from gremlin.modules import output

    def forget(name: str, guid: str) -> None:
        try:
            from gremlin import device_forget
        except ImportError:
            logging.getLogger("system").warning("Device Library: nothing forgets")
            return
        device_forget.forget_device(name, guid)

    def file_choices() -> str:
        from gremlin.modules import store

        return json.dumps(store.bindings(), sort_keys=True)

    return types.SimpleNamespace(
        library=library,
        history=history,
        forget=forget,
        file_choices=file_choices,
        profiles=library_profiles,
        copy=library_copy,
        swap=library_swap,
        vjoy_ids=output.vjoy_ids,
    )


def size_text(count: int) -> str:
    """A size on disk for the status bar, e.g. "48 MB"."""
    if count < 1024:
        return f"{count} bytes"
    size = float(count)
    for unit in ("KB", "MB", "GB"):
        size /= 1024.0
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if size >= 10 else f"{size:.1f} {unit}"
    return ""


def _count_text(count: int) -> str:
    if count == 0:
        return "No saved setups"
    return "1 saved setup" if count == 1 else f"{count} saved setups"


def _date(at: str) -> str:
    return (at or "")[:10]


def _date_time(at: str) -> str:
    return (at or "")[:16].replace("T", " ")


def inputs_text(counts: dict) -> str:
    """S8: "32 buttons, 6 axes, 1 hat" ("" when not known)."""
    if not counts:
        return ""
    words = []
    for key, one, many in (
        ("buttons", "button", "buttons"),
        ("axes", "axis", "axes"),
        ("hats", "hat", "hats"),
    ):
        n = int(counts.get(key) or 0)
        words.append(f"no {many}" if n == 0 else f"{n} {one if n == 1 else many}")
    return ", ".join(words)


def _short_id(guid: str) -> str:
    """A few characters of a device id, to tell twins apart (S22, S26)."""
    clean = "".join(c for c in str(guid or "") if c.isalnum())
    return clean[:8].upper()


def _built_in_icon(dev: dict) -> str:
    """The row icon of a built-in input (10 S6): "keyboard" for Keyboard,
    "" (the device icon) for the rest."""
    if not dev.get("builtIn"):
        return ""
    from gremlin.modules import ids

    guid = ids.guid_key(dev.get("guid", ""))
    if guid == ids.guid_key(ids.KEYBOARD):
        return "keyboard"
    if not guid and str(dev.get("name", "")).casefold() == "keyboard":
        return "keyboard"
    return ""


def _twin_label(dev: dict, names: list[str]) -> str:
    """The device's name, with its short id when another device has the
    same name (casefolded names of every device in names)."""
    name = str(dev.get("name", ""))
    short = _short_id(dev.get("guid", ""))
    if short and names.count(name.casefold()) > 1:
        return f"{name} [{short}]"
    return name


def _and(words: list[str]) -> str:
    return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " and " + words[-1]


def also_move_text(others: list[dict]) -> str:
    """S30: "Also move Left stick from vJoy 2 to vJoy 1 (swap them)", every
    other stick on a target vJoy named with its own from and to."""
    groups: dict[tuple[int, int], list[str]] = {}
    for row in others:
        try:
            key = (int(row.get("vjoy") or 0), int(row.get("to") or 0))
        except (TypeError, ValueError):
            continue
        name = str(row.get("name") or "")
        names = groups.setdefault(key, [])
        if name and name not in names:
            names.append(name)
    parts = [
        f"{_and(names)} from vJoy {a} to vJoy {b}"
        for (a, b), names in groups.items()
        if names
    ]
    if not parts:
        return ""
    return "Also move " + ", and ".join(parts) + " (swap them)"


def _is_autosave(setup: dict) -> bool:
    return setup.get("origin") == "autosave" and not setup.get("own")


def _setup_sub(setup: dict) -> str:
    """The line under a saved setup's name (how it was kept)."""
    origin = setup.get("origin", "user")
    if origin == "pack":
        return setup.get("reason") or "From a Device Pack"
    if origin == "autosave":
        return (
            "Was an autosave, now yours" if setup.get("own") else "Kept automatically"
        )
    return "Saved by you"


def _vjoy_text(vjoys: dict) -> str:
    parts = [
        f"vJoy {number} ({count} input{'s' if count != 1 else ''})"
        for number, count in sorted(vjoys.items(), key=lambda kv: int(kv[0]))
    ]
    if not parts:
        return ""
    if len(parts) == 1:
        return "Sends to " + parts[0]
    return "Sends to " + ", ".join(parts[:-1]) + " and " + parts[-1]


def _result(op: str, value: object) -> dict:
    """A Result map for QML: always op, ok, error, warnings, notes."""
    out: dict[str, Any] = (
        dict(value) if isinstance(value, dict) else {"ok": bool(value)}
    )
    out["op"] = op
    out.setdefault("ok", True)
    out.setdefault("error", "")
    out["warnings"] = list(out.get("warnings") or [])
    out["notes"] = list(out.get("notes") or [])
    return out


class DeviceLibraryModel(QtCore.QObject):
    """The Device Library for QML (context property deviceLibrary)."""

    changed = QtCore.Signal()
    result = QtCore.Signal(dict)
    busyChanged = QtCore.Signal()
    # Undo or Redo changed (undoText, redoText).
    stepsChanged = QtCore.Signal()
    planningChanged = QtCore.Signal()
    # A plan's Result, from a worker thread or the main thread.
    _planned = QtCore.Signal(str, int, object)
    # From a worker thread to the main thread: (op, ticket, result, change).
    _done = QtCore.Signal(str, int, object, bool)
    _sized = QtCore.Signal(int)

    def __init__(
        self,
        parent: QtCore.QObject | None = None,
        api: types.SimpleNamespace | None = None,
        watch_devices: bool = True,
    ) -> None:
        super().__init__(parent)
        self._api = api
        self._devices: list[dict] = []
        self._open: set[str] = set()
        self._selected = ""
        # Every selected row (S50: several saved setups, or several
        # devices); _selected is the one the details show.
        self._picked: list[str] = []
        # The rows a running change is changing (S43's busy mark).
        self._busy_keys: list[str] = []
        self._filters: dict[str, bool] = {name: True for name in FILTERS}
        self._search = ""
        self._matches: set[str] | None = None
        self._busy = False
        self._busy_op = ""
        self._ticket = 0
        self._size: int | None = None
        self._sizing = False
        self._resize = False
        self._settings: dict[str, Any] = {"keep": 10, "default_parts": [], "folder": ""}
        from gremlin import library_undo

        # This session's Library actions, for Undo and Redo (S53).
        self._steps = library_undo.Steps()
        # Clear History empties the steps: Edit › Undo / Redo follow (08 S12b).
        self._steps.on_cleared.append(self.stepsChanged.emit)
        # When the action being recorded started (None: none is), and what
        # undoes / redoes it when History can't (Copy, Swap, Output, Restore).
        self._since: float | None = None
        self._action: dict | None = None
        self._rows: list[dict] = []
        # Read once per refresh: a device's inputs (S8), a setup's photo (S11).
        self._inputs: dict[str, str] = {}
        self._photos: dict[str, str] = {}
        # The sticks last noted as seen (S8).
        self._seen: set[str] = set()
        # op -> (ticket, fn, args, paths): the newest plan asked for,
        # waiting for ticks to settle.
        self._plans: dict[str, tuple] = {}
        self._plan_running: set[str] = set()
        self._plan_timers: dict[str, QtCore.QTimer] = {}
        # The History group a Remove from Library is recorded in (S51-S52).
        self._group = ""
        self._choices: str | None = None
        self._done.connect(self._finish)
        self._planned.connect(self._take_plan)
        self._sized.connect(self._take_size)
        if watch_devices:
            try:
                from gremlin import event_handler

                event_handler.EventListener().device_change_event.connect(self.refresh)
            except Exception:
                logging.getLogger("system").exception(
                    "Device Library: device changes not followed"
                )

    # | The owners

    @property
    def api(self) -> types.SimpleNamespace:
        if self._api is None:
            self._api = _real_api()
        return self._api

    # | Reading the Library

    def _responsive(self) -> contextlib.AbstractContextManager:
        """library_profiles.responsive(), or nothing for owners without it."""
        make = getattr(self.api.profiles, "responsive", None)
        return make() if make is not None else contextlib.nullcontext()

    @QtCore.Slot()
    def refresh(self) -> None:
        """Reads the Library again (device changes, after each change).
        While a change runs it waits for it: the change's owner is part way
        through the Library then (section 6)."""
        if self._busy:
            # _finish refreshes when the change is done.
            return
        lib = self.api.library
        try:
            self._devices = list(lib.devices())
        except Exception:
            logging.getLogger("system").exception("Device Library: list failed")
            self._devices = []
        try:
            self._settings = dict(lib.settings())
        except Exception:
            logging.getLogger("system").exception("Device Library: settings failed")
        if self._search:
            self._matches = self._search_keys(self._search)
        keys = {d["key"] for d in self._devices} | {
            s["key"] for d in self._devices for s in d.get("setups", [])
        }
        self._open &= keys
        if self._selected and self._selected not in keys:
            self._selected = ""
        self._picked = [k for k in self._picked if k in keys]
        if self._selected and self._selected not in self._picked:
            self._picked = [self._selected]
        self._inputs.clear()
        self._photos.clear()
        self._note_seen()
        self._rebuild()
        self._measure()

    def _note_seen(self) -> None:
        """S8: tells the Library which sticks are plugged in when that
        changes (the ones just unplugged too: their last time seen)."""
        now = {
            str(d.get("guid"))
            for d in self._devices
            if d.get("state") == "connected" and d.get("guid")
        }
        if now == self._seen:
            return
        changed = sorted(now | self._seen)
        self._seen = now
        note = getattr(self.api.library, "note_seen", None)
        if note is None:
            return
        try:
            note(changed)
        except Exception:
            logging.getLogger("system").exception("Device Library: seen not kept")

    def _inputs_of(self, key: str) -> str:
        if key not in self._inputs:
            text = ""
            read = getattr(self.api.library, "inputs", None)
            if read is not None:
                try:
                    text = inputs_text(read(key) or {})
                except Exception:
                    logging.getLogger("system").exception(
                        "Device Library: inputs not read"
                    )
            self._inputs[key] = text
        return self._inputs[key]

    def _photo_of(self, key: str) -> str:
        if key not in self._photos:
            path = ""
            read = getattr(self.api.library, "photo", None)
            if read is not None:
                try:
                    path = str(read(key) or "")
                except Exception:
                    logging.getLogger("system").exception(
                        "Device Library: photo not read"
                    )
            self._photos[key] = path
        return self._photos[key]

    def _search_keys(self, text: str) -> set[str]:
        try:
            return set(self.api.library.search(text))
        except Exception:
            logging.getLogger("system").exception("Device Library: search failed")
            return set()

    def _rebuild(self) -> None:
        rows: list[dict] = []
        matches = self._matches
        names = [str(d.get("name", "")).casefold() for d in self._devices]
        for dev in self._devices:
            state = dev.get("state", "not_connected")
            built_in = bool(dev.get("builtIn"))
            # S6: the state filters never hide the built-in inputs; a
            # search does.
            if not built_in and not self._filters.get(state, True):
                continue
            setups = list(dev.get("setups", []))
            if not self._filters["autosaves"]:
                setups = [s for s in setups if not _is_autosave(s)]
            opened = dev["key"] in self._open
            if matches is not None:
                hits = [s for s in setups if s["key"] in matches]
                if dev["key"] not in matches:
                    if not hits:
                        continue
                    setups = hits
                opened = opened or bool(hits)
            count = len(dev.get("setups", []))
            rows.append(
                {
                    "kind": "device",
                    "key": dev["key"],
                    "device": dev["key"],
                    "name": dev.get("name", ""),
                    # Twins (the same shown name) are told apart by their
                    # id in the list, as in the To lists.
                    "label": _twin_label(dev, names),
                    "description": dev.get("description", ""),
                    "state": state,
                    "stateLabel": STATE_LABELS.get(state, state),
                    "count": count,
                    "countText": _count_text(count),
                    "open": opened,
                    "hasChildren": count > 0,
                    "builtIn": built_in,
                    "icon": _built_in_icon(dev),
                    # The list's section: built-ins sit under their heading.
                    "section": "builtin" if built_in else "",
                }
            )
            if not opened:
                continue
            for setup in setups:
                rows.append(
                    {
                        "kind": "setup",
                        "key": setup["key"],
                        "device": dev["key"],
                        "name": setup.get("name", ""),
                        "description": setup.get("description", ""),
                        "sub": _setup_sub(setup),
                        "date": _date(setup.get("created", "")),
                        "mark": "autosave" if _is_autosave(setup) else "own",
                        "state": state,
                        "builtIn": built_in,
                        "section": "builtin" if built_in else "",
                    }
                )
        self._rows = rows
        self.changed.emit()

    def _measure(self) -> None:
        """The Library's size on disk, measured in the background (S4)."""
        if self._sizing:
            self._resize = True
            return
        self._sizing = True
        self._resize = False
        size_bytes = self.api.library.size_bytes

        def work() -> None:
            try:
                value = int(size_bytes())
            except Exception:
                value = -1
            try:
                self._sized.emit(value)
            except RuntimeError:
                pass

        try:
            from gremlin import threads

            threads.start("Device Library size", work)
        except Exception:
            self._sizing = False

    @QtCore.Slot(int)
    def _take_size(self, value: int) -> None:
        self._sizing = False
        self._size = value if value >= 0 else None
        self.changed.emit()
        if self._resize:
            self._measure()

    def _device(self, key: str) -> dict | None:
        return next((d for d in self._devices if d["key"] == key), None)

    def _setup(self, key: str) -> tuple[dict, dict] | tuple[None, None]:
        for dev in self._devices:
            for setup in dev.get("setups", []):
                if setup["key"] == key:
                    return dev, setup
        return None, None

    # | Properties

    def _get_rows(self) -> list:
        return self._rows

    def _get_selected(self) -> str:
        return self._selected

    def _get_filters(self) -> dict:
        return dict(self._filters)

    def _get_search(self) -> str:
        return self._search

    def _get_busy(self) -> bool:
        return self._busy

    def _get_picked(self) -> list:
        return list(self._picked)

    def _get_busy_keys(self) -> list:
        return list(self._busy_keys)

    def _get_undo(self) -> str:
        return self._steps.undo_text()

    def _get_redo(self) -> str:
        return self._steps.redo_text()

    def _get_status(self) -> str:
        devices = len(self._devices)
        setups = sum(len(d.get("setups", [])) for d in self._devices)
        parts = [
            f"{devices} device{'s' if devices != 1 else ''} ·"
            f" {_count_text(setups).lower()}",
            f"Autosaves: newest {self._settings.get('keep', 10)} per stick",
        ]
        if self._size is not None:
            parts.append(f"Library: {size_text(self._size)}")
        return "     ".join(parts)

    def _get_folder(self) -> str:
        return str(self._settings.get("folder", ""))

    def _get_details(self) -> dict:
        key = self._selected
        if not key:
            return {}
        dev = self._device(key)
        if dev is not None:
            return self._device_details(dev)
        dev, setup = self._setup(key)
        if dev is None or setup is None:
            return {}
        return self._setup_details(dev, setup)

    def _device_details(self, dev: dict) -> dict:
        state = dev.get("state", "not_connected")
        count = len(dev.get("setups", []))
        return {
            "kind": "device",
            "key": dev["key"],
            "deviceKey": dev["key"],
            "crumb": "Device",
            "name": dev.get("name", ""),
            "description": dev.get("description", ""),
            "state": state,
            "stateLabel": STATE_LABELS.get(state, state),
            "guid": dev.get("guid", ""),
            "module": dev.get("module", ""),
            # S8: what inputs it has and when it was last seen.
            "inputs": self._inputs_of(dev["key"]),
            "lastSeen": "now"
            if state == "connected"
            else _date_time(str(dev.get("seen") or "")),
            # S22: Copy takes its current settings (module file here, or
            # plugged in now); otherwise one of its saved setups.
            "hasCurrent": bool(dev.get("module"))
            or state == "connected"
            or bool(dev.get("builtIn")),
            "countText": _count_text(count),
            "count": count,
            "connected": state == "connected",
            "canDeleteDevice": state != "connected"
            and not dev.get("module")
            and not dev.get("builtIn"),
            "builtIn": bool(dev.get("builtIn")),
        }

    def _setup_details(self, dev: dict, setup: dict) -> dict:
        holds = list(setup.get("holds", []))
        when = _date_time(setup.get("created", ""))
        origin = setup.get("origin", "user")
        if origin == "autosave" and not setup.get("own"):
            why = setup.get("reason") or setup.get("name", "")
            kept = (
                f"Kept automatically ({why}) · {when}"
                if why
                else f"Kept automatically · {when}"
            )
        elif origin == "autosave":
            kept = f"Kept automatically, now yours · {when}"
        elif origin == "pack":
            kept = f"{setup.get('reason') or 'From a Device Pack'} · {when}"
        else:
            kept = f"Saved by you · {when}"
        bindings = []
        if "bindings" in holds:
            for prof in setup.get("profiles", []):
                line = f"Bindings from {prof.get('name', '')}"
                if prof.get("modes"):
                    line += " · modes " + ", ".join(prof["modes"])
                if prof.get("actions") is not None:
                    n = int(prof.get("actions") or 0)
                    line += f" · {n} action{'s' if n != 1 else ''}"
                bindings.append(line)
            if not bindings:
                bindings.append("Bindings")
        modes: list[str] = []
        for prof in setup.get("profiles", []):
            for mode in prof.get("modes", []):
                if mode not in modes:
                    modes.append(mode)
        state = dev.get("state", "not_connected")
        return {
            "kind": "setup",
            "key": setup["key"],
            "deviceKey": dev["key"],
            "deviceName": dev.get("name", ""),
            "crumb": f"{dev.get('name', '')} › saved setup",
            "name": setup.get("name", ""),
            "description": setup.get("description", ""),
            "kept": kept,
            "own": bool(setup.get("own")),
            "origin": origin,
            "holds": holds,
            "holdsLabels": [
                _HOLDS_LABELS[p]
                for p in [*PARTS, "setup_damaged"]
                if p in holds and p in _HOLDS_LABELS
            ],
            "bindings": bindings,
            "modes": modes,
            "sends": _vjoy_text(setup.get("vjoys", {}) or {}),
            "history": [
                {"at": _date(h.get("at", "")), "text": h.get("text", "")}
                for h in setup.get("history", [])
            ],
            "photo": self._photo_of(setup["key"]),
            "state": state,
            "guid": dev.get("guid", ""),
            "connected": state == "connected",
            # Its device's current settings (S12: something to save now).
            "module": dev.get("module", ""),
            "hasCurrent": bool(dev.get("module"))
            or state == "connected"
            or bool(dev.get("builtIn")),
            "builtIn": bool(dev.get("builtIn")),
        }

    rows = QtCore.Property(list, fget=_get_rows, notify=changed)
    selected = QtCore.Property(str, fget=_get_selected, notify=changed)
    details = QtCore.Property(dict, fget=_get_details, notify=changed)
    filters = QtCore.Property(dict, fget=_get_filters, notify=changed)
    searchText = QtCore.Property(str, fget=_get_search, notify=changed)
    statusText = QtCore.Property(str, fget=_get_status, notify=changed)
    folderText = QtCore.Property(str, fget=_get_folder, notify=changed)
    busy = QtCore.Property(bool, fget=_get_busy, notify=busyChanged)
    selectedKeys = QtCore.Property(list, fget=_get_picked, notify=changed)
    busyKeys = QtCore.Property(list, fget=_get_busy_keys, notify=busyChanged)
    undoText = QtCore.Property(str, fget=_get_undo, notify=stepsChanged)
    redoText = QtCore.Property(str, fget=_get_redo, notify=stepsChanged)

    @QtCore.Property(list, constant=True)
    def partList(self) -> list:
        return [{"key": p, "label": PART_LABELS[p]} for p in PARTS]

    # | The list

    @QtCore.Slot(str)
    def toggleOpen(self, key: str) -> None:
        if key in self._open:
            self._open.discard(key)
        else:
            self._open.add(key)
        self._rebuild()

    @QtCore.Slot(bool)
    def setAllOpen(self, on: bool) -> None:
        """View › Expand All / Collapse All."""
        self._open = (
            {d["key"] for d in self._devices if d.get("setups")} if on else set()
        )
        self._rebuild()

    @QtCore.Slot(str)
    def select(self, key: str) -> None:
        self._selected = key
        self._picked = [key] if key else []
        dev, _setup = self._setup(key)
        if dev is not None:
            self._open.add(dev["key"])
            self._rebuild()
        else:
            self.changed.emit()

    def _kind(self, key: str) -> str:
        return "device" if self._device(key) is not None else "setup"

    @QtCore.Slot(str, str)
    def pick(self, key: str, how: str) -> None:
        """S50: Ctrl-click ("toggle") adds or takes away a row, Shift-click
        ("range") selects the rows from the last one clicked to this one.
        Several saved setups, or several devices: a row of the other kind
        starts a new selection. Anything else selects only this row."""
        if how not in ("toggle", "range") or not self._picked:
            self.select(key)
            return
        kind = self._kind(key)
        same = [k for k in self._picked if self._kind(k) == kind]
        if not same:
            self.select(key)
            return
        if how == "toggle":
            if key in same:
                same.remove(key)
                if not same:
                    self.select("")
                    return
                self._picked = same
                if self._selected == key:
                    self._selected = same[-1]
            else:
                self._picked = [*same, key]
                self._selected = key
        else:
            order = [r["key"] for r in self._rows if r["kind"] == kind]
            anchor = self._selected if self._selected in same else same[-1]
            if key not in order or anchor not in order:
                self.select(key)
                return
            a, b = sorted((order.index(anchor), order.index(key)))
            self._picked = order[a : b + 1]
            self._selected = key
        self.changed.emit()

    @QtCore.Slot(str, result=dict)
    def deviceTarget(self, key: str) -> dict:
        """A device's own name, id and Home card key: what Home's Delete
        Device, Module Setup, Button Map and Show on Home take (S15, S44)."""
        dev = self._device(key)
        if dev is None:
            return {}
        name, guid = self._target(key)
        from gremlin.modules import store

        return {
            "key": key,
            "name": name,
            "guid": guid,
            "shown": str(dev.get("name", "")),
            "slug": store.card_key(name),
            "module": str(dev.get("module", "") or ""),
            "state": str(dev.get("state", "")),
        }

    @QtCore.Slot(str, result=dict)
    def removalPlan(self, key: str) -> dict:
        """S15: what Remove from Library would remove (module_file: the
        module file still here, which Home's Delete Device removes first)."""
        try:
            return dict(self.api.library.removal_plan(key) or {})
        except Exception:
            logging.getLogger("system").exception("Device Library: removal plan")
            dev = self._device(key)
            return {"module_file": str(dev.get("module", "")) if dev else ""}

    @QtCore.Slot(str, str, result=str)
    def findDevice(self, name: str, guid: str) -> str:
        """The key of the device with that id (or name), "" when none."""

        def clean(v: str) -> str:
            return str(v or "").strip("{}").lower()

        if guid:
            for dev in self._devices:
                if clean(dev.get("guid", "")) == clean(guid):
                    return dev["key"]
        for dev in self._devices:
            if name and dev.get("name") == name:
                return dev["key"]
        return ""

    @QtCore.Slot(str, result=str)
    def newestSetup(self, deviceKey: str) -> str:
        """The device's newest saved setup ("" when it has none): what a
        device row with no current settings here copies (S22)."""
        dev = self._device(deviceKey)
        setups = dev.get("setups", []) if dev else []
        return setups[0]["key"] if setups else ""

    @QtCore.Slot(str, bool)
    def setFilter(self, name: str, on: bool) -> None:
        if name in self._filters:
            self._filters[name] = bool(on)
            self._rebuild()

    @QtCore.Slot(str)
    def setSearch(self, text: str) -> None:
        self._search = text.strip()
        self._matches = self._search_keys(self._search) if self._search else None
        self._rebuild()

    # | Names and descriptions (S7, S13): quick writes, done at once

    @QtCore.Slot(str, str, result=bool)
    def rename(self, key: str, name: str) -> bool:
        name = name.strip()
        if not name:
            self.result.emit(
                _result("rename", {"ok": False, "error": "A name can't be empty."})
            )
            return False
        return self._now("rename", self.api.library.rename, key, name)

    @QtCore.Slot(str, str, result=bool)
    def describe(self, key: str, text: str) -> bool:
        return self._now("describe", self.api.library.describe, key, text)

    def _now(self, op: str, fn: Callable[..., object], *args: object) -> bool:
        if self._busy:
            self.result.emit(_result(op, {"ok": False, "error": _BUSY_TEXT}))
            return False
        since = self._step_start()
        try:
            res = _result(op, fn(*args))
        except Exception as e:
            logging.getLogger("system").exception("Device Library: %s failed", op)
            res = _result(op, {"ok": False, "error": str(e)})
        self._take_step(since)
        self.refresh()
        self.result.emit(res)
        return bool(res["ok"])

    # | Changes, in the background, one at a time

    def _start(
        self,
        op: str,
        fn: Callable[..., object],
        *args: object,
        change: bool = True,
        main: bool = False,
        keys: list[str] | tuple[str, ...] = (),
        title: str = "",
    ) -> int:
        """Runs fn(*args) on a program thread; its Result comes back as
        result(map) with op and the returned ticket. A change (change=True)
        is refused while another runs. Returns 0 when refused.

        main=True: work that touches what the main thread owns (the open
        profile, devices, module files, settings) runs on the main thread
        instead, after the window has shown it is busy, inside
        library_profiles.responsive(): its file work runs in the background
        while the event loop keeps going (section 6).

        A change other than Undo / Redo is a step for Undo (S53). title:
        Copy, Swap, Change vJoy Output and Restore, one History entry named
        title, undone from its autosaves and redone by running it again."""
        if change and self._busy:
            self.result.emit(_result(op, {"ok": False, "error": _BUSY_TEXT}))
            return 0
        self._ticket += 1
        ticket = self._ticket
        if change:
            self._busy = True
            self._busy_op = op
            self._busy_keys = [str(k) for k in keys if k]
            self.busyChanged.emit()
            if op not in _NOT_STEPS:
                if self._since is None:
                    self._since = self._step_start()
                if title:
                    self._action = {"title": title, "fn": fn, "args": args}
                    fn = self._grouped(title, fn)

        def work() -> None:
            try:
                value = fn(*args)
            except Exception as e:
                logging.getLogger("system").exception("Device Library: %s failed", op)
                value = {"ok": False, "error": str(e) or type(e).__name__}
            self._emit_done(op, ticket, value, change)

        if main:

            def on_main() -> None:
                with self._responsive():
                    work()

            # The next turn of the event loop: busy is drawn first.
            QtCore.QTimer.singleShot(0, self, on_main)
            return ticket
        try:
            from gremlin import threads

            threads.start(f"Device Library {op}", work)
        except Exception as e:
            self._done.emit(op, ticket, {"ok": False, "error": str(e)}, change)
        return ticket

    def _emit_done(self, op: str, ticket: int, value: object, change: bool) -> None:
        """From any thread; a model already gone takes nothing (the
        thread ends by itself either way)."""
        try:
            self._done.emit(op, ticket, value, change)
        except RuntimeError:
            pass

    @QtCore.Slot(str, int, object, bool)
    def _finish(self, op: str, ticket: int, value: object, change: bool) -> None:
        res = _result(op, value)
        res["ticket"] = ticket
        if op in ("remove", "deleteMany"):
            self.endRemove()
        if change:
            self._busy = False
            self._busy_op = ""
            self._busy_keys = []
            self.busyChanged.emit()
            if op in _NOT_STEPS:
                self.stepsChanged.emit()
            else:
                action, self._action = self._action, None
                since, self._since = self._since, None
                self._take_step(since, action if res["ok"] else None)
            self.refresh()
        self.result.emit(res)
        if change:
            # Plans asked for meanwhile run now.
            for waiting in list(self._plans):
                timer = self._plan_timers.get(waiting)
                if timer is not None and not timer.isActive():
                    self._run_plan(waiting)

    @staticmethod
    def _paths(urls: list) -> list[Path]:
        """The ticked profiles; "" is the open profile that was never saved
        (S33), passed on as Path("") (library_profiles.Batch's open one)."""
        return [to_local_path(u) if str(u) else Path("") for u in (urls or [])]

    def _target(self, key: str) -> tuple[str, str]:
        """(name, guid) for the owners: the device's own name where the
        Library gives it (the shown name can be a Home alias, S7), and
        always its id, which decides which stick it is (S12, S22, S26)."""
        dev = self._device(key)
        if dev is None:
            return "", ""
        name = dev.get("ownName") or dev.get("name", "")
        return str(name), str(dev.get("guid") or "")

    @QtCore.Slot(str, list, result=int)
    def saveToLibrary(self, key: str, profilePaths: list) -> int:
        """S12: a saved setup of the device (its own), one per ticked profile."""
        name, guid = self._target(key)
        return self._start(
            "save",
            self.api.library.save_setup,
            name,
            guid,
            self._paths(profilePaths),
            main=True,
        )

    # | Plans (what Copy, Swap and Change vJoy Output would do): ticks
    # settle first, then the plan runs on the main thread (it reads the
    # open profile and the device lists) with the saved profiles read in
    # the background (library_profiles.responsive, section 6). None runs
    # while a change does: it waits for it.

    def _get_planning(self) -> bool:
        return bool(self._plans or self._plan_running)

    # A plan is waiting or running: the dialogs show "Checking…".
    planning = QtCore.Property(bool, fget=_get_planning, notify=planningChanged)

    def _plan(
        self,
        op: str,
        fn: Callable[..., dict],
        args: Callable[[list[Path]], tuple],
        paths: list[Path],
    ) -> int:
        """Asks for a plan; only the newest asked for each op runs, after
        _PLAN_SETTLE_MS without another (one replan after ticks settle).
        Its Result comes back as result(map) with op and the ticket."""
        was = self._get_planning()
        self._ticket += 1
        ticket = self._ticket
        self._plans[op] = (ticket, fn, args, list(paths))
        timer = self._plan_timers.get(op)
        if timer is None:
            timer = QtCore.QTimer(self)
            timer.setSingleShot(True)
            timer.setInterval(_PLAN_SETTLE_MS)
            timer.timeout.connect(lambda op=op: self._run_plan(op))
            self._plan_timers[op] = timer
        timer.start()
        if not was:
            self.planningChanged.emit()
        return ticket

    def _run_plan(self, op: str) -> None:
        if op in self._plan_running or self._busy:
            # One at a time per plan, none during a change: the newest runs
            # when that is back.
            return
        pending = self._plans.pop(op, None)
        if pending is None:
            return
        ticket, fn, args, paths = pending
        self._plan_running.add(op)
        try:
            with self._responsive():
                value = fn(*args(paths))
        except Exception as e:
            logging.getLogger("system").exception("Device Library: %s failed", op)
            value = {"ok": False, "error": str(e) or type(e).__name__}
        if not isinstance(value, dict):
            value = {"ok": bool(value)}
        self._planned.emit(op, ticket, value)

    @QtCore.Slot(str, int, object)
    def _take_plan(self, op: str, ticket: int, value: object) -> None:
        self._plan_running.discard(op)
        res = _result(op, value)
        res["ticket"] = ticket
        self.result.emit(res)
        if op in self._plans and not self._plan_timers[op].isActive():
            self._run_plan(op)
        if not self._get_planning():
            self.planningChanged.emit()

    @QtCore.Slot(str, str, list, list, list, result=int)
    def planCopy(
        self, sourceKey: str, targetKey: str, parts: list, profiles: list, modes: list
    ) -> int:
        name, guid = self._target(targetKey)
        parts, modes = list(parts), list(modes)
        return self._plan(
            "planCopy",
            self.api.copy.plan_copy,
            lambda chosen: (sourceKey, name, guid, parts, chosen, modes),
            self._paths(profiles),
        )

    @QtCore.Slot(str, str, list, list, list, result=int)
    def copy(
        self, sourceKey: str, targetKey: str, parts: list, profiles: list, modes: list
    ) -> int:
        name, guid = self._target(targetKey)
        return self._start(
            "copy",
            self.api.copy.copy,
            sourceKey,
            name,
            guid,
            list(parts),
            self._paths(profiles),
            list(modes),
            main=True,
            title=f"Copied {self._shown(sourceKey)} to {self._shown(targetKey)}",
        )

    @QtCore.Slot(str, str, list, list, result=int)
    def planSwap(
        self, firstKey: str, secondKey: str, parts: list, profiles: list
    ) -> int:
        first, second = self._target(firstKey), self._target(secondKey)
        parts = list(parts)
        return self._plan(
            "planSwap",
            self.api.swap.plan_swap,
            lambda chosen: (first, second, parts, chosen),
            self._paths(profiles),
        )

    @QtCore.Slot(str, str, list, list, result=int)
    def swap(self, firstKey: str, secondKey: str, parts: list, profiles: list) -> int:
        return self._start(
            "swap",
            self.api.swap.swap,
            self._target(firstKey),
            self._target(secondKey),
            list(parts),
            self._paths(profiles),
            main=True,
            title=f"Swapped {self._shown(firstKey)} with {self._shown(secondKey)}",
        )

    @staticmethod
    def _moves(moves: dict) -> dict[int, int]:
        return {int(k): int(v) for k, v in (moves or {}).items()}

    @QtCore.Slot(str, dict, bool, list, result=int)
    def planOutput(self, key: str, moves: dict, swapOther: bool, profiles: list) -> int:
        name, guid = self._target(key)
        clean, other = self._moves(moves), bool(swapOther)
        return self._plan(
            "planOutput",
            self.api.copy.plan_output,
            lambda chosen: (name, guid, clean, other, chosen),
            self._paths(profiles),
        )

    @QtCore.Slot(str, dict, bool, list, result=int)
    def changeOutput(
        self, key: str, moves: dict, swapOther: bool, profiles: list
    ) -> int:
        name, guid = self._target(key)
        return self._start(
            "output",
            self.api.copy.change_output,
            name,
            guid,
            self._moves(moves),
            bool(swapOther),
            self._paths(profiles),
            main=True,
            title=f"Changed the vJoy output of {self._shown(key)}",
        )

    @QtCore.Slot(result=int)
    def undo(self) -> int:
        """S53: puts the newest Library action of this session back."""
        if not self._steps.undo_text():
            return 0
        return self._start("undo", self._steps.undo, main=True)

    @QtCore.Slot(result=int)
    def redo(self) -> int:
        """S53: does the last undone Library action again."""
        if not self._steps.redo_text():
            return 0
        return self._start("redo", self._steps.redo, main=True)

    # | Undo and Redo steps (S53)

    @staticmethod
    def _step_start() -> float:
        from gremlin import library_undo

        return library_undo.started()

    def _grouped(self, title: str, fn: Callable[..., object]) -> Callable[..., object]:
        """fn as one History entry named title (S51)."""
        hist = getattr(self.api, "history", None)
        if hist is None:
            return fn

        def run(*args: object) -> object:
            token = hist.begin_group(title)
            try:
                return fn(*args)
            finally:
                hist.end_group(token)

        return run

    def _last_change(self) -> dict | None:
        try:
            return self.api.library.last_change()
        except Exception:  # noqa: BLE001 - nothing to undo it with
            logging.getLogger("system").exception("Device Library: no last change")
            return None

    def _take_step(self, since: float | None, action: dict | None = None) -> None:
        """The action that started at since has ended: what it recorded is
        a step for Undo (S53). Copy, Swap, Change vJoy Output and Restore
        (action) change the open profile too, which History doesn't hold
        (S33): they undo from the autosaves they kept and redo by running
        again."""
        if since is None:
            return
        undo: Callable[[], dict] | None = None
        redo: Callable[[], dict] | None = None
        if action is not None:
            kept = {"change": self._last_change()}
            copy = self.api.copy
            title = str(action["title"])
            fn, args = action["fn"], action["args"]

            def undo_it() -> dict:
                put_back = getattr(copy, "undo_change", None)
                if put_back is None:
                    run = self._grouped(f"Undid {title}", copy.undo_last)
                    return run()  # type: ignore[return-value]
                run = self._grouped(f"Undid {title}", put_back)
                return run(kept["change"])  # type: ignore[return-value]

            def redo_it() -> dict:
                out = self._grouped(title, fn)(*args)
                if isinstance(out, dict) and out.get("ok"):
                    kept["change"] = self._last_change()
                return out  # type: ignore[return-value]

            undo, redo = undo_it, redo_it
        try:
            self._steps.note(
                since,
                title=str(action["title"]) if action else "",
                undo=undo,
                redo=redo,
            )
        except Exception:  # noqa: BLE001 - the action is done either way
            logging.getLogger("system").exception("Device Library: no Undo step")
        self.stepsChanged.emit()

    def _shown(self, key: str) -> str:
        """A row's name for a step's title: a device's, or a saved setup's."""
        dev = self._device(key)
        if dev is not None:
            return str(dev.get("name") or "")
        _dev, setup = self._setup(key)
        return str((setup or {}).get("name") or "a saved setup")

    @QtCore.Slot(str, str, result=int)
    def exportSetup(self, key: str, url: str) -> int:
        dest = to_local_path(url)
        if dest.suffix.lower() != ".zip":
            dest = dest.with_name(dest.name + ".zip")
        # Main thread: the owner reads the settings and the modules folder
        # (item 7); its file work can go through library_profiles.background.
        return self._start(
            "export", self.api.library.export_setup, key, dest, main=True
        )

    @QtCore.Slot(str, result=int)
    def importPack(self, url: str) -> int:
        """S35, S39: a Device Pack .zip becomes a saved setup."""
        path = to_local_path(url)
        if path.suffix.lower() != ".zip":
            self.result.emit(
                _result(
                    "import",
                    {"ok": False, "error": f"{path.name} isn't a Device Pack (.zip)."},
                )
            )
            return 0
        return self._start("import", self.api.library.import_pack, path, main=True)

    @QtCore.Slot(str, result=int)
    def deleteItem(self, key: str) -> int:
        return self._start(
            "delete", self.api.library.delete, key, main=True, keys=[key]
        )

    # | The row menus' changes (S15, S44-S50)

    @QtCore.Slot(list)
    def beginRemove(self, keys: list) -> None:
        """S51-S52: Remove from Library is one History entry. Everything
        recorded on the main thread from now (Home's Delete Device run
        first by the window, then removeDevice/deleteMany) joins it until
        that removal's result, or endRemove()."""
        hist = getattr(self.api, "history", None)
        if hist is None:
            return
        self.endRemove()
        clean = [str(k) for k in keys or [] if str(k)]
        if len(clean) == 1:
            plan = self.removalPlan(clean[0])
            what = str(plan.get("shown") or plan.get("name") or "a device")
        else:
            what = f"{len(clean)} devices"
        self._group = hist.begin_group(f"Removed {what} from the Device Library")
        self._since = self._step_start()
        self._choices = self._file_choices() if self._group else None
        # A window that never ends it doesn't hold History's records.
        token = self._group
        QtCore.QTimer.singleShot(_GROUP_LIMIT_MS, self, lambda: self._end(token))

    @QtCore.Slot(str)
    def beginClearSetup(self, key: str) -> None:
        """S52 (D-10-ONE-ENTRY-TITLES): Clear Setup's autosave and module
        file delete (Home's Delete Device, run by the window) are one
        History entry, until endRemove()."""
        hist = getattr(self.api, "history", None)
        if hist is None:
            return
        self.endRemove()
        plan = self.removalPlan(str(key))
        what = str(plan.get("shown") or plan.get("name") or "a device")
        self._group = hist.begin_group(f"Cleared the setup of {what}")
        self._since = self._step_start()
        self._choices = self._file_choices() if self._group else None
        token = self._group
        QtCore.QTimer.singleShot(_GROUP_LIMIT_MS, self, lambda: self._end(token))

    @QtCore.Slot()
    def endRemove(self) -> None:
        self._end(self._group)

    def _end(self, token: str) -> None:
        hist = getattr(self.api, "history", None)
        if not token or token != self._group or hist is None:
            return
        self._group = ""
        self._note_choices(hist)
        hist.end_group(token)
        if not self._busy:
            # Clear Setup ends here, with no change of the model's own.
            since, self._since = self._since, None
            self._take_step(since)

    def _file_choices(self) -> str | None:
        read = getattr(self.api, "file_choices", None)
        try:
            return read() if read is not None else None
        except Exception:  # noqa: BLE001 - not kept, not recorded
            return None

    def _note_choices(self, hist: Any) -> None:  # noqa: ANN401
        """The file choices the removal dropped (03 S94, 10 S52): an
        internal setting the settings save doesn't record, so recorded here
        into the group, for its Restore."""
        before, self._choices = self._choices, None
        after = self._file_choices()
        if before is None or after is None or before == after:
            return
        key = "global/internal/module-file-bindings"
        hist.record(
            "settings",
            "Module file choices",
            {"keys": [key]},
            {key: json.dumps(json.loads(before))},
            {key: json.dumps(json.loads(after))},
        )

    def _removing(self, fn: Callable[..., dict], *args: object) -> Callable[[], dict]:
        """fn(*args), then each device it removed forgotten (S52: friendly
        name, Home card settings, calibration)."""
        keys = [str(k) for k in (args[0] if isinstance(args[0], list) else args)]
        targets = {k: self._target(k) for k in keys}

        def run() -> dict:
            out = fn(*args)
            forget = getattr(self.api, "forget", None)
            if forget is None or not isinstance(out, dict) or not out.get("ok"):
                return out
            gone = out.get("removed")
            for key in gone if isinstance(gone, list) else keys:
                name, guid = targets.get(str(key), ("", ""))
                if name or guid:
                    forget(name, guid)
            return out

        return run

    @QtCore.Slot(str, result=int)
    def removeDevice(self, key: str) -> int:
        """S15 Remove from Library: the device and all its saved setups
        (its module file, if any, went first through Home's Delete Device)."""
        ticket = self._start(
            "remove",
            self._removing(self.api.library.remove_device, key),
            main=True,
            keys=[key],
        )
        if not ticket:
            self.endRemove()
        return ticket

    @QtCore.Slot(str, result=int)
    def deleteSavedSetups(self, key: str) -> int:
        """S15 Delete Saved Setups: forgets a connected stick's saved
        setups; the stick keeps its settings."""
        return self._start(
            "deleteSetups",
            self.api.library.delete_saved_setups,
            key,
            main=True,
            keys=[key],
        )

    @QtCore.Slot(list, result=int)
    def deleteMany(self, keys: list) -> int:
        """S50: Delete... / Remove from Library... on every selected row."""
        clean = [str(k) for k in keys if str(k)]
        ticket = self._start(
            "deleteMany",
            self._removing(self.api.library.delete_many, clean),
            main=True,
            keys=clean,
        )
        if not ticket:
            self.endRemove()
        return ticket

    @QtCore.Slot(str, result=bool)
    def keep(self, key: str) -> bool:
        """S49 Keep This Autosave: the autosave becomes the user's own."""
        return self._now("keep", self.api.library.keep, key)

    @QtCore.Slot(str, result=int)
    def restoreToStick(self, key: str) -> int:
        """S48: a saved setup back on its own stick, as Copy does
        (autosave first, Undo)."""
        dev, _setup = self._setup(key)
        return self._start(
            "restore",
            self.api.copy.restore_to_stick,
            key,
            main=True,
            keys=[key],
            title=f"Restored {self._shown(key)} to "
            + str((dev or {}).get("name") or "its stick"),
        )

    @QtCore.Slot(str, str, result=int)
    def exportCurrent(self, key: str, url: str) -> int:
        """S44 Export Current Setup...: a Device Pack of the device's
        current settings."""
        dest = to_local_path(url)
        if dest.suffix.lower() != ".zip":
            dest = dest.with_name(dest.name + ".zip")
        return self._start(
            "exportCurrent",
            self.api.library.export_current,
            key,
            dest,
            main=True,
            keys=[key],
        )

    @QtCore.Slot(int, result=list)
    def tidyPreview(self, months: int) -> list:
        """S38: what Tidy would remove (nothing is removed here)."""
        try:
            return list(self.api.library.tidy_preview(int(months)))
        except Exception:
            logging.getLogger("system").exception("Device Library: tidy preview failed")
            return []

    @QtCore.Slot(list, result=int)
    def tidy(self, keys: list) -> int:
        return self._start(
            "tidy", self.api.library.tidy, [str(k) for k in keys], main=True
        )

    @QtCore.Slot(result=dict)
    def settings(self) -> dict:
        try:
            return dict(self.api.library.settings())
        except Exception:
            return dict(self._settings)

    @QtCore.Slot(dict, result=int)
    def setSettings(self, values: dict) -> int:
        clean: dict[str, Any] = {}
        if "keep" in values:
            clean["keep"] = max(1, int(values["keep"]))
        if "default_parts" in values:
            clean["default_parts"] = [p for p in values["default_parts"] if p in PARTS]
        if "folder" in values:
            clean["folder"] = (
                str(to_local_path(values["folder"])) if values["folder"] else ""
            )

        def apply() -> dict:
            self.api.library.set_settings(clean)
            return {"ok": True}

        # Main thread: the folder is a program setting (Configuration().set).
        return self._start("settings", apply, main=True)

    @QtCore.Slot(result=list)
    def connectedSticks(self) -> list:
        """The devices plugged in now (To lists: S22, S26)."""
        out = []
        connected = [d for d in self._devices if d.get("state") == "connected"]
        names = [str(d.get("name", "")).casefold() for d in connected]
        for dev in connected:
            # Twins (the same name) are told apart by their id.
            label = _twin_label(dev, names)
            if dev.get("description"):
                label += f"  ({dev['description']})"
            out.append(
                {
                    "key": dev["key"],
                    "name": dev.get("name", ""),
                    "guid": dev.get("guid", ""),
                    "label": label,
                }
            )
        return out

    @QtCore.Slot(list, result=int)
    @QtCore.Slot(list, bool, result=int)
    def profilesUsing(self, guids: list, alwaysOpen: bool = False) -> int:
        """The profiles with bindings for these devices: result op
        "profiles" with "profiles". The open profile is read here on the
        main thread (it is edited there), the saved ones in the background.
        alwaysOpen keeps the open profile in the list even with no bindings
        for them (Copy, Swap, Change: S23, 08 S89, D-10-PROFILES)."""
        clean = [str(g) for g in guids if str(g)]
        prof = self.api.profiles
        try:
            row = prof.open_profile_row(clean, True)
        except Exception:
            logging.getLogger("system").exception("Device Library: open profile")
            row = None
        open_path = str(row.get("path") or "") if row else ""
        if row is not None and not alwaysOpen and not int(row.get("actions") or 0):
            row = None

        def work() -> dict:
            found = list(prof.saved_profiles_using(clean, open_path)) if clean else []
            rows = ([row] if row is not None else []) + found
            return {
                "ok": True,
                "profiles": [dict(p, path=str(p.get("path", ""))) for p in rows],
            }

        return self._start("profiles", work, change=False)

    @QtCore.Slot(list, result=str)
    def alsoMoveText(self, others: list) -> str:
        """S30: the "Also move …" line for every other stick on a target
        vJoy (the plan's others: [{name, vjoy, to}]), "" when none."""
        return also_move_text(list(others or []))

    @QtCore.Slot(result=list)
    def vjoyNumbers(self) -> list:
        """S30: the vJoy devices that exist (from the output modules)."""
        read = getattr(self.api, "vjoy_ids", None)
        if read is None:
            return []
        try:
            return sorted({int(n) for n in read()})
        except Exception:
            logging.getLogger("system").exception("Device Library: vJoy list")
            return []

    @QtCore.Slot(str, result=str)
    def fileUrl(self, path: str) -> str:
        return QtCore.QUrl.fromLocalFile(path).toString() if path else ""
