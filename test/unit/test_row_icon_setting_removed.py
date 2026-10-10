# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""AS1 (user, 2026-10-10): the Options setting "Action details" (row icon
mode, global/general/action-sequence-information) and the action-icon strip
it controlled are gone (05 section 3)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(".")

import gremlin.ui.device as device  # noqa: E402
import gremlin.ui.module_inputs as module_inputs  # noqa: E402
import gremlin.ui.option as option  # noqa: E402
import gremlin.ui.osc_device_model as osc_device_model  # noqa: E402
from gremlin.config import Configuration  # noqa: E402

_ROOT = Path(__file__).resolve().parents[2]
_KEY = ("global", "general", "action-sequence-information")
_GONE_ROLES = {b"actionSequenceDescriptor", b"actionSequenceDisplayMode"}


def test_the_setting_is_not_registered_or_laid_out() -> None:
    assert not Configuration().exists(*_KEY)
    laid_out = [
        key
        for _section, groups in option._LAYOUT
        for _group, keys in groups
        for key in keys
    ]
    assert _KEY not in laid_out
    assert _KEY[2] not in option._ENTRY_TITLES
    source = (_ROOT / "gremlin" / "ui" / "device.py").read_text(encoding="utf-8")
    assert "action-sequence-information" not in source


def test_no_list_model_has_the_icon_strip_roles() -> None:
    for model in (
        device.Device,
        module_inputs.ModuleClaimedInputModel,
        osc_device_model.OscDeviceManagementModel,
    ):
        names = {bytes(n.data()) for n in model.roles.values()}
        assert not names & _GONE_ROLES, model.__name__
    assert not hasattr(device, "_generate_action_sequence_descriptor")
    assert not hasattr(device, "KeyboardManagerModel")


def test_no_qml_reads_the_strip() -> None:
    assert not (_ROOT / "qml" / "InputButton.qml").exists()
    assert not (_ROOT / "qml" / "KeyboardInputList.qml").exists()
    for path in (_ROOT / "qml").rglob("*.qml"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert "actionSequenceDisplayMode" not in text, path.name
        assert "actionSequenceDescriptor" not in text, path.name
