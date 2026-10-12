# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Export / Import Device entry points (D-FIXLIST-B2, 08 S111): Tools ›
Device Setup › Export / Import Device opens the one window on its Export
tab, and a Home card's Export Device… / Import Device… open the same window
(DialogDevicePack.qml) on the matching tab with the card's device. The old
box (DialogDeviceExport.qml, gremlin/ui/device_export.py) is gone.

The off-screen part runs the real program in its own process
(b2_card_smoke.py)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parents[1]


def test_the_old_export_box_is_gone() -> None:
    assert not (_ROOT / "qml" / "DialogDeviceExport.qml").exists()
    assert not (_ROOT / "gremlin" / "ui" / "device_export.py").exists()
    main = (_ROOT / "joystick_gremlin.py").read_text(encoding="utf-8")
    assert "device_export" not in main
    page = (_ROOT / "qml" / "StatusPage.qml").read_text(encoding="utf-8")
    assert "DialogDeviceExport" not in page


def _run(tmp_path: Path) -> dict[str, object]:
    import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
    import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

    proc = proc_tree.run(
        [sys.executable, str(_HERE / "b2_card_smoke.py")],
        cwd=str(_ROOT),
        text=True,
        encoding="utf-8",
        timeout=180,
        env={
            **os.environ,
            "QT_QPA_PLATFORM": "offscreen",
            "PYTHONIOENCODING": "utf-8",
            "USERPROFILE": str(tmp_path),
        },
    )
    lines = proc.stdout.splitlines()
    found = [line for line in lines if line.startswith("RESULT ")]
    assert found, smoke_report.explain(proc)
    return json.loads(found[-1][len("RESULT ") :])


def test_tools_menu_and_home_card_open_the_export_import_window(
    tmp_path: Path,
) -> None:
    r = _run(tmp_path)
    assert r["tools-text"] == "Export / Import Device", r
    assert r["tools-open"] is True, r
    assert r["tools-mode"] == "export", r
    assert r["page"] is True, r
    for tab in ("export", "import"):
        assert r[f"{tab}-open"] is True, r
        assert r[f"{tab}-mode"] == tab, r
        assert r[f"{tab}-old-box"] is False, r
    # Once DialogDevicePack.openFor exists (WIN), the card's device goes with it.
    if r.get("has-openFor"):
        assert str(r["export-guid"]).lower() == str(r["guid"]).lower(), r
