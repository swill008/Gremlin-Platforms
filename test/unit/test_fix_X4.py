# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Final phase fix round, agent X4: modes, scripts and Backend."""

from __future__ import annotations

import builtins
import pathlib
import sys
import threading
import time
import types
from typing import Any, cast
from xml.etree import ElementTree

import pytest

from gremlin import code_runner, event_handler, profile, user_script, util

# --- D-04-ALPHA-CASEFOLD, D-04-LAST-ACTIVE (04 S52): the first listed mode
# (Last Active with no record) ignores capitals ------------------------------


def test_first_mode_is_alphabetical_ignoring_capitals() -> None:
    from gremlin import mode_manager

    p = profile.Profile()
    for name in ("Bravo", "alpha"):
        p.modes.add_mode(name)
    p.modes.set_parent("alpha", "Bravo")
    # "Default" < "alpha" by code point; ignoring capitals, alpha comes first,
    # nested or not.
    assert p.settings.startup_mode == "Last Active"
    assert mode_manager.resolve_start_mode(p) == "alpha"


# --- D-04-Q13-RUNLIMIT (04 Q13, S87): Run's reload has the time limit -----


@pytest.fixture
def gate() -> types.SimpleNamespace:
    """block: set means the test script waits for release at its next run."""
    state = types.SimpleNamespace(block=threading.Event(), release=threading.Event())
    builtins._x4_gate = state  # type: ignore[attr-defined]
    yield state
    state.release.set()
    del builtins._x4_gate  # type: ignore[attr-defined]


def _script_file(tmp_path: pathlib.Path, name: str, waits: bool) -> pathlib.Path:
    path = tmp_path / f"{name}.py"
    wait = (
        "if builtins._x4_gate.block.is_set():\n"
        "    builtins._x4_gate.release.wait(30)\n"
        if waits
        else ""
    )
    path.write_text(
        "import builtins\n"
        "import gremlin.user_script as us\n"
        "flag = us.BoolVariable('Flag', 'a flag', True, False)\n"
        "@us.periodic(10.0)\n"
        f"def tick_{name}():\n"
        "    pass\n"
        f"{wait}",
        encoding="utf-8",
    )
    return path


def _periodic_names() -> list[str]:
    return sorted(
        cb.__name__ for cb in (e[2] for e in user_script.periodic_registry._queue)
    )


def test_run_reload_of_a_script_that_waits_is_failed_and_the_rest_runs(
    tmp_path: pathlib.Path,
    gate: types.SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(user_script, "TOP_LEVEL_TIME_LIMIT", 0.3)
    monkeypatch.setattr(sys, "path", list(sys.path))
    waits = user_script.Script(_script_file(tmp_path, "waits", True), "Waits")
    other = user_script.Script(_script_file(tmp_path, "other", False), "Other")
    assert waits.load_error == "" and other.load_error == ""
    runner = types.SimpleNamespace(
        _sys_path=None,
        _profile=types.SimpleNamespace(
            scripts=types.SimpleNamespace(scripts=[waits, other])
        ),
    )
    gate.block.set()
    # Old code: the reload waits on the main thread; let it go after 3 s.
    releaser = threading.Timer(3.0, gate.release.set)
    releaser.start()
    try:
        started = time.monotonic()
        code_runner.CodeRunner._setup_user_scripts(cast(Any, runner))
        elapsed = time.monotonic() - started
    finally:
        releaser.cancel()
        user_script.periodic_registry.clear()
    assert elapsed < 2.0
    assert waits.load_error == (
        "Its top-level code did not finish within 0.3 s (it may loop or wait)"
    )
    assert other.load_error == ""


def test_callbacks_of_top_level_code_that_timed_out_are_not_registered(
    tmp_path: pathlib.Path,
    gate: types.SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(user_script, "TOP_LEVEL_TIME_LIMIT", 0.3)
    script = user_script.Script(_script_file(tmp_path, "late", True), "Late")
    user_script.periodic_registry.clear()
    gate.block.set()
    # Old code: the reload waits on the main thread; let it go after 3 s.
    releaser = threading.Timer(3.0, gate.release.set)
    releaser.start()
    try:
        assert script.reload() is False
        releaser.cancel()
        # The code finishes after all: what it registered stays out.
        gate.release.set()
        deadline = time.monotonic() + 3.0
        while (
            any(t.name.endswith("script Late") for t in threading.enumerate())
            and time.monotonic() < deadline
        ):
            time.sleep(0.02)
        assert user_script.periodic_registry._registry == {}
    finally:
        user_script.periodic_registry.clear()


def test_callbacks_of_top_level_code_keep_their_script(
    tmp_path: pathlib.Path,
) -> None:
    script = user_script.Script(_script_file(tmp_path, "kept", False), "Kept")
    user_script.periodic_registry.clear()
    try:
        assert script.reload() is True
        keys = list(user_script.periodic_registry._registry)
        assert len(keys) == 1
        assert keys[0] == (script.id, "tick_kept")
    finally:
        user_script.periodic_registry.clear()


# --- D-04-S86-RELATIVE (04 S86): relative path inside the scripts folder --


def _saved_path(node: ElementTree.Element) -> str:
    for prop in node.iter("property"):
        if prop.findtext("name") == "path":
            return prop.findtext("value") or ""
    raise AssertionError("no path")


def test_script_paths_save_relative_inside_the_scripts_folder(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = tmp_path / "scripts"
    (folder / "sub").mkdir(parents=True)
    monkeypatch.setattr(util, "scripts_dir", lambda: folder)
    inside = user_script.Script(_script_file(folder / "sub", "inside", False), "In")
    outside = user_script.Script(_script_file(tmp_path, "outside", False), "Out")
    try:
        inside.variables["Flag"].value = True
        node_in = inside.to_xml()
        node_out = outside.to_xml()
        assert pathlib.Path(_saved_path(node_in)) == pathlib.Path("sub/inside.py")
        assert pathlib.Path(_saved_path(node_out)) == tmp_path / "outside.py"

        for node, original in ((node_in, inside), (node_out, outside)):
            loaded = user_script.Script()
            loaded.from_xml(node)
            assert loaded.path == original.path
            assert loaded.load_error == ""
        loaded = user_script.Script()
        loaded.from_xml(node_in)
        assert loaded.variables["Flag"].value is True
    finally:
        user_script.periodic_registry.clear()
        user_script.callback_registry.clear()


# --- Backend: its activity link goes with it -------------------------------


def test_is_active_after_a_backend_is_deleted_raises_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import shiboken6

    from gremlin import shared_state
    from gremlin.ui import backend

    monkeypatch.setattr(shared_state, "current_profile", shared_state.current_profile)
    source = event_handler.EventHandler()
    instance = backend.Backend.klass(cast(Any, None))
    received: list[bool] = []
    instance.activityChanged.connect(lambda: received.append(True))
    source.is_active.emit(True)
    assert received == [True]
    shiboken6.delete(instance)
    assert not shiboken6.isValid(instance)
    del instance
    # A slot's error goes to sys.excepthook, not to the sender.
    errors: list[BaseException] = []
    monkeypatch.setattr(sys, "excepthook", lambda _t, e, _tb: errors.append(e))
    source.is_active.emit(False)  # old code: "Signal source has been deleted"
    assert errors == []
