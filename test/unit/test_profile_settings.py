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
    assert p.settings.startup_mode == "Use Heuristic"
    assert p.settings.macro_default_delay is None  # Follows Options.
    assert p.settings.vjoy_as_input == {}
    assert p.settings.vjoy_initial_values == {}

    p2 = _roundtrip_profile(p)
    assert p2.settings.startup_mode == "Use Heuristic"
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
    # The old automatic 0.05 means "not set": it follows Options.
    assert p.settings.macro_default_delay is None

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
