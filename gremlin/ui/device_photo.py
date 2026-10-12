# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The device's background picture (07 S157, D-07-BG-COMPOSITE): a picture
of the whole visible background plane, kept in the device's folder as
pictures/device-photo.png and shown as "the device's photo" everywhere
(07 S127).

DevicePhotoMaker decides which folders need it made again and asks the
hidden QML host (DevicePhotoHost.qml, the editor's own renderer) to draw
one job at a time; the store owns the file (store.background_key,
device_photo_key, write_device_photo, remove_device_photo). It follows
signal.moduleFilesChanged, so every write path that changes a background
(editor Save, Import Device, Restore Import, History restore, Device
Library restore, Module Setup's Import Image, the Logical Device card's
pictures) makes it again; a save that leaves the background as it was
makes nothing (the key is the same).

Main thread only; no thread of its own (program-thread-rules). Its two
timers (the start-up check, a job's time limit) are single-shot QTimers the
maker owns: they belong to the window, not to a Run, so a Run's Stop
(run_scope) neither cancels nor fires them, and they end with the maker.
Both are made once and connected to the maker's own slots: no lambda holds
the maker, and no timer is deleted later (a lambda on a deleteLater'd child
timer was the maker's last reference, so the timer's deletion deleted the
maker, which deleted the timer again: a Fatal Python error, Aborted).
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

import shiboken6
from PySide6 import QtCore, QtGui

import gremlin.ui.type_aliases as ta
from gremlin.modules import store
from gremlin.signal import signal

syslog = logging.getLogger("system")

# A job the host never answers is dropped after this (the renderer gives up
# on a picture that never loads after about 8 s).
JOB_TIMEOUT = 10.0
# A start-up check after the host is ready, for files made stale while the
# program was closed.
START_DELAY = 2.0
# Tries per folder and background key before it waits for the next change
# (a failed job is retried once, at the next check).
TRIES = 2

_running: DevicePhotoMaker | None = None


def want(device_name: str, guid: str) -> None:
    """The running maker's request(); nothing without one. profilePhotoUrl
    calls it when the file is missing or stale (07 S127 fallback)."""
    global _running
    if _running is None:
        return
    # The maker dies with its window or app (tests make many): a reference
    # left behind must not reach a deleted object.
    if not shiboken6.isValid(_running):
        _running = None
        return
    _running.request(device_name, guid)


def _temp_dir() -> Path:
    return store.folder() / "cache" / "device-photo"


class _Job:
    def __init__(self, folder: Path, key: str, token: str, out: Path) -> None:
        self.folder = folder
        self.key = key
        self.token = token
        self.out = out


class DevicePhotoMaker(QtCore.QObject):
    """Makes each device's background picture again when it is stale."""

    # token, the module file's nodes (JSON text), the pictures folder's URL
    # (ends in "/"), the longest side wanted, the PNG path to save to.
    renderWanted = QtCore.Signal(str, str, str, int, str)
    hostReadyChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        global _running
        super().__init__(parent)
        self._host_ready = False
        self._started = False
        self._queue: dict[str, Path] = {}
        self._job: _Job | None = None
        self._tries: dict[str, tuple[str, int]] = {}
        self._start_timer = QtCore.QTimer(self)
        self._start_timer.setSingleShot(True)
        self._start_timer.timeout.connect(self.check_all)
        self._job_timer = QtCore.QTimer(self)
        self._job_timer.setSingleShot(True)
        self._job_timer.timeout.connect(self._timed_out)
        signal.moduleFilesChanged.connect(self.check_all)
        _running = self

    def close(self) -> None:
        """Stops following module files and drops any waiting job (tests,
        and the program's end)."""
        global _running
        try:
            signal.moduleFilesChanged.disconnect(self.check_all)
        except (RuntimeError, TypeError):
            pass
        self._start_timer.stop()
        self._job_timer.stop()
        job, self._job = self._job, None
        if job is not None:
            self._drop(job)
        self._queue.clear()
        if _running is self:
            _running = None

    # --- the host ------------------------------------------------------------

    def _get_host_ready(self) -> bool:
        return self._host_ready

    def _set_host_ready(self, ready: bool) -> None:
        ready = bool(ready)
        if ready == self._host_ready:
            return
        self._host_ready = ready
        self.hostReadyChanged.emit()
        if ready and not self._started:
            self._started = True
            self._start_timer.start(int(START_DELAY * 1000))
        self._pump()

    hostReady = QtCore.Property(
        bool, fget=_get_host_ready, fset=_set_host_ready, notify=hostReadyChanged
    )

    # --- asking --------------------------------------------------------------

    def request(self, device_name: str, guid: str) -> None:
        """Queue one device; nothing when its file is current; its file is
        removed when it has no visible background."""
        try:
            path = store.device_dir(device_name, guid)
        except Exception:  # noqa: BLE001 - a lookup never stops a page
            syslog.exception(f"Device photo: no folder for {device_name}")
            return
        if path.is_dir():
            self._request_folder(path)
            self._pump()

    @QtCore.Slot()
    def check_all(self) -> None:
        """Every device folder: the stale ones are made again."""
        for path in store.device_dirs().values():
            self._request_folder(path)
        self._pump()

    def _request_folder(self, path: Path) -> None:
        name = str(path)
        if name in self._queue or (self._job and str(self._job.folder) == name):
            return
        doc = store.read_path(store.module_file_in(path))
        key = store.background_key(doc, path)
        if not key:
            self._tries.pop(name, None)
            if store.device_photo_path(path).exists():
                try:
                    store.remove_device_photo(path)
                except OSError:
                    syslog.exception(f"Device photo of {path.name} not removed")
                    return
                # Only a file that went sends the notice (no loop on a
                # file that can't be removed).
                if not store.device_photo_path(path).exists():
                    store.notify_module_files()
            return
        if store.device_photo_key(path) == key:
            self._tries.pop(name, None)
            return
        held = self._tries.get(name)
        if held is not None and held[0] == key and held[1] >= TRIES:
            return
        self._queue[name] = path

    # --- one job at a time -----------------------------------------------------

    def _pump(self) -> None:
        while self._job is None and self._host_ready and self._queue:
            name = next(iter(self._queue))
            path = self._queue.pop(name)
            doc = store.read_path(store.module_file_in(path))
            key = store.background_key(doc, path)
            if not key or store.device_photo_key(path) == key:
                continue
            token = uuid.uuid4().hex
            out = _temp_dir() / f"{token}.png"
            try:
                out.parent.mkdir(parents=True, exist_ok=True)
            except OSError:
                syslog.exception("Device photo: no temporary folder")
                return
            nodes = doc.get("nodes") if isinstance(doc, dict) else None
            self._job = _Job(path, key, token, out)
            self._job_timer.start(int(JOB_TIMEOUT * 1000))
            pictures = QtCore.QUrl.fromLocalFile(str(path / store.PICTURES)).toString()
            self.renderWanted.emit(
                token,
                json.dumps(nodes if isinstance(nodes, list) else []),
                pictures.rstrip("/") + "/",
                int(store.DEVICE_PHOTO_SIDE),
                str(out),
            )
            # The host may answer at once (inside emit); the loop then goes on.

    @QtCore.Slot()
    def _timed_out(self) -> None:
        job = self._job
        if job is None:
            return
        syslog.warning(f"Device photo of {job.folder.name}: no picture in time")
        self._failed(job)

    def _failed(self, job: _Job) -> None:
        name = str(job.folder)
        held = self._tries.get(name)
        count = held[1] + 1 if held is not None and held[0] == job.key else 1
        self._tries[name] = (job.key, count)
        self._job = None
        self._drop(job)
        self._pump()

    def _drop(self, job: _Job) -> None:
        """The job is over: its time limit and temporary files go."""
        self._job_timer.stop()
        for path in (job.out, white_path(job.out)):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass

    @QtCore.Slot(str, bool)
    def rendered(self, token: str, ok: bool) -> None:
        """The host saved the picture on black at the job's path and on
        white beside it (ok), or gave up."""
        job = self._job
        if job is None or job.token != token:
            # Timed out or closed meanwhile: its late files go.
            if token.isalnum():
                late = _temp_dir() / f"{token}.png"
                for path in (late, white_path(late)):
                    try:
                        path.unlink(missing_ok=True)
                    except OSError:
                        pass
            return
        self._job_timer.stop()
        if not ok:
            syslog.warning(f"Device photo of {job.folder.name}: not drawn")
            self._failed(job)
            return
        doc = store.read_path(store.module_file_in(job.folder))
        if store.background_key(doc, job.folder) != job.key:
            # The background changed while it was drawn: draw it again.
            self._job = None
            self._drop(job)
            self._request_folder(job.folder)
            self._pump()
            return
        data = _with_key(job.out, white_path(job.out), job.key)
        if data is None:
            syslog.warning(f"Device photo of {job.folder.name}: unreadable picture")
            self._failed(job)
            return
        try:
            store.write_device_photo(job.folder, data)
        except OSError:
            syslog.exception(f"Device photo of {job.folder.name} not saved")
            self._failed(job)
            return
        self._tries.pop(str(job.folder), None)
        self._job = None
        self._drop(job)
        # Cards, Module Setup, HidHide and the Library read the photo again;
        # the check this sends finds the file current (no loop).
        store.notify_module_files()
        self._pump()


def white_path(out: Path) -> Path:
    """Where the host saves the picture drawn on white: beside the one on
    black, "<name>.white.png" (an off-screen grab keeps no transparency)."""
    out = Path(out)
    return out.with_name(out.stem + ".white.png")


def matte(on_black: QtGui.QImage, on_white: QtGui.QImage) -> QtGui.QImage:
    """One transparent picture from the same drawing on black and on white:
    alpha is 255 minus the difference between the two, the colour the one
    on black (already premultiplied by that alpha)."""
    black = on_black.convertToFormat(QtGui.QImage.Format.Format_RGB32)
    diff = on_white.convertToFormat(QtGui.QImage.Format.Format_RGB32)
    painter = QtGui.QPainter(diff)
    painter.setCompositionMode(
        QtGui.QPainter.CompositionMode.CompositionMode_Difference
    )
    painter.drawImage(0, 0, black)
    painter.end()
    diff.invertPixels()
    out = bytearray(bytes(black.constBits()))
    # Green of the inverted difference (all three channels match for a
    # drawing on black and on white) as alpha.
    out[3::4] = bytes(diff.constBits())[1::4]
    image = QtGui.QImage(
        bytes(out),
        black.width(),
        black.height(),
        black.bytesPerLine(),
        QtGui.QImage.Format.Format_ARGB32_Premultiplied,
    )
    return image.convertToFormat(QtGui.QImage.Format.Format_ARGB32)


def _with_key(on_black: Path, on_white: Path, key: str) -> bytes | None:
    """The transparent PNG made from the two pictures, with the background
    key in its text chunk; None when either is unreadable or they differ
    in size."""
    black = QtGui.QImage(str(on_black))
    white = QtGui.QImage(str(on_white))
    if black.isNull() or white.isNull() or black.size() != white.size():
        return None
    image = matte(black, white)
    image.setText(store.DEVICE_PHOTO_KEY, key)
    data = QtCore.QByteArray()
    buffer = QtCore.QBuffer(data)
    buffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
    saved = image.save(buffer, "PNG")  # pyright: ignore[reportCallIssue, reportArgumentType]
    buffer.close()
    return bytes(data.data()) if saved else None
