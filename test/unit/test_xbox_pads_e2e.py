# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Xbox Setup's pad count and the Output View's pad sections, end to end on
the real program (D-XBOX-PADS, 2026-10-12).

A journey (test/journeys/_harness.py): the app is built off-screen in its
own process with a temporary USERPROFILE and the fake joystick driver (the
shared RIG). Nothing touches ViGEmBus: the main run fakes it as working (a
fake XboxProxy records every write by pad), the "nodriver" run reports it
missing. Device A is the pJoy Pro, device B the Saitek X52.

Main run:

1. no Map to Xbox binding: the Output View shows the empty line, no pad
   section, and hides the Find bar and the Appearance button;
2. Xbox Setup (Main.openXboxSetup, the window's own SpinBox and OK) raises
   the count 1 -> 2: pad 2 is on, its "Xbox 360 2" output module is there,
   Home still has one Xbox card;
3. A on pad 1 (Button 1 -> A), B on pad 2 (Axis 1 -> Left Stick X) and on
   pad 1 (Button 2 -> B): sections "Xbox 360 1" then "Xbox 360 2", each with
   Driven by, the bound count, chip lines per device and its own list's
   source lines;
4. "Show only bound controls" is ticked the first time and narrows every
   section to its bound controls; Find narrows every section;
5. folding pad 2 is remembered when the page is opened again;
6. lowering the count to 1 asks first and lists B's pad-2 binding; Yes keeps
   the binding, pad 2's section goes, and that action's Map to Xbox editor
   shows the red ⚠ text naming Xbox Setup;
7. a write to pad 2 while the count is 1 is not sent; one to pad 1 is.

"nodriver" run:

8. the Output View shows the one red driver line; its link opens Xbox
   Setup (and the empty line rules of 1 still hold).

Export Device of the Xbox card is not covered here (the harness has no easy
path for exporting an output module).

Each part records its own values (an error in one doesn't hide the others).
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
    RIG,
    Journey,
    run_journey,
    step,
)

EMPTY = (
    "No Xbox controller has a binding yet. Add a Map to Xbox action on Device "
    "Bindings to see it here."
)
DRIVER_LINE = "ViGEmBus driver not found: the Xbox pads can't be sent."
OPEN_SETUP = "Open Xbox Setup"
BOUND_ONLY = "Show only bound controls"

# Writes the fake ViGEm received: [pad, target, value].
WRITES: list[list] = []


# +-------------------------------------------------------------------------
# | Script side (the child process)


class _Part:
    """Runs one part; an error is recorded under the part's name and the
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


class _FakePad:
    def __init__(self, pad: int) -> None:
        self.pad = pad

    def apply(self, target: Any, value: Any) -> None:  # noqa: ANN401
        WRITES.append([self.pad, getattr(target, "value", str(target)), value])

    def user_index(self) -> int:
        return self.pad - 1


class _FakeXboxProxy:
    """ViGEm as if installed: records writes, plugs nothing in."""

    def available(self) -> bool:
        return True

    def __getitem__(self, pad: int) -> _FakePad:
        return _FakePad(int(pad))

    def snapshot(self, pad: int) -> dict:
        return {}


def _xbox(j: Journey, uid: Any, kind: str, number: int, pad: int, target: str) -> None:  # noqa: ANN401
    """A Map to Xbox action on a stick input, in the open profile."""
    from gremlin import plugin_manager
    from gremlin.types import InputType
    from vigem.xbox import XboxTarget

    input_type = InputType.JoystickAxis if kind == "axis" else InputType.JoystickButton
    action = plugin_manager.PluginManager().create_instance("Map to Xbox", input_type)
    action.xbox_device_id = pad
    action.xbox_target = XboxTarget.from_string(target)
    item = j.profile.get_input_item(uid, input_type, number, "Default", True)
    item.add_item_binding().root_action.insert_action(action, "children")


def _actions_edited() -> None:
    from gremlin.signal import signal

    signal.actionsChanged.emit()


def _page(j: Journey) -> Any:  # noqa: ANN401
    from PySide6 import QtQuick

    item = j.ev("_xboxLoader.item")
    return item if isinstance(item, QtQuick.QQuickItem) else None


def _named(root: Any, name: str) -> Any:  # noqa: ANN401
    if root is None:
        return None
    return next((i for i in Journey.walk(root) if i.objectName() == name), None)


def _shown(item: Any) -> bool:  # noqa: ANN401
    if item is None:
        return False
    while item is not None:
        if not item.isVisible():
            return False
        item = item.parentItem()
    return True


def _texts_shown(root: Any) -> list[str]:  # noqa: ANN401
    """Every shown text in the page (labels, buttons, links)."""
    found = []
    for i in Journey.walk(root):
        text = i.property("text")
        if isinstance(text, str) and text and _shown(i):
            found.append(text)
    return found


def _open_page(j: Journey) -> Any:  # noqa: ANN401
    j.ev("Commands.trigger('view.xboxOutput')")
    j.wait_until(lambda: _page(j) is not None, "the Xbox Output View")
    j.settle()
    return _page(j)


def _close_page(j: Journey) -> None:
    j.ev("closeWorkRoomNow()")
    j.settle()
    j.wait_until(lambda: _page(j) is None, "the page closed")


def _sections_model(j: Journey) -> Any:  # noqa: ANN401
    from gremlin.ui.xbox_output_list import (  # pyright: ignore[reportAttributeAccessIssue]
        XboxPadSectionsModel,
    )

    page = _page(j)
    assert page is not None, "the Xbox Output View is not open"
    return j.wait_until(
        lambda: page.findChild(XboxPadSectionsModel), "the page's XboxPadSectionsModel"
    )


def _sections(j: Journey) -> list[dict]:
    return [
        {
            "padId": r.get("padId"),
            "title": r.get("title"),
            "drivenBy": r.get("drivenBy"),
            "boundCount": r.get("boundCount"),
        }
        for r in Journey.catalog_rows(_sections_model(j))
    ]


def _lists(j: Journey) -> dict[int, Any]:
    """Each pad section's XboxOutputListModel, by padId (the page's
    padList)."""
    page = _page(j)
    found: dict[int, Any] = {}
    for pad in range(1, 5):
        model = j.ev(f"padList({pad})", page)
        if model is not None:
            found[pad] = model
    return found


def _list_sources(model: Any) -> dict[str, list[str]]:  # noqa: ANN401
    """Each control's title -> its source lines, where it has any."""
    out: dict[str, list[str]] = {}
    titles = {}
    for row in Journey.catalog_rows(model):
        if row.get("rowKind") == "parent":
            titles[row.get("key")] = str(row.get("title"))
        elif row.get("rowKind") == "child":
            parent = titles.get(row.get("parentKey"), f"? {row.get('parentKey')}")
            out.setdefault(parent, []).append(str(row.get("title")))
    return {k: sorted(v) for k, v in out.items()}


