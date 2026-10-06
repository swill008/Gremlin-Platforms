# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import sys
import uuid

sys.path.append(".")

from gremlin import shared_state
from gremlin.profile import Profile, binding_fingerprint
from gremlin.types import InputType


def test_draft_does_not_change_the_parent_until_ok() -> None:
    profile = Profile()
    shared_state.current_profile = profile
    item = profile.get_input_item(
        uuid.uuid4(), InputType.JoystickButton, 1, "Default", True
    )
    assert item is not None
    item.add_item_binding()
    item.action_sequences[0].root_action.action_label = "keep"
    before = len(item.action_sequences)
    library = profile.library

    draft = library.draft(item, 0)
    draft.item.action_sequences[0].root_action.action_label = "draft"
    assert item.action_sequences[0].root_action.action_label == "keep"
    assert len(item.action_sequences) == before
    assert binding_fingerprint(draft.item.action_sequences[0]) != binding_fingerprint(
        item.action_sequences[0]
    )
    library.discard(draft)
    assert item.action_sequences[0].root_action.action_label == "keep"
    assert len(item.action_sequences) == before

    draft = library.draft(item, blank=True)
    draft.item.action_sequences[0].root_action.action_label = "new"
    index = library.commit(draft, item)

    assert index == 1
    assert item.action_sequences[0].root_action.action_label == "keep"
    assert item.action_sequences[1].root_action.action_label == "new"
    shared_state.current_profile = None
