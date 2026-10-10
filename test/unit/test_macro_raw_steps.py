# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Macro steps the program can't read, Save of missing Logical Device steps
and the start of a new vJoy step.

05 S117 (R11c): a step that can't be read, or of an unknown type, doesn't
stop the profile opening; it is kept and saved back as it was, does nothing
at Run, and the editor and rule checks say so. Save keeps a Logical Device
step whose control is missing.
05 S113 (R6): a new vJoy macro step starts on the first output a vJoy output
module claims; with none claimed it is added with a notice.
"""

from __future__ import annotations

import pathlib
import uuid
from types import SimpleNamespace
from xml.etree import ElementTree

import pytest

from action_plugins import macro as macro_plugin
from gremlin import macro
from gremlin.macro_raw import RawMacroStep
from gremlin.profile import Profile
from gremlin.types import InputType

_MACRO_ID = uuid.UUID("8759f48d-8879-488a-9895-07503bf0dc0c")
_ROOT_ID = uuid.UUID("66cfeb76-bc9d-4754-925c-3563654db158")
_DEVICE = "97b77b40-07d8-11f0-8028-444553540000"

_PAUSE = """
            <macro-action type="pause">
                <property type="float">
                    <name>duration</name>
                    <value>0.5</value>
                </property>
            </macro-action>"""

# A key step without its is-pressed property.
_KEY_NO_PRESSED = """
            <macro-action type="key">
                <property type="int">
                    <name>scan-code</name>
                    <value>32</value>
                </property>
                <property type="bool">
                    <name>is-extended</name>
                    <value>False</value>
                </property>
            </macro-action>"""

# A key step with a scan code no key has.
_KEY_BAD_SCAN = """
            <macro-action type="key">
                <property type="int">
                    <name>scan-code</name>
                    <value>4095</value>
                </property>
                <property type="bool">
                    <name>is-extended</name>
                    <value>True</value>
                </property>
                <property type="bool">
                    <name>is-pressed</name>
                    <value>True</value>
                </property>
            </macro-action>"""

_UNKNOWN_TYPE = """
            <macro-action type="teleport" speed="9">
                <property type="int">
                    <name>where</name>
                    <value>42</value>
                </property>
            </macro-action>"""

# A Logical Device step naming a control (by permanent id) the Logical
# Device doesn't have.
_LOGICAL_MISSING = """
            <macro-action type="logical-device" uid="no-such-control">
                <property type="input_type">
                    <name>input-type</name>
                    <value>button</value>
                </property>
                <property type="int">
                    <name>input-id</name>
                    <value>7</value>
                </property>
                <property type="bool">
                    <name>value</name>
                    <value>True</value>
                </property>
            </macro-action>"""


def _profile_text(steps: str) -> str:
    return f"""<?xml version="1.0" ?>
<profile version="14">
    <settings>
        <startup-mode>Default</startup-mode>
        <macro-default-delay>0.05</macro-default-delay>
    </settings>
    <inputs>
        <input>
            <device-id>{_DEVICE}</device-id>
            <input-type>button</input-type>
            <mode>Default</mode>
            <input-id>1</input-id>
            <action-configuration>
                <root-action>{_ROOT_ID}</root-action>
                <behavior>button</behavior>
            </action-configuration>
        </input>
    </inputs>
    <library>
        <action id="{_MACRO_ID}" type="macro">
            <property type="bool">
                <name>is-exclusive</name>
                <value>False</value>
            </property>
            <property type="bool">
                <name>is-preemptive</name>
                <value>False</value>
            </property>
            <property type="string">
                <name>repeat-mode</name>
                <value>Single</value>
            </property>
            <property type="int">
                <name>repeat-count</name>
                <value>1</value>
            </property>
            <property type="float">
                <name>repeat-delay</name>
                <value>0.1</value>
            </property>{steps}
            <property type="string">
                <name>action-label</name>
                <value>Macro</value>
            </property>
            <property type="activation-mode">
                <name>activation-mode</name>
                <value>press</value>
            </property>
        </action>
        <action id="{_ROOT_ID}" type="root">
            <actions>
                <action-id>{_MACRO_ID}</action-id>
            </actions>
            <property type="string">
                <name>action-label</name>
                <value></value>
            </property>
            <property type="activation-mode">
                <name>activation-mode</name>
                <value>disallowed</value>
            </property>
        </action>
    </library>
    <modes>
        <mode>Default</mode>
    </modes>
    <scripts/>
