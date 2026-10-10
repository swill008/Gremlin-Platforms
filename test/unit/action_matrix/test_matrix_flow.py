# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Action editor matrix: the flow actions (Chain, Condition, Tempo, Double
Tap, Smart Toggle, Macro, Reference, Root) on every surface that takes
their input kind.

Each case: Add Action, every editable field changed and read back (then put
back), the child actions a container needs to show output (Map to vJoy),
save and reload, a fake input through the real runner with the expected
vJoy writes, then Undo/Redo of one more edit on the panes (05 S35: the live
editor has no Undo). The editor QML is loaded for every action and kind in
one off-screen program run.

Expected outputs come from each action's own rules (05 S89 for Chain, the
Tempo / Double Tap / Smart Toggle state machines, 05 S60a for Reference,
05 S113/S116 for a new macro vJoy step). Every step is record()ed.
"""

from __future__ import annotations

import json
import pathlib
import uuid
from typing import Any

import pytest

from test.unit.action_matrix import harness  # pyright: ignore[reportMissingImports]
from test.unit.action_matrix.harness import (  # pyright: ignore[reportMissingImports]
    Surface,
    allowed,
    open_editors,
    plugin,
    record,
    settle,
)

TAGS = (
    "chain",
    "condition",
    "tempo",
    "double-tap",
    "smart-toggle",
    "macro",
    "reference",
    "root",
)
MAP = "map-to-vjoy"
SHOTS = harness.DEFAULT_RESULTS.parent / "shots"

# vJoy button/axis/hat ids the children write to.
FIRST, SECOND, TARGET, UNDO_ID = 3, 4, 5, 9

# Each container's child slots: the first gets FIRST, the second SECOND.
CHILD_SLOTS: dict[str, tuple[str, ...]] = {
    "chain": ("0", "1"),
    "condition": ("true", "false"),
    "tempo": ("short", "long"),
    "double-tap": ("single", "double"),
    "smart-toggle": ("children",),
    "root": ("children",),
}

# Field values where a dummy of the type isn't a valid choice.
FIELD_VALUES: dict[tuple[str, str], Any] = {
    ("condition", "logicalOperator"): "1",  # Any (default All = "2")
    ("tempo", "activateOn"): "press",
    ("double-tap", "activateOn"): "combined",
    ("macro", "repeatMode"): "count",
}

# Set first (and put back last): other fields depend on them.
FIRST_FIELDS = ("repeatMode",)

# Timing actions run with a short threshold so presses stay quick.
TIMING_FIELD = {
    "tempo": "threshold",
    "double-tap": "threshold",
    "smart-toggle": "delay",
}
THRESHOLD = 0.2
SHORT, LONG = 0.04, 0.4


# The input kinds each allows (the plugins load only once the program's
# configuration is up, after collection; test_flow_kinds checks this).
KINDS: dict[str, tuple[str, ...]] = {
    "chain": ("button", "key"),
    "condition": ("axis", "button", "hat", "key"),
    "tempo": ("button", "key"),
    "double-tap": ("button", "key"),
    "smart-toggle": ("button", "key"),
    "macro": ("button", "key"),
    "reference": ("axis", "button", "hat", "key"),
    "root": ("axis", "button", "hat", "key"),
}


def _flow_cases() -> list[tuple[str, str, str]]:
    return [
        (tag, kind, surface)
        for tag in TAGS
        for surface in Surface.ALL
        for kind in harness.SURFACE_INPUTS[surface]
        if kind in KINDS[tag]
    ]


def test_flow_kinds() -> None:
    every = dict(harness.actions())
    assert {tag: every[tag] for tag in TAGS} == KINDS
    assert all(allowed(t, k, s) for t, k, s in _flow_cases())


# +-------------------------------------------------------------------------
# | Helpers


def _on(kind: str) -> Any:  # noqa: ANN401
    return {"axis": 0.5, "hat": "north"}.get(kind, True)


def _off(kind: str) -> Any:  # noqa: ANN401
    return {"axis": 0.0, "hat": "center"}.get(kind, False)


def _drive(case: Any, steps: list[tuple[Any, float]]) -> list[tuple]:  # noqa: ANN401
    """OK, then Run with each (value, wait-after) in order; the outputs.
    Like Case.run, with a wait of its own after each event (timing
    actions need held presses)."""
    assert case.commit(), "OK wrote nothing"
    with harness._running(case.profile, case._watched) as collected:  # noqa: SLF001
        from gremlin import event_handler

        handler = event_handler.EventHandler()
        for value, wait in steps:
            handler.process_event(case._event(case.input_type, value))  # noqa: SLF001
            settle(wait)
        settle(0.1)
        return collected()


def _writes(sent: list[tuple]) -> list[tuple]:
    """vJoy writes as (kind, id, value)."""
    return [
        (s[2], s[3], s[4])
        for s in sent
        if s[0] in ("write_vjoy", "write_vjoy_axis_linear") and len(s) >= 5
    ]


def _buttons(sent: list[tuple], vjoy_input: int) -> list[bool]:
    return [bool(v) for k, i, v in _writes(sent) if k == "button" and i == vjoy_input]


def _ids(sent: list[tuple]) -> set[int]:
    return {i for _k, i, _v in _writes(sent)}


def _add_child(case: Any, slot: str, vjoy_input: int) -> tuple[bool, str]:  # noqa: ANN401
    """Add Action (Map to vJoy) inside the case's container, on vjoy_input."""
    model = case.model()
    if case.tag == "chain" and slot != "0":
        while model.chainCount <= int(slot):
            model.addSequence()
            settle()
            model = case.model()
    model.appendAction(plugin(MAP).name, slot)
    settle()
    kids = case.model().getActions(slot)
    if not kids:
        return False, f"no child in {slot}"
    kids[-1].setProperty("vjoyInputId", vjoy_input)
    settle()
    got = case.model().getActions(slot)[-1].property("vjoyInputId")
    return got == vjoy_input, f"{slot}: Map to vJoy on {got}"


