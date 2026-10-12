# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Module Setup's Device Image and the device's photo (D-03-DEVICE-IMAGE;
03 S52, 07 S127, 08 S107).

An input module's Add Image… / Change Image… / Remove Image in Module Setup
wait in the window's edit until Save and set or drop the module file's
deviceImage; the device map is not touched. The device's photo is the
device image first; an unnamed pictures/photo.* is never shown. The Device
Mapping Editor's Save never writes the device image key. Export's preview
shows the shown photo, not the bottom background picture.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import pytest

from gremlin.modules import module_file, store
from gremlin.ui import device_photo, hardware_profile
from test.unit._device_folders import put_module

sys.path.append(str(pathlib.Path(__file__).parent.parent))
import proc_tree  # noqa: E402  # pyright: ignore[reportMissingImports]  (test/)
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

_ROOT = pathlib.Path(__file__).parents[2]
_PNG = b"\x89PNG\r\n\x1a\n" + b"\x03" * 24
_JPG = b"\xff\xd8\xff\xe0" + b"\x01" * 32 + b"\xff\xd9"
_BG = {
    "id": "bg",
    "kind": "draw",
    "shape": "image",
    "plane": "background",
    "src": "pictures/photo.jpg",
}


@pytest.fixture
def maps(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> pathlib.Path:
    modules = tmp_path / "modules"
    modules.mkdir()
    monkeypatch.setattr(store, "folder", lambda: modules)
    # Asking for the photo may ask for the background picture to be made.
    wanted: list = []
    monkeypatch.setattr(device_photo, "want", lambda *a, **k: wanted.append(a))
    return modules


def _stick(maps: pathlib.Path, doc: dict, pictures: dict[str, bytes]) -> pathlib.Path:
    path = put_module(
        maps, "Stick R", {"device": "Stick R", "direction": "source", **doc}
    )
    (path.parent / "pictures").mkdir(exist_ok=True)
    for name, data in pictures.items():
        (path.parent / "pictures" / name).write_bytes(data)
    return path


def _file(url: str) -> str:
    return url.split("?")[0].rsplit("/", 1)[-1]


def test_the_photo_is_the_device_image_and_without_it_the_background(
    maps: pathlib.Path,
) -> None:
    _stick(
        maps,
        {"nodes": [_BG], "deviceImage": "pictures/device-image.png"},
        {"photo.jpg": _JPG, "device-image.png": _PNG},
    )
    hw = hardware_profile.HardwareProfile()
    assert _file(hw.profilePhotoUrl("Stick R")) == "device-image.png"
    assert hw.hasDeviceImage("Stick R")
    # Remove Image's preview in Module Setup: the photo without the image.
    assert _file(hw.generatedPhotoUrl("Stick R")) == "photo.jpg"


def test_an_unnamed_old_photo_file_is_not_shown(maps: pathlib.Path) -> None:
    # Old: profilePhotoUrl fell back to any pictures/photo.* by glob.
    _stick(maps, {"nodes": []}, {"photo.jpg": _JPG})
    hw = hardware_profile.HardwareProfile()
    assert hw.profilePhotoUrl("Stick R") == ""
    assert not hw.hasDeviceImage("Stick R")


def test_a_named_image_whose_file_is_gone_is_not_an_image(maps: pathlib.Path) -> None:
    _stick(
        maps,
        {"nodes": [_BG], "deviceImage": "pictures/device-image.png"},
        {"photo.jpg": _JPG},
    )
    hw = hardware_profile.HardwareProfile()
    assert not hw.hasDeviceImage("Stick R")
    assert _file(hw.profilePhotoUrl("Stick R")) == "photo.jpg"


def test_keep_image_waits_in_the_edit_as_device_image(maps: pathlib.Path) -> None:
    path = _stick(maps, {"nodes": [_BG]}, {"photo.jpg": _JPG})
    pick = maps.parent / "pick" / "shot.png"
    pick.parent.mkdir()
    pick.write_bytes(_PNG)
    hw = hardware_profile.HardwareProfile()
    hw.beginEditFor("Stick R", "setup")
    ref = hw.keepImage("Stick R", pick.as_uri())
    assert ref == "pictures/device-image.png"
    # The device's folder is untouched until Save (07 S107).
    assert sorted(p.name for p in (path.parent / "pictures").iterdir()) == ["photo.jpg"]
    assert hw.imageUrl(ref).startswith("file:")
    hw.cancelEditFor("Stick R", "setup")
    assert not (path.parent / "pictures" / "device-image.png").exists()


def test_keep_image_refuses_a_damaged_module_file(
    maps: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    put_module(maps, "Stick R", "{ damaged")
    told: list = []
    monkeypatch.setattr(module_file, "report_refused", lambda d: told.append(d))
    pick = maps.parent / "shot.png"
    pick.write_bytes(_PNG)
    hw = hardware_profile.HardwareProfile()
    hw.beginEditFor("Stick R", "setup")
    assert hw.keepImage("Stick R", pick.as_uri()) == ""
    hw.cancelEditFor("Stick R", "setup")
    assert len(told) == 1


@pytest.mark.parametrize(
    ("on_disk", "in_editor", "kept"),
    [
        # Removed on Home while the editor was open: its Save doesn't bring
        # it back.
        (None, "pictures/device-image.png", None),
        # Changed on Home while the editor was open: the new one stays.
        ("pictures/device-image_1.png", "pictures/device-image.png",
         "pictures/device-image_1.png"),
        ("pictures/device-image.png", None, "pictures/device-image.png"),
    ],
)
def test_the_editors_save_never_writes_the_device_image(
    maps: pathlib.Path, on_disk: str | None, in_editor: str | None, kept: str | None
) -> None:
    doc: dict = {"nodes": [_BG]}
    if on_disk:
        doc["deviceImage"] = on_disk
    path = _stick(
        maps,
        doc,
        {"photo.jpg": _JPG, "device-image.png": _PNG, "device-image_1.png": _PNG},
    )
    payload: dict = {"kind": "control.hardware", "device": "Stick R", "nodes": [_BG]}
    if in_editor:
        payload["deviceImage"] = in_editor
    assert hardware_profile.HardwareProfile().save("Stick R", json.dumps(payload))
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved.get("deviceImage") == kept


def test_export_preview_shows_the_device_image(maps: pathlib.Path) -> None:
    # Old: the bottom background picture (08 S107 gap).
    _stick(
        maps,
        {"nodes": [_BG], "deviceImage": "pictures/device-image.png"},
        {"photo.jpg": _JPG, "device-image.png": _PNG},
    )
    peek = json.loads(
        hardware_profile.HardwareProfile().peekPackDeviceById("Stick R", "")
    )
    assert peek["ok"], peek
    assert _file(peek["photoUrl"]) == "device-image.png"


def test_module_setup_finishing_its_edit_sets_no_background_picture(
    maps: pathlib.Path,
) -> None:
    # Old: commitEditFor made an Import Image's picture the bottom
    # background picture; saveClaim is the one writer now.
    path = _stick(maps, {"nodes": []}, {})
    pick = maps.parent / "shot.png"
    pick.write_bytes(_PNG)
    hw = hardware_profile.HardwareProfile()
    hw.beginEditFor("Stick R", "setup")
    assert hw.copyImage(pick.as_uri(), "Stick R")
    assert hw.commitEditFor("Stick R", "setup") == ""
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["nodes"] == []
    assert store.device_photo_ref(saved) == ""


# --- the real Module Setup window, off-screen, in its own process ----------

_CODE = r"""
import json, os, sys
ROOT, PICK = sys.argv[1], sys.argv[2]
sys.path.insert(0, ROOT)
import importlib.util
spec = importlib.util.spec_from_file_location(
    'fake_hardware', os.path.join(ROOT, 'test', 'fake_hardware.py'))
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()
from gremlin.ui import ui_scale_option
ui_scale_option.active_scale = lambda: 100
import gremlin.ui.update_model as um
um.UpdateModel.startup = lambda self, *a, **k: None
import joystick_gremlin
from gremlin import history
from gremlin.modules import store
from PySide6 import QtCore, QtQml, QtQuick, QtTest
sys.path.insert(0, os.path.join(ROOT, 'test'))
from qt_wait import wait_until
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window

def run(target, code):
    expr = QtQml.QQmlExpression(QtQml.qmlContext(target), target, code)
    value = expr.evaluate()
    assert not expr.hasError(), expr.error().toString()
    return value[0] if isinstance(value, tuple) else value

before = set(app.topLevelWindows())
run(win, '_root.openConfigureModule("source", null)')
w = wait_until(lambda: next(
    (x for x in app.topLevelWindows()
     if x not in before and isinstance(x, QtQuick.QQuickWindow) and x.isVisible()),
    None), 'the Module Setup window')
name, guid = w.property('deviceName'), w.property('deviceGuid')

OLD = b'\xff\xd8\xff\xe0' + b'\x01' * 32 + b'\xff\xd9'
folder = store.ensure_device_dir(name, guid)
module = store.module_file_in(folder)
(folder / 'pictures').mkdir(exist_ok=True)
(folder / 'pictures' / 'photo.jpg').write_bytes(OLD)
NODES = [{'id': 'bg', 'kind': 'draw', 'shape': 'image',
          'plane': 'background', 'src': 'pictures/photo.jpg'}]
module.write_text(json.dumps({
    'kind': 'control.hardware', 'device': name, 'direction': 'source',
    'nodes': NODES,
    'claim': {'buttons': [], 'axes': [], 'hats': [], 'keys': []},
}), encoding='utf-8')
store._dirs_changed()
run(w, '_win.reloadModuleControls()')
saved = module.read_bytes()

def pictures():
    return sorted(p.name for p in (folder / 'pictures').iterdir())

def buttons():
    return {
        'add': run(w, '_win.isInput ? (_win.hasImage'
                      ' ? "Change Image…" : "Add Image…") : ""'),
        'remove': bool(run(w, '_win.hasImage')),
    }

def pick():
    url = QtCore.QUrl.fromLocalFile(PICK).toString()
    run(w, '_imageDialog.picked(%s)' % json.dumps(url))
    QtTest.QTest.qWait(100)

def doc():
    return json.loads(module.read_text(encoding='utf-8'))

def mine():
    history.flush()
    return [e for e in history.entries() if folder.name in json.dumps(e)]

out = {'start': buttons()}
# Add Image…, then Discard: nothing changes.
pick()
out['picked'] = dict(buttons(), preview=run(w, '_win.photoUrl'), pictures=pictures())
run(w, '_win.putPhotoBack()')
QtTest.QTest.qWait(100)
out['discard'] = dict(buttons(), pictures=pictures(), same=module.read_bytes() == saved)
# Add Image…, then Save.
n0 = len(mine())
pick()
ok = run(w, '_win.commitModule()')
QtTest.QTest.qWait(200)
d = doc()
out['save'] = dict(
    buttons(), ok=bool(ok), image=d.get('deviceImage'), nodes=d.get('nodes') == NODES,
    pictures=pictures(), entries=len(mine()) - n0,
    preview=run(w, '_win.photoUrl').split('?')[0].rsplit('/', 1)[-1],
    temp_left=store.edit_temp_dir(name, guid, 'setup').exists(),
)
# Remove Image, then Save.
n0 = len(mine())
run(w, '_win.removeImage()')
out['removing'] = dict(
    buttons(), preview=run(w, '_win.photoUrl').split('?')[0].rsplit('/', 1)[-1],
    pictures=pictures(),
)
ok = run(w, '_win.commitModule()')
QtTest.QTest.qWait(200)
d = doc()
out['removed'] = dict(
    buttons(), ok=bool(ok), has_key='deviceImage' in d, nodes=d.get('nodes') == NODES,
    pictures=pictures(), entries=len(mine()) - n0,
)
print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive
"""


@pytest.fixture(scope="module")
def window(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    pick = home / "pick" / "shot.png"
    pick.parent.mkdir()
    pick.write_bytes(_PNG)
    script = home / "setup_image.py"
    script.write_text(_CODE, encoding="utf-8")
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen")
    proc = proc_tree.run(
        [sys.executable, str(script), str(_ROOT), str(pick)],
        cwd=home,
        env=env,
        text=True,
        timeout=120,
    )
    lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, smoke_report.explain(proc)
    return json.loads(lines[0][len("RESULT "):])


def test_module_setup_add_image_waits_and_discard_leaves_the_folder(
    window: dict,
) -> None:
    assert window["start"] == {"add": "Add Image…", "remove": False}, window
    picked = window["picked"]
    assert picked["add"] == "Change Image…" and picked["remove"], picked
    assert picked["preview"].startswith("file:"), picked
    assert "device-image.png" not in picked["pictures"], picked
    discard = window["discard"]
    assert discard["add"] == "Add Image…" and not discard["remove"], discard
    assert "device-image.png" not in discard["pictures"] and discard["same"], discard


def test_module_setup_save_names_the_device_image_and_leaves_the_map(
    window: dict,
) -> None:
    save = window["save"]
    assert save["ok"], save
    assert save["image"] == "pictures/device-image.png", save
    # The device map's background is unchanged (old: the picture replaced
    # the bottom background picture).
    assert save["nodes"], save
    assert {"device-image.png", "photo.jpg"} <= set(save["pictures"]), save
    assert save["preview"] == "device-image.png", save
    assert save["add"] == "Change Image…" and save["remove"], save
    assert save["entries"] == 1, save
    assert not save["temp_left"], save


def test_module_setup_remove_image_waits_for_save_then_drops_it(window: dict) -> None:
    removing = window["removing"]
    # The preview is the photo without the image; nothing gone until Save.
    # (the background picture, or the bottom background picture while
    # that is being made, 07 S157)
    assert removing["preview"] in ("device-photo.png", "photo.jpg"), removing
    assert {"device-image.png", "photo.jpg"} <= set(removing["pictures"]), removing
    assert removing["add"] == "Add Image…" and not removing["remove"], removing
    removed = window["removed"]
    assert removed["ok"] and not removed["has_key"] and removed["nodes"], removed
    assert "device-image.png" not in removed["pictures"], removed
    assert "photo.jpg" in removed["pictures"], removed
    assert removed["entries"] == 1, removed