</profile>
"""


def _steps_of(path: pathlib.Path) -> list[ElementTree.Element]:
    root = ElementTree.parse(path).getroot()
    for action in root.iter("action"):
        if action.get("type") == "macro":
            return list(action.iter("macro-action"))
    raise AssertionError("no macro in the file")


def _same(a: ElementTree.Element, b: ElementTree.Element) -> bool:
    """Same element: tag, attributes, children and text (indentation aside)."""

    def flat(e: ElementTree.Element) -> str:
        return ElementTree.canonicalize(
            ElementTree.tostring(e, encoding="unicode"), strip_text=True
        )

    return flat(a) == flat(b)


def _load_and_save(tmp_path: pathlib.Path, steps: str) -> tuple[Profile, pathlib.Path]:
    src = tmp_path / "macro_in.xml"
    src.write_text(_profile_text(steps), encoding="utf-8")
    p = Profile()
    p.from_xml(src)
    out = tmp_path / "macro_out.xml"
    p.to_xml(out)
    return p, out


@pytest.mark.parametrize(
    "bad",
    [_KEY_NO_PRESSED, _KEY_BAD_SCAN, _UNKNOWN_TYPE],
    ids=["missing-is-pressed", "unknown-scan-code", "unknown-step-type"],
)
def test_an_unreadable_step_opens_and_saves_back_unchanged(
    tmp_path: pathlib.Path, bad: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """05 S117: the profile opens, the step is kept and written back as it
    was, between the steps around it."""
    from gremlin import keyboard

    # Windows' keyboard layout has no key for scan code 4095 (extended).
    real = keyboard._scan_code_to_virtual_code
    monkeypatch.setattr(
        keyboard,
        "_scan_code_to_virtual_code",
        lambda code, ext: 0xFF if code == 4095 else real(code, ext),
    )
    monkeypatch.delitem(keyboard.g_scan_code_to_key, (4095, True), raising=False)
    p, out = _load_and_save(tmp_path, _PAUSE + bad + _PAUSE)

    data = p.library.get_action(_MACRO_ID)
    assert [type(s) for s in data.actions] == [
        macro.PauseAction,
        RawMacroStep,
        macro.PauseAction,
    ]
    raw = data.actions[1]
    assert "kept as it was" in raw.problem

    original = _steps_of(tmp_path / "macro_in.xml")
    saved = _steps_of(out)
    assert len(saved) == 3
    assert _same(saved[1], original[1])


def test_an_unreadable_step_does_nothing_at_run_and_is_reported(
    tmp_path: pathlib.Path,
) -> None:
    """05 S117: not played; the editor (user feedback, the step's model) and
    the rule checks say so."""
    from gremlin import validate

    p, _ = _load_and_save(tmp_path, _PAUSE + _UNKNOWN_TYPE)
    data = p.library.get_action(_MACRO_ID)

    functor = macro_plugin.MacroFunctor(data)
    assert not any(isinstance(s, RawMacroStep) for s in functor.macro.sequence)

    feedback = data.user_feedback()
    assert [f.feedback_type.name for f in feedback] == ["Warning"]
    assert "teleport" in feedback[0].message

    model = macro_plugin.MacroModel.model_lookup[RawMacroStep.tag]
    assert model is macro_plugin.RawStepModel
    assert "teleport" in model.problem.fget(SimpleNamespace(_action=data.actions[1]))

    problems = validate.profile(p)
    code = "PROFILE-MACRO-STEP-UNREADABLE"
    found = [x for x in problems if validate.code_of(x) == code]
    assert len(found) == 1 and "teleport" in found[0]
    assert validate.is_warning(found[0])

    qml = (
        pathlib.Path(macro_plugin.__file__).parent / "MacroAction.qml"
    ).read_text(encoding="utf-8")
    assert 'roleValue: "unreadable"' in qml
    assert "modelData.problem" in qml


def test_save_keeps_a_logical_device_step_whose_control_is_missing(
    tmp_path: pathlib.Path,
) -> None:
    """05 S117: only never-filled-in steps are left out on Save."""
    from gremlin.logical_device import LogicalDevice

    LogicalDevice().reset()
    p, out = _load_and_save(tmp_path, _PAUSE + _LOGICAL_MISSING)

    step = p.library.get_action(_MACRO_ID).actions[1]
    assert isinstance(step, macro.LogicalDeviceAction)
    assert step.is_missing()

    saved = _steps_of(out)
    assert [s.get("type") for s in saved] == ["pause", "logical-device"]
    assert saved[1].get("uid") == "no-such-control"


def test_save_still_leaves_out_a_never_filled_in_step() -> None:
    """A Logical Device step that never got a control is not written."""
    from gremlin.logical_device import LogicalDevice

    LogicalDevice().reset()
    data = macro_plugin.MacroData()
    blank = macro.LogicalDeviceAction(InputType.JoystickButton, None, False)
    data.actions = [macro.PauseAction(0.5), blank]
    node = data._to_xml()
    assert [s.get("type") for s in node.iter("macro-action")] == ["pause"]


# --- 05 S113: a new vJoy step starts on the first claimed output --------------


def _fake_vjoy(monkeypatch: pytest.MonkeyPatch, claims: dict[int, dict]) -> None:
    """vJoy output modules with these claims; each vJoy has 32 buttons,
    8 axes and 4 hats and is used as an output."""
    from gremlin import device_initialization
    from gremlin.modules import output

    monkeypatch.setattr(
        output,
        "vjoy_modules",
        lambda: sorted(
            (vid, SimpleNamespace(claim=claim)) for vid, claim in claims.items()
        ),
    )
    monkeypatch.setattr(
        output,
        "vjoy_driver_ids",
        lambda _vid: {
            "axes": set(range(1, 9)),
            "buttons": set(range(1, 33)),
            "hats": set(range(1, 5)),
        },
    )
    monkeypatch.setattr(
        device_initialization,
        "output_vjoy_devices",
        lambda: [SimpleNamespace(vjoy_id=vid) for vid in claims],
    )


def _add_vjoy_step() -> tuple[list, list]:
    from gremlin.signal import signal

    steps: list = []
    shown: list = []

    def note(_title: str, text: str) -> None:
        shown.append(text)

    fake = SimpleNamespace(
        action_lookup=macro_plugin.MacroModel.action_lookup,
        _action_list_model=SimpleNamespace(append=steps.append),
        changed=SimpleNamespace(emit=lambda: None),
    )
    signal.showNotification.connect(note)
    try:
        macro_plugin.MacroModel.addAction(fake, "vjoy")
    finally:
        signal.showNotification.disconnect(note)
    return steps, shown


def test_a_new_vjoy_step_starts_on_the_first_claimed_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_vjoy(monkeypatch, {3: {"buttons": [5]}})
    steps, shown = _add_vjoy_step()
    assert shown == []
    step = steps[0]
    assert (step.vjoy_id, step.input_type, step.input_id) == (
        3,
        InputType.JoystickButton,
        5,
    )


def test_a_new_vjoy_step_with_nothing_claimed_is_added_with_a_notice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_vjoy(monkeypatch, {1: {}})
    steps, shown = _add_vjoy_step()
    assert len(steps) == 1 and isinstance(steps[0], macro.VJoyAction)
    assert shown == ["Claim an output on a vJoy output module first."]


def test_the_macro_editor_removes_a_step_with_remove_step() -> None:
    """R11a: the slot is removeStep (no behaviour change)."""
    # removeAction is ActionModel's own slot (removes an action); the
    # macro model no longer hides it with a step-removing one.
    assert hasattr(macro_plugin.MacroModel, "removeStep")
    assert "removeAction" not in vars(macro_plugin.MacroModel)
    qml = (
        pathlib.Path(macro_plugin.__file__).parent / "MacroAction.qml"
    ).read_text(encoding="utf-8")
    assert "_root.action.removeStep(index)" in qml
    assert "removeAction" not in qml
