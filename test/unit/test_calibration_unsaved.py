# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest import mock

from gremlin.ui import device

_DEFAULTS = (-32768, 0, 0, 32767, True)


def _model(low: int, center_low: int, center_high: int, high: int) -> SimpleNamespace:
    return SimpleNamespace(
        _device=SimpleNamespace(axis_map=[SimpleNamespace(axis_index=1)]),
        _device_uuid=uuid.uuid4(),
        _module_slug="stick",
        _state=[
            {
                "low": low,
                "centerLow": center_low,
                "centerHigh": center_high,
                "high": high,
                "withCenter": True,
            }
        ],
    )


def test_back_at_the_saved_values_is_not_unsaved() -> None:
    # Reset to defaults when the defaults are what is saved: nothing to save.
    model = _model(-32768, 0, 0, 32767)
    with mock.patch.object(device, "values_for_module", return_value=_DEFAULTS):
        assert device.AxisCalibration._matches_saved(model, 0)


def test_a_changed_limit_is_unsaved() -> None:
    model = _model(-32768, 0, 0, 32766)
    with mock.patch.object(device, "values_for_module", return_value=_DEFAULTS):
        assert not device.AxisCalibration._matches_saved(model, 0)
