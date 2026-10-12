# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Mapping Editor audit fixes in the window (07), driven in the running program
off-screen (its own process and user folder, test/journeys/_harness.py).

- A change made, its recovery copy written, the change undone and the
  window closed: the copy goes and the next open offers nothing (S32, S34).
- Cancel and Save stop a drag left open, so it can't hold Undo in the next
  edit (S55a).
- A narrow window unpins and folds Chips; opening the folded drawer keeps
  the user's kept pin for the next window (S131).
- A greyed Arrange row says why when the pointer is on it (S121).
- Keyboard Shortcuts lists the Mouse group before Keys (glossary).
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "journeys"))
from _harness import Journey, run_journey, step  # noqa: E402


def _open(j: Journey) -> object:
    j.ev('openDeviceMappingEditorForCard(_moduleModel.cardMap("pjoy_pro"))')
    w = j.window("Device Mapping Editor")
    j.wait_until(lambda: j.ev("loadedDevice", w) == "pJoy Pro", "the map")
    return w


def _edit(j: Journey, w: object) -> None:
    j.ev("enterEdit()", w)
    j.wait_until(
        lambda: j.ev("editing && _ed() !== null && _ed().seeded === true", w),
        "the editor in Edit",
    )


def _undone_change(j: Journey) -> None:
    o = j.out
    w = _open(j)
    _edit(j, w)
    j.ev('_ed().addDrawFree("rect", 100, 100, 300, 250)', w)
    j.ev("recoveryNow()", w)
    o["rec-written"] = j.ev("_hw.loadRecovery(targetName).length > 0", w)
    j.ev("_ed().undo()", w)
    o["rec-dirty"] = j.ev("isDirty()", w)
    # The window goes when it closes; the copy is read from the next one.
    j.ev("close()", w)
    j.settle()
    w = _open(j)
    j.settle()
    o["rec-after-close"] = j.ev("_hw.loadRecovery(targetName).length > 0", w)
    o["rec-offer"] = j.ev("_recoverGate.opened", w)
    if o["rec-offer"]:
        # (Old code: the copy goes so the later parts can start Edit.)
        j.ev("putOffRecovery(); _hw.clearRecovery(targetName)", w)


def _gestures(j: Journey) -> None:
    o = j.out
    w = j.window("Device Mapping Editor")
    _edit(j, w)
    j.ev("_ed().beginGesture()", w)
    j.ev("discardEdit()", w)
    o["g-after-cancel"] = j.ev("_ed().gestureActive", w)
    # (Left open, the next Edit would never start: ended here so the later
    # parts still run on the old code.)
    j.ev("_ed().stopGesture()", w)
    _edit(j, w)
    j.ev('_ed().addDrawFree("rect", 100, 100, 300, 250)', w)
    j.ev("_ed().beginGesture()", w)
    o["g-save"] = j.ev("saveEdit(false)", w)
    o["g-after-save"] = j.ev("_ed().gestureActive", w)
    j.ev("_ed().stopGesture()", w)
    j.ev("discardEdit()", w)


def _narrow(j: Journey) -> None:
    o = j.out
    w = j.window("Device Mapping Editor")
    j.ev("width = 1600", w)
    _edit(j, w)
    j.wait_until(lambda: j.ev("sidesRestored", w), "the kept side panels")
    # Both pinned and out, kept so.
    j.ev("_chipsSide.pinned = true; _chipsSide.open = true;"
         " sideChangedByUser(_chipsSide, 'chips');"
         " _layersSide.pinned = true; _layersSide.open = true;"
         " sideChangedByUser(_layersSide, 'layers')", w)
    j.settle()
    j.ev("width = minimumWidth", w)
    j.wait_until(lambda: j.ev("chipsSqueezed", w), "Chips folded for room")
    # The folded drawer clicked open: over the map, unpinned.
    j.ev("_chipsSide.unfold()", w)
    j.settle()
    o["sq-open"] = [j.ev("_chipsSide.open", w), j.ev("_chipsSide.pinned", w)]
    o["sq-kept-pin"] = j.ev('!!_opts.sidePanelState("chips").pinned', w)
    j.ev("width = 1600", w)
    j.wait_until(lambda: j.ev("_mapRow.width > 1500", w), "the wide window")
    j.settle()
    # On screen the user's open drawer stays as it is (S131); the kept pin
    # is still theirs.
    o["sq-widened"] = [j.ev("_chipsSide.open", w), j.ev("_chipsSide.pinned", w)]
    o["sq-widened-kept-pin"] = j.ev('!!_opts.sidePanelState("chips").pinned', w)
    j.ev("discardEdit()", w)


