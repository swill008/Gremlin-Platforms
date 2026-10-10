# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Action editor matrix, the output actions: Map to vJoy, Map to Xbox, Map to
Keyboard, Map to Mouse, Map to Logical Device and Send OSC, on every input
kind each allows and every surface that edits that kind (harness.py).

Per case: (1) Add Action, (3) every editable field changed and read back
(then put back), (4) save and reload, (6) Run with a fake input event and
the expected output on the fakes, (5) Undo/Redo on the pane surfaces. (2)
the editor QML, one off-screen process for every action and kind. Every
step is record()ed.

Run expectations (page 05 section 8, page 06):
- Map to vJoy writes the chosen output with the input's value (05 S82; the
  harness's write_vjoy stand-in, so claims aren't checked here).
- Map to Xbox sends the chosen pad and target the input's value (05 S84).
- Map to Keyboard holds the keys while the input is held, modifiers first,
  and releases them on release (05 S85, S100).
- Map to Mouse Button mode presses and releases the button (05 S86 wheel
  aside); Motion moves the mouse while an axis is off-centre or a hat is
  held (06 S72).
- Map to Logical Device sets the chosen Logical Device control to the
  input's value (05 section 8 table, row Map to Logical Device).
- Send OSC sends the address with the input value on press (05 S110, S111);
  osc_output.send is a stand-in here, nothing reaches the network.