def _other_input(case: Any) -> Any:  # noqa: ANN401
    """A second input of the same kind, with a Map to vJoy on TARGET, as
    the Configuration page adds it. Returns its Map to vJoy's data."""
    import dill
    from gremlin.logical_device import LogicalDevice
    from gremlin.ui.profile import InputItemModel

    guid, kind, _input_id, mode = case.key
    if case.surface == Surface.PANE_KEYBOARD:
        key = (dill.UUID_Keyboard, kind, (31, False), mode)
    elif case.surface == Surface.PANE_LOGICAL:
        key = (guid, kind, LogicalDevice().create(kind).id, mode)
    else:
        key = (guid, kind, 2, mode)
    item = case.profile.get_input_item(*key, create_if_missing=True)
    item.add_item_binding()
    owner = InputItemModel(item, 0, None)
    case._kept.append(owner)  # noqa: SLF001
    root = owner.data(owner.index(0, 0), 0x0100 + 1).rootAction
    root.appendAction(plugin(MAP).name, "children")
    settle()
    child = root.getActions("children")[-1]
    child.setProperty("vjoyInputId", TARGET)
    settle()
    return child.action_data


# +-------------------------------------------------------------------------
# | Run expectations, per action


def _run_checks(case: Any) -> tuple[bool | None, Any]:  # noqa: ANN401
    """Runs the case's scenarios; (ok, observed). ok None: not checked."""
    tag, kind = case.tag, case.input_type
    on, off = _on(kind), _off(kind)
    if tag in ("root", "condition", "reference"):
        want = TARGET if tag == "reference" else FIRST
        sent = _drive(case, [(on, 0.1), (off, 0.1)])
        ids = _ids(sent)
        # Condition with no checks and "All": all([]) is true, so the true
        # branch runs, never the false one.
        ok = want in ids and (tag != "condition" or SECOND not in ids)
        if kind in ("button", "key"):
            ok = ok and _buttons(sent, want) == [True, False]
        return ok, _writes(sent)
    if tag == "chain":
        # 05 S89: each press/release goes to the next sequence in turn.
        sent = _drive(case, [(True, SHORT), (False, SHORT)] * 2)
        ok = _buttons(sent, FIRST) == [True, False] and _buttons(sent, SECOND) == [
            True,
            False,
        ]
        order = [i for _k, i, _v in _writes(sent)]
        return ok and order[:2] == [FIRST, FIRST], _writes(sent)
    if tag == "tempo":
        # Release mode: a short press pulses "short"; a held one presses
        # "long" at the threshold and releases it on release.
        tap = _drive(case, [(True, SHORT), (False, LONG)])
        hold = _drive(case, [(True, LONG), (False, SHORT)])
        ok = (
            _buttons(tap, FIRST) == [True, False]
            and not _buttons(tap, SECOND)
            and _buttons(hold, SECOND) == [True, False]
            and not _buttons(hold, FIRST)
        )
        return ok, {"tap": _writes(tap), "hold": _writes(hold)}
    if tag == "double-tap":
        # Exclusive: one tap pulses "single" after the threshold; two quick
        # taps run "double" only.
        one = _drive(case, [(True, SHORT), (False, LONG)])
        two = _drive(
            case, [(True, SHORT), (False, SHORT), (True, SHORT), (False, LONG)]
        )
        ok = (
            _buttons(one, FIRST) == [True, False]
            and not _buttons(one, SECOND)
            and _buttons(two, SECOND) == [True, False]
            and not _buttons(two, FIRST)
        )
        return ok, {"single": _writes(one), "double": _writes(two)}
    if tag == "smart-toggle":
        # A tap toggles: held on after the first tap, off after the second;
        # a press held past the delay is momentary.
        taps = _drive(case, [(True, SHORT), (False, 0.3), (True, SHORT), (False, 0.3)])
        hold = _drive(case, [(True, LONG), (False, SHORT)])
        ok = _buttons(taps, FIRST) == [True, False] and _buttons(hold, FIRST) == [
            True,
            False,
        ]
        first_tap = _drive(case, [(True, SHORT), (False, 0.3)])
        ok = ok and _buttons(first_tap, FIRST) == [True]
        return ok, {
            "two taps": _writes(taps),
            "one tap": _writes(first_tap),
            "hold": _writes(hold),
        }
    if tag == "macro":
        # A new vJoy step: vJoy 1 button 1, Pressed (05 S113 with nothing
        # claimed keeps its own default; 05 S116 starts it on Pressed).
        sent = _drive(case, [(True, 0.3), (False, 0.2)])
        return ("button", 1, True) in _writes(sent), _writes(sent)
    return None, "no expectation"


