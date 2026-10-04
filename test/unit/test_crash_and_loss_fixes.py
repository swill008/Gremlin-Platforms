# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Crashes and lost work from the 3 Oct review (ACT5, ACT7-9, ACT13-15, DEV13).

- Split Axis split at 1.0: full deflection divided by zero (ACT5).
- A Chain with every sequence removed, an empty macro, and Cycle / Switch /
  Temporary with no mode crashed on each press; they now do nothing
  (ACT7, ACT8, ACT9).
- Calibration: a capture started from 0 instead of the stick's position,
  and a range saved without moving the axis divided by zero on every event;
  such a save is now refused with the reason (DEV13).
- Response Curve: Symmetric was not saved (ACT13); changing the curve type
  threw the points away, it now keeps them (ACT14).
- A profile of another version replaced the open one with an empty profile
  and went into Recent; it now raises, so the open one is put back (ACT15).
"""

from __future__ import annotations

import sys

sys.path.append(".")

import pathlib
import uuid
from types import SimpleNamespace
from xml.etree import ElementTree

import pytest

from gremlin import error, util
from gremlin.types import InputType

# ACT5 ---------------------------------------------------------------------


def test_a_range_of_no_width_does_not_divide_by_zero() -> None:
    assert util.linear_axis_value_interpolation(1.0, 1.0, 1.0) == -1.0
    assert util.linear_axis_value_interpolation(-1.0, -1.0, -1.0) == -1.0
    assert util.linear_axis_value_interpolation(0.5, 0.0, 1.0) == 0.0  # unchanged


@pytest.mark.parametrize("split", [1.0, -1.0])
def test_split_axis_at_the_end_handles_full_deflection(split: float) -> None:
    from action_plugins.split_axis import SplitAxisFunctor

    functor = object.__new__(SplitAxisFunctor)
    functor.data = SimpleNamespace(split_value=split)
    seen = []
    functor.functors = {
        "lower": [lambda e, v, p: seen.append(("lower", v.current))],
        "upper": [lambda e, v, p: seen.append(("upper", v.current))],
    }
    for value in (-1.0, 0.0, 1.0):
        functor(None, SimpleNamespace(current=value), [])
    assert len(seen) == 3 and all(-1.0 <= v <= 1.0 for _, v in seen)


# ACT7, ACT8, ACT9 ---------------------------------------------------------------


def test_a_chain_with_no_sequences_does_nothing() -> None:
    from action_plugins.chain import ChainFunctor

    functor = object.__new__(ChainFunctor)
    functor.data = SimpleNamespace(chain_sequences=[], timeout=0.0)
    functor.functors = {}
    functor.current_index = 0
    functor.last_execution = 0.0
    functor(None, SimpleNamespace(current=True), [])
    functor(None, SimpleNamespace(current=False), [])


def test_an_empty_macro_does_nothing() -> None:
    from gremlin.macro import Macro, MacroManager

    manager = object.__new__(MacroManager)
    manager.default_delay = 0.01
    macro = Macro()
    manager._preprocess_macro(macro)
    assert macro.sequence == []


@pytest.mark.parametrize("kind", ["Switch", "Cycle", "Temporary"])
def test_a_mode_change_with_no_mode_does_nothing(kind: str) -> None:
    from action_plugins.change_mode import ChangeModeFunctor, ChangeType

    functor = object.__new__(ChangeModeFunctor)
    functor.data = SimpleNamespace(
        change_type=ChangeType[kind], target_modes=[], _target_modes=[]
    )
    functor._mode_sequence = None
    functor._should_execute = lambda value: True
    functor(None, SimpleNamespace(current=True), [])
    functor._release_temporary_mode()


def test_cycling_through_no_modes_does_nothing() -> None:
    from gremlin import mode_manager

    # Returns before it touches the manager (a Qt object).
    mode_manager.ModeManager.klass.cycle(
        SimpleNamespace(), mode_manager.ModeSequence([])
    )


# DEV13 ----------------------------------------------------------------------


def test_calibrations_with_no_range_do_not_divide_by_zero() -> None:
    assert util.no_center_calibration(7, 3, 3) == -1.0  # was ZeroDivisionError
    assert util.with_center_calibration(5, 0, 0, 0, 0) == 0.0


def _calibration(low: int, high: int) -> SimpleNamespace:
    from gremlin.ui.device import AxisCalibration

    guid = uuid.uuid4()
    model = SimpleNamespace(
        _device=SimpleNamespace(
            axis_lookup={1: 1}, axis_map=[SimpleNamespace(axis_index=1)]
        ),
        _device_uuid=guid,
        _module_slug="stick",
        _state=[{
            "low": low, "centerLow": 0, "centerHigh": 0, "high": high,
            "withCenter": True, "unsavedChanges": True,
        }],
        _active_calibrations=[{"center": False, "extrema": False}],
        _calibration_fn=[lambda raw: 0.0],
        _update_calibration=lambda index: None,
        emit_update=lambda index: None,
    )
    model._refused = lambda index: AxisCalibration._refused(model, index)
    return model


def _axis_event(model: SimpleNamespace, raw: int) -> SimpleNamespace:
    return SimpleNamespace(
        device_guid=model._device_uuid, event_type=InputType.JoystickAxis,
        identifier=1, raw_value=raw, value=0.0,
    )


@pytest.mark.parametrize(("kind", "low", "high"), [
    ("center", "centerLow", "centerHigh"), ("extrema", "low", "high"),
])
def test_a_capture_starts_from_the_first_value_read(
    kind: str, low: str, high: str
) -> None:
    from gremlin.ui.device import AxisCalibration

    model = _calibration(-32768, 32767)
    model._active_calibrations[0][kind] = True
    model._active_calibrations[0]["cvalues" if kind == "center" else "evalues"] = None
    for raw in (300, 340, 280):  # an off-centre stick, barely moving
        AxisCalibration._event_callback(model, _axis_event(model, raw))
    # Not 0 to 340 (the capture used to start at 0).
    assert (model._state[0][low], model._state[0][high]) == (280, 340)


def test_a_calibration_with_no_range_is_refused_with_the_reason() -> None:
    from gremlin.ui.device import AxisCalibration

    flat = _calibration(120, 120)
    reason = AxisCalibration._refused(flat, 0)
    assert "lowest and highest values are the same" in reason
    assert AxisCalibration.saveRefusedReason(flat, 0) == reason
    assert AxisCalibration.saveAllRefusedReason(flat) == reason
    assert AxisCalibration.save(flat, 0) is False
    assert AxisCalibration.saveAll(flat) is False
    good = _calibration(-32768, 32767)
    assert AxisCalibration._refused(good, 0) == ""


# ACT13, ACT14 -----------------------------------------------------------------


def _points(curve: object) -> list[tuple[float, float]]:
    from action_plugins.response_curve import _curve_points

    return [(round(x, 3), round(y, 3)) for x, y in _curve_points(curve)]


_TYPES = ["PiecewiseLinear", "CubicSpline", "CubicBezierSpline"]


@pytest.mark.parametrize("source", _TYPES)
@pytest.mark.parametrize("target", _TYPES)
def test_changing_the_curve_type_keeps_the_points(source: str, target: str) -> None:
    from action_plugins.response_curve import converted_curve
    from gremlin import spline

    shape = [(-1.0, -1.0), (-0.3, -0.6), (0.4, 0.1), (1.0, 1.0)]
    if source == "CubicBezierSpline":
        flat = [shape[0], (-0.95, -1.0)]
        for x, y in shape[1:-1]:
            flat += [(x - 0.05, y), (x, y), (x + 0.05, y)]
        flat += [(0.95, 1.0), shape[-1]]
        curve = spline.CubicBezierSpline(flat)
    else:
        curve = getattr(spline, source)(shape)
    new = converted_curve(curve, getattr(spline, target))
    assert type(new) is getattr(spline, target)
    assert _points(new) == shape


def test_symmetric_is_saved_and_read_back() -> None:
    from action_plugins.response_curve import ResponseCurveData

    data = ResponseCurveData()
    data.curve.is_symmetric = True
    node = data._to_xml()
    again = ResponseCurveData()
    again._from_xml(node, None)
    assert again.curve.is_symmetric is True


def test_a_curve_saved_before_symmetric_was_saved_reads_as_not_symmetric() -> None:
    from action_plugins.response_curve import ResponseCurveData

    node = ResponseCurveData()._to_xml()
    for prop in list(node.findall("property")):
        if prop.findtext("name") == "symmetric":
            node.remove(prop)
    again = ResponseCurveData()
    again._from_xml(node, None)
    assert again.curve.is_symmetric is False


# ACT15 ----------------------------------------------------------------------


def test_a_profile_of_another_version_raises(tmp_path: pathlib.Path) -> None:
    from gremlin.profile import Profile

    path = tmp_path / "old.xml"
    root = ElementTree.Element("profile", version=str(Profile.current_version - 1))
    ElementTree.ElementTree(root).write(path)
    with pytest.raises(error.ProfileError, match="version"):
        Profile().from_xml(path)
