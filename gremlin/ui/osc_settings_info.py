# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import osc_device_file
from gremlin.ui.device import QML_IMPORT_MAJOR_VERSION, QML_IMPORT_NAME

assert QML_IMPORT_NAME == "Gremlin.Device"
assert QML_IMPORT_MAJOR_VERSION == 1

ALL_ADDRESSES = "All addresses on this PC"


@ta.QmlElement
class OscSettingsInfo(QtCore.QObject):
    """The Listening box's text: the server settings and Targets list in
    OSC's file (D-09-OSC-FILE point 4, 09 S96), not the configuration."""

    @QtCore.Slot(result=str)
    def summary(self) -> str:
        server = osc_device_file.read_server()
        host = str(server.get("host") or "").strip() or ALL_ADDRESSES
        targets = ", ".join(
            f"{t['name']} {t['host']}:{t['port']}"
            for t in osc_device_file.read_targets()
        )
        return (
            f"OSC enabled: {'Yes' if server.get('enabled') else 'No'}\n"
            f"Input host: {host}\n"
            f"Input port: {server.get('port')}\n"
            f"OSC output: {'On' if server.get('output_enabled') else 'Off'}\n"
            f"Targets: {targets or 'none'}\n\n"
            "Send the OSC packet to the input host and port."
        )
