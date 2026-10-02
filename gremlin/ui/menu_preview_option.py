# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Options, UI section: a preview of the program's one menu
style (Gremlin.Menus) in the current mode, with live samples to try."""

from __future__ import annotations

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin.ui.option import BaseMetaConfigOptionWidget, MetaConfigOption


class MenuPreviewOption(QtCore.QObject, BaseMetaConfigOptionWidget):
    def __init__(self, parent: ta.OQO = None) -> None:
        QtCore.QObject.__init__(self, parent)
        BaseMetaConfigOptionWidget.__init__(self)

    def _qml_path(self) -> str:
        return "file:///" + QtCore.QFile("qml:OptionMenuPreview.qml").fileName()


MetaConfigOption().register(
    "ui",
    "general",
    "menu-preview",
    "Menus, right-click menus, dropdown lists and the command palette share "
    "one look in light and dark mode. Try them here.",
    MenuPreviewOption,
)
