# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Health (01 S197) and Search without health (01 S196), end to end.

A journey (test/journeys/_harness.py): the app off-screen in its own
process with a temporary USERPROFILE, the fake "pJoy Pro", vJoy 1 and 2
only, and an input module for "HID Remapper 2DGG", a device the driver
never lists (not plugged in all session; "the X52" below). The profile
Echo binds the X52's Button 1 to vJoy 3 Button 1 (there is no vJoy 3),
the X52's Button 2 to vJoy 1 Button 3 and pJoy Pro's Button 1 to vJoy 1
Button 1. Echo is saved and opened again, then:

1. health.broken_count() is 1; the toolbar Health button shows 1 in red.
2. tools.health opens the Health window: "Binding output not found (1)"
   is there and ticked, its row has the ⚠ and the Why panel's reason.
3. Change target… (Health) to vJoy 1 Button 2: the count is 0, the button
   gray with no number; Undo: 1 again.
4. The Search window has no Health part: no health filters, no ⚠ and no
   "Not plugged in" on its lines.
5. Two X52 rows picked (Ctrl+click), Remove binding…: both go; one Undo
   puts both back.

Only the hardware edge is faked (fake driver, fake vJoy).

Spec: 01 S196, 01 S197; claude/plans/search-health-contract.md section 7.
"""

from __future__ import annotations

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
WARN = "⚠"


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


def _broken() -> int:
    from gremlin import health

    return int(health.broken_count())


def _texts(j: Journey, item: Any) -> list[str]:  # noqa: ANN401
    """Every visible text under an item (labels, chips, badges)."""
    out = []
    for it in j.walk(item):
        if not it.isVisible():
            continue
        text = it.property("text")
        if isinstance(text, str) and text:
            out.append(text)
    return out


def _health_button(j: Journey) -> Any:  # noqa: ANN401
    """The toolbar's Health button (caption "Health")."""
    for it in j.walk(j.win.contentItem()):
        if it.property("caption") == "Health" or it.objectName() == "healthButton":
            return it
    raise AssertionError("no Health button in the toolbar")


def _button(j: Journey) -> dict:
    """What the Health button shows: its number, colour and tooltip."""
    button = _health_button(j)
    colour = str(j.ev("String(color)", button))
    styles = {
        name: str(j.ev(f"String(Style.{name})"))
        for name in (
            "danger",
            "dangerBright",
            "dangerText",
            "fgMuted",
            "fgSoft",
            "fg",
            "fgDisabled",
        )
    }
    texts = _texts(j, button)
    return {
        "visible": bool(button.isVisible()),
        "color": colour,
        "red": colour
        in (styles["danger"], styles["dangerBright"], styles["dangerText"]),
        "gray": colour
        in (styles["fgMuted"], styles["fgSoft"], styles["fgDisabled"], styles["fg"]),
        "digits": [t for t in texts if t.strip().isdigit()],
        "tooltip": str(j.ev("String(tooltip)", button) or ""),
    }


def _model_of(window: Any, name: str) -> Any:  # noqa: ANN401
    """The window's model whose class name contains name."""
    from PySide6 import QtCore

    for obj in window.findChildren(QtCore.QObject):
        if name in obj.metaObject().className():
            if hasattr(obj, "roleNames"):
                return obj
    raise AssertionError(f"no {name} model in the window")


def _rows(model: Any) -> list[dict]:  # noqa: ANN401
    out = []
    for n, r in enumerate(Journey.catalog_rows(model)):
        if str(r.get("rowKind") or "result") != "result":
            continue
        out.append(
            {
                "_row": n,
                "device": str(r.get("deviceName") or ""),
                "input": str(r.get("inputLabel") or ""),
                "notFound": bool(r.get("notFound")),
                "notPlugged": bool(r.get("notPlugged")),
                "why": str(r.get("why") or ""),
                "checks": [str(c) for c in (r.get("checks") or [])],
            }
        )
    return out


def _checks(model: Any) -> list[dict]:  # noqa: ANN401
    """The sidebar's tick boxes: [{name, label, count, checked}]."""
    found = model.property("checks")
    if found is None:
        found = model.property("filters")
    out = []
    for c in found or []:
        out.append(
            {
                "name": str(c.get("name") or c.get("check") or ""),
                "label": str(c.get("label") or c.get("text") or ""),
                "count": int(c.get("count") or 0),
                "checked": bool(c.get("checked", c.get("on", False))),
            }
        )
    return out


def _bindings(j: Journey, uid: Any, button: int) -> list:  # noqa: ANN401
    """What a button sends in the open profile: [[vjoy, button]]."""
    sends = []
    for item in j.profile.inputs.get(uid, []):
        if item.input_id != button or item.mode != "Default":
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


def _x52(j: Journey) -> Any:  # noqa: ANN401
    import uuid

    return uuid.UUID(j.out["0:x52-guid"])