def _parents(model: Any) -> list[str]:  # noqa: ANN401
    return [
        str(r.get("title"))
        for r in Journey.catalog_rows(model)
        if r.get("rowKind") == "parent"
    ]


def _find_box(j: Journey) -> Any:  # noqa: ANN401
    return _named(_page(j), "xboxOutputFind")


def _appearance_button(j: Journey) -> Any:  # noqa: ANN401
    loader = j.ev("_pageBarLoader")
    root = loader.property("item") if loader is not None else None
    return _named(root, "xboxOutputAppearanceButton")


def _xbox_cards(j: Journey) -> list[str]:
    """Home cards for Gremlin's Xbox output."""
    from gremlin.modules.registry import is_gremlin_xbox_name

    j.ev('uiState.setCurrentRoom("status")')
    j.wait_until(lambda: j.ev("uiState.currentRoom") == "status", "Home")
    j.settle()
    names = []
    for it in Journey.walk(j.win.contentItem()):
        if it.metaObject().indexOfSignal("cardFocused()") < 0:
            continue
        name = str(it.property("rawName") or it.property("cardName") or "")
        if is_gremlin_xbox_name(name) or name.startswith("Xbox 360"):
            names.append(name)
    return names


def _setup_window(j: Journey) -> Any:  # noqa: ANN401
    j.ev("openXboxSetup()")
    return j.window("Xbox Setup")


