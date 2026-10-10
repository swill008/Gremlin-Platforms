# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Configuration page's model (HardwareLayoutModel, 05 S121) on a stick
with no module file and no connected device: the claimed rows are given
here, so tests of the pane, Undo and Delete reach the page's real model.

Spec: none (test helper).
"""

from __future__ import annotations

import uuid
from typing import Any

from gremlin.common import input_to_ui_string
from gremlin.modules import store
from gremlin.modules.claim import type_of
from gremlin.types import InputType
from gremlin.ui.control_layout import parent_key


def key(kind: InputType, hid: int) -> str:
    """The parent row key ("parent:button:1")."""
    return parent_key(kind, hid)


def page_on(
    guid: uuid.UUID,
    inputs: list[tuple[str, int]] | tuple[tuple[str, int], ...] = (("button", 1),),
    device_name: str = "",
) -> Any:  # noqa: ANN401 - HardwareLayoutModel
    """The page's model showing these claimed inputs ("button", 1), ...; the
    device index is the input's place in the list."""
    from gremlin.ui.hardware_layout import HardwareLayoutModel

    model = HardwareLayoutModel()
    held = model._store
    fixed = {
        (kind, int(hid)): (index, input_to_ui_string(type_of(kind), int(hid)))
        for index, (kind, hid) in enumerate(inputs)
    }

    def load() -> None:
        # As the store's own load, with the claimed inputs given here.
        held._inputs = dict(fixed)
        layout = store.normalize_layout(store.layout_for(held.guid, held.device_name))
        held._groups = list(layout["groups"])
        held._order = list(layout["order"])
        held._group_of = dict(layout["group_of"])
        names = (store.pending_layout(held.guid) or {}).get("names", {})
        held._names = {k: v for k, v in names.items() if str(v or "").strip()}

    held.load = load
    held.guid = str(guid)
    held.device_name = device_name
    load()
    model._rebuild()
    return model


def close(model: Any) -> None:  # noqa: ANN401
    """Closes the pane and drops what the page held unsaved."""
    guid = model._store.guid
    model.endPane()
    if guid:
        store.discard_pending(guid)
    model.deleteLater()
