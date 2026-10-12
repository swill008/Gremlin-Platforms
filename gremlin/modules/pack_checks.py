# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The checks every shared zip passes before anything in it is read
(08 S110, D-08-PACK-LIMITS): the Device Pack's .zip, a device folder's
.gmap, a .gtemplate and the Device Library's saved setups."""

from __future__ import annotations

import zipfile
from xml.etree import ElementTree

# The most a pack may unpack to (all its files together); a bigger one is
# refused before anything in it is read.
MAX_UNPACKED = 64 * 1024 * 1024


def too_big(zf: zipfile.ZipFile) -> str:
    """Why the pack is too big to unpack ("" when it isn't)."""
    total = sum(max(0, info.file_size) for info in zf.infolist())
    if total <= MAX_UNPACKED:
        return ""
    mb = 1024 * 1024
    return (
        f"This file is too big to read: it unpacks to {total // mb} MB "
        f"and the most is {MAX_UNPACKED // mb} MB."
    )


def _is_block(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        ElementTree.fromstring(value)
    except ElementTree.ParseError:
        return False
    return True


def wires_problem(wires: object) -> str:
    """What is wrong with a pack's wires.json ("" when nothing is): every
    reader trusts its shape once this passes."""
    if not isinstance(wires, dict):
        return "Its wires.json is not a document."
    modes = wires.get("modes")
    if modes is not None and not isinstance(modes, list):
        return "Its wires.json has modes that are not a list."
    for mode in modes or []:
        if not isinstance(mode, dict):
            return "Its wires.json has a mode that is not a document."
        name = mode.get("name")
        if name is not None and not isinstance(name, str):
            return "Its wires.json has a mode whose name is not text."
        label = f'mode "{name or "Default"}"'
        lines = mode.get("lines")
        if lines is not None and not (
            isinstance(lines, list) and all(isinstance(x, str) for x in lines)
        ):
            return f"Its wires.json has lines in {label} that are not a list of text."
        inputs = mode.get("inputs")
        if inputs is not None and not (
            isinstance(inputs, list) and all(_is_block(x) for x in inputs)
        ):
            return f"Its wires.json has inputs in {label} that can't be read."
    actions = wires.get("actions")
    if actions is not None and not (
        isinstance(actions, list) and all(_is_block(x) for x in actions)
    ):
        return "Its wires.json has actions that can't be read."
    tree = wires.get("tree")
    if tree is not None and not (
        isinstance(tree, dict)
        and all(isinstance(v, str) or v is None for v in tree.values())
    ):
        return "Its wires.json has a mode tree that is not a document."
    osc = wires.get("osc")
    if osc is not None and not isinstance(osc, list):
        return "Its wires.json has OSC rows that are not a list."
    return ""
