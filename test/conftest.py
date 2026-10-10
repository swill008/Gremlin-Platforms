# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import os
import pathlib
import sys
import tempfile
import threading
import time
from collections.abc import Callable, Iterator
from typing import IO, TYPE_CHECKING

if TYPE_CHECKING:
    import pluggy

# Tests never put a window on the user's screen: the Gremlin app some tests
# build (pytest-qt's qapp) and every window it opens stay off-screen.
os.environ["QT_QPA_PLATFORM"] = "offscreen"
# Nor reach the network (the programs tests start inherit it): the update
# check is off. HTTPS_PROXY doesn't stop Qt's network calls.
os.environ["GREMLIN_OFFLINE"] = "1"
os.environ.setdefault(
    "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
)

# Mock before any imports happen
from unittest.mock import Mock

import pytest

# No test reaches the real vJoy driver (to-do 44): the guard goes in before
# anything that could load vJoyInterface.dll. By its folder: as a plain module
# (pytest -p conftest), "test" is Python's own.
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import vjoy_guard  # noqa: E402  # pyright: ignore[reportMissingImports]

vjoy_guard.install()

import gremlin.util  # noqa: E402

gremlin.util.userprofile_path = Mock(return_value=tempfile.mkdtemp())

import fake_input  # noqa: E402  # pyright: ignore[reportMissingImports]

import gremlin.ui.backend  # noqa: E402
import gremlin.windows_event_hook  # noqa: E402
import joystick_gremlin  # noqa: E402

# Tests never hook the keyboard and mouse of the PC they run on, and never
# send keys or mouse input to it (test/fake_input.py).
gremlin.windows_event_hook.enabled = False
fake_input.install()

# Hang tracing for the programs tests start (test/hang_trace/sitecustomize.py):
# one that stalls or runs longer than this prints every thread's stack and
# ends, and one whose main code has ended doesn't wait for its threads. Below the
# shortest timeout a test gives such a program (60 s), so the stacks arrive
# before the test gives up. Tests in this process: stall detection below.
os.environ.setdefault("GREMLIN_TEST_HANG_LIMIT", "50")
_HANG_TRACE = str(pathlib.Path(__file__).parent / "hang_trace")
if _HANG_TRACE not in os.environ.get("PYTHONPATH", "").split(os.pathsep):
    os.environ["PYTHONPATH"] = os.pathsep.join(
        p for p in (_HANG_TRACE, os.environ.get("PYTHONPATH", "")) if p
    )
sys.path.insert(0, _HANG_TRACE)
import stall_watch  # noqa: E402  # pyright: ignore[reportMissingImports]


