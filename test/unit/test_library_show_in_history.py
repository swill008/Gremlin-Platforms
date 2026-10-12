# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""10 S56: a Device Library row's Show in History opens Tools > History
filtered to that device (08 S32-S33), as Module Setup's History does (by
the device's id, its name on the "Only ..." line), even when
History is already open on everything and for a device with no card:
its module file's changes and the Device Library's changes to it (Save,
Delete, Remove), not a twin stick's or another file's."""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SMOKE = _ROOT / "test" / "unit" / "library_show_in_history_smoke.py"


def test_show_in_history_opens_history_on_the_device(tmp_path: pathlib.Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    env = dict(
        os.environ,
        USERPROFILE=str(home),
        QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1",
        PYTHONIOENCODING="utf-8",
    )
    result = proc_tree.run(
        [sys.executable, str(_SMOKE)],
        cwd=_ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, smoke_report.explain(result)
    out = json.loads(lines[-1][len("RESULT ") :])
    assert out["result"].get("ok"), out
    assert out["opened"]
    # Filtered by the device's id (08 S43), not by a file name.
    of_device = out["filter"]["ofDevice"]
    assert of_device["deviceId"] and of_device["guid"], out
    assert "fileName" not in of_device
    assert out["titles"] == [
        "UR delete setup",
        "UR module save",
        "UR remove",
        "UR save setup",
    ]
    assert out["about"] == "Shown Name"
    assert out["gone"].get("ok") and out["goneAbout"] == "Gone Stick"
    assert out["errors"] == []
