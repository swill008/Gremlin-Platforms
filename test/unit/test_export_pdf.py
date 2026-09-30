from pathlib import Path

from PySide6 import QtGui

from gremlin.ui.util import save_image_as_pdf


def test_writes_a_pdf(tmp_path: Path) -> None:
    image = QtGui.QImage(40, 30, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtGui.QColor("#3366CC"))
    target = tmp_path / "map.pdf"

    assert save_image_as_pdf(image, target)
    assert target.read_bytes().startswith(b"%PDF")
    assert not (tmp_path / "map.png").exists()


def test_empty_image_writes_nothing(tmp_path: Path) -> None:
    target = tmp_path / "map.pdf"

    assert not save_image_as_pdf(QtGui.QImage(), target)
    assert not target.exists()
