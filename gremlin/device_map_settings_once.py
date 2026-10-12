# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""ONE-TIME (tracker OT-3): the Button Map's settings move to the Device
Mapping Editor's names. Removed before release with OT-1 and OT-2.

The settings section "button-map" becomes "device-mapping-editor" (its
groups and keys keep their names), and global/internal/button-map-<x>
becomes global/internal/device-map-<x> (options group, recent colours,
picture folder). At start, each old setting found in the settings file is
copied to its new name and the old one dropped, unless the new section (or
the new key) is stored already: then nothing of it is touched. Once moved,
the old names are gone from the file, so the move never runs again. No
History entry. Main thread, with the settings as loaded from the file:
before register_config_options (joystick_gremlin), which would add the new
names with their defaults.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

syslog = logging.getLogger("system")

# ONE-TIME (tracker OT-3): the old and new names.
OLD_SECTION = "button-map"
NEW_SECTION = "device-mapping-editor"
INTERNAL = ("global", "internal")
OLD_PREFIX = "button-map-"
NEW_PREFIX = "device-map-"
REFUSED = "refused: tests"

# ONE-TIME (tracker OT-3): the user's own Gremlin Platforms folder, read from
# the environment when this module loads (tests patch gremlin.util).
_REAL_DATA = [
    Path(base) / "Gremlin Platforms"
    for base in (
        os.environ.get("USERPROFILE", ""),
        os.environ.get("HOMEDRIVE", "") + os.environ.get("HOMEPATH", ""),
    )
    if base
]


def _inside(path: Path, parent: Path) -> bool:
    """ONE-TIME (tracker OT-3): path is parent or under it."""
    try:
        Path(path).resolve().relative_to(Path(parent).resolve())
    except (ValueError, OSError):
        return False
    return True


def refuses_real_settings(path: Path) -> bool:
    """ONE-TIME (tracker OT-3): True in a test run (GREMLIN_TESTS=1, or
    pytest loaded) when the settings file is in the user's real Gremlin
    Platforms folder: a test never changes the user's settings."""
    testing = os.environ.get("GREMLIN_TESTS") == "1" or "pytest" in sys.modules
    return testing and any(_inside(path, real) for real in _REAL_DATA)


def new_key(key: tuple[str, str, str]) -> tuple[str, str, str] | None:
    """ONE-TIME (tracker OT-3): the new name of an old setting, None when the
    setting is not one of the old names."""
    section, group, name = key
    if section == OLD_SECTION:
        return (NEW_SECTION, group, name)
    if (section, group) == INTERNAL and name.startswith(OLD_PREFIX):
        return (section, group, NEW_PREFIX + name[len(OLD_PREFIX) :])
    return None


def plan(saved: set[tuple[str, str, str]]) -> dict:
    """ONE-TIME (tracker OT-3): {old key: new key} to move, from the stored
    settings' keys. The whole old section is left alone when the new section
    is stored already; an internal key when its new name is."""
    new_section_saved = any(k[0] == NEW_SECTION for k in saved)
    moves = {}
    for key in sorted(saved):
        target = new_key(key)
        if target is None or target in saved:
            continue
        if key[0] == OLD_SECTION and new_section_saved:
            continue
        moves[key] = target
    return moves


def run(path: Path | None = None) -> str:
    """ONE-TIME (tracker OT-3): moves the old settings in the running
    Configuration (as loaded, before the new names are registered) and saves
    at once. Returns a summary ("" when nothing was
    to do); REFUSED in a test run on the real settings file."""
    from gremlin import config

    cfg = config.Configuration()
    path = Path(path or config._config_file_path)  # noqa: SLF001 - the one settings file
    if refuses_real_settings(path):
        syslog.warning(f"Button Map settings move {REFUSED} ({path})")
        return REFUSED
    moved = 0
    with cfg._lock:  # noqa: SLF001 - one-time move of stored entries
        data = cfg._data  # noqa: SLF001
        for old, new in plan(set(data)).items():
            data[new] = {k: v for k, v in data.pop(old).items() if k != "is_registered"}
            moved += 1
        if not moved:
            return ""
        # A rename, not a change: no History entry.
        cfg._history_view = cfg._settings_view()  # noqa: SLF001
    cfg.save_now(str(path))
    summary = f"Button Map settings move: {moved} setting(s) renamed"
    syslog.info(summary)
    return summary


def run_if_needed() -> str:
    """ONE-TIME (tracker OT-3): the start's entry point (joystick_gremlin):
    "" when done or nothing to do, else the reason (logged; the start goes
    on and the next start tries again)."""
    try:
        return REFUSED if run() == REFUSED else ""
    except Exception as exc:  # noqa: BLE001 - logged, retried next start
        syslog.exception("Button Map settings move failed")
        return str(exc) or type(exc).__name__
