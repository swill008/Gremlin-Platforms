# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Journey 5: Button Map unsaved edits survive a crash.

First run of the program: the user opens the pJoy Pro's Button Map, saves
it with a blue photo, then edits again: draws a rectangle and chooses a
red photo. A recovery copy is written (as the autosave timer does), and
the program ends without closing anything (a crash).

Second run, same data folder: the Button Map offers the unsaved edits.
Not now keeps both the copy and the red photo (the map shows it). Edit
offers them again; Restore opens them for editing (the rectangle and the
red photo, unsaved). Save writes both to the module file, removes the
recovery copy and the kept photo, and the map opened again offers nothing.

Spec: 07 S32, S34 (Restore / Discard / Not now; Not now keeps both and
offers them next time), S36, S23; the audit 3 decision on the recovery
offer (AU-115, AU-08); 07 S20 and 01 S142, S143 (results on the message
line, choosers through the shared FilePicker). No known gap.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _harness import Journey, run_journey, step  # noqa: E402

_COLOURS = {"#336699": "blue", "#993366": "red"}


def _open_map(j: Journey) -> object:
    j.ev('openButtonMapForCard(_moduleModel.cardMap("pjoy_pro"))')
    window = j.window("Button Map")
    j.wait_until(lambda: j.ev("loadedDevice", window) == "pJoy Pro", "the pJoy's map")
    return window


def _editor_ready(j: Journey, window: object) -> None:
    j.wait_until(
        lambda: j.ev("editing && _ed() !== null && _ed().seeded === true", window),
        "the editor in Edit",
    )


def _photo(j: Journey, window: object) -> str:
    """The colour of the photo file the saved map names."""
    from PySide6 import QtCore, QtGui

    url = j.ev("_hw.imageUrl(JSON.parse(_hw.load(targetName)).image)", window)
    image = QtGui.QImage(QtCore.QUrl(str(url)).toLocalFile())
    if image.isNull():
        return "none"
    name = image.pixelColor(2, 2).name()
    return _COLOURS.get(name, name)


def _state(j: Journey, window: object) -> dict:
    return {
        "copy": bool(j.ev("_hw.loadRecovery(targetName).length > 0", window)),
        "kept-photo": bool(j.ev("_hw.hasPhotoStash(targetName)", window)),
        "photo": _photo(j, window),
    }


def _choose_photo(j: Journey, window: object, colour: str) -> None:
    """Photo > Choose Photo...: the file picked in its file dialog, OK.

    The chooser is the shared FilePicker (01 S143): its own file dialog is
    set up as Choose Photo opens it, given the file and accepted.
    """
    import json

    from PySide6 import QtCore, QtGui

    from gremlin import util

    image = QtGui.QImage(64, 64, QtGui.QImage.Format.Format_RGB32)
    image.fill(QtGui.QColor(colour))
    path = pathlib.Path(util.userprofile_path()) / f"photo-{colour[1:]}.png"
    image.save(str(path))
    url = QtCore.QUrl.fromLocalFile(str(path)).toString()
    j.ev(
        "(function() { var d = _imageDialog.prepare();"
        f" d.selectedFile = {json.dumps(url)}; d.accepted(); return true }})()",
        window,
    )
    j.wait_until(
        lambda: j.ev("_hw.hasPhotoStash(targetName)", window), "the chosen photo"
    )


def crash(j: Journey) -> None:
    out = j.out
    window = _open_map(j)
    j.ev("enterEdit()", window)
    _editor_ready(j, window)
    _choose_photo(j, window, "#336699")
    out["first-save"] = j.ev("saveEdit(false)", window)
    j.ev("discardEdit()", window)
    out["saved"] = _state(j, window)

    # A second edit: a rectangle and a red photo, then a recovery copy.
    j.ev("enterEdit()", window)
    _editor_ready(j, window)
    # A rectangle drawn on the map (editor pixels, as a drag gives them).
    j.ev('_ed().addDrawFree("rect", 100, 100, 300, 250)', window)
    out["drawn"] = j.ev(
        "editorNodesNow().filter(function(n) { return n.kind === 'draw' }).length",
        window,
    )
    _choose_photo(j, window, "#993366")
    out["dirty"] = j.ev("isDirty()", window)
    j.ev("autosaveNow()", window)
    out["before-crash"] = _state(j, window)
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
        "editorNodesNow().some(function(n) { return n.kind === 'draw' })", window
    )
    out["restored-dirty"] = j.ev("isDirty()", window)

    out["restored-photo"] = _photo(j, window)

    # Save.
    out["save"] = j.ev("saveEdit(false)", window)
    j.ev("discardEdit()", window)
    out["after-save"] = _state(j, window)
    out["saved-rect"] = j.ev(
        "JSON.parse(_hw.load(targetName)).nodes.some("
        "function(n) { return n.kind === 'draw' })",
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


def test_the_first_run_leaves_a_copy_and_the_new_photo(run: dict) -> None:
    crashed = run["crash"]
    assert step(crashed, "first-save") is True
    assert step(crashed, "saved") == {
        "copy": False,
        "kept-photo": False,
        "photo": "blue",
    }
    assert step(crashed, "drawn") == 1
    assert step(crashed, "dirty") is True
    assert step(crashed, "before-crash") == {
        "copy": True,
        "kept-photo": True,
        "photo": "red",
    }
    assert step(crashed, "saved-nodes-before-crash") == 0


def test_the_restart_offers_the_edits(run: dict) -> None:
    again = run["reopen"]
    assert step(again, "offer-title") == "Unsaved Edits Found"
    assert step(again, "offer-buttons") == ["Restore", "Discard", "Not now"]


def test_not_now_keeps_the_copy_and_the_new_photo(run: dict) -> None:
    again = run["reopen"]
    assert step(again, "not-now") == {"copy": True, "kept-photo": True, "photo": "red"}
    assert step(again, "not-now-editing") is False
    assert step(again, "edit-offers") is True
    assert step(again, "edit-editing") is False


def test_restore_brings_both_back_and_save_keeps_them(run: dict) -> None:
    again = run["reopen"]
    assert step(again, "restored-rect") is True
    assert step(again, "restored-dirty") is True
    assert step(again, "restored-photo") == "red"
    assert step(again, "save") is True
    assert step(again, "after-save") == {
        "copy": False,
        "kept-photo": False,
        "photo": "red",
    }
    assert step(again, "saved-rect") is True
    assert step(again, "offer-after-save") is False


if __name__ == "__main__":
    main()
