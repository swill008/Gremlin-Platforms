# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""Health (01 S197, D-01-HEALTH): the one owner of the four checks and the
only copy of their results. The search index keeps plain facts (each row's
declared references); this module says which rows have a problem, why, and
what can be done. Only the Health window and its toolbar button read it.

Results are worked out on first read after the index changes and kept until
the next change (or invalidate(), e.g. when a device is plugged in); reads
are thread-safe. A new check is a line in CHECKS, LABELS, FIXES and _RULES;
test_health.py fails when one is missing."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING

from gremlin import references as refs
from gremlin.modules import ids

if TYPE_CHECKING:
    from gremlin.search_index import SearchIndex, SearchRow

syslog = logging.getLogger("system")

# The checks, in the order they are shown.
CHECKS: tuple[str, ...] = ("notFound", "usedTwice", "noBindings", "notPlugged")
LABELS: dict[str, str] = {
    "notFound": "Binding output not found",
    "usedTwice": "Used twice",
    "noBindings": "No bindings",
    "notPlugged": "Not plugged in",
}
# What you can do, per check (the Why panel; Help style guide wording).
FIXES: dict[str, str] = {
    "notFound": (
        "Change the target to a vJoy you have, remove the binding, or set up "
        "the vJoy in Tools › Drivers."
    ),
    "usedTwice": (
        "Change the target of one of the bindings, or remove the one you "
        "don't need. Two inputs sending to one output fight over it."
    ),
    "noBindings": "Add an action to this input, or leave it if you don't need it.",
    "notPlugged": (
        "Plug the device in, or move its bindings to a device you have. The "
        "bindings stay in the profile and work again when it is plugged in."
    ),
}

RowKey = tuple


@dataclass(frozen=True)
class Finding:
    """One problem on one row: the check, the reason and what can be done."""

    check: str
    why: str
    fix: str


Results = Mapping[RowKey, tuple[Finding, ...]]


def row_key(row: SearchRow) -> RowKey:
    """A row's stable key: where it is (source, file, setup), which input
    in which mode, and which action of which binding."""
    return (
        row.source,
        refs.path_key(row.source_path) if row.source_path else "",
        row.source_name,
        ids.guid_key(row.device_guid),
        row.mode,
        row.input_type,
        refs.id_key(row.input_id),
        row.binding_index,
        tuple(row.path),
        row.inherited_from,
    )


def _input_key(row: SearchRow) -> tuple:
    return (ids.guid_key(row.device_guid), row.input_type, refs.id_key(row.input_id))


def _plugged(guid: str, name: str) -> bool:
    """Whether a device is there now (the device list, 03 S90a)."""
    from gremlin.modules import hardware

    return hardware.plugged_in(guid, name)


# --- the four rules ------------------------------------------------------------


def _not_found(rows: list[SearchRow]) -> dict[int, str]:
    """A reference the action declared as not there (references.py)."""
    found: dict[int, str] = {}
    for i, row in enumerate(rows):
        gone = [r for r in row.references if r.missing]
        if gone:
            found[i] = next((r.why for r in gone if r.why), "") or (
                "The output this binding sends to isn't there."
            )
    return found


def _used_twice(rows: list[SearchRow]) -> dict[int, str]:
    """The same output in the same mode of the same source sent by 2+
    different inputs."""
    inputs: dict[tuple, set[tuple]] = {}
    sends: list[tuple[int, tuple]] = []
    for i, row in enumerate(rows):
        for ref in row.references:
            if ref.role == "sends-output":
                key = (row.source, row.source_path, row.mode, ref.target)
                inputs.setdefault(key, set()).add(_input_key(row))
                sends.append((i, key))
    found: dict[int, str] = {}
    for i, key in sends:
        count = len(inputs[key])
        if count > 1 and i not in found:
            row = rows[i]
            shown = next(
                (t for r, t in zip(row.target_keys, row.targets) if r == key[3]),
                "this output",
            )
            found[i] = (
                f"{count} inputs send to {shown} in the {row.mode or 'Default'} mode."
            )
    return found


def _no_bindings(rows: list[SearchRow]) -> dict[int, str]:
    """An input with no action."""
    return {
        i: "This input has no action."
        for i, row in enumerate(rows)
        if not row.action_tag
    }


def _not_plugged(rows: list[SearchRow]) -> dict[int, str]:
    """A profile's device that isn't in the device list now (a Device
    Library setup never: it isn't tied to a plugged-in device)."""
    known: dict[tuple, bool] = {}
    found: dict[int, str] = {}
    for i, row in enumerate(rows):
        if row.source == "library":
            continue
        key = (ids.guid_key(row.device_guid), row.device_name)
        if key not in known:
            try:
                known[key] = bool(_plugged(row.device_guid, row.device_name))
            except Exception:  # noqa: BLE001 - no device list: not plugged in
                known[key] = False
        if not known[key]:
            found[i] = f"{row.device_name or 'This device'} isn't plugged in."
    return found