# +-------------------------------------------------------------------------
# | The flow, one case


def _fields_step(case: Any, rec: Any) -> None:  # noqa: ANN401
    """Each field changed and read back, then all put back (in reverse:
    Macro's repeat count and delay take a value only in a mode that uses
    them, so its mode changes first and goes back last)."""
    fields = sorted(case.fields(), key=lambda f: f["name"] not in FIRST_FIELDS)
    if not fields:
        rec("fields", None, "no editable fields")
        return
    bad = []
    seen = []
    for field in fields:
        name, before = field["name"], field["value"]
        value = FIELD_VALUES.get((case.tag, name))
        changed, _b, after = case.set(name, value)
        seen.append(f"{name}: {before!r} -> {after!r}")
        if not changed or (value is not None and after != value):
            bad.append(f"{name} didn't change ({before!r} -> {after!r})")
    for field in reversed(fields):
        name, before = field["name"], field["value"]
        _c, _b, restored = case.set(name, before)
        if restored != before:
            bad.append(f"{name} didn't go back to {before!r} ({restored!r})")
    rec("fields", not bad, bad or seen)
    assert not bad, bad


def _undo_edit(case: Any) -> str:  # noqa: ANN401
    """One more edit for Undo/Redo: a field, or a child's vJoy input."""
    fields = sorted(case.fields(), key=lambda f: f["name"] not in FIRST_FIELDS)
    if fields:
        name = fields[0]["name"]
        value = FIELD_VALUES.get((case.tag, name))
        changed, before, after = case.set(name, value)
        return f"{name} {before!r} -> {after!r}"
    slot = CHILD_SLOTS[case.tag][0]
    child = case.model().getActions(slot)[-1]
    child.setProperty("vjoyInputId", UNDO_ID)
    settle()
    return f"{slot} child vjoyInputId -> {UNDO_ID}"


