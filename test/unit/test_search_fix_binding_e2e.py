# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Fix a binding from Search, plugged in or not (01 S195), and the load
notice naming an unplugged device (04 S32a), end to end.

A journey (test/journeys/_harness.py): the app off-screen in its own
process with a temporary USERPROFILE, the fake "pJoy Pro", vJoy 1 and 2
only, and an input module for "HID Remapper 2DGG", a device the driver
never lists (not plugged in all session; "the X52" below). The profile
Delta binds its Button 1 to Map to vJoy vJoy 3 Button 1 (there is no
vJoy 3) and pJoy Pro's Button 1 to vJoy 1 Button 1. Delta is saved and
opened again (File > Load Profile), then through the real Search window
and its SearchModel:

1. The load notice names the X52 by its module name, never its id.
2. "Binding output not found" lists the X52's Button 1.
3. Remove binding… asks (naming the binding), Remove: the row is gone,
   the profile is changed, the health count drops; Undo puts it back.
4. Change target… to vJoy 1 Button 2: the row is no longer not found.
5. Open on the X52's row says it isn't plugged in (S195's message).

Only the hardware edge is faked (fake driver, fake vJoy).

Spec: 01 S195, 04 S32a; claude/plans/search-fix-binding-contract.md
section 4.
"""

from __future__ import annotations

import json
import pathlib
import sys
import traceback
from typing import Any

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test" / "journeys"))
from _harness import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    Journey,
    JourneyIncomplete,
    run_journey,
)

STICK = "pJoy Pro"
MODULE_NAME = "HID Remapper 2DGG"
OPEN_MESSAGE = (
    f"{MODULE_NAME} isn't plugged in, so its page can't open. "
    "Use Remove binding… or Change target… here, or plug it in."
)
ASK = f"Remove the Map to vJoy binding from Button 1 of {MODULE_NAME} (Default mode)?"


# +-------------------------------------------------------------------------
# | Script side (the child process)


class _Part:
    """One part of the story; an error is recorded under its name and the
    next part still runs."""

    def __init__(self, j: Journey, name: str) -> None:
        self.j = j
        self.name = name

    def __enter__(self) -> _Part:
        return self

    def __exit__(self, kind: Any, exc: Any, tb: Any) -> bool:  # noqa: ANN401
        if exc is not None:
            self.j.out[f"{self.name}:error"] = f"{kind.__name__}: {exc}"
            self.j.out[f"{self.name}:traceback"] = traceback.format_exc()
        return True


def _model(window: Any) -> Any:  # noqa: ANN401
    from gremlin.ui.search_model import SearchModel

    found = window.findChild(SearchModel)
    assert found is not None, "no SearchModel in the Search window"
    return found


def _results(model: Any) -> list[dict]:  # noqa: ANN401
    rows = Journey.catalog_rows(model)
    out = []
    for n, r in enumerate(rows):
        if str(r.get("rowKind") or "") != "result":
            continue
        out.append(
            {
                "_row": n,
                "source": str(r.get("source") or ""),
                "device": str(r.get("deviceName") or ""),
                "input": str(r.get("inputLabel") or ""),
                "mode": str(r.get("mode") or ""),
                "targets": [str(t) for t in (r.get("targets") or [])],
                "notFound": bool(r.get("notFound")),
            }
        )
    return out


def _health(model: Any) -> int:  # noqa: ANN401
    """The "Binding output not found" filter's count."""
    for f in model.property("filters") or []:
        if str(f.get("name")) == "notFound":
            return int(f.get("count") or 0)
    raise AssertionError("no notFound filter")


def _x52_rows(j: Journey, model: Any) -> list[dict]:  # noqa: ANN401
    """The X52's rows in the open profile, with the not-found filter on."""
    model.setProperty("text", "")
    j.wait_until(lambda: not model._debounce.isActive(), "the search", timeout=5.0)
    model.clearFilters()
    model.setFilter("notFound", True)
    j.settle()
    return [r for r in _results(model) if r["input"] == "Button 1" and r["notFound"]]


def _all_x52(j: Journey, model: Any) -> list[dict]:  # noqa: ANN401
    """Every Button 1 row of the open profile whose device is the X52 (no
    filter; an empty box shows nothing)."""
    model.clearFilters()
    model.setProperty("text", "Button 1")
    j.wait_until(lambda: not model._debounce.isActive(), "the search", timeout=5.0)
    j.settle()
    return [
        r
        for r in _results(model)
        if r["source"] == "open" and r["input"] == "Button 1" and r["device"] != STICK
    ]


def _profiles(j: Journey) -> str:
    import uuid

    from PySide6 import QtCore

    from gremlin import util
    from gremlin.signal import signal

    x52 = uuid.UUID(j.out["0:x52-guid"])
    pjoy = j.stick(STICK).device_guid.uuid
    j.map_button(x52, 1, "Default", 1, vjoy=3)
    j.map_button(pjoy, 1, "Default", 1, vjoy=1)
    signal.profileChanged.emit()
    j.settle()
    path = pathlib.Path(util.profiles_dir()) / "Delta.xml"
    url = QtCore.QUrl.fromLocalFile(str(path)).toString()
    assert j.backend.saveProfile(url), "Delta was not saved"
    notices: list[list[str]] = []
    signal.showNotification.connect(lambda t, x: notices.append([t, x]))
    j.reopen(url)
    j.settle()
    j.out["1:notices"] = notices
    j.out["0:loaded"] = pathlib.Path(j.backend.profilePath()).name
    j.out["0:clean"] = not bool(j.backend.profileContainsUnsavedChanges)
    return url


def _part_listed(j: Journey, model: Any) -> None:  # noqa: ANN401
    j.out["2:rows"] = _x52_rows(j, model)
    j.out["2:health"] = _health(model)


def _ask(j: Journey, window: Any, row: int) -> Any:  # noqa: ANN401
    """Remove binding… on a row (the menu's and side panel's entry): the
    question it opens."""
    dialog = j.ev(f"askRemove({row})", window)
    assert dialog is not None, "Remove binding… asked nothing"
    j.settle()
    return dialog


def _part_remove(j: Journey, window: Any, model: Any) -> None:  # noqa: ANN401
    rows = _x52_rows(j, model)
    assert rows, "no not-found X52 row"
    before = _health(model)
    j.out["3:fixes"] = dict(model.fixes(rows[0]["_row"]))
    # Cancel first: nothing changes.
    dialog = _ask(j, window, rows[0]["_row"])
    j.out["3:ask"] = str(dialog.property("titleText") or "")
    j.out["3:action"] = str(dialog.property("actionText") or "")
    j.ev("cancel(); true", dialog)
    j.settle()
    j.out["3:after-cancel"] = len(_x52_rows(j, model))
    j.out["3:dirty-after-cancel"] = bool(j.backend.profileContainsUnsavedChanges)
    # Remove.
    rows = _x52_rows(j, model)
    dialog = _ask(j, window, rows[0]["_row"])
    j.ev("accept(); true", dialog)
    j.wait_until(lambda: not _x52_rows(j, model), "the row to go", timeout=8.0)
    j.out["3:gone"] = _all_x52(j, model)
    j.out["3:dirty"] = bool(j.backend.profileContainsUnsavedChanges)
    model.setFilter("notFound", True)
    j.settle()
    j.out["3:health"] = [before, _health(model)]
    j.out["3:in-profile"] = _bindings(j)
    j.out["3:can-undo"] = bool(model.property("canUndo"))
    # Undo (Ctrl+Z in the window).
    j.ev("undo(); true", window)
    j.wait_until(lambda: _x52_rows(j, model), "the row back", timeout=8.0)
    j.out["3:back"] = _x52_rows(j, model)
    j.out["3:health-back"] = _health(model)
    j.out["3:in-profile-back"] = _bindings(j)


def _bindings(j: Journey) -> list:
    """What the X52's Button 1 sends in the open profile: [[vjoy, button]]."""
    import uuid

    x52 = uuid.UUID(j.out["0:x52-guid"])
    sends = []
    for item in j.profile.inputs.get(x52, []):
        if item.input_id != 1 or item.mode != "Default":
            continue
        for binding in item.action_sequences:
            for action in binding.root_action.get_actions()[0]:
                sends.append(
                    [
                        getattr(action, "vjoy_device_id", None),
                        getattr(action, "vjoy_input_id", None),
                    ]
                )
    return sends


def _part_change(j: Journey, window: Any, model: Any) -> None:  # noqa: ANN401
    rows = _x52_rows(j, model)
    assert rows, "no not-found X52 row"
    j.out["4:before"] = _bindings(j)
    # Change target…: the box, vJoy 1 Button 2 picked, Change.
    j.ev(f"askChangeTarget({rows[0]['_row']}); true", window)
    j.wait_until(lambda: j.ev("_targetBox.opened", window), "the box", timeout=5.0)
    j.out["4:start"] = j.ev(
        "({ vjoy: _targetBox.vjoyId, kind: _targetBox.inputType,"
        " id: _targetBox.inputId })",
        window,
    )
    j.ev("_targetBox.vjoyId = 1; _targetBox.inputId = 2; true", window)
    j.press_in("_targetBox", "Change", window)
    j.wait_until(lambda: not _x52_rows(j, model), "not found to clear", timeout=8.0)
    j.out["4:not-found"] = _x52_rows(j, model)
    j.out["4:rows"] = _all_x52(j, model)
    j.out["4:after"] = _bindings(j)
    j.out["4:dirty"] = bool(j.backend.profileContainsUnsavedChanges)
    j.ev("undo(); true", window)
    j.wait_until(lambda: _x52_rows(j, model), "the old target back", timeout=8.0)
    j.out["4:undone"] = _bindings(j)


def _part_open(j: Journey, window: Any, model: Any) -> None:  # noqa: ANN401
    rows = _x52_rows(j, model)
    assert rows, "no X52 row"
    j.ev(f"open({rows[0]['_row']}); true", window)
    j.settle()
    j.out["5:shown"] = bool(j.ev("_openMessage.visible", window))
    j.out["5:said"] = str(j.ev("_openMessage.text", window) or "")
    # Still on Home: no page opened.
    j.out["5:page"] = bool(j.ev("!!deviceBindingsPane()"))


def story(j: Journey) -> None:
    _profiles(j)
    window = j.ev('_root.openSearch("")')
    assert window is not None, "openSearch gave no window"
    model = _model(window)
    j.wait_until(
        lambda: model.search_index().status().get("state") == "ready",
        "the search index",
        timeout=30.0,
    )
    j.settle()
    for name, part in (
        ("2", lambda: _part_listed(j, model)),
        ("3", lambda: _part_remove(j, window, model)),
        ("4", lambda: _part_change(j, window, model)),
        ("5", lambda: _part_open(j, window, model)),
    ):
        with _Part(j, name):
            part()


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module()
        import dill

        # Never in the fake driver: not plugged in.
        guid = dill.GUID(dill._GUID(Data1=0xC6EC6FC0, Data2=1, Data3=1, Data4=(5,) * 8))
        j.out["0:x52-guid"] = str(guid.uuid)
        j.input_module(MODULE_NAME, guid=guid, slug="hid_remapper_2dgg")
        j.vjoy_module(1)
        j.vjoy_module(2)

    Journey(before, vjoy_ids=(1, 2)).run(story)


# +-------------------------------------------------------------------------
# | Pytest side


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("search_fix_binding_e2e"))


