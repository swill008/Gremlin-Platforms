# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Screens (audit 3).

- Button Map: switching device with the crash-recovery offer open deleted
  the recovery copy, and Restore then loaded the first device's edits into
  the second (6). Not now kept the copy but deleted its new photo; it now
  keeps both until Restore or Discard (decision A).
- Swap Devices listed the devices from before a swap, so a second Swap
  swapped everything back (17).
- Keyboard: after Add Key the highlighted row was another key than the
  editor's (20); a key only looked at in a mode showed Delete (33), and
  Delete in the mode with its actions left it listed.
- Button Map: Ctrl+V after switching device pasted the clipboard's picture
  instead of the chips copied (21); Group Selected refused a chip on a
  table with a text, which grouping packs, and Ctrl+G ignored it (22).
- Options search: "other" showed every row under "Other" (28).

The screens run off-screen in their own process (this file, run as a
script: python test/unit/test_audit3_screens.py <part> <out_dir>).
"""

from __future__ import annotations

import json
import os
import sys

sys.path.append(".")

import pathlib
import subprocess
import tempfile
import unittest.mock
from collections.abc import Iterator

_HERE = pathlib.Path(__file__).parent
_ROOT = _HERE.parents[1]


def _run(part: str, tmp_path: pathlib.Path) -> dict[str, str]:
    """Runs one screen part; its RESULT lines by name."""
    result = subprocess.run(
        [sys.executable, str(pathlib.Path(__file__)), part, str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=180,
        cwd=str(_ROOT),
        env={
            **os.environ,
            "QT_QPA_PLATFORM": "offscreen",
            "GREMLIN_OFFLINE": "1",
            "USERPROFILE": str(tmp_path),
        },
    )
    lines = result.stdout.splitlines()
    assert "done" in lines, result.stdout[-2000:] + result.stderr[-2000:]
    errors = [line for line in lines if line.startswith("ERROR")]
    assert errors == [], errors
    # No QML warning from the files these fixes are in.
    ours = ("DialogJoystickButtonMap.qml", "KeyboardInputList.qml",
            "ConfigGroup.qml", "rig_groups.js", "rig_selection.js")
    warned = [
        line for line in lines
        if line.startswith("WARN") and any(f in line for f in ours)
    ]
    assert warned == [], warned
    return {
        line.split(" ", 2)[1]: line.split(" ", 2)[2] if line.count(" ") >= 2 else ""
        for line in lines
        if line.startswith("RESULT ")
    }


# --- models, in this process ---------------------------------------------------

if __name__ != "__main__":
    import pytest
    from PySide6 import QtCore

    import dill
    from gremlin import shared_state
    from gremlin.event_handler import Event
    from gremlin.profile import Profile
    from gremlin.signal import signal
    from gremlin.types import InputType
    from gremlin.ui.backend import Backend, UIState
    from gremlin.ui.device import KeyboardManagerModel

    _APPS: list[QtCore.QCoreApplication] = []

    @pytest.fixture(scope="module", autouse=True)
    def _app() -> Iterator[QtCore.QCoreApplication]:
        app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
        _APPS.append(app)
        yield app

    @pytest.fixture
    def profile() -> Iterator[Profile]:
        previous = shared_state.current_profile
        shared_state.current_profile = Profile()
        yield shared_state.current_profile
        shared_state.current_profile = previous

    def _role(model: QtCore.QAbstractListModel, name: bytes) -> int:
        return next(r for r, n in model.roles.items() if bytes(n) == name)

    def _rows(model: QtCore.QAbstractListModel, name: bytes) -> list:
        role = _role(model, name)
        return [model.data(model.index(r, 0), role) for r in range(model.rowCount())]

    # 17 ------------------------------------------------------------------------

    def test_the_swap_list_follows_a_swap_and_another_profile(
        xml_dir: pathlib.Path,
    ) -> None:
        import uuid

        from gremlin.ui.profile import ProfileDeviceListModel
        from gremlin.ui.tools import Tools

        previous = shared_state.current_profile
        loaded = Profile()
        loaded.from_xml(str(xml_dir / "profile_auto_mapper.xml"))
        shared_state.current_profile = loaded
        try:
            model = ProfileDeviceListModel()
            source = "97b77b40-07d8-11f0-8028-444553540000"
            target = str(uuid.uuid4())
            assert _rows(model, b"uuid") == [source]
            Tools().swapDevices(source, target)
            # The bindings moved: both listed, with their new counts (the
            # list said the old device still had them).
            uuids = _rows(model, b"uuid")
            assert uuids == [source, target]
            labels = _rows(model, b"nameAndActions")
            assert labels[0].endswith("- 0 actions")
            assert labels[1].endswith("- 9 actions")
            # Another profile: its devices, not the old one's.
            shared_state.current_profile = Profile()
            signal.profileChanged.emit()
            assert model.rowCount() == 0
        finally:
            shared_state.current_profile = previous

    # 20 / 33 -------------------------------------------------------------------

    def _add(model: KeyboardManagerModel, key: tuple, mode: str = "Default") -> int:
        pressed = Event(InputType.Keyboard, key, dill.UUID_Keyboard, mode)
        return model.addKey([pressed], mode)

    def test_add_key_gives_its_row_and_a_key_finds_its_row(profile: Profile) -> None:
        model = KeyboardManagerModel()
        assert _add(model, (31, False)) == 0  # S
        # A (30) sorts before S: the new key's row, not the row number held.
        assert _add(model, (30, False)) == 0
        assert model.inputIdentifier(0).input_id == (30, False)
        s_key = model.inputIdentifier(1)
        assert model.rowOf(s_key) == 1
        assert model.rowOf(None) == -1
        assert model.addKey([], "Default") == -1

    def test_a_key_only_looked_at_shows_no_delete(
        profile: Profile, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import gremlin.ui.backend

        # The editor's model of the input isn't needed, only what asking for
        # it leaves in the profile.
        monkeypatch.setattr(gremlin.ui.backend, "InputItemModel", lambda *a: a[0])
        profile.modes.add_mode("Combat")
        model = KeyboardManagerModel()
        _add(model, (30, False), "Combat")
        profile.get_input_item(
            dill.UUID_Keyboard, InputType.Keyboard, (30, False), "Combat"
        ).add_item_binding()
        in_mode = _role(model, b"inMode")
        # The editor shows the key in Default: that makes an empty input.
        state = UIState()
        backend = unittest.mock.Mock(profile=profile, ui_state=state)
        assert Backend.klass.getInputItem(backend, model.inputIdentifier(0), 0)
        assert profile.get_input_item(
            dill.UUID_Keyboard, InputType.Keyboard, (30, False), "Default"
        ) is not None
        # Default has nothing to delete (Delete showed, and did nothing).
        assert model.data(model.index(0, 0), in_mode) is False
        model.setMode("Combat")
        assert model.data(model.index(0, 0), in_mode) is True
        # A key just added, with no actions anywhere: Delete removes it.
        _add(model, (31, False), "Combat")
        assert model.data(model.index(1, 0), in_mode) is True
        state.deleteLater()

    def test_a_key_only_looked_at_elsewhere_is_deleted_there(
        profile: Profile, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import gremlin.ui.backend

        monkeypatch.setattr(gremlin.ui.backend, "InputItemModel", lambda *a: a[0])
        profile.modes.add_mode("Combat")
        model = KeyboardManagerModel()

        def bind(key: tuple, mode: str) -> None:
            _add(model, key, mode)
            item = profile.get_input_item(
                dill.UUID_Keyboard, InputType.Keyboard, key, mode
            )
            assert item is not None
            item.add_item_binding()

        bind((30, False), "Combat")
        bind((31, False), "Combat")
        # A also has actions in Default: Delete in Combat keeps it listed.
        bind((30, False), "Default")
        # S only looked at in Default (the editor makes an empty input).
        state = UIState()
        backend = unittest.mock.Mock(profile=profile, ui_state=state)
        s_key = model.inputIdentifier(1)
        assert s_key is not None
        assert Backend.klass.getInputItem(backend, s_key, 0)
        modes = [str(i.mode) for i in profile.inputs[dill.UUID_Keyboard]]
        assert sorted(modes) == ["Combat", "Combat", "Default", "Default"]
        in_mode = _role(model, b"inMode")
        model.setMode("Combat")
        model.deleteInput(1)
        # Only Combat's input goes: an empty one in Default may be a key added
        # there on purpose, so S stays listed ...
        assert model.rowCount() == 2
        row = model.rowOf(s_key)
        assert row == 1
        # ... and with no actions anywhere, its Delete shows in Default and
        # removes it.
        model.setMode("Default")
        assert model.data(model.index(row, 0), in_mode) is True
        model.deleteInput(row)
        assert model.rowCount() == 1
        assert model.rowOf(s_key) == -1
        # A's Combat actions deleted; its Default ones stay, and so does A.
        model.setMode("Combat")
        model.deleteInput(0)
        assert model.rowCount() == 1
        assert [i.mode for i in profile.inputs[dill.UUID_Keyboard]] == ["Default"]
        state.deleteLater()

    # 6 / decision A, 21, 22, 20, 28, 17: the screens ---------------------------

    def test_button_map_recovery_offer_and_device_switch(
        tmp_path: pathlib.Path,
    ) -> None:
        r = _run("buttonmap", tmp_path)
        # The offer is open on Stick A.
        assert r["offer-a"] == "true"
        # Stick B opened from Home: A's offer is put off, never deleted or
        # applied to B; A's new photo stays with it.
        assert r["switched"] == "gate:false pending:false copyA:true stashA:true"
        assert r["restore-on-b"] == "editing:false"
        # Back on A: offered again; Not now keeps the copy and the new photo.
        assert r["offer-a-again"] == "true"
        assert r["not-now"] == "copyA:true stashA:true photo:new"
        # Edit after Not now offers them again (no new session to write over
        # the copy or delete it on Cancel).
        assert r["edit-offers"] == (
            "gate:true editing:false copyA:true stashA:true photo:new"
        )
        # Discard puts the saved photo back and removes the copy.
        assert r["discard"] == "copyA:false stashA:false photo:old"
        # Blank page with the offer open: put off as well.
        assert r["blank"] == "gate:false copyA:true stashA:true"
        # A copy that only changed the photo (same file name) is offered.
        assert r["photo-only"] == "offered:true gate:true copyA:true stashA:true"
        # A copy kept under the stick's old name: Restore opens it; Cancel
        # removes it and puts the saved photo back.
        assert r["renamed"] == (
            "editing:true a2:true copyA:false stashA:false photo:old"
        )
        # Ctrl+C on one device, Ctrl+V on the next: the chips, not the
        # clipboard's older picture.
        assert r["carry"] == "kept:true pasted:1 btn"
        # A chip on a table with a text, no table selected: packs.
        assert r["group-table-text"] == "true"
        assert r["group-drawings"] == "false"
        # Where it can't group, Group Selected / Ctrl+G stay on and say why
        # (Ctrl+G's gate made these messages unreachable).
        assert r["group-two-tables"] == "true:Group one table at a time."
        assert r["group-table-drawing"] == (
            "true:Select chips or text with the table to pack."
        )

    def test_keyboard_highlight_follows_the_editor(tmp_path: pathlib.Path) -> None:
        r = _run("keyboard", tmp_path)
        # S picked; A added (sorts first): A is highlighted and in the editor.
        assert r["picked"] == "0 S 0"
        assert r["added"] == "0 A A 0"
        # Another reset (a key added before the one shown, from elsewhere):
        # the highlight follows the editor's key to its new row.
        assert r["moved"] == "2 S S 2"

    def test_swap_list_selection_after_a_swap(tmp_path: pathlib.Path) -> None:
        r = _run("swap", tmp_path)
        before, after = r["swap"].split(" | ")
        assert before.endswith("- 9 actions")
        # The same device stays chosen, now with its new count.
        assert after.endswith("- 0 actions")
        assert r["swap-count"] == "2"

    def test_options_search_does_not_match_other(tmp_path: pathlib.Path) -> None:
        r = _run("options", tmp_path)
        # "other" finds nothing in a group just for being "Other"...
        assert r["other-shown"] == "false"
        # ...and a real group's title still counts.
        assert r["titled-shown"] == "true"


# --- the screens, in their own process ----------------------------------------


class _Out:
    @staticmethod
    def result(name: str, value: object) -> None:
        print(f"RESULT {name} {value}", flush=True)


def _boot() -> None:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ.setdefault(
        "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    )
    sys.path.insert(0, str(_ROOT))
    import gremlin.util

    # Settings and module files in a folder of their own, never the user's.
    gremlin.util.userprofile_path = unittest.mock.Mock(return_value=tempfile.mkdtemp())


def _engine(out: pathlib.Path) -> tuple:
    from PySide6 import QtCore, QtGui, QtQml

    app = QtGui.QGuiApplication(sys.argv[:1])
    QtQml.qmlRegisterSingletonType(
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "Style.qml")),
        "Gremlin.Style", 1, 0, "Style",
    )
    import gremlin.ui.backend  # noqa: F401
    import gremlin.ui.button_map_options  # noqa: F401
    import gremlin.ui.device_names  # noqa: F401
    import joystick_gremlin

    joystick_gremlin.register_config_options()
    engine = QtQml.QQmlApplicationEngine()
    engine.addImportPath(str(_ROOT / "theme"))
    warnings: list[str] = []
    engine.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))
    return app, engine, warnings


def _js(win: object, code: str) -> str:
    from PySide6 import QtQml

    expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
    value = expr.evaluate()[0]
    if expr.hasError():
        print(f"ERROR {code[:60]}: {expr.error().toString()}", flush=True)
        return ""
    return str(value)


def _wait(ms: int) -> None:
    from PySide6 import QtTest

    QtTest.QTest.qWait(ms)


def _fakes() -> tuple:
    from PySide6 import QtCore

    class FakeBackend(QtCore.QObject):
        uiScaleChanged = QtCore.Signal()
        propertyChanged = QtCore.Signal()
        activityChanged = QtCore.Signal()

        uiScale = QtCore.Property(int, fget=lambda self: 100, notify=uiScaleChanged)
        gremlinActive = QtCore.Property(
            bool, fget=lambda self: False, notify=activityChanged
        )
        currentMode = QtCore.Property(
            str, fget=lambda self: "Default", notify=propertyChanged
        )

        @QtCore.Slot(str)
        def noteSave(self, text: str) -> None:
            pass

    class FakeUiState(QtCore.QObject):
        modeChanged = QtCore.Signal()
        currentMode = QtCore.Property(
            str, fget=lambda self: "Default", notify=modeChanged
        )

    return FakeBackend, FakeUiState


def _button_map(out: pathlib.Path) -> None:
    from PySide6 import QtCore, QtGui

    app, engine, warnings = _engine(out)  # noqa: F841 (kept for the run)
    backend_cls, ui_cls = _fakes()
    backend, ui_state = backend_cls(), ui_cls()
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("uiState", ui_state)
    engine.load(
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "DialogJoystickButtonMap.qml"))
    )
    win = engine.rootObjects()[0]
    win.setProperty("width", 1400)
    win.setProperty("height", 900)
    win.setProperty("visible", True)
    _wait(600)

    def picture(name: str, colour: str) -> str:
        image = QtGui.QImage(64, 64, QtGui.QImage.Format.Format_RGB32)
        image.fill(QtGui.QColor(colour))
        path = out / name
        image.save(str(path))
        return QtCore.QUrl.fromLocalFile(str(path)).toString()

    old_url = picture("old.png", "#336699")
    new_url = picture("new.png", "#993366")
    a1 = ("{id: 'a1', kind: 'draw', shape: 'rect',"
          " fx: 0.1, fy: 0.1, fw: 0.1, fh: 0.1}")
    # Stick A saved with the old photo; then an edit changed the photo and
    # the program closed: kept photo, new photo, recovery copy.
    crash = (
        "var n = 'Stick A';"
        " _hw.stashPhoto(n);"
        f" var rel = _hw.copyImage('{new_url}', n);"
        f" _hw.saveRecovery(n, JSON.stringify({{image: rel, nodes: [{a1},"
        " {id: 'a2', kind: 'draw', shape: 'rect',"
        " fx: 0.4, fy: 0.4, fw: 0.1, fh: 0.1}]}));"
        " rel"
    )
    _js(win, "var n = 'Stick A';"
             " _hw.save(n, JSON.stringify({kind: 'control.hardware',"
             f" device: n, nodes: [{a1}]}}));"
             f" var r = _hw.copyImage('{old_url}', n);"
             # Saved with that photo: Save names it (07 Q2, GL-174).
             " _hw.save(n, JSON.stringify({kind: 'control.hardware',"
             f" device: n, image: r, nodes: [{a1}]}}))")
    _js(win, "_hw.save('Stick B', JSON.stringify({kind: 'control.hardware',"
             " device: 'Stick B', nodes: []}))")
    _js(win, crash)

    state_a = ("'copyA:' + (_hw.loadRecovery('Stick A').length > 0)"
               " + ' stashA:' + _hw.hasPhotoStash('Stick A')")
    _js(win, "_buttonMap.openForDevice('Stick A', '', ''); 1")
    _wait(500)
    _Out.result("offer-a", _js(win, "String(_recoverGate.opened)"))
    # Home: Stick B's Button Map, with the offer still open.
    _js(win, "_buttonMap.openForDevice('Stick B', '', ''); 1")
    _wait(500)
    _Out.result("switched", _js(
        win, "'gate:' + _recoverGate.opened"
             " + ' pending:' + (_buttonMap._pendingRecovery !== null)"
             f" + ' ' + {state_a}"))
    _js(win, "_buttonMap.restoreRecovery(); 1")
    _wait(200)
    _Out.result("restore-on-b", _js(win, "'editing:' + _buttonMap.editing"))
    _js(win, "_buttonMap.discardEdit(); 1")
    _wait(200)

    # Which photo shows: the photo file's colour (copyImage keeps one name).
    photo_file = ("var p = _hw.imageUrl(JSON.parse(_hw.load('Stick A')).image); p")

    def photo_colour() -> str:
        url = _js(win, photo_file)
        image = QtGui.QImage(QtCore.QUrl(url).toLocalFile())
        if image.isNull():
            return "none"
        name = image.pixelColor(2, 2).name()
        return {"#993366": "new", "#336699": "old"}.get(name, name)

    _js(win, "_buttonMap.openForDevice('Stick A', '', ''); 1")
    _wait(500)
    _Out.result("offer-a-again", _js(win, "String(_recoverGate.opened)"))
    # Not now.
    _js(win, "_recoverGate.close(); 1")
    _wait(300)
    _Out.result("not-now", _js(win, state_a) + " photo:" + photo_colour())
    # Edit after Not now: the edits are offered again, not a new session
    # (its autosave wrote over the copy and its Cancel deleted copy and
    # photo).
    edit = _js(win, "_buttonMap.enterEdit();"
                    " 'gate:' + _recoverGate.opened + ' editing:' + _buttonMap.editing")
    _js(win, "_recoverGate.close(); _buttonMap.autosaveNow();"
             " _buttonMap.discardEdit(); 1")
    _wait(300)
    _Out.result("edit-offers",
                edit + " " + _js(win, state_a) + " photo:" + photo_colour())
    # Opened again: offered again; Discard.
    _js(win, "_buttonMap.offerRecovery(); 1")
    _wait(300)
    _js(win, "_recoverGate._choice = 'discard'; _recoverGate.close();"
             " _recoverGate.discarded(); 1")
    _wait(300)
    _Out.result("discard", _js(win, state_a) + " photo:" + photo_colour())
    # The same again, then Blank Button Map with the offer open.
    _js(win, crash)
    _js(win, "_buttonMap.offerRecovery(); 1")
    _wait(300)
    _js(win, "_buttonMap.openBlank(); 1")
    _wait(300)
    _Out.result("blank", _js(win, f"'gate:' + _recoverGate.opened + ' ' + {state_a}"))

    # Back on A (Not now). A copy that only changed the photo, kept under
    # the old file name, reads the same as the saved map: still offered
    # (it was deleted and the old photo put back).
    _js(win, "_buttonMap.openForDevice('Stick A', '', ''); 1")
    _wait(500)
    _js(win, "_recoverGate.close(); 1")
    _wait(200)
    _js(win, "_hw.saveRecovery('Stick A', JSON.stringify({image: _buttonMap.liveImage,"
             " photo: _buttonMap.livePhoto || _buttonMap.photoFromDoc(null),"
             " nodes: _buttonMap.liveNodes})); 1")
    offered = _js(win, "String(_buttonMap.offerRecovery())")
    _Out.result("photo-only", f"offered:{offered} gate:"
                + _js(win, "String(_recoverGate.opened)") + " " + _js(win, state_a))
    _js(win, "_recoverGate.close(); 1")
    _wait(200)
    # The stick was renamed since the crash: its copy (found by module file)
    # names the old name. Restore opens it; Cancel then removes the copy and
    # puts the saved photo back.
    from gremlin.ui.hardware_profile import _maps_dir

    copies = [
        p for p in (_maps_dir() / "recovery").glob("*.json")
        if json.loads(p.read_text(encoding="utf-8")).get("device") == "Stick A"
    ]
    if not copies:
        print("ERROR renamed: Stick A's recovery copy is gone", flush=True)
        _report(warnings)
    copy = copies[0]
    doc = json.loads(copy.read_text(encoding="utf-8"))
    doc["device"] = "Old Stick A"
    doc["nodes"] = doc["nodes"] + [{"id": "a2", "kind": "draw", "shape": "rect",
                                    "fx": 0.4, "fy": 0.4, "fw": 0.1, "fh": 0.1}]
    copy.write_text(json.dumps(doc), encoding="utf-8")
    _js(win, "_buttonMap.offerRecovery(); _buttonMap.restoreRecovery(); 1")
    _wait(400)
    restored = _js(win, "'editing:' + _buttonMap.editing + ' a2:'"
                        " + _buttonMap.workNodes.some(function(n) {"
                        " return n.id === 'a2' })")
    _js(win, "_recoverGate.close(); _buttonMap.discardEdit(); 1")
    _wait(300)
    _Out.result("renamed",
                restored + " " + _js(win, state_a) + " photo:" + photo_colour())

    # 21: a picture on the clipboard, then chips copied on Stick B; Ctrl+V
    # on Stick C pastes the chips.
    _js(win, "_hw.save('Stick C', JSON.stringify({kind: 'control.hardware',"
             " device: 'Stick C', nodes: []}))")
    mime = QtCore.QMimeData()
    mime.setUrls([QtCore.QUrl(old_url)])
    QtGui.QGuiApplication.clipboard().setMimeData(mime)
    _wait(300)
    _js(win, "_buttonMap.openForDevice('Stick B', '', ''); 1")
    _wait(500)
    _js(win, "_buttonMap.enterEdit(); var e = _ed();"
             " e.nodes.push({id: 'c1', kind: 'btn', hwId: 1, chipFx: 0.3, chipFy: 0.3,"
             " hotFx: 0.35, hotFy: 0.35}); e.bump(); e.setSelection(['c1']);"
             " e.copySelection(); 1")
    _wait(300)
    kept = _js(win, "String(_buttonMap.keptCopySerial === _hw.clipboardSerial)")
    _js(win, "_buttonMap.discardEdit(); _buttonMap.openForDevice('Stick C', '', ''); 1")
    _wait(500)
    _js(win, "_buttonMap.enterEdit(); 1")
    _wait(400)
    pasted = _js(win, "var e = _ed(); var before = e.nodes.length; e.pasteClipboard();"
                      " var n = e.nodeAt(e.selectedId);"
                      " (e.nodes.length - before) + ' ' + (n ? n.kind : '-')")
    _Out.result("carry", f"kept:{kept} pasted:{pasted}")
    _js(win, "_buttonMap.discardEdit(); 1")
    _wait(300)

    # 22: a table, a chip on it and a text beside it; chip and text chosen.
    _js(win, "_buttonMap.enterEdit(); var e = _ed();"
             " e.nodes.push({id: 't1', kind: 'draw', shape: 'table',"
             " fx: 0.2, fy: 0.2, fw: 0.5, fh: 0.5});"
             " e.nodes.push({id: 'c2', kind: 'btn', hwId: 2, chipFx: 0.4, chipFy: 0.4,"
             " hotFx: 0.8, hotFy: 0.8});"
             " e.nodes.push({id: 'x1', kind: 'draw', shape: 'text', text: 'Hi',"
             " fx: 0.8, fy: 0.1, fw: 0.1, fh: 0.05}); e.bump(); 1")
    _wait(500)
    _Out.result("group-table-text", _js(
        win, "var e = _ed(); e.setSelection(['c2', 'x1']); String(e.canGroup())"))
    _Out.result("group-drawings", _js(
        win, "var e = _ed(); e.nodes.push({id: 'd9', kind: 'draw', shape: 'rect',"
             " fx: 0.05, fy: 0.85, fw: 0.05, fh: 0.05}); e.bump();"
             " e.setSelection(['x1', 'd9']); String(e.canGroup())"))
    # Ctrl+G (as its Shortcut: only when canGroup) on two tables, and on a
    # table with only a drawing: says why nothing was grouped.
    ctrl_g = ("String(e.canGroup()) + ':'"
              " + (e.canGroup() ? (e.groupSelection(), e.packWarn) : '')")
    _Out.result("group-two-tables", _js(
        win, "var e = _ed(); e.nodes.push({id: 't2', kind: 'draw', shape: 'table',"
             " fx: 0.75, fy: 0.75, fw: 0.2, fh: 0.2}); e.bump();"
             f" e.setSelection(['t1', 't2']); {ctrl_g}"))
    _Out.result("group-table-drawing", _js(
        win, f"var e = _ed(); e.packWarn = ''; e.setSelection(['t1', 'd9']); {ctrl_g}"))
    _js(win, "_buttonMap.discardEdit(); 1")
    _report(warnings)


def _keyboard(out: pathlib.Path) -> None:
    from PySide6 import QtCore

    app, engine, warnings = _engine(out)  # noqa: F841
    import dill
    import gremlin.action_label  # noqa: F401
    import gremlin.ui.device  # noqa: F401
    import gremlin.ui.util  # noqa: F401
    from gremlin import shared_state
    from gremlin.profile import Profile
    from gremlin.ui.backend import UIState

    shared_state.current_profile = Profile()
    backend_cls, _ = _fakes()
    backend = backend_cls()
    ui_state = UIState()
    ui_state.setCurrentDevice(str(dill.UUID_Keyboard))
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("uiState", ui_state)
    from gremlin.signal import signal

    engine.rootContext().setContextProperty("signal", signal)
    engine.loadData(
        b"""
