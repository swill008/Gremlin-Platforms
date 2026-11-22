# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""Health (01 S197, D-01-HEALTH): gremlin.health owns the four checks and
the only copy of their results; the search index keeps no health fields."""

from __future__ import annotations

import dataclasses
import sys
import threading
from collections.abc import Iterator

sys.path.append(".")

import pytest

from gremlin import health, search_index
from gremlin.references import Reference
from gremlin.search_index import SearchRow

_GUID = "{4DCB3090-97EC-11EB-8003-444553540000}"
_GONE = "{11111111-2222-3333-4444-555555555555}"


def _row(input_id: int, **kw: object) -> SearchRow:
    target = kw.pop("target", ("vjoy", 1, 3, input_id))
    values: dict = dict(
        source="open",
        source_name="Hornet",
        source_path="C:/p/Hornet.xml",
        device_guid=_GUID,
        device_name="Stick",
        mode="Default",
        input_type=3,
        input_id=input_id,
        input_label=f"Button {input_id}",
        custom_name="",
        action_tag="map-to-vjoy",
        action_name="Map to vJoy",
        text="",
        targets=(f"vJoy 1 Button {target[-1]}",),
        target_keys=(target,),
        role="sends-output",
        binding_index=0,
        path=("Map to vJoy",),
        kinds=frozenset({"action"}),
        references=(Reference("sends-output", target),),
    )
    values.update(kw)
    return SearchRow(**values)


class _Index:
    """A stand-in SearchIndex: rows() and the listeners."""

    def __init__(self, rows: list[SearchRow]) -> None:
        self._rows = tuple(rows)
        self.listeners: list = []

    def rows(self) -> tuple[SearchRow, ...]:
        return self._rows

    def set_rows(self, rows: list[SearchRow]) -> None:
        self._rows = tuple(rows)
        for callback in list(self.listeners):
            callback()

    def add_listener(self, callback: object) -> None:
        self.listeners.append(callback)

    def remove_listener(self, callback: object) -> None:
        self.listeners.remove(callback)


@pytest.fixture(autouse=True)
def _clean(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(health, "_plugged", lambda guid, name: guid != _GONE)
    health._reset_for_tests()
    yield
    health._reset_for_tests()


def _checks(found: object, row: SearchRow) -> list[str]:
    return [f.check for f in found.get(health.row_key(row), ())]  # type: ignore[attr-defined]


def test_tables_cover_every_check() -> None:
    assert set(health.LABELS) == set(health.CHECKS)
    assert set(health.FIXES) == set(health.CHECKS)
    assert set(health._RULES) == set(health.CHECKS)
    assert all(health.FIXES[c] and health.LABELS[c] for c in health.CHECKS)


def test_not_found_takes_the_reference_reason() -> None:
    why = "vJoy 9 isn't set up."
    gone = _row(1, references=(Reference("sends-output", ("vjoy", 9, 3, 1), why=why),))
    flagged = _row(2, references=(Reference("sends-output", ("x",), not_found=True),))
    fine = _row(3)
    found = health.compute([gone, flagged, fine])
    [finding] = found[health.row_key(gone)]
    assert finding == health.Finding("notFound", why, health.FIXES["notFound"])
    assert "Tools › Drivers" in finding.fix
    assert _checks(found, flagged) == ["notFound"]
    assert found[health.row_key(flagged)][0].why
    assert _checks(found, fine) == []


def test_used_twice_same_output_same_mode_same_source() -> None:
    a = _row(1, target=("vjoy", 1, 3, 5))
    b = _row(2, target=("vjoy", 1, 3, 5))
    other_mode = _row(3, target=("vjoy", 1, 3, 5), mode="Taxi")
    other_file = _row(4, target=("vjoy", 1, 3, 5), source_path="C:/p/Viper.xml")
    # The same input twice (two actions of one binding) is not two inputs.
    same_input = [
        _row(6, target=("vjoy", 1, 3, 7)),
        _row(6, target=("vjoy", 1, 3, 7), path=("Other",)),
    ]
    found = health.compute([a, b, other_mode, other_file, *same_input])
    assert _checks(found, a) == _checks(found, b) == ["usedTwice"]
    assert "2 inputs send to vJoy 1 Button 5" in found[health.row_key(a)][0].why
    assert all(_checks(found, r) == [] for r in (other_mode, other_file, *same_input))


def test_no_bindings_and_not_plugged() -> None:
    empty = _row(1, action_tag="", references=())
    unplugged = _row(2, device_guid=_GONE, device_name="Throttle")
    library = _row(3, device_guid=_GONE, source="library")
    found = health.compute([empty, unplugged, library])
    assert _checks(found, empty) == ["noBindings"]
    assert _checks(found, unplugged) == ["notPlugged"]
    assert found[health.row_key(unplugged)][0].why == "Throttle isn't plugged in."
    assert _checks(found, library) == []


def test_findings_are_in_check_order() -> None:
    row = _row(
        1,
        device_guid=_GONE,
        references=(Reference("sends-output", ("vjoy", 9, 3, 1), why="gone"),),
    )
    twin = _row(2, device_guid=_GONE, target=("vjoy", 9, 3, 1))
    found = health.compute([twin, row])
    assert _checks(found, row) == ["notFound", "usedTwice", "notPlugged"]


def test_counts_broken_count_and_findings() -> None:
    gone = Reference("sends-output", ("vjoy", 9, 3, 1), why="gone")
    rows = [
        _row(1, references=(gone,)),
        _row(2, references=(gone,), source="profile"),
        _row(3, action_tag="", references=()),
        _row(4),
    ]
    health.attach(_Index(rows))  # type: ignore[arg-type]
    assert health.counts() == {
        "notFound": 2,
        "usedTwice": 0,
        "noBindings": 1,
        "notPlugged": 0,
    }
    assert health.counts([rows[1]])["notFound"] == 1
    assert health.broken_count() == 1  # the open profile only
    assert [f.check for f in health.findings(rows[0])] == ["notFound"]
    assert health.findings(rows[3]) == ()


def test_results_are_cached_and_recomputed_when_the_index_changes() -> None:
    index = _Index([_row(1)])
    health.attach(index)  # type: ignore[arg-type]
    told: list[int] = []
    health.on_changed(lambda: told.append(1))
    first = health.results()
    assert health.results() is first  # one cached copy
    assert health.broken_count() == 0
    gone = Reference("sends-output", ("vjoy", 9, 3, 1), why="gone")
    index.set_rows([_row(1, references=(gone,))])
    assert told == [1]
    assert health.results() is not first
    assert health.broken_count() == 1
    health.invalidate()
    assert told == [1, 1]


def test_reads_from_threads_get_one_whole_copy() -> None:
    health.attach(_Index([_row(i) for i in range(50)]))  # type: ignore[arg-type]
    seen: list[object] = []
    workers = [
        threading.Thread(target=lambda: seen.append(health.results())) for _ in range(8)
    ]
    for w in workers:
        w.start()
    for w in workers:
        w.join(10.0)
    assert len(seen) == 8
    assert all(len(r) == 0 for r in seen)  # type: ignore[arg-type]


def test_attach_follows_a_real_index(tmp_path: object) -> None:
    from gremlin.profile import Profile

    index = search_index.SearchIndex(folder=tmp_path, library=False)  # type: ignore[arg-type]
    health.attach(index)
    told: list[int] = []
    health.on_changed(lambda: told.append(1))
    index.rebuild_open(Profile())
    assert told
    health.attach(None)
    assert health._index_changed not in index._listeners


def test_search_row_has_no_health_fields() -> None:
    """Guard (S197): the index keeps plain facts; health is gremlin.health's."""
    names = {f.name for f in dataclasses.fields(SearchRow)}
    assert not names & {"not_found", "why", "used_twice", "plugged"}
    for name in ("mark_used_twice", "_mark_used_twice", "_default_plugged"):
        assert not hasattr(search_index, name), name
