# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Closing the OSC page's model (OscLayoutModel) at a test's end."""

from __future__ import annotations

from typing import Any


def close_osc_page(model: Any) -> None:  # noqa: ANN401
    """Closes the pane and deletes the model now. Letting Python drop it is
    not enough: a failed test's traceback keeps it alive, still connected
    to oscDeviceModified, and it rebuilt on a later test's stand-in profile
    (seed 809820, unit-2)."""
    import shiboken6

    if not shiboken6.isValid(model):
        return
    model.endPane()
    shiboken6.delete(model)
