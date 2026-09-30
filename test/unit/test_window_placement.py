# -*- coding: utf-8; -*-
from pathlib import Path
from unittest.mock import patch

_SRC = Path(__file__).resolve().parents[2] / "gremlin/ui/window_placement.py"


class _Screen:
    def __init__(self, x: int, y: int, w: int, h: int) -> None:
        from PySide6 import QtCore
        self._avail = QtCore.QRect(x, y, w, h)

    def availableGeometry(self):  # noqa: ANN201, N802
        return self._avail


def _margins():  # noqa: ANN202
    from PySide6 import QtCore
    return QtCore.QMargins(8, 31, 8, 8)


def test_saved_spot_on_screen_is_kept() -> None:
    from PySide6 import QtCore
    from gremlin.ui import window_placement as wp
    screen = _Screen(0, 0, 3412, 1440)
    saved = QtCore.QRect(607, 210, 1346, 813)
    with patch.object(wp, "_available_screens", return_value=[screen]):
        assert wp._placed_screen(saved) is screen
    assert wp._fit_client(saved, screen, _margins()) == saved


def test_title_bar_above_the_screen_is_moved_down() -> None:
    from PySide6 import QtCore
    from gremlin.ui import window_placement as wp
    screen = _Screen(0, 0, 3412, 1440)
    fitted = wp._fit_client(QtCore.QRect(500, 10, 1346, 813), screen, _margins())
    assert (fitted.x(), fitted.y()) == (500, 31)


def test_spot_on_a_missing_monitor_is_not_used() -> None:
    from PySide6 import QtCore
    from gremlin.ui import window_placement as wp
    saved = QtCore.QRect(4000, 200, 1346, 813)
    with patch.object(wp, "_available_screens", return_value=[_Screen(0, 0, 3412, 1440)]):
        assert wp._placed_screen(saved) is None


def test_first_launch_is_centered() -> None:
    from PySide6 import QtCore
    from gremlin.ui import window_placement as wp
    assert wp._never_placed(QtCore.QRect(0, 0, wp.DEFAULT_W, wp.DEFAULT_H))
    assert not wp._never_placed(QtCore.QRect(0, 0, 1346, 813))


def test_too_big_window_is_shrunk_to_the_work_area() -> None:
    from PySide6 import QtCore
    from gremlin.ui import window_placement as wp
    screen = _Screen(0, 0, 1920, 1040)
    fitted = wp._fit_client(QtCore.QRect(100, 100, 2400, 1400), screen, _margins())
    assert fitted == QtCore.QRect(8, 31, 1920 - 16, 1040 - 39)


def test_catalog_display_options_persist() -> None:
    text = _SRC.read_text(encoding="utf-8")
    assert 'KEY_CATALOG_PANEL = "catalog-display-options-open"' in text
    assert "def catalogPanelOpen" in text
    assert "def setCatalogPanelOpen" in text
    main = Path(__file__).resolve().parents[2] / "qml/Main.qml"
    qml = main.read_text(encoding="utf-8")
    assert "catalogPanel = _windowPlacement.catalogPanelOpen()" in qml
    assert "onCatalogPanelChanged: _windowPlacement.setCatalogPanelOpen(catalogPanel)" in qml
    close = qml[qml.find("function closeWorkRoom") : qml.find("function requestNewProfile")]
    assert "catalogPanel = false" not in close
