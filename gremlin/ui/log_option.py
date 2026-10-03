# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import logging

from PySide6 import QtCore

from gremlin.config import Configuration
from gremlin.ui.option import BaseMetaConfigOptionWidget, MetaConfigOption
import gremlin.ui.type_aliases as ta

QML_IMPORT_NAME = "Gremlin.Config"
QML_IMPORT_MAJOR_VERSION = 1

LOG_SECTION = "global"
LOG_GROUP = "general"
LOG_NAME = "log-level"

LEVEL_NAMES = ("Off", "ALL", "Info", "Warning", "Error")
DEFAULT_LEVEL = "Warning"
LOGGER_NAMES = ("system", "user", "event")

_LEVEL_MAP = {
    "Off": logging.CRITICAL + 1,
    "ALL": logging.DEBUG,
    "Info": logging.INFO,
    "Warning": logging.WARNING,
    "Error": logging.ERROR,
}


def normalize_level(value: object) -> str:
    raw = str(value or DEFAULT_LEVEL).strip()
    if raw.lower() in ("debug", "all"):
        return "ALL"
    text = raw.title()
    if text == "Warn":
        text = "Warning"
    if text not in LEVEL_NAMES:
        return DEFAULT_LEVEL
    return text


def apply_log_level(value: object | None = None) -> str:
    if value is None:
        cfg = Configuration()
        if cfg.exists(LOG_SECTION, LOG_GROUP, LOG_NAME):
            value = cfg.value(LOG_SECTION, LOG_GROUP, LOG_NAME)
        else:
            value = DEFAULT_LEVEL
    level_name = normalize_level(value)
    py_level = _LEVEL_MAP[level_name]
    disabled = level_name == "Off"
    for name in LOGGER_NAMES:
        logger = logging.getLogger(name)
        logger.disabled = disabled
        logger.setLevel(py_level)
        for handler in logger.handlers:
            handler.setLevel(py_level)
    return level_name


@ta.QmlElement
class LogLevelModel(QtCore.QObject, BaseMetaConfigOptionWidget):
    levelChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        QtCore.QObject.__init__(self, parent)
        BaseMetaConfigOptionWidget.__init__(self)
        self._config = Configuration()

    def _get_level(self) -> str:
        if self._config.exists(LOG_SECTION, LOG_GROUP, LOG_NAME):
            return normalize_level(self._config.value(LOG_SECTION, LOG_GROUP, LOG_NAME))
        return DEFAULT_LEVEL

    def _set_level(self, value: str) -> None:
        level_name = apply_log_level(value)
        current = ""
        if self._config.exists(LOG_SECTION, LOG_GROUP, LOG_NAME):
            current = normalize_level(self._config.value(LOG_SECTION, LOG_GROUP, LOG_NAME))
        if level_name != current:
            self._config.set(LOG_SECTION, LOG_GROUP, LOG_NAME, level_name)
        self.levelChanged.emit()

    @QtCore.Slot(str)
    def setLevel(self, value: str) -> None:
        self._set_level(value)

    level = QtCore.Property(str, fget=_get_level, fset=_set_level, notify=levelChanged)

    def _qml_path(self) -> str:
        return "file:///" + QtCore.QFile("qml:OptionLogLevel.qml").fileName()


MetaConfigOption().register(
    LOG_SECTION,
    LOG_GROUP,
    "debug",
    "Write diagnostic logs to the logs folder (Options → Folders).",
    LogLevelModel,
)
