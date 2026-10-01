# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import uuid
from types import SimpleNamespace

import dill
from gremlin.modules import ids
from gremlin.ui import module_model

_EVO = "87fdb100-a8f5-11f1-8003-444553540000"


def test_every_form_of_a_guid_has_the_same_key() -> None:
    forms = [
        _EVO,
        _EVO.upper(),
        "{" + _EVO + "}",
        " {" + _EVO.upper() + "} ",
        uuid.UUID(_EVO),
        SimpleNamespace(uuid=uuid.UUID(_EVO)),  # DILL GUID objects carry .uuid
    ]
    keys = {ids.guid_key(f) for f in forms}
    assert keys == {_EVO.replace("-", "")}


def test_empty_values_give_an_empty_key() -> None:
    assert ids.guid_key(None) == ""
    assert ids.guid_key("") == ""


def test_stored_key_is_the_text_already_saved() -> None:
    # Binding store keys: upper case, no braces, no dashes. Must not change.
    assert ids.stored_guid_key("{" + _EVO + "}") == _EVO.replace("-", "").upper()


def test_built_in_ids_match_the_old_values() -> None:
    assert ids.LOGICAL_DEVICE == dill.UUID_LogicalDevice
    assert ids.KEYBOARD == dill.UUID_Keyboard
    assert str(ids.OSC) == "a7c3e91b-4d2f-4e18-9b06-2f8c1d5a6e70"
    assert str(ids.XBOX) == "c8e4b6a1-3d92-4f17-9a50-7b2c4e8f1d60"
    # Module rows keep the exact upper-case text written to module files.
    assert module_model.KEYBOARD_GUID == "6F1D2B61-D5A0-11CF-BFC7-444553540000"
    assert module_model.OSC_GUID == "A7C3E91B-4D2F-4E18-9B06-2F8C1D5A6E70"
    assert module_model.XBOX_GUID == "C8E4B6A1-3D92-4F17-9A50-7B2C4E8F1D60"
    assert module_model.LOGICAL_GUID == "F0AF472F-8E17-493B-A1EB-7333EE8543F2"
