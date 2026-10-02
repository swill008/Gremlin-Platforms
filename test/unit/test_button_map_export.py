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

from gremlin.ui.hardware_profile import save_page_image


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