def _setup_set_count(j: Journey, n: int) -> Any:  # noqa: ANN401
    """Opens Xbox Setup, sets the count and presses OK. Returns the window."""
    win = _setup_window(j)
    box = j.item(win, "xboxSetupPadCount")
    assert box is not None, "no xboxSetupPadCount"
    box.setProperty("value", n)
    j.settle()
    j.click(j.item(win, "xboxSetupOk"))
    j.settle()
    return win


def _visible(win: Any) -> bool:  # noqa: ANN401
    """A window that closed may also be gone (deleted on close)."""
    import shiboken6

    return shiboken6.isValid(win) and win.isVisible()


def _question(win: Any) -> Any:  # noqa: ANN401
    import shiboken6
    from PySide6 import QtCore

    for q in win.contentItem().findChildren(QtCore.QObject, "confirmDialog"):
        if shiboken6.isValid(q) and q.property("opened"):
            return q
    return None


def _part_empty(j: Journey, prefix: str) -> None:
    out = j.out
    page = _open_page(j)
    texts = _texts_shown(page)
    out[f"{prefix}:emptyShown"] = _shown(_named(page, "xboxOutputEmpty"))
    out[f"{prefix}:emptyText"] = EMPTY in texts
    out[f"{prefix}:sections"] = _sections(j)
    out[f"{prefix}:findShown"] = _shown(_find_box(j))
    out[f"{prefix}:findExists"] = _find_box(j) is not None
    out[f"{prefix}:appearanceShown"] = _shown(_appearance_button(j))
    out[f"{prefix}:driverLine"] = _shown(_named(page, "xboxDriverMissing"))
    out[f"{prefix}:driverText"] = DRIVER_LINE in texts
    out[f"{prefix}:openSetupLink"] = any(OPEN_SETUP in t for t in texts)


def _part_count_up(j: Journey) -> None:
    from gremlin.modules import output, registry

    out = j.out
    out["up:before"] = [output.xbox_pad_count(), output.xbox_pads_on()]
    out["up:cardsBefore"] = _xbox_cards(j)
    win = _setup_set_count(j, 2)
    out["up:closed"] = j.await_value(lambda: _visible(win), False)
    out["up:after"] = j.await_value(
        lambda: [output.xbox_pad_count(), output.xbox_pads_on()], [2, [1, 2]]
    )
    out["up:modules"] = sorted(output.xbox_modules())
    out["up:moduleName2"] = getattr(output.xbox_module(2), "name", None)
    out["up:registry"] = sorted(
        m.name for m in registry.outputs() if output.is_xbox_module(m.name)
    )
    out["up:cardsAfter"] = _xbox_cards(j)


def _part_sections(j: Journey) -> None:
    from gremlin.ui.input_pairing import device_label

    out = j.out
    pjoy = str(j.stick("pJoy Pro").device_guid.uuid)
    x52 = str(j.stick("Saitek X52").device_guid.uuid)
    a, b = device_label(pjoy), device_label(x52)
    out["sec:names"] = [a, b]
    _open_page(j)
    out["sec:rows"] = j.await_value(
        lambda: [r["title"] for r in _sections(j)], ["Xbox 360 1", "Xbox 360 2"]
    )
    out["sec:all"] = _sections(j)
    page = _page(j)
    texts = _texts_shown(page)
    out["sec:titlesShown"] = [t for t in ("Xbox 360 1", "Xbox 360 2") if t in texts]
    out["sec:emptyShown"] = _shown(_named(page, "xboxOutputEmpty"))
    out["sec:sectionsShown"] = [
        n for n in (1, 2) if _shown(_named(page, f"xboxPadSection{n}"))
    ]
    out["sec:headings"] = {
        n: " / ".join(_texts_shown(_named(page, f"xboxPadHeading{n}")))
        if _named(page, f"xboxPadHeading{n}") is not None
        else None
        for n in (1, 2)
    }
    out["sec:findShown"] = _shown(_find_box(j))
    out["sec:appearanceShown"] = _shown(_appearance_button(j))
    out["sec:mappedHeadings"] = sum(
        1 for t in texts if t in ("Mapped axes", "Mapped buttons")
    )
    # One chip line per device driving a pad ("<device>  [1 | A] [3 | B]").
    for n in (1, 2):
        for kind in ("Axis", "Button"):
            out[f"sec:chips{kind}{n}"] = sorted(
                [
                    str(i.property("deviceName")),
                    sorted(
                        f"{c.property('hwLabel')} | {c.property('xbLabel')}"
                        for c in Journey.walk(i)
                        if c.objectName() == "xboxChip"
                    ),
                ]
                for i in Journey.walk(page)
                if i.objectName() == f"xbox{kind}Line{n}" and _shown(i)
            )
    out["sec:faces"] = [
        n for n in (1, 2) if _shown(_named(page, f"xboxPadFace{n}"))
    ]
    lists = _lists(j)
    out["sec:listPads"] = sorted(lists)
    out["sec:sources1"] = _list_sources(lists[1]) if 1 in lists else None
    out["sec:sources2"] = _list_sources(lists[2]) if 2 in lists else None
    out["sec:expect1"] = {
        "A": [f"{a} · Button 1"],
        "B": [f"{b} · Button 2"],
    }
    out["sec:expect2"] = {"Left Stick X": [f"{b} · Axis 1"]}


