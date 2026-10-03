# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from PySide6 import QtCore

from gremlin.config import Configuration
from gremlin.osc import (
    DEFAULT_OUTPUT_PORT,
    DEFAULT_PORT,
    OSC_GROUP,
    OSC_SECTION,
    parse_delay_ms,
    parse_port,
    local_ipv4_addresses,
)
from gremlin.ui.option import BaseMetaConfigOptionWidget, MetaConfigOption
import gremlin.ui.type_aliases as ta

QML_IMPORT_NAME = "Gremlin.Config"
QML_IMPORT_MAJOR_VERSION = 1


class OscAddressModel(QtCore.QAbstractListModel, BaseMetaConfigOptionWidget):
    """Dropdown of this PC's IPv4 addresses plus a refresh action."""

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"name"),
    }
    currentIndexChanged = QtCore.Signal()
    portChanged = QtCore.Signal()

    config_name = "host"
    port_name = "port"
    port_default = DEFAULT_PORT
    qml_file = "qml:OptionOscInputHost.qml"

    def __init__(self, parent: ta.OQO = None) -> None:
        QtCore.QAbstractListModel.__init__(self, parent)
        BaseMetaConfigOptionWidget.__init__(self)
        self._config = Configuration()
        self._addresses = self._addresses_with_saved()

    def _addresses_with_saved(self) -> list[str]:
        addresses = local_ipv4_addresses()
        current = str(
            self._config.value(OSC_SECTION, OSC_GROUP, self.config_name) or ""
        ).strip()
        if current and current not in addresses:
            addresses.insert(0, current)
        return addresses

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._addresses)

    def data(
        self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> str | None:
        if role == QtCore.Qt.ItemDataRole.UserRole + 1:
            return self._addresses[index.row()]
        return None

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    @QtCore.Slot()
    def refresh(self) -> None:
        self.beginResetModel()
        self._addresses = self._addresses_with_saved()
        self.endResetModel()
        self.currentIndexChanged.emit()

    def _normalize_host(self, host: str) -> None:
        return str(host or "").strip()

    def _commit_host(self, host: str) -> None:
        host = self._normalize_host(host)
        if not host:
            return
        current = self._normalize_host(
            str(self._config.value(OSC_SECTION, OSC_GROUP, self.config_name) or "")
        )
        if host != current:
            self._config.set(OSC_SECTION, OSC_GROUP, self.config_name, host)
        if host not in self._addresses:
            self.beginResetModel()
            self._addresses = [host] + [item for item in self._addresses if item != host]
            self.endResetModel()
        self.currentIndexChanged.emit()

    @QtCore.Slot(str)
    def setHost(self, host: str) -> None:
        self._commit_host(host)

    def _get_current_index(self) -> int:
        current = str(
            self._config.value(OSC_SECTION, OSC_GROUP, self.config_name) or ""
        )
        try:
            return self._addresses.index(current)
        except ValueError:
            return 0

    def _set_current_index(self, index: int) -> None:
        if not (0 <= index < len(self._addresses)):
            return
        self._commit_host(self._addresses[index])

    def _get_port(self) -> str:
        raw = self._config.value(OSC_SECTION, OSC_GROUP, self.port_name)
        return str(parse_port(raw, self.port_default))

    def _set_port(self, value: str) -> None:
        port = str(parse_port(value, self.port_default))
        current = str(
            self._config.value(OSC_SECTION, OSC_GROUP, self.port_name) or ""
        ).strip()
        if port != current:
            self._config.set(OSC_SECTION, OSC_GROUP, self.port_name, port)
        self.portChanged.emit()

    @QtCore.Slot(str)
    def setPort(self, value: str) -> None:
        self._set_port(value)

    currentIndex = QtCore.Property(
        int,
        fget=_get_current_index,
        fset=_set_current_index,
        notify=currentIndexChanged,
    )
    port = QtCore.Property(
        str,
        fget=_get_port,
        fset=_set_port,
        notify=portChanged,
    )

    def _qml_path(self) -> str:
        return "file:///" + QtCore.QFile(self.qml_file).fileName()


@ta.QmlElement
class OscInputHostModel(OscAddressModel):
    config_name = "host"
    port_name = "port"
    port_default = 8001
    qml_file = "qml:OptionOscInputHost.qml"


@ta.QmlElement
class OscOutputHostModel(OscAddressModel):
    config_name = "output-host"
    port_name = "output-port"
    port_default = DEFAULT_OUTPUT_PORT
    qml_file = "qml:OptionOscOutputHost.qml"


@ta.QmlElement
class OscAutoreleaseModel(QtCore.QObject, BaseMetaConfigOptionWidget):
    """Autorelease delay in ms with preset buttons."""

    delayChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        QtCore.QObject.__init__(self, parent)
        BaseMetaConfigOptionWidget.__init__(self)
        self._config = Configuration()

    def _get_delay(self) -> str:
        raw = self._config.value(OSC_SECTION, OSC_GROUP, "autorelease-delay")
        return str(parse_delay_ms(raw))

    def _set_delay(self, value: str) -> None:
        delay = parse_delay_ms(value)
        self._config.set(OSC_SECTION, OSC_GROUP, "autorelease-delay", str(delay))
        self.delayChanged.emit()

    @QtCore.Slot(int)
    def setPreset(self, milliseconds: int) -> None:
        self._set_delay(str(milliseconds))

    delayMs = QtCore.Property(
        str, fget=_get_delay, fset=_set_delay, notify=delayChanged
    )

    def _qml_path(self) -> str:
        return "file:///" + QtCore.QFile("qml:OptionOscAutorelease.qml").fileName()


MetaConfigOption().register(
    OSC_SECTION,
    OSC_GROUP,
    "input-host",
    "Input IP and port the program listens on. Pick a scanned address or type one.",
    OscInputHostModel,
)
MetaConfigOption().register(
    OSC_SECTION,
    OSC_GROUP,
    "output-address",
    "Output IP and port for OSC feedback to Companion.",
    OscOutputHostModel,
)
MetaConfigOption().register(
    OSC_SECTION,
    OSC_GROUP,
    "delay-presets",
    "Default Autorelease Delay in milliseconds.",
    OscAutoreleaseModel,
)
