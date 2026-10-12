# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Screens (audit 3).

- Device Mapping Editor: switching device with the crash-recovery offer open deleted
  the recovery copy, and Restore then loaded the first device's edits into
  the second (6). Not now kept the copy but deleted its new photo; it now
  keeps both until Restore or Discard (decision A).
- Swap Devices listed the devices from before a swap, so a second Swap
  swapped everything back (17). The Swap Devices window is gone (Device
  Library, D-10-SWAP); the list model's refresh is still checked.
- Keyboard: after Add Key the highlighted row was another key than the
  editor's (20); a key only looked at in a mode showed Delete (33), and
  Delete in the mode with its actions left it listed.
- Device Mapping Editor: Ctrl+V after switching device pasted the clipboard's picture
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
import tempfile
import unittest.mock
from collections.abc import Iterator

_HERE = pathlib.Path(__file__).parent
_ROOT = _HERE.parents[1]


def _run(part: str, tmp_path: pathlib.Path) -> dict[str, str]:
    """Runs one screen part; its RESULT lines by name."""
    import proc_tree  # pyright: ignore[reportMissingImports]  (test/)

    result = proc_tree.run(
        [sys.executable, str(pathlib.Path(__file__)), part, str(tmp_path)],
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
    ours = (
        "DialogDeviceMappingEditor.qml",
        "KeyboardPage.qml",
        "ConfigGroup.qml",
        "rig_groups.js",
        "rig_selection.js",
    )
    warned = [
        line
        for line in lines
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
    from gremlin.ui.keyboard_layout import KeyboardLayoutModel, key_row

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

        from gremlin import swap_devices
        from gremlin.ui.profile import ProfileDeviceListModel

        previous = shared_state.current_profile
        loaded = Profile()
        loaded.from_xml(str(xml_dir / "profile_auto_mapping_tool.xml"))
        shared_state.current_profile = loaded
        try:
            model = ProfileDeviceListModel()
            source = "97b77b40-07d8-11f0-8028-444553540000"
            target = str(uuid.uuid4())
            assert _rows(model, b"uuid") == [source]
            swap_devices.swap_devices(loaded, uuid.UUID(source), uuid.UUID(target))
            signal.profileChanged.emit()
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

    # The Keyboard page's model (KeyboardLayoutModel, 05 S128).
    _KEPT: list[QtCore.QObject] = []

    def _page() -> KeyboardLayoutModel:
        model = KeyboardLayoutModel()
        _KEPT.append(model)
        return model

    @pytest.fixture(autouse=True)
    def _no_held_layout() -> Iterator[None]:
        from gremlin.modules import store
        from gremlin.ui.keyboard_layout import keyboard_store

        yield
        store.discard_pending("")
        keyboard_store().load()

    def _add(model: KeyboardLayoutModel, key: tuple, mode: str = "Default") -> str:
        pressed = Event(InputType.Keyboard, key, dill.UUID_Keyboard, mode)
        return model.addKey([pressed], mode)

    def _listed(model: KeyboardLayoutModel) -> list[str]:
        return [r["key"] for r in model._rows if r["rowKind"] == "parent"]

    def test_add_key_gives_its_row_and_a_key_finds_its_row(profile: Profile) -> None:
        model = _page()
        s_row = _add(model, (31, False))  # S
        assert s_row == key_row((31, False)) and _listed(model) == [s_row]
        # A after S: the new key's own row key, not a row number held.
        a_row = _add(model, (30, False))
        assert a_row == key_row((30, False))
        assert set(_listed(model)) == {a_row, s_row}
        assert model.addKey([], "Default") == ""

    def test_a_key_only_looked_at_shows_no_delete(profile: Profile) -> None:
        profile.modes.add_mode("Combat")
        model = _page()
        a_row = _add(model, (30, False), "Combat")
        profile.get_input_item(
            dill.UUID_Keyboard, InputType.Keyboard, (30, False), "Combat"
        ).add_item_binding()
        # The pane shows the key in Default: a draft, nothing made in the
        # profile.
        model.setMode("Default")
        model.beginPane(a_row, -1)
        assert model.paneModel is not None
        model.endPane()
        assert (
            profile.get_input_item(
                dill.UUID_Keyboard, InputType.Keyboard, (30, False), "Default"
            )
            is None
        )
        # Default has nothing to delete: no Delete.
        assert not model.canDelete(a_row)
        model.setMode("Combat")
        assert model.canDelete(a_row)
        # A key just added, with no actions anywhere: Delete removes it.
        s_row = _add(model, (31, False), "Combat")
        assert model.canDelete(s_row)

    def test_a_key_only_looked_at_elsewhere_is_deleted_there(profile: Profile) -> None:
        profile.modes.add_mode("Combat")
        model = _page()

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
        # S added in Default too, with no actions there.
        s_row = _add(model, (31, False), "Default")
        modes = [str(i.mode) for i in profile.inputs[dill.UUID_Keyboard]]
        assert sorted(modes) == ["Combat", "Combat", "Default", "Default"]
        model.setMode("Combat")
        model.deleteParents([s_row])
        # Only Combat's input goes: an empty one in Default may be a key added
        # there on purpose, so S stays listed ...
        assert len(_listed(model)) == 2 and s_row in _listed(model)
        # ... and with no actions anywhere, its Delete shows in Default and
        # removes it.
        model.setMode("Default")
        assert model.canDelete(s_row)
        model.deleteParents([s_row])
        assert s_row not in _listed(model) and len(_listed(model)) == 1
        # A's Combat actions deleted; its Default ones stay, and so does A.
        model.setMode("Combat")
        model.deleteParents([key_row((30, False))])
        assert len(_listed(model)) == 1
        assert [i.mode for i in profile.inputs[dill.UUID_Keyboard]] == ["Default"]

    # 6 / decision A, 21, 22, 20, 28, 17: the screens ---------------------------

    def test_device_mapping_editor_recovery_offer_and_device_switch(
        tmp_path: pathlib.Path,
    ) -> None:
        r = _run("editor", tmp_path)
        # The offer is open on Stick A.
        assert r["offer-a"] == "true"
        # Stick B opened from Home: A's offer is put off, never deleted or
        # applied to B; A's new photo stays with it.
        assert r["switched"] == "gate:false pending:false copyA:true stashA:true"
        assert r["restore-on-b"] == "editing:false"
        # Back on A: offered again; Not now keeps the copy and the new photo
        # (waiting in the edit; the saved map shows the saved photo until
        # Save, 07 S107).
        assert r["offer-a-again"] == "true"
        assert r["not-now"] == "copyA:true stashA:true photo:old"
        # Edit after Not now offers them again (no new session to write over
        # the copy or delete it on Cancel).
        assert r["edit-offers"] == (
            "gate:true editing:false copyA:true stashA:true photo:old"
        )
        # Discard puts the saved photo back and removes the copy.
        assert r["discard"] == "copyA:false stashA:false photo:old"
        # Blank page with the offer open: put off as well.
        assert r["blank"] == "gate:false copyA:true stashA:true"
        # A copy that only changed the photo is offered.

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
        # The selected row, then the key in the pane (05 S73: Add Key selects
        # the key and opens the pane on it).
        assert r["picked"] == "S S"
        assert r["added"] == "A A"
        # Keys added from elsewhere: the selection and the pane stay on A.
        assert r["moved"] == "A A"

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
        "Gremlin.Style",
        1,
        0,
        "Style",
    )
    import gremlin.ui.backend  # noqa: F401
    import gremlin.ui.device_map_options  # noqa: F401
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


def _device_mapping_editor(out: pathlib.Path) -> None:
    from PySide6 import QtCore, QtGui

    app, engine, warnings = _engine(out)  # noqa: F841 (kept for the run)
    backend_cls, ui_cls = _fakes()
    backend, ui_state = backend_cls(), ui_cls()
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("uiState", ui_state)
    engine.load(
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "DialogDeviceMappingEditor.qml"))
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
    a1 = "{id: 'a1', kind: 'draw', shape: 'rect', fx: 0.1, fy: 0.1, fw: 0.1, fh: 0.1}"

    # The device's photo is the bottom background picture, a node like any
    # other (07 S111, S127); a recovery copy holds the nodes only.
    def bg(ref: str) -> str:
        return (
            "{id: 'bg', kind: 'draw', shape: 'image', plane: 'background',"
            f" src: {ref}, fx: 0.125, fy: 0.125, fw: 0.75, fh: 0.75}}"
        )

    # Stick A saved with the old photo; then an edit changed the photo and
    # the program closed: kept photo, new photo, recovery copy.
    crash = (
        "var n = 'Stick A';"
        " _hw.beginEdit(n);"
        f" var rel = _hw.copyImage('{new_url}', n);"
        f" _hw.saveRecovery(n, JSON.stringify({{nodes: [{bg('rel')}, {a1},"
        " {id: 'a2', kind: 'draw', shape: 'rect',"
        " fx: 0.4, fy: 0.4, fw: 0.1, fh: 0.1}]}));"
        " rel"
    )
    _js(
        win,
        "var n = 'Stick A';"
        " _hw.save(n, JSON.stringify({kind: 'control.hardware',"
        f" device: n, nodes: [{a1}]}}));"
        f" var r = _hw.copyImage('{old_url}', n);"
        # Saved with that photo: Save names it (07 Q2, GL-174).
        " _hw.save(n, JSON.stringify({kind: 'control.hardware',"
        f" device: n, nodes: [{bg('r')}, {a1}]}}))",
    )
    _js(
        win,
        "_hw.save('Stick B', JSON.stringify({kind: 'control.hardware',"
        " device: 'Stick B', nodes: []}))",
    )
    _js(win, crash)

    state_a = (
        "'copyA:' + (_hw.loadRecovery('Stick A').length > 0)"
        " + ' stashA:' + _hw.editActive('Stick A')"
    )
    _js(win, "_editorWin.openForDevice('Stick A', ''); 1")
    _wait(500)
    _Out.result("offer-a", _js(win, "String(_recoverGate.opened)"))
    # Home: Stick B's Device Mapping Editor, with the offer still open.
    _js(win, "_editorWin.openForDevice('Stick B', ''); 1")
    _wait(500)
    _Out.result(
        "switched",
        _js(
            win,
            "'gate:' + _recoverGate.opened"
            " + ' pending:' + (_editorWin._pendingRecovery !== null)"
            f" + ' ' + {state_a}",
        ),
    )
    _js(win, "_editorWin.restoreRecovery(); 1")
    _wait(200)
    _Out.result("restore-on-b", _js(win, "'editing:' + _editorWin.editing"))
    _js(win, "_editorWin.discardEdit(); 1")
    _wait(200)

    # Which photo shows: the saved map's bottom background picture (07
    # S127), by its file's colour (copyImage keeps one name).
    photo_file = "_hw.profilePhotoUrl('Stick A')"

    def photo_colour() -> str:
        url = _js(win, photo_file)
        image = QtGui.QImage(QtCore.QUrl(url).toLocalFile())
        if image.isNull():
            return "none"
        name = image.pixelColor(2, 2).name()
        return {"#993366": "new", "#336699": "old"}.get(name, name)

    _js(win, "_editorWin.openForDevice('Stick A', ''); 1")
    _wait(500)
    _Out.result("offer-a-again", _js(win, "String(_recoverGate.opened)"))
    # Not now.
    _js(win, "_recoverGate.close(); 1")
    _wait(300)
    _Out.result("not-now", _js(win, state_a) + " photo:" + photo_colour())
    # Edit after Not now: the edits are offered again, not a new session
    # (its recovery copy wrote over the copy and its Cancel deleted copy and
    # photo).
    edit = _js(
        win,
        "_editorWin.enterEdit();"
        " 'gate:' + _recoverGate.opened + ' editing:' + _editorWin.editing",
    )
    _js(
        win,
        "_recoverGate.close(); _editorWin.recoveryNow(); _editorWin.discardEdit(); 1",
    )
    _wait(300)
    _Out.result(
        "edit-offers", edit + " " + _js(win, state_a) + " photo:" + photo_colour()
    )
    # Opened again: offered again; Discard.
    _js(win, "_editorWin.offerRecovery(); 1")
    _wait(300)
    _js(
        win,
        "_recoverGate._choice = 'discard'; _recoverGate.close();"
        " _recoverGate.discarded(); 1",
    )
    _wait(300)
    _Out.result("discard", _js(win, state_a) + " photo:" + photo_colour())
    # The same again, then Blank Device Mapping Editor with the offer open.
    new_ref = _js(win, crash)
    _js(win, "_editorWin.offerRecovery(); 1")
    _wait(300)
    _js(win, "_editorWin.openBlank(); 1")
    _wait(300)
    _Out.result("blank", _js(win, f"'gate:' + _recoverGate.opened + ' ' + {state_a}"))

    # Back on A (Not now). A copy that only changed the photo (the new one
    # waits in the edit under its own name, 07 S107) is still offered (it
    # was deleted and the old photo put back).
    _js(win, "_editorWin.openForDevice('Stick A', ''); 1")
    _wait(500)
    _js(win, "_recoverGate.close(); 1")
    _wait(200)
    _js(
        win,
        f"_hw.saveRecovery('Stick A', JSON.stringify({{nodes: [{bg(repr(new_ref))}]"
        ".concat(_editorWin.liveNodes.filter(function(n) {"
        " return n.plane !== 'background' }))})); 1",
    )
    offered = _js(win, "String(_editorWin.offerRecovery())")
    _Out.result(
        "photo-only",
        f"offered:{offered} gate:"
        + _js(win, "String(_recoverGate.opened)")
        + " "
        + _js(win, state_a),
    )
    _js(win, "_recoverGate.close(); 1")
    _wait(200)
    # The stick was renamed since the crash: its copy (in its device folder,
    # 07 S32) names the old name. Restore opens it; Cancel then removes the
    # copy and puts the saved photo back.
    from gremlin.modules import store

    copies = [
        p
        for p in [store.recovery_path("Stick A")]
        if p.is_file()
        and json.loads(p.read_text(encoding="utf-8")).get("device") == "Stick A"
    ]

    if not copies:
        print("ERROR renamed: Stick A's recovery copy is gone", flush=True)

        _report(warnings)
    copy = copies[0]
    doc = json.loads(copy.read_text(encoding="utf-8"))
    doc["device"] = "Old Stick A"
    doc["nodes"] = doc["nodes"] + [
        {
            "id": "a2",
            "kind": "draw",
            "shape": "rect",
            "fx": 0.4,
            "fy": 0.4,
            "fw": 0.1,
            "fh": 0.1,
        }
    ]
    copy.write_text(json.dumps(doc), encoding="utf-8")
    _js(win, "_editorWin.offerRecovery(); _editorWin.restoreRecovery(); 1")
    _wait(400)
    restored = _js(
        win,
        "'editing:' + _editorWin.editing + ' a2:'"
        " + _editorWin.workNodes.some(function(n) {"
        " return n.id === 'a2' })",
    )
    _js(win, "_recoverGate.close(); _editorWin.discardEdit(); 1")
    _wait(300)
    _Out.result(
        "renamed", restored + " " + _js(win, state_a) + " photo:" + photo_colour()
    )

    # 21: a picture on the clipboard, then chips copied on Stick B; Ctrl+V
    # on Stick C pastes the chips.
    _js(
        win,
        "_hw.save('Stick C', JSON.stringify({kind: 'control.hardware',"
        " device: 'Stick C', nodes: []}))",
    )
    mime = QtCore.QMimeData()
    mime.setUrls([QtCore.QUrl(old_url)])
    QtGui.QGuiApplication.clipboard().setMimeData(mime)
    _wait(300)
    _js(win, "_editorWin.openForDevice('Stick B', ''); 1")
    _wait(500)
    _js(
        win,
        "_editorWin.enterEdit(); var e = _ed();"
        " e.nodes.push({id: 'c1', kind: 'btn', hwId: 1, chipFx: 0.3, chipFy: 0.3,"
        " hotFx: 0.35, hotFy: 0.35}); e.bump(); e.setSelection(['c1']);"
        " e.copySelection(); 1",
    )
    _wait(300)
    kept = _js(win, "String(_editorWin.keptCopySerial === _hw.clipboardSerial)")
    _js(win, "_editorWin.discardEdit(); _editorWin.openForDevice('Stick C', ''); 1")
    _wait(500)
    _js(win, "_editorWin.enterEdit(); 1")
    _wait(400)
    pasted = _js(
        win,
        "var e = _ed(); var before = e.nodes.length; e.pasteClipboard();"
        " var n = e.nodeAt(e.selectedId);"
        " (e.nodes.length - before) + ' ' + (n ? n.kind : '-')",
    )
    _Out.result("carry", f"kept:{kept} pasted:{pasted}")
    _js(win, "_editorWin.discardEdit(); 1")
    _wait(300)

    # 22: a table, a chip on it and a text beside it; chip and text chosen.
    _js(
        win,
        "_editorWin.enterEdit(); var e = _ed();"
        " e.nodes.push({id: 't1', kind: 'draw', shape: 'table',"
        " fx: 0.2, fy: 0.2, fw: 0.5, fh: 0.5});"
        " e.nodes.push({id: 'c2', kind: 'btn', hwId: 2, chipFx: 0.4, chipFy: 0.4,"
        " hotFx: 0.8, hotFy: 0.8});"
        " e.nodes.push({id: 'x1', kind: 'draw', shape: 'text', text: 'Hi',"
        " fx: 0.8, fy: 0.1, fw: 0.1, fh: 0.05}); e.bump(); 1",
    )
    _wait(500)
    _Out.result(
        "group-table-text",
        _js(win, "var e = _ed(); e.setSelection(['c2', 'x1']); String(e.canGroup())"),
    )
    _Out.result(
        "group-drawings",
        _js(
            win,
            "var e = _ed(); e.nodes.push({id: 'd9', kind: 'draw', shape: 'rect',"
            " fx: 0.05, fy: 0.85, fw: 0.05, fh: 0.05}); e.bump();"
            " e.setSelection(['x1', 'd9']); String(e.canGroup())",
        ),
    )
    # Ctrl+G (as its Shortcut: only when canGroup) on two tables, and on a
    # table with only a drawing: says why nothing was grouped.
    ctrl_g = (
        "String(e.canGroup()) + ':'"
        " + (e.canGroup() ? (e.groupSelection(), e.packWarn) : '')"
    )
    _Out.result(
        "group-two-tables",
        _js(
            win,
            "var e = _ed(); e.nodes.push({id: 't2', kind: 'draw', shape: 'table',"
            " fx: 0.75, fy: 0.75, fw: 0.2, fh: 0.2}); e.bump();"
            f" e.setSelection(['t1', 't2']); {ctrl_g}",
        ),
    )
    _Out.result(
        "group-table-drawing",
        _js(
            win,
            f"var e = _ed(); e.packWarn = ''; e.setSelection(['t1', 'd9']); {ctrl_g}",
        ),
    )
    _js(win, "_editorWin.discardEdit(); 1")
    _report(warnings)


