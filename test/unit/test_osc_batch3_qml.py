# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC batch 3 on the real OSC page, its windows and OSC Setup, end to end
off-screen.

A journey (test/journeys/_harness.py): the app runs in its own process with
a temporary USERPROFILE, the fake joystick driver and a fake vJoy; no socket
is opened. The story drives the page's own QML as a user would:

1. An axis input's row has an Invert check box (Logical's writer-row
   Invert); a button's row has none; a click writes Invert to OSC's list as
   one Undo step (S161).
2. Edit Settings… on an axis input shows Shaping (Deadzone low / high); a
   bad value is refused in the window; OK writes the deadzone. On two axis
   inputs with different deadzones the boxes start blank ("Differs"). An
   encoder shows Acceleration next to Step size; Medium is written (S164).
3. The page menu's Add Inputs has "From TouchOSC Layout…"; Import reads a
   .tosc file into a preview list with check boxes (an input already in the
   list greyed); only the ticked rows are added and the page shows the
   added/skipped report (S162).
4. OSC Setup's Server tab has "Allowed senders": empty says everyone is
   accepted; Add writes a range to OSC's file; a bad entry is refused;
   Remove asks first and empties the list (S160).
5. The OSC Monitor shows a blocked message with Input "blocked"; its row
   menu's "Allow this sender" puts the host on the allow-list (S160).