def pytest_collection_modifyitems(
    session: pytest.Session, config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Stops a run that mixes test/unit with the folders needing the Gremlin app.

    The unit tests run on a plain QCoreApplication; test/integration and
    test/action_interaction need JoystickGremlinApp. One process has one
    application, so mixed runs fail in hundreds of confusing ways.
    """
    root = pathlib.Path(__file__).parent
    folders = set()
    for item in items:
        try:
            folders.add(pathlib.Path(str(item.path)).relative_to(root).parts[0])
        except ValueError:
            continue
    if "unit" in folders and folders & {"integration", "action_interaction"}:
        raise pytest.UsageError(
            "Run each test folder in its own pytest run: "
            "pytest test/unit, pytest test/integration, pytest test/action_interaction."
        )
    _shuffle(config, items)


# | Random test order (off by default): --random-order shuffles with a new
# | seed, --random-seed=N (or GREMLIN_TEST_SEED=N with --random-order) with
# | that one. The seed is in the header, so a run can be repeated. Files are
# | shuffled, then the tests inside each file: a file's fixtures are still
# | set up once.


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("gremlin", "Gremlin-Platforms test options")
    group.addoption(
        "--random-order",
        action="store_true",
        default=False,
        help="Run the tests in a random order (seed in the header).",
    )
    group.addoption(
        "--random-seed",
        type=int,
        default=None,
        help="Run the tests in the random order of this seed (implies --random-order).",
    )


def _order_seed(config: pytest.Config) -> int | None:
    """The shuffle seed, or None when the order isn't shuffled."""
    seed = config.getoption("--random-seed", None)
    if seed is None and not config.getoption("--random-order", False):
        return None
    if seed is None:
        try:
            seed = int(os.environ.get("GREMLIN_TEST_SEED", ""))
        except ValueError:
            import random

            seed = random.randrange(1, 1_000_000)
    return int(seed)


_ORDER_SEED = pytest.StashKey[int | None]()


def _shuffle(config: pytest.Config, items: list[pytest.Item]) -> None:
    if _ORDER_SEED not in config.stash:
        config.stash[_ORDER_SEED] = _order_seed(config)
    seed = config.stash[_ORDER_SEED]
    if seed is None:
        return
    import random

    rng = random.Random(seed)
    files: dict[str, list[pytest.Item]] = {}
    for item in items:
        files.setdefault(str(item.path), []).append(item)
    order = list(files)
    rng.shuffle(order)
    shuffled: list[pytest.Item] = []
    for name in order:
        tests = files[name]
        rng.shuffle(tests)
        shuffled.extend(tests)
    items[:] = shuffled


def pytest_report_header(config: pytest.Config) -> str | None:
    if _ORDER_SEED not in config.stash:
        config.stash[_ORDER_SEED] = _order_seed(config)
    seed = config.stash[_ORDER_SEED]
    if seed is None:
        return None
    return f"random order: seed {seed} (repeat with --random-seed={seed})"


@pytest.fixture(autouse=True)
def _no_message_boxes(monkeypatch: pytest.MonkeyPatch) -> list[tuple]:
    """No test shows a real Windows message box (they appear on screen even
    off-screen, and wait for a click): they are recorded instead."""
    shown: list[tuple] = []
    monkeypatch.setattr(
        joystick_gremlin, "_message_box", lambda *a: shown.append(a) or 1
    )
    return shown


@pytest.fixture(scope="session")
def qapp_cls() -> type[joystick_gremlin.JoystickGremlinApp]:
    return joystick_gremlin.JoystickGremlinApp


@pytest.fixture(scope="session")
def test_root_dir() -> pathlib.Path:
    return pathlib.Path(__file__).parent


# | Stall detection (test/hang_trace/stall_watch.py): a test whose main thread
# | stops making progress fails within seconds with the stack of every thread,
# | and the run goes on. A test may run 120 s at most.


class _Stalls:
    watch: stall_watch.StallWatch | None = None
    out: IO[str] = sys.stderr
    reports: dict[str, str] = {}
    finished = 0
    exit_status = 0
    exit_deadman: object = None


@pytest.hookimpl(trylast=True)  # after pytest's faulthandler kept the real stderr
def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "validate_off: leave the test out of the rule checks (it builds "
        "broken state on purpose)",
    )
    if not config.pluginmanager.is_registered(vjoy_guard):
        config.pluginmanager.register(vjoy_guard, "vjoy_guard")
    try:
        from _pytest.faulthandler import fault_handler_stderr_fd_key

        _Stalls.out = os.fdopen(
            os.dup(config.stash[fault_handler_stderr_fd_key]), "w", encoding="utf-8"
        )
    except Exception:
        _Stalls.out = sys.__stderr__ or sys.stderr
    if stall_watch.PROGRAM_WATCH is not None:  # pytest started by a test
        stall_watch.PROGRAM_WATCH.stop()
    watch = stall_watch.StallWatch(_test_stalled, _Stalls.out, limit=120.0)
    watch.start()
    _Stalls.watch = watch


