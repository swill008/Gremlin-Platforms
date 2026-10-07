# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""test/run_tests.py splits test/unit by the times it knows: its own last
run's, else the CI times kept in test/test_times.json."""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

import pytest

_ROOT = pathlib.Path(__file__).parents[2]


def _module(name: str, path: pathlib.Path):  # noqa: ANN202
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def run_tests(tmp_path, monkeypatch):  # noqa: ANN001, ANN201
    module = _module("run_tests_under_test", _ROOT / "test" / "run_tests.py")
    monkeypatch.setattr(module, "_STATE", tmp_path / "state")
    monkeypatch.setattr(module, "_SEED_TIMES", tmp_path / "test_times.json")
    # No pytest --collect-only: a file's tests are made up here.
    monkeypatch.setattr(module, "_tests_in", lambda f: [f"{f}::a", f"{f}::b"])
    return module


def test_parts_end_near_the_same_time(run_tests) -> None:  # noqa: ANN001
    times = {"a": 9.0, "b": 5.0, "c": 4.0, "d": 3.0, "e": 3.0, "f": 2.0}
    split = run_tests._split(list(times), 3, times)
    loads = sorted(sum(times[f] for f in part) for part in split)
    assert loads == [8.0, 9.0, 9.0]


def test_the_seed_times_are_used_when_this_pc_has_none(run_tests) -> None:  # noqa: ANN001
    run_tests._SEED_TIMES.write_text(
        json.dumps({"test/unit/test_x.py": 50.0, "test/unit/test_y.py": 1.0}),
        encoding="utf-8",
    )
    assert run_tests._known_times()["test/unit/test_x.py"] == 50.0
    run_tests._save("file-times.json", {"test/unit/test_x.py": 7.0})
    known = run_tests._known_times()
    assert known["test/unit/test_x.py"] == 7.0, "this PC's own time wins"
    assert known["test/unit/test_y.py"] == 1.0


def test_a_heavy_seed_file_is_spread_test_by_test(run_tests) -> None:  # noqa: ANN001
    files = [f"test/unit/test_{n}.py" for n in "abcd"]
    times = dict.fromkeys(files, 1.0) | {"test/unit/test_a.py": 40.0}
    run_tests._SEED_TIMES.write_text(json.dumps(times), encoding="utf-8")
    units, weights = run_tests._units(files, 2, run_tests._known_times())
    assert "test/unit/test_a.py::a" in units and "test/unit/test_a.py" not in units
    assert weights["test/unit/test_a.py::a"] == 20.0


def test_no_seed_file_still_splits(run_tests) -> None:  # noqa: ANN001
    assert run_tests._known_times() == {}
    split = run_tests._split(["x", "y", "z"], 2, {})
    assert sorted(len(part) for part in split) == [1, 2]


def test_the_state_folder_can_be_moved_but_the_one_run_lock_stays(
    tmp_path, monkeypatch  # noqa: ANN001
) -> None:
    monkeypatch.setenv("GREMLIN_TEST_STATE", str(tmp_path / "ci-state"))
    module = _module("run_tests_moved", _ROOT / "test" / "run_tests.py")
    assert module._STATE == tmp_path / "ci-state"
    assert module._RUNNING.parent == module._RUNS != module._STATE


def test_start_up_and_collection_are_no_tests_time(run_tests) -> None:  # noqa: ANN001
    assert run_tests._COLLECTED.match("collecting ... collected 1398 items")
    assert run_tests._COLLECTED.match("collected 1 item")
    assert not run_tests._COLLECTED.match("test/unit/x.py::collected PASSED")


def test_ci_times_come_from_the_gaps_between_results() -> None:
    tool = _module("ci_test_times_under_test", _ROOT / "tools" / "ci_test_times.py")
    prefix = "check\tTests\t2026-10-07T21:15:"
    log = [
        f"{prefix}15.0000000Z [00:00] unit-1 0/?  started: 136 files",
        f"{prefix}28.0000000Z [00:13] unit-1 0/?  collecting ... collected 3 items",
        f"{prefix}30.5000000Z [00:15] unit-1 1/3  test/unit/test_a.py::t PASSED [1/3]",
        f"{prefix}31.0000000Z [00:16] unit-1 2/3  test/unit/test_a.py::u FAILED [2/3]",
        f"{prefix}34.0000000Z [00:19] unit-1 3/3  test/unit/test_b.py::t PASSED [3/3]",
    ]
    assert tool.file_times(log) == {
        "test/unit/test_a.py": 3.0, "test/unit/test_b.py": 3.0,
    }


def test_the_kept_times_cover_the_unit_files() -> None:
    times = json.loads((_ROOT / "test" / "test_times.json").read_text("utf-8"))
    assert all(isinstance(t, (int, float)) and t >= 0 for t in times.values())
    unit = sorted(p.relative_to(_ROOT).as_posix()
                  for p in (_ROOT / "test" / "unit").glob("test_*.py"))
    # New files take 1 s until the times are written again; most must be known.
    assert sum(f in times for f in unit) >= len(unit) * 0.8