def _why(j: Journey) -> None:
    o = j.out
    w = j.window("Device Mapping Editor")
    _edit(j, w)
    j.ev('_ed().addDrawFree("rect", 100, 100, 300, 250)', w)
    # The new rectangle selected: it is already in the foreground.
    j.ev("(function() { var e = _ed(); var n = e.nodes.filter(function(x) {"
         " return x.kind === 'draw' || x.shape === 'rect' }); e.setSelection("
         "[n[n.length - 1].id]) })()", w)
    j.ev("cmdRev++", w)
    find = ("(function() { for (var i = 0; i < _cmdRows.length; i++)"
            " if (_cmdRows[i].id === 'moveToForeground') return _cmdRows[i].item;"
            " return null })()")
    o["why-greyed"] = j.ev(find + ".enabled === false", w)
    o["why-text"] = j.ev(find + ".whyText", w)
    j.ev("_arrangeMenu.popup(0, 0)", w)
    j.wait_until(lambda: j.ev("_arrangeMenu.opened", w), "the Arrange menu")
    watcher = ("(function() { var l = _arrangeMenu.contentItem; var c ="
               " l.children.concat(l.contentItem.children);"
               " for (var i = 0; i < c.length; i++)"
               " if (c[i].objectName === 'dmeCmdWhy')"
               " return c[i]; return null })()")
    # What the menu's hover watcher shows with the pointer on the row (the
    # row's middle in the watcher's coordinates). Qt's own hover delivery
    # isn't driven: an offscreen window sends the popup no hover.
    o["why-tip"] = j.ev("(function() { var x = " + watcher + "; var r = " + find + ";"
                        " var p = r.mapToItem(x, r.width / 2, r.height / 2);"
                        " return x.tipAt(p.x, p.y) })()", w)
    o["why-tip-enabled-row"] = j.ev(
        "(function() { var x = " + watcher + "; var r = _arrangeMenu.itemAt(0);"
        " var p = r.mapToItem(x, r.width / 2, r.height / 2);"
        " return x.tipAt(p.x, p.y) })()", w)
    j.ev("_arrangeMenu.close()", w)
    j.ev("discardEdit()", w)


def _shortcuts(j: Journey) -> None:
    w = j.window("Device Mapping Editor")
    rows = j.ev("_shortcutsWin.list.describe()", w)
    j.out["shortcut-groups"] = [r[2:] for r in rows if r.startswith("# ")][-2:]


def story(j: Journey) -> None:
    for part in (_undone_change, _gestures, _narrow, _why, _shortcuts):
        try:
            part(j)
        except Exception as exc:  # noqa: BLE001  (later parts still run)
            j.out["error"] = (j.out.get("error", "") + f" {part.__name__}: "
                              f"{type(exc).__name__}: {exc}").strip()


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module()

    Journey(before).run(story)


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("bm_fix_win"))


def test_undone_edit_leaves_no_recovery_copy(run: dict) -> None:
    assert step(run, "rec-written") is True
    assert step(run, "rec-dirty") is False
    assert step(run, "rec-after-close") is False
    assert step(run, "rec-offer") is False


def test_cancel_and_save_stop_an_open_drag(run: dict) -> None:
    assert step(run, "g-after-cancel") is False
    assert step(run, "g-save") is True
    assert step(run, "g-after-save") is False


def test_narrow_window_keeps_the_users_pin(run: dict) -> None:
    assert step(run, "sq-open") == [True, False]
    assert step(run, "sq-kept-pin") is True
    assert step(run, "sq-widened") == [True, False]
    assert step(run, "sq-widened-kept-pin") is True


def test_greyed_row_says_why(run: dict) -> None:
    assert step(run, "why-greyed") is True
    assert step(run, "why-text") == "Already in the foreground"
    assert step(run, "why-tip") == "Already in the foreground"
    assert step(run, "why-tip-enabled-row") == ""


def test_shortcuts_list_mouse_before_keys(run: dict) -> None:
    assert step(run, "shortcut-groups") == ["Mouse", "Keys"]


if __name__ == "__main__":
    main()