Spec: 09 S160-S162, S164.
"""

from __future__ import annotations

import pathlib
import sys
import traceback
import zlib
from typing import Any

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test" / "journeys"))
from _harness import Journey, JourneyIncomplete, run_journey  # noqa: E402

BLOCKED_HOST = "10.0.0.9"


# +-------------------------------------------------------------------------
# | Script side (the child process)


class _Part:
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


def _rows(model: Any) -> list[dict]:  # noqa: ANN401
    names = {int(k): bytes(v).decode() for k, v in model.roleNames().items()}
    out = []
    for r in range(model.rowCount()):
        index = model.index(r, 0)
        row = {}
        for role, name in names.items():
            value = model.data(index, role)
            plain = isinstance(value, (str, int, float, bool, type(None)))
            row[name] = value if plain else str(value)
        out.append(row)
    return out


def _osc_row(address: str) -> Any:  # noqa: ANN401
    from gremlin.osc import OscDevice

    for row in OscDevice().rows.rows():
        if row.label == address:
            return row
    return None


def _top(j: Journey, window: Any = None) -> Any:  # noqa: ANN401
    root = (window or j.win).contentItem()
    while root.parentItem() is not None:
        root = root.parentItem()
    return root


def _visible(j: Journey, root: Any, name: str) -> list:  # noqa: ANN401
    return [i for i in j.walk(root) if i.objectName() == name and i.isVisible()]


def _one(j: Journey, name: str, window: Any = None) -> Any:  # noqa: ANN401
    found = _visible(j, _top(j, window), name)
    return found[0] if found else None


def _mouse(j: Journey, item: Any, right: bool = False, window: Any = None) -> None:  # noqa: ANN401
    from PySide6 import QtCore

    p = item.mapToScene(QtCore.QPointF(min(40.0, item.width() / 2), item.height() / 2))
    button = (
        QtCore.Qt.MouseButton.RightButton if right else QtCore.Qt.MouseButton.LeftButton
    )
    j.QTest.mouseClick(
        window or j.win, button, QtCore.Qt.KeyboardModifier.NoModifier, p.toPoint()
    )
    j.settle()


def _type(j: Journey, field: Any, text: str, window: Any = None) -> None:  # noqa: ANN401
    from PySide6 import QtCore

    win = window or j.win
    field.forceActiveFocus()
    QtCore.QMetaObject.invokeMethod(field, "selectAll")
    j.QTest.keyClick(win, QtCore.Qt.Key.Key_Delete)
    for char in text:
        j.QTest.keyClick(win, char)
    j.settle()


def _page(j: Journey) -> Any:  # noqa: ANN401
    for item in j.walk(j.win.contentItem()):
        if item.metaObject().className().startswith("OscPage") and item.isVisible():
            return item
    return None


def _open_page(j: Journey) -> tuple[Any, Any]:  # noqa: ANN401
    from gremlin.ui.osc_layout import OscLayoutModel

    j.ev('openConfigurationForCard(_moduleModel.cardMap("osc"))')
    j.wait_until(lambda: j.backend.uiState.currentTab == "osc", "the OSC page")
    layout = j.wait_until(lambda: j.win.findChild(OscLayoutModel), "the layout model")
    page = j.wait_until(lambda: _page(j), "the OscPage item")
    return page, layout


def _setup(j: Journey, page: Any) -> None:  # noqa: ANN401
    for settings in (
        '{address: "/fader/1", mode: "axis"}',
        '{address: "/fader/2", mode: "axis", deadzone_low: -0.2, deadzone_high: 0.2}',
        '{address: "/deck/1", mode: "button"}',
        '{address: "/enc/1", mode: "encoder", enc_output: "axis"}',
    ):
        j.ev("_devices.createConfiguredInput(%s); true" % settings, page)
    j.settle()


def _key_of(layout: Any, address: str) -> str:  # noqa: ANN401
    for row in _rows(layout):
        if row["rowKind"] == "parent" and address in str(row["title"]) + str(
            row["systemName"]
        ):
            return row["key"]
    return ""


def _part_invert(j: Journey, page: Any, layout: Any) -> None:  # noqa: ANN401
    out = j.out
    boxes = _visible(j, page, "oscRowInvert")
    # Axis inputs: /fader/1, /fader/2 and the encoder's axis output.
    out["1:boxes"] = len(boxes)
    fader = _key_of(layout, "/fader/1")

    def box_of_fader() -> Any:  # noqa: ANN401
        # Rows are made again when the model changes: find the box afresh.
        return next(
            b
            for b in _visible(j, page, "oscRowInvert")
            if j.ev("rowModel.key", b.parentItem()) == fader
        )

    box = box_of_fader()
    out["1:box-text"] = box.property("text")
    _mouse(j, box)
    row = _osc_row("/fader/1")
    out["1:box-checked"] = box_of_fader().property("checked")
    out["1:file-invert"] = bool(row and row.invert)
    out["1:can-undo"] = j.ev("_layout.canUndo", page)
    j.ev("_layout.undo(); true", page)
    j.settle()
    out["1:invert-after-undo"] = bool(_osc_row("/fader/1").invert)
    _mouse(j, box_of_fader())
    out["1:invert-again"] = bool(_osc_row("/fader/1").invert)


def _part_settings(j: Journey, page: Any, layout: Any) -> None:  # noqa: ANN401
    out = j.out
    fader = _key_of(layout, "/fader/1")
    fader2 = _key_of(layout, "/fader/2")
    enc = _key_of(layout, "/enc/1")
    deck = _key_of(layout, "/deck/1")
    # One axis input.
    j.ev('editSettings(["%s"]); true' % fader, page)
    j.settle()
    out["2:shaping-shown"] = _one(j, "oscShapingSection") is not None
    low, high = _one(j, "oscDeadzoneLow"), _one(j, "oscDeadzoneHigh")
    _type(j, low, "-2")
    out["2:bad-error"] = str(_one(j, "oscDeadzoneError").property("text"))
    out["2:bad-ok"] = _one(j, "oscOk").property("enabled")
    _type(j, low, "-0.1")
    _type(j, high, "0.15")
    j.click(_one(j, "oscOk"))
    j.settle()
    out["2:deadzone"] = list(_osc_row("/fader/1").deadzone)
    # A button: no Shaping.
    j.ev('editSettings(["%s"]); true' % deck, page)
    j.settle()
    out["2:button-shaping"] = _one(j, "oscShapingSection") is not None
    j.ev("_addDialog.close(); true", page)
    j.settle()
    # Two axis inputs whose deadzones differ: blank, "Differs".
    j.ev('editSettings(["%s", "%s"]); true' % (fader, fader2), page)
    j.settle()
    out["2:many-shaping"] = _one(j, "oscShapingSection") is not None
    low = _one(j, "oscDeadzoneLow")
    out["2:many-low"] = [low.property("text"), low.property("placeholderText")]
    j.ev("_addDialog.close(); true", page)
    j.settle()
    # The encoder: Acceleration next to Step size.
    j.ev('editSettings(["%s"]); true' % enc, page)
    j.settle()
    accel = _one(j, "oscEncAccel")
    out["2:accel-shown"] = accel is not None and _one(j, "oscEncStep") is not None
    out["2:accel-start"] = accel.property("currentText") if accel else None
    j.ev("currentIndex = 2; activated(2); true", accel)
    j.click(_one(j, "oscOk"))
    j.settle()
    out["2:enc-accel"] = _osc_row("/enc/1").enc_accel


def _partial(kind: str, value: str, low: float = 0.0, high: float = 1.0) -> str:
    return (
        f"<partial><type>{kind}</type><conversion>STRING</conversion>"
        f"<value>{value}</value><scaleMin>{low}</scaleMin>"
        f"<scaleMax>{high}</scaleMax></partial>"
    )


def _node(kind: str, name: str, children: str = "") -> str:
    osc = ""
    if kind != "GROUP":
        osc = (
            "<osc><enabled>1</enabled><send>1</send><receive>1</receive><path>"
            + _partial("CONSTANT", "/")
            + _partial("PROPERTY", "name")
            + "</path><arguments>"
            + _partial("VALUE", "x")
            + "</arguments></osc>"
        )
    return (
        f'<node ID="id-{name}" type="{kind}"><properties>'
        f'<property type="s"><key>name</key><value>{name}</value></property>'
        f"</properties><values/><messages>{osc}</messages>"
        f"<children>{children}</children></node>"
    )


def write_tosc(folder: pathlib.Path) -> pathlib.Path:
    """A small TouchOSC layout: two faders, a button already in the list,
    a new button and a label."""
    body = _node(
        "GROUP",
        "root",
        _node("FADER", "volume")
        + _node("FADER", "pan")
        + _node("BUTTON", "deck")
        + _node("BUTTON", "mute")
        + _node("LABEL", "title"),
    )
    xml = f'<?xml version="1.0" encoding="UTF-8"?><lexml version="3">{body}</lexml>'
    path = folder / "board.tosc"
    path.write_bytes(zlib.compress(xml.encode("utf-8")))
    return path


def _part_touchosc(j: Journey, page: Any) -> None:  # noqa: ANN401
    import json
    import os

    out = j.out
    menu = json.loads(
        j.ev(
            "_menuOnRow = false; _menuOnGroup = false;"
            " (function(m) { var s = {};"
            " m.sections.forEach(function(x) {"
            " s[x.title] = x.items.map(function(r) { return r.text }) });"
            " return JSON.stringify(s) })(_layoutMenuModel())",
            page,
        )
    )
    out["3:add-section"] = menu.get("Add Inputs", [])
    j.ev(
        "_devices.createConfiguredInput({address: '/deck', mode: 'button'}); true", page
    )
    path = write_tosc(pathlib.Path(os.environ["USERPROFILE"]))
    j.ev("openImport(); true", page)
    j.settle()
    out["3:file-button"] = _one(j, "oscImportFile") is not None
    loaded = j.ev("_importDialog.loadFile(%s)" % json.dumps(path.as_uri()), page)
    j.settle()
    out["3:loaded"] = loaded
    rows = j.ev("_importDialog.toscRows", page) or []
    out["3:preview"] = [[r["address"], r["kindText"], r["exists"]] for r in rows]
    j.wait_until(
        lambda: all(_one(j, f"oscToscTick{i}") for i in range(len(rows))),
        "the preview rows",
        5,
    )
    ticks = [_one(j, f"oscToscTick{i}") for i in range(len(rows))]
    out["3:ticks"] = [
        None if t is None else [t.property("checked"), t.property("enabled")]
        for t in ticks
    ]
    out["3:skipped-line"] = bool(_one(j, "oscToscSkipped"))
    # Untick "pan", then add.
    pan = next(i for i, r in enumerate(rows) if r["address"] == "/pan")
    _mouse(j, ticks[pan])
    out["3:ok-text"] = _one(j, "oscImportOk").property("text")
    j.click(_one(j, "oscImportOk"))
    j.settle()
    out["3:added"] = sorted(
        a for a in ("/volume", "/pan", "/mute") if _osc_row(a) is not None
    )
    out["3:message"] = j.ev("_message.text", page)


def _setup_window(j: Journey) -> Any:  # noqa: ANN401
    from PySide6 import QtQuick

    from gremlin.modules import ids

    j.ev(
        '_root.openConfigureModule("source", _root._cardForGuid("%s"))'
        % str(ids.OSC).upper()
    )

    def find() -> Any:  # noqa: ANN401
        for w in j.app.topLevelWindows():
            if (
                w is not j.win
                and w.isVisible()
                and isinstance(w, QtQuick.QQuickWindow)
                and _one(j, "oscServerSection", w) is not None
            ):
                return w
        return None

    return j.wait_until(find, "OSC Setup", 10)


def _part_senders(j: Journey) -> None:  # noqa: ANN401
    from gremlin import osc_device_file

    out = j.out
    w = _setup_window(j)
    out["4:card"] = _one(j, "oscAllowedSenders", w) is not None
    empty = _one(j, "oscSendersEmpty", w)
    out["4:empty-text"] = None if empty is None else empty.property("text")
    field = _one(j, "oscSenderField", w)
    _type(j, field, "not an address", w)
    j.click(_one(j, "oscSenderAdd", w))
    j.settle()
    out["4:bad"] = list(osc_device_file.read_server()["allow_senders"])
    _type(j, field, "192.168.1.0/24", w)
    j.click(_one(j, "oscSenderAdd", w))
    j.settle()
    out["4:added"] = list(osc_device_file.read_server()["allow_senders"])
    out["4:row-text"] = _one(j, "oscSenderText0", w).property("text")
    out["4:empty-gone"] = _one(j, "oscSendersEmpty", w) is None
    j.click(_one(j, "oscSenderRemove0", w))
    confirm = j.wait_until(lambda: _one(j, "confirmAction", w), "the question", 5)
    out["4:asked"] = list(osc_device_file.read_server()["allow_senders"])
    j.click(confirm)
    j.settle()
    out["4:removed"] = list(osc_device_file.read_server()["allow_senders"])
    w.close()
    j.settle()


def _part_monitor(j: Journey, page: Any) -> None:  # noqa: ANN401
    from gremlin import osc_device_file, osc_traffic

    out = j.out
    j.ev("showMonitor(); true", page)
    j.settle()
    j.wait_until(lambda: j.ev("_monitor.holdsPort", page), "the Monitor open", 5)
    osc_traffic.note("in", "/blocked/1", [1], (BLOCKED_HOST, 5000), ["blocked"])
    cell = j.wait_until(lambda: _one(j, "oscMonitorInput0"), "the blocked row", 5)
    out["5:input"] = cell.property("text")
    out["5:add-hidden"] = _one(j, "oscMonitorAddRow0") is None
    _mouse(j, cell, right=True)
    out["5:menu-host"] = j.ev("_monitor._menuHost", page)
    out["5:menu-open"] = j.await_value(
        lambda: j.ev("_monitor.rowMenu.opened", page), True
    )
    texts = j.ev(
        "_monitor.rowMenu.model.quick.map(function(r) { return r.text })", page
    )
    out["5:menu"] = list(texts or [])
    j.ev(
        "_monitor.rowMenu.model.quick.filter(function(r) {"
        " return r.text === 'Allow this sender' })[0].run(); true",
        page,
    )
    j.settle()
    out["5:allowed"] = list(osc_device_file.read_server()["allow_senders"])


def story(j: Journey) -> None:
    j.win.setWidth(1600)
    j.win.setHeight(950)
    page, layout = _open_page(j)
    _setup(j, page)
    with _Part(j, "1"):
        _part_invert(j, page, layout)
    with _Part(j, "2"):
        _part_settings(j, page, layout)
    with _Part(j, "3"):
        _part_touchosc(j, page)
    with _Part(j, "4"):
        _part_senders(j)
    with _Part(j, "5"):
        _part_monitor(j, page)


def before(j: Journey) -> None:
    import gremlin.osc as gosc

    # No socket: the page and the Monitor work without the OSC listener.
    gosc.OscRuntime._bind = lambda self: None
    gosc.OscRuntime.hold_open = lambda self, token: True
    gosc.OscRuntime.release_open = lambda self, token: None
    j.input_module()
    j.vjoy_module()


def main() -> None:
    Journey(before).run(story)


# +-------------------------------------------------------------------------
# | Pytest side


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("osc_batch3_qml"))


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


def test_axis_rows_have_an_invert_box_that_writes_one_undo_step(run: dict) -> None:
    assert _step(run, "1:boxes") == 3
    assert _step(run, "1:box-text") == "Invert"
    assert _step(run, "1:file-invert") is True
    assert _step(run, "1:box-checked") is True
    assert _step(run, "1:can-undo") is True
    assert _step(run, "1:invert-after-undo") is False
    assert _step(run, "1:invert-again") is True


def test_edit_settings_shows_shaping_for_axis_inputs(run: dict) -> None:
    assert _step(run, "2:shaping-shown") is True
    assert "-0.99" in _step(run, "2:bad-error")
    assert _step(run, "2:bad-ok") is False
    assert _step(run, "2:deadzone") == pytest.approx([-0.1, 0.15])
    assert _step(run, "2:button-shaping") is False


def test_several_inputs_with_different_deadzones_start_blank(run: dict) -> None:
    assert _step(run, "2:many-shaping") is True
    assert _step(run, "2:many-low") == ["", "Differs"]


def test_encoder_offers_acceleration_next_to_step_size(run: dict) -> None:
    assert _step(run, "2:accel-shown") is True
    assert _step(run, "2:accel-start") == "Off"
    assert _step(run, "2:enc-accel") == "medium"


def test_touchosc_layout_is_previewed_and_only_ticked_rows_added(run: dict) -> None:
    assert "From TouchOSC Layout…" in _step(run, "3:add-section")
    assert _step(run, "3:file-button") is True
    assert _step(run, "3:loaded") is True
    assert _step(run, "3:preview") == [
        ["/volume", "Axis", False],
        ["/pan", "Axis", False],
        ["/deck", "Button", True],
        ["/mute", "Button", False],
    ]
    assert _step(run, "3:ticks") == [
        [True, True],
        [True, True],
        [False, False],
        [True, True],
    ]
    assert _step(run, "3:skipped-line") is True
    assert _step(run, "3:ok-text") == "Add 2 Inputs"
    assert _step(run, "3:added") == ["/mute", "/volume"]
    assert "Added 2" in _step(run, "3:message")


def test_server_tab_lists_allowed_senders(run: dict) -> None:
    assert _step(run, "4:card") is True
    assert _step(run, "4:empty-text") == "Empty: OSC from every sender is accepted."
    assert _step(run, "4:bad") == []
    assert _step(run, "4:added") == ["192.168.1.0/24"]
    assert _step(run, "4:row-text") == "192.168.1.0/24"
    assert _step(run, "4:empty-gone") is True
    assert _step(run, "4:asked") == ["192.168.1.0/24"]
    assert _step(run, "4:removed") == []


def test_monitor_shows_blocked_and_allows_the_sender(run: dict) -> None:
    assert _step(run, "5:input") == "blocked"
    assert _step(run, "5:add-hidden") is True
    assert _step(run, "5:menu-host") == BLOCKED_HOST
    assert _step(run, "5:menu-open") is True
    assert "Allow this sender" in _step(run, "5:menu")
    assert _step(run, "5:allowed") == [BLOCKED_HOST]


if __name__ == "__main__":
    main()
