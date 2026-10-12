# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Module Setup and Home with device folders (D-03-DEVICE-FOLDERS).

03 S54: Module Setup names the device's folder, "(not saved yet)" without a
module file. S58: "Import from" lists the other devices' folders and keeps
the previous file in the device's own imported/. S52: Import Image copies
into the device's pictures/. S92: Delete Device removes the whole folder.
08 S111: the card menu has Export Device… and Import Device….
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
from collections.abc import Iterator
from pathlib import Path

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)
from PySide6 import QtCore

from gremlin import config, device_initialization
from gremlin.modules import store
from gremlin.ui import module_model

_HERE = pathlib.Path(__file__).parent
_ROOT = _HERE.parents[1]
_CLAIM = {"buttons": [1], "axes": [], "hats": [], "keys": []}
_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32 + b"\xff\xd9"


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    yield app


_DISPLAY_KEYS = (
    module_model._CFG_HIDDEN,
    module_model._CFG_ORDER,
    module_model._CFG_STACKS,
    module_model._CFG_SIZES,
    module_model._CFG_COMPACT,
    module_model._CFG_SPLIT,
    module_model._CFG_KEPT_STUBS,
    module_model._CFG_SHOW_STUBS,
)


@pytest.fixture
def modules(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    """A tmp modules folder; the Home card settings (Delete Device keeps the
    stick's card in kept-stubs, 03 S94a) are put back afterwards."""
    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(store, "folder", lambda: folder)
    store._dirs_changed()
    module_model._ensure_display_options()
    cfg = config.Configuration()
    sec, grp = module_model._CFG_SECTION, module_model._CFG_GROUP
    display = {key: cfg.value(sec, grp, key) for key in _DISPLAY_KEYS}
    yield folder
    for key, value in display.items():
        cfg.set(sec, grp, key, value)
    store._dirs_changed()


def _pjoy_guid() -> str:
    dev = next(
        d for d in device_initialization.physical_devices() if d.name == "pJoy Pro"
    )
    return str(dev.device_guid)


def _save(name: str, guid: str, doc: dict) -> Path:
    """A device's folder with its device.json and module.json."""
    path = store.module_file_in(store.ensure_device_dir(name, guid))
    path.write_text(json.dumps(doc), encoding="utf-8")
    store._dirs_changed()
    return path


def _stick(name: str) -> dict:
    return {
        "kind": "control.hardware",
        "device": name,
        "direction": "source",
        "claim": _CLAIM,
    }


# --- 03 S54: the label --------------------------------------------------------


def test_label_is_the_folder_name_or_not_saved_yet(modules: Path) -> None:
    guid = _pjoy_guid()
    model = module_model.ModuleListModel()
    assert not model.moduleFileExists(guid, "pJoy Pro")
    _save("pJoy Pro", guid, _stick("pJoy Pro"))
    # Old: "pjoy_pro" (the file's slug), shown as "pjoy_pro.json".
    assert model.moduleFileFor(guid, "pJoy Pro") == "pJoy Pro"
    assert model.moduleFileExists(guid, "pJoy Pro")
    assert (modules / "pJoy Pro" / "module.json").is_file()


def test_module_setup_shows_the_folder_and_no_file_notice() -> None:
    qml = (_ROOT / "qml" / "DialogConfigureModule.qml").read_text(encoding="utf-8")
    assert (
        'moduleFileLabel = saved && folder.length ? folder : "(not saved yet)"' in qml
    )
    # The foreign-file notice and the built ".json" names are gone.
    assert "foreignModuleFile" not in qml
    assert "still opens" not in qml
    assert '+ ".json"' not in qml
    # Import Image goes through the window's "setup" edit (SETUP-PHOTO).
    assert "_win.importPhoto(String(selected))" in qml
    assert "importedFolderUrl(deviceGuid, deviceName)" in qml


# --- 03 S58: Import from another device's folder ---------------------------


def test_import_from_another_folder_keeps_the_previous_file(modules: Path) -> None:
    guid = _pjoy_guid()
    mine = _save("pJoy Pro", guid, _stick("pJoy Pro") | {"note": "mine"})
    previous = mine.read_bytes()
    other = modules / "Other Stick"
    other.mkdir()
    (other / store.ID_FILE).write_text(
        json.dumps({"format": 1, "id": "name:other_stick", "name": "Other Stick"}),
        encoding="utf-8",
    )
    (other / store.MODULE_FILE).write_text(
        json.dumps(_stick("Other Stick") | {"note": "theirs"}), encoding="utf-8"
    )
    store._dirs_changed()
    model = module_model.ModuleListModel()
    choices = model.moduleFileNames(guid, "pJoy Pro")
    assert "Other Stick" in choices and "pJoy Pro" not in choices

    message = model.importModuleFile(guid, "pJoy Pro", "Other Stick", "source")
    assert message.startswith("Imported "), message
    assert json.loads(mine.read_text(encoding="utf-8")).get("note") == "theirs"
    kept = list((modules / "pJoy Pro" / "imported").glob("module*.json"))
    assert len(kept) == 1 and kept[0].read_bytes() == previous
    # Nothing lands in a shared modules/imported folder.
    assert not (modules / "imported").exists()
    # The chosen device's file is left as it was.
    assert json.loads((other / "module.json").read_text())["note"] == "theirs"


# --- 03 S52: Import Image ---------------------------------------------------


def test_import_image_lands_in_the_device_pictures(
    modules: Path, tmp_path: Path
) -> None:
    guid = _pjoy_guid()
    _save("pJoy Pro", guid, _stick("pJoy Pro"))
    src = tmp_path / "pick" / "shot.jpg"
    src.parent.mkdir()
    src.write_bytes(_JPEG)
    dest = modules / "pJoy Pro" / "pictures" / "photo.jpg"
    assert (
        module_model.import_photo("pJoy Pro", guid, src.as_uri())
        == "pictures/photo.jpg"
    )
    assert dest.read_bytes() == _JPEG
    # A new picture of another type replaces the old photo.
    png = src.with_name("shot.png")
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
    assert (
        module_model.import_photo("pJoy Pro", guid, png.as_uri())
        == "pictures/photo.png"
    )
    assert not dest.exists()
    # The module file is written by the window's Save, not here.
    assert "image" not in json.loads((modules / "pJoy Pro" / "module.json").read_text())


# --- 03 S92: Delete Device ----------------------------------------------------


def test_delete_device_removes_the_whole_folder(modules: Path) -> None:
    guid = _pjoy_guid()
    _save("pJoy Pro", guid, _stick("pJoy Pro"))
    folder = modules / "pJoy Pro"
    (folder / "pictures").mkdir()
    (folder / "pictures" / "photo.jpg").write_bytes(_JPEG)
    (folder / "recovery.json").write_text("{}", encoding="utf-8")
    model = module_model.ModuleListModel()
    result = json.loads(model.deleteDevice("pJoy Pro", guid))
    assert result["ok"], result
    assert not folder.exists()


def test_delete_device_text_has_no_shared_file() -> None:
    page = (_ROOT / "qml" / "StatusPage.qml").read_text(encoding="utf-8")
    assert "_deleteForeign" not in page and "_deleteShared" not in page
    assert "another device uses it" not in page
    assert "removes this device's folder" in page


# --- 08 S111: Export Device… / Import Device… on the card --------------------

_OPEN_DEVICE = (
    "_probe.close(); _probe.build = _card.menuModel; _probe.openAt(_card, 20, 20);"
    " if (_probe.describe().indexOf('> Device') >= 0) _probe.activate('Device');"
    " _probe.describe().join('|')"
)

_STEPS = [
    (
        "connect",
        "_card.exportDevice.connect(function() { _win.ran = 'export' });"
        " _card.importDevice.connect(function() { _win.ran = 'import' }); 'ok'",
    ),
    (
        "saved",
        "_card.slug = 'pjoy_pro'; _card.tab = 'physical'; _card.bus = 'DirectInput';"
        " _card.isModule = true; " + _OPEN_DEVICE,
    ),
    ("export-runs", "_win.ran = ''; _probe.activate('Export Device…'); _win.ran"),
    (
        "import-runs",
        _OPEN_DEVICE.replace("_probe.describe().join('|')", "")
        + " _win.ran = ''; _probe.activate('Import Device…'); _win.ran",
    ),
    ("unsaved", "_card.isModule = false; " + _OPEN_DEVICE),
    ("closed", "_probe.close(); 'ok'"),
]

_RUNNER = (
    "import sys, importlib.util\n"
    "spec = importlib.util.spec_from_file_location('menus_smoke', sys.argv[1])\n"
    "mod = importlib.util.module_from_spec(spec)\n"
    "spec.loader.exec_module(mod)\n"
    f"mod.STEPS = {_STEPS!r}\n"
    "sys.argv = [sys.argv[0], sys.argv[2]]\n"
    "mod.main()\n"
)


def test_card_menu_has_export_and_import_device(tmp_path: Path) -> None:
    result = proc_tree.run(
        [sys.executable, "-c", _RUNNER, str(_HERE / "menus_smoke.py"), str(tmp_path)],
        text=True,
        encoding="utf-8",
        timeout=120,
        env={
            **os.environ,
            "QT_QPA_PLATFORM": "offscreen",
            "PYTHONIOENCODING": "utf-8",
            "USERPROFILE": str(tmp_path),
        },
    )
    lines = result.stdout.splitlines()
    assert "done" in lines, smoke_report.explain(result)
    assert [line for line in lines if line.startswith("ERROR")] == []
    results = {
        line.split(" ", 2)[1]: line.split(" ", 2)[2]
        for line in lines
        if line.startswith("RESULT ") and line.count(" ") >= 2
    }
    saved = results["saved"].split("|")
    assert "  Export Device…" in saved and "  Import Device…" in saved
    assert results["export-runs"] == "export"
    assert results["import-runs"] == "import"
    # No module file yet: nothing to export (an item that can't be used
    # isn't shown).
    unsaved = results["unsaved"].split("|")
    assert not any(row.startswith("  Export Device") for row in unsaved)
    assert "  Import Device…" in unsaved


def test_home_page_opens_the_export_import_window() -> None:
    page = (_ROOT / "qml" / "StatusPage.qml").read_text(encoding="utf-8")
    assert (
        "card.onExportDevice.connect(function() { _page.exportDevice(card) })" in page
    )
    assert (
        "card.onImportDevice.connect(function() { _page.importDevice(card) })" in page
    )
    # One window for both (D-FIXLIST-B2): DialogDevicePack.qml on the
    # card's tab and device (test_b2_card drives it).
    assert '_openExportImport("export", card)' in page
    assert '_openExportImport("import", card)' in page
    assert 'Helpers.createComponent("DialogDevicePack.qml"' in page
    assert "DialogDeviceExport" not in page
