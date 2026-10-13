# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Search window's model (D-01-SEARCH-INDEX, layer 3): the typed text
and toggles, Look in, quick and Health filters with counts, results grouped
profile → device as one flat list (header rows and result rows), sort,
folds, the detail pane's facts, Listen, suggestions and the nothing-found
hints. Rows come from gremlin.search_index; matching from
gremlin.search_query. It only reads: it changes nothing."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from typing import Any

from PySide6 import QtCore, QtGui

import gremlin.ui.type_aliases as ta
from gremlin.signal import signal
from gremlin.ui.device import QML_IMPORT_MAJOR_VERSION, QML_IMPORT_NAME

assert QML_IMPORT_NAME == "Gremlin.Device"
assert QML_IMPORT_MAJOR_VERSION == 1

log = logging.getLogger("system")

# Typing waits this long before searching (ms).
DEBOUNCE_MS = 120
# Open-profile notices wait this long before the index rebuilds it (ms).
REBUILD_MS = 300
# A search kept this long without typing goes into Recent (ms).
RECENT_MS = 1500
RECENT_MAX = 10
# The remembered state's name in window_placement's tool-row store.
STATE_NAME = "search"

LOOK_IN = ("all", "this", "library")
# Look in's choices as the window names them.
LOOK_IN_LABELS = {
    "all": "All profiles",
    "this": "This profile only",
    "library": "Device Library",
}

# Quick filters (Show): name -> label; a row passes when its kinds hold the
# name. The kinds come from SearchRow.kinds, so a new kind needs only a
# line here.
KIND_FILTERS: dict[str, str] = {
    "key": "Keys",
    "action": "Actions",
    "name": "Names",
    "vjoy": "vJoy",
    "xbox": "Xbox",
    "osc": "OSC",
}


def _no_bindings(row: Any) -> bool:  # noqa: ANN401
    return not getattr(row, "action_tag", "")


# Health filters: name -> (label, test on a SearchRow).
HEALTH_FILTERS: dict[str, tuple[str, Callable[[Any], bool]]] = {
    "usedTwice": ("Used twice", lambda row: bool(getattr(row, "used_twice", False))),
    "notFound": (
        "Binding output not found",
        lambda row: bool(getattr(row, "not_found", False)),
    ),
    "noBindings": ("No bindings", _no_bindings),
    "notPlugged": (
        "Not plugged in",
        lambda row: (
            getattr(row, "source", "") != "library"
            and getattr(row, "plugged", None) is False
        ),
    ),
}

# The SearchRow fields shown as roles (camelCase), in contract order.
ROW_FIELDS = (
    ("source", "source"),
    ("source_name", "sourceName"),
    ("source_path", "sourcePath"),
    ("device_guid", "deviceGuid"),
    ("device_name", "deviceName"),
    ("plugged", "plugged"),
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
    ("not_found", "notFound"),
    ("why", "why"),
    ("used_twice", "usedTwice"),
    ("binding_index", "bindingIndex"),
    ("path", "path"),
    ("kinds", "kinds"),
    ("notes", "notes"),
    ("inherited_from", "inheritedFrom"),
)
# Values for fields a row may not carry.
_FIELD_DEFAULTS: dict[str, object] = {"notes": (), "inherited_from": ""}
ROLE_NAMES = (
    "rowKind",
    "title",
    "count",
    "folded",
    "groupKey",
    "depth",
    *(name for _, name in ROW_FIELDS),
    "highlights",
    "tags",
    "notPlugged",
    "score",
)
SORT_COLUMNS = {
    "input": lambda row: (str(row.input_label).casefold(), str(row.custom_name)),
    "mode": lambda row: str(row.mode).casefold(),
    "action": lambda row: (str(row.action_name).casefold(), str(row.text)),
}


