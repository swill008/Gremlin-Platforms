# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Device Image on the real path (D-03-DEVICE-IMAGE; 03 S52, S88, S136,
07 S127), off-screen with stand-in hardware. test_device_image_e2e.py runs
it in its own process with a fresh user folder.

The real main window, its Home page and card menu, its Home Undo, its
Module Setup window and the Device Mapping Editor's Save slot, over the
stand-in stick "pJoy Pro" whose map has a background (so the main window's
maker makes its generated picture, pictures/device-photo.png):

1. Home card menu Add Image… -> the picker -> the card shows the image;
   Change Image…; Remove Image -> the card shows the generated picture;
   Home Undo / Redo of each. Setting the image makes nothing again (3a).
2. Module Setup Add Image… waits until Save, then the card shows it;
   Remove Image -> Save; Add Image… then Discard leaves the folder as it was.
3. The Device Mapping Editor's Save while an image is set keeps it.
4. An output card and the Logical Device card are as before.

Each step records its findings (or its error) under its own key. Prints
RESULT {json}.

    python test/unit/device_image_e2e_smoke.py
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import traceback
from collections.abc import Callable, Iterator
from pathlib import Path

from smoke_exit import smoke_exit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location(
    "fake_hardware", ROOT / "test" / "fake_hardware.py"
)
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake = fake_hardware.install()

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

import shiboken6  # noqa: E402
from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest  # noqa: E402

import dill  # noqa: E402
import joystick_gremlin  # noqa: E402
from gremlin.modules import store  # noqa: E402

NAME = "pJoy Pro"
GUID = str(dill.GUID(fake.devices[0].device_guid).uuid)
FOLDER = store.ensure_device_dir(NAME, GUID)
PICS = FOLDER / "pictures"
PICS.mkdir(exist_ok=True)
MODULE = store.module_file_in(FOLDER)
PHOTO = PICS / "device-photo.png"
KEY = getattr(store, "DEVICE_IMAGE_KEY", "deviceImage")

PICKS = Path(os.environ["USERPROFILE"]) / "picks"
PICKS.mkdir(exist_ok=True)


def _picture(path: Path, color: QtGui.QColor, w: int = 64, h: int = 32) -> bytes:
    img = QtGui.QImage(w, h, QtGui.QImage.Format.Format_RGB32)
    img.fill(color)
    img.save(str(path), "PNG")
    return path.read_bytes()


# A background rectangle (the generated picture is made of it) and a chip.
BG = {"kind": "draw", "id": "bg", "shape": "rect", "plane": "background",
      "fx": 0.1, "fy": 0.1, "fw": 0.6, "fh": 0.6, "rot": 0, "opacity": 1,
      "color": "#00FF00", "border": "#00FF00", "fill": "filled",
      "locked": False, "pinned": False, "sockets": []}  # fmt: skip
CHIP = {"kind": "btn", "id": "b1", "label": "Button 1", "chipFx": 0.8, "chipFy": 0.2}

MODULE.write_text(
    json.dumps({
        "kind": "control.hardware", "device": NAME, "direction": "source",
        "boundGuidLocal": GUID,
        "claim": {"buttons": [1], "axes": [], "hats": [], "friendly": {}},
        "nodes": [BG, CHIP],
    }),
    encoding="utf-8",
)  # fmt: skip

out: dict = {"errors": {}}


def step(name: str, fn: Callable[[], None]) -> None:
    try:
        fn()
    except Exception:  # noqa: BLE001 - recorded for the test to show
        out["errors"][name] = traceback.format_exc()[-1500:]


def wait_until(cond: Callable[[], object], limit_ms: int = 8000) -> bool:
    waited = 0
    while waited < limit_ms:
        try:
            if cond():
                return True
        except Exception:  # noqa: BLE001
            pass
        QtTest.QTest.qWait(50)
        waited += 50
    return False


