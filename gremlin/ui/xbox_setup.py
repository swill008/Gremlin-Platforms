# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Xbox Setup (D-XBOX-PADS): how many Xbox pads the program sends to."""

from __future__ import annotations

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin.modules import output
from gremlin.signal import signal
from gremlin.ui.device import QML_IMPORT_MAJOR_VERSION, QML_IMPORT_NAME

assert QML_IMPORT_NAME == "Gremlin.Device"
assert QML_IMPORT_MAJOR_VERSION == 1

MAX_PADS = 4


@ta.QmlElement
class XboxSetupModel(QtCore.QObject):
    """The Xbox Setup window's pad count: read, what lowering it leaves
    behind, and apply."""

    padCountChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        signal.xboxPadsChanged.connect(self.padCountChanged)

    @QtCore.Property(int, notify=padCountChanged)
    def padCount(self) -> int:
        return int(output.xbox_pad_count())

    @QtCore.Property(int, constant=True)
    def maxPads(self) -> int:
        return MAX_PADS

    @QtCore.Slot(int, result=list)
    def bindingsOutside(self, n: int) -> list[str]:
        """Map to Xbox bindings on the pads above n (any mode)."""
        pads = list(range(max(1, int(n)) + 1, MAX_PADS + 1))
        return list(output.xbox_bindings_on_pads(pads)) if pads else []

    @QtCore.Slot(int)
    def apply(self, n: int) -> None:
        n = min(MAX_PADS, max(1, int(n)))
        if n != self.padCount:
            output.set_xbox_pad_count(n)
