# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Action editor matrix: Change Mode, Load Profile, Pause and Resume, Play
Sound, Text to Speech, Run Command and Description on every input kind and
surface they allow. For each: Add Action, every editor field set and read
back, save and reload, Undo/Redo on the panes, and a fake input through the
real runner with the effect recorded (05 S93-S97, S55).

Nothing real happens at Run: the mode switch, pause toggle, sound, speech,
program start and profile load are stand-ins that record the call.
"""

from __future__ import annotations

import contextlib
import pathlib
import sys
from collections.abc import Callable, Iterator
from typing import Any
from unittest import mock

import pytest
from PySide6 import QtCore

from test.unit.action_matrix.harness import (  # pyright: ignore[reportMissingImports]
    DEFAULT_RESULTS,
    Surface,
    actions,
    cases,
    open_editors,
    plugin,
    record,
)

TAGS = (
    "change-mode",
    "load-profile",
    "pause-resume",
    "play-sound",
    "text-to-speech",
    "run-command",
    "description",
)
# Written out: the plugins can't be listed before the settings are
# registered (a package fixture); test_the_seven_actions_are_listed checks
# this list against harness.cases().
_PANES = (Surface.CONFIG_PAGE, Surface.PANE_BUTTON_MAP, Surface.PANE_LOGICAL)
CASES = sorted(
    [(tag, "button", s) for tag in TAGS for s in _PANES]
    + [(tag, "key", Surface.PANE_KEYBOARD) for tag in TAGS]
    + [("description", k, s) for k in ("axis", "hat") for s in _PANES]
)
SHOTS = DEFAULT_RESULTS.parent / "shots"
TARGET = "Matrix"


def _module(tag: str) -> Any:  # noqa: ANN401
    return sys.modules[plugin(tag).__module__]


def _edits(tag: str, tmp: pathlib.Path) -> tuple[list[tuple[str, Any]], tuple]:
    """(every editor field with a changed value, a second edit for Undo)."""
    if tag == "change-mode":
        return [("changeType", "Temporary"), ("targetModes", [TARGET])], (
            "changeType",
            "Cycle",
        )
    if tag == "load-profile":
        return [("profile_filename", str(tmp / "matrix-target.xml"))], (
            "profile_filename",
            str(tmp / "other.xml"),
        )
    if tag == "pause-resume":
        return [("operation", "Toggle")], ("operation", "Resume")
    if tag == "play-sound":
        return [("soundFilename", str(tmp / "matrix.wav")), ("soundVolume", 73)], (
            "soundVolume",
            20,
        )
    if tag == "text-to-speech":
        return [
            ("text", "matrix ${current_mode}"),
            ("queueMode", "interrupt"),
            ("playbackRate", 0.5),
            ("playbackVolume", 0.25),
            ("playbackPitch", -0.5),
        ], ("text", "second")
    if tag == "run-command":
        return [
            ("executable", r"C:\matrix\fake.exe"),
            ("arguments", 'one "two three"'),
        ], ("arguments", "x")
    return [("description", "matrix note")], ("description", "second")


def _event_values(kind: str) -> Any:  # noqa: ANN401
    return {"axis": [0.5, -0.5], "hat": ["north", "center"]}.get(kind, [True, False])


@contextlib.contextmanager
def _stand_ins(tag: str, tmp: pathlib.Path) -> Iterator[dict]:
    """The outside world for the whole test: never real speech, sound, a
    program or a profile load."""
    from gremlin import tts

    got: dict[str, Any] = {}
    with contextlib.ExitStack() as stack:
        manager = mock.MagicMock()
        manager.return_value.speech_available.return_value = True
        stack.enter_context(mock.patch.object(tts, "TTSManager", manager))
        got["tts"] = manager
        player = mock.MagicMock()
        stack.enter_context(
            mock.patch.object(_module("play-sound"), "AudioPlayer", player)
        )
        got["audio"] = player
        start = mock.MagicMock(return_value=(True, 4242))
        stack.enter_context(mock.patch.object(QtCore.QProcess, "startDetached", start))
        got["process"] = start
        backend = mock.MagicMock()
        backend.Backend.return_value.profile.has_unsaved_changes.return_value = False
        stack.enter_context(
            mock.patch.object(_module("load-profile"), "backend", backend)
        )
        got["backend"] = backend
        # Files the editors point at, so the "missing file" branches don't run.
        (tmp / "matrix.wav").write_bytes(b"RIFF0000WAVE")
        from gremlin.profile import Profile

        Profile().to_xml(tmp / "matrix-target.xml")
        yield got


def _check_run(
    tag: str, kind: str, case: Any, got: dict, tmp: pathlib.Path  # noqa: ANN401
) -> tuple[bool | None, Any]:
    """Runs the case with a press and release (axis/hat: two values) and
    checks the effect the spec asks for."""
    from gremlin import event_handler, mode_manager, tts

    if tag == "change-mode":
        case.watch(mode_manager.ModeManager(), "switch_to")
    elif tag == "pause-resume":
        for name in ("pause", "resume", "toggle_active"):
            case.watch(event_handler.EventHandler(), name)
    sent = case.run(value=_event_values(kind))

    if tag == "change-mode":
        # Temporary: press enters the target mode as a temporary mode.
        calls = [(s[1].name, s[1].is_temporary) for s in sent if s[0] == "switch_to"]
        return calls == [(TARGET, True)], {"switch_to": calls}
    if tag == "pause-resume":
        calls = [s[0] for s in sent if s[0] in ("pause", "resume", "toggle_active")]
        # Run's start resumes the handler (code_runner start), then the
        # press toggles; the release does nothing (ActivateOnPress).
        return calls == ["resume", "toggle_active"], calls
    if tag == "play-sound":
        calls = got["audio"].return_value.enqueue.call_args_list
        want = [mock.call(str(tmp / "matrix.wav"), 73)]
        return calls == want, [str(c) for c in calls]
    if tag == "text-to-speech":
        calls = got["tts"].return_value.enqueue.call_args_list
        want = [
            mock.call(
                tts.TTSRequest(
                    text="matrix Default", rate=0.5, volume=0.25, pitch=-0.5
                ),
                tts.TTSQueueMode.Interrupt,
            )
        ]
        return calls == want, [str(c) for c in calls]
    if tag == "run-command":
        calls = got["process"].call_args_list
        want = [mock.call(r"C:\matrix\fake.exe", ["one", "two three"])]
        return calls == want, [str(c) for c in calls]
    if tag == "load-profile":
        # The load is a 0 s Run timer after the event (settled inside run()).
        calls = got["backend"].Backend.return_value.run_profile.call_args_list
        want = [mock.call(str(tmp / "matrix-target.xml"))]
        return calls == want, [str(c) for c in calls]
    # Description does nothing at Run.
    return sent == [], sent


def _reset(got: dict) -> None:
    for m in got.values():
        m.reset_mock(return_value=False, side_effect=False)


def test_the_seven_actions_are_listed() -> None:
    kinds = dict(actions())
    for tag in TAGS:
        assert tag in kinds, tag
    assert sorted(c for c in cases() if c[0] in TAGS) == CASES


@pytest.mark.parametrize(("tag", "kind", "surface"), CASES)
def test_misc_action_on_surface(
    matrix: Any,  # noqa: ANN401
    tmp_path: pathlib.Path,
    tag: str,
    kind: str,
    surface: str,
) -> None:
    with _stand_ins(tag, tmp_path) as got:
        _case(matrix, tmp_path, tag, kind, surface, got)


def _case(
    matrix: Any,  # noqa: ANN401
    tmp: pathlib.Path,
    tag: str,
    kind: str,
    surface: str,
    got: dict,
) -> None:
    rec: Callable[..., None] = lambda step, ok, detail="": record(  # noqa: E731
        tag, surface, kind, step, ok, detail
    )
    problems: list[str] = []

    case = matrix.open(tag, kind, surface)
    rec("add", case.action.tag == tag, case.action.tag)
    assert case.action.tag == tag
    if tag == "change-mode":
        case.profile.modes.add_mode(TARGET)

    edits, second = _edits(tag, tmp)
    names = {f["name"] for f in case.fields()}
    rec("fields", names == {n for n, _ in edits}, sorted(names))
    assert names == {n for n, _ in edits}, f"fields not covered: {names}"

    for name, value in edits:
        changed, before, after = case.set(name, value)
        ok = changed and after == value
        rec(f"set:{name}", ok, f"{before!r} -> {after!r}")
        if not ok:
            problems.append(f"set {name}: {before!r} -> {after!r}")

    ok, diff = case.save_reload()
    rec("save_reload", ok, diff)
    if not ok:
        problems.append(f"save_reload: {diff}")
    for name, value in edits:
        if case.get(name) != value:
            problems.append(f"after OK {name} reads {case.get(name)!r}")

    ok, detail = _check_run(tag, kind, case, got, tmp)
    rec("run", ok, detail)
    if not ok:
        problems.append(f"run: {detail}")
    _reset(got)

    case.reopen()
    case.set(*second)
    ok, detail = case.undo_redo()
    rec("undo_redo", ok, detail)
    if surface == Surface.CONFIG_PAGE:
        if ok is not None:
            problems.append(f"undo_redo on the live editor: {ok} {detail}")
    elif not ok:
        problems.append(f"undo_redo: {detail}")

    assert not problems, "\n".join(problems)


def _editor_requests() -> list[dict]:
    pairs = sorted({(tag, kind) for tag, kind, _ in CASES})
    return [
        {"tag": tag, "input": kind, "shot": str(SHOTS / f"{tag}_{kind}.png")}
        for tag, kind in pairs
    ]


def test_misc_editors_qml_off_screen(tmp_path: pathlib.Path) -> None:
    """Every editor loads in the off-screen program with no QML warning from
    its plugin folder (one program run for all of them)."""
    requests = _editor_requests()
    got = open_editors(requests, tmp_path)
    problems = []
    for req, editor in zip(requests, got, strict=True):
        ok = bool(editor.get("ok")) and not editor.get("plugin_warnings")
        record(
            req["tag"],
            "editor_qml",
            req["input"],
            "open_editor",
            ok,
            {
                "warnings": editor.get("warnings"),
                "plugin_warnings": editor.get("plugin_warnings"),
                "error": editor.get("error", ""),
                "shot": req["shot"],
            },
        )
        if not ok:
            problems.append(f"{req['tag']} {req['input']}: {editor}")
        elif not pathlib.Path(req["shot"]).is_file():
            problems.append(f"{req['tag']} {req['input']}: no screenshot")
    assert not problems, "\n".join(problems)