def ev(host: QtCore.QObject, code: str) -> object:
    expr = QtQml.QQmlExpression(QtQml.qmlContext(host), host, code)
    value = expr.evaluate()
    assert not expr.hasError(), f"{code}: {expr.error().toString()}"
    value = value[0] if isinstance(value, tuple) else value
    if isinstance(value, QtQml.QJSValue):
        value = value.toQObject() if value.isQObject() else value.toVariant()
    return value


def walk(item: QtQuick.QQuickItem) -> Iterator[QtQuick.QQuickItem]:
    yield item
    for child in item.childItems():
        yield from walk(child)


def doc() -> dict:
    return json.loads(MODULE.read_text(encoding="utf-8"))


def image_ref() -> str:
    return str(doc().get(KEY) or "")


def image_bytes() -> bytes | None:
    ref = image_ref()
    if not ref:
        return None
    path = FOLDER / ref
    return path.read_bytes() if path.is_file() else None


def image_files() -> list[str]:
    return sorted(p.name for p in PICS.glob("device-image*"))


def snapshot() -> dict[str, str]:
    """Every file of the device folder by its path -> a hash of its bytes."""
    return {
        str(p.relative_to(FOLDER)): hashlib.sha1(p.read_bytes()).hexdigest()
        for p in sorted(FOLDER.rglob("*"))
        if p.is_file()
    }


RED = _picture(PICKS / "red.png", QtGui.QColor(255, 0, 0))
BLUE = _picture(PICKS / "blue.png", QtGui.QColor(0, 0, 255))
YELLOW = _picture(PICKS / "yellow.png", QtGui.QColor(255, 255, 0))
WHITE = _picture(PICKS / "white.png", QtGui.QColor(255, 255, 255))


def url(name: str) -> str:
    return QtCore.QUrl.fromLocalFile(str(PICKS / name)).toString()


app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window
QtTest.QTest.qWait(800)
quick = shiboken6.wrapInstance(shiboken6.getCppPointer(win)[0], QtQuick.QQuickWindow)
quick.resize(1600, 1000)

maker = app.engine.rootContext().contextProperty("devicePhotoMaker")
renders: list = []
if maker is not None and hasattr(maker, "renderWanted"):
    maker.renderWanted.connect(lambda *a: renders.append(list(a)))

page: QtCore.QObject | None = None
SLUG = ""


def card_js(slug_or_name: str, by: str = "name") -> str:
    test = (
        f"(c.rawName==={json.dumps(slug_or_name)}||c.cardName==={json.dumps(slug_or_name)})"
        if by == "name"
        else f"c.slug==={json.dumps(slug_or_name)}"
    )
    return (
        "(function(){for(var i=0;i<_liveCards.length;++i){var c=_liveCards[i];"
        f"if(c&&{test})return c}}return null}})()"
    )


def card(slug: str = "") -> QtCore.QObject | None:
    assert page is not None
    return ev(page, card_js(slug or SLUG, "slug"))  # type: ignore[return-value]


def card_state(slug: str = "") -> dict:
    c = card(slug)
    if c is None:
        return {"card": None}
    return {"hasImage": c.property("hasImage"), "photo": str(c.property("photo") or "")}


def menu_of(c: QtCore.QObject) -> QtCore.QObject | None:
    return ev(  # type: ignore[return-value]
        c,
        "(function(){for(var i=0;i<data.length;++i){var d=data[i];"
        "if(d&&typeof d.describe==='function'&&typeof d.activate==='function')"
        "return d}return null})()",
    )


def menu_rows(c: QtCore.QObject) -> list[str]:
    """Right-clicks the card and reads its menu (opening Device when it is
    a submenu)."""
    assert isinstance(c, QtQuick.QQuickItem) or True
    item = shiboken6.wrapInstance(shiboken6.getCppPointer(c)[0], QtQuick.QQuickItem)
    point = item.mapToScene(QtCore.QPointF(30, 30)).toPoint()
    QtTest.QTest.mouseClick(
        quick, QtCore.Qt.MouseButton.RightButton, QtCore.Qt.KeyboardModifier.NoModifier,
        point,
    )  # fmt: skip
    QtTest.QTest.qWait(250)
    menu = menu_of(c)
    assert menu is not None, "the card has no menu"
    rows = str(ev(menu, "describe().join('|')") or "").split("|")
    if "> Device" in rows:
        ev(menu, "activate('Device')")
        rows = str(ev(menu, "describe().join('|')") or "").split("|")
    return rows


