# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Runs the tests in parallel, with a clock, so you can watch it.

    python test/run_tests.py                 every test (before a commit)
    python test/run_tests.py --failed        only what failed last time
    python test/run_tests.py --quick PATH... these tests, stop at the first failure
    python test/run_tests.py PATH...         these test files or folders
    python test/run_tests.py --changed       the tests that touch what changed
                                             since the last commit (while working)
    python test/run_tests.py --random-order  any of the above in random order (the
                                             seed is printed; --seed N repeats it)

The folders run at the same time in separate pytest runs (test/unit can't
share a process with the two that need the Gremlin app), and test/unit is
split into parts, balanced by how long each file took last time (chosen
unit files and --failed tests too: a heavy file test by test). Every
line shows the time since the start, which part it is from and how many
tests of all are done. A part that prints nothing for a while says which
test it is in; a part that runs longer than LIMIT_S is stopped. At the end:
each part's result, the total time and the slowest tests. The same output
goes to a log file (its path is shown at the start and end).
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from typing import Any

FOLDERS = ["test/unit", "test/action_interaction", "test/integration", "test/journeys"]
# 8 cores: 6 unit parts and the two other folders. Measured full runs:
# 4 parts 1:10, 5 parts 0:59, 6 parts 0:54 (then action_interaction is the
# longest part).
UNIT_PARTS = 6
LIMIT_S = 600
QUIET_S = 15  # say which test a part is in after this long without output

_ROOT = pathlib.Path(__file__).parents[1]
_STATE = pathlib.Path(tempfile.gettempdir()) / "gremlin-test-runs"
_LOG = pathlib.Path(tempfile.gettempdir()) / "gremlin-test-run.log"
_COUNT = re.compile(r"\[\s*(\d+)/(\d+)\]\s*$")
_RESULT = re.compile(r"^(\S+::\S+) (PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)")
_SUMMARY = re.compile(r"=+ (.* in [\d.]+s.*) =+$")
_SLOW = re.compile(r"^(\d+\.\d+)s (call|setup|teardown)\s+(\S+)")


@dataclass
class Part:
    name: str
    folder: str
    targets: list[str]
    process: subprocess.Popen | None = None
    began: float = 0.0
    done: int = 0
    total: int = 0
    current: str = ""
    last_output: float = 0.0
    last_note: float = 0.0
    summary: str = "no summary (see the log)"
    finished: bool = False
    took: float = 0.0
    failed: list[str] = field(default_factory=list)
    # When the last test result came: the time since then is the next one's.
    last_result: float = 0.0
    file_times: dict[str, float] = field(default_factory=dict)


