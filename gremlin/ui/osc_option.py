# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""OSC's server settings, edited in OSC's Module Setup ("Server" section)
and kept in OSC's own file (D-09-OSC-FILE point 4). Options only points
there."""

from __future__ import annotations

import ipaddress
import logging
import re
import types
from typing import Any

from PySide6 import QtCore, QtGui

import gremlin.ui.type_aliases as ta
from gremlin import osc_device_file
from gremlin.osc import OSC_GROUP, OSC_SECTION, local_ipv4_addresses
from gremlin.ui.option import BaseMetaConfigOptionWidget, MetaConfigOption

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


def _check_rate(text: object) -> tuple[int | None, str]:
    try:
        rate = int(str(text).replace(",", "").strip())
    except (TypeError, ValueError):
        rate = 0
    if rate < 1:
        return None, "The rate is a whole number of messages a second (1 or more)."
    return rate, ""


def check_target(
    name: str, host: str, port: object, targets: list[dict], own_id: str = ""
) -> tuple[dict | None, str]:
    """A target {name, host, port} checked against the others; (None, why)
    when it can't be used."""
    name = str(name or "").strip()
    host = str(host or "").strip()
    if not name:
        return None, "Give the target a name."
    for other in targets:
        same = str(other.get("name", "")).casefold() == name.casefold()
        if same and other.get("id") != own_id:
            return None, f'There is already a target named "{name}".'
    if not host:
        return None, "Type the computer to send to."
    why = check_host(host)
    if why:
        return None, why
    number, why = _check_port(port)
    if why:
        return None, why
    return {"name": name, "host": host, "port": number}, ""


def _discovery() -> types.ModuleType | None:
    """gremlin.osc_discovery when it's there (None otherwise)."""
    try:
        from gremlin import osc_discovery
    except ImportError:
        return None
    return osc_discovery