def run_menu(c: QtCore.QObject, text: str) -> object:
    menu_rows(c)
    menu = menu_of(c)
    assert menu is not None
    ran = ev(menu, f"activate({json.dumps(text)})")
    QtTest.QTest.qWait(200)
    return ran


def pick(host: QtCore.QObject, file_url: str, title: str = "Choose Image") -> bool:
    """The FilePicker the step opened answers with file_url (its own
    _accept, the path its dialog's accepted takes)."""
    for dialog in host.findChildren(QtCore.QObject, "filePickerFileDialog"):
        owner = dialog.parent()
        if owner is not None and owner.property("title") == title:
            try:
                ev(dialog, "close()")
            except AssertionError:
                pass
            QtTest.QTest.qWait(100)
            ev(owner, f"_accept({json.dumps(file_url)})")
            QtTest.QTest.qWait(300)
            return True
    return False


def settle() -> None:
    QtTest.QTest.qWait(600)


# --- 0. Home is up, the generated picture is made ---------------------------------


def start() -> None:
    global page, SLUG
    ev(win, "_moduleModel.reload()")
    assert wait_until(lambda: ev(win, "_statusLoader.item !== null"))
    loader_item = ev(win, "_statusLoader.item")
    page = loader_item
    for child in loader_item.childItems():  # type: ignore[union-attr]
        own = QtQml.qmlContext(child)
        if own is not None and own != QtQml.qmlContext(loader_item):
            page = child
            break
    if not wait_until(lambda: ev(page, card_js(NAME)) is not None):  # type: ignore[arg-type]
        page = loader_item
    assert wait_until(lambda: ev(page, card_js(NAME)) is not None), "no pJoy Pro card"  # type: ignore[arg-type]
    SLUG = str(ev(page, card_js(NAME) + ".slug"))  # type: ignore[arg-type]
    out["slug"] = SLUG
    out["generated"] = wait_until(PHOTO.is_file, 20000)
    settle()
    out["start-card"] = card_state()
    out["start-photo-mtime"] = PHOTO.stat().st_mtime_ns if PHOTO.exists() else None


step("start", start)


# --- 1. Home card menu: Add, Change, Remove; Undo / Redo --------------------------


def home() -> None:
    renders.clear()
    c = card()
    assert c is not None
    out["home-rows-before"] = menu_rows(c)
    ev(menu_of(c), "close()")  # type: ignore[arg-type]
    QtTest.QTest.qWait(100)

    out["home-add-ran"] = run_menu(c, "Add Image…")
    out["home-add-picked"] = pick(page, url("red.png"))  # type: ignore[arg-type]
    settle()
    out["home-add"] = {
        "ref": image_ref(), "red": image_bytes() == RED, "files": image_files(),
        **card_state(),
    }  # fmt: skip
    out["home-rows-with-image"] = menu_rows(card())  # type: ignore[arg-type]
    ev(menu_of(card()), "close()")  # type: ignore[arg-type]
    QtTest.QTest.qWait(100)

    out["home-change-ran"] = run_menu(card(), "Change Image…")  # type: ignore[arg-type]
    out["home-change-picked"] = pick(page, url("blue.png"))  # type: ignore[arg-type]
    settle()
    out["home-change"] = {
        "ref": image_ref(), "blue": image_bytes() == BLUE, "files": image_files(),
        **card_state(),
    }  # fmt: skip

    out["home-remove-ran"] = run_menu(card(), "Remove Image")  # type: ignore[arg-type]
    settle()
    out["home-remove"] = {"ref": image_ref(), "files": image_files(), **card_state()}
    out["home-renders"] = len(renders)
    out["home-photo-mtime"] = PHOTO.stat().st_mtime_ns if PHOTO.exists() else None

    # Home Undo / Redo: one step each.
    undo: list[dict] = []
    for _ in range(3):
        done = ev(win, "_moduleModel")._undo_steps  # type: ignore[attr-defined]
        tip = f"Undo {done[-1][0]}" if done else ""
        ev(win, "_moduleModel.undo()")
        settle()
        undo.append({
            "tip": tip, "ref": image_ref(), "bytes": _which(image_bytes()),
            "files": image_files(), **card_state(),
        })  # fmt: skip
    out["home-undo"] = undo
    redo: list[dict] = []
    for _ in range(3):
        ev(win, "_moduleModel.redo()")
        settle()
        redo.append({
            "ref": image_ref(), "bytes": _which(image_bytes()),
            "files": image_files(), **card_state(),
        })  # fmt: skip
    out["home-redo"] = redo
    out["home-renders-after-undo"] = len(renders)