import QtQuick
import QtQuick.Window
Window {
    width: 600; height: 700; visible: true
    QtObject { id: bsi; property var icons: ({ remove: "x" }) }
    KeyboardInputList { id: _page; anchors.fill: parent }
    function list() {
        function find(item) {
            if (item.model !== undefined && item.currentIndex !== undefined
                    && item.count !== undefined)
                return item
            for (var i = 0; i < item.children.length; i++) {
                var f = find(item.children[i])
                if (f) return f
            }
            return null
        }
        return find(_page)
    }
}
""",
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "Root.qml")),
    )
    win = engine.rootObjects()[0]
    _wait(400)

    from PySide6 import QtQml

    from gremlin.event_handler import Event
    from gremlin.types import InputType
    from gremlin.ui.util import InputListenerModel

    context = QtQml.qmlContext(win)
    model = QtQml.QQmlExpression(context, win, "list().model").evaluate()[0]
    add_key = win.findChildren(InputListenerModel)[0]

    def press(code: int) -> list:
        return [Event(InputType.Keyboard, (code, False), dill.UUID_Keyboard, "Default")]

    # Row highlighted and its key; the editor's key and the row it was given.
    name = "l.model.data(l.model.index({0}, 0), 257)"
    shown = ("var l = list(); var r = l.currentIndex;"
             " r + ' ' + (r >= 0 ? " + name.format("r") + " : '-')")
    # The editor's key: the highlighted row's key, or "other".
    editor = ("var l = list(); var r = l.currentIndex;"
              " (r >= 0 && l.model.inputIdentifier(r).label"
              " === uiState.currentInput.label ? " + name.format("r")
              + " : 'other') + ' ' + uiState.currentInputIndex")
    model.addKey(press(31), "Default")  # S
    _wait(200)
    _js(win, "list().currentIndex = 0; 1")
    _wait(200)
    index = _js(win, "String(uiState.currentInputIndex)")
    _Out.result("picked", _js(win, shown) + " " + index)
    # Add Key, as the button's listener hands over a pressed A.
    add_key.listeningTerminated.emit(press(30))
    _wait(300)
    _Out.result("added", _js(win, shown) + " " + _js(win, editor))
    # The editor on S, then two keys sorting before it added from elsewhere.
    _js(win, "list().currentIndex = 1; 1")
    _wait(200)
    model.addKey(press(16), "Default")  # Q
    model.addKey(press(17), "Default")  # W
    _wait(300)
    _Out.result("moved", _js(win, shown) + " " + _js(win, editor))
    _report(warnings)


def _swap(out: pathlib.Path) -> None:
    import uuid

    from PySide6 import QtCore

    app, engine, warnings = _engine(out)  # noqa: F841
    from gremlin import event_handler, shared_state
    from gremlin.profile import Profile

    # Device changes aren't wanted here: no listener (and no Windows hooks).
    class _Listener(QtCore.QObject):
        device_change_event = QtCore.Signal()

    listener = _Listener()
    event_handler.EventListener = lambda: listener
    import gremlin.ui.profile  # noqa: F401
    import gremlin.ui.tools  # noqa: F401
    from gremlin.types import InputType

    # A stick with nine bound buttons.
    loaded = Profile()
    shared_state.current_profile = loaded
    stick = uuid.UUID("97b77b40-07d8-11f0-8028-444553540000")
    for button in range(1, 10):
        loaded.get_input_item(
            stick, InputType.JoystickButton, button, "Default", True
        ).add_item_binding()
    engine.loadData(
        b"""
