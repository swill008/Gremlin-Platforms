# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Action editor matrix: the axis actions (Response Curve, Split Axis, Merge
Axis, Dual Axis Deadzone, Axis Delta) and Hat as Buttons, on every surface
that edits their input kind (the Keyboard pane edits keys only: n.a.).

Per case: Add Action, every editor field changed and read back, save and
reload (values kept), Undo/Redo on the panes, and a fake input through the
real runner to the fake vJoy (05 table rows for each action; S80, S87, S88,
S114, Q9, Q10). The editor QML is one off-screen run for all of them.
Every step goes to the matrix results file (harness.record).
"""

from __future__ import annotations

import pathlib
from collections.abc import Callable
from typing import Any
from unittest import mock

import pytest

from test.unit.action_matrix.harness import (  # pyright: ignore[reportMissingImports]
    Case,
    Surface,
    _stick_guid,
    actions,
    cases,
    open_editors,
    record,
    settle,
)

TAGS = (
    "response-curve",
    "split-axis",
    "merge-axis",
    "dual-axis-deadzone",
    "axis-delta",
    "hat-buttons",
)
_EDITING = (Surface.CONFIG_PAGE, Surface.PANE_BUTTON_MAP, Surface.PANE_LOGICAL)
# Plugins load only once the test config is up, so the list is written out
# here and checked against harness.cases() in the first test.
CASES = [
    (tag, "hat" if tag == "hat-buttons" else "axis", surface)
    for tag in TAGS
    for surface in _EDITING
]
SHOTS = pathlib.Path(
    r"C:\Users\Stacie\AppData\Local\Temp\claude"
    r"\E--Users-Stacie-Documents-GitHub-Gremlin-Platforms"
    r"\f29f32c5-d945-4e62-b89f-3680504a29c8\scratchpad\aematrix\shots"
)

# Every writable field each editor model has (a new one fails the fields
# test until it is covered here).
FIELDS: dict[str, set[str]] = {
    "response-curve": {"isSymmetric", "curveType", "selectedPoint"},
    "split-axis": {"splitValue"},
    "merge-axis": {"label", "mergeAction", "firstAxis", "secondAxis", "operation"},
    "dual-axis-deadzone": {
        "label",
        "innerDeadzone",
        "outerDeadzone",
        "axis1",
        "axis2",
        "deadzone",
    },
    "axis-delta": {"changeThreshold"},
    "hat-buttons": {"buttonCount"},
}


# +-------------------------------------------------------------------------
# | Fields


def _axis(input_id: int) -> Any:  # noqa: ANN401
    from gremlin.types import InputType
    from gremlin.ui.device import InputIdentifier

    return InputIdentifier(_stick_guid(), InputType.JoystickAxis, input_id)


def _norm(value: Any) -> Any:  # noqa: ANN401
    """A comparable form of a field's value (an InputIdentifier is a view)."""
    if hasattr(value, "device_guid") and hasattr(value, "input_id"):
        return (value.device_guid, value.input_type, value.input_id)
    if isinstance(value, float):
        return round(value, 6)
    return value


def _get(case: Case, field: str) -> Any:  # noqa: ANN401
    """A field's value; through Python, as Qt's property() has no converter
    for the QObject-typed ones (InputIdentifier, Deadzone)."""
    return getattr(case.model(), field)


def _put(case: Case, field: str, value: Any) -> None:  # noqa: ANN401
    setattr(case.model(), field, value)
    settle()


def _set(case: Case, field: str, value: Any) -> tuple[bool, Any, Any]:  # noqa: ANN401
    """Sets a field as the QML would and reads it back: (ok, before, after)."""
    before = _norm(_get(case, field))
    _put(case, field, value)
    after = _norm(_get(case, field))
    return after == _norm(value) and after != before, before, after


def _plus(case: Case, slot: str, field: str) -> tuple[bool, Any, Any]:  # noqa: ANN401
    """The editor's "+" (a new instance shown in this one's place); the case
    follows the new action. ok: the field now names the new one."""
    old = case.action
    before = _get(case, field)
    getattr(case.model(), slot)()
    settle()
    kids = case.root_model().action_data.get_actions()[0]
    new = [a for a in kids if getattr(a, "tag", "") == case.tag and a is not old]
    if not new:
        return False, before, "no new instance in the input"
    case.action = new[0]
    after = _get(case, field)
    return after == str(new[0].id) and after != before, before, after