def _part_find(j: Journey) -> None:
    out = j.out
    lists = _lists(j)
    box = _find_box(j)
    assert box is not None, "no xboxOutputFind box"
    bar = _named(_page(j), "xboxOutputFindBar")
    out["find:boundOnly"] = {pad: _parents(m) for pad, m in sorted(lists.items())}
    # Untick it for the text checks: every control again.
    tick = next(
        (i for i in Journey.walk(bar) if i.property("text") == BOUND_ONLY),
        None,
    )
    assert tick is not None, f"no {BOUND_ONLY!r} tick"
    j.ev("checked = false; clicked(); true", tick)
    j.settle()
    out["find:unticked"] = {pad: len(_parents(m)) for pad, m in sorted(lists.items())}
    box.setProperty("text", "Left Stick")
    j.settle()
    out["find:text"] = {pad: _parents(m) for pad, m in sorted(lists.items())}
    box.setProperty("text", "Saitek")
    j.settle()
    out["find:source"] = {pad: _parents(m) for pad, m in sorted(lists.items())}
    box.setProperty("text", "")
    j.settle()
    out["find:cleared"] = {pad: len(_parents(m)) for pad, m in sorted(lists.items())}


def _pad_open(j: Journey, pad: int) -> Any:  # noqa: ANN401
    return j.ev(f"isPadOpen({pad})", _page(j))


def _part_fold(j: Journey) -> None:
    from gremlin.ui import window_placement

    out = j.out
    out["fold:before"] = [_pad_open(j, 1), _pad_open(j, 2)]
    j.ev("setPadOpen(2, false); true", _page(j))
    j.settle()
    out["fold:after"] = [_pad_open(j, 1), _pad_open(j, 2)]
    out["fold:stored"] = window_placement.tool_row_state("xboxOutput")
    _close_page(j)
    _open_page(j)
    _sections_model(j)
    out["fold:reopened"] = [_pad_open(j, 1), _pad_open(j, 2)]
    j.ev("setPadOpen(2, true); true", _page(j))
    j.settle()