def _keyboard(out: pathlib.Path) -> None:
    from PySide6 import QtCore

    app, engine, warnings = _engine(out)  # noqa: F841
    import dill
    import gremlin.ui.device  # noqa: F401
    import gremlin.ui.keyboard_layout  # noqa: F401
    import gremlin.ui.util  # noqa: F401
    from gremlin import plugin_manager, shared_state
    from gremlin.profile import Profile
    from gremlin.ui.backend import UIState

    plugin_manager.PluginManager()  # the action editors' QML types (the pane)
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
    width: 900; height: 700; visible: true
    property alias page: _page
    QtObject { id: bsi; property var icons: ({ remove: "x", verticalDrag: "=" }) }
    KeyboardPage { id: _page; anchors.fill: parent }
}
""",
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "Root.qml")),
    )
    if not engine.rootObjects():
        for warning in warnings:
            print("WARN " + warning.encode("ascii", "replace").decode(), flush=True)
        raise RuntimeError("KeyboardPage did not load")
    win = engine.rootObjects()[0]
    _wait(400)

    from PySide6 import QtQml

    from gremlin.event_handler import Event
    from gremlin.types import InputType
    from gremlin.ui.util import InputListenerModel

    context = QtQml.qmlContext(win)
    model = QtQml.QQmlExpression(context, win, "page.layoutModel").evaluate()[0]
    add_key = win.findChildren(InputListenerModel)[0]

    def press(code: int) -> list:
        return [Event(InputType.Keyboard, (code, False), dill.UUID_Keyboard, "Default")]

    # The selected row's name, then the pane's.
    shown = "page.layoutModel.selectionLabel + ' ' + page.paneTitle"
    # Add Key, as its listener hands over a pressed S, then A.
    add_key.listeningTerminated.emit(press(31))  # S
    _wait(300)
    _Out.result("picked", _js(win, shown))
    add_key.listeningTerminated.emit(press(30))  # A
    _wait(300)
    _Out.result("added", _js(win, shown))
    # Two keys added from elsewhere.
    model.addKey(press(16), "Default")  # Q
    model.addKey(press(17), "Default")  # W
    _wait(300)
    _Out.result("moved", _js(win, shown))
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
    _Out.result(
        "other-shown", _js(win, f"other.filterText = '{needle}'; String(other.visible)")
    )
    word = title.split()[0].lower()
    _Out.result(
        "titled-shown",
        _js(win, f"titled.filterText = '{word}'; String(titled.visible)"),
    )
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
        parts = {
            "editor": _device_mapping_editor,
            "keyboard": _keyboard,
            "options": _options,
        }
        parts[_part](_out_dir)
    except Exception as failed:  # noqa: BLE001 (said, then the process ends)
        import traceback

        traceback.print_exc()
        print(f"ERROR {_part}: {failed!r}", flush=True)
        os._exit(1)