def _profile(j: Journey) -> None:
    from PySide6 import QtCore

    from gremlin import util
    from gremlin.signal import signal

    pjoy = j.stick(STICK).device_guid.uuid
    j.map_button(_x52(j), 1, "Default", 1, vjoy=3)
    j.map_button(_x52(j), 2, "Default", 3, vjoy=1)
    j.map_button(pjoy, 1, "Default", 1, vjoy=1)
    signal.profileChanged.emit()
    j.settle()
    path = pathlib.Path(util.profiles_dir()) / "Echo.xml"
    url = QtCore.QUrl.fromLocalFile(str(path)).toString()
    assert j.backend.saveProfile(url), "Echo was not saved"
    j.reopen(url)
    j.settle()
    j.out["0:loaded"] = pathlib.Path(j.backend.profilePath()).name


def _part_toolbar(j: Journey) -> None:
    j.out["1:broken"] = j.await_value(_broken, 1, timeout=20.0)
    j.wait_until(lambda: _button(j)["digits"] == ["1"], "the button's 1", timeout=10.0)
    j.out["1:button"] = _button(j)


def _not_found_rows(model: Any) -> list[dict]:  # noqa: ANN401
    return [r for r in _rows(model) if r["notFound"] or "notFound" in r["checks"]]


def _part_window(j: Journey) -> tuple[Any, Any]:
    j.ev('Commands.trigger("tools.health"); true')
    window = j.window("Health")
    model = _model_of(window, "Health")
    j.wait_until(lambda: _not_found_rows(model), "the not-found row", timeout=20.0)
    j.settle()
    j.out["2:checks"] = _checks(model)
    rows = _not_found_rows(model)
    j.out["2:rows"] = rows
    j.out["2:texts"] = _texts(j, window.contentItem())
    # The Why panel: the row picked.
    j.ev(f"pick({rows[0]['_row']}); true", window)
    j.settle()
    j.out["2:why-texts"] = _texts(j, window.contentItem())
    return window, model


def _part_change(j: Journey, window: Any, model: Any) -> None:  # noqa: ANN401
    rows = [r for r in _not_found_rows(model) if r["input"] == "Button 1"]
    assert rows, "no not-found row"
    j.ev(f"pick({rows[0]['_row']}); askChangeTarget(); true", window)
    j.wait_until(lambda: j.ev("_targetBox.opened", window), "the box", timeout=5.0)
    j.ev("_targetBox.vjoyId = 1; _targetBox.inputId = 2; true", window)
    j.press_in("_targetBox", "Change", window)
    j.out["3:broken"] = j.await_value(_broken, 0, timeout=10.0)
    j.out["3:sends"] = _bindings(j, _x52(j), 1)
    j.await_value(lambda: _button(j)["digits"], [], timeout=10.0)
    j.out["3:button"] = _button(j)
    j.ev("undo(); true", window)
    j.out["3:broken-undo"] = j.await_value(_broken, 1, timeout=10.0)
    j.out["3:sends-undo"] = _bindings(j, _x52(j), 1)
    j.await_value(lambda: _button(j)["digits"], ["1"], timeout=10.0)
    j.out["3:button-undo"] = _button(j)


def _part_search(j: Journey) -> None:
    window = j.ev('_root.openSearch("Button")')
    assert window is not None, "openSearch gave no window"
    model = _model_of(window, "SearchModel")
    j.wait_until(
        lambda: model.search_index().status().get("state") == "ready",
        "the search index",
        timeout=30.0,
    )
    j.wait_until(lambda: not model._debounce.isActive(), "the search", timeout=5.0)
    j.settle()
    names = [str(f.get("name") or "") for f in (model.property("filters") or [])]
    j.out["4:filters"] = names
    rows = _rows(model)
    j.out["4:x52-rows"] = [r for r in rows if r["device"] == MODULE_NAME]
    j.out["4:role-names"] = sorted(
        bytes(v).decode() for v in model.roleNames().values()
    )
    j.out["4:texts"] = _texts(j, window.contentItem())


def _x52_health_rows(model: Any) -> list[dict]:  # noqa: ANN401
    return [r for r in _rows(model) if r["device"] == MODULE_NAME]


def _part_remove_two(j: Journey, window: Any, model: Any) -> None:  # noqa: ANN401
    # Not plugged in lists both X52 bindings.
    for c in _checks(model):
        model.setCheck(c["name"], c["name"] == "notPlugged")
    j.wait_until(
        lambda: len({r["input"] for r in _x52_health_rows(model)}) >= 2,
        "both X52 rows",
        timeout=10.0,
    )
    rows = {}
    for r in _x52_health_rows(model):
        rows.setdefault(r["input"], r)
    picked = [rows["Button 1"]["_row"], rows["Button 2"]["_row"]]
    j.out["5:before"] = [_bindings(j, _x52(j), 1), _bindings(j, _x52(j), 2)]
    j.ev(f"pick({picked[0]}); true", window)
    j.ev(f"pick({picked[1]}, Qt.ControlModifier); true", window)
    j.settle()
    j.out["5:picked"] = int(model.property("selectedCount"))
    dialog = j.ev("askRemove()", window)
    assert dialog is not None, "Remove binding… asked nothing"
    j.settle()
    j.out["5:ask"] = str(dialog.property("titleText") or "")
    j.ev("accept(); true", dialog)
    j.wait_until(
        lambda: not _bindings(j, _x52(j), 1) and not _bindings(j, _x52(j), 2),
        "both bindings to go",
        timeout=8.0,
    )
    j.out["5:after"] = [_bindings(j, _x52(j), 1), _bindings(j, _x52(j), 2)]
    j.ev("undo(); true", window)
    j.settle()
    j.out["5:undo"] = [_bindings(j, _x52(j), 1), _bindings(j, _x52(j), 2)]


