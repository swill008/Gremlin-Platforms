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


def _run(tmp_path: pathlib.Path, bindings: dict | None = None) -> dict:
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


def test_remove_says_why_when_the_module_file_stays(tmp_path: pathlib.Path) -> None:
    # Another stick uses the file: Delete Device keeps it (ok), so Remove
    # must stop and say so, never stop silently (D-10-REMOVE-ERROR).
    other = "AAAA0001-0000-0000-0000-000000000000"
    out = _run(tmp_path, {other: "hid_remapper_achb"})
    assert out["fileAfter"], out
    assert out["after"] is not None, out
    assert out["bad"] and "module file is still here" in out["message"], out
