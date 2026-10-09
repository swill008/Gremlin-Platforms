# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Logical Device card's Add / Change / Remove Image (03 S88,
D-03-LD-IMAGE): the real StatusCard's right-click menu off-screen (the
menus_smoke.py harness with these steps), and the Home page routing the
card's requests to the model's slots."""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

_HERE = pathlib.Path(__file__).parent
_ROOT = _HERE.parents[1]

_OPEN_DEVICE = (
    "_probe.close(); _probe.build = _card.menuModel; _probe.openAt(_card, 20, 20);"
    # The menu remembers an open section: open Device only when it's shut.
    " if (_probe.describe().indexOf('> Device') >= 0) _probe.activate('Device');"
    " _probe.describe().join('|')"
)

_STEPS = [
    ("connect",
     "_card.addImage.connect(function() { _win.ran = 'add' });"
     " _card.removeImage.connect(function() { _win.ran = 'remove' }); 'ok'"),
    ("logical-bare",
     "_card.slug = 'logical'; _card.tab = 'logical'; _card.bus = 'Logical';"
     " _card.photo = ''; " + _OPEN_DEVICE),
    ("logical-add-runs", "_win.ran = ''; _probe.activate('Add Image…'); _win.ran"),
    ("logical-photo",
     "_card.photo = 'file:///no/such/photo.png'; " + _OPEN_DEVICE),
    ("logical-change-runs",
     "_win.ran = ''; _probe.activate('Change Image…'); _win.ran"),
    ("logical-remove-runs",
     _OPEN_DEVICE.replace("_probe.describe().join('|')", "")
     + " _win.ran = ''; _probe.activate('Remove Image'); _win.ran"),
    ("stick-photo",
     "_card.slug = 'pjoy_pro'; _card.tab = 'physical'; _card.bus = 'DirectInput';"
     " " + _OPEN_DEVICE),
    ("stick-bare", "_card.photo = ''; " + _OPEN_DEVICE),
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


def _results(tmp_path: pathlib.Path) -> dict[str, str]:
    result = subprocess.run(
        [sys.executable, "-c", _RUNNER, str(_HERE / "menus_smoke.py"), str(tmp_path)],
        capture_output=True,
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
    assert "done" in lines, (result.stderr or "")[-2000:]
    errors = [line for line in lines if line.startswith("ERROR")]
    assert errors == []
    return {
        line.split(" ", 2)[1]: line.split(" ", 2)[2]
        for line in lines
        if line.startswith("RESULT ") and line.count(" ") >= 2
    }


def test_logical_card_menu_has_the_image_items(tmp_path: pathlib.Path) -> None:
    results = _results(tmp_path)
    bare = results["logical-bare"].split("|")
    assert "  Add Image…" in bare
    assert "  Change Image…" not in bare and "  Remove Image" not in bare
    with_photo = results["logical-photo"].split("|")
    assert "  Change Image…" in with_photo and "  Remove Image" in with_photo
    assert "  Add Image…" not in with_photo
    # Choosing them asks the page (which calls the model's slots).
    assert results["logical-add-runs"] == "add"
    assert results["logical-change-runs"] == "add"
    assert results["logical-remove-runs"] == "remove"
    # Other cards are unchanged, photo or not.
    for step in ("stick-photo", "stick-bare"):
        rows = results[step]
        assert "Image" not in rows, (step, rows)
        assert "Delete Device" in rows, (step, rows)


def test_home_page_routes_the_card_image_to_the_model() -> None:
    page = (_ROOT / "qml" / "StatusPage.qml").read_text(encoding="utf-8")
    for line in (
        "card.onAddImage.connect(function() { _page.pickCardImage(card.slug) })",
        "card.onRemoveImage.connect(function() { _page.removeCardImage(card.slug) })",
    ):
        assert line in page, line
    picker = page[page.index("id: _cardImagePicker"):]
    picker = picker[: picker.index("\n    }\n")]
    assert 'kind: "picture"' in picker
    assert 'title: "Choose Image"' in picker
    assert 'nameFilters: ["Images (*.jpg *.jpeg *.png *.webp *.bmp)"]' in picker
    assert "model.setCardImage(_page._imageSlug, String(selectedFile))" in picker
    assert "model.removeCardImage(slug)" in page
