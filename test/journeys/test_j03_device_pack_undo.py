# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Journey 3: Device Pack export, import onto another stick, Undo Import.

Two sticks: the pJoy Pro (checked buttons 1-3, button 1 named "Trigger";
button 1 sends vJoy button 1 in Default, button 2 sends vJoy button 2 in
Combat) and a Saitek X52 (its own module file; button 4 sends vJoy
button 9 in Default). The user opens Tools > Device Pack, exports the pJoy
Pro, opens the pack, puts it on the X52 (the red warning first), and
presses Replace: the X52 gets the pJoy's checked controls (added to its
own, 08 Q3) and its wires in Default and Combat (replacing the X52's),
the old X52 file is kept in the imported folder, the pJoy Pro is
untouched. Then Undo Import: the X52's module file is as it
was and its wires are back (button 4 only). Saved and opened again, the
profile has the wires from before the import.

Spec: 08 S49, S53, S59, S62, S64, S65 with Q3, S68, S73, S74, S80, S81.
GL-230 (the warning said "replaces" where checked controls are added) is
fixed in batch 3. GL-031 and GL-032 need a change after the import, so
this path doesn't reach them.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _harness import Journey, run_journey, step  # noqa: E402


def story(j: Journey) -> None:
    import json

    from PySide6 import QtCore

    from gremlin import util

    out = j.out
    pjoy = j.stick("pJoy Pro").device_guid.uuid
    x52 = j.stick("Saitek X52").device_guid.uuid
    j.profile.modes.add_mode("Combat")
    j.profile.modes.set_parent("Combat", "Default")
    j.map_button(pjoy, 1, "Default", 1)
    j.map_button(pjoy, 2, "Combat", 2)
    j.map_button(x52, 4, "Default", 9)
    _path, url = j.save_and_reopen("journey3")
    out["pjoy-before"] = j.wires(pjoy)
    out["x52-before"] = j.wires(x52)
    modules = util.modules_dir()
    x52_file = modules / "saitek_x52.json"
    x52_text_before = x52_file.read_text(encoding="utf-8")

    # Tools > Device Pack: export the pJoy Pro.
    j.ev('Helpers.createComponent("DialogDevicePack.qml")')
    pack = j.window("Device Pack")
    j.ev('_exportDevice.currentIndex = _exportDevice.find("pJoy Pro")', pack)
    j.ev("refreshExport()", pack)
    out["export-modes"] = [m["name"] for m in j.ev("exportModes", pack)]
    zip_path = util.export_dir() / "pjoy.zip"
    zip_url = QtCore.QUrl.fromLocalFile(str(zip_path)).toString()
    exported = json.loads(
        j.ev(f'_hw.exportPack("pJoy Pro", "{zip_url}", exportOptions())', pack)
    )
    out["exported"] = bool(exported.get("ok")) and zip_path.is_file()

    # Open the pack (as Open Device Pack does) and put it on the X52.
    j.ev(f'zipUrl = "{zip_url}"', pack)
    j.ev("_hw.keepPackImport()", pack)
    j.ev('mode = "import"; _pages.currentIndex = 1', pack)
    j.ev("loadPack(JSON.parse(_hw.peekPackZip(zipUrl)))", pack)
    j.ev('_saveAs.text = "Saitek X52"', pack)
    j.ev("askImport()", pack)
    out["warning"] = j.ev("_warnText.text", pack)
    replace = j.item(pack, "packReplace")
    out["replace-shown"] = bool(replace and replace.isVisible())
    j.click(replace)
    out["status-import"] = j.ev("status", pack)
    out["can-undo"] = j.ev("canUndo", pack)
    out["x52-file-after-import"] = json.loads(x52_file.read_text(encoding="utf-8"))[
        "claim"
    ]
    out["imported-backups"] = (
        sorted(p.name for p in (modules / "imported").glob("*") if p.is_file())
        if (modules / "imported").is_dir()
        else []
    )
    out["x52-after-import"] = j.wires(x52)
    out["pjoy-after-import"] = j.wires(pjoy)

    # Undo Import.
    j.ev("undoImport()", pack)
    out["status-undo"] = j.ev("status", pack)
    out["can-undo-after"] = j.ev("canUndo", pack)
    out["x52-file-restored"] = x52_file.read_text(encoding="utf-8") == x52_text_before
    out["x52-after-undo"] = j.wires(x52)
    out["pjoy-after-undo"] = j.wires(pjoy)
    out["modes-after-undo"] = sorted(j.profile.modes.mode_names())

    # Saved and opened again: the wires from before the import.
    assert j.backend.saveProfile(url)
    j.reopen(url)
    out["x52-after-reload"] = j.wires(x52)
    out["pjoy-after-reload"] = j.wires(pjoy)


def main() -> None:
    def before(j: Journey) -> None:
        x52 = j.add_stick("Saitek X52", 1)
        j.input_module(buttons=[1, 2, 3])
        j.input_module("Saitek X52", buttons=[4], guid=x52)
        j.vjoy_module()

    Journey(before).run(story)


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("j03"))


_PJOY = {"Combat": [[2, [2]]], "Default": [[1, [1]]]}
_X52 = {"Default": [[4, [9]]]}


def test_the_pack_is_exported_with_its_modes(run: dict) -> None:
    assert step(run, "pjoy-before") == _PJOY
    assert step(run, "x52-before") == _X52
    assert sorted(step(run, "export-modes")) == ["Combat", "Default"]
    assert step(run, "exported") is True


def test_import_onto_the_other_stick_replaces_its_file_and_wires(run: dict) -> None:
    warning = step(run, "warning")
    assert "Saitek X52" in warning.splitlines()[0]
    assert "The previous module file is kept in the imported folder." in warning
    assert step(run, "replace-shown") is True
    assert step(run, "can-undo") is True
    # The pack's checked controls are added to the X52's (08 Q3).
    assert sorted(step(run, "x52-file-after-import")["buttons"]) == [1, 2, 3, 4]
    assert step(run, "imported-backups"), "the old X52 file is kept"
    assert step(run, "x52-after-import") == _PJOY
    assert step(run, "pjoy-after-import") == _PJOY


def test_the_warning_says_checked_controls_are_added(run: dict) -> None:
    assert "adds the pack's checked controls" in step(run, "warning")


def test_undo_import_puts_the_file_and_the_wires_back(run: dict) -> None:
    assert step(run, "can-undo-after") is False
    assert step(run, "x52-file-restored") is True
    assert step(run, "x52-after-undo") == _X52
    assert step(run, "pjoy-after-undo") == _PJOY
    assert step(run, "modes-after-undo") == ["Combat", "Default"]
    assert step(run, "x52-after-reload") == _X52
    assert step(run, "pjoy-after-reload") == _PJOY


if __name__ == "__main__":
    main()