def _clock(start: float) -> str:
    seconds = int(time.monotonic() - start)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def _load(name: str, default: Any) -> Any:  # noqa: ANN401
    try:
        return json.loads((_STATE / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _save(name: str, value: object) -> None:
    _STATE.mkdir(exist_ok=True)
    (_STATE / name).write_text(json.dumps(value, indent=1), encoding="utf-8")


# One run at a time on this PC: two (from two checkouts or sessions) slow
# each other down several times over, fail tests on timing and spoil the
# times the parts are balanced by. A run that finds another going waits.
_RUNNING = _STATE / "running.json"
_WAIT_S = 900


def _alive(pid: int) -> bool:
    import ctypes

    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(0x1000, False, pid)  # query limited info
    if not handle:
        return False
    try:
        code = ctypes.c_ulong()
        kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        return code.value == 259  # still active
    finally:
        kernel32.CloseHandle(handle)


def _wait_for_other_run() -> None:
    start = time.monotonic()
    said = 0.0
    while True:
        other = _load("running.json", {})
        pid = int(other.get("pid") or 0)
        if not pid or pid == os.getpid() or not _alive(pid):
            break
        waited = time.monotonic() - start
        if waited > _WAIT_S:
            print(f"Still another test run after {_WAIT_S // 60} min: going ahead.")
            break
        if waited - said >= 15 or said == 0.0:
            said = waited or 0.001
            print(f"Waiting for another test run to finish (pid {pid}, "
                  f"{other.get('root', '?')}), {int(waited)} s...", flush=True)
        time.sleep(2)
    _save("running.json", {"pid": os.getpid(), "root": str(_ROOT)})


def _done_running() -> None:
    if int(_load("running.json", {}).get("pid") or 0) == os.getpid():
        try:
            _RUNNING.unlink()
        except OSError:
            pass


def _failed_file() -> str:
    """Each checkout keeps its own list of what failed last."""
    import hashlib

    tag = hashlib.sha1(str(_ROOT).lower().encode()).hexdigest()[:8]
    return f"last-failed-{tag}.json"


def _folder_of(target: str) -> str:
    path = target.replace("\\", "/")
    for folder in FOLDERS:
        if path == folder or path.startswith(folder + "/"):
            return folder
    raise SystemExit(f"Not in a test folder: {target}")


def _split(files: list[str], parts: int, times: dict[str, float]) -> list[list[str]]:
    """Files in parts of about equal time (longest first, each to the
    part with the least so far)."""
    loads = [[0.0, []] for _ in range(parts)]
    for f in sorted(files, key=lambda f: -times.get(f, 1.0)):
        least = min(loads, key=lambda load: load[0])
        least[0] += times.get(f, 1.0)
        least[1].append(f)
    return [sorted(files) for _, files in loads if files]


def _tests_in(test_file: str) -> list[str]:
    """The test ids in test_file (pytest --collect-only)."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q",
         "-p", "no:cacheprovider", test_file],
        cwd=_ROOT, capture_output=True, text=True, timeout=120, check=False,
    )
    return [line for line in result.stdout.splitlines() if "::" in line]


def _units(files: list[str], parts: int, times: dict[str, float]) -> tuple[
    list[str], dict[str, float]
]:
    """What to spread over the parts: files, except that a file heavier than
    half a part's share is spread test by test (one file could otherwise
    keep its part running long after the others are done)."""
    share = sum(times.get(f, 1.0) for f in files) / parts
    units: list[str] = []
    weights: dict[str, float] = {}
    for f in files:
        took = times.get(f, 1.0)
        # A single test (from --failed) is never split further.
        tests = _tests_in(f) if took > share / 2 and "::" not in f else []
        if len(tests) > 1:
            for test in tests:
                units.append(test)
                weights[test] = took / len(tests)
        else:
            units.append(f)
            weights[f] = took
    return units, weights


def plan(targets: list[str], parts: int) -> list[Part]:
    by_folder: dict[str, list[str]] = {}
    for target in targets:
        by_folder.setdefault(_folder_of(target), []).append(target)
    jobs = []
    times = _load("file-times.json", {})
    for folder, chosen in by_folder.items():
        short = folder.split("/")[-1]
        if folder == "test/unit" and parts > 1:
            if chosen == [folder]:
                files = sorted(
                    p.relative_to(_ROOT).as_posix()
                    for p in (_ROOT / folder).glob("test_*.py")
                )
            else:
                # Chosen files and --failed tests are spread the same way.
                files = sorted({t.replace("\\", "/") for t in chosen})
            units, weights = _units(files, parts, times)
            split = _split(units, min(parts, len(units)), weights)
            if len(split) == 1:
                jobs.append(Part("unit", folder, split[0]))
                continue
            for i, part_units in enumerate(split, 1):
                jobs.append(Part(f"unit-{i}", folder, part_units))
        else:
            jobs.append(Part(short, folder, chosen))
    return jobs


def _validate_report(part: Part) -> pathlib.Path:
    """Each part's own validate report (test/conftest.py writes it): parts
    running at once don't write into one file."""
    return pathlib.Path(tempfile.gettempdir()) / f"gremlin-validate-{part.name}.txt"


def _start(
    part: Part, quick: bool, lines: queue.Queue, extra: tuple[str, ...] = ()
) -> None:
    command = [
        sys.executable, "-m", "pytest", "-v", "-p", "no:cacheprovider",
        "-o", "console_output_style=count", "--durations=15", *extra,
        *part.targets,
    ]
    if quick:
        command.insert(4, "-x")
    part.process = subprocess.Popen(
        command, cwd=_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
        env=dict(
            os.environ,
            PYTHONUNBUFFERED="1",
            GREMLIN_VALIDATE_REPORT=str(_validate_report(part)),
        ),
    )
    part.began = part.last_output = part.last_result = time.monotonic()

    def read() -> None:
        assert part.process is not None and part.process.stdout is not None
        for line in part.process.stdout:
            lines.put((part, line.rstrip("\n")))
        lines.put((part, None))

    threading.Thread(target=read, daemon=True).start()


def _add_time(part: Part, test_file: str) -> None:
    """A result came: the time since the last one (its setup included, a
    module fixture's too) was this test's, so its file's."""
    now = time.monotonic()
    took, part.last_result = now - part.last_result, now
    part.file_times[test_file] = part.file_times.get(test_file, 0.0) + took


def _end(process: subprocess.Popen) -> None:
    """Ends pytest and anything it started."""
    subprocess.run(
        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
        capture_output=True, check=False,
    )


def run(
    parts: list[Part], quick: bool, log, extra: tuple[str, ...] = ()  # noqa: ANN001
) -> tuple[list[tuple[float, str]], float]:
    start = time.monotonic()

    def say(part: Part | None, text: str) -> None:
        done = sum(p.done for p in parts)
        total = sum(p.total for p in parts)
        name = f"{part.name:<11}" if part else " " * 11
        line = f"[{_clock(start)}] {name} {done}/{total or '?'}  {text}"
        print(line, flush=True)
        log.write(line + "\n")
        log.flush()

    lines: queue.Queue = queue.Queue()
    for part in parts:
        _start(part, quick, lines, extra)
        what = " ".join(part.targets)
        if len(part.targets) > 3:
            what = f"{len(part.targets)} files"
        say(part, f"started: {what}")
    slow: list[tuple[float, str]] = []
    while not all(p.finished for p in parts):
        try:
            part, line = lines.get(timeout=1.0)
        except queue.Empty:
            now = time.monotonic()
            for p in parts:
                if p.finished:
                    continue
                if now - p.began > LIMIT_S:
                    say(p, f"!!! over {LIMIT_S // 60} min, stopping it")
                    assert p.process is not None
                    _end(p.process)
                    p.summary = f"STOPPED after {LIMIT_S // 60} min"
                elif now - p.last_output > QUIET_S and now - p.last_note > QUIET_S:
                    p.last_note = now
                    say(p, f"... still in {p.current or 'start-up'} "
                           f"({int(now - p.last_output)} s)")
            continue
        if line is None:
            assert part.process is not None
            part.process.wait()
            part.finished = True
            part.took = time.monotonic() - part.began
            say(part, f"=== {part.summary} ({part.took:.0f} s)")
            continue
        part.last_output = time.monotonic()
        if m := _COUNT.search(line):
            part.done, part.total = int(m.group(1)), int(m.group(2))
        if m := _RESULT.match(line):
            node, outcome = m.group(1), m.group(2)
            part.current = node
            _add_time(part, node.split("::")[0])
            if outcome in ("FAILED", "ERROR") and node not in part.failed:
                part.failed.append(node)
        if m := _SUMMARY.search(line):
            part.summary = m.group(1)
        if m := _SLOW.match(line):
            slow.append((float(m.group(1)), f"{m.group(2):<8} {m.group(3)}"))
        say(part, line)
    return slow, time.monotonic() - start


def main() -> int:
    # A test's output may hold characters the console (or a redirect) can't
    # show: show a stand-in rather than stop the run.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("targets", nargs="*", help="test files or folders")
    parser.add_argument("--failed", action="store_true",
                        help="only the tests that failed in the last run")
    parser.add_argument("--changed", action="store_true",
                        help="tests touching what changed since the last commit")
    parser.add_argument("--quick", action="store_true",
                        help="stop at the first failure")
    parser.add_argument("--parts", type=int, default=UNIT_PARTS,
                        help=f"parts test/unit is split into (default {UNIT_PARTS})")
    parser.add_argument("--random-order", action="store_true",
                        help="run the tests in random order (test/conftest.py "
                             "shuffles them; the seed is printed)")
    parser.add_argument("--seed", type=int, default=None,
                        help="the random order's seed (implies --random-order)")
    args = parser.parse_args()

    if args.failed:
        targets = list(_load(_failed_file(), []))
        if not targets:
            print("Nothing failed in the last run.")
            return 0
    elif args.changed:
        sys.path.insert(0, str(_ROOT / "test"))
        import changed_tests

        changed = changed_tests.changed_files()
        if not changed:
            print("Nothing changed since the last commit.")
            return 0
        targets, reasons = changed_tests.choose(changed)
        print(f"Changed: {len(changed)} files. Tests that touch them: {len(targets)}")
        for reason in reasons:
            print("  " + reason)
        if not targets:
            print("No test touches these changes.")
            return 0
    else:
        targets = args.targets or FOLDERS
    _wait_for_other_run()
    try:
        return _run_and_report(targets, args)
    finally:
        _done_running()


def _order_options(args: argparse.Namespace) -> tuple[str, ...]:
    """The random-order options for every part (all with the same seed, so
    the run can be repeated): --seed, else GREMLIN_TEST_SEED, else a new
    one."""
    if not args.random_order and args.seed is None:
        return ()
    seed = args.seed
    if seed is None:
        try:
            seed = int(os.environ.get("GREMLIN_TEST_SEED", ""))
        except ValueError:
            import random

            seed = random.randrange(1, 1_000_000)
    return ("--random-order", f"--random-seed={seed}")


def _run_and_report(targets: list[str], args: argparse.Namespace) -> int:
    parts = plan(targets, args.parts)
    extra = _order_options(args)
    with _LOG.open("w", encoding="utf-8") as log:
        print(f"Log: {_LOG}", flush=True)
        if extra:
            seed = extra[1].split("=")[1]
            note = f"Random order, seed {seed} (repeat with --seed {seed})"
            print(note, flush=True)
            log.write(note + "\n")
        slow, took = run(parts, args.quick, log, extra)
        failed = [node for p in parts for node in p.failed]
        if not args.failed or not failed:
            _save(_failed_file(), failed)
        times = dict(_load("file-times.json", {}))
        measured: dict[str, float] = {}
        for p in parts:  # a file spread over parts: add its shares up
            for test_file, seconds in p.file_times.items():
                measured[test_file] = measured.get(test_file, 0.0) + seconds
        # Only some of a file's tests ran (--failed, file::test): its time
        # is not the file's, and would leave a heavy file unsplit next time.
        partial = {t.replace("\\", "/").split("::")[0] for t in targets if "::" in t}
        times.update({f: t for f, t in measured.items() if f not in partial})
        _save("file-times.json", times)
        out = ["", f"=== All done in {int(took) // 60:02d}:{int(took) % 60:02d}"]
        out += [f"  {p.name:<11} {p.summary} ({p.took:.0f} s)" for p in parts]
        if failed:
            out.append(f"Failed ({len(failed)}), rerun with --failed:")
            out += [f"  {node}" for node in failed]
        if slow:
            out.append("Slowest:")
            slowest = sorted(slow, reverse=True)[:10]
            out += [f"  {s:6.2f}s {what}" for s, what in slowest]
        out.append("Validate reports:")
        out += [f"  {p.name:<11} {_validate_report(p)}" for p in parts]
        out.append(f"Log: {_LOG}")
        for line in out:
            print(line, flush=True)
            log.write(line + "\n")
    # A part that never reached pytest's summary (pytest missing, a crash)
    # is a failure too: CI once passed with no test run at all.
    ok = not failed and all(
        " failed" not in p.summary and "STOPPED" not in p.summary
        and " error" not in p.summary
        and re.search(r"\d+ (passed|skipped|xfailed|deselected)", p.summary)
        for p in parts
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
