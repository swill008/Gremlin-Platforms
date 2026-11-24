# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Health window's model (01 S197, D-01-HEALTH, layer 3): Look in (All
profiles / This profile only), the four checks as tick boxes with counts,
the rows with a ticked problem grouped profile → device as one flat list
(header rows and result rows), the picked lines (Ctrl/Shift), the Why
panel's facts, and Remove binding… / Change target… / Undo. The rows come
from gremlin.search_index; the findings only from gremlin.health (the one
owner of the rules and their results). Edits are gremlin.binding_edit's;
a change to several lines is one Undo."""

from __future__ import annotations

import html
import logging
from collections.abc import Callable
from typing import Any

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin.signal import signal
from gremlin.ui.device import QML_IMPORT_MAJOR_VERSION, QML_IMPORT_NAME

assert QML_IMPORT_NAME == "Gremlin.Device"
assert QML_IMPORT_MAJOR_VERSION == 1

log = logging.getLogger("system")

# Open-profile notices wait this long before the index rebuilds it (ms).
REBUILD_MS = 300

LOOK_IN = ("all", "this")
LOOK_IN_LABELS = {"all": "All profiles", "this": "This profile only"}
DEFAULT_LOOK_IN = "this"

# The box's title when an edit can't be made (as Search's, 01 S195).
REFUSED_TITLE = "Can't change the binding"
# The action Change target… is for (Map to vJoy).
VJOY_TAG = "map-to-vjoy"

# Menu places a fix text may name -> the command that opens them. A new
# place adds its line here.
FIX_LINKS = {
    "Tools › Drivers": "tools.drivers",
    "Tools › Xbox Setup": "tools.xboxSetup",
    "Tools › HidHide": "tools.hidhide",
    "Tools › Input Module Setup": "tools.configureInput",
    "Tools › Output Module Setup": "tools.configureOutput",
    "Tools › Device Library": "tools.deviceLibrary",
}

# The SearchRow fields shown as roles (camelCase).
ROW_FIELDS = (
    ("source", "source"),
    ("source_name", "sourceName"),
    ("source_path", "sourcePath"),
    ("device_guid", "deviceGuid"),
    ("device_name", "deviceName"),
    ("mode", "mode"),
    ("input_type", "inputType"),
    ("input_id", "inputId"),
    ("input_label", "inputLabel"),
    ("custom_name", "customName"),
    ("action_tag", "actionTag"),
    ("action_name", "actionName"),
    ("text", "text"),
    ("targets", "targets"),
    ("target_keys", "targetKeys"),
    ("role", "role"),
    ("binding_index", "bindingIndex"),
    ("path", "path"),
    ("notes", "notes"),
    ("inherited_from", "inheritedFrom"),
)
_FIELD_DEFAULTS: dict[str, object] = {"notes": (), "inherited_from": ""}
ROLE_NAMES = (
    "rowKind",
    "title",
    "count",
    "folded",
    "groupKey",
    "depth",
    *(name for _, name in ROW_FIELDS),
    "checks",
    "notFound",
    "why",
    "notPlugged",
    "usedTwice",
    "reasons",
    "selected",
)


def _qml(value: object) -> object:
    """A SearchRow value for QML: tuples as lists, enums as values."""
    if isinstance(value, (tuple, list)):
        return [_qml(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted(str(item) for item in value)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    inner = getattr(value, "value", None)
    if inner is not None and value.__class__.__module__ != "builtins":
        return _qml(inner)
    return str(value)


def fix_html(text: str) -> str:
    """A fix text as rich text: the places it names (FIX_LINKS) as links
    whose href is the command that opens them."""
    out = html.escape(str(text or ""), quote=False)
    for name, command in FIX_LINKS.items():
        shown = html.escape(name, quote=False)
        out = out.replace(shown, f'<a href="{command}">{shown}</a>')
    return out


def row_line(row: Any, reasons: list[str] | tuple[str, ...] = ()) -> str:  # noqa: ANN401
    """A row as one line of text (Copy as text): where, what, and why."""
    name = row.input_label
    if row.custom_name:
        name = f"{row.custom_name} ({row.input_label})"
    line = " › ".join(
        str(part) for part in (row.source_name, row.device_name, row.mode, name) if part
    )
    if row.text:
        line += f": {row.text}"
    if row.targets:
        line += " → " + ", ".join(row.targets)
    if reasons:
        line += " · " + " ".join(str(r) for r in reasons)
    return line


def _default_index() -> Any:  # noqa: ANN401
    from gremlin import search_index

    return search_index.default_index()


def _default_health() -> Any:  # noqa: ANN401
    from gremlin import health

    return health


# Health follows plugging in and out once, from the first window (main thread).
_watching = False


def _watch_devices(health: Any) -> None:  # noqa: ANN401
    global _watching
    if _watching:
        return
    try:
        health.watch_devices()
        _watching = True
    except Exception:  # noqa: BLE001 - no device events (tests, early start)
        log.debug("Health: device changes not followed", exc_info=True)


def _set_clipboard(text: str) -> None:
    """Search's clipboard helper (main thread only; tests replace it)."""
    from gremlin.ui import search_model

    search_model._set_clipboard(text)