import QtQuick
import QtQuick.Controls
import QtQuick.Window
import Gremlin.Profile
import Gremlin.Tools
Window {
    width: 500; height: 200; visible: true
    property alias box: _box
    Tools { id: _tools }
    ComboBox {
        id: _box
        width: 400
        model: ProfileDeviceListModel {}
        textRole: "nameAndActions"
        valueRole: "uuid"
    }
    function swap(to) { return _tools.swapDevices(_box.currentValue, to) }
}
""",
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "Root.qml")),
    )
    win = engine.rootObjects()[0]
    _wait(300)
    before = _js(win, "box.currentText")
    chosen = _js(win, "box.currentValue")
    _js(win, f"swap('{uuid.uuid4()}')")
    _wait(300)
    after = _js(win, "box.currentText")
    same = _js(win, "box.currentValue")
    if same != chosen:
        print(f"ERROR swap: the choice moved from {chosen} to {same}", flush=True)
    _Out.result("swap", f"{before} | {after}")
    _Out.result("swap-count", _js(win, "String(box.count)"))
    _report(warnings)


def _options(out: pathlib.Path) -> None:
    from PySide6 import QtCore

    app, engine, warnings = _engine(out)  # noqa: F841
    from gremlin.ui import option

    # A group's settings, under "Other" and under their own title.
    section, groups = option.main_layout()[0]
    title, keys = groups[0]
    other = option.ConfigEntryModel(keys[0][0], keys[0][1], keys=keys[:1])
    titled = option.ConfigEntryModel(keys[0][0], keys[0][1], keys=keys[:1])
    engine.rootContext().setContextProperty("otherModel", other)
    engine.rootContext().setContextProperty("titledModel", titled)
    engine.rootContext().setContextProperty("titledName", title)
    engine.loadData(
        b"""