def _part_count_down(j: Journey) -> None:
    from gremlin.modules import output
    from gremlin.ui.input_pairing import device_label

    out = j.out
    x52_uid = j.stick("Saitek X52").device_guid.uuid
    b = device_label(str(x52_uid))
    # The input as Device Bindings names it (the hardware's axis name).
    out["down:expectLines"] = [
        f"{b} · {name} → Xbox 360 2 · Left Stick X (Default)"
        for name in ("X Axis", "Axis 1")
    ]
    win = _setup_set_count(j, 1)
    q = j.wait_until(lambda: _question(win), "the lowering question")
    out["down:countWhileAsking"] = output.xbox_pad_count()
    out["down:questionText"] = str(q.property("bodyText") or "")
    out["down:actionText"] = str(q.property("actionText") or "")
    yes = q.findChild(__import__("PySide6.QtQuick").QtQuick.QQuickItem, "confirmAction")
    assert yes is not None, "no confirmAction button"
    j.click(yes)
    j.settle()
    out["down:after"] = j.await_value(
        lambda: [output.xbox_pad_count(), output.xbox_pads_on()], [1, [1]]
    )
    out["down:modules"] = sorted(output.xbox_modules())
    # The binding is kept.
    out["down:kept"] = output.xbox_bindings_on_pads([2])
    # Pad 2's section goes from the open page.
    _open_page(j)
    out["down:sections"] = j.await_value(
        lambda: [r["title"] for r in _sections(j)], ["Xbox 360 1"]
    )
    out["down:cardsAfter"] = _xbox_cards(j)
    # The action's own Map to Xbox editor: the red ⚠ text and its pad list.
    catalog = j.open_device_bindings("saitek_x52")
    j.open_input(catalog, "axis", 1)
    actions = j.wait_until(
        lambda: [a for a in j.pane_actions(catalog) if a is not None][1:],
        "the Map to Xbox editor",
    )
    editor = next(
        (a for a in actions if a.metaObject().indexOfProperty("cantSendText") >= 0),
        None,
    )
    assert editor is not None, "no Map to Xbox editor model in the pane"
    out["down:cantSend"] = str(editor.property("cantSendText") or "")
    out["down:padChoices"] = [
        int(c["value"]) for c in (editor.property("padChoices") or [])
    ]
    out["down:padLabel"] = str(editor.property("padLabel") or "")


def _part_write(j: Journey) -> None:
    from gremlin.modules import output
    from vigem.xbox import XboxTarget

    out = j.out
    # As during a Run (nothing is sent while stopped).
    output._sending = lambda: True  # type: ignore[assignment]
    WRITES.clear()
    out["write:pad2"] = output.write_xbox(2, XboxTarget.from_string("a"), True)
    out["write:pad1"] = output.write_xbox(1, XboxTarget.from_string("a"), True)
    out["write:recorded"] = list(WRITES)


def _part_driver_missing(j: Journey) -> None:
    out = j.out
    page = _page(j) or _open_page(j)
    out["drv:lineShown"] = _shown(_named(page, "xboxDriverMissing"))
    link = _named(page, "xboxOpenSetupLink")
    assert link is not None, "no xboxOpenSetupLink"
    out["drv:linkText"] = str(link.property("text") or "")
    if link.metaObject().indexOfSignal("clicked()") >= 0:
        j.click(link)
    else:  # a Text link: what its onLinkActivated / tap sends
        j.ev("xboxSetupRequested(); true", page)
        out["drv:linkNotClickable"] = True
    win = j.window("Xbox Setup")
    out["drv:setupOpened"] = win.isVisible()
    out["drv:setupCount"] = j.item(win, "xboxSetupPadCount").property("value")
    win.close()
    j.settle()


def story(j: Journey) -> None:
    with _Part(j, "empty"):
        _part_empty(j, "empty")
    with _Part(j, "up"):
        _part_count_up(j)
    pjoy = j.stick("pJoy Pro").device_guid.uuid
    x52 = j.stick("Saitek X52").device_guid.uuid
    _xbox(j, pjoy, "button", 1, 1, "a")
    _xbox(j, x52, "axis", 1, 2, "left_stick_x")
    _xbox(j, x52, "button", 2, 1, "b")
    _actions_edited()
    j.settle()
    for name, part in (
        ("sec", _part_sections),
        ("find", _part_find),
        ("fold", _part_fold),
        ("down", _part_count_down),
        ("write", _part_write),
    ):
        with _Part(j, name):
            part(j)


def nodriver_story(j: Journey) -> None:
    with _Part(j, "nd"):
        _part_empty(j, "nd")
    with _Part(j, "drv"):
        _part_driver_missing(j)


def _modules(j: Journey) -> None:
    import dill

    x52 = next(
        dill.GUID(d.device_guid) for d in j.dill_fake.devices if d.name == b"Saitek X52"
    )
    j.input_module()
    j.input_module("Saitek X52", guid=x52)


