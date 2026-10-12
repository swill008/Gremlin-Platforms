# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Guard: module files have one owner, gremlin/modules/store.py.

System-maps map 1 (module file ownership) section 5, gap list GL-067: outside
the store and the registry (the read-only index that holds the lookup rule),
nothing in gremlin/ builds a module file's path from a name, builds a
path inside a device folder itself (module.json, device.json,
recovery.json, pictures/, imported/; D-03-DEVICE-FOLDERS), calls the
History hooks of module files or writes with the bare atomic writer. A
caller that does fails here; it asks the store instead (device_dir,
module_file, pictures_dir, recovery_path, imported_dir, read, update,
replace, put_picture, delete, move_aside, card_key...).
"""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]

# The owners: the store, the registry (the lookup rule and the index), and
# the History hooks themselves (only the store calls them).
_OWNERS = {
    "gremlin/modules/store.py",
    "gremlin/modules/registry.py",
    "gremlin/history_modules.py",
    # ONE-TIME (tracker OT-1): the move from the old layout builds the new
    # folders itself.
    "gremlin/modules/folders_move.py",
}

_RULES = {
    "builds a module file name from a device name": re.compile(
        r"(?<![\w.])plain_slug\(|registry\.plain_slug\(|(?<![\w.])_slug\("
    ),
    "builds a path in the modules folder from a name": re.compile(
        r"(modules_dir|_maps_dir|store\.folder|_folder)\(\)\s*/\s*f[\"']"
    ),
    "looks a device's module file up itself": re.compile(r"resolve_module_slug\("),
    "builds a path inside a device folder itself": re.compile(
        r"/\s*[\"'](module|device|recovery)\.json[\"']|/\s*[\"'](pictures|imported)[\"']"
    ),
    "calls a module file History hook": re.compile(
        r"history_modules\.(note_write|note_delete|delete_before|before_change)\("
        r"|(?<![\w.])deleting\(|history_modules\.deleting\("
    ),
    "writes with module_file directly": re.compile(
        r"module_file\.(write_text|write_json|write_bytes|start_fresh)\("
    ),
}

# (file, rule) pairs that are not module files: the atomic writer is shared
# with profiles, settings and History's own files.
_ALLOWED = {
    ("gremlin/config.py", "writes with module_file directly"),
    ("gremlin/history.py", "writes with module_file directly"),
    ("gremlin/profile.py", "writes with module_file directly"),
    # The module file writer forwards module files to the store.
    ("gremlin/modules/module_file.py", "writes with module_file directly"),
    # History Restore's copy of a profile next to the profile.
    ("gremlin/ui/history_model.py", "writes with module_file directly"),
    # The Device Library's own list and saved-setup packs (10), not module
    # files: module files it puts back go through the store (store.replace).
    ("gremlin/device_library.py", "writes with module_file directly"),
    # ONE-TIME (tracker OT-4): the Library part id move rewrites the
    # Library's own list (library.json), not a module file.
    ("gremlin/library_part_id_once.py", "writes with module_file directly"),
    # Profile recovery copies (04 S94) live in the data folder's recovery
    # folder, not the modules folder; they are not module files.
    ("gremlin/profile_recovery.py", "builds a path in the modules folder from a name"),
    # Device classes (03 S90b) compare a file's slug with the built-in slugs;
    # they build no path.
    ("gremlin/modules/device_class.py", "builds a module file name from a device name"),
    # Saved profiles that aren't open, changed by Copy / Swap (10 S33).
    ("gremlin/library_profiles.py", "writes with module_file directly"),
    # Device Mapping Editor templates, their exports and the photo cache (07): not
    # module files, but written safely with the shared atomic writer.
    ("gremlin/ui/hardware_profile.py", "writes with module_file directly"),
    # .gmap / .gtemplate files the user exports, and imported templates
    # (07 S110, 08 S111): not module files, written with the safe writer.
    ("gremlin/modules/device_zip.py", "writes with module_file directly"),
}


def _sources() -> list[tuple[str, str]]:
    found = []
    for path in sorted((_ROOT / "gremlin").rglob("*.py")):
        rel = path.relative_to(_ROOT).as_posix()
        if rel in _OWNERS:
            continue
        found.append((rel, path.read_text(encoding="utf-8")))
    return found


def _problems() -> list[str]:
    problems = []
    for rel, text in _sources():
        for number, line in enumerate(text.splitlines(), 1):
            code = line.split("#", 1)[0]
            for what, rule in _RULES.items():
                if rule.search(code) and (rel, what) not in _ALLOWED:
                    problems.append(f"{rel}:{number} {what}: {line.strip()}")
    return problems


def test_only_the_store_builds_module_paths_and_calls_history() -> None:
    assert _problems() == []


def test_the_rules_catch_what_they_are_for() -> None:
    # The guard itself: each rule matches the code it is meant to stop.
    samples = {
        "builds a module file name from a device name": "x = plain_slug(name)",
        "builds a path in the modules folder from a name": (
            'p = _maps_dir() / f"{slug}.json"'
        ),
        "looks a device's module file up itself": "registry.resolve_module_slug(n, g)",
        "builds a path inside a device folder itself": 'p = folder / "module.json"',
        "calls a module file History hook": "history_modules.note_write(p, t, o)",
        "writes with module_file directly": "module_file.write_json(path, doc)",
    }
    for what, code in samples.items():
        assert _RULES[what].search(code), what
    names = _RULES["builds a module file name from a device name"]
    assert names.search("registry.plain_slug(value)")
    assert names.search("slug = _slug(name)")
    # A method whose name ends in _slug, or the store's own doors, are fine.
    assert not names.search("self._module_slug(name)")
    assert not names.search("store.own_slug(name)")
    hooks = _RULES["calls a module file History hook"]
    assert hooks.search("with history_modules.deleting(path):")
    assert not hooks.search("store.delete_path(path)")
    paths = _RULES["builds a path in the modules folder from a name"]
    assert paths.search("util.modules_dir() / f'{slug}.json'")
    assert not paths.search('store.folder() / "templates"')
    inside = _RULES["builds a path inside a device folder itself"]
    for code in ('d / "pictures" / name', "d / 'device.json'", 'd / "imported"'):
        assert inside.search(code), code
    assert not inside.search('zf.writestr("module.json", data)')
    assert not inside.search('GMAP_MODULE = "module.json"')
