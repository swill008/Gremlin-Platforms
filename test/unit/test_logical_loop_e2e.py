# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""A loop between Logical Device controls is stopped (06 S94, D-06-LD-LOOP).

Real path: the profile runs on the real CodeRunner; Map to Logical Device
and the macro Logical Device step emit on the real EventListener, the real
InputModuleRuntime passes the event on and the real EventHandler runs the
control's actions. Only the hardware is fake (the unit conftest's fake
driver, hooks off) and the drivers, OSC, sound and speech are stand-ins.

Each case runs in its own pytest process (all of them at once), with a hard
timeout: a loop that recurses or runs away on the code under test fails
that case quickly instead of stalling the suite. The child writes what it
saw (events per control, user-log warnings, notices, how long each input
took) to a JSON file; the tests here check it.

Hop rule: an input starts a chain; each control the chain drives is one
hop; at most MAX_HOPS (8) hops, so at most 1 + 8 events per input on the
controls of the loop. A little slack is allowed for the drop point.
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import subprocess
import sys
import time
from typing import Any

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
CASE_ENV = "LD_LOOP_E2E_CASE"
OUT_ENV = "LD_LOOP_E2E_OUT"
CHILD_TIMEOUT = 90  # s: a child still running then has hung
MAX_HOPS = 8
# Events on the loop's controls one input may cause: the input itself plus
# MAX_HOPS hops, plus one for where the drop is counted.
PER_INPUT = 1 + MAX_HOPS + 1

CASES = (
    "self_button",
    "self_axis",
    "self_hat",
    "a_b_a",
    "macro_self",
    "relative_self_xml",
    "chain_ok",
)


# +-------------------------------------------------------------------------
# | Parent: start every case at once, read the results


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> dict[str, dict]:
    if os.environ.get(CASE_ENV):
        return {}
    folder = tmp_path_factory.mktemp("ldloop")
    started: dict[str, tuple[subprocess.Popen, pathlib.Path, pathlib.Path, Any]] = {}
    for case in CASES:
        out = folder / f"{case}.json"
        log = folder / f"{case}.log"
        home = folder / f"home-{case}"
        home.mkdir()
        env = dict(
            os.environ,
            **{CASE_ENV: case, OUT_ENV: str(out)},
            USERPROFILE=str(home),
            QT_QPA_PLATFORM="offscreen",
            PYTHONUNBUFFERED="1",
        )
        env.pop("GREMLIN_VALIDATE_REPORT", None)
        # To a file, not a pipe (a full pipe would block the child).
        handle = log.open("w", encoding="utf-8")
        process = subprocess.Popen(
            [
                sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                "-p", "no:randomly",
                f"{pathlib.Path(__file__).relative_to(ROOT).as_posix()}::test_child_case",
            ],
            cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT,
        )
        started[case] = (process, out, log, handle)
    got: dict[str, dict] = {}
    deadline = time.monotonic() + CHILD_TIMEOUT
    for case, (process, out, log, handle) in started.items():
        try:
            code = process.wait(timeout=max(1.0, deadline - time.monotonic()))
            timed_out = False
        except subprocess.TimeoutExpired:
            process.kill()
            code = process.wait(timeout=30)
            timed_out = True
        handle.close()
        text = log.read_text(encoding="utf-8", errors="replace")
        data: dict = {}
        if out.is_file():
            data = json.loads(out.read_text(encoding="utf-8"))
        data["_exit"] = code
        data["_timed_out"] = timed_out
        data["_log"] = text[-1500:]
        got[case] = data
    return got


def _case(results: dict[str, dict], name: str) -> dict:
    data = results[name]
    where = f"{name}: exit {data['_exit']}, child output:\n{data['_log']}"
    if data["_timed_out"]:
        pytest.fail(f"hung (killed after {CHILD_TIMEOUT} s) - {where}", pytrace=False)
    if "inputs" not in data:
        pytest.fail(f"the child gave no result (crashed?) - {where}", pytrace=False)
    assert data["_exit"] == 0, where
    return data


