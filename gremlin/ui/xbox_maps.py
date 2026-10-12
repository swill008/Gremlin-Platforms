# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations


def xbox_maps_for_item(item) -> list[tuple[int, str]]:
    """(pad, control value) of each Map to Xbox in the input's bindings
    (gremlin.usages; its own sends, not anything nested below it)."""
    from gremlin import usages

    return [
        (int(ref.target[1]), str(ref.target[2]))
        for ref in usages.item_usages(None, item)
        if ref.target[0] == "xbox"
        and ref.usage.role == "sends-output"
        and ref.usage.own
        and ref.usage.action_tag == "map-to-xbox"
    ]