def main() -> None:
    if "nodriver" in sys.argv[1:]:

        def missing(j: Journey) -> None:
            from gremlin.modules import output

            _modules(j)
            output.xbox_driver_installed = lambda: False
            output.xbox_driver_version = lambda: ""
            output.xbox_available = lambda: False
            output.xbox_error = lambda: ""

        Journey(missing, **RIG).run(nodriver_story)
        return

    def faked(j: Journey) -> None:
        from gremlin.modules import output
        from vigem import xbox

        _modules(j)
        proxy = _FakeXboxProxy()
        xbox.XboxProxy = lambda: proxy  # type: ignore[assignment,misc]
        output.xbox_driver_installed = lambda: True
        output.xbox_driver_version = lambda: "1.22.0.0"
        output.xbox_available = lambda: True
        output.xbox_error = lambda: ""

    Journey(faked, **RIG).run(story)


# +-------------------------------------------------------------------------
# | Pytest side


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("xbox_pads"))


@pytest.fixture(scope="module")
def nodriver(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("xbox_nodriver"), "nodriver")


def _no_error(run: dict, part: str) -> None:
    assert f"{part}:error" not in run, (
        run.get(f"{part}:error"),
        run.get(f"{part}:traceback"),
    )


def test_no_binding_shows_the_empty_line_only(run: dict) -> None:
    _no_error(run, "empty")
    assert step(run, "empty:emptyShown") is True
    assert step(run, "empty:emptyText") is True
    assert step(run, "empty:sections") == []
    assert step(run, "empty:findShown") is False
    assert step(run, "empty:appearanceShown") is False
    assert step(run, "empty:driverLine") is False  # the driver is found


def test_xbox_setup_raises_the_count_with_one_home_card(run: dict) -> None:
    _no_error(run, "up")
    assert step(run, "up:before") == [1, [1]]
    assert step(run, "up:closed") is False
    assert step(run, "up:after") == [2, [1, 2]]
    # Pad 1 needs no module of its own (always on); pad 2's is made.
    assert 2 in step(run, "up:modules")
    assert step(run, "up:moduleName2") == "Xbox 360 2"
    assert "Xbox 360 2" in step(run, "up:registry")
    assert len(step(run, "up:cardsBefore")) == 1, step(run, "up:cardsBefore")
    assert len(step(run, "up:cardsAfter")) == 1, step(run, "up:cardsAfter")


def test_one_section_per_pad_on_and_bound_in_order(run: dict) -> None:
    _no_error(run, "sec")
    a, b = step(run, "sec:names")
    assert step(run, "sec:rows") == ["Xbox 360 1", "Xbox 360 2"]
    pads = step(run, "sec:all")
    assert [p["padId"] for p in pads] == [1, 2]
    assert a in str(pads[0]["drivenBy"]) and b in str(pads[0]["drivenBy"])
    assert b in str(pads[1]["drivenBy"]) and a not in str(pads[1]["drivenBy"])
    assert [p["boundCount"] for p in pads] == [2, 1]
    assert step(run, "sec:titlesShown") == ["Xbox 360 1", "Xbox 360 2"]
    assert step(run, "sec:emptyShown") is False
    assert step(run, "sec:sectionsShown") == [1, 2]
    headings = step(run, "sec:headings")
    for pad, count in (("1", "2 controls bound"), ("2", "1 control")):
        words = str(headings[pad])
        assert f"Xbox 360 {pad}" in words, headings
        assert "Driven by: " in words and count in words, headings
    assert step(run, "sec:findShown") is True
    assert step(run, "sec:appearanceShown") is True
    assert step(run, "sec:faces") == [1, 2]
    assert step(run, "sec:mappedHeadings") >= 2


def test_each_section_has_chip_lines_per_device(run: dict) -> None:
    _no_error(run, "sec")
    a, b = step(run, "sec:names")
    # Pad 1: A (Button 1 -> A) and B (Button 2 -> B); pad 2: B (Axis 1 ->
    # Left Stick X).
    buttons1 = step(run, "sec:chipsButton1")
    assert [line[0] for line in buttons1] == sorted([a, b]), buttons1
    assert all(len(line[1]) == 1 for line in buttons1), buttons1
    assert step(run, "sec:chipsAxis1") == []
    axes2 = step(run, "sec:chipsAxis2")
    assert [line[0] for line in axes2] == [b], axes2
    assert len(axes2[0][1]) == 1, axes2
    assert step(run, "sec:chipsButton2") == []