def _check_stopped(data: dict, controls: list[str], warnings: int = 1) -> None:
    """Every input stayed quick, each chain stopped within the hop limit,
    one user-log warning and one notice for the Run."""
    for step in data["inputs"]:
        assert step["seconds"] < 2.0, f"input took too long: {step}"
        total = sum(step["events"].get(c, 0) for c in controls)
        assert total <= PER_INPUT, f"chain didn't stop at {MAX_HOPS} hops: {step}"
    assert len(data["warnings"]) == warnings, data["warnings"]
    assert len(data["notices"]) == warnings, data["notices"]
    for text in data["warnings"] + data["notices"]:
        assert "loop" in text.lower(), text


def test_a_button_driving_itself_stops_and_says_so_once_per_run(
    results: dict[str, dict],
) -> None:
    """06 S94: Button 1 -> Button 1, pressed and released, two Runs."""
    data = _case(results, "self_button")
    _check_stopped(data, ["A"], warnings=2)  # one per Run
    assert data["per_run"] == [1, 1], data


def test_an_absolute_axis_driving_itself_stops(results: dict[str, dict]) -> None:
    """06 S94: Axis 1 -> Axis 1 (Absolute)."""
    _check_stopped(_case(results, "self_axis"), ["A"])


def test_a_hat_driving_itself_stops(results: dict[str, dict]) -> None:
    """06 S94: Hat 1 -> Hat 1."""
    _check_stopped(_case(results, "self_hat"), ["A"])


def test_a_to_b_to_a_stops(results: dict[str, dict]) -> None:
    """06 S94: Button 1 -> Button 2 -> Button 1."""
    _check_stopped(_case(results, "a_b_a"), ["A", "B"])


def test_a_macro_step_driving_its_own_control_stops(
    results: dict[str, dict],
) -> None:
    """06 S94: a Macro on Button 1 whose Logical Device step presses Button 1
    (queued: the step runs on the macro thread)."""
    data = _case(results, "macro_self")
    _check_stopped(data, ["A"])
    assert data["late_events"] == 0, f"still looping after 2 s: {data}"


def test_a_relative_axis_driving_itself_stops(results: dict[str, dict]) -> None:
    """06 S93/S94: a Relative self-target the picker can't offer, set in the
    profile file: the loop stops instead of running away."""
    data = _case(results, "relative_self_xml")
    assert data["loaded_target_is_self"], data
    assert data["late_events"] == 0, f"still running after 1.5 s: {data}"
    assert len(data["warnings"]) == 1, data["warnings"]
    assert len(data["notices"]) == 1, data["notices"]


def test_a_chain_without_a_loop_still_delivers(results: dict[str, dict]) -> None:
    """06 S94 (no false stop): Button 1 -> Button 2 and Axis 1 -> Axis 2."""
    data = _case(results, "chain_ok")
    assert data["warnings"] == [] and data["notices"] == [], data
    assert data["delivered"] == {
        "button": [True, False],
        "axis": [0.5],
    }, data


# +-------------------------------------------------------------------------
# | Child: one case on the real Run path


def test_child_case() -> None:
    case = os.environ.get(CASE_ENV)
    if not case:
        pytest.skip("runs only as a child of this file's tests")
    from PySide6 import QtCore

    # The unit tests run without an application; a child needs one so the
    # events the macro thread and the relative loop send (queued to the main
    # thread, as in the program) are delivered. Own process: nothing shared.
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    result = _Child().run(case)
    pathlib.Path(os.environ[OUT_ENV]).write_text(
        json.dumps(result, default=str), encoding="utf-8"
    )
    del app


