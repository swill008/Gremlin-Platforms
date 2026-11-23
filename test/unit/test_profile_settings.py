# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from gremlin.profile import Profile


def _roundtrip_profile(profile: Profile) -> Profile:
    """Serialize profile to a temp file and load it back, then returning
    the new Profile.

    Args:
        profile: The Profile to serialize and reload.

    Returns:
        The reloaded Profile.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "roundtrip.xml"
        profile.to_xml(str(out))
        new_profile = Profile()
        new_profile.from_xml(str(out))
        return new_profile


def test_settings_defaults_roundtrip() -> None:
    p = Profile()
    assert p.settings.startup_mode == "Last Active"
    assert p.settings.macro_default_delay is None  # Follows Options.
    assert p.settings.vjoy_as_input == {}
    assert p.settings.vjoy_initial_values == {}

    p2 = _roundtrip_profile(p)
    assert p2.settings.startup_mode == "Last Active"
    assert p2.settings.macro_default_delay == p.settings.macro_default_delay
    assert p2.settings.vjoy_as_input == {}
    assert p2.settings.vjoy_initial_values == {}


def test_settings_modifications_roundtrip() -> None:
    p = Profile()
    p.settings.startup_mode = "Default"
    p.settings.macro_default_delay = 0.1
    p.settings.vjoy_as_input = {1: True, 2: False}
    p.settings.set_initial_vjoy_axis_value(1, 0, 0.25)
    p.settings.set_initial_vjoy_axis_value(1, 1, -0.5)
    p.settings.set_initial_vjoy_axis_value(2, 0, 1.0)

    assert p.settings.startup_mode == "Default"
    assert p.settings.macro_default_delay == 0.1
    assert p.settings.vjoy_as_input.get(1) is True
    assert p.settings.vjoy_as_input.get(2, False) is False
    assert p.settings.get_initial_vjoy_axis_value(1, 0) == 0.25
    assert p.settings.get_initial_vjoy_axis_value(1, 1) == -0.5
    assert p.settings.get_initial_vjoy_axis_value(2, 0) == 1.0

    p2 = _roundtrip_profile(p)
    assert p2.settings.startup_mode == "Default"
    assert p2.settings.macro_default_delay == 0.1
    assert p2.settings.vjoy_as_input.get(1) is True
    assert p2.settings.vjoy_as_input.get(2, False) is False
    assert p2.settings.get_initial_vjoy_axis_value(1, 0) == 0.25
    assert p2.settings.get_initial_vjoy_axis_value(1, 1) == -0.5
    assert p2.settings.get_initial_vjoy_axis_value(2, 0) == 1.0


def test_vjoy_initial_values_container_behavior() -> None:
    p = Profile()

    assert p.settings.get_initial_vjoy_axis_value(3, 5) == 0.0

    p.settings.set_initial_vjoy_axis_value(3, 5, 0.75)
    assert p.settings.get_initial_vjoy_axis_value(3, 5) == 0.75

    p.settings.set_initial_vjoy_axis_value(3, 5, -0.25)
    assert p.settings.get_initial_vjoy_axis_value(3, 5) == -0.25


def test_load_profile_settings_from_existing_xml(xml_dir: Path) -> None:
    xml_path = xml_dir / "profile_realistic.xml"
    assert xml_path.exists(), "Expected sample XML profile to exist"

    p = Profile()
    p.from_xml(str(xml_path))

    assert p.settings.startup_mode == "Default"
    # A saved delay with no "options" source is the profile's own, 0.05 too.
    assert p.settings.macro_default_delay == 0.05

    assert p.settings.vjoy_as_input == {}
    assert p.settings.vjoy_initial_values == {}


def test_macro_delay_follows_options_unless_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin import profile

    monkeypatch.setattr(profile, "options_macro_delay", lambda: 0.2)
    p = Profile()
    assert p.settings.effective_macro_delay() == 0.2

    # Saved following Options: older builds still get a number to read.
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "follow.xml"
        p.to_xml(str(out))
        text = out.read_text(encoding="utf-8")
        assert "<macro-default-delay>0.2</macro-default-delay>" in text
        assert "<macro-delay-source>options</macro-delay-source>" in text
        again = Profile()
        again.from_xml(str(out))
        assert again.settings.macro_default_delay is None

    p.settings.macro_default_delay = 0.3
    p2 = _roundtrip_profile(p)
    assert p2.settings.macro_default_delay == 0.3
    assert p2.settings.effective_macro_delay() == 0.3


def test_a_saved_own_delay_of_0_05_stays_0_05(monkeypatch: pytest.MonkeyPatch) -> None:
    from gremlin import profile

    monkeypatch.setattr(profile, "options_macro_delay", lambda: 0.2)
    p = Profile()
    p.settings.macro_default_delay = 0.05  # the user's own choice
    again = _roundtrip_profile(p)
    assert again.settings.macro_default_delay == 0.05
    assert again.settings.effective_macro_delay() == 0.05


def test_settings_model_switches_between_options_and_own(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin import profile, shared_state
    from gremlin.ui.profile import ProfileSettingsModel

    monkeypatch.setattr(profile, "options_macro_delay", lambda: 0.2)
    p = Profile()
    monkeypatch.setattr(shared_state, "current_profile", p)
    model = ProfileSettingsModel()
    assert model.property("macroDelayFromOptions") is True
    assert model.property("macroDefaultDelay") == 0.2
    model.setProperty("macroDelayFromOptions", False)  # Starts from today's value.
    assert p.settings.macro_default_delay == 0.2
    model.setProperty("macroDefaultDelay", 0.5)
    assert model.property("macroDelayFromOptions") is False
    model.setProperty("macroDelayFromOptions", True)
    assert p.settings.macro_default_delay is None


# +-------------------------------------------------------------------------
# | The control API reaches the vJoy Initial Values boxes (13 D-13-INITIAL-VALUES)

_API_CODE = r"""
import importlib.util, json, os, sys
ROOT = sys.argv[1]
sys.path.insert(0, ROOT)
spec = importlib.util.spec_from_file_location(
    "fake_hardware", os.path.join(ROOT, "test", "fake_hardware.py"))
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()
import gremlin.ui.update_model as um
um.UpdateModel.startup = lambda self, *a, **k: None
import joystick_gremlin
from PySide6 import QtTest
from gremlin import shared_state
from gremlin.ui import control_windows
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
QtTest.QTest.qWait(500)

