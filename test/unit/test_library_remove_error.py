# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""10 S15, S47 (D-10-REMOVE-ERROR): Remove from Library through the real
window on a stick set up here but not plugged in (the user's HID Remapper
ACHB: an input module file, empty claim, no nodes, and a "stick deleted"
autosave). Its module file and its row go; when Delete Device keeps the
file (another stick uses it), the window says so and removes nothing."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SMOKE = _ROOT / "test" / "unit" / "library_remove_error_smoke.py"
_NAME = "HID Remapper ACHB"
_GUID = "10C58030-BE86-11F1-8001-444553540000"
_MODULE = {
    "kind": "control.hardware",
    "device": _NAME,
    "direction": "source",
    "boundName": _NAME,
    "boundGuidLocal": _GUID,
    "claim": {"buttons": [], "axes": [], "hats": [], "keys": [], "friendly": {}},
    "space": "world",
    "pageW": 32000,
    "pageH": 18000,
    "photoWell": 0.75,
    "nodes": [],
}


def _run(
    tmp_path: pathlib.Path,
    bindings: dict | None = None,
    history: bool = False,
    clear: bool = False,
) -> dict:
    home = tmp_path / "home"
    modules = home / "Gremlin Platforms" / "modules"
    modules.mkdir(parents=True)
    module = modules / "hid_remapper_achb.json"
    module.write_text(json.dumps(_MODULE, indent=2), encoding="utf-8")
    env = dict(
        os.environ,
        USERPROFILE=str(home),
        QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1",
        PYTHONIOENCODING="utf-8",
        GREMLIN_SMOKE_HISTORY="1" if history else "0",
        GREMLIN_SMOKE_CLEAR="1" if clear else "0",
    )
    args = [sys.executable, str(_SMOKE), _NAME, str(module)]
    if bindings is not None:
        args.append(json.dumps(bindings))
    result = subprocess.run(
        args,
        cwd=_ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, f"No RESULT (exit {result.returncode}).\n{result.stderr[-3000:]}"
    return json.loads(lines[-1][len("RESULT ") :])


def test_remove_deletes_the_module_file(tmp_path: pathlib.Path) -> None:
    out = _run(tmp_path)
    assert out["before"] and out["before"]["state"] == "not_connected"
    assert out["plan"]["module_file"]
    assert out["target"]["guid"] == _GUID
    assert not out["fileAfter"], out
    assert out["after"] is None, out
    assert not out["bad"], out["message"]


def test_remove_drops_a_stale_file_choice_with_the_file(tmp_path: pathlib.Path) -> None:
    # A choice left by an id that is neither plugged in nor in the Library
    # (an old id of the same stick) is no other device (03 S94): the file
    # goes and so does that choice (10 S52, D-10-REMOVE-ALL).
    other = "AAAA0001-0000-0000-0000-000000000000"
    out = _run(tmp_path, {other: "hid_remapper_achb"})
    assert not out["fileAfter"], out
    assert out["after"] is None, out
    assert not out["bad"], out["message"]
    assert "hid_remapper_achb" not in out["bindingsAfter"].values(), out


def test_remove_is_one_history_entry_and_restore_puts_it_all_back(
    tmp_path: pathlib.Path,
) -> None:
    # 10 S51-S52 (D-10-IN-HISTORY, D-10-REMOVE-ALL), 08 S12a: Remove from
    # Library on a stick with a module file, a saved setup, a friendly name
    # and a stale file choice is one action, so one entry (not Delete
    # Device's autosave, the module file's delete, the settings and the
    # Library's part); its Restore puts every piece back.
    other = "AAAA0001-0000-0000-0000-000000000000"
    out = _run(tmp_path, {other: "hid_remapper_achb"}, history=True)
    assert out["before"] and out["before"]["count"] >= 1, out
    assert out["after"] is None and not out["fileAfter"], out
    shown = out["plan"]["shown"] or _NAME
    assert out["titles"] == [f"Removed {shown} from the Device Library"], out
    assert out["restore"]["ok"], out
    assert out["fileRestored"], out
    assert out["rowRestored"] is not None, out
    assert out["rowRestored"]["count"] == out["before"]["count"], out
    assert out["bindingsRestored"].get(other) == "hid_remapper_achb", out
    assert out["aliasAfter"] == "" and out["aliasRestored"] == "Left Box", out


def test_clear_setup_is_one_history_entry_and_restore_puts_the_file_back(
    tmp_path: pathlib.Path,
) -> None:
    # 10 S52 (D-10-ONE-ENTRY-TITLES): Clear Setup's autosave and module
    # file delete are one entry, "Cleared the setup of X"; Restore puts the
    # module file back. The device stays in the Library.
    out = _run(tmp_path, history=True, clear=True)
    assert out["fileBefore"] and not out["fileAfter"], out
    shown = out["plan"]["shown"] or _NAME
    assert out["titles"] == [f"Cleared the setup of {shown}"], out
    assert out["restore"]["ok"], out
    assert out["fileRestored"], out
