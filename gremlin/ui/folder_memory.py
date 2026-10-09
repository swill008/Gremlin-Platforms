# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The last folder used for each kind of file (01 S143, D-01-SHARED-PIECES).

Every file and folder chooser (qml/FilePicker.qml) opens where the user last
picked that kind of file. Kept in configuration.json, global/internal
"last-folders": a map of kind to local folder path.
"""

from __future__ import annotations

import logging
import os

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin.config import Configuration
from gremlin.types import PropertyType

QML_IMPORT_NAME = "Gremlin.UI"
QML_IMPORT_MAJOR_VERSION = 1

SECTION = "global"
GROUP = "internal"
KEY = "last-folders"
DESCRIPTION = "The last folder used for each kind of file, by kind."

KINDS = (
    "device-pack",
    "picture",
    "profile",
    "script",
    "export",
    "module-file",
    "log",
    "diagnostics",
    "template",
    "other",
)


def ensure() -> Configuration:
    """The setting, registered with what it holds now."""
    cfg = Configuration()
    value = cfg.value(SECTION, GROUP, KEY) if cfg.exists(SECTION, GROUP, KEY) else {}
    if not isinstance(value, dict):
        value = {}
    cfg.register(SECTION, GROUP, KEY, PropertyType.Dict, value, DESCRIPTION, {}, False)
    return cfg


def _local_path(url: str) -> str:
    """A local path from a file URL or a plain path."""
    url = (url or "").strip()
    if not url:
        return ""
    qurl = QtCore.QUrl(url)
    if qurl.isLocalFile():
        return os.path.normpath(qurl.toLocalFile())
    if "://" in url:
        return ""
    return os.path.normpath(url)


def _folder_of(path: str) -> str:
    """The folder itself, or the folder a (possibly new) file goes in."""
    if os.path.isdir(path):
        return path
    parent = os.path.dirname(path)
    return parent if parent and os.path.isdir(parent) else ""


def last_folder(kind: str) -> str:
    """The remembered folder for a kind as a local path; "" for an unknown
    kind, none yet, or a folder that no longer exists."""
    if kind not in KINDS:
        return ""
    stored = ensure().value(SECTION, GROUP, KEY).get(kind, "")
    if isinstance(stored, str) and stored and os.path.isdir(stored):
        return stored
    return ""


def remember(kind: str, url: str) -> bool:
    """Keeps the folder of a picked file or folder for its kind."""
    if kind not in KINDS:
        logging.getLogger("system").warning(
            f"Unknown file kind '{kind}' not remembered"
        )
        return False
    folder = _folder_of(_local_path(url))
    if not folder:
        return False
    cfg = ensure()
    folders = dict(cfg.value(SECTION, GROUP, KEY))
    if folders.get(kind) == folder:
        return True
    folders[kind] = folder
    cfg.set(SECTION, GROUP, KEY, folders)
    return True


@ta.QmlElement
class FolderMemory(QtCore.QObject):
    """QML access: lastFolder(kind) -> folder URL or "", remember(kind, url)."""

    @QtCore.Slot(str, result=str)
    def lastFolder(self, kind: str) -> str:  # noqa: N802
        folder = last_folder(kind)
        return QtCore.QUrl.fromLocalFile(folder).toString() if folder else ""

    @QtCore.Slot(str, str, result=bool)
    def remember(self, kind: str, url: str) -> bool:
        return remember(kind, url)

    @QtCore.Slot(result=list)
    def kinds(self) -> list[str]:
        return list(KINDS)