def _deadzone(case: Case, values: dict[str, float]) -> list[tuple]:
    """Response Curve's four deadzone values (a sub-object in the model)."""
    out = []
    for name, value in values.items():
        before = getattr(case.model().deadzone, name)
        setattr(case.model().deadzone, name, value)
        settle()
        after = getattr(case.model().deadzone, name)
        out.append((f"deadzone.{name}", after == pytest.approx(value), before, after))
    return out


def _field_names(case: Case) -> set[str]:
    """The editor model's own writable properties (harness Case.fields()
    without the values: Qt's property() can't read the QObject-typed ones)."""
    meta = case.model().metaObject()
    base = meta
    while base is not None and base.className() != "ActionModel":
        base = base.superClass()
    start = base.propertyCount() if base is not None else meta.propertyOffset()
    return {
        meta.property(i).name()
        for i in range(start, meta.propertyCount())
        if meta.property(i).isWritable()
    }


def apply_fields(case: Case) -> list[tuple[str, bool, Any, Any]]:
    """Changes every field of the case's editor; one row per field."""
    rows: list[tuple[str, bool, Any, Any]] = []

    def one(name: str, value: Any) -> None:  # noqa: ANN401
        ok, before, after = _set(case, name, value)
        rows.append((name, ok, before, after))

    tag = case.tag
    if tag == "response-curve":
        one("isSymmetric", True)
        one("curveType", "Cubic Spline")
        # S50: changing the type keeps Symmetric.
        kept = _get(case, "isSymmetric")
        rows.append(("isSymmetric kept by curveType (S50)", kept is True, True, kept))
        # The selected point is the editor's view state (kept by the model
        # object, not saved): set and read on one model.
        model = case.model()
        model.selectedPoint = 1
        settle()
        rows.append(
            (
                "selectedPoint (view state)",
                model.selectedPoint == 1,
                0,
                model.selectedPoint,
            )
        )
        for name, ok, before, after in _deadzone(
            case, {"low": -0.9, "centerLow": -0.2, "centerHigh": 0.2, "high": 0.9}
        ):
            rows.append((name, ok, before, after))
    elif tag == "split-axis":
        one("splitValue", 0.5)
    elif tag == "merge-axis":
        ok, before, after = _plus(case, "newMergeAxis", "mergeAction")
        rows.append(("mergeAction (+)", ok, before, after))
        one("label", "matrix")
        one("firstAxis", _axis(1))
        one("secondAxis", _axis(2))
        one("operation", "maximum-deflection")
    elif tag == "dual-axis-deadzone":
        ok, before, after = _plus(case, "newDeadzone", "deadzone")
        rows.append(("deadzone (+)", ok, before, after))
        one("label", "matrix")
        one("axis1", _axis(1))
        one("axis2", _axis(2))
        one("innerDeadzone", 0.2)
        one("outerDeadzone", 0.9)
    elif tag == "axis-delta":
        one("changeThreshold", 0.25)
    elif tag == "hat-buttons":
        one("buttonCount", 8)
    return rows


def _check_reloaded(tag: str, data: Any) -> list[str]:  # noqa: ANN401
    """What apply_fields set, on the action read back from the saved file."""
    from action_plugins.merge_axis import MergeOperation
    from gremlin import spline

    problems = []

    def want(what: str, got: Any, expected: Any) -> None:  # noqa: ANN401
        if got != expected:
            problems.append(f"{what}: {got!r} != {expected!r}")

    if tag == "response-curve":
        want("deadzone", [round(v, 6) for v in data.deadzone], [-0.9, -0.2, 0.2, 0.9])
        want("curve", type(data.curve), spline.CubicSpline)
        want("symmetric", data.curve.is_symmetric, True)
    elif tag == "split-axis":
        want("split value", data.split_value, 0.5)
    elif tag == "merge-axis":
        want("label", data.label, "matrix")
        want("operation", data.operation, MergeOperation.MaximumDeflection)
        want("axis 1", data.axis_in1.input_id, 1)
        want("axis 2", data.axis_in2.input_id, 2)
        want("axis 1 device", data.axis_in1.device_guid, _stick_guid())
    elif tag == "dual-axis-deadzone":
        want("label", data.label, "matrix")
        want("inner", round(data.inner_deadzone, 6), 0.2)
        want("outer", round(data.outer_deadzone, 6), 0.9)
        want("axis 1", data.axis1.input_id, 1)
        want("axis 2", data.axis2.input_id, 2)
    elif tag == "axis-delta":
        want("threshold", round(data.change_threshold, 6), 0.25)
    elif tag == "hat-buttons":
        want("button count", data.button_count, 8)
        want("directions", len(data.direction), 9)
    return problems