class _Child:
    def __init__(self) -> None:
        from gremlin.logical_device import LogicalDevice
        from gremlin.profile import Profile

        self.ld = LogicalDevice()
        self.profile = Profile()
        self.names: dict[tuple, str] = {}
        self.events: dict[str, int] = {}
        self.timeline: list[tuple[float, str, Any]] = []
        self.warnings: list[str] = []
        self.notices: list[str] = []

    # --- building the profile ---------------------------------------------

    def control(self, name: str, kind: Any) -> Any:  # noqa: ANN401
        made = self.ld.create(kind)
        self.names[(made.type, made.id)] = name
        return made

    def map_to(
        self,
        src: Any,  # noqa: ANN401
        dst: Any,  # noqa: ANN401
        relative: bool = False,
    ) -> Any:  # noqa: ANN401
        from gremlin import plugin_manager
        from gremlin.types import AxisMode

        action = plugin_manager.PluginManager().create_instance(
            "Map to Logical Device", src.type
        )
        # Set directly: bypasses the editor's default and picker (S92/S93).
        action.logical_input_type = dst.type
        action.logical_input_id = dst.id
        if relative:
            action.axis_mode = AxisMode.Relative
        self._bind(src, action)
        return action

    def macro_on(self, src: Any, step_target: Any) -> None:  # noqa: ANN401
        from gremlin import macro, plugin_manager

        action = plugin_manager.PluginManager().create_instance("Macro", src.type)
        action.actions = [
            macro.LogicalDeviceAction(step_target.type, step_target.id, True)
        ]
        self._bind(src, action)

    def _bind(self, src: Any, action: Any) -> None:  # noqa: ANN401
        item = self.profile.get_input_item(
            self.ld.device_guid, src.type, src.id, "Default", create_if_missing=True
        )
        item.add_item_binding().root_action.insert_action(action, "children")

    # --- running ----------------------------------------------------------

    def _on_event(self, event: Any) -> None:  # noqa: ANN401
        if event.device_guid != self.ld.device_guid:
            return
        name = self.names.get((event.event_type, event.identifier), "?")
        self.events[name] = self.events.get(name, 0) + 1
        value = event.is_pressed if event.is_pressed is not None else event.value
        self.timeline.append((time.monotonic(), name, value))

    def _listen(self) -> None:
        from gremlin.modules.runtime import InputModuleRuntime
        from gremlin.signal import signal

        # Before the Run connects the handler: seen ahead of it, even when
        # the handler recurses.
        InputModuleRuntime().event.connect(self._on_event)
        signal.showNotification.connect(lambda *a: self.notices.append(" ".join(a)))
        signal.showError.connect(lambda *a: self.notices.append(" ".join(a)))
        owner = self

        class Catch(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                if record.levelno >= logging.WARNING and "loop" in (
                    record.getMessage().lower()
                ):
                    owner.warnings.append(record.getMessage())

        logging.getLogger("user").addHandler(Catch())

    def _start(self, profile: Any) -> Any:  # noqa: ANN401
        from unittest import mock

        from gremlin import code_runner, shared_state
        from gremlin.modules import output

        self._patches = []
        for name in ("output", "OscRuntime", "audio_player", "tts"):
            self._patches.append(mock.patch.object(code_runner, name, mock.MagicMock()))
        for name in ("write_vjoy", "write_vjoy_axis_linear", "release_vjoy_button",
                     "write_xbox"):
            self._patches.append(mock.patch.object(output, name, mock.MagicMock()))
        for p in self._patches:
            p.start()
        shared_state.current_profile = profile
        run = code_runner.CodeRunner()
        run._refresh_axes = lambda: None  # noqa: SLF001
        run.start(profile, "Default")
        return run

    def _stop(self, run: Any) -> None:  # noqa: ANN401
        from gremlin import event_handler, shared_state

        run.stop()
        shared_state.set_runtime_active(False)
        event_handler.EventHandler().resume()
        for p in reversed(self._patches):
            p.stop()

    def send(self, src: Any, value: Any, wait: float = 0.3) -> dict:  # noqa: ANN401
        """One input on a Logical control, as the Logical Device emits it."""
        from gremlin import event_handler, mode_manager
        from gremlin.types import InputType

        kw: dict[str, Any] = {}
        if src.type == InputType.JoystickButton:
            kw = {"is_pressed": bool(value), "raw_value": bool(value)}
            src.update(bool(value))
        elif src.type == InputType.JoystickHat:
            kw = {"value": value, "raw_value": value}
            src.update(value)
        else:
            kw = {"value": float(value), "raw_value": float(value)}
            src.update(float(value))
        before = dict(self.events)
        start = time.monotonic()
        event_handler.EventListener().joystick_event.emit(
            event_handler.Event(
                event_type=src.type,
                identifier=src.id,
                device_guid=self.ld.device_guid,
                mode=mode_manager.ModeManager().current.name,
                **kw,
            )
        )
        took = time.monotonic() - start
        _settle(wait)
        diff = {k: v - before.get(k, 0) for k, v in self.events.items()}
        return {"value": str(value), "seconds": took, "events": diff}

    # --- the cases --------------------------------------------------------

    def run(self, case: str) -> dict:
        from gremlin import shared_state
        from gremlin.types import HatDirection, InputType

        shared_state.current_profile = self.profile
        self._listen()
        out: dict[str, Any] = {"inputs": []}
        button, axis, hat = (
            InputType.JoystickButton,
            InputType.JoystickAxis,
            InputType.JoystickHat,
        )
        if case == "self_button":
            a = self.control("A", button)
            self.map_to(a, a)
            per_run = []
            for _ in range(2):
                seen = len(self.warnings)
                run = self._start(self.profile)
                try:
                    out["inputs"].append(self.send(a, True))
                    out["inputs"].append(self.send(a, False))
                finally:
                    self._stop(run)
                per_run.append(len(self.warnings) - seen)
            out["per_run"] = per_run
        elif case in ("self_axis", "self_hat"):
            kind = axis if case == "self_axis" else hat
            a = self.control("A", kind)
            self.map_to(a, a)
            run = self._start(self.profile)
            try:
                value = 0.5 if kind == axis else HatDirection.North
                out["inputs"].append(self.send(a, value))
            finally:
                self._stop(run)
        elif case == "a_b_a":
            a, b = self.control("A", button), self.control("B", button)
            self.map_to(a, b)
            self.map_to(b, a)
            run = self._start(self.profile)
            try:
                out["inputs"].append(self.send(a, True))
            finally:
                self._stop(run)
        elif case == "macro_self":
            a = self.control("A", button)
            self.macro_on(a, a)
            run = self._start(self.profile)
            try:
                step = self.send(a, True, wait=2.0)
                out["inputs"].append(step)
                mark = len(self.timeline)
                _settle(1.0)
                out["late_events"] = len(self.timeline) - mark
            finally:
                self._stop(run)
        elif case == "relative_self_xml":
            out.update(self._relative_from_file(axis))
        elif case == "chain_ok":
            a, b = self.control("A", button), self.control("B", button)
            ax, bx = self.control("AX", axis), self.control("BX", axis)
            self.map_to(a, b)
            self.map_to(ax, bx)
            run = self._start(self.profile)
            try:
                out["inputs"].append(self.send(a, True))
                out["inputs"].append(self.send(a, False))
                out["inputs"].append(self.send(ax, 0.5))
            finally:
                self._stop(run)
            out["delivered"] = {
                "button": [v for _t, n, v in self.timeline if n == "B"],
                "axis": [round(float(v), 3) for _t, n, v in self.timeline if n == "BX"],
            }
        out["warnings"] = self.warnings
        out["notices"] = self.notices
        out["events"] = self.events
        return out

    def _relative_from_file(self, axis: Any) -> dict:  # noqa: ANN401
        """Axis 1 -> Axis 1 Relative, saved and opened again (the picker
        can't make it: S93), then deflected once."""
        import tempfile

        from gremlin import shared_state
        from gremlin.profile import Profile

        a = self.control("A", axis)
        self.map_to(a, a, relative=True)
        path = pathlib.Path(tempfile.mkdtemp()) / "relative-self.xml"
        self.profile.to_xml(path)
        loaded = Profile()
        loaded.from_xml(path)
        shared_state.current_profile = loaded
        item = loaded.get_input_item(
            self.ld.device_guid, a.type, a.id, "Default", create_if_missing=False
        )
        action = item.action_sequences[0].root_action.get_actions()[0][0]
        is_self = (action.logical_input_type, action.logical_input_id) == (
            a.type,
            a.id,
        )
        out: dict[str, Any] = {"loaded_target_is_self": is_self, "inputs": []}
        run = self._start(loaded)
        try:
            step = self.send(a, 0.5, wait=1.5)
            out["inputs"].append(step)
            mark = len(self.timeline)
            _settle(1.0)
            out["late_events"] = len(self.timeline) - mark
        finally:
            self._stop(run)
        return out


def _settle(seconds: float) -> None:
    from PySide6 import QtCore

    end = time.monotonic() + seconds
    while True:
        QtCore.QCoreApplication.processEvents()
        QtCore.QCoreApplication.sendPostedEvents(None, 0)
        if time.monotonic() >= end:
            return
        time.sleep(0.01)

