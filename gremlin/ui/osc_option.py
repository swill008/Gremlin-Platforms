# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""OSC's server settings, edited in OSC's Module Setup ("Server" section)
and kept in OSC's own file (D-09-OSC-FILE point 4). Options only points
there."""

from __future__ import annotations

import ipaddress
import logging
import re
from typing import Any

from PySide6 import QtCore

from gremlin import osc_device_file
from gremlin.osc import OSC_GROUP, OSC_SECTION, local_ipv4_addresses
from gremlin.ui.option import BaseMetaConfigOptionWidget, MetaConfigOption
import gremlin.ui.type_aliases as ta

QML_IMPORT_NAME = "Gremlin.Config"
QML_IMPORT_MAJOR_VERSION = 1

syslog = logging.getLogger("system")

# One part of a host name: letters, digits and inner hyphens (RFC 1123).
_LABEL = re.compile(r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)$")


def check_host(text: str) -> str:
    """Why host can't be used ("" when it can): blank (all addresses), an
    IP address or a host name."""
    host = str(text or "").strip()
    if not host:
        return ""
    try:
        ipaddress.ip_address(host)
        return ""
    except ValueError:
        pass
    name = host[:-1] if host.endswith(".") else host
    parts = name.split(".")
    if (
        len(name) <= 253
        and all(_LABEL.match(p) for p in parts)
        # All digits and dots is a mistyped IP address, not a name.
        and not all(p.isdigit() for p in parts)
    ):
        return ""
    return f"\"{host}\" is not an IP address or a computer name."


def _check_port(text: object) -> tuple[int | None, str]:
    try:
        port = int(str(text).replace(",", "").strip())
    except (TypeError, ValueError):
        return None, "A port is a whole number from 1 to 65535."
    if not 1 <= port <= 65535:
        return None, "A port is a whole number from 1 to 65535."
    return port, ""


def _check_delay(text: object) -> tuple[int | None, str]:
    try:
        delay = int(str(text).replace(",", "").strip())
    except (TypeError, ValueError):
        return None, "The delay is a whole number of milliseconds (0 to 10000)."
    if not 0 <= delay <= 10000:
        return None, "The delay is a whole number of milliseconds (0 to 10000)."
    return delay, ""


@ta.QmlElement
class OscServerModel(QtCore.QObject):
    """The Server section of OSC's Module Setup. Each change is checked,
    then written to OSC's file at once (it takes effect at once)."""

    changed = QtCore.Signal()
    messageChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._server: dict[str, Any] = {}
        self._message = ""
        self.reload()
        from gremlin.signal import signal

        for name in ("oscServerSettingsChanged", "oscDeviceReloaded"):
            sig = getattr(signal, name, None)
            if sig is not None:
                sig.connect(self.reload)

    @QtCore.Slot()
    def reload(self) -> None:
        self._server = osc_device_file.read_server()
        self.changed.emit()

    @QtCore.Slot(str, result=bool)
    def isOscDevice(self, guid: str) -> bool:
        from gremlin.modules import ids
        from gremlin.modules.ids import guid_key

        return guid_key(guid) == guid_key(str(ids.OSC))

    def _say(self, text: str) -> None:
        if text != self._message:
            self._message = text
            self.messageChanged.emit()

    @QtCore.Slot(str, "QVariant", result=bool)
    def setValue(self, key: str, value: object) -> bool:
        """Checks and saves one setting; False (with message) when refused."""
        if key not in osc_device_file.SERVER_DEFAULTS:
            return False
        if key == "host":
            why = check_host(str(value or ""))
            if why:
                self._say(why)
                return False
            value = str(value or "").strip()
        elif key in ("port", "output_port"):
            value, why = _check_port(value)
            if why:
                self._say(why)
                return False
        elif key == "output_host":
            value = str(value or "").strip()
            why = check_host(value) if value else "Type the computer to send to."
            if why:
                self._say(why)
                return False
        elif key == "autorelease_delay_ms":
            value, why = _check_delay(value)
            if why:
                self._say(why)
                return False
        else:
            value = bool(value)
        self._say("")
        if self._server.get(key) == value:
            return True
        settings = dict(self._server)
        settings[key] = value
        try:
            osc_device_file.write_server(settings, "OSC Module Setup")
        except OSError as exc:
            syslog.error("OSC: server settings not written: %s", exc)
            self._say("Not written. The OSC file could not be saved.")
            return False
        self.reload()
        return self._server.get(key) == value

    def _get(self, key: str) -> object:
        return self._server.get(key, osc_device_file.SERVER_DEFAULTS[key])

    @QtCore.Property(bool, notify=changed)
    def enabled(self) -> bool:
        return bool(self._get("enabled"))

    @QtCore.Property(str, notify=changed)
    def host(self) -> str:
        return str(self._get("host") or "")

    @QtCore.Property(str, notify=changed)
    def port(self) -> str:
        return str(self._get("port"))

    @QtCore.Property(str, notify=changed)
    def outputHost(self) -> str:
        return str(self._get("output_host") or "")

    @QtCore.Property(str, notify=changed)
    def outputPort(self) -> str:
        return str(self._get("output_port"))

    @QtCore.Property(bool, notify=changed)
    def autoreleaseNoArg(self) -> bool:
        return bool(self._get("autorelease_no_arg"))

    @QtCore.Property(str, notify=changed)
    def autoreleaseDelay(self) -> str:
        return str(self._get("autorelease_delay_ms"))

    @QtCore.Property(bool, notify=changed)
    def padArgs(self) -> bool:
        return bool(self._get("pad_args"))

    @QtCore.Property(str, notify=messageChanged)
    def message(self) -> str:
        return self._message

    @QtCore.Slot(result=str)
    def localAddresses(self) -> str:
        """This PC's addresses, for the Host field's tip."""
        return ", ".join(ip for ip in local_ipv4_addresses() if ip != "127.0.0.1")


@ta.QmlElement
class OscModuleSetupLink(QtCore.QObject, BaseMetaConfigOptionWidget):
    """Options' one OSC line: its button opens OSC's Module Setup."""

    def __init__(self, parent: ta.OQO = None) -> None:
        QtCore.QObject.__init__(self, parent)
        BaseMetaConfigOptionWidget.__init__(self)

    @QtCore.Slot(result=bool)
    def open(self) -> bool:
        from gremlin.signal import signal

        sig = getattr(signal, "openOscModuleSetup", None)
        if sig is None:
            return False
        sig.emit()
        return True

    def _qml_path(self) -> str:
        return "file:///" + QtCore.QFile("qml:OptionOscModuleSetup.qml").fileName()


MetaConfigOption().register(
    OSC_SECTION,
    OSC_GROUP,
    "module-setup",
    "OSC settings are in OSC › Module Setup.",
    OscModuleSetupLink,
)