out = {}
profile = shared_state.current_profile
# Profile Settings is a window of its own (04 S96): window.open opens it
# at General, window.press moves it to vJoy (13 S29).
out["open"] = control_windows.call_open({"id": "tools.profileSettings"})
QtTest.QTest.qWait(500)
title = "Profile Settings"
out["press"] = control_windows.call_press(
    {"window": title, "button": "profileSettingsSection:vjoy"})
QtTest.QTest.qWait(500)
rows = control_windows.call_read({"window": title})["items"]
out["boxes"] = {
    r["name"]: r["text"] for r in rows
    if r["kind"] == "field" and r["name"].startswith("vjoyInitialValue:")
}
name = "vjoyInitialValue:1:X Axis"
out["name"] = name
out["before"] = profile.settings.get_initial_vjoy_axis_value(1, 1)
try:
    out["type"] = control_windows.call_type(
        {"window": title, "field": name, "text": "0.5"})
except Exception as e:
    out["type-error"] = str(e)
QtTest.QTest.qWait(200)
out["after"] = profile.settings.get_initial_vjoy_axis_value(1, 1)
out["boxes-after"] = {
    r["name"]: r["text"]
    for r in control_windows.call_read({"window": title})["items"]
    if r["kind"] == "field" and r["name"].startswith("vjoyInitialValue:")
}
print("OUT " + json.dumps(out), flush=True)
os._exit(0)
"""


def test_initial_value_boxes_are_reachable_by_the_api(tmp_path: Path) -> None:
    """The real program off-screen (stand-in vJoy 1): the Profile Settings
    window opened by window.open tools.profileSettings and moved to its vJoy
    section by window.press, window.read lists each initial value box
    as vjoyInitialValue:<vJoy>:<axis> with its value, and window.type sets
    the profile's initial value through the box."""
    import json
    import os
    import sys

    import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
    import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

    root = Path(__file__).parents[2]
    home = tmp_path / "home"
    (home / "Gremlin Platforms").mkdir(parents=True)
    env = dict(
        os.environ,
        USERPROFILE=str(home),
        QT_QPA_PLATFORM="offscreen",
        HTTPS_PROXY="http://127.0.0.1:9",
    )
    done = proc_tree.run(
        [sys.executable, "-c", _API_CODE, str(root)],
        cwd=root,
        env=env,
        text=True,
        timeout=120,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("OUT ")]
    assert lines, smoke_report.explain(done)
    out = json.loads(lines[-1][4:])

    assert out["open"] == {"ran": True}
    assert out["press"] == {"pressed": "vJoy"}
    # vJoy 1's six stand-in axes, each named and showing its value.
    assert len(out["boxes"]) == 6, out["boxes"]
    assert out["name"] in out["boxes"], out["boxes"]
    assert out["boxes"][out["name"]] == "0.00"  # two decimals (04 S98)
    assert "type-error" not in out, out["type-error"]
    assert out["before"] == 0.0
    assert out["after"] == 0.5
    assert out["boxes-after"][out["name"]] == "0.50"