# +-------------------------------------------------------------------------
# | Run: child Map to vJoy outputs and the expected writes


def _add_vjoy(case: Case, selector: str, input_id: int, kind: str) -> None:
    """A Map to vJoy (vJoy 1, kind input_id) at the end of the case's
    action's container (selector "root": after the action in the binding)."""
    owner = case.root_model() if selector == "root" else case.model()
    where = "children" if selector == "root" else selector
    before = len(owner.getActions(where))
    owner.appendAction("Map to vJoy", where)
    settle()

    def child() -> Any:  # noqa: ANN401
        parent = case.root_model() if selector == "root" else case.model()
        kids = parent.getActions(where)
        assert len(kids) == before + 1, f"no Map to vJoy added to {where}"
        return kids[-1]

    for name, value in (
        ("vjoyDeviceId", 1),
        ("vjoyInputType", kind),
        ("vjoyInputId", input_id),
    ):
        child().setProperty(name, value)
        settle()
    got = (
        child().property("vjoyDeviceId"),
        child().property("vjoyInputType"),
        child().property("vjoyInputId"),
    )
    assert got == (1, kind, input_id), got


def _writes(sent: list[tuple]) -> list[tuple]:
    """(kind, id, value) of each vJoy write; a button release as False."""
    out = []
    for s in sent:
        if s[0] == "write_vjoy":
            value = s[4]
            out.append(
                (s[2], s[3], round(value, 4) if isinstance(value, float) else value)
            )
        elif s[0] == "release_vjoy_button":
            out.append(("button", s[2], False))
    return out


def _fake_axes(values: dict[int, float]) -> Any:  # noqa: ANN401
    """inputs.axis_value stand-in: the stick's axes 1 and 2."""
    from gremlin.modules import inputs

    stick = _stick_guid()

    def axis_value(device_guid: Any, axis_id: Any) -> float:  # noqa: ANN401
        if device_guid == stick and axis_id in values:
            return values[axis_id]
        return 0.0

    return mock.patch.object(inputs, "axis_value", axis_value)


Runner = Callable[[Case], tuple[list[tuple], list[tuple]]]


def _run_response_curve(case: Case) -> tuple[list[tuple], list[tuple]]:
    """05 row: deadzone then curve; later actions see the new value (S80)."""
    _put(case, "curveType", "Piecewise Linear")
    _deadzone(case, {"low": -1.0, "centerLow": -0.2, "centerHigh": 0.2, "high": 1.0})
    _add_vjoy(case, "root", 3, "axis")
    sent = case.run("axis", [0.6, 0.1, -0.6])
    want = [("axis", 3, 0.5), ("axis", 3, 0.0), ("axis", 3, -0.5)]
    return _writes(sent), want


def _run_split_axis(case: Case) -> tuple[list[tuple], list[tuple]]:
    """05 row / S88: the rescaled value to the side the value is in; on
    crossing, the side left gets -1."""
    _put(case, "splitValue", 0.5)
    _add_vjoy(case, "lower", 3, "axis")
    _add_vjoy(case, "upper", 4, "axis")
    sent = case.run("axis", [0.75, 0.0])
    lower = -((0.0 + 1.0) / 1.5 * 2.0 - 1.0)
    want = [("axis", 4, 0.0), ("axis", 4, -1.0), ("axis", 3, round(lower, 4))]
    return _writes(sent), want


def _merge_setup(case: Case, operation: str) -> None:
    for name, value in (
        ("firstAxis", _axis(1)),
        ("secondAxis", _axis(2)),
        ("operation", operation),
    ):
        _put(case, name, value)


