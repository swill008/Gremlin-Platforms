# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Module Setup's Add Image… (an input module's Device Image; old: Import
Image) waits in the window's edit until Save (03 S52, 07 S107,
D-03-DEVICE-FOLDERS, D-03-DEVICE-IMAGE).

Import Image wrote the picture straight into the device's pictures/, so
Cancel (which only drops the edit's temporary folder) left the new photo
in place; and Save wrote twice (saveClaim named photo.* and the edit's
commit named it again): two History entries.

Opens the real Module Setup off-screen in its own process, picks a picture
through its Import Image picker and presses Cancel, then again and Save.
"""

from __future__ import annotations

import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

sys.path.append(".")

import json
import os
import pathlib

import pytest

_ROOT = pathlib.Path(__file__).parents[2]

_CODE = r"""
import json, os, sys, time
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
import pathlib
import joystick_gremlin
from gremlin import history
from gremlin.modules import store
from PySide6 import QtCore, QtQml, QtQuick, QtTest
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window

def run(target, code):
    expr = QtQml.QQmlExpression(QtQml.qmlContext(target), target, code)
    value = expr.evaluate()
    assert not expr.hasError(), expr.error().toString()
    return value[0] if isinstance(value, tuple) else value

before = set(app.topLevelWindows())
run(win, '_root.openConfigureModule("source", null)')
QtTest.QTest.qWait(400)
w = next(x for x in app.topLevelWindows()
         if x not in before and isinstance(x, QtQuick.QQuickWindow) and x.isVisible())
name, guid = w.property('deviceName'), w.property('deviceGuid')

OLD = b'\xff\xd8\xff\xe0' + b'\x01' * 32 + b'\xff\xd9'
folder = store.ensure_device_dir(name, guid)
module = store.module_file_in(folder)
(folder / 'pictures').mkdir(exist_ok=True)
(folder / 'pictures' / 'photo.jpg').write_bytes(OLD)
module.write_text(json.dumps({
    'kind': 'control.hardware', 'device': name, 'direction': 'source',
    # The device's photo: the bottom background picture (07 S127).
    'nodes': [{'id': 'bg', 'kind': 'draw', 'shape': 'image',
               'plane': 'background', 'src': 'pictures/photo.jpg'}],
    'claim': {'buttons': [], 'axes': [], 'hats': [], 'keys': []},
}), encoding='utf-8')
store._dirs_changed()
run(w, '_win.reloadModuleControls()')
saved = module.read_bytes()

def pictures():
    return {p.name: p.read_bytes() for p in sorted((folder / 'pictures').iterdir())}

def pick():
    url = QtCore.QUrl.fromLocalFile(PICK).toString()
    run(w, '_imageDialog.picked(%s)' % json.dumps(url))
    QtTest.QTest.qWait(100)

def mine():
    history.flush()
    return [e for e in history.entries() if folder.name in json.dumps(e)]

out = {}
# Import Image, then Cancel (Discard).
pick()
out['preview'] = run(w, '_win.photoUrl')
run(w, '_win.putPhotoBack()')
QtTest.QTest.qWait(100)
out['cancel'] = {
    'pictures': sorted(pictures()),
    'old_kept': pictures().get('photo.jpg') == OLD,
    'module_same': module.read_bytes() == saved,
}
# Import Image, then Save (with a claim ticked in the same Save).
n0 = len(mine())
pick()
# Until Save the device's folder is not touched (07 S107).
waiting = sorted(pictures()) == ['photo.jpg'] and pictures()['photo.jpg'] == OLD
run(w, '_driver.setClaimed(0, true)')
ok = run(w, '_win.commitModule()')
QtTest.QTest.qWait(200)
# The device's background picture (07 S157) of the map's photo.jpg: the
# maker draws it from the module file the test wrote, so it can land
# before or after Save. Wait (bounded) until the maker is idle and the
# picture is current.
maker = app.device_photo_maker
deadline = time.monotonic() + 30
while time.monotonic() < deadline and not (
        maker._job is None and not maker._queue
        and store.device_photo_current(folder)):
    QtTest.QTest.qWait(50)
doc = json.loads(module.read_text(encoding='utf-8'))
image = store.device_image_ref(doc)
new = folder / image if image else None
out['save'] = {
    'waiting': waiting,
    'ok': bool(ok),
    'image': image,
    'bottom': store.device_photo_ref(doc),
    'image_is_new': bool(
        new and new.is_file() and new.read_bytes() == pathlib.Path(PICK).read_bytes()),
    'claimed': doc.get('claim', {}),
    'pictures': sorted(pictures()),
    'entries': len(mine()) - n0,
    'temp_left': (store.edit_temp_dir(name, guid, 'setup')).exists(),
}
print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive
"""


@pytest.fixture(scope="module")
def result(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    pick = home / "pick" / "shot.png"
    pick.parent.mkdir()
    pick.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x02" * 24)
    script = home / "setup_photo.py"
    script.write_text(_CODE, encoding="utf-8")
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen")
    proc = proc_tree.run(
        [sys.executable, str(script), str(_ROOT), str(pick)], cwd=home,
        env=env, text=True, timeout=120,
    )
    lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, smoke_report.explain(proc)
    return json.loads(lines[0][len("RESULT "):])


def test_cancel_after_import_image_leaves_the_folder_as_it_was(result: dict) -> None:
    # The picked picture was shown while the window was open.
    assert result["preview"].startswith("file:"), result
    cancel = result["cancel"]
    # Old: photo.png stayed in pictures/ and photo.jpg was removed.
    assert cancel["pictures"] == ["photo.jpg"], cancel
    assert cancel["old_kept"] and cancel["module_same"], cancel


def test_save_after_import_image_names_it_in_one_write(result: dict) -> None:
    save = result["save"]
    # Old: Import Image wrote pictures/photo.png at once.
    assert save["waiting"], save
    assert save["ok"], save
    # Old: the picture became the bottom background picture (photo.*); an
    # input module's Add Image… now names the Device Image (deviceImage,
    # 03 S52, D-03-DEVICE-IMAGE) and leaves the map alone.
    assert save["image"].startswith("pictures/device-image"), save
    assert save["bottom"] == "pictures/photo.jpg", save
    assert save["image_is_new"], save
    assert save["claimed"].get("buttons") or save["claimed"].get("axes") or save[
        "claimed"
    ].get("keys"), save
    # The map's own photo is still named, so it stays (07 S106); the
    # device's background picture is drawn from it (07 S157).
    assert save["pictures"] == sorted(
        [save["image"].split("/", 1)[1], "photo.jpg", "device-photo.png"]
    ), save
    # Old: two writes (saveClaim, then the edit's commit): two entries.
    assert save["entries"] == 1, save
    assert not save["temp_left"], save