_RULES: dict[str, Callable[[list[SearchRow]], dict[int, str]]] = {
    "notFound": _not_found,
    "usedTwice": _used_twice,
    "noBindings": _no_bindings,
    "notPlugged": _not_plugged,
}


def compute(rows: Iterable[SearchRow]) -> Results:
    """The four rules over rows (no cache): row key -> its findings, in
    CHECKS order; rows with none are left out."""
    rows = list(rows)
    per_row: dict[int, list[Finding]] = {}
    for check in CHECKS:
        try:
            hits = _RULES[check](rows)
        except Exception:  # noqa: BLE001 - one rule's error hides no other
            syslog.exception(f"Health: the {check} check failed")
            continue
        for i, why in hits.items():
            per_row.setdefault(i, []).append(Finding(check, why, FIXES[check]))
    return MappingProxyType(
        {row_key(rows[i]): tuple(found) for i, found in sorted(per_row.items())}
    )


# --- the one cached copy -------------------------------------------------------

_lock = threading.Lock()
_index: SearchIndex | None = None
_cached_rows: tuple | None = None
_cached: Results = MappingProxyType({})
_listeners: list[Callable[[], None]] = []


def attach(index: SearchIndex | None) -> None:
    """Reads results from this index (default: the program's one index,
    attached on first read) and recomputes when it changes."""
    global _index
    with _lock:
        old = _index
        _index = index
        _drop()
    if old is not None and old is not index:
        old.remove_listener(_index_changed)
    if index is not None and old is not index:
        index.add_listener(_index_changed)


def _current_index() -> SearchIndex:
    if _index is None:
        from gremlin import search_index

        attach(search_index.default_index())
    assert _index is not None
    return _index


def _drop() -> None:
    global _cached_rows, _cached
    _cached_rows = None
    _cached = MappingProxyType({})


def _index_changed() -> None:
    invalidate()


def invalidate() -> None:
    """Forgets the results (the device list changed, or anything else the
    rules read) and tells the listeners; the next read works them out."""
    with _lock:
        _drop()
    _notify()


def on_changed(callback: Callable[[], None]) -> None:
    """callback() when the results may have changed; it may run on a
    program thread, so a Qt caller queues it to the main thread."""
    with _lock:
        if callback not in _listeners:
            _listeners.append(callback)


def remove_listener(callback: Callable[[], None]) -> None:
    with _lock:
        if callback in _listeners:
            _listeners.remove(callback)


def _notify() -> None:
    with _lock:
        listeners = list(_listeners)
    for callback in listeners:
        try:
            callback()
        except Exception:  # noqa: BLE001 - a listener's error stays its own
            syslog.exception("Health: change listener failed")


def watch_devices() -> None:
    """Recomputes when a device is plugged in or out (call once, on the
    main thread, from the first Health reader)."""
    from gremlin import event_handler

    event_handler.EventListener().device_change_event.connect(invalidate)


def results(rows: Iterable[SearchRow] | None = None) -> Results:
    """Row key -> findings for every row of the index (cached until it
    changes); with rows, for those rows only (not cached)."""
    global _cached_rows, _cached
    if rows is not None:
        return compute(rows)
    snapshot = _current_index().rows()
    with _lock:
        if _cached_rows is snapshot:
            return _cached
    worked = compute(snapshot)
    with _lock:
        _cached_rows = snapshot
        _cached = worked
    return worked


def findings(row: SearchRow) -> tuple[Finding, ...]:
    """A row's findings, in CHECKS order (none: ())."""
    return results().get(row_key(row), ())


def counts(scope_rows: Iterable[SearchRow] | None = None) -> dict[str, int]:
    """Rows with each check among scope_rows (default: every row)."""
    found = results()
    rows = _current_index().rows() if scope_rows is None else scope_rows
    total: dict[str, int] = dict.fromkeys(CHECKS, 0)
    for row in rows:
        for finding in found.get(row_key(row), ()):
            total[finding.check] += 1
    return total


def broken_count() -> int:
    """Bindings in the open profile whose output isn't found (the toolbar's
    Health number)."""
    return counts(r for r in _current_index().rows() if r.source == "open")["notFound"]


def _reset_for_tests() -> None:
    """Detaches the index and the listeners."""
    attach(None)
    with _lock:
        _listeners.clear()


__all__ = [
    "CHECKS",
    "FIXES",
    "LABELS",
    "Finding",
    "attach",
    "broken_count",
    "compute",
    "counts",
    "findings",
    "invalidate",
    "on_changed",
    "remove_listener",
    "results",
    "row_key",
    "watch_devices",
]