def _test_stalled(report: str) -> None:
    """From the watchdog thread: fail the stalled test, or end the run when
    it can't be stopped (stuck inside C code)."""
    watch = _Stalls.watch
    nodeid = report.split("\n", 2)[1].removeprefix("=== STALLED: ")
    _Stalls.reports[nodeid] = report
    finished = _Stalls.finished
    stall_watch.write(_Stalls.out, report + "Failing this test.\n")
    stall_watch.raise_in_main_thread(stall_watch.TestStalled)
    deadline = time.monotonic() + stall_watch.STOP_GRACE
    while time.monotonic() < deadline:
        moved_on = watch is not None and watch.label not in (None, nodeid)
        if _Stalls.finished != finished or moved_on:
            return
        time.sleep(0.1)
    stall_watch.write(
        _Stalls.out,
        f"The test didn't stop within {stall_watch.STOP_GRACE:.0f} s (stuck inside "
        "C code): ending the run.\n" + stall_watch.describe_threads(),
    )
    stall_watch.end_process(3)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item: pytest.Item, nextitem: pytest.Item | None):  # noqa: ANN201
    if _Stalls.watch is not None:
        _Stalls.watch.watch(item.nodeid)
    try:
        yield
    finally:
        if _Stalls.watch is not None:
            _Stalls.watch.watch(None)
        if item.nodeid in _Stalls.reports:
            stall_watch.raise_in_main_thread(None)  # not raised yet: take it back
        _Stalls.finished += 1


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    _Stalls.exit_status = int(exitstatus)


# GREMLIN_TEST_EXIT_DEADMAN (seconds) shortens it for test_exit_hang.py.
EXIT_DEADMAN_S = 20.0


def _arm_exit_deadman() -> None:
    try:
        seconds = float(os.environ.get("GREMLIN_TEST_EXIT_DEADMAN") or EXIT_DEADMAN_S)
    except ValueError:
        seconds = EXIT_DEADMAN_S
    try:
        # Stacks by faulthandler, then TerminateProcess from a Windows timer:
        # no Python, no GIL (see stall_watch._Deadman). Kept alive to the end.
        deadman = stall_watch._Deadman(_Stalls.out)  # noqa: SLF001
        deadman.arm(seconds)
        _Stalls.exit_deadman = deadman
    except Exception:
        import faulthandler

        faulthandler.dump_traceback_later(seconds, exit=True, file=_Stalls.out)


@pytest.hookimpl(trylast=True)
def pytest_unconfigure(config: pytest.Config) -> None:
    """The run is over: stop the program's threads, so none keeps the
    process open. Any that still won't stop is named, with its stack, and
    the process ends with pytest's own result instead of waiting.

    And a deadman: a process still alive EXIT_DEADMAN_S from here (stuck in
    atexit or native teardown, to-do 42) prints every thread's stack and is
    ended, an EXIT HANG test/run_tests.py also reports."""
    _arm_exit_deadman()
    import gremlin.threads

    gremlin.threads.shutdown(timeout=2.0)
    main = threading.main_thread()
    left = [
        t for t in threading.enumerate()
        if t is not main and not t.daemon and t.is_alive()
    ]
    if left:
        stall_watch.write(
            _Stalls.out,
            "\n=== These threads would keep the test run from ending: "
            f"{', '.join(t.name for t in left)}\n"
            + stall_watch.describe_threads()
            + "=== Ending the run.\n",
        )
        stall_watch.end_process(_Stalls.exit_status)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):  # noqa: ANN201
    outcome = yield
    report = _Stalls.reports.get(item.nodeid)
    if report is not None and call.excinfo is not None:
        outcome.get_result().sections.append(("stall report", report))


def _stop_history_writer(deadline: float) -> None:
    """The History writer idles a second after its last item before ending,
    and its stop callback doesn't wake a get() in progress. Let it write what
    is queued (bounded), then stop it and wake it with a no-op so it ends
    now; the join below still checks that it did."""
    history = sys.modules.get("gremlin.history")
    if history is None or history._writer is None:
        return
    with history._queue.all_tasks_done:
        while history._queue.unfinished_tasks:
            left = deadline - time.monotonic()
            if left <= 0:
                break
            history._queue.all_tasks_done.wait(left)
    # Under the lock the writer ends with, so the no-op never outlives it.
    with history._start_lock:
        if history._writer is not None:
            history._stop.set()
            history._queue.put(lambda: None)