def _run_merge_axis(case: Case) -> tuple[list[tuple], list[tuple]]:
    """S87: both axes through the input modules; S114 Maximum Deflection
    (furthest from centre wins, a tie goes to axis 2); Average."""
    _merge_setup(case, "maximum-deflection")
    _add_vjoy(case, "children", 3, "axis")
    got: list[tuple] = []
    with _fake_axes({1: 0.3, 2: -0.6}):
        got += _writes(case.run("axis", 0.3))
    with _fake_axes({1: 0.5, 2: -0.5}):
        got += _writes(case.run("axis", 0.5))
    case.reopen()
    _merge_setup(case, "average")
    with _fake_axes({1: 0.4, 2: -0.2}):
        got += _writes(case.run("axis", 0.4))
    want = [("axis", 3, -0.6), ("axis", 3, -0.5), ("axis", 3, 0.1)]
    return got, want


def _run_dual_axis_deadzone(case: Case) -> tuple[list[tuple], list[tuple]]:
    """05 row: inner circle / outer square; X to the first list, Y to the
    second (axes through the input modules, S87)."""
    for name, value in (
        ("axis1", _axis(1)),
        ("axis2", _axis(2)),
        ("innerDeadzone", 0.2),
        ("outerDeadzone", 0.9),
    ):
        _put(case, name, value)
    _add_vjoy(case, "first", 3, "axis")
    _add_vjoy(case, "second", 4, "axis")
    with _fake_axes({1: 0.5, 2: 0.0}):
        got = _writes(case.run("axis", 0.5))
    want = [("axis", 3, round((0.5 - 0.2) / 0.7, 4)), ("axis", 4, 0.0)]
    return got, want


def _run_axis_delta(case: Case) -> tuple[list[tuple], list[tuple]]:
    """05 row / Q9: a pulse on Positive / Negative each time the axis moved
    by the threshold (0 is a value)."""
    _put(case, "changeThreshold", 0.25)
    _add_vjoy(case, "positive", 3, "button")
    _add_vjoy(case, "negative", 4, "button")
    sent = case.run("axis", [0.0, 0.3, 0.0], wait=0.4)
    # Each pulse's release comes 50 ms later, so the two pulses overlap
    # here: compared per button, presses in order.
    got = _writes(sent)
    presses = [w[1] for w in got if w[2] is True]
    per_button = {i: [w[2] for w in got if w[1] == i] for i in (3, 4)}
    return [("presses", *presses), *sorted(per_button.items())], [
        ("presses", 3, 4),
        (3, [True, False]),
        (4, [True, False]),
    ]


def _run_hat_buttons(case: Case) -> tuple[list[tuple], list[tuple]]:
    """05 row: each direction button runs its list (8 way)."""
    _put(case, "buttonCount", 8)
    _add_vjoy(case, "North", 5, "button")
    _add_vjoy(case, "North-East", 6, "button")
    sent = case.run("hat", ["north", "center", "north-east", "center"])
    want = [
        ("button", 5, True),
        ("button", 5, False),
        ("button", 6, True),
        ("button", 6, False),
    ]
    return _writes(sent), want


RUNS: dict[str, Runner] = {
    "response-curve": _run_response_curve,
    "split-axis": _run_split_axis,
    "merge-axis": _run_merge_axis,
    "dual-axis-deadzone": _run_dual_axis_deadzone,
    "axis-delta": _run_axis_delta,
    "hat-buttons": _run_hat_buttons,
}


# +-------------------------------------------------------------------------
# | The tests


def _cid(cases: list[tuple[str, str, str]]) -> list[str]:
    return [f"{c[0]}-{c[1]}-{c[2]}" for c in cases]


def test_the_six_actions_and_their_kinds() -> None:
    kinds = dict(actions())
    for tag in TAGS[:-1]:
        assert kinds[tag] == ("axis",), (tag, kinds[tag])
    assert kinds["hat-buttons"] == ("hat",)
    # Three surfaces each (the Keyboard pane edits keys only).
    assert sorted(c for c in cases() if c[0] in TAGS) == sorted(CASES)
    for tag in TAGS:
        record(tag, Surface.PANE_KEYBOARD, "key", "all", None, "edits keys only")