def _step(out: dict, key: str) -> Any:  # noqa: ANN401
    if key in out:
        return out[key]
    part = key.split(":", 1)[0]
    raise JourneyIncomplete(
        f"Part {part} never reached {key!r}.\n"
        f"Error: {out.get(part + ':error', out.get('error', '(none)'))}\n"
        f"{out.get(part + ':traceback', out.get('traceback', ''))}\n"
        f"--- stderr\n{out.get('_stderr', '')}"
    )


def test_delta_is_saved_and_open_again(run: dict) -> None:
    assert _step(run, "0:loaded") == "Delta.xml"
    assert _step(run, "0:clean") is True


def test_the_load_notice_names_the_unplugged_device_by_its_module_name(
    run: dict,
) -> None:
    notices = _step(run, "1:notices")
    texts = [x for t, x in notices if t == "Open Profile"]
    assert texts == [f"{MODULE_NAME}: 1 binding output not found."], notices
    assert run["0:x52-guid"] not in json.dumps(notices), notices


def test_search_lists_the_binding_under_binding_output_not_found(run: dict) -> None:
    rows = _step(run, "2:rows")
    assert len(rows) == 1, rows
    assert rows[0]["device"] == MODULE_NAME, rows
    assert _step(run, "2:health") >= 1


def test_remove_binding_asks_then_removes_and_undo_puts_it_back(run: dict) -> None:
    fixes = _step(run, "3:fixes")
    assert fixes.get("remove") is True and fixes.get("changeTarget") is True, fixes
    assert _step(run, "3:ask") == ASK
    assert _step(run, "3:action") == "Remove"
    assert _step(run, "3:after-cancel") == 1, "Cancel removed the binding"
    assert _step(run, "3:dirty-after-cancel") is False
    assert _step(run, "3:gone") == [], run["3:gone"]
    assert _step(run, "3:dirty") is True
    before, after = _step(run, "3:health")
    assert after == before - 1, run["3:health"]
    assert _step(run, "3:in-profile") == []
    assert _step(run, "3:can-undo") is True
    assert len(_step(run, "3:back")) == 1
    assert _step(run, "3:health-back") == before
    assert _step(run, "3:in-profile-back") == [[3, 1]]


def test_change_target_to_an_existing_vjoy_clears_not_found(run: dict) -> None:
    assert _step(run, "4:before") == [[3, 1]]
    start = _step(run, "4:start")
    assert start["vjoy"] == 3 and start["id"] == 1, start
    assert _step(run, "4:not-found") == []
    rows = _step(run, "4:rows")
    assert len(rows) == 1 and not rows[0]["notFound"], rows
    assert _step(run, "4:after") == [[1, 2]]
    assert _step(run, "4:dirty") is True
    assert _step(run, "4:undone") == [[3, 1]]


def test_open_on_the_unplugged_device_says_it_isnt_plugged_in(run: dict) -> None:
    assert _step(run, "5:shown") is True
    assert _step(run, "5:said") == OPEN_MESSAGE
    assert _step(run, "5:page") is False


def test_no_program_errors(run: dict) -> None:
    assert run.get("_errors") == [], run.get("_errors")
    assert "error" not in run, run.get("traceback")


if __name__ == "__main__":
    main()
