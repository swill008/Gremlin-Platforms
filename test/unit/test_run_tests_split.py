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


# A module fixture is built once in every part a file runs in: a file split
# over 6 parts was booked 6 setups and stayed "heavy" for ever (35 s app
# start-up: test_stage1_button_map 47 s became 252 s).
_FILES = [f"test/unit/test_{n}.py" for n in "abcd"]


def _times_with(run_tests, total: float, setup: float) -> dict[str, float]:  # noqa: ANN001
    run_tests._save("file-times.json", dict.fromkeys(_FILES, 1.0)
                    | {"test/unit/test_a.py": total})
    run_tests._save("file-setup.json", {"test/unit/test_a.py": setup})
    return run_tests._known_times()


def test_a_file_heavy_only_by_its_setup_is_not_split(run_tests) -> None:  # noqa: ANN001
    # 47 s of which 35 s is one fixture: splitting can't share those 35 s.
    times = _times_with(run_tests, 47.0, 35.0)
    units, _ = run_tests._units(_FILES, 2, times, run_tests._known_setup())
    assert "test/unit/test_a.py" in units


def test_a_file_heavy_by_its_tests_is_split(run_tests) -> None:  # noqa: ANN001
    times = _times_with(run_tests, 47.0, 5.0)
    units, _ = run_tests._units(_FILES, 2, times, run_tests._known_setup())
    assert "test/unit/test_a.py::a" in units and "test/unit/test_a.py" not in units


def test_a_split_file_books_its_setup_once(run_tests) -> None:  # noqa: ANN001
    one, two = run_tests.Part("unit-1", "test/unit", []), run_tests.Part(
        "unit-2", "test/unit", [])
    f = "test/unit/test_a.py"
    for part, gaps in ((one, [36.0, 1.0, 1.0]), (two, [36.0, 1.0])):
        for took in gaps:  # the first result of a part carries the setup
            run_tests._book(part, f, took)
    total, setup = run_tests._measured([one, two])
    assert setup[f] == 35.0
    assert total[f] == 40.0, "35 s setup once + 5 tests of 1 s"


def test_only_a_full_run_saves_the_times(run_tests) -> None:  # noqa: ANN001
    import argparse

    def args(**kw: bool) -> argparse.Namespace:
        return argparse.Namespace(**({"failed": False, "changed": False,
                                      "quick": False, "real_vjoy": False} | kw))

    assert run_tests._saves_times(run_tests.FOLDERS, args())
    assert run_tests._saves_times(["test/unit"], args())
    assert not run_tests._saves_times(["test/unit/test_a.py"], args())
    assert not run_tests._saves_times(["test/unit"], args(quick=True))
    assert not run_tests._saves_times(["test/unit/test_a.py"], args(changed=True))
    assert not run_tests._saves_times(["test/unit/test_a.py::t"], args(failed=True))