def _qml(value: object) -> object:
    """A SearchRow value for QML: tuples and sets as lists, enums as values."""
    if isinstance(value, (tuple, list)):
        return [_qml(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted(str(item) for item in value)
    if hasattr(value, "value") and value.__class__.__module__ != "builtins":
        try:
            return _qml(value.value)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - not an enum after all
            return str(value)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def _tags(row: Any) -> list[str]:  # noqa: ANN401
    tags = []
    if getattr(row, "used_twice", False):
        tags.append("usedTwice")
    if getattr(row, "not_found", False):
        tags.append("notFound")
    if HEALTH_FILTERS["notPlugged"][1](row):
        tags.append("notPlugged")
    if getattr(row, "inherited_from", ""):
        tags.append("inherited")
    return tags


def _spans(match: Any) -> dict:  # noqa: ANN401
    """A Match's highlight spans per field as {qmlField: [[start, end]…]}."""
    raw = getattr(match, "spans", None) or getattr(match, "highlights", None) or {}
    names = dict(ROW_FIELDS)
    found: dict[str, list] = {}
    for field, spans in dict(raw).items():
        found[str(names.get(field) or field)] = [[int(a), int(b)] for a, b in spans]
    return found


def _quoted(text: str) -> str:
    return '"' + str(text).replace('"', "") + '"'


def heard_text(event: Any) -> tuple[str, str]:  # noqa: ANN401
    """A Listen event (stick or key) as (what was heard, search text)."""
    from gremlin import common
    from gremlin.types import InputType

    kind = getattr(event, "event_type", None)
    ident = getattr(event, "identifier", None)
    try:
        label = common.input_to_ui_string(kind, ident)  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001 - an input with no ui string
        label = str(ident)
    if kind == InputType.Keyboard:
        return label, f"key:{_quoted(label)}"
    from gremlin.ui.input_pairing import device_label

    device = device_label(str(getattr(event, "device_guid", "") or ""))
    return f"{device} {label}", f"device:{_quoted(device)} {_quoted(label)}"


def target_text(row: Any, i: int = 0) -> str:  # noqa: ANN401
    """Search text for every use of a row's target i: its kind's prefix and
    quoted display text (vjoy:"vJoy 2 Button 30") when that prefix reads
    the target, else the quoted text alone."""
    from gremlin import search_index, search_query

    keys = tuple(getattr(row, "target_keys", ()) or ())
    shown = tuple(getattr(row, "targets", ()) or ())
    if i >= len(keys):
        return ""
    label = shown[i] if i < len(shown) else search_query.display(keys[i])
    prefix = search_index.TARGET_KINDS.get(str(keys[i][0]) if keys[i] else "", "")
    if prefix in search_query.PREFIXES:
        looked = search_query.prefix_texts(prefix, row)
        if any(key == f"targets:{i}" for key, *_ in looked):
            return f"{prefix}:{_quoted(label)}"
    return _quoted(label)


def _set_clipboard(text: str) -> None:
    """Text on the clipboard: only in a GUI application, on its thread
    (the clipboard is a main-thread object). Tests replace this: the real
    clipboard is the user's and setText crashed full runs (conftest's
    _no_real_clipboard)."""
    app = QtGui.QGuiApplication.instance()
    if not isinstance(app, QtGui.QGuiApplication):
        return
    if QtCore.QThread.currentThread() is not app.thread():
        log.warning("Search: Copy as text ignored off the main thread")
        return
    board = QtGui.QGuiApplication.clipboard()
    if board is not None:
        board.setText(text)


def _default_index() -> Any:  # noqa: ANN401
    """The program's one index (made and built on first use; saves reach it
    through search_index.note_saved)."""
    from gremlin import search_index

    return search_index.default_index()


def _settings_load() -> dict:
    from gremlin.ui import window_placement

    try:
        return dict(window_placement.tool_row_state(STATE_NAME))
    except Exception:  # noqa: BLE001 - no settings store (early start-up)
        return {}


def _settings_save(state: dict) -> None:
    from gremlin.ui import window_placement

    try:
        window_placement.save_tool_row_state(STATE_NAME, state)
    except Exception:  # noqa: BLE001 - no settings store (early start-up)
        log.debug("Search: could not save its state", exc_info=True)


def _toggle(field: str, notify: QtCore.Signal) -> QtCore.Property:
    """A search toggle (Aa, ab, .*) kept in self.<field>."""

    def get(self: SearchModel) -> bool:
        return bool(getattr(self, field))

    def put(self: SearchModel, value: bool) -> None:
        if bool(value) != getattr(self, field):
            setattr(self, field, bool(value))
            self.togglesChanged.emit()
            self._changed()

    return QtCore.Property(
        bool,
        fget=get,
        fset=put,
        notify=notify,
    )


@ta.QmlElement
class SearchModel(QtCore.QAbstractListModel):
    """The Search window: query in, grouped results out."""

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1 + i: QtCore.QByteArray(name.encode())
        for i, name in enumerate(ROLE_NAMES)
    }

    textChanged = QtCore.Signal()
    togglesChanged = QtCore.Signal()
    lookInChanged = QtCore.Signal()
    resultsChanged = QtCore.Signal()
    statusChanged = QtCore.Signal()
    recentChanged = QtCore.Signal()
    suggestionsChanged = QtCore.Signal()
    listenChanged = QtCore.Signal()
    detailOpenChanged = QtCore.Signal()
    # The index changed (any thread): carried to the main thread.
    _indexChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None, index: Any = None) -> None:  # noqa: ANN401
        super().__init__(parent)
        self._index: Any = index
        self._text = ""
        self._case = False
        self._word = False
        self._regex = False
        self._look_in = "all"
        self._filters_on: set[str] = set()
        self._suggestions_on = False
        self._detail_open = True
        self._recent: list[str] = []
        self._sort_column = ""
        self._sort_descending = False
        self._folded: set[str] = set()
        # Results: flat list of {role: value} and the matched SearchRows.
        self._rows: list[dict] = []
        self._matched: list[tuple[Any, Any]] = []
        self._counts: dict[str, int] = {}
        self._profile_count = 0
        self._result_count = 0
        self._did_you_mean = ""
        self._hints: list[dict] = []
        self._nothing_text = ""
        self._suggestions: list[str] = []
        self._status_text = ""
        self._unreadable: list[dict] = []
        self._query_error = ""
        # Listen.
        self._listening = False
        self._heard = ""
        self._listen_error = ""
        self._listener: Any = None
        self._osc_hooked = False
        self._closed = False
        self._load_state()

        self._debounce = self._timer(DEBOUNCE_MS, self._run)
        self._recent_timer = self._timer(RECENT_MS, self._add_recent)
        self._rebuild_timer = self._timer(REBUILD_MS, self._rebuild_open)
        self._indexChanged.connect(
            self._on_index_changed, QtCore.Qt.ConnectionType.QueuedConnection
        )
        for notice in self._notices():
            notice.connect(self._rebuild_soon)
        self._hook_index()
        self._run()

    def _timer(self, ms: int, slot: Callable[[], None]) -> QtCore.QTimer:
        timer = QtCore.QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(ms)
        timer.timeout.connect(slot)
        return timer

    # Index.

    def search_index(self) -> Any:  # noqa: ANN401
        """The search index (the program's one, unless given)."""
        if self._index is None:
            self._index = _default_index()
        return self._index

    def _hook_index(self) -> None:
        """Follow the index's changes (it builds itself on first use)."""
        try:
            index = self.search_index()
            index.set_on_change(self._index_changed_any_thread)
        except Exception:  # noqa: BLE001 - no index: Search shows nothing
            log.exception("Search: the index could not start")

    def _index_changed_any_thread(self, *_: object) -> None:
        try:
            self._indexChanged.emit()
        except RuntimeError:  # the model is gone
            pass

    @QtCore.Slot()
    def _on_index_changed(self) -> None:
        from gremlin import search_query

        search_query.clear_cache()
        self._run()

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
            log.exception("Search: the open profile could not be indexed again")

    def close(self) -> None:
        """Stop listening to notices, the index and Listen (window closed,
        tests)."""
        if self._closed:
            return
        self._closed = True
        self.stopListen()
        for notice in self._notices():
            try:
                notice.disconnect(self._rebuild_soon)
            except (RuntimeError, TypeError):
                pass
        if self._index is not None:
            self._index.set_on_change(None)
        for timer in (self._debounce, self._recent_timer, self._rebuild_timer):
            timer.stop()

    # Remembered state.

    def _load_state(self) -> None:
        state = _settings_load()
        self._text = str(state.get("text", "") or "")
        self._case = bool(state.get("matchCase", False))
        self._word = bool(state.get("wholeWord", False))
        self._regex = bool(state.get("regex", False))
        look_in = str(state.get("lookIn", "all"))
        self._look_in = look_in if look_in in LOOK_IN else "all"
        known = set(KIND_FILTERS) | set(HEALTH_FILTERS)
        self._filters_on = {str(n) for n in state.get("filters", []) if n in known}
        self._suggestions_on = bool(state.get("suggestionsOn", False))
        self._detail_open = bool(state.get("detailOpen", True))
        self._recent = [str(t) for t in state.get("recent", []) if t][:RECENT_MAX]

    def _save_state(self) -> None:
        _settings_save(
            {
                "text": self._text,
                "matchCase": self._case,
                "wholeWord": self._word,
                "regex": self._regex,
                "lookIn": self._look_in,
                "filters": sorted(self._filters_on),
                "suggestionsOn": self._suggestions_on,
                "detailOpen": self._detail_open,
                "recent": list(self._recent),
            }
        )

    # Query properties.

    def _get_text(self) -> str:
        return self._text

    def _set_text(self, value: str) -> None:
        value = str(value or "")
        if value == self._text:
            return
        self._text = value
        self.textChanged.emit()
        self._update_suggestions()
        self._debounce.start()
        self._recent_timer.start()

    text = QtCore.Property(str, fget=_get_text, fset=_set_text, notify=textChanged)

    matchCase = _toggle("_case", togglesChanged)
    wholeWord = _toggle("_word", togglesChanged)
    regex = _toggle("_regex", togglesChanged)

    def _get_suggestions_on(self) -> bool:
        return self._suggestions_on

    def _set_suggestions_on(self, value: bool) -> None:
        if bool(value) != self._suggestions_on:
            self._suggestions_on = bool(value)
            self.togglesChanged.emit()
            self._update_suggestions()
            self._save_state()

    suggestionsOn = QtCore.Property(
        bool,
        fget=_get_suggestions_on,
        fset=_set_suggestions_on,
        notify=togglesChanged,
    )

    def _get_look_in(self) -> str:
        return self._look_in

    def _set_look_in(self, value: str) -> None:
        value = str(value)
        if value in LOOK_IN and value != self._look_in:
            self._look_in = value
            self.lookInChanged.emit()
            self._changed()

    lookIn = QtCore.Property(
        str, fget=_get_look_in, fset=_set_look_in, notify=lookInChanged
    )

    def _get_detail_open(self) -> bool:
        return self._detail_open

    def _set_detail_open(self, value: bool) -> None:
        if bool(value) != self._detail_open:
            self._detail_open = bool(value)
            self.detailOpenChanged.emit()
            self._save_state()

    detailOpen = QtCore.Property(
        bool, fget=_get_detail_open, fset=_set_detail_open, notify=detailOpenChanged
    )

    def _changed(self) -> None:
        """A toggle, scope or filter changed: search now and remember it."""
        self._debounce.stop()
        self._run()
        self._save_state()

    @QtCore.Property(list, notify=resultsChanged)
    def filters(self) -> list:
        """[{name, label, group "show"|"health", on, count}]."""
        rows = [
            {
                "name": name,
                "label": label,
                "group": "show",
                "on": name in self._filters_on,
                "count": self._counts.get(name, 0),
            }
            for name, label in KIND_FILTERS.items()
        ]
        rows.extend(
            {
                "name": name,
                "label": label,
                "group": "health",
                "on": name in self._filters_on,
                "count": self._counts.get(name, 0),
            }
            for name, (label, _) in HEALTH_FILTERS.items()
        )
        return rows

    @QtCore.Slot(str, bool)
    def setFilter(self, name: str, on: bool) -> None:  # noqa: N802
        if name not in KIND_FILTERS and name not in HEALTH_FILTERS:
            return
        if on == (name in self._filters_on):
            return
        if on:
            self._filters_on.add(name)
        else:
            self._filters_on.discard(name)
        self._changed()

    @QtCore.Slot()
    def clearFilters(self) -> None:  # noqa: N802
        if self._filters_on:
            self._filters_on.clear()
            self._changed()

    # Results and status.

    @QtCore.Property(int, notify=resultsChanged)
    def resultCount(self) -> int:  # noqa: N802
        return self._result_count

    @QtCore.Property(int, notify=resultsChanged)
    def profileCount(self) -> int:  # noqa: N802
        return self._profile_count

    @QtCore.Property(str, notify=resultsChanged)
    def didYouMean(self) -> str:  # noqa: N802
        return self._did_you_mean

    @QtCore.Property(list, notify=resultsChanged)
    def nothingFoundHints(self) -> list:  # noqa: N802
        """[{text, action}]; applyHint(action) does it."""
        return list(self._hints)

    @QtCore.Property(str, notify=resultsChanged)
    def nothingFoundText(self) -> str:  # noqa: N802
        """What was looked for and where, when nothing is found ("" else)."""
        return self._nothing_text

    @QtCore.Property(str, notify=resultsChanged)
    def queryError(self) -> str:  # noqa: N802
        """Why the text is no search (a bad regular expression), else ""."""
        return self._query_error

    @QtCore.Property(str, notify=statusChanged)
    def statusText(self) -> str:  # noqa: N802
        return self._status_text

    @QtCore.Property(list, notify=statusChanged)
    def unreadable(self) -> list:
        """[{path, reason}] of profiles the index couldn't read."""
        return list(self._unreadable)

    @QtCore.Property(list, notify=recentChanged)
    def recent(self) -> list:
        return list(self._recent)

    @QtCore.Property(list, notify=suggestionsChanged)
    def suggestions(self) -> list:
        return list(self._suggestions)

    # The search.

    def _all_rows(self) -> list:
        try:
            return list(self.search_index().rows())
        except Exception:  # noqa: BLE001 - no index yet
            log.debug("Search: no rows", exc_info=True)
            return []

    def _in_scope(self, rows: list) -> list:
        if self._look_in == "this":
            return [r for r in rows if r.source == "open"]
        if self._look_in == "library":
            return [r for r in rows if r.source == "library"]
        # The open profile stands for its file (its unsaved changes count).
        open_paths = {r.source_path for r in rows if r.source == "open"}
        return [
            r
            for r in rows
            if not (r.source == "profile" and r.source_path in open_paths)
        ]

    def _passes(self, row: Any) -> bool:  # noqa: ANN401
        kinds = {n for n in self._filters_on if n in KIND_FILTERS}
        health = {n for n in self._filters_on if n in HEALTH_FILTERS}
        if kinds and not kinds & set(row.kinds):
            return False
        return not health or any(HEALTH_FILTERS[n][1](row) for n in health)

    @QtCore.Slot()
    def search(self) -> None:
        """Search now (no debounce)."""
        self._debounce.stop()
        self._run()

    @QtCore.Slot()
    def _run(self) -> None:
        from gremlin import search_query

        rows = self._in_scope(self._all_rows())
        text = self._text.strip()
        matched: list[tuple[Any, Any]] = []
        self._query_error = ""
        if text:
            try:
                query = search_query.parse(text, self._case, self._word, self._regex)
            except Exception as err:  # noqa: BLE001 - a bad regular expression
                query = None
                self._query_error = str(err)
            if query is not None:
                for row in rows:
                    found = search_query.match(row, query)
                    if found is not None:
                        matched.append((row, found))
        elif self._filters_on:
            matched = [(row, None) for row in rows]
        counts: dict[str, int] = {}
        for row, _ in matched:
            for name in KIND_FILTERS:
                if name in row.kinds:
                    counts[name] = counts.get(name, 0) + 1
            for name, (_, test) in HEALTH_FILTERS.items():
                if test(row):
                    counts[name] = counts.get(name, 0) + 1
        self._counts = counts
        self._matched = [(row, m) for row, m in matched if self._passes(row)]
        self._result_count = len(self._matched)
        self._profile_count = len({(r.source, r.source_path) for r, _ in self._matched})
        self._nothing_found(text, rows)
        self._update_status()
        self._layout()

    def _vocabulary(self, rows: Iterable[Any] | None = None) -> list[str]:
        words: set[str] = set()
        for row in self._all_rows() if rows is None else rows:
            for value in (
                row.custom_name,
                row.input_label,
                row.action_name,
                row.device_name,
                row.mode,
                row.source_name,
                *row.targets,
            ):
                if value:
                    words.add(str(value))
        return sorted(words, key=str.casefold)

    def _nothing_found(self, text: str, rows: list) -> None:
        self._did_you_mean = ""
        self._hints = []
        self._nothing_text = ""
        if not text or self._matched:
            return
        from gremlin import search_query

        where = LOOK_IN_LABELS[self._look_in]
        self._nothing_text = f"Nothing found for '{text}' in {where}."
        if not self._regex:
            try:
                self._did_you_mean = (
                    search_query.did_you_mean(text, self._vocabulary(rows)) or ""
                )
            except Exception:  # noqa: BLE001 - no suggestion
                self._did_you_mean = ""
        hints = []
        if self._did_you_mean:
            hints.append(
                {
                    "text": f"Did you mean {self._did_you_mean}?",
                    "action": "text:" + self._did_you_mean,
                }
            )
        if self._look_in != "all":
            hints.append({"text": "Search all profiles", "action": "lookIn:all"})
        if self._filters_on:
            hints.append({"text": "Clear filters", "action": "filters:clear"})
        for field, label in (
            ("_case", "Match case"),
            ("_word", "Whole word"),
            ("_regex", "Regular expression"),
        ):
            if getattr(self, field):
                hints.append({"text": f"Turn off {label}", "action": f"off:{field}"})
        self._hints = hints

    @QtCore.Slot(str)
    def applyHint(self, action: str) -> None:  # noqa: N802
        """Do a nothing-found hint's action."""
        kind, _, value = str(action).partition(":")
        if kind == "text":
            self.searchFor(value)
        elif kind == "lookIn":
            self._set_look_in(value)
        elif kind == "filters":
            self.clearFilters()
        elif kind == "off" and value in ("_case", "_word", "_regex"):
            setattr(self, value, False)
            self.togglesChanged.emit()
            self._changed()

    def _update_status(self) -> None:
        try:
            status = dict(self.search_index().status())
        except Exception:  # noqa: BLE001 - no index yet
            status = {"state": "building", "done": 0, "total": 0, "unreadable": []}
        done, total = int(status.get("done", 0)), int(status.get("total", 0))
        bad = [
            {"path": str(path), "reason": str(reason)}
            for path, reason in status.get("unreadable", [])
        ]
        if status.get("state") == "building":
            text = f"Indexing {done} of {total} profiles…"
        else:
            uses, profiles = self._result_count, self._profile_count
            text = (
                f"{uses} {'use' if uses == 1 else 'uses'} in {profiles} "
                f"{'profile' if profiles == 1 else 'profiles'}"
            )
        if bad:
            text += (
                f" · {len(bad)} could not be read"
                if len(bad) != 1
                else " · 1 could not be read"
            )
        if text != self._status_text or bad != self._unreadable:
            self._status_text = text
            self._unreadable = bad
            self.statusChanged.emit()

    # Layout: profile → device → results.

    def _sort_key(self) -> Callable[[tuple[Any, Any]], Any]:
        column = SORT_COLUMNS.get(self._sort_column)
        if column is None:
            return lambda pair: -float(getattr(pair[1], "score", 0) or 0)
        return lambda pair: column(pair[0])

    def _layout(self) -> None:
        source_order = {"open": 0, "profile": 1, "library": 2}
        groups: dict[tuple, dict[tuple, list]] = {}
        names: dict[tuple, Any] = {}
        for pair in self._matched:
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
                source_order.get(k[0], 3),
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
                pairs = sorted(devices[device_key], key=self._sort_key())
                if self._sort_descending and self._sort_column:
                    pairs.reverse()
                flat.append(self._header("device", device_key[1], dkey, 1, len(pairs)))
                if dkey in self._folded:
                    continue
                flat.extend(self._result(row, m, dkey) for row, m in pairs)
        self.beginResetModel()
        self._rows = flat
        self.endResetModel()
        self.resultsChanged.emit()

    def _header(self, kind: str, title: str, key: str, depth: int, count: int) -> dict:
        return {
            "rowKind": kind,
            "title": str(title),
            "count": count,
            "folded": key in self._folded,
            "groupKey": key,
            "depth": depth,
        }

    def _result(self, row: Any, match: Any, key: str) -> dict:  # noqa: ANN401
        item = {
            "rowKind": "result",
            "title": str(row.custom_name or row.input_label),
            "count": 0,
            "folded": False,
            "groupKey": key,
            "depth": 2,
            "highlights": _spans(match) if match is not None else {},
            "tags": _tags(row),
            "notPlugged": "notPlugged" in _tags(row),
            "score": float(getattr(match, "score", 0) or 0),
            "_row": row,
        }
        for field, name in ROW_FIELDS:
            item[name] = _qml(getattr(row, field, _FIELD_DEFAULTS.get(field)))
        return item

    @QtCore.Slot(str, "QVariant")
    def setSort(self, column: str, order: object) -> None:  # noqa: N802
        """Sort results in each device by "input", "mode" or "action"
        ("" = best match first); order Qt.DescendingOrder (1) or "desc"."""
        self._sort_column = str(column) if column in SORT_COLUMNS else ""
        self._sort_descending = order in (1, "desc", "descending") or (
            order == QtCore.Qt.SortOrder.DescendingOrder
        )
        self._layout()

    @QtCore.Slot(int)
    def toggleFold(self, row: int) -> None:  # noqa: N802
        if not 0 <= row < len(self._rows):
            return
        item = self._rows[row]
        if item["rowKind"] == "result":
            return
        self._folded ^= {item["groupKey"]}
        self._layout()

    @QtCore.Slot(bool)
    def foldAll(self, folded: bool) -> None:  # noqa: N802
        if folded:
            self._folded = {f"{r.source}|{r.source_path}" for r, _ in self._matched}
        else:
            self._folded = set()
        self._layout()

    # Rows for QML.

    def _plain(self, row: int) -> dict:
        if not 0 <= row < len(self._rows):
            return {}
        return {k: v for k, v in self._rows[row].items() if not k.startswith("_")}

    @QtCore.Slot(int, result="QVariantMap")
    def get(self, row: int) -> dict:
        """One row's roles as a map (to go to it)."""
        return self._plain(row)

    def _mode_chain(self, row: Any) -> list[str]:  # noqa: ANN401
        """The row's mode and the modes it inherits from (open profile only)."""
        chain = [str(row.mode)]
        if row.source != "open":
            return chain
        from gremlin import shared_state

        modes = getattr(shared_state.current_profile, "modes", None)
        if modes is None:
            return chain
        try:
            node = modes.find_mode(chain[0]).parent
        except Exception:  # noqa: BLE001 - no such mode
            return chain
        # The hidden root has no parent and is not a mode.
        while node is not None and node.parent is not None:
            chain.append(str(node.value))
            node = node.parent
        return chain

    @QtCore.Slot(int, result="QVariantMap")
    def detail(self, row: int) -> dict:
        """The detail pane: the row's fields, its binding text, mode chain
        and the other inputs sending to the same output (Used twice)."""
        if not 0 <= row < len(self._rows) or "_row" not in self._rows[row]:
            return {}
        found = self._rows[row]["_row"]
        partners = []
        if found.used_twice:
            mine = set(found.target_keys)
            for other in self._all_rows():
                if (
                    other.source == found.source
                    and other.source_path == found.source_path
                    and other.mode == found.mode
                    and (other.device_guid, other.input_id)
                    != (found.device_guid, found.input_id)
                    and mine & set(other.target_keys)
                ):
                    name = other.custom_name or other.input_label
                    partners.append(f"{other.device_name} · {name}")
        info = self._plain(row)
        info["bindingText"] = "\n".join(
            [str(found.text), *(f"→ {t}" for t in found.targets)]
        )
        info["modeChain"] = self._mode_chain(found)
        info["clashPartners"] = sorted(set(partners), key=str.casefold)
        info["notes"] = [str(n) for n in getattr(found, "notes", ()) or ()]
        info["inheritedFrom"] = str(getattr(found, "inherited_from", "") or "")
        return info

    @QtCore.Slot(int, result=str)
    def copyText(self, row: int) -> str:  # noqa: N802
        """A result as one line of text, also put on the clipboard."""
        if not 0 <= row < len(self._rows) or "_row" not in self._rows[row]:
            return ""
        found = self._rows[row]["_row"]
        name = found.input_label
        if found.custom_name:
            name = f"{found.custom_name} ({found.input_label})"
        mode = str(found.mode or "")
        parent = getattr(found, "inherited_from", "")
        if parent:
            mode = f"{mode} (Inherited from {parent})"
        line = " › ".join(
            str(part)
            for part in (found.source_name, found.device_name, mode, name)
            if part
        )
        if found.text:
            line += f": {found.text}"
        if found.targets:
            line += " → " + ", ".join(found.targets)
        notes = [str(n) for n in getattr(found, "notes", ()) or () if n]
        if notes:
            line += " · Notes: " + "; ".join(notes)
        _set_clipboard(line)
        return line

    @QtCore.Property(list, constant=True)
    def prefixes(self) -> list:
        """[{name, description}] of the prefixes (the ? popup)."""
        from gremlin import search_query

        return [
            {"name": name, "description": description}
            for name, (_, description) in search_query.PREFIXES.items()
        ]

    @QtCore.Slot(int)
    def searchForTarget(self, row: int) -> None:  # noqa: N802
        """Search for every use of the row's first target."""
        if not 0 <= row < len(self._rows) or "_row" not in self._rows[row]:
            return
        text = target_text(self._rows[row]["_row"])
        if text:
            self.searchFor(text)

    @QtCore.Slot(str)
    def searchFor(self, text: str) -> None:  # noqa: N802
        """Fill the box and search now (Find uses…, Listen, a hint, Recent)."""
        text = str(text or "")
        if text != self._text:
            self._text = text
            self.textChanged.emit()
        self._update_suggestions()
        self.search()
        self._add_recent()

    # Recent and suggestions.

    @QtCore.Slot()
    def _add_recent(self) -> None:
        self._recent_timer.stop()
        text = self._text.strip()
        if not text:
            self._save_state()
            return
        recent = [t for t in self._recent if t != text]
        # Typing on from the last search replaces it.
        if recent and text.startswith(recent[0]):
            recent.pop(0)
        self._recent = [text, *recent][:RECENT_MAX]
        self.recentChanged.emit()
        self._save_state()

    @QtCore.Slot()
    def clearRecent(self) -> None:  # noqa: N802
        self._recent = []
        self.recentChanged.emit()
        self._save_state()

    def _update_suggestions(self) -> None:
        found: list[str] = []
        if self._suggestions_on and self._text.strip():
            from gremlin import search_query

            try:
                found = list(
                    search_query.suggestions(
                        self._text, self._vocabulary(), list(self._recent)
                    )
                )
            except Exception:  # noqa: BLE001 - no suggestions
                found = []
        if found != self._suggestions:
            self._suggestions = found
            self.suggestionsChanged.emit()

    # Listen.

    @QtCore.Property(bool, notify=listenChanged)
    def listening(self) -> bool:
        return self._listening

    @QtCore.Property(str, notify=listenChanged)
    def heardText(self) -> str:  # noqa: N802
        """ "Heard: …" after a Listen caught something."""
        return self._heard

    @QtCore.Property(str, notify=listenChanged)
    def listenError(self) -> str:  # noqa: N802
        """Why OSC is not heard (listening is off), else ""."""
        return self._listen_error

    def _make_listener(self) -> Any:  # noqa: ANN401
        from gremlin.ui.util import InputListenerModel

        listener = InputListenerModel(self)
        listener.setProperty("eventTypes", ["axis", "button", "hat", "key"])
        listener.setProperty("multipleInputs", False)
        return listener

    @staticmethod
    def _osc_runtime() -> Any:  # noqa: ANN401
        from gremlin import osc

        return osc.OscRuntime()

    @QtCore.Slot()
    def listen(self) -> None:
        """Wait for a stick control, a key or an OSC message; the first one
        fills the box."""
        if self._listening:
            return
        self._listening = True
        self._heard = ""
        self._listen_error = ""
        if self._listener is None:
            self._listener = self._make_listener()
            self._listener.listeningTerminated.connect(self._on_listened)
        self._listener.enabled = True
        try:
            runtime = self._osc_runtime()
            on = runtime.listenInfo().get("state") == "listening"
        except Exception:  # noqa: BLE001 - no OSC runtime
            runtime, on = None, False
        if on and runtime is not None:
            runtime.incoming.connect(self._on_osc)
            self._osc_hooked = True
        else:
            self._listen_error = "OSC is not listening (Listen for OSC messages is off)"
        self.listenChanged.emit()

    @QtCore.Slot()
    def stopListen(self) -> None:  # noqa: N802
        if not self._listening:
            return
        self._listening = False
        if self._listener is not None:
            self._listener.enabled = False
        if self._osc_hooked:
            self._osc_hooked = False
            try:
                self._osc_runtime().incoming.disconnect(self._on_osc)
            except (RuntimeError, TypeError):
                pass
        self.listenChanged.emit()

    def _heard_it(self, heard: str, text: str) -> None:
        self.stopListen()
        self._heard = f"Heard: {heard}"
        self.listenChanged.emit()
        self.searchFor(text)

    @QtCore.Slot(list)
    def _on_listened(self, inputs: list) -> None:
        if not self._listening:
            return
        if not inputs:  # Esc held: cancelled
            self.stopListen()
            return
        heard, text = heard_text(inputs[0])
        self._heard_it(heard, text)

    def _on_osc(self, address: str, _args: object = None, _peer: object = None) -> None:
        if self._listening and address:
            self._heard_it(f"OSC {address}", f"osc:{_quoted(address)}")

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