@pytest.fixture(autouse=True)
def _no_threads_left_running() -> Iterator[None]:
    """A test may not leave threads running (a program thread left behind
    keeps the process from ending, see test/hang_trace/sitecustomize.py)."""
    before = set(threading.enumerate())
    yield
    new = [t for t in threading.enumerate() if t not in before and not t.daemon]
    watch = _Stalls.watch
    label = watch.label if watch is not None else None
    if watch is not None:
        watch.watch(None)  # a short wait on purpose, not a stall
    deadline = time.monotonic() + 2.0
    _stop_history_writer(deadline)
    for thread in new:
        try:
            thread.join(max(0.0, deadline - time.monotonic()))
        except RuntimeError:
            # Listed but still starting: let it start, then wait as usual.
            time.sleep(0.05)
            thread.join(max(0.0, deadline - time.monotonic()))
    if watch is not None and label is not None:
        watch.watch(label)
    left = [thread.name for thread in new if thread.is_alive()]
    if left:
        pytest.fail(f"The test left threads running: {', '.join(left)}")


@pytest.fixture(autouse=True)
def _history_written_before_the_test() -> None:
    """History work an earlier test left (a writer still busy when its thread
    check gave up) is written before this test's fixtures point History at
    their own folder; otherwise it lands in theirs."""
    history = sys.modules.get("gremlin.history")
    if history is None:
        return
    deadline = time.monotonic() + 5.0
    while history._writer is not None and time.monotonic() < deadline:
        time.sleep(0.02)
    history.flush()


# | Rule checks (gremlin/validate.py): after each test the open profile is
# | checked, and after a test that ran or stopped a CodeRunner, what a Run
# | leaves behind. A problem that isn't a warning (validate.WARNINGS) fails
# | the test (D-TEST-RULES-FAIL): the profile check fails the test itself,
# | the Run check is an error at teardown. Every problem, warnings too, goes
# | to a report file (GREMLIN_VALIDATE_REPORT, else gremlin-validate-report.txt
# | in the temp folder; each run adds its own block) and a one-line summary
# | ends the run. @pytest.mark.validate_off leaves a test out.


class _Validate:
    run_before = 0
    last_profile: tuple[int, tuple[str, ...]] | None = None
    found: dict[str, list[str]] = {}


def _run_number() -> int:
    scope = sys.modules.get("gremlin.run_scope")
    return int(scope.number()) if scope else 0


def _validate_report_path() -> pathlib.Path:
    named = os.environ.get("GREMLIN_VALIDATE_REPORT", "").strip()
    if named:
        return pathlib.Path(named)
    return pathlib.Path(tempfile.gettempdir()) / "gremlin-validate-report.txt"


def _note(nodeid: str, problems: list[str]) -> list[str]:
    if problems:
        _Validate.found.setdefault(nodeid, []).extend(problems)
    return problems


def _damage(problems: list[str]) -> list[str]:
    """The problems that fail a test: all but the warnings."""
    from gremlin import validate

    return [p for p in problems if not validate.is_warning(p)]


def _fail_on_damage(
    outcome: pluggy.Result[None], problems: list[str], when: str
) -> None:
    """Fails the test phase (outcome) with the damage among the problems,
    unless it failed already (its own failure says more)."""
    damage = _damage(problems)
    if not damage or outcome.excinfo is not None:
        return
    text = "\n".join(f"    {p}" for p in damage)
    outcome.force_exception(
        pytest.fail.Exception(
            f"Rule checks (gremlin/validate.py) found damage {when}:\n{text}\n"
            "(@pytest.mark.validate_off leaves out a test that builds it on purpose)",
            pytrace=False,
        )
    )