@ta.QmlElement
class OscServerModel(QtCore.QObject):
    """The Server section of OSC's Module Setup. Each change is checked,
    then written to OSC's file at once (it takes effect at once)."""

    changed = QtCore.Signal()
    messageChanged = QtCore.Signal()
    foundChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._server: dict[str, Any] = {}
        self._targets: list[dict] = []
        self._found: list[dict] = []
        self._message = ""
        self.reload()
        self.refreshFound()
        from gremlin.signal import signal

        for name in ("oscServerSettingsChanged", "oscDeviceReloaded"):
            sig = getattr(signal, name, None)
            if sig is not None:
                sig.connect(self.reload)
        sig = getattr(signal, "oscDevicesFound", None)
        if sig is not None:
            sig.connect(self.refreshFound)

    @QtCore.Slot()
    def reload(self) -> None:
        self._server = osc_device_file.read_server()
        self._targets = osc_device_file.read_targets()
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
        elif key == "feedback_rate":
            value, why = _check_rate(value)
            if why:
                self._say(why)
                return False
        elif key == "sync_address":
            value = str(value or "").strip()
            if not value.startswith("/"):
                self._say("An OSC address starts with /.")
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
        self._apply_discovery(key)
        return self._server.get(key) == value

    def _apply_discovery(self, key: str) -> None:
        """Starts or stops discovery at once when its switch (or the port)
        changes."""
        found = _discovery()
        if found is None or key not in ("announce", "find_devices", "port"):
            return
        try:
            if key in ("announce", "port") and hasattr(found, "set_announce"):
                port = int(str(self._get("port")))
                found.set_announce(bool(self._get("announce")), port)
            if key == "find_devices" and hasattr(found, "set_find"):
                found.set_find(bool(self._get("find_devices")))
                self.refreshFound()
        except Exception:  # noqa: BLE001 - discovery trouble never stops a save
            syslog.exception("OSC: discovery switch not applied")

    # Targets (D-09-OSC-OUTPUT): where Send OSC and feedback send.

    @QtCore.Property(list, notify=changed)
    def targets(self) -> list[dict]:
        return [dict(t) for t in self._targets]

    def _write_targets(self, targets: list[dict]) -> bool:
        try:
            osc_device_file.write_targets(targets, "OSC Module Setup")
        except OSError as exc:
            syslog.error("OSC: targets not written: %s", exc)
            self._say("Not written. The OSC file could not be saved.")
            return False
        self.reload()
        return True

    @QtCore.Slot(str, str, "QVariant", result=bool)
    def addTarget(self, name: str, host: str, port: object) -> bool:
        """Adds a target; False (with message) when refused."""
        target, why = check_target(name, host, port, self._targets)
        if target is None:
            self._say(why)
            return False
        target["id"] = osc_device_file.new_id()
        if not self._write_targets(self._targets + [target]):
            return False
        self._say(f"Added target {target['name']}.")
        return True

    @QtCore.Slot(str, str, str, "QVariant", result=bool)
    def editTarget(self, target_id: str, name: str, host: str, port: object) -> bool:
        """Changes a target's name, host and port; False (with message) when
        refused."""
        if not any(t["id"] == target_id for t in self._targets):
            return False
        target, why = check_target(name, host, port, self._targets, target_id)
        if target is None:
            self._say(why)
            return False
        targets = [
            dict(t, **target) if t["id"] == target_id else dict(t)
            for t in self._targets
        ]
        if not self._write_targets(targets):
            return False
        self._say(f"Changed target {target['name']}.")
        return True

    @QtCore.Slot(str, result=bool)
    def removeTarget(self, target_id: str) -> bool:
        gone = next((t for t in self._targets if t["id"] == target_id), None)
        if gone is None:
            return False
        targets = [dict(t) for t in self._targets if t["id"] != target_id]
        if not self._write_targets(targets):
            return False
        self._say(f"Removed target {gone['name'] or gone['host']}.")
        return True

    # Discovery (D-09-OSC-DISCOVERY).

    @QtCore.Slot()
    def refreshFound(self) -> None:
        found = _discovery()
        devices: list[dict] = []
        try:
            raw = found.found() if found is not None and hasattr(found, "found") else []
            for entry in raw or []:
                if isinstance(entry, dict) and entry.get("host"):
                    devices.append(
                        {
                            "name": str(entry.get("name") or entry.get("host")),
                            "host": str(entry.get("host")),
                            "port": int(str(entry.get("port") or 0)),
                        }
                    )
        except Exception:  # noqa: BLE001 - a broken list shows as empty
            syslog.exception("OSC: found devices not read")
        if devices != self._found:
            self._found = devices
            self.foundChanged.emit()

    @QtCore.Property(bool, notify=changed)
    def discoveryAvailable(self) -> bool:
        """False when discovery can't run here (no zeroconf)."""
        found = _discovery()
        try:
            return bool(found is not None and found.available())
        except Exception:  # noqa: BLE001 - counts as not available
            return False

    @QtCore.Property(list, notify=foundChanged)
    def foundDevices(self) -> list[dict]:
        return [dict(d) for d in self._found]

    @QtCore.Slot(str, str, "QVariant", result=bool)
    def addFoundTarget(self, name: str, host: str, port: object) -> bool:
        """Adds a found device as a target, its name made unique."""
        base = str(name or host).strip() or str(host)
        names = {str(t.get("name", "")).casefold() for t in self._targets}
        unique, n = base, 2
        while unique.casefold() in names:
            unique, n = f"{base} {n}", n + 1
        return self.addTarget(unique, host, port)

    # This PC's addresses, for the app that sends to Gremlin.

    @QtCore.Property(list, notify=changed)
    def pcAddresses(self) -> list[str]:
        own = [ip for ip in local_ipv4_addresses() if ip != "127.0.0.1"]
        return own or ["127.0.0.1"]

    @QtCore.Slot(str, result=bool)
    def copyText(self, text: str) -> bool:
        app = QtCore.QCoreApplication.instance()
        if not isinstance(app, QtGui.QGuiApplication):
            return False
        app.clipboard().setText(str(text))
        self._say(f"Copied {text}.")
        return True

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

    @QtCore.Property(bool, notify=changed)
    def outputEnabled(self) -> bool:
        return bool(self._get("output_enabled"))

    @QtCore.Property(bool, notify=changed)
    def replyToSender(self) -> bool:
        return bool(self._get("reply_to_sender"))

    @QtCore.Property(bool, notify=changed)
    def announce(self) -> bool:
        return bool(self._get("announce"))

    @QtCore.Property(bool, notify=changed)
    def findDevices(self) -> bool:
        return bool(self._get("find_devices"))

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
