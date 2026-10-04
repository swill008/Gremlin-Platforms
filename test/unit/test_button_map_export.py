# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Button Map export: the page is cut out of the picture of the editor and
written as PNG, JPG or PDF on the window's background colour."""

from __future__ import annotations

import sys

sys.path.append(".")

import pathlib

from PySide6 import (
    QtCore,
    QtGui,
)

from gremlin.ui.hardware_profile import HardwareProfile, save_page_image, save_pages


def _editor_picture() -> QtGui.QImage:
    """A 200 x 100 picture: transparent around a red 120 x 60 page at 40, 20."""
    image = QtGui.QImage(200, 100, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(image)
    painter.fillRect(40, 20, 120, 60, QtGui.QColor("#FF0000"))
    painter.end()
    return image


def test_png_is_the_page_on_the_background(tmp_path: pathlib.Path) -> None:
    image = _editor_picture()
    painter = QtGui.QPainter(image)
    painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_Clear)
    painter.fillRect(40, 20, 10, 10, QtCore.Qt.GlobalColor.transparent)
    painter.end()
    target = tmp_path / "map.png"

    assert save_page_image(image, 40, 20, 120, 60, target, "png", "#102030")
    saved = QtGui.QImage(str(target))
    assert saved.size() == QtCore.QSize(120, 60)
    assert saved.pixelColor(60, 30).name() == "#ff0000"
    # A clear spot on the page shows the background, not transparency.
    assert saved.pixelColor(2, 2).name() == "#102030"
    assert saved.pixelColor(2, 2).alpha() == 255


def test_jpg(tmp_path: pathlib.Path) -> None:
    target = tmp_path / "map.jpg"

    assert save_page_image(_editor_picture(), 40, 20, 120, 60, target, "jpg", "#000000")
    saved = QtGui.QImage(str(target))
    assert saved.size() == QtCore.QSize(120, 60)
    assert saved.pixelColor(60, 30).red() > 200


def test_pdf_page_keeps_the_screen_size(tmp_path: pathlib.Path) -> None:
    one = tmp_path / "one.pdf"
    two = tmp_path / "two.pdf"

    assert save_page_image(_editor_picture(), 40, 20, 120, 60, one, "pdf", "#000000")
    big = _editor_picture().scaled(400, 200)
    assert save_page_image(big, 80, 40, 240, 120, two, "pdf", "#000000", 2)
    assert one.read_bytes().startswith(b"%PDF")
    # Same page size (points); the 2x file just carries more pixels.
    box = b"/MediaBox [0 0 120.000000 60.000000]"
    assert box in one.read_bytes()
    assert box in two.read_bytes()


def test_rect_outside_the_picture_writes_nothing(tmp_path: pathlib.Path) -> None:
    target = tmp_path / "map.png"

    assert not save_page_image(_editor_picture(), 500, 500, 10, 10, target, "png", "")
    assert not save_page_image(QtGui.QImage(), 0, 0, 10, 10, target, "png", "")
    assert not target.exists()


def _page(colour: str) -> QtGui.QImage:
    image = QtGui.QImage(120, 60, QtGui.QImage.Format.Format_RGB32)
    image.fill(QtGui.QColor(colour))
    return image


def test_export_modes_pdf_has_a_page_per_mode(tmp_path: pathlib.Path) -> None:
    target = tmp_path / "map.pdf"
    pages = [("Default", _page("#FF0000")), ("Combat", _page("#00FF00"))]

    assert save_pages(pages, target, "pdf", 2) == [target]
    data = target.read_bytes()
    assert data.count(b"/Type /Page\n") + data.count(b"/Type /Page ") >= 2
    assert b"/MediaBox [0 0 60.000000 30.000000]" in data


def test_export_modes_images_get_one_file_each(tmp_path: pathlib.Path) -> None:
    target = tmp_path / "map.png"
    pages = [("Default", _page("#FF0000")), ("Nav/Land", _page("#00FF00"))]

    written = save_pages(pages, target, "png")
    assert [p.name for p in written] == ["map - Default.png", "map - Nav_Land.png"]
    assert QtGui.QImage(str(written[1])).pixelColor(5, 5).name() == "#00ff00"
    assert not target.exists()


def test_export_pages_through_the_window_slots(tmp_path: pathlib.Path) -> None:
    profile = HardwareProfile()
    profile.beginExportPages()
    assert profile.addExportPage(_editor_picture(), 40, 20, 120, 60, "A", "#000000")
    assert not profile.addExportPage(QtGui.QImage(), 0, 0, 10, 10, "B", "#000000")
    assert profile.addExportPage(_editor_picture(), 40, 20, 120, 60, "C", "#000000")
    url = QtCore.QUrl.fromLocalFile(str(tmp_path / "modes.jpg")).toString()
    assert profile.finishExportPages(url, "jpg", 1, "{}") == 2
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "modes - A.jpg",
        "modes - C.jpg",
    ]
    # Finished: nothing left over for the next export.
    assert profile.finishExportPages(url, "jpg", 1, "{}") == 0


# Printing needs the widgets application, so it runs in a process of its own.
_PRINT = r"""
import os, sys
sys.path.insert(0, ".")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6 import QtGui, QtPrintSupport, QtWidgets
app = QtWidgets.QApplication(sys.argv[:1])
from gremlin.ui.hardware_profile import print_image
printer = QtPrintSupport.QPrinter(QtPrintSupport.QPrinter.PrinterMode.ScreenResolution)
printer.setOutputFormat(QtPrintSupport.QPrinter.OutputFormat.PdfFormat)
printer.setOutputFileName(sys.argv[1])
image = QtGui.QImage(120, 60, QtGui.QImage.Format.Format_RGB32)
image.fill(QtGui.QColor("#3366CC"))
ok = print_image(printer, image)
none = print_image(printer, QtGui.QImage())
print(ok, none, flush=True)
os._exit(0)
"""


def test_print_draws_the_page(tmp_path: pathlib.Path) -> None:
    import os
    import subprocess

    target = tmp_path / "printed.pdf"
    root = pathlib.Path(__file__).parents[2]
    result = subprocess.run(
        [sys.executable, "-c", _PRINT, str(target)],
        capture_output=True,
        text=True,
        cwd=root,
        timeout=60,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
    )
    assert result.stdout.split() == ["True", "False"], result.stderr[-1000:]
    assert target.read_bytes().startswith(b"%PDF")


def test_print_slot_is_there_for_the_window() -> None:
    assert hasattr(HardwareProfile, "printPage")


def test_pdf_on_a_paper_is_that_page(tmp_path: pathlib.Path) -> None:
    from gremlin.ui.util import page_layout

    target = tmp_path / "letter.pdf"
    setup = {"paper": "letter", "landscape": False, "margin": "quarter"}
    assert save_page_image(
        _editor_picture(), 40, 20, 120, 60, target, "pdf", "#000000", 1, setup
    )
    # US Letter, portrait: 8.5 x 11 in = 612 x 792 points.
    assert b"/MediaBox [0 0 612.000000 792.000000]" in target.read_bytes()
    layout = page_layout(setup)
    assert layout is not None
    margins = layout.margins(QtGui.QPageLayout.Unit.Inch)
    assert abs(margins.left() - 0.25) < 1e-6 and abs(margins.top() - 0.25) < 1e-6
    wide = page_layout({"paper": "a4", "landscape": True, "margin": "none"})
    assert wide is not None
    assert wide.orientation() == QtGui.QPageLayout.Orientation.Landscape
    assert wide.margins().left() == 0
    # "Fit to area": no paper, the page takes the picture's shape.
    assert page_layout({"paper": "fit"}) is None
