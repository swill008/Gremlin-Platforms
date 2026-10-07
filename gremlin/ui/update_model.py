# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Checks for, downloads and installs updates for the Update dialog.

Network calls run through QNetworkAccessManager so the window never waits on
GitHub. The installer only runs after Gremlin has shut down (see main()).
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

from PySide6 import (
    QtCore,
    QtGui,
    QtNetwork,
)

from gremlin import (
    updater,
    util,
)
from gremlin.config import Configuration
from gremlin.signal import signal

_CHECK_TIMEOUT_MS = 10000
_DOWNLOAD_STALL_MS = 30000

# The update being installed: set just before setup starts, read and cleared
# on the next start. Still on an older version then means setup failed and
# put the previous version back.
_PENDING = ("global", "internal", "update-pending-version")
_PENDING_SETUP = ("global", "internal", "update-pending-setup")


def _register(config: Configuration) -> None:
    """The settings the update keeps between runs (registering again
    changes nothing)."""
    from gremlin.types import PropertyType

    config.register(
        *_PENDING, PropertyType.String, "",
        "Version the in-app update was installing (checked on the next start).", {},
    )
    config.register(
        *_PENDING_SETUP, PropertyType.String, "",
        "Installer the in-app update ran (its log is beside it).", {},
    )


def _one_off_request(url: str) -> QtNetwork.QNetworkRequest:
    """A request whose connection closes when the reply is done. Kept open
    for reuse, GitHub closes it about 30 s later and Qt prints
    "QIODevice::read (QSslSocket): device not open"; the program makes one
    request at a time, so there is nothing to reuse it for."""
    request = QtNetwork.QNetworkRequest(QtCore.QUrl(url))
    request.setAttribute(
        QtNetwork.QNetworkRequest.Attribute.Http2AllowedAttribute, False
    )
    request.setRawHeader(b"Connection", b"close")
    return request

