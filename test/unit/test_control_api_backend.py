# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Backend's part of the control API (claude/program-map/13-control-api.md
S17, S25-S27): "commands" and "command.run" through control_api.dispatch
(the path a pipe request takes, from a worker thread while this main thread
runs events), with Main.qml's command bridge as real JavaScript functions;
and the public reasons a load or save failed (last_load_problem,
last_save_problem) that profile.load / profile.save answer with.
"""

from __future__ import annotations

import re
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from PySide6 import QtCore, QtQml

from gremlin import control_api
from gremlin.ui.backend import Backend

_QML = Path(__file__).resolve().parents[2] / "qml"

# As Main.qml's _apiCommandList / _apiRunCommand: view.home runs,
# view.off can't be used now, tools.boom throws.
_LIST_JS = """(function() {
    return [
        { id: "view.home", text: "Home", group: "View" },
        { id: "tools.options", text: "Options", group: "Tools", window: true },
        { id: "view.off", text: "Off", group: "View" },
        { id: "tools.boom", text: "Boom", group: "Tools" }
    ]
})"""
_RUN_JS = """(function(id) {
    if (id === "tools.boom")
        throw new Error("kaput");
    return id === "view.home";
})"""


def _off_main(fn: Callable[[], Any], timeout: float = 20.0) -> Any:  # noqa: ANN401
    """Runs fn on a worker thread (as the API's listener does) while this
    main thread runs events."""
    box: dict[str, Any] = {}

    def work() -> None:
        try:
            box["value"] = fn()
        except BaseException as e:  # noqa: BLE001 - handed back
            box["error"] = e

    thread = threading.Thread(target=work, name="test-api-backend", daemon=True)
    thread.start()
    deadline = time.monotonic() + timeout
    while thread.is_alive() and time.monotonic() < deadline:
        QtCore.QCoreApplication.processEvents()
        time.sleep(0.005)
    assert not thread.is_alive(), f"no answer within {timeout} s"
    if "error" in box:
        raise box["error"]
    return box.get("value")


def _fake_backend() -> SimpleNamespace:
    """Backend's own API methods on a plain object (no main window)."""
    fake = SimpleNamespace(_command_list_fn=None, _command_run_fn=None)
    for name in ("_command_bridge", "command_list", "run_command_id",
                 "last_load_problem", "last_save_problem"):
        method = getattr(Backend.klass, name)  # type: ignore[attr-defined]
        setattr(fake, name, method.__get__(fake))
    return fake


@pytest.fixture
def engine(qapp: object) -> QtQml.QJSEngine:
    return QtQml.QJSEngine()


@pytest.fixture
def backend(monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    """The switch on; commands / command.run registered from a fake
    Backend, the earlier entries put back after."""
    monkeypatch.setattr(control_api, "allowed", lambda: True)
    fake = _fake_backend()
    with control_api._calls_lock:  # noqa: SLF001
        kept = {n: control_api._calls.get(n) for n in ("commands", "command.run")}  # noqa: SLF001
    Backend.klass.register_api_calls(fake, control_api)  # type: ignore[attr-defined]
    try:
        yield fake
    finally:
        with control_api._calls_lock:  # noqa: SLF001
            for name, entry in kept.items():
                if entry is None:
                    control_api._calls.pop(name, None)  # noqa: SLF001
                else:
                    control_api._calls[name] = entry  # noqa: SLF001


def _bridge(fake: SimpleNamespace, engine: QtQml.QJSEngine) -> None:
    fake._command_list_fn = engine.evaluate(_LIST_JS)
    fake._command_run_fn = engine.evaluate(_RUN_JS)
    assert fake._command_list_fn.isCallable()
    assert fake._command_run_fn.isCallable()


def _call(name: str, **args: object) -> dict:
    return _off_main(lambda: control_api.dispatch(name, dict(args)))


def test_command_run_without_an_id_is_bad_args(
    backend: SimpleNamespace, engine: QtQml.QJSEngine
) -> None:
    _bridge(backend, engine)
    for answer in (_call("command.run"), _call("command.run", id="  ")):
        assert answer["ok"] is False
        assert answer["code"] == "bad_args"
        assert answer["error"].startswith("command.run needs id")
        assert answer["error"].endswith(".")


def test_command_run_with_an_unknown_id_is_not_found(
    backend: SimpleNamespace, engine: QtQml.QJSEngine
) -> None:
    _bridge(backend, engine)
    answer = _call("command.run", id="no.such")
    assert answer == {
        "ok": False,
        "error": "No command called 'no.such'.",
        "code": "not_found",
    }


def test_command_run_known_commands_answer_ran(
    backend: SimpleNamespace, engine: QtQml.QJSEngine
) -> None:
    """S17: a known command that can't be used now answers ran false."""
    _bridge(backend, engine)
    assert _call("command.run", id="view.home") == {"ok": True, "result": {"ran": True}}
    assert _call("command.run", id="view.off") == {"ok": True, "result": {"ran": False}}


def test_a_command_that_throws_in_qml_fails_with_its_text(
    backend: SimpleNamespace, engine: QtQml.QJSEngine
) -> None:
    _bridge(backend, engine)
    answer = _call("command.run", id="tools.boom")
    assert answer["ok"] is False
    assert answer["code"] == "failed"
    assert "'tools.boom'" in answer["error"]
    assert "kaput" in answer["error"]
    assert answer["error"].endswith(".") and not answer["error"].endswith("..")


def test_commands_before_the_bridge_is_ready_are_not_ready(
    backend: SimpleNamespace,
) -> None:
    for answer in (_call("commands"), _call("command.run", id="view.home")):
        assert answer == {
            "ok": False,
            "error": "The menu commands aren't ready yet.",
            "code": "not_ready",
        }


def test_commands_lists_the_bridge_commands(
    backend: SimpleNamespace, engine: QtQml.QJSEngine
) -> None:
    _bridge(backend, engine)
    answer = _call("commands")
    assert answer["ok"] is True
    assert [row["id"] for row in answer["result"]] == [
        "view.home", "tools.options", "view.off", "tools.boom",
    ]
    windows = {row["id"]: row["window"] for row in answer["result"]}
    assert windows == {
        "view.home": False, "tools.options": True, "view.off": False,
        "tools.boom": False,
    }


def test_command_run_declares_its_id(backend: SimpleNamespace) -> None:
    """S26: help and the MCP schema come from the declared arguments."""
    entry = next(c for c in control_api.calls() if c["name"] == "command.run")
    assert entry["args"]["id"]["type"] == "str"
    assert entry["args"]["id"]["required"] is True
    assert entry["args"]["id"]["help"]
    commands = next(c for c in control_api.calls() if c["name"] == "commands")
    assert commands["args"] == {}


def test_last_save_problem_keeps_why_the_write_failed(tmp_path: Path) -> None:
    """The profile's own write raised: the reason is kept for the API,
    and saveProblem stays "" so the save dialogs keep their own words."""

    def refuse(_path: object) -> None:
        raise PermissionError("Access is denied")

    fake = _fake_backend()
    fake.profile = SimpleNamespace(to_xml=refuse, fpath=None)
    target = tmp_path / "p.xml"
    assert Backend.klass.saveProfile(fake, target.as_uri()) is False  # type: ignore[attr-defined]
    assert fake.last_save_problem() == "The profile wasn't saved: Access is denied."
    assert Backend.klass.saveProblem(fake) == ""  # type: ignore[attr-defined]


def test_last_load_problem_says_why_the_load_failed(tmp_path: Path) -> None:
    fake = _fake_backend()
    missing = tmp_path / "gone.xml"
    assert Backend.klass._load_profile(fake, str(missing), report=False) is False  # type: ignore[attr-defined]  # noqa: SLF001
    assert fake.last_load_problem() == "The file isn't there any more."
    fake._load_problem = ""
    assert fake.last_load_problem() == ""


# --- each command says whether it opens a window (13 S29) --------------------

# What makes a window of its own in Main.qml and its code-behind.
_MAKES_WINDOW = re.compile(
    r"Helpers\.createComponent\(|Qt\.createComponent\(|DeviceLibraryOpen\.openDeviceLibrary\("
)


def _command_specs() -> dict[str, str]:
    """main_commands.js: each command's id to its spec text."""
    text = (_QML / "main_commands.js").read_text(encoding="utf-8")
    parts = re.split(r'\n\s*\{ id: "', text)[1:]
    return {part.split('"', 1)[0]: part for part in parts}


def _main_functions() -> dict[str, str]:
    """Main.qml's functions: name to body text (to the next function)."""
    text = (_QML / "Main.qml").read_text(encoding="utf-8")
    found = list(re.finditer(r"\n\s*function (\w+)\(", text))
    ends = [match.start() for match in found[1:]] + [len(text)]
    return {
        match.group(1): text[match.end(): end]
        for match, end in zip(found, ends, strict=True)
    }


def _opens_window(spec: str, functions: dict[str, str]) -> bool:
    """The command's run makes a window, itself or through one of
    Main.qml's functions it calls (one level, as the menus call them)."""
    run = spec.split("run:", 1)[1] if "run:" in spec else ""
    if _MAKES_WINDOW.search(run):
        return True
    for name in re.findall(r"\b(\w+)\(", run):
        if name in ("openTool", "openToolWith"):
            return True
        body = functions.get(name)
        if body is not None and _MAKES_WINDOW.search(body):
            return True
    return False


def test_every_command_that_opens_a_window_says_so() -> None:
    """Guard: a main-window command whose run opens a window of its own has
    window: true, and one that doesn't (a page of the main window, a file
    dialog, another program) hasn't."""
    functions = _main_functions()
    specs = _command_specs()
    assert len(specs) > 40
    wrong = {
        command_id: _opens_window(spec, functions)
        for command_id, spec in specs.items()
        if _opens_window(spec, functions) != ("window: true" in spec)
    }
    assert wrong == {}, f"window: true missing (True) or not wanted (False): {wrong}"


def test_known_window_commands_are_flagged_and_pages_are_not() -> None:
    specs = _command_specs()
    for command_id in ("tools.options", "tools.search", "tools.deviceLibrary",
                       "tools.configureInput", "help.about", "debug.liveLog",
                       "tools.profileSettings", "tools.scripts"):  # 04 S96
        assert "window: true" in specs[command_id], command_id
    # The old main-window pages are gone, with no old ids kept.
    assert "view.settings" not in specs and "view.scripts" not in specs
    for command_id in ("view.home",
                       "tools.logical", "tools.oscMonitor", "tools.inputTester",
                       "file.load", "view.palette"):
        assert "window: true" not in specs[command_id], command_id
