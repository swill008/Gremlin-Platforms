# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The device's background picture is made again whenever the background
changes (07 S157, D-07-BG-COMPOSITE): DevicePhotoMaker asks the QML host
for one picture at a time and saves it, with its background key, in the
device's folder. Here a fake host (a slot that writes a PNG to the path it
is given) stands in for DevicePhotoHost.qml.

- a stale or missing file is drawn and saved with the background's key;
- a current file, or a change to the foreground only, makes nothing;
- no visible background: the file goes;
- requests wait for the host; one job at a time;
- a failed or timed-out job is retried once, then waits for a change;
- a background changed while it was drawn is drawn again;
- the module-files notice runs the check; want() reaches the running maker;
- a maker let go after a job is freed at once: nothing it made holds it
  (a job timer's lambda used to, and the timer's later deletion then
  deleted the maker from inside the timer's own: Fatal Python error).
"""

from __future__ import annotations

import gc
import json
import time
import weakref
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from PySide6 import QtCore, QtGui

from gremlin.modules import store
from gremlin.ui import device_photo


def _settle(until: Callable[[], bool] | None = None, seconds: float = 2.0) -> None:
    """Runs the event loop until until() is true or seconds pass."""
    app = QtCore.QCoreApplication.instance()
    assert app is not None
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 20)
        if until is not None and until():
            return
        time.sleep(0.01)


@pytest.fixture
def modules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    base = tmp_path / "modules"
    base.mkdir()
    monkeypatch.setattr(store, "folder", lambda: base)
    store._dirs_changed()
    return base


@pytest.fixture
def notices(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """The module-files notices the maker sends, counted, not sent (a real
    notice left pending after a picture was saved keeps the test process
    from ending; the notice itself is test_owner_notices_senders.py's)."""
    sent: list[int] = []
    monkeypatch.setattr(store, "notify_module_files", lambda: sent.append(1))
    return sent


class _Host:
    """Records each job; answers at once with a 40 x 20 PNG when auto."""

    def __init__(self, maker: device_photo.DevicePhotoMaker) -> None:
        self.maker = maker
        self.jobs: list[tuple[str, str, str, int, str]] = []
        self.auto = True
        self.ok = True
        maker.renderWanted.connect(self._job)

    def _job(self, token: str, nodes: str, pictures: str, side: int, out: str) -> None:
        self.jobs.append((token, nodes, pictures, side, out))
        if self.auto:
            self.answer(len(self.jobs) - 1)

    def answer(self, index: int, ok: bool | None = None) -> None:
        token, _nodes, _pictures, _side, out = self.jobs[index]
        ok = self.ok if ok is None else ok
        if ok:
            # As DevicePhotoHost.qml does: the drawing on black at out and on
            # white beside it (an off-screen grab keeps no transparency).
            assert _drawn_on(QtGui.QColor("black")).save(out)
            white = device_photo.white_path(Path(out))
            assert _drawn_on(QtGui.QColor("white")).save(str(white))
        self.maker.rendered(token, ok)


def _drawn_on(ground: QtGui.QColor) -> QtGui.QImage:
    """40 x 20: an opaque red left half, nothing on the right half."""
    image = QtGui.QImage(40, 20, QtGui.QImage.Format.Format_RGB32)
    image.fill(ground)
    painter = QtGui.QPainter(image)
    painter.fillRect(0, 0, 20, 20, QtGui.QColor(255, 0, 0))
    painter.end()
    return image


def _temp_files() -> list[Path]:
    return sorted((store.folder() / "cache" / "device-photo").glob("*"))


@pytest.fixture
def maker(
    modules: Path, notices: list[int], qapp: QtCore.QCoreApplication
) -> Iterator[device_photo.DevicePhotoMaker]:
    made = device_photo.DevicePhotoMaker()
    yield made
    made.close()


@pytest.fixture
def host(maker: device_photo.DevicePhotoMaker) -> _Host:
    return _Host(maker)


def _device(name: str, nodes: list[dict]) -> Path:
    path = store.ensure_device_dir(name)
    (path / store.PICTURES).mkdir(exist_ok=True)
    image = QtGui.QImage(64, 32, QtGui.QImage.Format.Format_RGB32)
    image.fill(0x336699)
    assert image.save(str(path / store.PICTURES / "stick.png"))
    _write(path, nodes)
    return path


def _write(path: Path, nodes: list[dict]) -> None:
    doc = {"kind": "control.hardware", "device": path.name, "nodes": nodes}
    (path / store.MODULE_FILE).write_text(json.dumps(doc), encoding="utf-8")


def _bg(**extra: object) -> dict:
    node = {
        "id": "b1",
        "kind": "draw",
        "shape": "image",
        "src": "pictures/stick.png",
        "plane": "background",
        "fx": 0.2,
        "fy": 0.2,
        "fw": 0.3,
        "fh": 0.3,
    }
    node.update(extra)
    return node


_CHIP = {"id": "c1", "kind": "chip", "fx": 0.5, "fy": 0.5}


def _key_now(path: Path) -> str:
    return store.background_key(store.read_path(path / store.MODULE_FILE), path)


def test_a_missing_file_is_drawn_and_saved_with_the_background_key(
    maker: device_photo.DevicePhotoMaker, host: _Host, notices: list[int]
) -> None:
    path = _device("Stick One", [_bg(), dict(_CHIP)])
    maker.setProperty("hostReady", True)
    maker.request("Stick One", "")

    assert len(host.jobs) == 1
    token, nodes, pictures, side, out = host.jobs[0]
    assert token
    assert [n["id"] for n in json.loads(nodes)] == ["b1", "c1"]
    folder_url = QtCore.QUrl.fromLocalFile(str(path / "pictures")).toString()
    assert pictures == folder_url + "/"
    assert side == store.DEVICE_PHOTO_SIDE == 1024
    assert Path(out).parent == store.folder() / "cache" / "device-photo"
    assert _temp_files() == [], "both temporary files are removed"

    photo = store.device_photo_path(path)
    assert photo == path / "pictures" / "device-photo.png"
    assert photo.is_file()
    assert QtGui.QImageReader(str(photo)).text(store.DEVICE_PHOTO_KEY) == _key_now(path)
    assert store.device_photo_key(path) == _key_now(path)
    assert store.device_photo_current(path)
    assert notices == [1], "pages are told to read the photo again"

    saved = QtGui.QImage(str(photo))
    assert saved.size() == QtCore.QSize(40, 20)
    assert saved.hasAlphaChannel()
    drawn = saved.pixelColor(5, 5)
    assert (drawn.alpha(), drawn.red(), drawn.green()) == (255, 255, 0)
    assert saved.pixelColor(30, 5).alpha() == 0, "nothing drawn: transparent"


def test_the_matte_keeps_part_transparency() -> None:
    def half_red(ground: str) -> QtGui.QImage:
        image = QtGui.QImage(4, 4, QtGui.QImage.Format.Format_RGB32)
        image.fill(QtGui.QColor(ground))
        painter = QtGui.QPainter(image)
        painter.fillRect(0, 0, 4, 4, QtGui.QColor(255, 0, 0, 128))
        painter.end()
        return image

    out = device_photo.matte(half_red("black"), half_red("white"))
    color = out.pixelColor(1, 1)
    assert abs(color.alpha() - 128) <= 2
    assert color.red() >= 250 and color.green() <= 4 and color.blue() <= 4


def test_a_current_file_and_a_foreground_change_make_nothing(
    maker: device_photo.DevicePhotoMaker, host: _Host
) -> None:
    path = _device("Stick One", [_bg(), dict(_CHIP)])
    maker.setProperty("hostReady", True)
    maker.check_all()
    assert len(host.jobs) == 1

    maker.check_all()
    assert len(host.jobs) == 1, "a current file is not made again"

    _write(path, [_bg(), dict(_CHIP, fx=0.9)])
    maker.check_all()
    assert len(host.jobs) == 1, "chips moved: the background is as it was"

    _write(path, [_bg(fx=0.4), dict(_CHIP)])
    maker.check_all()
    assert len(host.jobs) == 2, "the background moved: made again"
    assert store.device_photo_key(path) == _key_now(path)


def test_no_visible_background_removes_the_file(
    maker: device_photo.DevicePhotoMaker, host: _Host, notices: list[int]
) -> None:
    path = _device("Stick One", [_bg()])
    maker.setProperty("hostReady", True)
    maker.check_all()
    assert store.device_photo_path(path).is_file()

    _write(path, [_bg(hidden=True), dict(_CHIP)])
    maker.check_all()
    assert not store.device_photo_path(path).exists()
    assert len(host.jobs) == 1
    assert len(notices) == 2, "made, then removed: pages told each time"
    maker.check_all()
    assert len(notices) == 2, "nothing left to remove: no notice"


def test_requests_wait_for_the_host(
    maker: device_photo.DevicePhotoMaker, host: _Host
) -> None:
    path = _device("Stick One", [_bg()])
    maker.request("Stick One", "")
    assert host.jobs == []
    assert not store.device_photo_path(path).exists()

    maker.setProperty("hostReady", True)
    assert len(host.jobs) == 1
    assert store.device_photo_current(path)


def test_one_job_at_a_time(maker: device_photo.DevicePhotoMaker, host: _Host) -> None:
    first = _device("Stick One", [_bg()])
    second = _device("Stick Two", [_bg()])
    host.auto = False
    maker.setProperty("hostReady", True)
    maker.check_all()
    maker.check_all()
    assert len(host.jobs) == 1, "the second waits for the first"

    host.answer(0)
    assert len(host.jobs) == 2
    host.answer(1)
    assert store.device_photo_current(first)
    assert store.device_photo_current(second)


def test_a_failed_job_is_retried_once_then_waits_for_a_change(
    maker: device_photo.DevicePhotoMaker, host: _Host
) -> None:
    path = _device("Stick One", [_bg()])
    host.ok = False
    maker.setProperty("hostReady", True)
    maker.check_all()
    maker.check_all()
    maker.check_all()
    assert len(host.jobs) == device_photo.TRIES == 2
    assert not store.device_photo_path(path).exists()
    assert _temp_files() == []

    host.ok = True
    _write(path, [_bg(fx=0.5)])
    maker.check_all()
    assert len(host.jobs) == 3
    assert store.device_photo_current(path)


def test_a_timed_out_job_is_dropped_and_a_late_answer_ignored(
    maker: device_photo.DevicePhotoMaker,
    host: _Host,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(device_photo, "JOB_TIMEOUT", 0.05)
    first = _device("Stick One", [_bg()])
    second = _device("Stick Two", [_bg()])
    host.auto = False
    maker.setProperty("hostReady", True)
    maker.check_all()
    _settle(lambda: len(host.jobs) == 2)
    assert len(host.jobs) == 2, "the next job starts after the timeout"

    host.answer(0)  # too late
    assert not store.device_photo_path(first).exists()
    host.answer(1)
    assert store.device_photo_current(second)
    assert _temp_files() == [], "the timed-out job's files went too"


def test_a_background_changed_while_drawn_is_drawn_again(
    maker: device_photo.DevicePhotoMaker, host: _Host
) -> None:
    path = _device("Stick One", [_bg()])
    host.auto = False
    maker.setProperty("hostReady", True)
    maker.check_all()
    _write(path, [_bg(fw=0.6)])
    host.answer(0)
    assert not store.device_photo_path(path).exists()
    assert len(host.jobs) == 2
    host.answer(1)
    assert store.device_photo_key(path) == _key_now(path)


class _Signals(QtCore.QObject):
    moduleFilesChanged = QtCore.Signal()


def test_the_module_files_notice_runs_the_check(
    modules: Path,
    notices: list[int],
    qapp: QtCore.QCoreApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The maker's own copy of the program signal: the real one also reaches
    # the program's other listeners, which re-read this folder's picture and
    # keep the test process from ending.
    fake = _Signals()
    monkeypatch.setattr(device_photo, "signal", fake)
    path = _device("Stick One", [_bg()])
    made = device_photo.DevicePhotoMaker()
    try:
        host = _Host(made)
        made.setProperty("hostReady", True)  # the start-up check waits 2 s
        fake.moduleFilesChanged.emit()
        assert len(host.jobs) == 1
        assert store.device_photo_current(path)
    finally:
        made.close()
    fake.moduleFilesChanged.emit()
    assert len(host.jobs) == 1, "closed: it no longer follows the notice"


def test_the_start_up_check_runs_once_the_host_is_ready(
    maker: device_photo.DevicePhotoMaker,
    host: _Host,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(device_photo, "START_DELAY", 0.05)
    path = _device("Stick One", [_bg()])
    maker.setProperty("hostReady", True)
    assert host.jobs == []
    _settle(lambda: store.device_photo_current(path))
    assert len(host.jobs) == 1


def test_want_reaches_the_running_maker_only(
    modules: Path,
    notices: list[int],
    qapp: QtCore.QCoreApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _device("Stick One", [_bg()])
    monkeypatch.setattr(device_photo, "_running", None)
    device_photo.want("Stick One", "")  # no maker: nothing happens

    made = device_photo.DevicePhotoMaker()
    try:
        host = _Host(made)
        made.setProperty("hostReady", True)
        device_photo.want("Stick One", "")
        assert len(host.jobs) == 1
        assert store.device_photo_current(path)
    finally:
        made.close()
    assert device_photo._running is None


def test_a_maker_let_go_after_a_job_is_freed_at_once(
    modules: Path, notices: list[int], qapp: QtCore.QCoreApplication
) -> None:
    path = _device("Stick One", [_bg()])
    made = device_photo.DevicePhotoMaker()
    host = _Host(made)
    made.setProperty("hostReady", True)
    made.request("Stick One", "")
    assert store.device_photo_current(path)
    made.close()
    gone = weakref.ref(made)
    del made, host
    gc.collect()
    assert gone() is None, "something the maker made still holds it"
    # Nothing it left waits to be deleted later.
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
