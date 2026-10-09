# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""01 S143, D-01-SHARED-PIECES: every file and folder chooser opens in the
last folder used for that kind of file, remembered between sessions in the
program settings (global/internal "last-folders").

The settings file is a temporary one; the dialogs are never shown (the
picker is set up with prepare() and the dialog's accepted signal is driven).
"""

from __future__ import annotations

import sys

sys.path.append(".")

import json
import pathlib
from collections.abc import Iterator

import pytest
from PySide6 import QtCore, QtQml

import gremlin.config
from gremlin import deferred_write
from gremlin.common import SingletonMetaclass
from gremlin.ui import folder_memory

_ROOT = pathlib.Path(__file__).parents[2]


@pytest.fixture
def settings_file(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[pathlib.Path]:
    path = tmp_path / "configuration.json"
    monkeypatch.setattr(gremlin.config, "_config_file_path", str(path))
    monkeypatch.setattr(gremlin.config, "_damaged_copy", "")
    monkeypatch.setattr(deferred_write, "_scheduler", lambda: None)
    SingletonMetaclass._instances.pop(gremlin.config.Configuration, None)
    yield path
    SingletonMetaclass._instances.pop(gremlin.config.Configuration, None)


def _url(path: pathlib.Path) -> str:
    return QtCore.QUrl.fromLocalFile(str(path)).toString()


def _new_session() -> None:
    deferred_write.flush("configuration")
    SingletonMetaclass._instances.pop(gremlin.config.Configuration, None)


def test_each_kind_keeps_its_own_folder(
    settings_file: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    packs = tmp_path / "packs"
    pictures = tmp_path / "pictures"
    packs.mkdir()
    pictures.mkdir()
    memory = folder_memory.FolderMemory()
    assert memory.lastFolder("device-pack") == ""

    # A picked file: its folder is kept. A picked folder: itself.
    assert memory.remember("device-pack", _url(packs / "stick.zip"))
    assert memory.remember("picture", _url(pictures))

    assert memory.lastFolder("device-pack") == _url(packs)
    assert memory.lastFolder("picture") == _url(pictures)
    assert memory.lastFolder("profile") == ""


def test_the_folders_survive_a_new_session(
    settings_file: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    folder_memory.remember("script", _url(scripts / "new.py"))
    _new_session()

    assert settings_file.is_file()
    assert folder_memory.FolderMemory().lastFolder("script") == _url(scripts)


def test_an_unknown_kind_gives_the_default(
    settings_file: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    memory = folder_memory.FolderMemory()
    assert not memory.remember("nonsense", _url(tmp_path))
    assert memory.lastFolder("nonsense") == ""


def test_a_folder_that_is_gone_gives_the_default(
    settings_file: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    logs = tmp_path / "logs"
    logs.mkdir()
    memory = folder_memory.FolderMemory()
    memory.remember("log", _url(logs))
    logs.rmdir()
    assert memory.lastFolder("log") == ""


_kept: list[QtQml.QQmlComponent] = []


def _picker(engine: QtQml.QQmlEngine, body: str) -> QtCore.QObject:
    source = (
        "import QtQuick\n"
        f'import "{_url(_ROOT / "qml")}"\n'
        f'Item {{ FilePicker {{ objectName: "picker"\n {body} }} }}\n'
    )
    component = QtQml.QQmlComponent(engine)
    base = QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "x.qml"))
    component.setData(source.encode(), base)
    root = component.create()
    assert root is not None, component.errorString()
    QtQml.QQmlEngine.setObjectOwnership(
        root, QtQml.QQmlEngine.ObjectOwnership.CppOwnership
    )
    _kept.append(component)
    return root


def _call(obj: QtCore.QObject, code: str) -> object:
    expression = QtQml.QQmlExpression(QtQml.qmlContext(obj), obj, code)
    value, _undefined = expression.evaluate()
    assert not expression.hasError(), expression.error().toString()
    return value


def test_file_picker_opens_in_the_remembered_folder_and_remembers_the_pick(
    qapp: object, settings_file: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    given = tmp_path / "given"
    last = tmp_path / "last"
    chosen = tmp_path / "chosen"
    for folder in (given, last, chosen):
        folder.mkdir()
    engine = QtQml.QQmlEngine()
    root = _picker(
        engine,
        f'kind: "device-pack"; mode: "open"; folder: "{_url(given)}"\n'
        "property var got: []\n onPicked: (u) => got.push(String(u))",
    )
    picker = root.findChild(QtCore.QObject, "picker")
    dialog = picker.findChild(QtCore.QObject, "filePickerFileDialog")

    # Nothing remembered yet: the given folder.
    _call(picker, "prepare()")
    assert dialog.property("currentFolder").toString() == _url(given)

    folder_memory.remember("device-pack", _url(last))
    _call(picker, "prepare()")
    assert dialog.property("currentFolder").toString() == _url(last)

    # The user picks a file in another folder: that folder is kept.
    (chosen / "pack.zip").write_bytes(b"")
    pick = _url(chosen / "pack.zip")
    _call(dialog, f'selectedFile = "{pick}"; accepted()')
    got = _call(picker, "JSON.stringify(got)")
    assert got == json.dumps([pick], separators=(",", ":"))
    assert folder_memory.FolderMemory().lastFolder("device-pack") == _url(chosen)
    _call(picker, "prepare()")
    assert dialog.property("currentFolder").toString() == _url(chosen)
    root.deleteLater()


def test_folder_picker_remembers_the_chosen_folder(
    qapp: object, settings_file: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    chosen = tmp_path / "exports"
    chosen.mkdir()
    engine = QtQml.QQmlEngine()
    root = _picker(engine, 'kind: "export"; mode: "folder"')
    picker = root.findChild(QtCore.QObject, "picker")
    dialog = picker.findChild(QtCore.QObject, "filePickerFolderDialog")

    # The user goes to a folder and accepts it. (Without a shown dialog Qt
    # keeps no selectedFolder; the picker then takes the folder shown.)
    _call(picker, "prepare()")
    _call(dialog, f'currentFolder = "{_url(chosen)}"; accepted()')
    assert folder_memory.FolderMemory().lastFolder("export") == _url(chosen)
    _call(picker, "prepare()")
    assert dialog.property("currentFolder").toString() == _url(chosen)
    root.deleteLater()


def test_save_picker_suggests_the_name_in_the_remembered_folder(
    qapp: object, settings_file: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    last = tmp_path / "exports"
    last.mkdir()
    folder_memory.remember("export", _url(last))
    engine = QtQml.QQmlEngine()
    root = _picker(
        engine,
        f'kind: "export"; mode: "save"; currentFile: "{_url(tmp_path / "Stick.zip")}"',
    )
    picker = root.findChild(QtCore.QObject, "picker")
    dialog = picker.findChild(QtCore.QObject, "filePickerFileDialog")

    _call(picker, "prepare()")
    assert dialog.property("currentFolder").toString() == _url(last)
    assert _call(dialog, "String(selectedFile)") == _url(last / "Stick.zip")
    root.deleteLater()


def test_save_picker_keeps_a_bare_name_with_nothing_remembered(
    qapp: object, settings_file: pathlib.Path
) -> None:
    # The Device Library's first export passes only "Left.zip": the name is
    # still suggested (in Documents) rather than dropped.
    engine = QtQml.QQmlEngine()
    root = _picker(engine, 'kind: "device-pack"; mode: "save"; currentFile: "Left.zip"')
    picker = root.findChild(QtCore.QObject, "picker")
    dialog = picker.findChild(QtCore.QObject, "filePickerFileDialog")

    _call(picker, "prepare()")
    assert str(_call(dialog, "String(selectedFile)")).endswith("/Left.zip")
    root.deleteLater()