def _which(data: bytes | None) -> str:
    for name, known in (
        ("red", RED),
        ("blue", BLUE),
        ("yellow", YELLOW),
        ("white", WHITE),
    ):
        if data == known:
            return name
    return "" if data is None else "other"


step("home", home)


# --- 2. Module Setup: Add -> Save; Remove -> Save; Add -> Discard -------------------


def setup_window() -> QtCore.QObject:
    ev(win, f"openConfigureModule('source', _moduleModel.cardMap({json.dumps(SLUG)}))")
    assert wait_until(lambda: ev(win, "configureWin") is not None, 5000)
    setup = ev(win, "configureWin")
    assert setup is not None
    QtTest.QTest.qWait(500)
    return setup  # type: ignore[return-value]


def items(setup: QtCore.QObject) -> Iterator[QtQuick.QQuickItem]:
    window = shiboken6.wrapInstance(
        shiboken6.getCppPointer(setup)[0], QtQuick.QQuickWindow
    )
    yield from walk(window.contentItem())


def button(setup: QtCore.QObject, name: str = "", text: str = "") -> QtQuick.QQuickItem:
    for item in items(setup):
        if name and item.objectName() == name:
            return item
        if text and item.property("text") == text and item.isVisible():
            return item
    raise AssertionError(f"no button {name or text}")


def press(item: QtQuick.QQuickItem) -> None:
    ev(item, "clicked()")
    QtTest.QTest.qWait(300)


def close_setup(setup: QtCore.QObject) -> None:
    ev(setup, "allowClose = true; close()")
    wait_until(lambda: ev(win, "configureWin") is None, 3000)


def setup_add_save() -> None:
    assert not image_ref(), "an image was left from step 1"
    setup = setup_window()
    image = button(setup, "moduleSetupImage")
    out["setup-add-text"] = image.property("text")
    before = snapshot()
    press(image)
    out["setup-add-picked"] = pick(setup, url("yellow.png"))
    out["setup-add-waits"] = snapshot() == before and not image_ref()
    out["setup-remove-shown"] = button(setup, "moduleSetupRemoveImage").isVisible()
    press(button(setup, text="Save Module"))
    settle()
    wait_until(lambda: card_state().get("hasImage") is True, 3000)
    out["setup-add"] = {
        "ref": image_ref(), "yellow": image_bytes() == YELLOW, "files": image_files(),
        **card_state(),
    }  # fmt: skip
    close_setup(setup)


step("setup-add", setup_add_save)


def setup_remove_save() -> None:
    setup = setup_window()
    out["setup-change-text"] = button(setup, "moduleSetupImage").property("text")
    remove = button(setup, "moduleSetupRemoveImage")
    out["setup-remove-visible"] = remove.isVisible()
    press(remove)
    out["setup-remove-waits"] = bool(image_ref())
    press(button(setup, text="Save Module"))
    settle()
    wait_until(lambda: card_state().get("hasImage") is False, 3000)
    out["setup-remove"] = {"ref": image_ref(), "files": image_files(), **card_state()}
    close_setup(setup)


step("setup-remove", setup_remove_save)