"""

from __future__ import annotations

import pathlib
from typing import Any

import pytest

from test.unit.action_matrix.harness import (  # pyright: ignore[reportMissingImports]
    SURFACE_INPUTS,
    Case,
    Surface,
    cases,
    open_editors,
    record,
    settle,
)

# The input kinds each action allows (checked against the plugins by
# test_kinds_match_plugins; the plugins load only once a test runs).
KINDS: dict[str, tuple[str, ...]] = {
    "map-to-vjoy": ("axis", "button", "hat", "key"),
    "map-to-xbox": ("axis", "button", "hat", "key"),
    "map-to-keyboard": ("button", "key"),
    "map-to-mouse": ("axis", "button", "hat", "key"),
    "map-to-logical-device": ("axis", "button", "hat", "key"),
    "send-osc": ("axis", "button", "key"),
}
TAGS = tuple(KINDS)
CASES = [
    (tag, kind, surface)
    for tag, kinds in KINDS.items()
    for surface in Surface.ALL
    for kind in SURFACE_INPUTS[surface]
    if kind in kinds
]

SHOTS = pathlib.Path(
    r"C:\Users\Stacie\AppData\Local\Temp\claude"
    r"\E--Users-Stacie-Documents-GitHub-Gremlin-Platforms"
    r"\f29f32c5-d945-4e62-b89f-3680504a29c8\scratchpad\aematrix\shots"
)

# Scan codes (not extended): Left Shift, B, C.
SHIFT, KEY_B, KEY_C = 42, 48, 46


# +-------------------------------------------------------------------------
# | Helpers


def _fields(case: Case) -> list[dict]:
    """The editor model's own writable properties. Like Case.fields, but a
    value Qt can't hand back as a QVariant (Map to Logical Device's
    InputIdentifier) is read as a Python attribute."""
    model = case.model()
    meta = model.metaObject()
    base = meta
    while base is not None and base.className() != "ActionModel":
        base = base.superClass()
    start = base.propertyCount() if base is not None else meta.propertyOffset()
    out = []
    for i in range(start, meta.propertyCount()):
        prop = meta.property(i)
        if not prop.isWritable():
            continue
        out.append({"name": prop.name(), "type": prop.typeName()})
    return out


def _get(case: Case, name: str) -> Any:  # noqa: ANN401
    value = getattr(case.model(), name)
    if hasattr(value, "input_id"):  # an InputIdentifier
        return (value.input_type, value.input_id)
    return value


def _put(case: Case, name: str, value: Any) -> Any:  # noqa: ANN401
    """Sets a field as the QML would and returns what it reads back."""
    setattr(case.model(), name, value)
    settle()
    return _get(case, name)


def _event(kind: Any, identifier: Any) -> Any:  # noqa: ANN401
    import dill
    from gremlin.event_handler import Event

    return Event(kind, identifier, dill.UUID_Keyboard, "Default", is_pressed=True)


def _set_keys(case: Case, scans: list[int]) -> str:
    from gremlin.types import InputType

    case.model().updateInputs([_event(InputType.Keyboard, (s, False)) for s in scans])
    settle()
    return case.model().property("keyCombination")


def _set_mouse_button(case: Case, button: Any) -> str:  # noqa: ANN401
    from gremlin.types import InputType

    case.model().updateInputs([_event(InputType.Mouse, button)])
    settle()
    return case.model().property("button")


def _logical_control(kind: str) -> Any:  # noqa: ANN401
    """A new Logical Device control for the action to drive (not the
    input a Logical case edits)."""
    from gremlin.logical_device import LogicalDevice
    from gremlin.types import InputType

    control_type = {
        "axis": InputType.JoystickAxis,
        "hat": InputType.JoystickHat,
    }.get(kind, InputType.JoystickButton)
    return LogicalDevice().create(control_type)


def _identifier(control: Any) -> Any:  # noqa: ANN401
    from gremlin.logical_device import LogicalDevice
    from gremlin.ui.device import InputIdentifier

    return InputIdentifier(LogicalDevice().device_guid, control.type, control.id)


# Changed values per field (others: harness dummy-like rules below).
def _new_value(case: Case, name: str, current: Any) -> Any:  # noqa: ANN401
    if name == "vjoyInputType":
        return "button" if current != "button" else "axis"
    if name == "axisMode":
        return "relative" if current != "relative" else "absolute"
    if name == "xboxTarget":
        choices = [c["value"] for c in case.model().property("targetChoices")]
        others = [c for c in choices if c != current]
        return others[0] if others else current
    if name == "triggerRange":
        return "upper" if current != "upper" else "full"
    if name == "mode":
        return "Motion" if current == "Button" else "Button"
    if name == "direction":
        return 90 if current != 90 else 0
    if name == "target":
        from gremlin import osc_output

        return osc_output.REPLY if current != osc_output.REPLY else "matrix-target"
    if name == "address":
        return "/matrix/field"
    if name == "logicalInputIdentifier":
        return _identifier(_logical_control(case.input_type))
    if isinstance(current, bool):
        return not current
    if isinstance(current, int):
        return current + 1
    if isinstance(current, float):
        return 0.5 if abs(current - 0.5) > 1e-9 else 0.25
    return None


def _check_fields(case: Case) -> tuple[bool, list]:
    """Every field changed, read back, then put back. (all ok, details)."""
    details = []
    ok = True
    for field in _fields(case):
        name = field["name"]
        try:
            before = _get(case, name)
            value = _new_value(case, name, before)
            after = _put(case, name, value)
            want = _get_want(value)
            changed = after == want and after != before
            back = _put(case, name, _restore_value(before, value))
            restored = back == before
        except Exception as error:  # noqa: BLE001
            details.append({"field": name, "error": repr(error)})
            ok = False
            continue
        details.append(
            {
                "field": name,
                "before": str(before),
                "set": str(value),
                "read": str(after),
                "restored": restored,
            }
        )
        ok = ok and changed and restored
    return ok, details


def _get_want(value: Any) -> Any:  # noqa: ANN401
    if hasattr(value, "input_id"):
        return (value.input_type, value.input_id)
    return value


def _restore_value(before: Any, value: Any) -> Any:  # noqa: ANN401
    """The old value in the form the setter takes."""
    if isinstance(before, tuple) and hasattr(value, "input_id"):
        from gremlin.logical_device import LogicalDevice
        from gremlin.ui.device import InputIdentifier

        return InputIdentifier(LogicalDevice().device_guid, before[0], before[1])
    return before


# +-------------------------------------------------------------------------
# | The setup each action runs with, and what Run should give


class _Plan:
    """The run setup for one case: the fields to set, the event(s), the
    stand-ins to watch, and the check of what reached the outputs."""

    def __init__(self, case: Case) -> None:
        self.case = case
        self.kind = case.input_type
        self.values: list = []
        self.wait = 0.3
        self.expected = ""
        self.target = ""  # Map to Xbox: the target chosen
        self.control: Any = None  # Map to Logical Device: the control driven

    def event_values(self) -> list:
        return {
            "axis": [0.5],
            "button": [True, False],
            "key": [True, False],
            "hat": ["north", "center"],
        }[self.kind]


def _setup(case: Case) -> _Plan:
    """Puts the action on a known setup for Run (after the field check)."""
    plan = _Plan(case)
    plan.values = plan.event_values()
    tag = case.tag
    if tag == "map-to-vjoy":
        _put(case, "vjoyInputId", 7)
        plan.expected = "vJoy 1 output 7 gets the input's value"
    elif tag == "map-to-xbox":
        choices = [c["value"] for c in case.model().property("targetChoices")]
        plan.target = choices[-1]
        _put(case, "xboxTarget", plan.target)
        plan.expected = f"pad 1 target {plan.target} gets the input's value"
    elif tag == "map-to-keyboard":
        _set_keys(case, [KEY_B, SHIFT])
        plan.expected = "Shift then B down on press; both up on release (S85)"
    elif tag == "map-to-mouse":
        from gremlin import sendinput

        if case.model().property("mode") == "Button":
            from gremlin.types import MouseButton

            _set_mouse_button(case, MouseButton.Right)
            case.watch(sendinput, "mouse_press")
            case.watch(sendinput, "mouse_release")
            plan.expected = "Right button pressed then released"
        else:
            plan.values = [0.5] if plan.kind == "axis" else ["north"]
            plan.wait = 0.4
            plan.expected = "mouse motion while held (06 S72)"
    elif tag == "map-to-logical-device":
        from gremlin.logical_device import LogicalDevice

        control = _logical_control(plan.kind)
        plan.control = control
        _put(case, "logicalInputIdentifier", _identifier(control))
        case.watch(LogicalDevice.Input, "update")
        plan.expected = f"Logical {control.type.name} {control.id} gets the value"
    elif tag == "send-osc":
        from gremlin import osc_output

        _put(case, "address", "/matrix")
        if not case.get("values"):
            case.model().addValue()
        case.model().setValueField(0, "source", "input")
        settle()
        case.watch(osc_output, "send")
        plan.expected = "/matrix sent once on press with the input value"
    return plan


def _check_run(plan: _Plan, sent: list[tuple]) -> tuple[bool | None, str]:
    """(ok, why). ok None: not checked."""
    from gremlin.types import HatDirection, MouseButton

    case, kind = plan.case, plan.kind
    tag = case.tag
    if tag == "map-to-vjoy":
        writes = [s for s in sent if s[0] == "write_vjoy"]
        if kind == "axis":
            want = [("write_vjoy", 1, "axis", 7, 0.5)]
        elif kind == "hat":
            want = [
                ("write_vjoy", 1, "hat", 7, HatDirection.North),
                ("write_vjoy", 1, "hat", 7, HatDirection.Center),
            ]
        else:
            want = [
                ("write_vjoy", 1, "button", 7, True),
                ("write_vjoy", 1, "button", 7, False),
            ]
        return writes == want, f"want {want}"
    if tag == "map-to-xbox":
        writes = [s for s in sent if s[0] == "write_xbox"]
        target = plan.target
        if kind == "axis":
            values = [0.5]
        elif kind == "hat":
            values = [HatDirection.North, HatDirection.Center]
        else:
            values = [True, False]
        got = [(s[1], getattr(s[2], "value", s[2]), s[3]) for s in writes]
        want = [(1, target, v) for v in values]
        return got == want, f"want {want}"
    if tag == "map-to-keyboard":
        keys = [s for s in sent if s[0] == "key"]
        want = [
            ("key", SHIFT, False, True),
            ("key", KEY_B, False, True),
        ]
        ok = keys[:2] == want and sorted(keys[2:]) == sorted(
            [("key", SHIFT, False, False), ("key", KEY_B, False, False)]
        )
        return ok, f"want {want} then both released"
    if tag == "map-to-mouse":
        if case.model().property("mode") == "Button":
            got = [s for s in sent if s[0] in ("mouse_press", "mouse_release")]
            want = [
                ("mouse_press", MouseButton.Right),
                ("mouse_release", MouseButton.Right),
            ]
            return got == want, f"want {want}"
        moves = [s for s in sent if s[0] == "input"]
        return len(moves) > 0, "want mouse input while held"
    if tag == "map-to-logical-device":
        control = plan.control
        got = [s[2] for s in sent if s[0] == "update" and s[1] is control]
        if kind == "axis":
            want: list = [0.5]
        elif kind == "hat":
            want = [HatDirection.North, HatDirection.Center]
        else:
            want = [True, False]
        return got == want, f"want {want} on the control"
    if tag == "send-osc":
        got = [s for s in sent if s[0] == "send"]
        value = 0.75 if kind == "axis" else 1.0
        if len(got) != 1:
            return False, f"want one send, got {len(got)}"
        _name, _target, address, values, types = got[0][:5]
        ok = address == "/matrix" and list(values) == [pytest.approx(value)]
        return ok, f"want /matrix [{value}]"
    return None, "not checked"


def _undo_edit(case: Case) -> None:
    """One field change for the Undo/Redo step."""
    tag = case.tag
    if tag == "map-to-vjoy":
        _put(case, "vjoyInputId", 9)
    elif tag == "map-to-keyboard":
        _set_keys(case, [KEY_C])
    elif tag == "map-to-mouse":
        _put(case, "mode", "Motion" if case.get("mode") == "Button" else "Button")
    elif tag == "send-osc":
        _put(case, "address", "/matrix/undo")
    elif tag == "map-to-logical-device":
        _put(
            case,
            "logicalInputIdentifier",
            _identifier(_logical_control(case.input_type)),
        )
    else:
        _put(case, "buttonInverted", not case.get("buttonInverted"))


def test_kinds_match_plugins() -> None:
    assert sorted(c for c in cases() if c[0] in TAGS) == sorted(CASES)


# +-------------------------------------------------------------------------
# | Known defects (xfail strict): (tag, kind, surface) -> reason

XFAIL: dict[tuple[str, str, str], str] = {}


def _params() -> list[Any]:
    out = []
    for tag, kind, surface in CASES:
        reason = XFAIL.get((tag, kind, surface))
        marks = [pytest.mark.xfail(strict=True, reason=reason)] if reason else []
        out.append(
            pytest.param(tag, kind, surface, marks=marks, id=f"{tag}-{kind}-{surface}")
        )
    return out


@pytest.mark.parametrize(("tag", "kind", "surface"), _params())
def test_output_action(matrix: Any, tag: str, kind: str, surface: str) -> None:  # noqa: ANN401
    problems: list[str] = []

    # (1) Add Action
    case = matrix.open(tag, kind, surface)
    ok = case.action.tag == tag
    record(tag, surface, kind, "add", ok, case.action.tag)
    assert ok
    if tag == "map-to-logical-device":
        # 06 S92: a new action never drives the control it sits on.
        target = _get(case, "logicalInputIdentifier")
        own = (case.key[1], case.key[2]) if surface == Surface.PANE_LOGICAL else None
        ok = target != own
        record(
            tag,
            surface,
            kind,
            "default_target",
            ok,
            {"target": str(target), "is_the_edited_input": target == own},
        )
        assert ok, f"default target is the edited input {own}"

    # (3) every field changed and read back
    ok, details = _check_fields(case)
    record(tag, surface, kind, "fields", ok, details)
    if not ok:
        problems.append(f"fields: {details}")
    if tag == "map-to-keyboard":
        combo = _set_keys(case, [KEY_C])
        ok_keys = combo != ""
        record(tag, surface, kind, "fields_keys", ok_keys, combo)
        if not ok_keys:
            problems.append("keys: no key combination after updateInputs")
    if tag == "map-to-mouse" and case.get("mode") == "Button":
        from gremlin.types import MouseButton

        got = _set_mouse_button(case, MouseButton.Middle)
        ok_button = got != "" and got != "Left"
        record(tag, surface, kind, "fields_button", ok_button, got)
        if not ok_button:
            problems.append(f"mouse button: read back {got!r}")

    # setup for Run, then (4) save and reload
    plan = _setup(case)
    ok, diff = case.save_reload()
    record(tag, surface, kind, "save_reload", ok, diff)
    if not ok:
        problems.append(f"save_reload: {diff}")

    # (6) Run
    sent = case.run(value=plan.values, wait=plan.wait)
    ok_run, why = _check_run(plan, sent)
    record(
        tag,
        surface,
        kind,
        "run",
        ok_run,
        {"expected": plan.expected, "check": why, "sent": [str(s) for s in sent[:20]]},
    )
    if ok_run is False:
        problems.append(f"run: {why}; got {sent[:20]}")

    # (5) Undo/Redo on the panes
    case.reopen()
    _undo_edit(case)
    ok_undo, detail = case.undo_redo()
    record(tag, surface, kind, "undo_redo", ok_undo, detail)
    if surface == Surface.CONFIG_PAGE:
        if ok_undo is not None:
            problems.append("undo_redo: the live editor has an Undo step")
    elif not ok_undo:
        problems.append(f"undo_redo: {detail}")

    assert not problems, "\n".join(problems)


# +-------------------------------------------------------------------------
# | (2) The editor QML, one off-screen program for every action and kind


def test_output_editors_qml(tmp_path: pathlib.Path) -> None:
    kinds = sorted({(tag, kind) for tag, kind, _surface in CASES})
    requests = [
        {"tag": tag, "input": kind, "shot": str(SHOTS / f"{tag}_{kind}.png")}
        for tag, kind in kinds
    ]
    got = open_editors(requests, tmp_path)
    problems = []
    for req, editor in zip(requests, got, strict=True):
        ok = bool(editor.get("ok")) and not editor.get("warnings")
        shot_ok = pathlib.Path(req["shot"]).is_file()
        record(
            req["tag"],
            "editor_qml",
            req["input"],
            "open_editor",
            ok and shot_ok,
            {
                "warnings": editor.get("warnings"),
                "qml": editor.get("qml"),
                "shot": req["shot"],
                "error": editor.get("error", ""),
            },
        )
        if not (ok and shot_ok):
            problems.append(f"{req['tag']} {req['input']}: {editor}")
    assert not problems, "\n".join(problems)
