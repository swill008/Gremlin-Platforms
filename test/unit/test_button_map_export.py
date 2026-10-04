# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Button Map export: RigRenderer's picture of the print area (already on
its background) written as PNG, JPG or PDF at exactly the size Print &
Export gives, whatever size the grab came back at."""

from __future__ import annotations

import sys

sys.path.append(".")

import pathlib

from PySide6 import (
    QtCore,
    QtGui,
)

from gremlin.ui.hardware_profile import (
    HardwareProfile,
    exact_page,
    save_area,
)


def _area_picture(w: int = 120, h: int = 60, dpr: float = 1.0) -> QtGui.QImage:
    """A grab of the print area: dark, a red block in its right half."""
    image = QtGui.QImage(w, h, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtGui.QColor("#102030"))
    painter = QtGui.QPainter(image)
    painter.fillRect(w // 2, 0, w - w // 2, h, QtGui.QColor("#FF0000"))
    painter.end()
    image.setDevicePixelRatio(dpr)
    return image


def test_png_is_the_area_at_its_size(tmp_path: pathlib.Path) -> None:
    target = tmp_path / "map.png"

    assert save_area(_area_picture(), 120, 60, target, "png")
    saved = QtGui.QImage(str(target))
    assert saved.size() == QtCore.QSize(120, 60)
    assert saved.pixelColor(100, 30).name() == "#ff0000"
    assert saved.pixelColor(2, 2).name() == "#102030"
    assert saved.pixelColor(2, 2).alpha() == 255


def test_a_grab_a_pixel_off_comes_out_exact(tmp_path: pathlib.Path) -> None:
    # A grab on a 150% screen: 181 x 90 pixels for 180 x 90 asked.
    page = exact_page(_area_picture(181, 90, 1.5), 180, 90)
    assert page is not None
    assert page.size() == QtCore.QSize(180, 90)
    assert page.devicePixelRatio() == 1.0
    # The whole picture is kept (scaled), not cut: the red half stays half.
    assert page.pixelColor(85, 45).name() == "#102030"
    assert page.pixelColor(95, 45).name() == "#ff0000"


def test_jpg(tmp_path: pathlib.Path) -> None:
    target = tmp_path / "map.jpg"

    assert save_area(_area_picture(), 120, 60, target, "jpg")
    saved = QtGui.QImage(str(target))
    assert saved.size() == QtCore.QSize(120, 60)
    assert saved.pixelColor(100, 30).red() > 200


def test_pdf_without_a_paper_is_96_pixels_an_inch(tmp_path: pathlib.Path) -> None:
    target = tmp_path / "fit.pdf"

    assert save_area(_area_picture(192, 96), 192, 96, target, "pdf", {"paper": "fit"})
    data = target.read_bytes()
    assert data.startswith(b"%PDF")
    # 192 x 96 pixels = 2 x 1 inches = 144 x 72 points.
    assert b"/MediaBox [0 0 144.000000 72.000000]" in data


def test_nothing_to_write_writes_nothing(tmp_path: pathlib.Path) -> None:
    target = tmp_path / "map.png"

    assert not save_area(QtGui.QImage(), 10, 10, target, "png")
    assert not save_area(_area_picture(), 0, 10, target, "png")
    assert not target.exists()


def test_save_area_slot(tmp_path: pathlib.Path) -> None:
    profile = HardwareProfile()
    url = QtCore.QUrl.fromLocalFile(str(tmp_path / "slot.png")).toString()
    assert profile.saveArea(_area_picture(), 120, 60, url, "png", "{}")
    assert QtGui.QImage(str(tmp_path / "slot.png")).size() == QtCore.QSize(120, 60)


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
    assert hasattr(HardwareProfile, "printImage")


def test_pdf_on_a_paper_is_that_page(tmp_path: pathlib.Path) -> None:
    from gremlin.ui.util import page_layout

    target = tmp_path / "letter.pdf"
    setup = {"paper": "letter", "landscape": False, "margin": "quarter"}
    assert save_area(_area_picture(), 120, 60, target, "pdf", setup)
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
    # "Freeform (As Drawn)": no paper, the page takes the picture's shape.
    assert page_layout({"paper": "fit"}) is None
