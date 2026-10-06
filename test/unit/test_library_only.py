# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Guard for map 2 ("Who owns an action object", claude/system-maps.md):
only the profile's Library adds or removes actions, copies them for a pane,
and writes a profile's input lists. Code outside gremlin/profile.py goes
through create / draft / commit / discard / release / snapshot / restore /
change instead.

_WAITING lists the places not moved yet (file -> hits). It may only
shrink: a file that no longer has hits must leave the list.
"""

from __future__ import annotations

import pathlib
import re

_ROOT = pathlib.Path(__file__).parents[2]

_FORBIDDEN = re.compile(
    r"library\.(add_action|delete_action|remove_unused|clone_action|from_xml)\("
    r"|drop_unused_actions\("
    r"|_copied_from"
    r"|\.inputs\[[^\]]+\]\s*=(?!=)"
)

# TODO(batch1/batch2): callers still to move onto the Library.
_WAITING: dict[str, int] = {
    "gremlin/swap_devices.py": 2,  # inputs[...] = -> a Profile method
    "gremlin/ui/device_pack.py": 1,  # inputs[...] =, GL-099 / GL-109 (batch 2)
}


def _sources() -> list[pathlib.Path]:
    files = [_ROOT / "joystick_gremlin.py"]
    for folder in ("gremlin", "action_plugins"):
        files.extend((_ROOT / folder).rglob("*.py"))
    return [f for f in files if f.relative_to(_ROOT).as_posix() != "gremlin/profile.py"]


def _hits() -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for path in _sources():
        rel = path.relative_to(_ROOT).as_posix()
        for number, line in enumerate(
            path.read_text(encoding="utf-8-sig").splitlines(), 1
        ):
            if _FORBIDDEN.search(line):
                found.setdefault(rel, []).append(f"{rel}:{number}: {line.strip()}")
    return found


def test_only_the_library_owns_action_objects() -> None:
    problems = []
    for rel, lines in sorted(_hits().items()):
        if len(lines) > _WAITING.get(rel, 0):
            problems.extend(lines)
    assert not problems, (
        "Use the profile's Library (create, draft, commit, discard, release, "
        "snapshot, restore, change) instead:\n" + "\n".join(problems)
    )


def test_the_waiting_list_only_shrinks() -> None:
    hits = _hits()
    stale = [
        f"{rel}: listed {count}, has {len(hits.get(rel, []))}"
        for rel, count in _WAITING.items()
        if len(hits.get(rel, [])) < count
    ]
    assert not stale, "Lower or remove these _WAITING entries:\n" + "\n".join(stale)