import QtQuick
import QtQuick.Layouts
import QtQuick.Window
Window {
    width: 600; height: 400; visible: true
    property alias other: _other
    property alias titled: _titled
    ColumnLayout {
        ConfigGroup { id: _other; index: 0; groupName: "Other"; entryModel: otherModel }
        ConfigGroup {
            id: _titled; index: 1; groupName: titledName; entryModel: titledModel
        }
    }
}
""",
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "Root.qml")),
    )
    win = engine.rootObjects()[0]
    _wait(300)
    needle = "other"
    name = _js(win, "String(otherModel.data(otherModel.index(0, 0), 256 + 5))")
    text = _js(win, "String(otherModel.data(otherModel.index(0, 0), 256 + 3))")
    if needle in (name + " " + text).lower():
        print(f"ERROR options: the row itself says {needle!r}", flush=True)
    _Out.result("other-shown",
                _js(win, f"other.filterText = '{needle}'; String(other.visible)"))
    word = title.split()[0].lower()
    _Out.result("titled-shown",
                _js(win, f"titled.filterText = '{word}'; String(titled.visible)"))
    _report(warnings)


def _report(warnings: list[str]) -> None:
    for warning in warnings:
        print("WARN " + warning.encode("ascii", "replace").decode(), flush=True)
    print("done", flush=True)
    # os._exit skips Qt's teardown, which can hang off-screen.
    os._exit(0)


if __name__ == "__main__":
    _boot()
    sys.stdout.reconfigure(encoding="utf-8")
    _part, _out_dir = sys.argv[1], pathlib.Path(sys.argv[2])
    _out_dir.mkdir(parents=True, exist_ok=True)
    try:
        {"buttonmap": _button_map, "keyboard": _keyboard, "swap": _swap,
         "options": _options}[_part](_out_dir)
    except Exception as failed:  # noqa: BLE001 (said, then the process ends)
        import traceback

        traceback.print_exc()
        print(f"ERROR {_part}: {failed!r}", flush=True)
        os._exit(1)
