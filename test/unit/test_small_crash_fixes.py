# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Small crash fixes from the 2026-10-10 audit (AUD-LINT-03/04/06/07, AUD-BMH-06)."""

from __future__ import annotations

import math
from unittest import mock
from xml.etree import ElementTree

import pytest

from gremlin import spline

# AUD-LINT-03: an unknown pause/resume operation falls back to Pause.


def test_pause_resume_lookup_unknown_falls_back_to_pause() -> None:
    from action_plugins.pause_resume import PauseResumeType

    assert PauseResumeType.lookup("Toggle") is PauseResumeType.Toggle
    assert PauseResumeType.lookup("Bogus") is PauseResumeType.Pause


def test_pause_resume_unknown_operation_loads_and_saves() -> None:
    from action_plugins.pause_resume import PauseResumeData, PauseResumeType
    from gremlin import util
    from gremlin.types import PropertyType

    node = util.create_action_node(
        PauseResumeData.tag,
        util.read_action_id(
            ElementTree.Element(
                "action", {"id": "11111111-1111-1111-1111-111111111111"}
            )
        ),
    )
    node.append(util.create_property_node("operation", "Bogus", PropertyType.String))

    data = PauseResumeData()
    # The plugin's own getLogger: a test earlier in the run may have swapped
    # the "system" logger's class, so Logger.warning alone isn't reliable.
    logger = mock.Mock()
    with mock.patch(
        "action_plugins.pause_resume.logging.getLogger", return_value=logger
    ):
        data._from_xml(node, None)  # type: ignore[arg-type]
    assert data.operation is PauseResumeType.Pause
    assert logger.warning.called
    saved = data._to_xml()
    assert "Pause" in ElementTree.tostring(saved, encoding="unicode")


# AUD-LINT-04: a NaN input gives a defined value (the curve at the centre).


@pytest.mark.parametrize(
    "curve",
    [
        spline.PiecewiseLinear([(-1.0, -1.0), (0.0, 0.3), (1.0, 1.0)]),
        spline.CubicSpline([(-1.0, -1.0), (0.0, 0.3), (1.0, 1.0)]),
        spline.CubicBezierSpline(),
    ],
    ids=["piecewise", "cubic", "bezier"],
)
def test_curve_nan_input_is_centre(curve: spline.AbstractCurve) -> None:
    value = curve(float("nan"))
    assert isinstance(value, float)
    assert not math.isnan(value)
    assert value == pytest.approx(curve(0.0))


# AUD-LINT-06: a non-button Logical Device macro step reports not pressed.


def test_macro_is_pressed_false_for_axis_step() -> None:
    from action_plugins.macro import LogicalDeviceActionModel
    from gremlin.types import InputType

    model = LogicalDeviceActionModel.__new__(LogicalDeviceActionModel)
    model._action = mock.Mock(input_type=InputType.JoystickAxis, value=0.5)
    assert model._get_is_pressed() is False


# AUD-LINT-07: the broken, unused ConditionModel.addAction slot is gone.


def test_condition_model_has_no_add_action() -> None:
    from action_plugins.condition import ConditionModel

    assert not hasattr(ConditionModel, "addAction")


# AUD-BMH-06: the Auto Mapper with no profile open returns a message.


def test_auto_mapper_without_profile_returns_message() -> None:
    from gremlin import shared_state
    from gremlin.ui.tools import Tools

    with mock.patch.object(shared_state, "current_profile", None):
        result = Tools().createMappings("", {}, {}, False, False)
    assert result == "No profile is open."