def test_each_pad_list_shows_its_own_sources(run: dict) -> None:
    _no_error(run, "sec")
    assert step(run, "sec:listPads") == [1, 2]
    assert step(run, "sec:sources1") == step(run, "sec:expect1")
    assert step(run, "sec:sources2") == step(run, "sec:expect2")


def test_find_narrows_every_section(run: dict) -> None:
    _no_error(run, "find")
    assert step(run, "find:boundOnly") == {"1": ["A", "B"], "2": ["Left Stick X"]}
    assert step(run, "find:unticked") == {"1": 22, "2": 22}
    text = step(run, "find:text")
    assert text == {
        "1": ["Left Stick X", "Left Stick Y"],
        "2": ["Left Stick X", "Left Stick Y"],
    }, text
    source = step(run, "find:source")
    assert source == {"1": ["B"], "2": ["Left Stick X"]}, source
    assert step(run, "find:cleared") == {"1": 22, "2": 22}


def test_folding_pad_2_is_remembered(run: dict) -> None:
    _no_error(run, "fold")
    assert step(run, "fold:before") == [True, True]
    assert step(run, "fold:after") == [True, False]
    stored = step(run, "fold:stored")
    assert stored.get("open", {}).get("2") is False, stored
    assert step(run, "fold:reopened") == [True, False]


def test_lowering_asks_keeps_the_binding_and_warns(run: dict) -> None:
    _no_error(run, "down")
    assert step(run, "down:countWhileAsking") == 2
    lines = step(run, "down:expectLines")
    text = step(run, "down:questionText")
    assert any(line in text for line in lines), (lines, text)
    assert step(run, "down:actionText") == "Yes"
    assert step(run, "down:after") == [1, [1]]
    assert 2 not in step(run, "down:modules")
    kept = step(run, "down:kept")
    assert len(kept) == 1 and kept[0] in lines, kept
    assert kept[0] in text  # the question lists what is kept
    assert step(run, "down:sections") == ["Xbox 360 1"]
    assert len(step(run, "down:cardsAfter")) == 1
    assert "Xbox Setup" in step(run, "down:cantSend"), step(run, "down:cantSend")
    assert step(run, "down:padChoices") == [1, 2]


def test_a_pad_outside_the_count_is_not_sent(run: dict) -> None:
    _no_error(run, "write")
    assert step(run, "write:pad2") is False
    assert step(run, "write:pad1") is True
    recorded = step(run, "write:recorded")
    assert [w[0] for w in recorded] == [1], recorded


def test_no_program_errors(run: dict) -> None:
    assert run.get("error") is None, (run.get("error"), run.get("traceback"))
    assert run.get("_errors") == []


def test_driver_missing_shows_one_red_line(nodriver: dict) -> None:
    _no_error(nodriver, "nd")
    assert step(nodriver, "nd:driverLine") is True
    assert step(nodriver, "nd:driverText") is True
    assert step(nodriver, "nd:openSetupLink") is True
    assert step(nodriver, "nd:emptyShown") is True
    assert step(nodriver, "nd:findShown") is False
    assert step(nodriver, "nd:appearanceShown") is False


def test_driver_line_link_opens_xbox_setup(nodriver: dict) -> None:
    _no_error(nodriver, "drv")
    assert step(nodriver, "drv:lineShown") is True
    assert OPEN_SETUP in step(nodriver, "drv:linkText")
    assert step(nodriver, "drv:setupOpened") is True
    assert step(nodriver, "drv:setupCount") == 1


def test_no_program_errors_without_the_driver(nodriver: dict) -> None:
    assert nodriver.get("error") is None, (
        nodriver.get("error"),
        nodriver.get("traceback"),
    )
    assert nodriver.get("_errors") == []


if __name__ == "__main__":
    main()