def _row_id(row: Any) -> tuple:  # noqa: ANN401
    """A picked line's identity across relayouts."""
    return (
        row.source,
        row.source_path,
        str(row.device_guid),
        row.mode,
        row.input_type,
        repr(row.input_id),
        row.binding_index,
        tuple(row.path),
        row.inherited_from,
        row.action_tag,
    )


@ta.QmlElement
class HealthModel(QtCore.QAbstractListModel):
    """The Health window: the rows with problems, grouped, and their fixes."""

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1 + i: QtCore.QByteArray(name.encode())
        for i, name in enumerate(ROLE_NAMES)
    }

    lookInChanged = QtCore.Signal()
    checksChanged = QtCore.Signal()
    resultsChanged = QtCore.Signal()
    selectionChanged = QtCore.Signal()
    undoChanged = QtCore.Signal()
    # An edit or undo was refused: (title, why) for the window's box.
    editRefused = QtCore.Signal(str, str)
    # Health's results changed (any thread): carried to the main thread.
    _healthChanged = QtCore.Signal()

    def __init__(
        self,
        parent: ta.OQO = None,
        index: Any = None,  # noqa: ANN401
        health: Any = None,  # noqa: ANN401
    ) -> None:
        super().__init__(parent)
        self._index: Any = index
        self._health: Any = health
        self._look_in = DEFAULT_LOOK_IN
        self._checks_on: set[str] = set(self.health().CHECKS)
        self._folded: set[str] = set()
        self._rows: list[dict] = []
        self._counts: dict[str, int] = {}
        self._problem_count = 0
        self._profile_count = 0
        self._selected: set[tuple] = set()
        self._anchor = -1
        self._closed = False
        # Undo: one list of binding_edit records per change (a change to
        # several lines is one entry), for the profile they are on.
        self._undo: list[list[Any]] = []
        self._undo_profile: Any = None

        self._rebuild_timer = QtCore.QTimer(self)
        self._rebuild_timer.setSingleShot(True)
        self._rebuild_timer.setInterval(REBUILD_MS)
        self._rebuild_timer.timeout.connect(self._rebuild_open)
        self._healthChanged.connect(
            self._on_health_changed, QtCore.Qt.ConnectionType.QueuedConnection
        )
        for notice in self._notices():
            notice.connect(self._rebuild_soon)
        _watch_devices(self.health())
        self._fresh_index()
        try:
            self.health().on_changed(self._health_changed_any_thread)
        except Exception:  # noqa: BLE001 - no health: the list stays as it is
            log.exception("Health: could not follow the results")
        self._run()

    # Sources.

    def health(self) -> Any:  # noqa: ANN401
        if self._health is None:
            self._health = _default_health()
        return self._health

    def search_index(self) -> Any:  # noqa: ANN401
        if self._index is None:
            self._index = _default_index()
        return self._index

    def _fresh_index(self) -> None:
        """The index may be older than this window (the toolbar's Health
        count builds it at start-up): the open profile and the other
        sources are read again."""
        try:
            self._rebuild_open()
            refresh = getattr(self.search_index(), "refresh_sources", None)
            if refresh is not None:
                refresh()
        except Exception:  # noqa: BLE001 - the old rows stay
            log.exception("Health: the index could not be read again")

    def _health_changed_any_thread(self) -> None:
        try:
            self._healthChanged.emit()
        except RuntimeError:  # the model is gone
            pass

    @QtCore.Slot()
    def _on_health_changed(self) -> None:
        if not self._closed:
            self._run()
            self.undoChanged.emit()

    @staticmethod
    def _notices() -> tuple:
        return (
            signal.profileChanged,
            signal.bindingsChanged,
            signal.actionsChanged,
            signal.modesChanged,
        )

    @QtCore.Slot()
    def _rebuild_soon(self) -> None:
        self._rebuild_timer.start()

    @QtCore.Slot()
    def _rebuild_open(self) -> None:
        from gremlin import shared_state

        try:
            self.search_index().rebuild_open(shared_state.current_profile)
        except Exception:  # noqa: BLE001 - the old rows stay
            log.exception("Health: the open profile could not be indexed again")

    @QtCore.Slot()
    def close(self) -> None:
        """Stop following notices and health (window closed, tests). A Slot,
        or QML's onClosing call never reaches it."""
        if self._closed:
            return
        self._closed = True
        self._rebuild_timer.stop()
        for notice in self._notices():
            try:
                notice.disconnect(self._rebuild_soon)
            except (RuntimeError, TypeError):
                pass
        try:
            self.health().remove_listener(self._health_changed_any_thread)
        except Exception:  # noqa: BLE001
            pass

    # Look in and the checks.

    def _get_look_in(self) -> str:
        return self._look_in

    def _set_look_in(self, value: str) -> None:
        value = str(value)
        if value in LOOK_IN and value != self._look_in:
            self._look_in = value
            self.lookInChanged.emit()
            self._run()

    lookIn = QtCore.Property(
        str, fget=_get_look_in, fset=_set_look_in, notify=lookInChanged
    )

    @QtCore.Property(list, constant=True)
    def scopes(self) -> list:
        return [{"name": n, "label": LOOK_IN_LABELS[n]} for n in LOOK_IN]

    @QtCore.Property(list, notify=checksChanged)
    def checks(self) -> list:
        """[{name, label, on, count}] in the order shown."""
        labels = self.health().LABELS
        return [
            {
                "name": name,
                "label": labels.get(name, name),
                "on": name in self._checks_on,
                "count": int(self._counts.get(name, 0)),
            }
            for name in self.health().CHECKS
        ]

    @QtCore.Slot(str, bool)
    def setCheck(self, name: str, on: bool) -> None:  # noqa: N802
        if name not in self.health().CHECKS:
            return
        before = set(self._checks_on)
        if on:
            self._checks_on.add(name)
        else:
            self._checks_on.discard(name)
        if before != self._checks_on:
            self._run()

    # The results.

    def _all_rows(self) -> list:
        try:
            return list(self.search_index().rows())
        except Exception:  # noqa: BLE001 - no index yet
            log.debug("Health: no rows", exc_info=True)
            return []

    def _in_scope(self, rows: list) -> list:
        if self._look_in == "this":
            return [r for r in rows if r.source == "open"]
        # The open profile stands for its file; the Device Library is not a profile.
        open_paths = {r.source_path for r in rows if r.source == "open"}
        return [
            r
            for r in rows
            if r.source != "library"
            and not (r.source == "profile" and r.source_path in open_paths)
        ]

    def _findings(self, row: Any) -> tuple:  # noqa: ANN401
        try:
            return tuple(self.health().findings(row))
        except Exception:  # noqa: BLE001 - a row health can't read
            log.debug("Health: no findings for a row", exc_info=True)
            return ()

    def _run(self) -> None:
        rows = self._in_scope(self._all_rows())
        try:
            self._counts = dict(self.health().counts(rows))
        except Exception:  # noqa: BLE001
            log.debug("Health: no counts", exc_info=True)
            self._counts = {}
        shown = []
        for row in rows:
            found = [f for f in self._findings(row) if f.check in self._checks_on]
            if found:
                shown.append((row, tuple(found)))
        self._problem_count = len(shown)
        self._profile_count = len({(r.source, r.source_path) for r, _ in shown})
        self._layout(shown)
        self.checksChanged.emit()

    def _layout(self, shown: list[tuple[Any, tuple]]) -> None:
        source_order = {"open": 0, "profile": 1}
        groups: dict[tuple, dict[tuple, list]] = {}
        names: dict[tuple, Any] = {}
        for pair in shown:
            row = pair[0]
            profile_key = (row.source, row.source_path)
            names[profile_key] = row
            groups.setdefault(profile_key, {}).setdefault(
                (str(row.device_guid), row.device_name), []
            ).append(pair)
        flat: list[dict] = []
        for profile_key in sorted(
            groups,
            key=lambda k: (
                source_order.get(k[0], 2),
                str(names[k].source_name).casefold(),
            ),
        ):
            first = names[profile_key]
            pkey = f"{profile_key[0]}|{profile_key[1]}"
            devices = groups[profile_key]
            title = first.source_name
            if first.source == "open":
                title = f"{title} (open)"
            flat.append(
                self._header("profile", title, pkey, 0, sum(map(len, devices.values())))
            )
            if pkey in self._folded:
                continue
            for device_key in sorted(devices, key=lambda k: str(k[1]).casefold()):
                dkey = f"{pkey}|{device_key[0]}"
                pairs = devices[device_key]
                flat.append(self._header("device", device_key[1], dkey, 1, len(pairs)))
                if dkey in self._folded:
                    continue
                flat.extend(self._result(row, found, dkey) for row, found in pairs)
        live = {_row_id(item["_row"]) for item in flat if "_row" in item}
        self._selected &= live
        self.beginResetModel()
        self._rows = flat
        self.endResetModel()
        self._anchor = -1
        self.resultsChanged.emit()
        self.selectionChanged.emit()

    def _header(self, kind: str, title: str, key: str, depth: int, count: int) -> dict:
        return {
            "rowKind": kind,
            "title": str(title),
            "count": count,
            "folded": key in self._folded,
            "groupKey": key,
            "depth": depth,
        }

    def _result(self, row: Any, found: tuple, key: str) -> dict:  # noqa: ANN401
        checks = [f.check for f in found]
        item = {
            "rowKind": "result",
            "title": str(row.custom_name or row.input_label),
            "count": 0,
            "folded": False,
            "groupKey": key,
            "depth": 2,
            "checks": checks,
            "notFound": "notFound" in checks,
            "why": next((f.why for f in found if f.check == "notFound"), ""),
            "notPlugged": "notPlugged" in checks,
            "usedTwice": "usedTwice" in checks,
            "reasons": [str(f.why) for f in found],
            "selected": _row_id(row) in self._selected,
            "_row": row,
            "_found": found,
        }
        for field, name in ROW_FIELDS:
            item[name] = _qml(getattr(row, field, _FIELD_DEFAULTS.get(field)))
        return item

    @QtCore.Property(int, notify=resultsChanged)
    def problemCount(self) -> int:  # noqa: N802
        return self._problem_count

    @QtCore.Property(int, notify=resultsChanged)
    def profileCount(self) -> int:  # noqa: N802
        return self._profile_count

    @QtCore.Property(str, notify=resultsChanged)
    def statusText(self) -> str:  # noqa: N802
        """'N problem(s) in N profile(s)'."""
        n, p = self._problem_count, self._profile_count
        return (
            f"{n} {'problem' if n == 1 else 'problems'} in {p} "
            f"{'profile' if p == 1 else 'profiles'}"
        )

    @QtCore.Slot(int)
    def toggleFold(self, row: int) -> None:  # noqa: N802
        if 0 <= row < len(self._rows) and self._rows[row]["rowKind"] != "result":
            self._folded ^= {self._rows[row]["groupKey"]}
            self._run()

    # Rows for QML.

    def _found(self, row: int) -> Any:  # noqa: ANN401
        if not 0 <= row < len(self._rows):
            return None
        return self._rows[row].get("_row")

    @QtCore.Slot(int, result="QVariantMap")
    def get(self, row: int) -> dict:
        """One row's roles as a map (to go to it)."""
        if not 0 <= row < len(self._rows):
            return {}
        return {k: v for k, v in self._rows[row].items() if not k.startswith("_")}

    @QtCore.Slot(int, result="QVariantMap")
    def why(self, row: int) -> dict:
        """The Why panel: {title, findings: [{check, label, why, fix, fixHtml}]}."""
        if self._found(row) is None:
            return {}
        labels = self.health().LABELS
        item = self._rows[row]
        return {
            "title": item["title"],
            "findings": [
                {
                    "check": f.check,
                    "label": labels.get(f.check, f.check),
                    "why": str(f.why),
                    "fix": str(f.fix),
                    "fixHtml": fix_html(f.fix),
                }
                for f in item["_found"]
            ],
        }

    # Picking lines (Ctrl+click, Shift+click).

    def _result_rows(self) -> list[int]:
        return [i for i, item in enumerate(self._rows) if "_row" in item]

    @QtCore.Slot(int, bool, bool)
    def select(self, row: int, ctrl: bool = False, shift: bool = False) -> None:
        """Click: only this line; Ctrl: add or take it away; Shift: every
        line from the last clicked one to this one."""
        if self._found(row) is None:
            return
        key = _row_id(self._rows[row]["_row"])
        if shift and self._anchor >= 0:
            low, high = sorted((self._anchor, row))
            span = {
                _row_id(self._rows[i]["_row"])
                for i in self._result_rows()
                if low <= i <= high
            }
            self._selected = (self._selected | span) if ctrl else span
        elif ctrl:
            self._selected ^= {key}
            self._anchor = row
        else:
            self._selected = {key}
            self._anchor = row
        self._selection_shown()

    @QtCore.Slot()
    def clearSelection(self) -> None:  # noqa: N802
        self._selected = set()
        self._anchor = -1
        self._selection_shown()

    def _selection_shown(self) -> None:
        for i in self._result_rows():
            self._rows[i]["selected"] = _row_id(self._rows[i]["_row"]) in self._selected
        if self._rows:
            role = next(
                r for r, n in self.roles.items() if n.toStdString() == "selected"
            )
            self.dataChanged.emit(
                self.index(0), self.index(len(self._rows) - 1), [role]
            )
        self.selectionChanged.emit()

    def _selected_rows(self) -> list[int]:
        return [i for i in self._result_rows() if self._rows[i]["selected"]]

    @QtCore.Property(list, notify=selectionChanged)
    def selectedRows(self) -> list:  # noqa: N802
        return self._selected_rows()

    @QtCore.Property(int, notify=selectionChanged)
    def selectedCount(self) -> int:  # noqa: N802
        return len(self._selected_rows())

    def _picked(self) -> list[Any]:
        return [self._rows[i]["_row"] for i in self._selected_rows()]

    # Copy, Open.

    @QtCore.Slot(result=str)
    def copyText(self) -> str:  # noqa: N802
        """The picked lines as text (one per line), also on the clipboard."""
        lines = [
            row_line(self._rows[i]["_row"], self._rows[i]["reasons"])
            for i in self._selected_rows()
        ]
        text = "\n".join(lines)
        if text:
            _set_clipboard(text)
        return text

    @QtCore.Slot(int, result=str)
    def openMessage(self, row: int) -> str:  # noqa: N802
        """Why Open can't go to the row's page ("" when it can)."""
        found = self._found(row)
        if found is None or not self._rows[row]["notPlugged"]:
            return ""
        name = str(found.device_name or "")
        try:
            from gremlin import binding_edit

            name = binding_edit.device_name(str(found.device_guid)) or name
        except Exception:  # noqa: BLE001 - the stored name stays
            pass
        return (
            f"{name} isn't plugged in, so its page can't open. Use Remove "
            "binding… or Change target… here, or plug it in."
        )

    # Fixing bindings (01 S195 edits, S197 several at once, one Undo).

    @staticmethod
    def _editable(row: Any) -> bool:  # noqa: ANN401
        return row is not None and row.source == "open" and bool(row.action_tag)

    @QtCore.Slot(result="QVariantMap")
    def fixes(self) -> dict:
        """What the menu offers for the picked lines: {remove, changeTarget}.
        Remove binding… when every picked line is an action of the open
        profile; Change target… for one picked Map to vJoy line."""
        picked = self._picked()
        remove = bool(picked) and all(self._editable(r) for r in picked)
        change = (
            len(picked) == 1
            and self._editable(picked[0])
            and picked[0].action_tag == VJOY_TAG
        )
        return {"remove": remove, "changeTarget": bool(change)}

    @QtCore.Slot(result=str)
    def removeQuestion(self) -> str:  # noqa: N802
        if not self.fixes()["remove"]:
            return ""
        picked = self._picked()
        if len(picked) > 1:
            return f"Remove {len(picked)} bindings?"
        from gremlin import binding_edit

        return f"Remove {binding_edit.describe(picked[0])}?"

    @QtCore.Slot(result=bool)
    def removeSelected(self) -> bool:  # noqa: N802
        """Removes the picked lines' actions, as one change (one Undo).
        The last action of a binding goes first, so the others keep their
        places."""
        if not self.fixes()["remove"]:
            return False
        from gremlin import binding_edit

        picked = sorted(
            self._picked(),
            key=lambda r: (int(r.binding_index or 0), tuple(r.path)),
            reverse=True,
        )
        return self._edited(
            [lambda r=r: binding_edit.remove_binding(r) for r in picked]
        )

    @QtCore.Slot(result="QVariantMap")
    def changeTargetStart(self) -> dict:  # noqa: N802
        """Change target…'s start: {vjoyId, inputType, inputId} ({} when
        it can't be changed)."""
        if not self.fixes()["changeTarget"]:
            return {}
        from gremlin.types import InputType

        for key in self._picked()[0].target_keys:
            if len(key) == 4 and key[0] == "vjoy":
                try:
                    kind = InputType.to_string(InputType(int(key[2])))
                except Exception:  # noqa: BLE001 - an odd target
                    continue
                return {
                    "vjoyId": int(key[1]),
                    "inputType": kind,
                    "inputId": int(key[3]),
                }
        return {}

    @QtCore.Slot(int, str, int, result=bool)
    def changeTarget(self, vjoy_id: int, kind: str, control: int) -> bool:  # noqa: N802
        if not self.fixes()["changeTarget"] or int(vjoy_id) <= 0:
            return False
        from gremlin import binding_edit

        row = self._picked()[0]
        return self._edited(
            [
                lambda: binding_edit.change_vjoy_target(
                    row, int(vjoy_id), str(kind), int(control)
                )
            ]
        )

    def _edited(self, edits: list[Callable[[], Any]]) -> bool:
        """Do the edits as one change; keep what was done for Undo even when
        one is refused (the box says why)."""
        from gremlin import shared_state

        done: list[Any] = []
        refused: Exception | None = None
        for edit in edits:
            try:
                done.append(edit())
            except Exception as err:  # noqa: BLE001 - the binding is gone or changed
                refused = err
                break
        if done:
            if self._undo_profile is not shared_state.current_profile:
                self._undo = []
            self._undo_profile = shared_state.current_profile
            self._undo.append(done)
            self._refresh_now()
        if refused is not None:
            self._refused(refused)
        return refused is None

    def _refused(self, err: Exception) -> None:
        from gremlin import binding_edit

        if isinstance(err, binding_edit.EditError) and str(err):
            text = str(err)
        else:
            text = "The binding could not be changed. The log has the details."
        log.warning("Health: %s", text, exc_info=err)
        self.editRefused.emit(REFUSED_TITLE, text)

    def _refresh_now(self) -> None:
        self._rebuild_timer.stop()
        self._rebuild_open()
        self._run()
        self.undoChanged.emit()

    def _undo_live(self) -> bool:
        """Undo lasts until the profile is saved or closed."""
        from gremlin import shared_state

        profile = shared_state.current_profile
        if not self._undo or profile is None or profile is not self._undo_profile:
            return False
        try:
            return bool(profile.has_unsaved_changes())
        except Exception:  # noqa: BLE001 - no change tracking
            return True

    @QtCore.Property(bool, notify=undoChanged)
    def canUndo(self) -> bool:  # noqa: N802
        return self._undo_live()

    @QtCore.Slot(result=bool)
    def undo(self) -> bool:
        """Takes back the last change, all its lines (Ctrl+Z)."""
        if not self._undo_live():
            if self._undo:
                self._undo = []
                self.undoChanged.emit()
            return False
        from gremlin import binding_edit

        group = self._undo.pop()
        while group:
            record = group[-1]
            try:
                binding_edit.undo(record)
            except Exception as err:  # noqa: BLE001 - refused (running): try later
                if not getattr(record, "done", False):
                    self._undo.append(group)
                self._refused(err)
                self._refresh_now()
                return False
            group.pop()
        self._refresh_now()
        return True

    # Model.

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._rows)

    def data(
        self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> Any:  # noqa: ANN401
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        name = self.roles.get(role)
        if name is None:
            return None
        return self._rows[index.row()].get(name.toStdString())

    def roleNames(self) -> dict[int, QtCore.QByteArray]:  # noqa: N802
        return self.roles
