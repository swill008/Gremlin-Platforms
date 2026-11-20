# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The "Updated" banner and What's New window's model (01 S183)."""

from __future__ import annotations

import logging

from PySide6 import QtCore
from PySide6.QtCore import Property, Signal, Slot

from gremlin import (
    util,
    whats_new,
)
from gremlin.config import Configuration


class WhatsNewModel(QtCore.QObject):
    """`whatsNew` in QML. Reads the last-run version when made, so it must
    be made before UpdateModel, which records the new one (01 S121)."""

    bannerChanged = Signal()
    notesChanged = Signal()

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._current = util.get_code_version()
        self._versions: list[str] = []
        try:
            last = Configuration().value("global", "internal", "last-run-version")
            self._versions = whats_new.banner_versions(last, self._current)
        except Exception:
            logging.getLogger("system").exception("What's New: start check failed")
        self._banner = bool(self._versions)
        self._title = f"Updated to {self._current}"
        self._message = "See what changed in this version."
        self._notes = ""

    @Property(bool, notify=bannerChanged)
    def bannerVisible(self) -> bool:
        return self._banner

    @Property(str, notify=bannerChanged)
    def bannerTitle(self) -> str:
        return self._title

    @Property(str, notify=bannerChanged)
    def bannerMessage(self) -> str:
        return self._message

    @Property(str, notify=notesChanged)
    def notesHtml(self) -> str:
        return self._notes

    @Slot()
    def dismissBanner(self) -> None:
        if self._banner:
            self._banner = False
            self.bannerChanged.emit()

    @Slot()
    def showBannerNotes(self) -> None:
        self._set_notes(self._versions or [self._current])

    @Slot()
    def showCurrentNotes(self) -> None:
        self._set_notes([self._current])

    def _set_notes(self, versions: list[str]) -> None:
        self._notes = whats_new.notes_html(versions)
        self.notesChanged.emit()