# Real defects found (kept as strict xfails until fixed). AE-reference-1
# (a Reference on a keyboard key offered nothing, 05 S60) is fixed.
XFAILS: dict[tuple[str, str, str], str] = {}


def _params() -> list[Any]:
    return [
        pytest.param(
            *case,
            marks=[pytest.mark.xfail(strict=True, reason=XFAILS[case])]
            if case in XFAILS
            else [],
        )
        for case in _flow_cases()
    ]


@pytest.mark.parametrize(("tag", "kind", "surface"), _params())
def test_flow_action(matrix: Any, tag: str, kind: str, surface: str) -> None:  # noqa: ANN401
    def rec(step: str, ok: bool | None, detail: object = "") -> None:
        record(tag, surface, kind, step, ok, detail)

    case = matrix.open(tag, kind, surface)
    rec("add", case.action.tag == tag, f"{case.action.tag} added")
    assert case.action.tag == tag

    _fields_step(case, rec)

    if tag == "reference":
        _reference_flow(case, rec)
        return

    for slot, vjoy_input in zip(CHILD_SLOTS.get(tag, ()), (FIRST, SECOND)):
        ok, detail = _add_child(case, slot, vjoy_input)
        rec(f"child {slot}", ok, detail)
        assert ok, detail
    if tag == "macro":
        case.model().addAction("vjoy")
        settle()
        rec("macro vjoy step", True, "addAction('vjoy')")
    if tag in TIMING_FIELD:
        case.set(TIMING_FIELD[tag], THRESHOLD)

    ok, diff = case.save_reload()
    rec("save_reload", ok, diff)
    assert ok, diff

    ok_run, observed = _run_checks(case)
    rec("run", ok_run, observed)
    assert ok_run, observed

    case.reopen()
    edit = _undo_edit(case)
    ok_undo, detail = case.undo_redo()
    rec("undo_redo", ok_undo, detail or edit)
    if surface == Surface.CONFIG_PAGE:
        assert ok_undo is None
    else:
        assert ok_undo, detail


def _reference_flow(case: Any, rec: Any) -> None:  # noqa: ANN401
    """Reference: the placeholder is saved, then pointed at another input's
    Map to vJoy (05 S60a: its list never offers a Root or a Reference)."""
    # A placeholder is never saved (05 map: Reference "never runs or saves").
    ok, diff = case.save_reload()
    left_out = not ok and diff == "reference isn't in the saved file"
    rec("save_reload placeholder", left_out, diff or "saved")
    assert left_out, diff
    case.reopen()
    if case.surface == Surface.CONFIG_PAGE:
        # A save prunes unfinished actions from the inputs (05 S66, Save
        # without them); the live editor has no draft to keep it, so the
        # placeholder is gone and is added again.
        kids = case.root_model().action_data.get_actions()[0]
        gone = all(a is not case.action for a in kids)
        rec("placeholder after save", gone, "pruned from the live input")
        case.action = case._add()  # noqa: SLF001
    target = _other_input(case)
    model = case.model()
    offered = list(model.actions._values)  # noqa: SLF001
    library = case.profile.library
    tags = {library.get_action(uuid.UUID(v)).tag for v in offered}
    ok_list = str(target.id) in offered and not tags & {"root", "reference"}
    why = {
        "offered": sorted(tags),
        "target behavior": str(target.behavior_type),
        "reference input type": str(model.input_type),
        "target in use": target.id in library.in_use(),
    }
    rec("reference list", ok_list, why)
    assert ok_list, why
    model.referenceAction(str(target.id))
    settle()
    if case.surface == Surface.CONFIG_PAGE:
        rec("undo_redo", None, "the live editor has no Undo (05 S35)")
    else:
        before = case.xml()
        ok_undo, detail = case.undo_redo()
        rec("undo_redo", ok_undo, detail or "placeholder <-> reference")
        assert ok_undo, detail
        assert case.xml() != before
        case.reopen()
    ok, diff = _save_reload_shared(case)
    rec("save_reload", ok, diff)
    assert ok, diff
    ok_run, observed = _run_checks(case)
    rec("run", ok_run, observed)
    assert ok_run, observed


