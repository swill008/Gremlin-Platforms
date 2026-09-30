# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import uuid
from unittest import mock

import pytest

import dill
from gremlin.osc import OSC_DEVICE_UUID
from gremlin.ui import input_pairing


@pytest.mark.parametrize(
    "guid, label",
    [
        (dill.UUID_LogicalDevice, "Logical Device"),
        (dill.UUID_Keyboard, "Keyboard"),
        (OSC_DEVICE_UUID, "OSC"),
    ],
)
def test_builtin_devices_have_names(guid: uuid.UUID, label: str) -> None:
    # DILL only names hardware; these used to show as raw IDs.
    assert input_pairing.device_label(str(guid)) == label
    assert input_pairing.device_label(str(guid).upper()) == label
    assert input_pairing.device_label("{" + str(guid) + "}") == label


def test_other_devices_use_the_hardware_name() -> None:
    guid = str(uuid.uuid4())
    with mock.patch.object(input_pairing, "_device_name", return_value="Stick") as name:
        assert input_pairing.device_label(guid) == "Stick"
    name.assert_called_once_with(guid)
