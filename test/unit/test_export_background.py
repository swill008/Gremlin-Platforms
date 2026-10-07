# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Button Map exports are encoded and written in the background (07 S101,
D-07-EXPORT-BG): saveAreaAsync returns at once, exporting is True until
areaSaved(ok, error) is announced on the main thread, one export at a time,
failures say what Q19 says."""

from __future__ import annotations

import sys

sys.path.append(".")

import pathlib
import threading
from collections.abc import Iterator

import pytest
from PySide6 import (
    QtCore,
    QtGui,
)

from gremlin import threads
from gremlin.ui import hardware_profile
from gremlin.ui.hardware_profile import HardwareProfile, export_failure

WAIT_MS = 10000


def _area_picture(w: int = 120, h: int = 60) -> QtGui.QImage:
    """A grab of the print area: dark, a red block in its right half."""
    image = QtGui.QImage(w, h, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtGui.QColor("#102030"))
    painter = QtGui.QPainter(image)
    painter.fillRect(w // 2, 0, w - w // 2, h, QtGui.QColor("#FF0000"))
    painter.end()
    return image


def _url(path: pathlib.Path) -> str:
    return QtCore.QUrl.fromLocalFile(str(path)).toString()


class _SlowEncoder:
    """save_area held until released: where it ran and on what."""

    def __init__(self) -> None:
        self.entered = threading.Event()
        self.release = threading.Event()
        self.thread: threading.Thread | None = None
        self.calls = 0
        self._real = hardware_profile.save_area

    def __call__(self, *args: object, **kwargs: object) -> bool:
        self.calls += 1
        self.thread = threading.current_thread()
        self.entered.set()
        # Bounded: a test that fails never leaves the worker waiting.
        self.release.wait(WAIT_MS / 1000)
        return self._real(*args, **kwargs)  # type: ignore[arg-type]


@pytest.fixture
def slow(monkeypatch: pytest.MonkeyPatch) -> Iterator[_SlowEncoder]:
    encoder = _SlowEncoder()
    monkeypatch.setattr(hardware_profile, "save_area", encoder)
    yield encoder
    encoder.release.set()
    if encoder.thread is not None:
        encoder.thread.join(WAIT_MS / 1000)


def _export_threads() -> list[str]:
    return [n for n in threads.running() if "export" in n.lower()]


def test_returns_at_once_and_the_window_stays_responsive(
    qtbot: object, slow: _SlowEncoder, tmp_path: pathlib.Path
) -> None:
    profile = HardwareProfile()
    target = tmp_path / "map.png"
    changes: list[bool] = []
    profile.exportingChanged.connect(lambda: changes.append(profile.exporting))
    announced: list[tuple[bool, str, threading.Thread]] = []
    profile.areaSaved.connect(
        lambda ok, err: announced.append((ok, err, threading.current_thread()))
    )

    assert profile.saveAreaAsync(_area_picture(), 120, 60, _url(target), "png", "{}")
    assert profile.exporting
    assert slow.entered.wait(WAIT_MS / 1000)
    # Encoding on a named program thread, not the main one.
    assert slow.thread is not None
    assert slow.thread is not threading.main_thread()
    assert slow.thread.name.startswith(threads.PREFIX)
    assert slow.thread.name in threads.running()
    # The main thread still runs Qt events while the encoder is held.
    ticked: list[bool] = []
    QtCore.QTimer.singleShot(0, lambda: ticked.append(True))
    qtbot.waitUntil(lambda: bool(ticked), timeout=WAIT_MS)  # type: ignore[attr-defined]
    assert profile.exporting
    assert not announced
    assert not target.exists()

    with qtbot.waitSignal(profile.areaSaved, timeout=WAIT_MS) as blocker:  # type: ignore[attr-defined]
        slow.release.set()
    assert blocker.args == [True, ""]
    assert announced[0][2] is threading.main_thread()
    assert not profile.exporting
    assert changes == [True, False]
    assert profile.exportError() == ""
    assert QtGui.QImage(str(target)).size() == QtCore.QSize(120, 60)
    qtbot.waitUntil(lambda: not _export_threads(), timeout=WAIT_MS)  # type: ignore[attr-defined]


def test_one_export_at_a_time(
    qtbot: object, slow: _SlowEncoder, tmp_path: pathlib.Path
) -> None:
    profile = HardwareProfile()
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"

    assert profile.saveAreaAsync(_area_picture(), 120, 60, _url(first), "png", "{}")
    assert slow.entered.wait(WAIT_MS / 1000)
    assert not profile.saveAreaAsync(
        _area_picture(), 120, 60, _url(second), "png", "{}"
    )
    with qtbot.waitSignal(profile.areaSaved, timeout=WAIT_MS):  # type: ignore[attr-defined]
        slow.release.set()
    assert slow.calls == 1
    assert first.exists()
    assert not second.exists()
    # Once it is done the next one may start.
    with qtbot.waitSignal(profile.areaSaved, timeout=WAIT_MS) as blocker:  # type: ignore[attr-defined]
        assert profile.saveAreaAsync(
            _area_picture(), 120, 60, _url(second), "png", "{}"
        )
    assert blocker.args == [True, ""]
    assert second.exists()


def test_the_picture_is_copied_when_the_export_starts(
    qtbot: object, slow: _SlowEncoder, tmp_path: pathlib.Path
) -> None:
    profile = HardwareProfile()
    target = tmp_path / "copy.png"
    image = _area_picture()

    assert profile.saveAreaAsync(image, 120, 60, _url(target), "png", "{}")
    assert slow.entered.wait(WAIT_MS / 1000)
    # The window drawing on its picture again doesn't reach the export.
    image.fill(QtGui.QColor("#00FF00"))
    with qtbot.waitSignal(profile.areaSaved, timeout=WAIT_MS):  # type: ignore[attr-defined]
        slow.release.set()
    saved = QtGui.QImage(str(target))
    assert saved.pixelColor(100, 30).name() == "#ff0000"
    assert saved.pixelColor(2, 2).name() == "#102030"


def test_a_write_failure_says_which_file_and_why(
    qtbot: object, tmp_path: pathlib.Path
) -> None:
    profile = HardwareProfile()
    target = tmp_path / "missing" / "map.png"

    with qtbot.waitSignal(profile.areaSaved, timeout=WAIT_MS) as blocker:  # type: ignore[attr-defined]
        assert profile.saveAreaAsync(
            _area_picture(), 120, 60, _url(target), "png", "{}"
        )
    ok, error = blocker.args
    assert ok is False
    assert error == export_failure(target)
    assert error.startswith("Export failed. map.png could not be written to ")
    assert "the folder does not exist" in error
    assert profile.exportError() == error
    assert not profile.exporting
    # The next one that works clears it.
    good = tmp_path / "map.png"
    with qtbot.waitSignal(profile.areaSaved, timeout=WAIT_MS) as blocker:  # type: ignore[attr-defined]
        assert profile.saveAreaAsync(_area_picture(), 120, 60, _url(good), "png", "{}")
    assert blocker.args == [True, ""]
    assert profile.exportError() == ""


def test_an_encoder_error_is_a_failure_not_a_stuck_export(
    qtbot: object, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    def broken(*_args: object, **_kwargs: object) -> bool:
        raise RuntimeError("encoder broke")

    monkeypatch.setattr(hardware_profile, "save_area", broken)
    profile = HardwareProfile()
    target = tmp_path / "map.png"

    with qtbot.waitSignal(profile.areaSaved, timeout=WAIT_MS) as blocker:  # type: ignore[attr-defined]
        assert profile.saveAreaAsync(
            _area_picture(), 120, 60, _url(target), "png", "{}"
        )
    assert blocker.args[0] is False
    assert blocker.args[1].startswith("Export failed. map.png")
    assert not profile.exporting


def test_pdf_in_the_background(qtbot: object, tmp_path: pathlib.Path) -> None:
    profile = HardwareProfile()
    target = tmp_path / "fit.pdf"

    with qtbot.waitSignal(profile.areaSaved, timeout=WAIT_MS) as blocker:  # type: ignore[attr-defined]
        assert profile.saveAreaAsync(
            _area_picture(192, 96), 192, 96, _url(target), "pdf", '{"paper": "fit"}'
        )
    assert blocker.args == [True, ""]
    data = target.read_bytes()
    assert data.startswith(b"%PDF")
    assert b"/MediaBox [0 0 144.000000 72.000000]" in data
    qtbot.waitUntil(lambda: not _export_threads(), timeout=WAIT_MS)  # type: ignore[attr-defined]


def test_the_old_save_area_still_saves_at_once(tmp_path: pathlib.Path) -> None:
    profile = HardwareProfile()
    target = tmp_path / "sync.png"
    assert profile.saveArea(_area_picture(), 120, 60, _url(target), "png", "{}")
    assert target.exists()
    assert not profile.exporting
