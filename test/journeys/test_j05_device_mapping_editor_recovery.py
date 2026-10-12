# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Journey 5: Device Mapping Editor unsaved edits survive a crash.

First run of the program: the user opens the pJoy Pro's Device Mapping Editor, adds a
blue picture to the background (Background > Add Picture to Background...)
and saves, then edits again: draws a rectangle and adds a red picture to
the background. A recovery copy is written (as the recovery timer does),
and the program ends without closing anything (a crash).

Second run, same data folder: the Device Mapping Editor offers the unsaved edits.
Not now keeps both the copy and the edit's temporary folder with the red
picture (07 S107; the saved map still has only the blue one). Edit offers
them again; Restore opens them for editing (the rectangle and both
background pictures, unsaved). Save writes both to the module file,
removes the recovery copy and the temporary folder, and the map opened
again offers nothing.

Spec: 07 S32, S34 (Restore / Discard / Not now; Not now keeps both and
offers them next time), S36, S23, S40 (Add Picture to Background: the top
background layer), S111; the audit 3 decision on the recovery offer
(AU-115, AU-08); 07 S20 and 01 S142, S143 (results on the message line,
choosers through the shared FilePicker). No known gap.
"""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _harness import Journey, run_journey, step  # noqa: E402

_COLOURS = {"#336699": "blue", "#993366": "red"}
# How many background layers the editor shows (07 S111).
_EDITOR_BACKGROUND = (
    "editorNodesNow().filter(function(n) { return n.plane === 'background' }).length"
)


def _open_map(j: Journey) -> object:
    j.ev('openDeviceMappingEditorForCard(_moduleModel.cardMap("pjoy_pro"))')
    window = j.window("Device Mapping Editor")
    j.wait_until(lambda: j.ev("loadedDevice", window) == "pJoy Pro", "the pJoy's map")
    return window


def _editor_ready(j: Journey, window: object) -> None:
    j.wait_until(
        lambda: j.ev("editing && _ed() !== null && _ed().seeded === true", window),
        "the editor in Edit",
    )


def _colour(j: Journey, window: object, ref: str) -> str:
    from PySide6 import QtCore, QtGui

    url = j.ev(f"_hw.imageUrl({json.dumps(ref)})", window)
    image = QtGui.QImage(QtCore.QUrl(str(url)).toLocalFile())
    if image.isNull():
        return "none"
    name = image.pixelColor(2, 2).name()
    return _COLOURS.get(name, name)


def _background(j: Journey, window: object) -> list[str]:
    """The colours of the saved map's background pictures, bottom first
    (07 S111: background nodes, "plane": "background")."""
    refs = j.ev(
        "JSON.stringify((JSON.parse(_hw.load(targetName)).nodes || [])"
        ".filter(function(n) { return n.plane === 'background' })"
        ".map(function(n) { return String(n.src || '') }))",
        window,
    )
    return [_colour(j, window, ref) for ref in json.loads(str(refs))]


def _state(j: Journey, window: object) -> dict:
    return {
        "copy": bool(j.ev("_hw.loadRecovery(targetName).length > 0", window)),
        "edit-kept": bool(j.ev("_hw.editActiveFor(targetName, '')", window)),
        "background": _background(j, window),
    }


def _add_to_background(j: Journey, window: object, colour: str) -> None:
    """Background > Add Picture to Background...: the file picked in its
    file dialog ("Choose Background Picture", 07 S40), OK.

    The chooser is the shared FilePicker (01 S143): its own file dialog is
    set up as the menu opens it, given the file and accepted.
    """
    from PySide6 import QtCore, QtGui

    from gremlin import util

    image = QtGui.QImage(64, 64, QtGui.QImage.Format.Format_RGB32)
    image.fill(QtGui.QColor(colour))
    path = pathlib.Path(util.userprofile_path()) / f"photo-{colour[1:]}.png"
    image.save(str(path))
    url = QtCore.QUrl.fromLocalFile(str(path)).toString()
    assert j.ev("_bgPictureDialog.title", window) == "Choose Background Picture"
    before = j.ev(_EDITOR_BACKGROUND, window)
    j.ev(
        "(function() { var d = _bgPictureDialog.prepare();"
        f" d.selectedFile = {json.dumps(url)}; d.accepted(); return true }})()",
        window,
    )
    j.wait_until(
        lambda: j.ev(_EDITOR_BACKGROUND, window) == before + 1,
        "the picture on the background",
    )


def crash(j: Journey) -> None:
    out = j.out
    window = _open_map(j)
    j.ev("enterEdit()", window)
    _editor_ready(j, window)
    _add_to_background(j, window, "#336699")
    out["first-save"] = j.ev("saveEdit(false)", window)
    j.ev("discardEdit()", window)
    out["saved"] = _state(j, window)

    # A second edit: a rectangle and a red background picture, then a
    # recovery copy.
    j.ev("enterEdit()", window)
    _editor_ready(j, window)
    # A rectangle drawn on the map (editor pixels, as a drag gives them).
    j.ev('_ed().addDrawFree("rect", 100, 100, 300, 250)', window)
    out["drawn"] = j.ev(
        "editorNodesNow().filter(function(n) {"
        " return n.kind === 'draw' && n.plane !== 'background' }).length",
        window,
    )
    _add_to_background(j, window, "#993366")
    out["dirty"] = j.ev("isDirty()", window)
    j.ev("recoveryNow()", window)
    out["before-crash"] = _state(j, window)
    # The saved map: the blue background picture only.
    out["saved-nodes-before-crash"] = j.ev(
        "JSON.parse(_hw.load(targetName)).nodes.length", window
    )
    # Journey.run ends the process now: no Save, no Cancel, no quit.


def reopen(j: Journey) -> None:
    out = j.out
    window = _open_map(j)
    j.wait_until(lambda: j.ev("_recoverGate.opened", window), "the recovery offer")
    out["offer-title"] = j.ev("_recoverGate.titleText", window)
    out["offer-buttons"] = [
        j.ev("_recoverGate.confirmText", window),
        j.ev("_recoverGate.discardText", window),
        j.ev("_recoverGate.cancelText", window),
    ]
    # Not now.
    j.press_in("_recoverGate", "Not now", window)
    j.wait_until(lambda: not j.ev("_recoverGate.opened", window), "the offer to close")
    out["not-now"] = _state(j, window)
    out["not-now-editing"] = j.ev("editing", window)

    # Edit: offered again. Restore.
    j.ev("enterEdit()", window)
    out["edit-offers"] = j.ev("_recoverGate.opened", window)
    out["edit-editing"] = j.ev("editing", window)
    j.press_in("_recoverGate", "Restore", window)
    _editor_ready(j, window)
    out["restored-rect"] = j.ev(
        "editorNodesNow().some(function(n) {"
        " return n.kind === 'draw' && n.shape === 'rect' })",
        window,
    )
    out["restored-background"] = j.ev(_EDITOR_BACKGROUND, window)
    out["restored-dirty"] = j.ev("isDirty()", window)

    out["restored-file"] = _background(j, window)

    # Save.
    out["save"] = j.ev("saveEdit(false)", window)
    j.ev("discardEdit()", window)
    out["after-save"] = _state(j, window)
    out["saved-rect"] = j.ev(
        "JSON.parse(_hw.load(targetName)).nodes.some("
        "function(n) { return n.kind === 'draw' && n.shape === 'rect' })",
        window,
    )
    out["offer-after-save"] = j.ev("offerRecovery()", window)


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module()

    phase = sys.argv[1] if len(sys.argv) > 1 else "crash"
    Journey(before if phase == "crash" else None).run(
        crash if phase == "crash" else reopen
    )


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("j05")
    first = run_journey(__file__, home, "crash")
    second = run_journey(__file__, home, "reopen")
    return {"crash": first, "reopen": second}


def test_the_first_run_leaves_a_copy_and_the_new_picture(run: dict) -> None:
    crashed = run["crash"]
    assert step(crashed, "first-save") is True
    assert step(crashed, "saved") == {
        "copy": False,
        "edit-kept": False,
        "background": ["blue"],
    }
    assert step(crashed, "drawn") == 1
    assert step(crashed, "dirty") is True
    # The red picture waits in the edit's temporary folder (07 S107): the
    # saved map still has only the blue one.
    assert step(crashed, "before-crash") == {
        "copy": True,
        "edit-kept": True,
        "background": ["blue"],
    }
    assert step(crashed, "saved-nodes-before-crash") == 1


def test_the_restart_offers_the_edits(run: dict) -> None:
    again = run["reopen"]
    assert step(again, "offer-title") == "Unsaved Edits Found"
    assert step(again, "offer-buttons") == ["Restore", "Discard", "Not now"]


def test_not_now_keeps_the_copy_and_the_new_picture(run: dict) -> None:
    again = run["reopen"]
    assert step(again, "not-now") == {
        "copy": True,
        "edit-kept": True,
        "background": ["blue"],
    }
    assert step(again, "not-now-editing") is False
    assert step(again, "edit-offers") is True
    assert step(again, "edit-editing") is False


def test_restore_brings_both_back_and_save_keeps_them(run: dict) -> None:
    again = run["reopen"]
    assert step(again, "restored-rect") is True
    # Both background pictures, the red one on top (07 S40).
    assert step(again, "restored-background") == 2
    assert step(again, "restored-dirty") is True
    # Unsaved: the file still has only the blue picture until Save (07 S107).
    assert step(again, "restored-file") == ["blue"]
    assert step(again, "save") is True
    assert step(again, "after-save") == {
        "copy": False,
        "edit-kept": False,
        "background": ["blue", "red"],
    }
    assert step(again, "saved-rect") is True
    assert step(again, "offer-after-save") is False


if __name__ == "__main__":
    main()