class UpdateModel(QtCore.QObject):
    """State of the update check, shown by DialogUpdate.qml.

    state: "idle", "checking", "upToDate", "available", "downloading",
    "ready" (downloaded and verified), "error" or "failed" (the last update
    did not finish; the previous version was put back).
    """

    changed = QtCore.Signal()
    progressChanged = QtCore.Signal()
    notesChanged = QtCore.Signal()
    # A newer release the user should hear about: QML opens the dialog.
    offerUpdate = QtCore.Signal()
    # The verified installer is ready: QML quits through the normal path.
    installRequested = QtCore.Signal()

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._config = Configuration()
        _register(self._config)
        self._network = QtNetwork.QNetworkAccessManager(self)
        self._state = "idle"
        self._error = ""
        self._release: updater.Release | None = None
        self._manual = False
        self._reply: QtNetwork.QNetworkReply | None = None
        self._file: QtCore.QFile | None = None
        # Why the download couldn't be saved (a full disk), or "".
        self._write_error = ""
        self._received = 0
        self._ready_path: Path | None = None
        self._install_on_exit = False
        # The update that didn't finish (state "failed"), and its setup log.
        self._failed_version = ""
        self._failed_log = ""
        # Try Again after a failed update: install as soon as the check
        # finds that version.
        self._retry = False
        # Release notes of the offered version(s), Markdown (01 S133), and
        # whether the releases list is still on its way.
        self._notes = ""
        self._notes_loading = False
        # The releases-list request on its way, and the release it is for;
        # a new check abandons it.
        self._notes_reply: QtNetwork.QNetworkReply | None = None
        self._notes_release: updater.Release | None = None
        self._kind = updater.install_kind(
            bool(getattr(sys, "frozen", False)), Path(sys.executable).parent
        )

    # --- properties ---------------------------------------------------------

    @QtCore.Property(str, notify=changed)
    def state(self) -> str:
        return self._state

    @QtCore.Property(str, notify=changed)
    def errorText(self) -> str:
        return self._error

    @QtCore.Property(str, constant=True)
    def currentVersion(self) -> str:
        return util.get_code_version()

    @QtCore.Property(str, notify=changed)
    def latestVersion(self) -> str:
        return self._release.version if self._release else ""

    @QtCore.Property(str, notify=changed)
    def releasePageUrl(self) -> str:
        return self._release.page_url if self._release else updater.RELEASES_PAGE_URL

    @QtCore.Property(str, notify=changed)
    def failedVersion(self) -> str:
        return self._failed_version

    @QtCore.Property(str, notify=changed)
    def failedLog(self) -> str:
        return self._failed_log

    @QtCore.Property(str, constant=True)
    def installKind(self) -> str:
        return self._kind

    @QtCore.Property(bool, notify=changed)
    def canInstall(self) -> bool:
        """True when this copy can update itself to the offered release."""
        return (
            self._kind == updater.INSTALLED
            and self._release is not None
            and self._release.setup is not None
        )

    @QtCore.Property(str, notify=notesChanged)
    def releaseNotes(self) -> str:
        """The offered release's notes (and those of the versions between),
        newest first, as safe Markdown; "" when there are none to show."""
        return self._notes

    @QtCore.Property(bool, notify=notesChanged)
    def notesLoading(self) -> bool:
        return self._notes_loading

    @QtCore.Property(float, notify=progressChanged)
    def progress(self) -> float:
        if not self._release or not self._release.setup:
            return 0.0
        return min(1.0, self._received / max(1, self._release.setup.size))

    # --- checking -----------------------------------------------------------

    def startup(self) -> None:
        """Run once the main window is up: say so after an update, then check
        if the user wants startup checks."""
        if self._note_failed_update():
            return
        self._note_finished_update()
        if self._config.value("global", "general", "check-for-updates"):
            self.check(False)

    @QtCore.Slot(bool)
    def check(self, manual: bool) -> None:
        if self._state in ("checking", "downloading"):
            return
        self._manual = bool(manual)
        self._abandon_notes()
        self._set_notes("", False)
        # Tests and off-screen checks set this: nothing goes out.
        if os.environ.get("GREMLIN_OFFLINE"):
            self._fail("Offline: the update check is turned off here.")
            return
        self._set_state("checking")
        url = updater.feed_url(
            self._config.value("global", "internal", "update-feed-url")
        )
        request = _one_off_request(url)
        request.setRawHeader(b"Accept", b"application/vnd.github+json")
        request.setRawHeader(b"User-Agent", b"Gremlin-Platforms")
        request.setTransferTimeout(_CHECK_TIMEOUT_MS)
        reply = self._network.get(request)
        reply.finished.connect(lambda: self._on_checked(reply))

    def _on_checked(self, reply: QtNetwork.QNetworkReply) -> None:
        reply.deleteLater()
        if reply.error() != QtNetwork.QNetworkReply.NetworkError.NoError:
            self._fail(f"Could not reach GitHub: {reply.errorString()}")
            return
        try:
            doc = json.loads(bytes(reply.readAll().data()).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            doc = None
        release = updater.parse_release(doc)
        if release is None:
            self._fail("GitHub did not report a release version.")
            return
        self._release = release
        retry, self._retry = self._retry, False
        if retry and release.version == self._failed_version and self.canInstall:
            self.download()
            return
        skipped = self._config.value("global", "internal", "skipped-update-version")
        if updater.should_offer(
            release.version, self.currentVersion, skipped, self._manual
        ):
            self._fetch_notes(release)
            self._set_state("available")
            self.offerUpdate.emit()
        else:
            self._set_state("upToDate")

    # --- release notes (01 S133) --------------------------------------------

    def _fetch_notes(self, release: updater.Release) -> None:
        """Show the release's own notes now, then ask GitHub for the list so
        the versions in between show too. The window never waits on it."""
        self._set_notes(
            updater.notes_markdown([(release.version, release.notes)]), False
        )
        url = updater.notes_url(
            updater.feed_url(
                self._config.value("global", "internal", "update-feed-url")
            )
        )
        self._abandon_notes()
        # Tests and off-screen checks set this: nothing goes out (older tests
        # hand the model the check's reply directly).
        if not url or os.environ.get("GREMLIN_OFFLINE"):
            return
        request = _one_off_request(url)
        request.setRawHeader(b"Accept", b"application/vnd.github+json")
        request.setRawHeader(b"User-Agent", b"Gremlin-Platforms")
        request.setTransferTimeout(_CHECK_TIMEOUT_MS)
        reply = self._network.get(request)
        self._notes_reply = reply
        self._notes_release = release
        # A bound slot, not a lambda: Qt drops the connection when the model
        # goes, so a late reply never reaches a deleted model.
        reply.finished.connect(self._on_notes)
        self._set_notes(self._notes, True)

    def _abandon_notes(self) -> None:
        """Stop the releases-list request on its way (a new check started);
        its reply is never read."""
        reply, self._notes_reply = self._notes_reply, None
        self._notes_release = None
        if reply is None:
            return
        try:
            reply.finished.disconnect(self._on_notes)
        except (RuntimeError, TypeError):
            pass
        try:
            reply.abort()
            reply.deleteLater()
        except RuntimeError:
            pass  # already gone

    @QtCore.Slot()
    def _on_notes(self) -> None:
        reply, self._notes_reply = self._notes_reply, None
        release, self._notes_release = self._notes_release, None
        if reply is None or release is None:
            return
        try:
            reply.deleteLater()
            self._read_notes(reply, release)
        except Exception:
            # Notes are extra: a bad reply never stops the update.
            logging.getLogger("system").exception("Update: release notes")
            self._set_notes(self._notes, False)

    def _read_notes(
        self, reply: QtNetwork.QNetworkReply, release: updater.Release
    ) -> None:
        docs = None
        if reply.error() == QtNetwork.QNetworkReply.NetworkError.NoError:
            try:
                docs = json.loads(bytes(reply.readAll().data()).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                docs = None
        else:
            logging.getLogger("system").info(
                "Update: no release list: %s", reply.errorString()
            )
        entries = updater.newer_notes(
            docs, util.get_code_version(), release.version
        )
        if not any(version == release.version for version, _ in entries):
            entries.insert(0, (release.version, release.notes))
        self._set_notes(updater.notes_markdown(entries), False)

    def _set_notes(self, notes: str, loading: bool) -> None:
        if (notes, loading) == (self._notes, self._notes_loading):
            return
        self._notes = notes
        self._notes_loading = loading
        self.notesChanged.emit()

    def _fail(self, text: str) -> None:
        logging.getLogger("system").warning("Update: %s", text)
        self._error = text
        self._set_state("error")
        # A startup check stays quiet; only a check the user asked for says why.
        if self._manual:
            self.offerUpdate.emit()

    # --- user choices -------------------------------------------------------

    @QtCore.Slot()
    def skipVersion(self) -> None:
        if self._release:
            self._config.set(
                "global", "internal", "skipped-update-version", self._release.version
            )

    @QtCore.Slot()
    def openReleasePage(self) -> None:
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(self.releasePageUrl))

    @QtCore.Slot()
    def download(self) -> None:
        if not self.canInstall or self._state == "downloading":
            return
        setup = self._release.setup
        folder = updater.updates_dir()
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self._fail(f"Could not save the download to {folder}: {exc}")
            return
        target = folder / setup.name
        if updater.file_matches(target, setup.size, setup.sha256):
            self._ready(target)
            return
        self._file = QtCore.QFile(str(target.with_suffix(".part")))
        if not self._file.open(QtCore.QIODevice.OpenModeFlag.WriteOnly):
            self._file = None
            self._fail(f"Could not write to {folder}.")
            return
        self._write_error = ""
        self._received = 0
        self.progressChanged.emit()
        request = _one_off_request(setup.url)
        request.setRawHeader(b"User-Agent", b"Gremlin-Platforms")
        request.setTransferTimeout(_DOWNLOAD_STALL_MS)
        self._reply = self._network.get(request)
        self._reply.readyRead.connect(self._on_data)
        self._reply.downloadProgress.connect(self._on_progress)
        self._reply.finished.connect(self._on_downloaded)
        self._set_state("downloading")

    @QtCore.Slot()
    def cancel(self) -> None:
        if self._reply is not None:
            self._reply.abort()

    def _on_data(self) -> None:
        if self._reply is not None and self._file is not None:
            if not self._write(self._file, self._reply.readAll()):
                self._reply.abort()

    def _write(self, file: QtCore.QFile, data: QtCore.QByteArray) -> bool:
        """Write a piece of the download; False (and why kept) if it failed."""
        if self._write_error:
            return False
        if file.write(data) == data.size():
            return True
        self._write_error = file.errorString() or "the disk may be full"
        return False

    def _on_progress(self, received: int, _total: int) -> None:
        self._received = int(received)
        self.progressChanged.emit()

    def _on_downloaded(self) -> None:
        reply, self._reply = self._reply, None
        file, self._file = self._file, None
        if reply is None or file is None:
            return
        reply.deleteLater()
        self._write(file, reply.readAll())
        if not file.flush() and not self._write_error:
            self._write_error = file.errorString() or "the disk may be full"
        file.close()
        part = Path(file.fileName())
        setup = self._release.setup
        if self._write_error:
            part.unlink(missing_ok=True)
            self._fail(
                f"Could not save the download to {part.parent}: "
                f"{self._write_error}. Nothing was installed."
            )
            return
        if reply.error() == QtNetwork.QNetworkReply.NetworkError.OperationCanceledError:
            part.unlink(missing_ok=True)
            self._set_state("available")
            return
        if reply.error() != QtNetwork.QNetworkReply.NetworkError.NoError:
            part.unlink(missing_ok=True)
            self._fail(f"Download failed: {reply.errorString()}")
            return
        if not updater.file_matches(part, setup.size, setup.sha256):
            part.unlink(missing_ok=True)
            self._fail(
                "The download does not match the checksum GitHub reported, "
                "so it was deleted. Nothing was installed."
            )
            return
        target = part.with_name(setup.name)
        try:
            target.unlink(missing_ok=True)
            part.rename(target)
        except OSError as exc:
            part.unlink(missing_ok=True)
            self._fail(
                f"Could not save the download to {part.parent}: {exc}. "
                "Nothing was installed."
            )
            return
        self._ready(target)

    def _ready(self, path: Path) -> None:
        self._ready_path = path
        self._set_state("ready")
        self.installRequested.emit()

    @QtCore.Slot()
    def retryUpdate(self) -> None:
        """Try Again after a failed update: check, then download (or reuse the
        verified download) and install that version."""
        if self._state != "failed":
            return
        self._retry = True
        self.check(True)

    @QtCore.Slot()
    def install(self) -> None:
        """Ask again to quit and install (after a cancelled quit)."""
        if self._state == "ready":
            self.installRequested.emit()

    # --- installing ---------------------------------------------------------

    @QtCore.Slot(bool)
    def setInstallOnExit(self, install: bool) -> None:
        self._install_on_exit = bool(install) and self._ready_path is not None

    def start_pending_install(self) -> bool:
        """Start the verified installer; called by main() after Gremlin shut down.

        The installer waits for nothing: Gremlin is already gone, and setup
        closes any copy still holding its files.
        """
        if not self._install_on_exit or self._ready_path is None:
            return False
        if not self._ready_path.is_file():
            return False
        log_path = self._ready_path.with_suffix(".log")
        logging.getLogger("system").info(
            "Update: starting %s (log: %s)", self._ready_path, log_path
        )
        self._config.set(*_PENDING, self._release.version if self._release else "")
        self._config.set(*_PENDING_SETUP, str(self._ready_path))
        # Saved now: the program ends right after this (a scheduled save
        # never ran, so a failed update was never noticed).
        self._save_settings()
        started = bool(
            QtCore.QProcess.startDetached(
                str(self._ready_path),
                updater.setup_arguments(str(log_path)),
                str(self._ready_path.parent),
            )
        )
        if not started:
            self._config.set(*_PENDING, "")
            self._config.set(*_PENDING_SETUP, "")
            self._save_settings()
        return started

    def _save_settings(self) -> None:
        """Saves the settings now; a settings file that can't be written
        (locked, read-only) is logged and the install carries on (the error
        stopped the quit: the installer never started)."""
        try:
            self._config.save_now()
        except Exception:
            logging.getLogger("system").exception("Update: could not save settings")

    def _note_failed_update(self) -> bool:
        """After an update that didn't finish (setup put the previous version
        back): open the dialog to say so, with Try Again. True if it did."""
        pending = str(self._config.value(*_PENDING) or "")
        setup = str(self._config.value(*_PENDING_SETUP) or "")
        if not pending:
            return False
        self._config.set(*_PENDING, "")
        self._config.set(*_PENDING_SETUP, "")
        if not updater.is_newer(pending, util.get_code_version()):
            return False
        logging.getLogger("system").warning(
            "Update: the update to %s did not finish; still %s",
            pending, self.currentVersion,
        )
        self._failed_version = pending
        self._failed_log = str(Path(setup).with_suffix(".log")) if setup else ""
        self._set_state("failed")
        self.offerUpdate.emit()
        return True

    def _note_finished_update(self) -> None:
        """After an update: say so once and delete the downloaded installer."""
        current = self.currentVersion
        previous = self._config.value("global", "internal", "last-run-version")
        if previous == current:
            return
        self._config.set("global", "internal", "last-run-version", current)
        if previous and updater.is_newer(current, previous):
            # The installers go; their logs stay (small, and they explain a
            # failed update).
            for leftover in updater.updates_dir().glob("*"):
                if leftover.is_file() and leftover.suffix.lower() != ".log":
                    leftover.unlink(missing_ok=True)
            signal.showNotification.emit(
                "Updated", f"Gremlin-Platforms is now version {current}."
            )

    def _set_state(self, state: str) -> None:
        if state != "error":
            self._error = ""
        self._state = state
        self.changed.emit()
