# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""No code outside gremlin/modules/device_class.py keeps its own list of the
built-in devices (03 S90b, D-03-DEVICE-CLASSES): a set, tuple, list or dict
holding two or more of the built-in ids (ids.KEYBOARD, ids.OSC,
ids.LOGICAL_DEVICE, ids.XBOX, dill.UUID_Keyboard, dill.UUID_LogicalDevice,
or a name assigned from one of them) or of the built-in names ("keyboard",
"osc", "logical device", "xbox", "vjoy"). A single use that means the one
device (osc.py's OSC_DEVICE_UUID = ids.OSC) is fine."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GREMLIN = ROOT / "gremlin"

# Where the built-in ids and names belong.
OWNERS = {
    "gremlin/modules/device_class.py",
    "gremlin/modules/ids.py",
    "gremlin/modules/registry.py",
}

# (file, assigned name) of lists allowed by decision.
ALLOWED = {
    # A slug-prefix rule for the name-only lookup note ("keyboard_stick" and
    # "xbox_wireless_controller" count too), not a device class: kept as it
    # is by the lead's decision (2026-10-09, D-03-DEVICE-CLASSES work).
    ("gremlin/modules/store.py", "_NAME_ONLY_OK"),
    # Home's tab pin keys, saved in the settings as they are spelled
    # ("logical", not "logical_device"): settings values, not a device list.
    ("gremlin/ui/vjoy_status.py", "EXTRA_ALLOWED"),
    ("gremlin/ui/vjoy_status.py", "EXTRA_DEFAULT"),
}

_ID_ATTRS = {
    ("ids", "KEYBOARD"), ("ids", "OSC"), ("ids", "LOGICAL_DEVICE"), ("ids", "XBOX"),
    ("dill", "UUID_Keyboard"), ("dill", "UUID_LogicalDevice"),
}
_NAMES = {"keyboard", "osc", "logical device", "logical_device", "logical-device",
          "xbox", "vjoy"}
# Also allowed beside the names in a device list (a tab key).
_TOLERATED = {"logical"}
_COLLECTIONS = (ast.Set, ast.Tuple, ast.List, ast.Dict)


def _id_ref(node: ast.AST, aliases: set[str]) -> str:
    """The built-in id this node names, or ""."""
    if (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and (node.value.id, node.attr) in _ID_ATTRS
    ):
        return node.attr.casefold().replace("uuid_", "").replace("_", "")
    if isinstance(node, ast.Name) and node.id in aliases:
        return node.id
    return ""


def _aliases(tree: ast.AST) -> dict[str, str]:
    """Module-level names assigned from one built-in id (KEYBOARD_GUID =
    str(ids.KEYBOARD).upper()) -> that id."""
    found: dict[str, str] = {}
    for node in getattr(tree, "body", []):
        if not isinstance(node, ast.Assign):
            continue
        refs = {_id_ref(n, set()) for n in ast.walk(node.value)} - {""}
        if len(refs) == 1:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    found[target.id] = refs.pop() if len(refs) == 1 else ""
                    refs = {found[target.id]}
    return found


def _allowed_nodes(tree: ast.AST, rel: str) -> set[int]:
    allowed: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and (rel, target.id) in ALLOWED:
                    allowed.update(id(n) for n in ast.walk(node.value))
    return allowed


def _offences(path: Path) -> list[str]:
    rel = path.relative_to(ROOT).as_posix()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
    aliases = _aliases(tree)
    alias_names = set(aliases)
    allowed = _allowed_nodes(tree, rel)
    found: list[str] = []
    reported: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, _COLLECTIONS) or id(node) in allowed:
            continue
        if id(node) in reported:
            continue
        inner = list(ast.walk(node))
        ids_here = set()
        names_here = set()
        other_strings = False
        for sub in inner:
            ref = _id_ref(sub, alias_names)
            if ref:
                ids_here.add(aliases.get(ref, ref) or ref)
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                plain = " ".join(sub.value.split()).casefold()
                if plain in _NAMES:
                    names_here.add(plain.replace("_", " ").replace("-", " "))
                elif plain.isidentifier() and plain not in _TOLERATED:
                    other_strings = True
        # A list of names counts only when it lists devices alone: a lookup
        # of input or action types ("keyboard", "joystick", "vjoy", or
        # "mouse", "macro") is not a device list.
        names_listed = len(names_here) >= 2 and not other_strings
        if len(ids_here) >= 2 or names_listed:
            found.append(f"{rel}:{node.lineno}")
            reported.update(id(sub) for sub in inner)
    return found


def test_no_builtin_lists_outside_device_class() -> None:
    offences: list[str] = []
    for path in sorted(GREMLIN.rglob("*.py")):
        if path.relative_to(ROOT).as_posix() in OWNERS:
            continue
        offences += _offences(path)
    assert not offences, (
        "Built-in device lists outside gremlin/modules/device_class.py "
        "(ask device_class / can() instead, 03 S90b):\n" + "\n".join(offences)
    )


def test_guard_catches_a_list(tmp_path: Path) -> None:
    """The guard sees the forms it is meant to catch, and lets single uses
    and the allowed constant through."""
    sample = GREMLIN / "_guard_sample_tmp.py"
    sample.write_text(
        "from gremlin.modules import ids\nimport dill\n"
        "A = (ids.KEYBOARD, ids.OSC)\n"
        "B = {'keyboard', 'osc', 'logical device'}\n"
        "K = str(ids.KEYBOARD)\nC = [(K, 'x'), (dill.UUID_LogicalDevice, 'y')]\n"
        "OSC_DEVICE_UUID = ids.OSC\nD = ('keyboard', 'mouse')\n"
        "E = {'keyboard': 1, 'joystick': 2, 'vjoy': 3}\n"
        "F = ['keyboard', 'logical', 'osc']\n",
        encoding="utf-8",
    )
    try:
        found = _offences(sample)
    finally:
        sample.unlink()
    assert [f.rsplit(":", 1)[1] for f in found] == ["3", "4", "6", "10"]
