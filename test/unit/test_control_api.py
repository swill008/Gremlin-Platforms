# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The control API in the program (claude/plans/control-api-contract.md):
the Options switch, the pipe and endpoint.json, the key, the call registry,
time limits, the switch's own key refused, Options changes into History
"(by API)", and the system log line of every call.

The pipe is a real named pipe (a fresh random name each time it opens, so
never the running program's); gremlin_ctl.client talks to it from a worker
thread while this (main) thread runs the events the main-thread calls
need. endpoint.json lands in the tests' temporary user folder
(gremlin.util.userprofile_path, test/conftest.py).
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
from collections.abc import Callable, Iterator
from multiprocessing.connection import Client as PipeClient
from pathlib import Path
from typing import Any

import pytest
from PySide6 import QtCore

from gremlin import control_api
from gremlin.config import Configuration
from gremlin_ctl import client as ctl

_ROOT = Path(__file__).resolve().parents[2]
_SWITCH = control_api.SWITCH_KEY
_OTHER = ("global", "vjoy", "keep-alive")  # a plain Bool the API may change


def _pump(ms: int = 20) -> None:
    end = time.monotonic() + ms / 1000.0
    while True:
        QtCore.QCoreApplication.processEvents()
        if time.monotonic() >= end:
            return
        time.sleep(0.005)


def _off_main(fn: Callable[[], Any], timeout: float = 20.0) -> Any:  # noqa: ANN401
    """Runs fn on a worker thread (as another program would) while this
    main thread runs events; returns its result or raises its error."""
    box: dict[str, Any] = {}

    def work() -> None:
        try:
            box["value"] = fn()
        except BaseException as e:  # noqa: BLE001 - handed back
            box["error"] = e

    thread = threading.Thread(target=work, name="test-api-client", daemon=True)
    thread.start()
    deadline = time.monotonic() + timeout
    while thread.is_alive() and time.monotonic() < deadline:
        _pump(10)
    assert not thread.is_alive(), f"no answer within {timeout} s"
    if "error" in box:
        raise box["error"]
    return box.get("value")


def _switch(on: bool) -> None:
    """As the Options row changes it (signal.configChanged follows)."""
    from gremlin.ui import option

    assert option.change_setting(_SWITCH, on)


@pytest.fixture
def api(qapp: object, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """control_api started as the program starts it, switch off; the real
    named pipe allowed (its name is random). Stopped, the switch and the
    other setting restored, after."""
    monkeypatch.setattr(control_api, "_under_test", lambda: False)
    cfg = Configuration()
    kept = {key: cfg.value(*key) for key in (_SWITCH, _OTHER)}
    cfg.set(*_SWITCH, False)
    control_api.start()
    try:
        yield control_api.endpoint_path()
    finally:
        control_api.stop()
        for key, value in kept.items():
            cfg.set(*key, value)
        _pump(50)


@pytest.fixture
def connected(api: Path) -> Iterator[ctl.Client]:
    _switch(True)
    client = _off_main(lambda: ctl.connect(endpoint=api))
    try:
        yield client
    finally:
        client.close()


# --- the switch --------------------------------------------------------------


def test_the_switch_is_off_in_new_settings(tmp_path: Path) -> None:
    """A first start (no settings file) has the switch off. Its own
    process, so the option is registered into empty settings."""
    import proc_tree  # pyright: ignore[reportMissingImports]  (test/)

    env = dict(os.environ, USERPROFILE=str(tmp_path), QT_QPA_PLATFORM="offscreen")
    code = (
        "import sys; sys.path.insert(0, '.');"
        "from gremlin import control_api;"
        "from gremlin.config import Configuration;"
        "control_api.register_options();"
        "print(repr(Configuration().value(*control_api.SWITCH_KEY)),"
        " control_api.allowed())"
    )
    done = proc_tree.run(
        [sys.executable, "-c", code], cwd=_ROOT, env=env, text=True, timeout=60
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip().splitlines()[-1] == "False False"


def test_options_shows_the_switch_under_general_control() -> None:
    from gremlin.ui import option

    general = dict(dict(option.main_layout())["General"])
    assert general["Control"] == [_SWITCH]
    assert option.entry_title(_SWITCH[2], "/".join(_SWITCH)) == (
        "Allow control from other programs"
    )


def test_switch_off_no_pipe_and_no_endpoint(api: Path) -> None:
    assert control_api.running() is False
    assert not api.exists()
    with pytest.raises(ctl.Off):
        ctl.connect(endpoint=api)


def test_switch_on_opens_the_pipe_and_writes_the_endpoint(api: Path) -> None:
    _switch(True)
    assert control_api.running() is True
    info = json.loads(api.read_text(encoding="utf-8"))
    assert set(info) == {"address", "key", "version", "pid"}
    assert info["address"].startswith(r"\\.\pipe\gremlin-platforms-api-")
    assert info["address"] == control_api.address()
    assert len(bytes.fromhex(info["key"])) == 32
    assert info["version"] == control_api.PROTOCOL_VERSION == 1
    assert info["pid"] == os.getpid()
    with _off_main(lambda: ctl.connect(endpoint=api)) as client:
        hello = _off_main(lambda: client.call("hello"))
    assert hello["version"] == 1
    assert isinstance(hello["program_version"], str)


def test_switch_off_closes_the_pipe_and_removes_the_endpoint(
    connected: ctl.Client, api: Path
) -> None:
    address = control_api.address()
    _switch(False)
    assert control_api.running() is False
    assert not api.exists()
    with pytest.raises((ctl.NotRunning, ctl.StoppedAnswering)):
        _off_main(lambda: connected.call("hello"))
    with pytest.raises(ctl.Off):
        ctl.connect(endpoint=api)
    # Nothing listens on the old address any more.
    with pytest.raises(OSError):
        _off_main(lambda: PipeClient(address, family="AF_PIPE", authkey=b"x" * 32))


def test_a_new_pipe_each_time_it_opens(api: Path) -> None:
    _switch(True)
    first = json.loads(api.read_text(encoding="utf-8"))
    _switch(False)
    _switch(True)
    second = json.loads(api.read_text(encoding="utf-8"))
    assert first["address"] != second["address"]
    assert first["key"] != second["key"]


def test_a_wrong_key_is_refused_and_the_right_one_still_works(
    api: Path, caplog: pytest.LogCaptureFixture
) -> None:
    from multiprocessing import AuthenticationError

    _switch(True)
    info = json.loads(api.read_text(encoding="utf-8"))
    with caplog.at_level(logging.WARNING, logger="system"):
        with pytest.raises((AuthenticationError, EOFError, OSError)):
            _off_main(
                lambda: PipeClient(
                    info["address"], family="AF_PIPE", authkey=b"\0" * 32
                )
            )
        _pump(200)
    assert any("connection was refused" in r.getMessage() for r in caplog.records)
    with _off_main(lambda: ctl.connect(endpoint=api)) as client:
        assert _off_main(lambda: client.call("hello"))["version"] == 1


# --- calls -------------------------------------------------------------------


def test_an_unknown_call_answers_not_ok(connected: ctl.Client) -> None:
    with pytest.raises(ctl.CallError, match="No call 'no.such.call'"):
        _off_main(lambda: connected.call("no.such.call"))
    reply = json.loads(
        control_api.handle_bytes(b'{"call": "no.such.call", "args": {}}')
    )
    assert reply["ok"] is False
    assert reply["code"] == "unknown_call"
    assert "No call 'no.such.call'" in reply["error"]


def test_with_the_switch_off_a_call_does_nothing(qapp: object) -> None:
    """The answer says so; the handler never runs."""
    ran: list[dict] = []
    control_api.register("test.never", lambda args: ran.append(args))
    cfg = Configuration()
    before = cfg.value(*_SWITCH)
    cfg.set(*_SWITCH, False)
    try:
        reply = control_api.dispatch("test.never", {})
    finally:
        cfg.set(*_SWITCH, before)
        with control_api._calls_lock:  # noqa: SLF001
            control_api._calls.pop("test.never", None)  # noqa: SLF001
    assert reply == {"ok": False, "error": control_api.OFF_TEXT, "code": "refused"}
    assert ran == []


def test_help_lists_every_call_with_its_summary(connected: ctl.Client) -> None:
    rows = _off_main(lambda: connected.call("help"))
    names = {r["name"] for r in rows}
    assert {
        "hello",
        "help",
        "state",
        "devices",
        "run.start",
        "run.stop",
        "profile.load",
        "profile.save",
        "option.get",
        "option.set",
        "options.list",
        "trace.on",
        "trace.off",
        "trace.status",
        "log",
    } <= names
    assert all(r["summary"] for r in rows), [r for r in rows if not r["summary"]]


@pytest.fixture
def slow_call() -> Iterator[list[str]]:
    """test.slow: a main-thread call that takes 1.5 s with a 0.3 s limit;
    test.quick: a main-thread call that answers at once."""
    done: list[str] = []

    def slow(_args: dict) -> str:
        time.sleep(1.5)
        done.append("slow")
        return "late"

    control_api.register("test.slow", slow, main_thread=True, timeout_s=0.3)
    control_api.register("test.quick", lambda _a: "quick", main_thread=True)
    try:
        yield done
    finally:
        with control_api._calls_lock:  # noqa: SLF001
            control_api._calls.pop("test.slow", None)  # noqa: SLF001
            control_api._calls.pop("test.quick", None)  # noqa: SLF001


def test_a_slow_main_thread_call_times_out_and_the_program_keeps_answering(
    connected: ctl.Client, slow_call: list[str]
) -> None:
    started = time.monotonic()
    with pytest.raises(
        ctl.CallError, match=r"test\.slow took over 0\.3 s; it may still finish\."
    ):
        _off_main(lambda: connected.call("test.slow"))
    assert time.monotonic() - started < 5.0
    _pump(100)
    assert _off_main(lambda: connected.call("test.quick")) == "quick"
    assert _off_main(lambda: connected.call("hello"))["version"] == 1


# --- Options -------------------------------------------------------------------


def test_option_set_refuses_the_switch_itself(connected: ctl.Client) -> None:
    with pytest.raises(ctl.CallError, match="Only the user"):
        _off_main(
            lambda: connected.call(
                "option.set", key="global/control/allow-other-programs", value=False
            )
        )
    assert Configuration().value(*_SWITCH) is True
    assert control_api.running() is True


def test_option_get_reads_a_setting(connected: ctl.Client) -> None:
    Configuration().set(*_OTHER, False)
    got = _off_main(lambda: connected.call("option.get", key="/".join(_OTHER)))
    assert got["value"] is False


@pytest.fixture
def history_groups(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """History's grouped entries as written (nothing reaches the History
    folder): later() runs the write at once, _write_group is kept here."""
    from gremlin import history

    written: list[dict] = []
    monkeypatch.setattr(history, "later", lambda work: work())
    monkeypatch.setattr(history, "_write_group", lambda group: written.append(group))
    return written


def test_option_set_changes_the_setting_and_history_marks_it_by_api(
    connected: ctl.Client, history_groups: list[dict]
) -> None:
    Configuration().set(*_OTHER, False)
    _off_main(lambda: connected.call("option.set", key="/".join(_OTHER), value=True))
    assert Configuration().value(*_OTHER) is True
    by_api = [g for g in history_groups if g["extra"].get("by") == "api"]
    assert len(by_api) == 1, history_groups
    assert by_api[0]["title"].endswith("(by API)")
    assert by_api[0]["area"] == "settings"
    assert by_api[0]["items"], "the setting change itself is in the entry"


def test_every_call_writes_an_api_line_to_the_system_log(
    connected: ctl.Client, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="system"):
        _off_main(lambda: connected.call("hello"))
        with pytest.raises(ctl.CallError):
            _off_main(lambda: connected.call("no.such.call"))
        _off_main(lambda: connected.call("option.get", key="/".join(_OTHER)))
    lines = [
        r.getMessage() for r in caplog.records if r.getMessage().startswith("API: ")
    ]
    assert any(
        t.startswith("API: no.such.call") and "-> error: No call" in t for t in lines
    )
    assert any(
        t.startswith("API: option.get") and "keep-alive" in t and t.endswith("-> ok")
        for t in lines
    )


def test_the_hello_handshake_writes_no_api_line(
    connected: ctl.Client, caplog: pytest.LogCaptureFixture
) -> None:
    """S8 (user 2026-11-23, 2a): the client says hello before every call;
    only the real calls are logged, so one command is one line."""
    with caplog.at_level(logging.INFO, logger="system"):
        _off_main(lambda: connected.call("hello"))
        _off_main(lambda: connected.call("option.get", key="/".join(_OTHER)))
    lines = [
        r.getMessage() for r in caplog.records if r.getMessage().startswith("API: ")
    ]
    assert not [t for t in lines if t.startswith("API: hello")]
    assert [t for t in lines if t.startswith("API: option.get")]


def test_stop_at_quit_closes_the_pipe_and_removes_the_endpoint(api: Path) -> None:
    _switch(True)
    assert api.exists()
    control_api.stop()
    assert control_api.running() is False
    assert not api.exists()
    # Stopped: the switch no longer opens it.
    _switch(False)
    _switch(True)
    assert control_api.running() is False


# --- devices: plugged in and known (S3) -----------------------------------------


def test_devices_lists_known_devices_that_are_not_plugged_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """S3: every device the program knows, each with plugged_in."""
    from types import SimpleNamespace

    from gremlin import device_initialization
    from gremlin.modules import store

    stick = SimpleNamespace(
        name="Stick",
        device_guid="{11111111-1111-1111-1111-111111111111}",
        is_virtual=False,
        vjoy_id=0,
        axis_count=3,
        button_count=12,
        hat_count=1,
    )
    monkeypatch.setattr(device_initialization, "joystick_devices", lambda: [stick])
    monkeypatch.setattr(
        store,
        "known_devices",
        lambda: [
            {
                "name": "Stick",
                "guid": stick.device_guid,
                "connected": True,
                "label": "Stick",
            },
            {
                "name": "Pedals",
                "guid": "{22222222-2222-2222-2222-222222222222}",
                "connected": False,
                "label": "My Pedals",
            },
        ],
    )
    rows = control_api._devices({})  # noqa: SLF001
    by_name = {r["name"]: r for r in rows}
    assert set(by_name) == {"Stick", "Pedals"}
    assert by_name["Stick"]["plugged_in"] is True
    assert by_name["Stick"]["buttons"] == 12
    assert by_name["Pedals"]["plugged_in"] is False
    assert by_name["Pedals"]["label"] == "My Pedals"
    assert by_name["Pedals"]["guid"] == "22222222-2222-2222-2222-222222222222"
    assert by_name["Pedals"]["buttons"] is None


def test_devices_lists_real_devices_only_each_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """S21 (user 2026-11-23, 2a): plugged-in devices, then known hardware
    that isn't plugged in, each once; not the program's own inputs, not the
    output modules, not known rows without a device id."""
    from types import SimpleNamespace

    from gremlin import device_initialization
    from gremlin.modules import device_class, store

    stick = SimpleNamespace(
        name="VKB Stick",
        device_guid="{11111111-1111-1111-1111-111111111111}",
        is_virtual=False,
        vjoy_id=0,
        axis_count=6,
        button_count=32,
        hat_count=1,
    )
    vjoys = [
        SimpleNamespace(
            name="vJoy Device",
            device_guid=f"{{3333333{n}-3333-3333-3333-333333333333}}",
            is_virtual=True,
            vjoy_id=n,
            axis_count=8,
            button_count=32,
            hat_count=0,
        )
        for n in (1, 2, 3)
    ]
    monkeypatch.setattr(
        device_initialization, "joystick_devices", lambda: [stick, *vjoys]
    )
    keyboard = str(device_class.guid_of_kind("keyboard"))
    known = [
        {"name": "Keyboard", "guid": "", "connected": False, "label": "Keyboard"},
        {"name": "Keyboard", "guid": keyboard, "connected": False, "label": "Keys"},
        {"name": "Logical Device", "guid": "", "connected": False},
        {"name": "OSC", "guid": "", "connected": False, "label": "OSC"},
        *({"name": f"vJoy {n}", "guid": "", "connected": False} for n in (1, 2, 3, 4)),
        {
            "name": "vJoy Device",
            "guid": "{44444444-4444-4444-4444-444444444444}",
            "connected": False,
        },
        {"name": "Xbox 360 Controller", "guid": "", "connected": False},
        {"name": "Throttle", "guid": "", "connected": False, "label": "Throttle"},
        {
            "name": "HID Remapper 2DGG",
            "guid": "{55555555-5555-5555-5555-555555555555}",
            "connected": False,
            "label": "HID Remapper 2DGG",
        },
        # Seen twice (the profile and a module file): listed once.
        {
            "name": "HID Remapper 2DGG",
            "guid": "{55555555-5555-5555-5555-555555555555}",
            "connected": False,
        },
    ]
    monkeypatch.setattr(store, "known_devices", lambda: known)
    rows = control_api._devices({})  # noqa: SLF001
    assert [(r["name"], r["plugged_in"]) for r in rows] == [
        ("VKB Stick", True),
        ("vJoy Device", True),
        ("vJoy Device", True),
        ("vJoy Device", True),
        ("HID Remapper 2DGG", False),
    ]


# --- profile.save: History marked by API (decision 3a) ---------------------------


def test_history_entries_made_by_the_api_are_marked(qapp: object) -> None:
    """history.made_by("api"): each entry made while it is set, and work
    later() runs on the writer thread, carries {"by": "api"} and a title
    ending "(by API)"; outside it nothing is marked."""
    from gremlin import history

    seen: list[dict] = []
    with history.made_by("api"):
        seen.append(history._make("profile", "Saved a", {}, None, None, "save"))  # noqa: SLF001
        history.later(
            lambda: seen.append(
                history._make("profile", "Saved b", {}, None, None, "save")  # noqa: SLF001
            )
        )
    history.flush()
    history._settle()  # noqa: SLF001
    seen.append(history._make("profile", "Saved c", {}, None, None, "save"))  # noqa: SLF001
    marked = {e["title"]: e.get("by") for e in seen}
    assert marked == {
        "Saved a (by API)": "api",
        "Saved b (by API)": "api",
        "Saved c": None,
    }
    # A Restore of a marked entry is the user's: its title drops the mark.
    assert history.original_title({"title": "Saved a (by API)", "by": "api"}) == (
        "Saved a"
    )


def test_profile_save_marks_its_history_entries_by_api(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """profile.save runs the program's save with History's "by" set: every
    entry the save records (each input, the whole-profile copy) is marked;
    kinds and subjects are as a save from the window makes them."""
    from gremlin import history, history_profile

    path = tmp_path / "api-save.xml"
    before = "<profile><devices/></profile>"
    after = "<profile><devices/><settings><x/></settings></profile>"
    made: list[dict] = []
    monkeypatch.setattr(history, "_append", lambda entry: made.append(entry))

    class _Backend:
        def profilePath(self) -> str:
            return str(path)

        def saveProfile(self, p: str) -> bool:
            history_profile.record_save(Path(p), before, after)
            return True

    monkeypatch.setattr(control_api, "_backend", lambda: _Backend())
    assert control_api._profile_save({}) == {"profile": str(path), "saved": True}  # noqa: SLF001
    history.flush()
    history._settle()  # noqa: SLF001
    mine = [e for e in made if (e.get("subject") or {}).get("profile") == str(path)]
    assert {e["kind"] for e in mine} >= {"profile"}
    assert all(e.get("by") == "api" for e in mine), mine
    assert all(e["title"].endswith("(by API)") for e in mine), mine


def test_command_run_with_an_unknown_id_is_an_error(connected: ctl.Client) -> None:
    """S17: an id that isn't a main window command fails the call ("No
    command called ..."); a known one that can't run now answers ran false."""
    from gremlin.ui.backend import Backend

    ran: list[str] = []

    class _Backend:
        def command_list(self) -> list[dict]:
            return [{"id": "view.home", "text": "Home", "group": "View"}]

        def run_command_id(self, command_id: str) -> bool:
            ran.append(command_id)
            return False  # known, but not usable now

    with control_api._calls_lock:  # noqa: SLF001
        kept = {n: control_api._calls.get(n) for n in ("commands", "command.run")}  # noqa: SLF001
    Backend.klass.register_api_calls(_Backend(), control_api)  # type: ignore[arg-type]
    try:
        with pytest.raises(ctl.CallError, match="No command called 'no.such.command'"):
            _off_main(lambda: connected.call("command.run", id="no.such.command"))
        assert ran == []
        assert _off_main(lambda: connected.call("command.run", id="view.home")) == {
            "ran": False
        }
        assert ran == ["view.home"]
    finally:
        with control_api._calls_lock:  # noqa: SLF001
            for name, entry in kept.items():
                if entry is None:
                    control_api._calls.pop(name, None)  # noqa: SLF001
                else:
                    control_api._calls[name] = entry  # noqa: SLF001


# --- FIX-B (user 2026-11-23, 2a and 3a) -------------------------------------------


def _call_through_dispatch(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    handler: Callable[[dict], Any],
    args: dict | None = None,
) -> tuple[dict, list[logging.LogRecord]]:
    """dispatch() of a throwaway call with the switch on; its answer and
    the API log records."""
    monkeypatch.setattr(control_api, "allowed", lambda: True)
    monkeypatch.setitem(
        control_api._calls,  # noqa: SLF001
        "test.fixb",
        control_api._Call(  # noqa: SLF001
            handler, False, 5.0, "", {k: control_api.Arg("any") for k in args or {}}
        ),
    )
    with caplog.at_level(logging.INFO, logger="system"):
        reply = control_api.dispatch("test.fixb", args)
    records = [r for r in caplog.records if r.getMessage().startswith("API: ")]
    return reply, records


def test_a_call_without_arguments_logs_one_space(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """3a: "API: state -> ok", not "API: state  -> ok"."""
    _, records = _call_through_dispatch(monkeypatch, caplog, lambda _a: 1)
    assert [r.getMessage() for r in records] == ["API: test.fixb -> ok"]


def test_a_call_with_arguments_logs_them_between_single_spaces(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _, records = _call_through_dispatch(monkeypatch, caplog, lambda _a: 1, {"a": 1})
    assert [r.getMessage() for r in records] == ['API: test.fixb {"a": 1} -> ok']


def test_a_call_error_is_one_line_without_a_traceback(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """2a: an expected error (CallError) answers its text alone and logs
    only the one-line API line."""

    def refuse(_args: dict) -> None:
        raise control_api.CallError("No window called 'X'")

    reply, records = _call_through_dispatch(monkeypatch, caplog, refuse)
    assert reply == {"ok": False, "error": "No window called 'X'", "code": "failed"}
    assert [r.getMessage() for r in records] == [
        "API: test.fixb -> error: No window called 'X'"
    ]
    assert not [r for r in records if r.exc_info]


def test_an_unexpected_error_still_logs_its_traceback(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A real fault (not a CallError) keeps its traceback in the log."""

    def broken(_args: dict) -> None:
        raise ZeroDivisionError("boom")

    reply, records = _call_through_dispatch(monkeypatch, caplog, broken)
    assert reply == {"ok": False, "error": "ZeroDivisionError: boom", "code": "failed"}
    assert [r for r in records if r.exc_info]


def test_devices_ids_are_in_one_form(monkeypatch: pytest.MonkeyPatch) -> None:
    """3a: plugged-in rows (DILL's upper-case GUID text) and known rows
    (the Library's lower-case form) both come back in the Library's form:
    lower case, dashes, no braces."""
    from types import SimpleNamespace

    import dill
    from gremlin import device_initialization
    from gremlin.modules import store

    stick = SimpleNamespace(
        name="Stick",
        device_guid=dill.GUID.from_str("{ABCDEF01-2345-6789-ABCD-EF0123456789}"),
        is_virtual=False,
        vjoy_id=0,
        axis_count=3,
        button_count=12,
        hat_count=1,
    )
    monkeypatch.setattr(device_initialization, "joystick_devices", lambda: [stick])
    monkeypatch.setattr(
        store,
        "known_devices",
        lambda: [
            {
                "name": "Pedals",
                "guid": "{22222222-AAAA-2222-2222-222222222222}",
                "connected": False,
                "label": "Pedals",
            },
        ],
    )
    rows = control_api._devices({})  # noqa: SLF001
    assert [r["guid"] for r in rows] == [
        "abcdef01-2345-6789-abcd-ef0123456789",
        "22222222-aaaa-2222-2222-222222222222",
    ]


# --- run.start / run.stop answer when done (D-13-RUN-WAIT) ------------------------


class _RunBackend(QtCore.QObject):
    """Backend's Run side as the API sees it: activate_gremlin hands the
    request over and the answer comes later on the main thread (as the
    input thread's runStarted/runStopped reach Backend's handlers)."""

    runStartHandled = QtCore.Signal(bool, str)
    runStopHandled = QtCore.Signal()

    def __init__(
        self, *, delay_ms: int = 150, fail: str = "", answer: bool = True
    ) -> None:
        super().__init__()
        self.gremlinStarting = False
        self.gremlinActive = False
        self.delay_ms = delay_ms
        self.fail = fail
        self.answer = answer
        self.asked: list[bool] = []

    def activate_gremlin(self, activate: bool) -> None:
        self.asked.append(activate)
        self.gremlinStarting = activate
        if self.answer:
            QtCore.QTimer.singleShot(self.delay_ms, lambda: self._done(activate))

    def _done(self, activate: bool) -> None:
        self.gremlinStarting = False
        if activate:
            self.gremlinActive = not self.fail
            self.runStartHandled.emit(not self.fail, self.fail)
        else:
            self.gremlinActive = False
            self.runStopHandled.emit()

    def listeners(self) -> int:
        return self.receivers(QtCore.SIGNAL("runStartHandled(bool,QString)")) + (
            self.receivers(QtCore.SIGNAL("runStopHandled()"))
        )


@pytest.fixture
def run_backend(
    monkeypatch: pytest.MonkeyPatch, connected: ctl.Client
) -> Callable[..., _RunBackend]:
    from gremlin import input_thread

    monkeypatch.setattr(input_thread, "is_running", lambda: True)
    monkeypatch.setattr(input_thread, "is_inline", lambda: False)

    def make(**kwargs: Any) -> _RunBackend:  # noqa: ANN401
        backend = _RunBackend(**kwargs)
        monkeypatch.setattr(control_api, "_backend", lambda: backend)
        return backend

    return make


def test_run_stop_answers_stopped_after_the_run_has_stopped(
    connected: ctl.Client, run_backend: Callable[..., _RunBackend]
) -> None:
    """The old answer read the state at once and said "running" (seen
    live): the answer now waits for the Run to stop."""
    backend = run_backend()
    backend.gremlinActive = True
    assert _off_main(lambda: connected.call("run.stop")) == {"run": "stopped"}
    assert backend.asked == [False]
    assert backend.listeners() == 0


def test_run_start_answers_running_after_the_run_has_started(
    connected: ctl.Client, run_backend: Callable[..., _RunBackend]
) -> None:
    backend = run_backend()
    assert _off_main(lambda: connected.call("run.start")) == {"run": "running"}
    assert backend.asked == [True]
    assert backend.listeners() == 0


def test_a_run_that_fails_to_start_is_an_error_with_its_text(
    connected: ctl.Client, run_backend: Callable[..., _RunBackend]
) -> None:
    backend = run_backend(fail="No vJoy device 3.")
    with pytest.raises(
        ctl.CallError, match=r"^Could not run the profile: No vJoy device 3\.$"
    ):
        _off_main(lambda: connected.call("run.start"))
    assert backend.listeners() == 0


def test_run_stop_without_an_answer_is_an_error_not_a_state(
    connected: ctl.Client,
    run_backend: Callable[..., _RunBackend],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(control_api, "RUN_WAIT_S", 0.5)
    backend = run_backend(answer=False)
    backend.gremlinActive = True
    with pytest.raises(ctl.CallError, match="didn't stop within 0.5 s"):
        _off_main(lambda: connected.call("run.stop"))
    assert backend.listeners() == 0


def test_run_start_and_stop_in_the_wanted_state_answer_at_once(
    connected: ctl.Client, run_backend: Callable[..., _RunBackend]
) -> None:
    backend = run_backend(answer=False)
    assert _off_main(lambda: connected.call("run.stop")) == {"run": "stopped"}
    backend.gremlinActive = True
    assert _off_main(lambda: connected.call("run.start")) == {"run": "running"}
    assert backend.asked == []
    assert backend.listeners() == 0


def test_run_start_inline_answers_from_the_finished_run(
    connected: ctl.Client,
    run_backend: Callable[..., _RunBackend],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inline (no input thread): the Run is done when activate_gremlin
    returns; the answer reads it, no wait."""
    from gremlin import input_thread

    monkeypatch.setattr(input_thread, "is_running", lambda: False)
    backend = run_backend(answer=False)

    def at_once(activate: bool) -> None:
        backend.asked.append(activate)
        backend.gremlinActive = activate

    backend.activate_gremlin = at_once  # type: ignore[method-assign]
    assert _off_main(lambda: connected.call("run.start")) == {"run": "running"}
    assert _off_main(lambda: connected.call("run.stop")) == {"run": "stopped"}
    assert backend.asked == [True, False]
    assert backend.listeners() == 0


def test_backend_says_when_it_has_handled_the_runs_answer(qapp: object) -> None:
    """Backend's handlers update the status, then emit runStartHandled /
    runStopHandled (what run.start / run.stop wait on), also for a Stop
    answered while a later Run is still starting."""
    from gremlin.ui.backend import Backend

    class _Runner:
        def is_running(self) -> bool:
            return False

    class _Stub(QtCore.QObject):
        runStartHandled = QtCore.Signal(bool, str)
        runStopHandled = QtCore.Signal()
        activityChanged = QtCore.Signal()

        def __init__(self) -> None:
            super().__init__()
            self.runner = _Runner()
            self._starting = True
            self._wanted_active = True

    stub = _Stub()
    seen: list[tuple] = []
    stub.runStartHandled.connect(lambda ok, error: seen.append(("start", ok, error)))
    stub.runStopHandled.connect(lambda: seen.append(("stop",)))
    Backend.klass._on_run_stopped(stub)  # type: ignore[arg-type]  # noqa: SLF001 - starting
    Backend.klass._on_run_started(stub, False, "It failed.")  # type: ignore[arg-type]  # noqa: SLF001
    assert stub._starting is False  # noqa: SLF001
    Backend.klass._on_run_stopped(stub)  # type: ignore[arg-type]  # noqa: SLF001
    assert seen == [("stop",), ("start", False, "It failed."), ("stop",)]


# --- research batch: codes, declared arguments, one deadline (S25-S30) ------------


@pytest.fixture
def switched_on(qapp: object, monkeypatch: pytest.MonkeyPatch) -> None:
    """dispatch() with the switch on, without opening a pipe."""
    monkeypatch.setattr(control_api, "allowed", lambda: True)


def _throwaway(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    handler: Callable[[dict], Any],
    **kw: Any,  # noqa: ANN401 - register's keywords
) -> None:
    # Register into a copy: registering first and then swapping in a copy
    # left the call in the real list, where it failed the help test (no
    # summary) whenever that ran later (CI run 45282828410).
    monkeypatch.setattr(control_api, "_calls", dict(control_api._calls))  # noqa: SLF001
    control_api.register(name, handler, **kw)


def test_each_kind_of_error_answers_its_code(
    switched_on: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S25: the answer's code, beside its text, for every kind."""

    def refuse(_args: dict) -> None:
        raise control_api.CallError("No window called 'X'.", "not_found")

    def broken(_args: dict) -> None:
        raise ZeroDivisionError("boom")

    _throwaway(monkeypatch, "test.refuse", refuse)
    _throwaway(monkeypatch, "test.broken", broken)
    _throwaway(monkeypatch, "test.quick", lambda _a: 1, timeout_s=0.2)
    assert control_api.dispatch("no.such.call")["code"] == "unknown_call"
    assert control_api.dispatch("state", {"x": 1})["code"] == "bad_args"
    assert control_api.dispatch("test.refuse")["code"] == "not_found"
    assert control_api.dispatch("test.broken")["code"] == "failed"
    assert control_api.dispatch("test.quick", [])["code"] == "bad_args"  # type: ignore[arg-type]
    control_api._busy.acquire()  # noqa: SLF001
    try:
        busy = control_api.dispatch("test.quick")
    finally:
        control_api._busy.release()  # noqa: SLF001
    assert busy == {
        "ok": False,
        "error": "Busy with another call; try again.",
        "code": "busy",
    }
    big = json.loads(
        control_api.handle_bytes(b" " * (control_api.MAX_REQUEST_BYTES + 1))
    )
    assert big["code"] == "too_large"
    assert json.loads(control_api.handle_bytes(b"{nope"))["code"] == "bad_args"
    monkeypatch.setattr(control_api, "allowed", lambda: False)
    assert control_api.dispatch("test.quick")["code"] == "refused"
    assert set(control_api.CODES) == {
        "bad_args",
        "unknown_call",
        "not_found",
        "not_ready",
        "refused",
        "busy",
        "timeout",
        "too_large",
        "failed",
    }


def test_an_unknown_argument_is_refused_before_the_call_runs(switched_on: None) -> None:
    """S26: a misspelled key used to turn all of tracing on."""
    from gremlin import trace

    before = trace.enabled()
    reply = control_api.dispatch("trace.on", {"categroy": "osc"})
    assert reply == {
        "ok": False,
        "error": "trace.on has no argument 'categroy' (it takes: category).",
        "code": "bad_args",
    }
    assert trace.enabled() == before


def test_a_missing_argument_is_refused(switched_on: None) -> None:
    reply = control_api.dispatch("profile.load", {})
    assert reply["code"] == "bad_args"
    assert reply["error"].startswith("profile.load needs path")
    assert reply["error"].endswith(".")


def test_arguments_out_of_range_or_of_the_wrong_type_are_refused(
    switched_on: None,
) -> None:
    for args in ({"lines": 0}, {"lines": 2001}, {"lines": "x"}, {"which": "System"}):
        reply = control_api.dispatch("log", args)
        assert reply["code"] == "bad_args", (args, reply)
        assert reply["error"].startswith("log: '"), reply
    assert control_api.dispatch("log", {"lines": 3})["ok"] is True


def test_help_gives_each_calls_arguments(switched_on: None) -> None:
    rows = {r["name"]: r for r in control_api.dispatch("help")["result"]}
    assert rows["state"]["args"] == {}
    lines = rows["log"]["args"]["lines"]
    assert (lines["type"], lines["min"], lines["max"]) == ("int", 1, 2000)
    assert rows["log"]["args"]["which"]["choices"] == ["system", "trace"]
    assert rows["profile.load"]["args"]["path"]["required"] is True
    assert set(rows["option.set"]["args"]) == {"key", "value"}


def test_trace_on_with_an_unknown_category_lists_them(switched_on: None) -> None:
    reply = control_api.dispatch("trace.on", {"category": "nope"})
    assert reply["code"] == "bad_args"
    assert "'nope'" in reply["error"] and "hidhide" in reply["error"]


def test_a_timed_out_main_thread_job_never_runs_later(
    switched_on: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S28: the main thread was busy past the limit; the job is dropped."""
    ran: list[str] = []
    _throwaway(
        monkeypatch,
        "test.late",
        lambda _a: ran.append("ran"),
        main_thread=True,
        timeout_s=0.2,
    )
    box: dict[str, dict] = {}
    worker = threading.Thread(
        target=lambda: box.setdefault("reply", control_api.dispatch("test.late")),
        daemon=True,
    )
    worker.start()
    worker.join(5.0)  # this (main) thread runs no events meanwhile
    assert not worker.is_alive()
    _pump(100)  # the queued job's turn comes: it must not run
    assert ran == []
    assert box["reply"]["code"] == "timeout"
    assert box["reply"]["error"] == "test.late took over 0.2 s and was not done."


def test_one_deadline_covers_the_busy_wait_and_the_call(
    switched_on: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S9: time spent waiting for a busy API comes off the call's limit."""
    seen: list[float] = []
    _throwaway(
        monkeypatch,
        "test.left",
        lambda _a: seen.append(control_api.time_left()),
        timeout_s=1.0,
    )
    control_api._busy.acquire()  # noqa: SLF001
    releaser = threading.Timer(0.4, control_api._busy.release)  # noqa: SLF001
    releaser.start()
    try:
        assert control_api.dispatch("test.left")["ok"] is True
    finally:
        releaser.join()
    assert seen and seen[0] <= 0.65, seen


def test_a_request_over_1_mb_is_answered_too_large(
    connected: ctl.Client, caplog: pytest.LogCaptureFixture
) -> None:
    """S9: through the real pipe it used to be dropped without a word."""
    with caplog.at_level(logging.WARNING, logger="system"):
        with pytest.raises(ctl.CallError, match="over 1 MB") as caught:
            _off_main(lambda: connected.call("hello", pad="x" * (1100 * 1024)))
    assert getattr(caught.value, "code", "too_large") == "too_large"
    assert any("over 1 MB" in r.getMessage() for r in caplog.records)
    assert _off_main(lambda: connected.call("hello"))["version"] == 1


def test_profile_load_refuses_a_relative_path(switched_on: None) -> None:
    """S30."""
    reply = control_api.dispatch("profile.load", {"path": "my profile.xml"})
    assert reply == {"ok": False, "error": "Give the full path.", "code": "bad_args"}


def test_a_profile_that_did_not_open_says_why_and_what_is_open(
    switched_on: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "broken.xml"
    target.write_text("<not a profile", encoding="utf-8")
    before = str(tmp_path / "before.xml")

    class _Backend:
        profileContainsUnsavedChanges = False

        def profilePath(self) -> str:
            return before

        def loadProfile(self, _path: str) -> None:
            pass  # failed: the one before is read again

        def last_load_problem(self) -> str:
            return "not well-formed (invalid token): line 1, column 0"

    monkeypatch.setattr(control_api, "_backend", lambda: _Backend())
    reply = control_api.dispatch("profile.load", {"path": str(target)})
    assert reply["code"] == "failed"
    assert reply["error"] == (
        f"The profile '{target}' didn't open: not well-formed (invalid token): "
        f"line 1, column 0; '{before}' is still open."
    )


def test_devices_survives_one_bad_device(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace

    from gremlin import device_initialization
    from gremlin.modules import store

    class _Broken:
        name = "Broken"
        device_guid = "{33333333-3333-3333-3333-333333333333}"
        is_virtual = False

        @property
        def axis_count(self) -> int:
            raise OSError("device went away")

    good = SimpleNamespace(
        name="Stick",
        device_guid="{11111111-1111-1111-1111-111111111111}",
        is_virtual=False,
        vjoy_id=0,
        axis_count=3,
        button_count=12,
        hat_count=1,
    )
    monkeypatch.setattr(
        device_initialization, "joystick_devices", lambda: [_Broken(), good]
    )
    monkeypatch.setattr(store, "known_devices", lambda: [{"guid": None}, 5])
    rows = control_api._devices({})  # noqa: SLF001
    assert [r["name"] for r in rows] == ["Stick"]


def _setting_of(kind: str) -> str:
    """An Options setting of that kind (text: plain text, a path or a
    choice, which all take text only)."""
    from gremlin.types import PropertyType

    wanted = {
        "int": (PropertyType.Int,),
        "float": (PropertyType.Float,),
        "text": (PropertyType.String, PropertyType.Path, PropertyType.Selection),
    }[kind]
    cfg = Configuration()
    for key in control_api._option_keys():  # noqa: SLF001
        if cfg.data_type(*key) in wanted:
            return "/".join(key)
    pytest.skip(f"no {kind} setting in Options")


@pytest.mark.parametrize(
    ("kind", "value"),
    [
        ("int", 1.7),
        ("int", "2.5"),
        ("float", "nan"),
        ("float", "inf"),
        ("text", 5),
        ("text", ["a"]),
    ],
)
def test_option_set_refuses_a_value_of_the_wrong_kind(
    switched_on: None, kind: str, value: object
) -> None:
    key = _setting_of(kind)
    cfg = Configuration()
    parts = tuple(key.split("/"))
    before = cfg.value(*parts)
    reply = control_api.dispatch("option.set", {"key": key, "value": value})
    assert reply["code"] == "bad_args", reply
    assert reply["error"].startswith("'") and reply["error"].endswith("."), reply
    assert cfg.value(*parts) == before