@pytest.mark.parametrize(("tag", "kind", "surface"), CASES, ids=_cid(CASES))
def test_add_and_fields(matrix: Any, tag: str, kind: str, surface: str) -> None:  # noqa: ANN401
    case = matrix.open(tag, kind, surface)
    record(tag, surface, kind, "add", case.action.tag == tag, case.action.tag)
    assert case.action.tag == tag

    names = _field_names(case)
    record(
        tag,
        surface,
        kind,
        "field_list",
        names == FIELDS[tag],
        {"got": sorted(names), "covered": sorted(FIELDS[tag])},
    )
    assert names == FIELDS[tag], sorted(names ^ FIELDS[tag])

    rows = apply_fields(case)
    for name, ok, before, after in rows:
        record(tag, surface, kind, f"set {name}", ok, f"{before!r} -> {after!r}")
    bad = [r for r in rows if not r[1]]
    assert not bad, bad


# The instance drop-down of each editor: (value property, list property).
_PICK = {
    "merge-axis": ("mergeAction", "mergeActionList"),
    "dual-axis-deadzone": ("deadzone", "deadzoneActionList"),
}
_AXES = {
    "merge-axis": ("axis_in1", "axis_in2"),
    "dual-axis-deadzone": ("axis1", "axis2"),
}
_PAIR_CASES = [c for c in CASES if c[0] in _PICK]


def _shown(case: Case) -> str:
    """The text the instance drop-down shows: the pick list's label for the
    editor's value."""
    value_name, list_name = _PICK[case.tag]
    model = case.model()
    value = getattr(model, value_name)
    picks = getattr(model, list_name)
    labels = dict(zip(picks._values, picks._labels, strict=True))  # noqa: SLF001
    return labels.get(value, "")


@pytest.mark.parametrize(("tag", "kind", "surface"), _PAIR_CASES, ids=_cid(_PAIR_CASES))
def test_add_starts_on_a_named_instance(
    matrix: Any,  # noqa: ANN401
    tag: str,
    kind: str,
    surface: str,
) -> None:
    """05 S120: right after Add Action the drop-down shows a new instance,
    named as "+" would name it."""
    case = matrix.open(tag, kind, surface)
    want = f"{case.cls.name} 1"
    shown = _shown(case)
    record(tag, surface, kind, "add names the instance (S120)", shown == want, shown)
    assert case.action.label == want
    assert shown == want


def test_second_add_numbering(matrix: Any) -> None:  # noqa: ANN401
    """05 S120: a second Dual Axis Deadzone is the next number; a second
    Merge Axis is the in-use one (Reuse by default), its name kept."""
    dual = matrix.open("dual-axis-deadzone", "axis", Surface.CONFIG_PAGE)
    dual.root_model().appendAction(dual.cls.name, "children")
    settle()
    labels = sorted(a.label for a in dual.profile.library.actions_by_type(dual.cls))
    assert labels == ["Dual Axis Deadzone 1", "Dual Axis Deadzone 2"]

    merge = matrix.open("merge-axis", "axis", Surface.CONFIG_PAGE)
    merge.root_model().appendAction(merge.cls.name, "children")
    settle()
    found = list(merge.profile.library.actions_by_type(merge.cls))
    assert [a.label for a in found] == ["Merge Axis 1"]


@pytest.mark.parametrize("tag", list(_PICK))
def test_load_keeps_the_saved_instance(
    tmp_path: pathlib.Path,
    tag: str,
) -> None:
    """05 S120: only Add Action names one; a loaded action keeps its saved
    instance (an unnamed one stays unnamed, nothing is added)."""
    from action_plugins.axis_pair import AxisRef
    from gremlin import shared_state
    from gremlin.profile import Profile
    from test.unit.action_matrix.harness import (  # pyright: ignore[reportMissingImports]
        MODE,
        plugin,
    )

    cls = plugin(tag)
    kept = shared_state.current_profile
    try:
        profile = Profile()
        shared_state.current_profile = profile
        item = profile.get_input_item(
            _stick_guid(), _kind_axis(), 1, MODE, create_if_missing=True
        )
        assert item is not None
        item.add_item_binding()
        root = item.action_sequences[0].root_action
        for label in ("", "Saved name"):
            action = profile.library.create(cls.name, _kind_axis(), reuse=False)
            action.label = label
            # Finished (both axes), so Save keeps it.
            for i, name in enumerate(_AXES[tag]):
                setattr(action, name, AxisRef(_stick_guid(), _kind_axis(), i + 1))
            root.insert_action(action, "children")
        path = tmp_path / "saved.xml"
        profile.to_xml(path)
        back = Profile()
        back.from_xml(path)
    finally:
        shared_state.current_profile = kept
    labels = sorted(a.label for a in back.library.actions_by_type(cls))
    assert labels == ["", "Saved name"]


