# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Gremlin Device Helper jobs mode: arguments, result states, failures."""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from dataclasses import dataclass
from pathlib import Path

import pytest

import gremlin_device_helper as helper


@dataclass
class FakeJob:
    op: str
    driver: str


@dataclass
class FakeResult:
    state: str
    message: str = ""
    restart: bool = False
    used: str = ""


class FakeStore:
    """Stands in for gremlin.drivers and gremlin.driver_jobs (own minimal
    fakes, so the tests don't depend on those files)."""

    def __init__(self, jobs: list[FakeJob] | Exception) -> None:
        self.jobs = jobs
        self.writes: list[tuple[list[str], bool]] = []

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        drivers = types.ModuleType("gremlin.drivers")
        drivers.JobResult = FakeResult  # type: ignore[attr-defined]
        drivers.read_jobs = self._read  # type: ignore[attr-defined]
        drivers.write_results = self._write  # type: ignore[attr-defined]
        driver_jobs = types.ModuleType("gremlin.driver_jobs")

        def blocked(*_a: object, **_k: object) -> None:
            raise AssertionError("the real run_job/runner must not run in a test")

        driver_jobs.run_job = blocked  # type: ignore[attr-defined]
        driver_jobs.real_runner = blocked  # type: ignore[attr-defined]
        driver_jobs.VJoyRun = lambda jobs: None  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "gremlin.drivers", drivers)
        monkeypatch.setitem(sys.modules, "gremlin.driver_jobs", driver_jobs)
        # `from gremlin import drivers` reads the package attribute first.
        import gremlin

        monkeypatch.setattr(gremlin, "drivers", drivers, raising=False)
        monkeypatch.setattr(gremlin, "driver_jobs", driver_jobs, raising=False)

    def _read(self, path: object) -> list[FakeJob]:
        if isinstance(self.jobs, Exception):
            raise self.jobs
        return self.jobs

    def _write(self, path: object, results: list[FakeResult], finished: bool) -> None:
        self.writes.append(([r.state for r in results], finished))


@pytest.fixture(autouse=True)
def _log_in_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(helper, "jobs_log_path", lambda: tmp_path / "helper.log")


# Arguments ---------------------------------------------------------------


def test_parse_pipe_mode() -> None:
    args = helper.parse_args(
        ["--pipe", "p", "--journal", "j", "--key", "k", "--parent", "7"]
    )
    assert args.mode == "pipe" and args.parent == 7