def _save_reload_shared(case: Any) -> tuple[bool, str]:  # noqa: ANN401
    """Case.save_reload for an input whose Reference became the shared Map
    to vJoy (the file holds no "reference" any more): saved, opened, saved
    again the same, and the input holds the target's id."""
    from gremlin.profile import Profile

    if not case.commit():
        return False, "OK wrote nothing"
    first = case.tmp / "reference-1.xml"
    second = case.tmp / "reference-2.xml"
    case.profile.to_xml(first)
    back = Profile()
    back.from_xml(first)
    back.to_xml(second)
    a = harness._canon_text(first.read_text(encoding="utf-8-sig"))  # noqa: SLF001
    b = harness._canon_text(second.read_text(encoding="utf-8-sig"))  # noqa: SLF001
    if 'type="reference"' in a or "<reference" in a:
        return False, "a Reference placeholder was saved"
    snap = json.loads(case.xml())
    if not snap or MAP not in json.dumps(snap):
        return False, f"the input holds no {MAP}: {snap}"
    return a == b, "" if a == b else "saved and reloaded files differ"


# +-------------------------------------------------------------------------
# | The editor QML, every flow action and kind, one off-screen run


def test_flow_editors_qml(tmp_path: pathlib.Path) -> None:
    kinds = dict(harness.actions())
    requests = [
        {"tag": tag, "input": kind, "shot": str(SHOTS / f"{tag}_{kind}.png")}
        for tag in TAGS
        for kind in kinds[tag]
    ]
    got = open_editors(requests, tmp_path)
    bad = []
    for req, editor in zip(requests, got, strict=True):
        ok = bool(editor.get("ok")) and not editor.get("warnings")
        record(
            req["tag"],
            "editor_qml",
            req["input"],
            "open_editor",
            ok,
            {
                "qml": editor.get("qml"),
                "warnings": editor.get("warnings"),
                "error": editor.get("error", ""),
                "shot": editor.get("shot"),
            },
        )
        if not ok:
            bad.append(editor)
    assert not bad, bad


def test_root_action_qml_is_used() -> None:
    """Root has no editor file of its own (R1, removed): the pane shows a
    binding's root through qml/RootActionNode.qml (InputItemBinding.qml);
    only ActionNode loads an action's qmlPath, and only for children, which a
    Root never is. RootAction.qml is gone and nothing names it."""
    root = harness.ROOT
    gone = not (root / "action_plugins" / "root" / "RootAction.qml").exists()
    uses = [
        p.relative_to(root).as_posix()
        for folder in ("qml", "action_plugins", "gremlin")
        for p in (root / folder).rglob("*")
        if p.suffix in (".qml", ".py")
        and "RootAction.qml" in p.read_text(encoding="utf-8", errors="ignore")
    ]
    record("root", "editor_qml", "-", "RootAction.qml gone", None, uses)
    assert gone and uses == [], uses