def setup_discard() -> None:
    before = snapshot()
    setup = setup_window()
    press(button(setup, "moduleSetupImage"))
    out["setup-discard-picked"] = pick(setup, url("white.png"))
    ev(setup, "close()")
    QtTest.QTest.qWait(300)
    out["setup-discard-asked"] = bool(ev(setup, "claimDirty"))
    ev(setup, "_saveGate.discardChosen()")
    wait_until(lambda: ev(win, "configureWin") is None, 3000)
    settle()
    after = snapshot()
    out["setup-discard"] = {
        "same": after == before,
        "added": sorted(set(after) - set(before)),
        "gone": sorted(set(before) - set(after)),
        "changed": sorted(k for k in before if k in after and before[k] != after[k]),
        "ref": image_ref(),
        **card_state(),
    }  # fmt: skip


step("setup-discard", setup_discard)


# --- 3. The Device Mapping Editor's Save keeps the image ----------------------------


def editor_save() -> None:
    from gremlin.ui import hardware_profile

    model = ev(win, "_moduleModel")
    assert model is not None
    out["editor-set"] = bool(model.setCardImage(SLUG, url("red.png")))  # type: ignore[attr-defined]
    settle()
    ref = image_ref()
    out["editor-ref-before"] = ref
    hw = hardware_profile.HardwareProfile()
    hw.setDeviceGuid(GUID)
    moved = dict(CHIP, chipFx=0.7)
    out["editor-save-1"] = bool(hw.save(NAME, json.dumps({"nodes": [BG, moved]})))
    out["editor-after-1"] = {"ref": image_ref(), "red": image_bytes() == RED}
    # The editor's loaded document named an image that has since gone: its
    # Save doesn't bring that back over the file's own.
    out["editor-save-2"] = bool(
        hw.save(NAME, json.dumps({"nodes": [BG, CHIP], KEY: "pictures/stale.png"}))
    )
    out["editor-after-2"] = {
        "ref": image_ref(), "red": image_bytes() == RED, "files": image_files(),
    }  # fmt: skip
    settle()
    out["editor-card"] = card_state()
    hw.deleteLater()


step("editor", editor_save)


# --- 4. Output card and Logical Device card: as before ------------------------------


def others() -> None:
    from gremlin import logical_device_file

    model = ev(win, "_moduleModel")
    dest = ev(
        page,  # type: ignore[arg-type]
        "(function(){for(var i=0;i<_liveCards.length;++i){var c=_liveCards[i];"
        "if(c&&c.direction==='dest'&&c.slug!=='logical')return c}return null})()",
    )
    if dest is not None:
        out["output-slug"] = str(dest.property("slug"))  # type: ignore[union-attr]
        out["output-rows"] = menu_rows(dest)  # type: ignore[arg-type]
        ev(menu_of(dest), "close()")  # type: ignore[arg-type]
        out["output-set"] = bool(
            model.setCardImage(out["output-slug"], url("red.png"))  # type: ignore[union-attr]
        )
    logical = ev(page, card_js("logical", "slug"))  # type: ignore[arg-type]
    if logical is not None:
        out["logical-rows"] = menu_rows(logical)  # type: ignore[arg-type]
        ev(menu_of(logical), "close()")  # type: ignore[arg-type]
    out["logical-set"] = bool(model.setCardImage("logical", url("red.png")))  # type: ignore[union-attr]
    settle()
    path = logical_device_file.path()
    ld = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    out["logical-doc"] = {
        "key": ld.get(KEY),
        "photo": store.device_photo_ref(ld),
        "image-files": sorted(
            p.name for p in path.parent.glob("pictures/device-image*")
        ),
    }  # fmt: skip
    if logical is not None:
        out["logical-card-photo"] = str(logical.property("photo") or "")  # type: ignore[union-attr]
    out["logical-remove"] = bool(model.removeCardImage("logical"))  # type: ignore[union-attr]
    settle()
    ld = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    out["logical-after-remove"] = store.device_photo_ref(ld)


step("others", others)

print("RESULT " + json.dumps(out, default=str), flush=True)
smoke_exit(0)