def test_parse_jobs_mode_with_and_without_parent() -> None:
    args = helper.parse_args(["--jobs", "a", "--results", "b"])
    assert args.mode == "jobs" and args.parent is None
    args = helper.parse_args(["--jobs", "a", "--results", "b", "--parent", "3"])
    assert args.mode == "jobs" and args.parent == 3


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["--jobs", "a"],
        ["--results", "b"],
        ["--pipe", "p", "--journal", "j"],
        ["--jobs", "a", "--results", "b", "--pipe", "p"],
        [
            "--pipe",
            "p",
            "--journal",
            "j",
            "--key",
            "k",
            "--parent",
            "1",
            "--jobs",
            "a",
            "--results",
            "b",
        ],
    ],
)
def test_parse_rejects_neither_partial_or_both(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as info:
        helper.parse_args(argv)
    assert info.value.code == 2


# Jobs mode ---------------------------------------------------------------


def test_results_go_waiting_running_done_in_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = FakeStore([FakeJob("install", "vjoy"), FakeJob("install", "hidhide")])
    store.install(monkeypatch)
    seen: list[str] = []

    def run_job(job: FakeJob, runner: object, **_kw: object) -> FakeResult:
        seen.append(job.driver)
        return FakeResult("done", restart=job.driver == "hidhide")

    code = helper.main(
        ["--jobs", "j.json", "--results", "r.json"],
        run_job=run_job,
        job_runner=object(),
    )
    assert code == 0
    assert seen == ["vjoy", "hidhide"]
    assert store.writes == [
        (["waiting", "waiting"], False),
        (["running", "waiting"], False),
        (["done", "waiting"], False),
        (["done", "running"], False),
        (["done", "done"], False),
        (["done", "done"], True),
    ]


def test_a_job_that_raises_fails_and_later_jobs_still_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = FakeStore([FakeJob("install", "vjoy"), FakeJob("install", "hidhide")])
    store.install(monkeypatch)
    final: list[FakeResult] = []

    def write(path: object, results: list[FakeResult], finished: bool) -> None:
        if finished:
            final.extend(results)

    sys.modules["gremlin.drivers"].write_results = write  # type: ignore[attr-defined]

    def run_job(job: FakeJob, runner: object, **_kw: object) -> FakeResult:
        if job.driver == "vjoy":
            raise RuntimeError("boom")
        return FakeResult("done")

    code = helper.main(
        ["--jobs", "j.json", "--results", "r.json"],
        run_job=run_job,
        job_runner=object(),
    )
    assert code == 0
    assert [r.state for r in final] == ["failed", "done"]
    assert "boom" in final[0].message


def test_bad_jobs_file_exits_2_and_writes_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = FakeStore(ValueError("not a job file"))
    store.install(monkeypatch)
    code = helper.main(["--jobs", "j.json", "--results", "r.json"], job_runner=object())
    assert code == 2
    assert store.writes == []


def test_missing_jobs_file_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
    store = FakeStore(FileNotFoundError("gone"))
    store.install(monkeypatch)
    assert helper.main(["--jobs", "j.json", "--results", "r.json"]) == 2


def test_the_real_runner_is_never_called_under_test(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no injected run_job the (blocked) real one is reached; the helper
    turns that into a "failed" job, not a crash, and still finishes."""
    store = FakeStore([FakeJob("install", "vjoy")])
    store.install(monkeypatch)
    assert helper.main(["--jobs", "j.json", "--results", "r.json"]) == 0
    assert store.writes[-1] == (["failed"], True)


def test_pipe_mode_still_dispatches_to_the_pipe_path(tmp_path: Path) -> None:
    key = tmp_path / "key"
    key.write_bytes(b"")
    code = helper.main(
        [
            "--pipe",
            "p",
            "--journal",
            str(tmp_path / "x" / "j.json"),
            "--key",
            str(key),
            "--parent",
            "1",
        ]
    )
    assert code == 2  # empty key file, the pipe mode's own exit


@pytest.mark.skipif(
    importlib.util.find_spec("gremlin.drivers") is None
    or importlib.util.find_spec("gremlin.driver_jobs") is None,
    reason="gremlin.drivers / gremlin.driver_jobs not written yet",
)
def test_round_trip_with_the_real_job_files(tmp_path: Path) -> None:
    from gremlin import drivers

    jobs_file, results_file = tmp_path / "jobs.json", tmp_path / "results.json"
    drivers.write_jobs(jobs_file, [drivers.Job("remove", "hidhide", [], [])])

    def run_job(job: object, runner: object, **_kw: object) -> object:
        return drivers.JobResult(state="done", message="ok")

    code = helper.main(
        ["--jobs", str(jobs_file), "--results", str(results_file)],
        run_job=run_job,
        job_runner=object(),
    )
    results, finished = drivers.read_results(results_file)
    assert code == 0 and finished
    assert [r.state for r in results] == ["done"]
    json.loads(results_file.read_text("utf-8"))


def test_one_vjoy_run_is_shared_by_the_jobs_of_a_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """12 S25b: an update's device check waits for a later vjoy_setup, so the
    run's jobs share one VJoyRun; a new run gets a new one."""
    jobs = [FakeJob("update", "vjoy"), FakeJob("vjoy_setup", "vjoy")]
    store = FakeStore(jobs)
    store.install(monkeypatch)
    import gremlin

    seen: list[object] = []

    class VJoyRun:
        def __init__(self, run_jobs: list[FakeJob]) -> None:
            self.jobs = run_jobs

    def run_job(job: FakeJob, runner: object, **kwargs: object) -> FakeResult:
        seen.append(kwargs["vjoy_run"])
        return FakeResult(state="done")

    gremlin.driver_jobs.VJoyRun = VJoyRun  # type: ignore[attr-defined]
    gremlin.driver_jobs.run_job = run_job  # type: ignore[attr-defined]
    for _ in range(2):
        assert helper.run_jobs(tmp_path / "j", tmp_path / "r", None, object()) == 0
    assert len(seen) == 4 and seen[0] is seen[1] and seen[2] is seen[3]
    assert seen[0] is not seen[2] and seen[0].jobs is jobs  # type: ignore[attr-defined]
