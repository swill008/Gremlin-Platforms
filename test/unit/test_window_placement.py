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


# Tool windows (D-01-TOOL-WINDOW-FIT): a mixed-DPI run asked for Module Setup
# at 1225 x 1296 on a 1080-high screen; the client area was fitted, so the
# title bar and borders fell off the screen and Qt refused the geometry.

class _DprScreen(_Screen):
    def __init__(self, x: int, y: int, w: int, h: int, dpr: float = 1.0) -> None:
        super().__init__(x, y, w, h)
        self._dpr = dpr

    def devicePixelRatio(self) -> float:  # noqa: N802
        return self._dpr


class _ToolWindow:
    def __init__(self, min_w: int = 0, min_h: int = 0, dpr: float = 1.0) -> None:
        from PySide6 import QtCore
        self.geometry = None
        self.minimum = QtCore.QSize(min_w, min_h)
        self._dpr = dpr

    def minimumSize(self) -> "QtCore.QSize":  # noqa: F821, N802
        return self.minimum

    def setMinimumWidth(self, w: int) -> None:  # noqa: N802
        self.minimum.setWidth(w)

    def setMinimumHeight(self, h: int) -> None:  # noqa: N802
        self.minimum.setHeight(h)

    def frameMargins(self) -> "QtCore.QMargins":  # noqa: F821, N802
        return _margins()

    def devicePixelRatio(self) -> float:  # noqa: N802
        return self._dpr

    def isVisible(self) -> bool:  # noqa: N802
        return False

    def setWindowStates(self, _states) -> None:  # noqa: ANN001, N802
        pass

    def setGeometry(self, rect) -> None:  # noqa: ANN001, N802
        self.geometry = rect


def _restore(entry: dict, screens: list, window: _ToolWindow, cursor_screen=None):  # noqa: ANN001, ANN202
    from gremlin.ui import window_placement as wp
    with patch.object(wp, "_ensure", return_value=None), \
            patch.object(wp, "_tool_map", return_value={"tool": entry}), \
            patch.object(wp, "_available_screens", return_value=screens), \
            patch.object(wp, "_screen_at", return_value=cursor_screen or screens[0]):
        wp.restore_tool(window, "tool", 900, 700)
    return window.geometry


def _frame_inside(rect, screen) -> bool:  # noqa: ANN001
    m = _margins()
    frame = rect.adjusted(-m.left(), -m.top(), m.right(), m.bottom())
    return screen.availableGeometry().contains(frame)


def test_saved_tool_window_taller_than_the_screen_keeps_its_frame_inside() -> None:
    screen = _DprScreen(0, 0, 1920, 1080)
    entry = {"x": 100, "y": 0, "w": 1225, "h": 1296}
    got = _restore(entry, [screen], _ToolWindow())
    assert _frame_inside(got, screen), got


def test_centred_tool_window_keeps_its_frame_inside() -> None:
    screen = _DprScreen(0, 0, 1920, 1080)
    got = _restore({"w": 1225, "h": 1296}, [screen], _ToolWindow())
    assert _frame_inside(got, screen), got


def test_tool_window_goes_to_the_screen_showing_most_of_it() -> None:
    left = _DprScreen(0, 0, 1920, 1080)
    right = _DprScreen(1920, 0, 1920, 1080)
    # 420 px on the left screen (enough to count), 580 px on the right.
    entry = {"x": 1500, "y": 100, "w": 1000, "h": 600}
    got = _restore(entry, [left, right], _ToolWindow())
    assert _frame_inside(got, right), got


def test_smallest_size_is_lowered_to_fit_the_work_area() -> None:
    screen = _DprScreen(0, 0, 1920, 1080)
    window = _ToolWindow(min_w=1225, min_h=1296)
    got = _restore({"x": 100, "y": 0, "w": 1225, "h": 1296}, [screen], window)
    m = _margins()
    assert window.minimum.height() <= 1080 - m.top() - m.bottom()
    assert _frame_inside(got, screen), got


def test_frame_is_measured_in_the_target_screens_units() -> None:
    from PySide6 import QtCore

    from gremlin.ui import window_placement as wp
    window = _ToolWindow(dpr=1.5)
    margins = wp._margins_on(window, _DprScreen(0, 0, 1920, 1080, dpr=1.0))
    assert margins == QtCore.QMargins(12, 46, 12, 12)
