# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Journey 20: device map pictures in the device's folder.

The pJoy Pro's map names a picture whose file is gone. Outside Edit its
area is empty; in Edit a grey "Picture missing: gone.png" box shows, and
its right-click menu offers Choose Picture…, which points it at a new file
(one Undo step). Then a picture is pasted and the edit cancelled: nothing
is left in the device's folder or the edit's temporary folder. Saved, the
chosen picture is in the device's folder and the map names it.

Spec: 07 S106, S107, S108, S62, S26 (D-03-DEVICE-FOLDERS).
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _harness import Journey, run_journey, step  # noqa: E402

_GONE = {"id": "pic1", "kind": "draw", "shape": "image", "src": "pictures/gone.png",
         "fx": 0.3, "fy": 0.3, "fw": 0.2, "fh": 0.2, "rot": 0, "opacity": 1}


def _open_map(j: Journey) -> object:
    j.ev('openDeviceMappingEditorForCard(_moduleModel.cardMap("pjoy_pro"))')
    window = j.window("Device Mapping Editor")
    j.wait_until(lambda: j.ev("loadedDevice", window) == "pJoy Pro", "the pJoy's map")
    return window


def _placeholder(j: Journey, window: object) -> dict:
    """The missing picture's placeholder: shown or not, and its text."""
    shown = False
    text = ""
    for item in j.walk(window.contentItem()):
        if item.objectName() != "pictureMissing":
            continue
        if not j.ev("missing", item):
            continue
        shown = shown or bool(item.isVisible())
        text = str(j.ev("fileName", item))
    return {"shown": shown, "file": text}


def _pictures(j: Journey, window: object) -> list[str]:
    """Picture files in the device's folder and in its edit's folder."""
    from gremlin.modules import store

    del window
    found = []
    for root in (store.pictures_dir("pJoy Pro"), store.staged_dir("pJoy Pro")):
        if root.is_dir():
            found += sorted(p.name for p in root.rglob("*.png"))
    return found


def story(j: Journey) -> None:
    from PySide6 import QtCore, QtGui

    from gremlin import util

    out = j.out
    window = _open_map(j)
    out["view"] = _placeholder(j, window)

    j.ev("enterEdit()", window)
    j.wait_until(
        lambda: j.ev("editing && _ed() !== null && _ed().seeded === true", window),
        "the editor in Edit",
    )
    j.settle()
    out["edit"] = _placeholder(j, window)
    j.ev('_ed().setSelection(["pic1"])', window)
    # A right-click on the picture: the menu is about it (RigPointerArea
    # sets its target).
    for item in j.walk(window.contentItem()):
        meta = item.metaObject()
        if meta.indexOfProperty("menuTarget") >= 0 and item.property("menuTarget"):
            j.ev("menuTarget.nodeId = 'pic1'; menuTarget.kind = ''; true", item)
            break
    out["menu"] = j.ev(
        "(function() { var m = _ed().menuModel(); var t = [];"
        " (m.sections || []).forEach(function(s) { (s.items || []).forEach("
        " function(i) { t.push(i.text) }) }); return t })()",
        window,
    )

    # Choose Picture…: the file picked in its dialog, OK.
    image = QtGui.QImage(16, 16, QtGui.QImage.Format.Format_RGB32)
    image.fill(QtGui.QColor("#336699"))
    path = pathlib.Path(util.userprofile_path()) / "found.png"
    image.save(str(path))
    url = QtCore.QUrl.fromLocalFile(str(path)).toString()
    j.ev(
        "(function() { _choosePictureDialog.nodeId = 'pic1';"
        " var d = _choosePictureDialog.prepare();"
        f" d.selectedFile = '{url}'; d.accepted(); return true }})()",
        window,
    )
    j.settle()
    out["chosen-src"] = j.ev("_ed().nodeAt('pic1').src", window)
    out["after-choose"] = _placeholder(j, window)
    out["waiting"] = _pictures(j, window)

    out["save"] = j.ev("saveEdit(false)", window)
    out["saved-src"] = j.ev(
        "JSON.parse(_hw.load(targetName)).nodes.filter("
        "function(n) { return n.id === 'pic1' })[0].src",
        window,
    )
    out["after-save"] = _pictures(j, window)

    # A pasted picture, then Cancel: nothing is left behind (S107).
    QtGui.QGuiApplication.clipboard().setImage(image.copy(0, 0, 8, 8))
    j.settle()
    j.ev("pastePicture()", window)
    j.settle()
    out["pasted-waiting"] = _pictures(j, window)
    j.ev("discardEdit()", window)
    j.settle()
    out["after-cancel"] = _pictures(j, window)


def main() -> None:
    def before(j: Journey) -> None:
        import json

        path = j.input_module()
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["nodes"] = [_GONE]
        path.write_text(json.dumps(doc), encoding="utf-8")

    Journey(before).run(story)


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("j20"))


def test_a_missing_picture_shows_only_in_edit(run: dict) -> None:
    assert step(run, "view") == {"shown": False, "file": "gone.png"}
    assert step(run, "edit") == {"shown": True, "file": "gone.png"}
    assert "Choose Picture…" in step(run, "menu")


def test_choose_picture_points_it_at_the_new_file(run: dict) -> None:
    assert step(run, "chosen-src") == "pictures/found.png"
    assert step(run, "after-choose")["shown"] is False
    # It waits in the edit until Save (S107) ...
    assert step(run, "waiting") == ["found.png"]
    assert step(run, "save") is True
    assert step(run, "saved-src") == "pictures/found.png"
    # ... then it is in the device's folder only.
    assert step(run, "after-save") == ["found.png"]


def test_paste_then_cancel_leaves_nothing(run: dict) -> None:
    assert step(run, "pasted-waiting") == ["found.png", "pasted.png"]
    assert step(run, "after-cancel") == ["found.png"]


if __name__ == "__main__":
    main()
