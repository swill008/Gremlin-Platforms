# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Journey 9: Delete Device with "Save a copy", then bring it back.

The pJoy Pro has a module file (buttons 1-3, button 1 named "Trigger")
and wires in two modes (button 1 sends vJoy button 1 in Default, button 2
sends vJoy button 2 in Combat); a Saitek X52 has a wire of its own. On
Home the user picks Delete Device on the pJoy's card: the explanation
(with "Save a copy in deleted devices" ticked), the red confirm, then the
result. A pack is written to the deleted devices folder; the pJoy's module
file and its wires go; the X52 keeps its wire; the pJoy's card stays,
without a module.

Then Tools > Device Pack > Import of that pack onto the pJoy Pro, Replace:
the module file (checked controls, the name "Trigger") and the wires in
both modes are back; saved and opened again, the profile has them.

Spec: 03 S90, S91, S92, S96 and Q4 (Delete Device leaves the profile
unsaved, decision); 08 S86, S87, S89, S68, S74. GL-138 (Delete
Device wrote the whole profile to disk at once) fixed in batch 2. GL-024
(no test for the "Save a copy" pack and importing it back) is what this
journey covers.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _harness import Journey, run_journey, step  # noqa: E402


def _status_page(j: Journey) -> object:
    """Home (the Status page) as the main window shows it."""

    def find() -> object:
        for item in j.walk(j.win.contentItem()):
            meta = item.metaObject()
            if meta.indexOfMethod("askDelete(QVariant)") >= 0 and item.isVisible():
                return item
        return None

    return j.wait_until(find, "Home")


def story(j: Journey) -> None:
    import json

    from PySide6 import QtCore

    from gremlin import util

    out = j.out
    pjoy = j.stick("pJoy Pro")
    x52 = j.stick("Saitek X52").device_guid.uuid
    uid = pjoy.device_guid.uuid
    modules = util.modules_dir()
    module_path = modules / "pjoy_pro.json"
    j.profile.modes.add_mode("Combat")
    j.profile.modes.set_parent("Combat", "Default")
    j.map_button(uid, 1, "Default", 1)
    j.map_button(uid, 2, "Combat", 2)
    j.map_button(x52, 4, "Default", 9)
    path, url = j.save_and_reopen("journey9")
    out["pjoy-before"] = j.wires(uid)

    def file_has_wires() -> bool:
        """The profile file on disk has an input of the pJoy."""
        import xml.etree.ElementTree as ElementTree

        inputs = ElementTree.parse(path).getroot().find("inputs")
        return any(
            (node.findtext("device-id") or "").strip().lower() == str(uid).lower()
            for node in (inputs if inputs is not None else [])
        )

    out["file-had-wires"] = file_has_wires()

    # Home: Delete Device on the pJoy's card.
    home = _status_page(j)
    j.ev('askDelete(model.cardMap("pjoy_pro"))', home)
    out["explain"] = j.ev("explainBody()", home)
    out["save-copy-ticked"] = j.ev("_deleteSaveCopy", home)
    out["confirm"] = j.ev("confirmBody()", home)
    j.ev("runDelete()", home)
    out["done-title"] = j.ev("_doneTitle", home)
    out["done"] = j.ev("_doneMessage", home)
    packs = sorted(util.deleted_devices_dir().rglob("*.zip"))
    out["packs"] = [p.relative_to(util.deleted_devices_dir()).as_posix() for p in packs]
    out["module-gone"] = not module_path.exists()
    out["pjoy-after-delete"] = j.wires(uid)
    out["x52-after-delete"] = j.wires(x52)
    out["card-stays"] = j.ev('_moduleModel.cardMap("pjoy_pro").name')
    out["unsaved-after-delete"] = j.profile.has_unsaved_changes()
    out["file-still-has-wires"] = file_has_wires()

    # Device Pack > Import of that pack onto the pJoy Pro, Replace.
    zip_url = QtCore.QUrl.fromLocalFile(str(packs[-1])).toString() if packs else ""
    j.ev('Helpers.createComponent("DialogDevicePack.qml")')
    pack = j.window("Device Pack")
    j.ev(f'zipUrl = "{zip_url}"', pack)
    j.ev("_hw.keepPackImport()", pack)
    j.ev('mode = "import"; _pages.currentIndex = 1', pack)
    j.ev("loadPack(JSON.parse(_hw.peekPackZip(zipUrl)))", pack)
    out["suggested"] = j.ev("packInfo.suggestedName || packInfo.exportedName", pack)
    j.ev('_saveAs.text = "pJoy Pro"', pack)
    j.ev("askImport()", pack)
    j.click(j.item(pack, "packReplace"))
    out["import-status"] = j.ev("status", pack)
    doc = (
        json.loads(module_path.read_text(encoding="utf-8"))
        if module_path.is_file()
        else {}
    )
    claim = doc.get("claim") or {}
    out["module-back"] = [sorted(claim.get("buttons", [])), claim.get("friendly", {})]
    out["pjoy-after-import"] = j.wires(uid)
    out["x52-after-import"] = j.wires(x52)

    assert j.backend.saveProfile(url)
    j.ev("close()", pack)
    j.reopen(url)
    out["pjoy-after-reload"] = j.wires(uid)
    out["x52-after-reload"] = j.wires(x52)


def main() -> None:
    def before(j: Journey) -> None:
        x52 = j.add_stick("Saitek X52", 1)
        path = j.input_module(buttons=[1, 2, 3])
        import json

        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["claim"]["friendly"] = {"button:1": "Trigger"}
        path.write_text(json.dumps(doc), encoding="utf-8")
        j.input_module("Saitek X52", buttons=[4], guid=x52)
        j.vjoy_module()

    Journey(before).run(story)


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("j09"))


_PJOY = {"Combat": [[2, [2]]], "Default": [[1, [1]]]}
_X52 = {"Default": [[4, [9]]]}


def test_delete_device_explains_and_saves_a_copy_first(run: dict) -> None:
    assert step(run, "pjoy-before") == _PJOY
    assert step(run, "file-had-wires") is True
    assert step(run, "save-copy-ticked") is True
    assert "module file" in step(run, "explain")
    assert step(run, "confirm").startswith("Really delete pJoy Pro?")
    assert "A pack will be written to deleted devices first." in step(run, "confirm")
    assert step(run, "done-title") == "Device deleted"
    packs = step(run, "packs")
    assert len(packs) == 1 and packs[0].startswith("pJoy Pro/")


def test_the_device_file_and_wires_go_and_others_stay(run: dict) -> None:
    assert step(run, "module-gone") is True
    assert step(run, "pjoy-after-delete") == {}
    assert step(run, "x52-after-delete") == _X52
    assert step(run, "card-stays") == "pJoy Pro"


def test_delete_device_leaves_the_profile_unsaved(run: dict) -> None:
    assert step(run, "unsaved-after-delete") is True
    assert step(run, "file-still-has-wires") is True


def test_device_pack_import_brings_it_back(run: dict) -> None:
    assert step(run, "suggested") == "pJoy Pro"
    assert step(run, "module-back") == [[1, 2, 3], {"button:1": "Trigger"}]
    assert step(run, "pjoy-after-import") == _PJOY
    assert step(run, "x52-after-import") == _X52
    assert step(run, "pjoy-after-reload") == _PJOY
    assert step(run, "x52-after-reload") == _X52


if __name__ == "__main__":
    main()