def story(j: Journey) -> None:
    _profile(j)
    with _Part(j, "1"):
        _part_toolbar(j)
    held: dict = {}
    with _Part(j, "2"):
        held["window"], held["model"] = _part_window(j)
    if held:
        with _Part(j, "3"):
            _part_change(j, held["window"], held["model"])
    with _Part(j, "4"):
        _part_search(j)
    if held:
        with _Part(j, "5"):
            _part_remove_two(j, held["window"], held["model"])


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module()
        import dill

        # Never in the fake driver: not plugged in.
        guid = dill.GUID(dill._GUID(Data1=0xC6EC6FC1, Data2=1, Data3=1, Data4=(6,) * 8))
        j.out["0:x52-guid"] = str(guid.uuid)
        j.input_module(MODULE_NAME, guid=guid, slug="hid_remapper_2dgg")
        j.vjoy_module(1)
        j.vjoy_module(2)

    Journey(before, vjoy_ids=(1, 2)).run(story)


# +-------------------------------------------------------------------------
# | Pytest side


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("health_e2e"))


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


def test_echo_is_saved_and_open_again(run: dict) -> None:
    assert _step(run, "0:loaded") == "Echo.xml"


def test_one_missing_vjoy_binding_is_counted_and_shown_red_on_the_toolbar(
    run: dict,
) -> None:
    assert _step(run, "1:broken") == 1
    button = _step(run, "1:button")
    assert button["visible"] is True, button
    assert button["digits"] == ["1"], button
    assert button["red"] is True, button
    assert button["tooltip"] == "1 binding output not found in this profile", button


def test_health_window_lists_the_binding_with_its_reason(run: dict) -> None:
    checks = _step(run, "2:checks")
    assert [c["label"] for c in checks] == [
        "Binding output not found",
        "Used twice",
        "No bindings",
        "Not plugged in",
    ], checks
    not_found = next(c for c in checks if c["label"] == "Binding output not found")
    assert not_found["count"] == 1 and not_found["checked"] is True, checks
    rows = _step(run, "2:rows")
    assert [(r["device"], r["input"]) for r in rows] == [(MODULE_NAME, "Button 1")], (
        rows
    )
    why = rows[0]["why"]
    assert why, rows
    texts = _step(run, "2:texts")
    assert "Binding output not found (1)" in texts, texts
    assert any(WARN in t for t in texts), "no ⚠ on the row"
    assert any(why in t for t in _step(run, "2:why-texts")), (
        "the Why panel lacks the reason"
    )


def test_change_target_in_health_clears_the_count_and_undo_brings_it_back(
    run: dict,
) -> None:
    assert _step(run, "3:broken") == 0
    assert _step(run, "3:sends") == [[1, 2]]
    button = _step(run, "3:button")
    assert button["digits"] == [] and button["red"] is False, button
    assert button["gray"] is True, button
    assert button["tooltip"] == "No problems found", button
    assert _step(run, "3:broken-undo") == 1
    assert _step(run, "3:sends-undo") == [[3, 1]]
    assert _step(run, "3:button-undo")["digits"] == ["1"]


def test_search_has_no_health_part(run: dict) -> None:
    filters = _step(run, "4:filters")
    for name in ("notFound", "usedTwice", "noBindings", "notPlugged"):
        assert name not in filters, filters
    assert _step(run, "4:x52-rows"), "Search lists no X52 rows"
    roles = _step(run, "4:role-names")
    for role in ("notFound", "notPlugged", "why", "usedTwice"):
        assert role not in roles, roles
    texts = _step(run, "4:texts")
    assert not [t for t in texts if WARN in t], texts
    assert "Not plugged in" not in texts, texts


def test_two_rows_picked_are_removed_together_and_one_undo_restores_both(
    run: dict,
) -> None:
    assert _step(run, "5:before") == [[[3, 1]], [[1, 3]]]
    assert _step(run, "5:picked") == 2
    assert _step(run, "5:ask").startswith("Remove 2 "), run["5:ask"]
    assert _step(run, "5:after") == [[], []]
    assert _step(run, "5:undo") == [[[3, 1]], [[1, 3]]]


def test_no_program_errors(run: dict) -> None:
    assert run.get("_errors") == [], run.get("_errors")
    assert "error" not in run, run.get("traceback")


if __name__ == "__main__":
    main()
