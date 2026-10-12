# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Home card menu (D-NEXTLIST-1 item 1, D-03-DEVICE-IMAGE): input module
cards offer Add Image… (no Device Image yet) or Change Image… and Remove
Image (hasImage); output cards and the Logical Device's own items are as
before; the card menu has no "Xbox Viewer" (it is part of the Xbox Output
View now). The menu items run on StatusCard.qml's own menuModel() with a
stand-in MenuModel, and end to end on the real Home page off-screen
(home_cards_smoke.py): the picked file and Remove reach the model's
setCardImage / removeCardImage."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import cast

from PySide6 import QtCore, QtQml

sys.path.insert(0, str(Path(__file__).resolve().parent))

import home_cards_smoke  # noqa: E402

_ROOT = Path(__file__).resolve().parents[2]
# HOME_QML_DIR: another qml folder (the old files, to show these fail there).
_QML = Path(os.environ.get("HOME_QML_DIR") or (_ROOT / "qml"))


def _function_source(text: str, name: str) -> str:
    start = text.index(f"function {name}(")
    depth = 0
    for index in range(text.index("{", start), len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise AssertionError(f"{name} has no end")


def card_menu(
    slug: str,
    direction: str,
    bus: str,
    tab: str,
    *,
    has_image: bool = False,
    photo: str = "",
    is_module: bool = True,
    damaged: str = "",
) -> dict[str, bool]:
    """Each item of StatusCard.qml's menuModel(): its text -> enabled."""
    text = (_QML / "StatusCard.qml").read_text(encoding="utf-8")
    script = (
        """
        var MenuModel = {
            action: function(text, run, enabled) {
                return {text: text, on: enabled === undefined ? true : !!enabled}
            },
            section: function(id, title, items) { return items },
            menu: function(kind, title, quick, sections) {
                var out = quick.filter(function(i) { return i !== null })
                sections.forEach(function(items) {
                    items.forEach(function(i) { if (i !== null) out.push(i) })
                })
                return out
            }
        }
        """
        + f"var slug = {json.dumps(slug)}; var cardName = 'Card';"
        + f" var rawName = cardName; var direction = {json.dumps(direction)};"
        + f" var bus = {json.dumps(bus)}; var tab = {json.dumps(tab)};"
        + " var stacked = false;"
        + f" var _card = {{ damaged: {json.dumps(damaged)}, canStackSelected: false,"
        + f" hasImage: {json.dumps(has_image)}, photo: {json.dumps(photo)},"
        + f" isModule: {json.dumps(is_module)} }};"
        + _function_source(text, "menuModel")
    )
    engine = QtQml.QJSEngine()
    loaded = cast(QtQml.QJSValue, engine.evaluate(script))
    assert not loaded.isError(), loaded.toString()
    result = cast(QtQml.QJSValue, engine.evaluate("JSON.stringify(menuModel())"))
    assert not result.isError(), result.toString()
    return {i["text"]: i["on"] for i in json.loads(result.toString())}


_IMAGE = {"Add Image…", "Change Image…", "Remove Image"}


def test_input_cards_offer_the_device_image_items(
    qapp: QtCore.QCoreApplication,
) -> None:
    cards = (("pjoy_pro", "physical"), ("keyboard", "keyboard"), ("osc", "osc"))
    for slug, tab in cards:
        bare = card_menu(slug, "source", "HID", tab)
        assert _IMAGE & set(bare) == {"Add Image…"}, (slug, bare)
        assert bare["Add Image…"] is True
        # A generated picture (photo) isn't an image: still Add Image….
        generated = card_menu(slug, "source", "HID", tab, photo="file:///p.png")
        assert _IMAGE & set(generated) == {"Add Image…"}, (slug, generated)
        held = card_menu(
            slug, "source", "HID", tab, has_image=True, photo="file:///i.png"
        )
        assert _IMAGE & set(held) == {"Change Image…", "Remove Image"}, (slug, held)


def test_a_card_without_a_readable_module_file_cannot_add_one(
    qapp: QtCore.QCoreApplication,
) -> None:
    assert (
        card_menu("pjoy_pro", "source", "HID", "physical", is_module=False)[
            "Add Image…"
        ]
        is False
    )
    damaged = card_menu(
        "pjoy_pro", "source", "HID", "physical", has_image=True, damaged="bad JSON"
    )
    assert damaged["Change Image…"] is False and damaged["Remove Image"] is False


def test_output_cards_have_none_and_the_logical_device_is_unchanged(
    qapp: QtCore.QCoreApplication,
) -> None:
    outputs = (("vjoy_1", "DirectInput", "physical"), ("xbox", "XInput", "xbox"))
    for slug, bus, tab in outputs:
        menu = card_menu(slug, "dest", bus, tab, has_image=True, photo="file:///p.png")
        assert not _IMAGE & set(menu), (slug, menu)
    # The Logical Device keeps its own picture items, driven by photo.
    bare = card_menu("logical", "source", "Logical", "logical")
    assert _IMAGE & set(bare) == {"Add Image…"}
    with_photo = card_menu(
        "logical", "source", "Logical", "logical", photo="file:///p.png"
    )
    assert _IMAGE & set(with_photo) == {"Change Image…", "Remove Image"}


def test_the_card_menu_has_no_xbox_viewer(qapp: QtCore.QCoreApplication) -> None:
    xbox = card_menu("xbox", "dest", "XInput", "xbox")
    assert "Xbox Viewer" not in xbox
    assert "vJoy Viewer" not in xbox
    vjoy = card_menu("vjoy_1", "dest", "DirectInput", "physical")
    assert "vJoy Viewer" in vjoy
    assert "Xbox Viewer" not in (_QML / "StatusCard.qml").read_text(encoding="utf-8")


def test_the_items_reach_the_model_end_to_end(tmp_path: Path) -> None:
    r = home_cards_smoke.run(tmp_path, "image")
    assert r["a-has-image"] is False and r["b-has-image"] is True
    a_rows = r["a-rows"]
    b_rows = r["b-rows"]
    assert isinstance(a_rows, list) and isinstance(b_rows, list)
    assert "  Add Image…" in a_rows and "  Remove Image" not in a_rows
    assert "  Change Image…" in b_rows and "  Remove Image" in b_rows
    assert r["a-add-ran"] is True and r["b-remove-ran"] is True
    # The FilePicker's file goes to setCardImage; Remove to removeCardImage.
    assert r["calls"] == ["set a file:///C:/pick/stick.png", "remove b"]