def _kind_axis() -> Any:  # noqa: ANN401
    from gremlin.types import InputType

    return InputType.JoystickAxis


@pytest.mark.parametrize(("tag", "kind", "surface"), CASES, ids=_cid(CASES))
def test_save_reload(matrix: Any, tag: str, kind: str, surface: str) -> None:  # noqa: ANN401
    from gremlin.profile import Profile

    case = matrix.open(tag, kind, surface)
    apply_fields(case)
    ok, diff = case.save_reload()
    problems = [diff] if not ok else []
    saved = case.tmp / f"{tag}-{surface}-{kind}-1.xml"
    if saved.is_file():
        back = Profile()
        back.from_xml(saved)
        found = list(back.library.actions_by_type(case.cls))
        if tag in ("merge-axis", "dual-axis-deadzone"):
            found = [a for a in found if getattr(a, "label", "") == "matrix"]
        if len(found) != 1:
            problems.append(f"{len(found)} {tag} in the reloaded profile")
        else:
            problems += _check_reloaded(tag, found[0])
    record(tag, surface, kind, "save_reload", not problems, "\n".join(problems))
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize(
    ("tag", "kind", "surface"),
    [c for c in CASES if c[2] != Surface.CONFIG_PAGE],
    ids=_cid([c for c in CASES if c[2] != Surface.CONFIG_PAGE]),
)
def test_undo_redo(matrix: Any, tag: str, kind: str, surface: str) -> None:  # noqa: ANN401
    case = matrix.open(tag, kind, surface)
    apply_fields(case)
    ok, detail = case.undo_redo()
    record(tag, surface, kind, "undo_redo", ok, detail)
    assert ok, detail


def test_undo_redo_live_editor_not_applicable() -> None:
    for tag, kind, surface in CASES:
        if surface == Surface.CONFIG_PAGE:
            record(
                tag,
                surface,
                kind,
                "undo_redo",
                None,
                "no Undo on the live editor (05 S35)",
            )


@pytest.mark.parametrize(("tag", "kind", "surface"), CASES, ids=_cid(CASES))
def test_run(matrix: Any, tag: str, kind: str, surface: str) -> None:  # noqa: ANN401
    case = matrix.open(tag, kind, surface)
    got, want = RUNS[tag](case)
    ok = got == want
    record(tag, surface, kind, "run", ok, {"got": got, "want": want})
    assert ok, f"got {got}\nwant {want}"


def test_editor_qml_off_screen(tmp_path: pathlib.Path) -> None:
    pairs = sorted({(c[0], c[1]) for c in CASES})
    requests = [
        {"tag": tag, "input": kind, "shot": str(SHOTS / f"{tag}_{kind}.png")}
        for tag, kind in pairs
    ]
    got = open_editors(requests, tmp_path)
    bad = []
    for req, editor in zip(requests, got, strict=True):
        ok = bool(editor.get("ok")) and not editor.get("warnings")
        shot_ok = pathlib.Path(req["shot"]).is_file()
        detail = {
            "warnings": editor.get("warnings"),
            "plugin_warnings": editor.get("plugin_warnings"),
            "error": editor.get("error", ""),
            "shot": req["shot"] if shot_ok else "",
        }
        # The editor is the same QML on every surface (harness: shown in
        # the Configuration page pane).
        for surface in (
            Surface.CONFIG_PAGE,
            Surface.PANE_BUTTON_MAP,
            Surface.PANE_LOGICAL,
        ):
            record(
                req["tag"], surface, req["input"], "open_editor", ok and shot_ok, detail
            )
        if not (ok and shot_ok):
            bad.append((req["tag"], detail))
    assert not bad, bad