def _check_profile(item: pytest.Item) -> list[str]:
    """The open profile, right after the test (before its fixtures put
    another one back)."""
    if item.get_closest_marker("validate_off") is not None:
        return []
    state = sys.modules.get("gremlin.shared_state")
    current = getattr(state, "current_profile", None) if state else None
    profile_module = sys.modules.get("gremlin.profile")
    if current is None or profile_module is None:
        return []
    if not isinstance(current, profile_module.Profile):
        return []  # a test's stand-in, not a profile to check
    from gremlin import validate

    found = validate.profile(current)
    # The same profile with the same problems: named once, at the first test
    # that left it so.
    key = (id(current), tuple(found))
    if key != _Validate.last_profile:
        _Validate.last_profile = key
        return _note(item.nodeid, found)
    return []


def _check_run(item: pytest.Item) -> list[str]:
    """What a Run left behind, after a test that ran or stopped one (its
    fixtures stopped it by now)."""
    if _run_number() == _Validate.run_before:
        return []
    if item.get_closest_marker("validate_off") is not None:
        return []
    state = sys.modules.get("gremlin.shared_state")
    if state is not None and state.runtime_active():
        return []  # still running (a Run shared by a class or module of tests)
    from gremlin import validate

    found = validate.after_stop()
    if any(validate.code_of(p) == "RUN-THREADS-LEFT" for p in found):
        # Stop asks the Run's threads to end; give them a moment.
        import gremlin.threads

        names = {gremlin.threads.PREFIX + n for n in validate.RUN_THREADS}
        deadline = time.monotonic() + 1.0
        for thread in threading.enumerate():
            if thread.name in names and thread is not threading.current_thread():
                thread.join(max(0.0, deadline - time.monotonic()))
        found = validate.after_stop()
    return _note(item.nodeid, found)


def _guard(item: pytest.Item, check: Callable[[pytest.Item], list[str]]) -> list[str]:
    try:
        return check(item)
    except Exception as exc:
        try:
            problem = f"VALIDATE-ERROR: the check after the test failed: {exc!r}"
            return _note(item.nodeid, [problem])
        except Exception:
            return []


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_setup(item: pytest.Item):  # noqa: ANN201
    try:
        _Validate.run_before = _run_number()
    except Exception:
        pass
    yield


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item: pytest.Item):  # noqa: ANN201
    outcome = yield
    _fail_on_damage(outcome, _guard(item, _check_profile), "in the open profile")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_teardown(item: pytest.Item, nextitem: pytest.Item | None):  # noqa: ANN201
    outcome = yield
    _fail_on_damage(outcome, _guard(item, _check_run), "after the Run")


def pytest_terminal_summary(
    terminalreporter: pytest.TerminalReporter, exitstatus: int, config: pytest.Config
) -> None:
    try:
        from collections import Counter

        found = _Validate.found
        codes = Counter(
            p.split(":", 1)[0].strip() for problems in found.values() for p in problems
        )
        path = _validate_report_path()
        lines = [
            f"=== {time.strftime('%Y-%m-%d %H:%M:%S')} pid {os.getpid()}: "
            f"pytest {' '.join(config.invocation_params.args)}"
        ]
        for nodeid, problems in found.items():
            lines.append(nodeid)
            lines.extend(f"    {p}" for p in problems)
        if not found:
            lines.append("No problems.")
        try:
            if path.is_file() and path.stat().st_size > 2_000_000:
                path.unlink()  # a fresh start instead of a file without end
        except OSError:
            pass
        with path.open("a", encoding="utf-8") as report:
            report.write("\n".join(lines) + "\n\n")
        total = sum(codes.values())
        summary = ", ".join(f"{code} x{n}" for code, n in codes.most_common())
        terminalreporter.write_line(
            f"validate: {total} problem(s) in {len(found)} test(s)"
            + (f" [{summary}]" if summary else "")
            + f" -> {path}"
        )
    except Exception as exc:
        try:
            terminalreporter.write_line(f"validate: no report ({exc!r})")
        except Exception:
            pass
