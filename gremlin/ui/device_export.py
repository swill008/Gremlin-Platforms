# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""QML access to a device folder's Export and Import (08 S111,
D-03-DEVICE-FOLDERS): gremlin.modules.device_zip behind two slots, used by
qml/DialogDeviceExport.qml. The bindings are the Device Pack's: these slots
hand device_zip the wires (device_pack.collect_wires) and the function that
puts them back (device_pack.put_gmap_wires)."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin.modules import device_zip
from gremlin.ui import device_pack

QML_IMPORT_NAME = "Gremlin.UI"
QML_IMPORT_MAJOR_VERSION = 1


def _local(path_or_url: str) -> Path:
    from gremlin.ui.util import to_local_path

    return to_local_path(path_or_url)


@ta.QmlElement
class DeviceExport(QtCore.QObject):
    """exportDevice / importDevice: "" when it worked, else why not."""

    # A device folder was imported (its id key): the cards and maps reread.
    deviceImported = QtCore.Signal(str)

    @QtCore.Slot(str, str, str, bool, result=str)
    def exportDevice(  # noqa: N802
        self,
        name: str,
        guid: str,
        path: str,
        withBindings: bool,  # noqa: N803
    ) -> str:
        try:
            # The open profile's wires; reads the profile, so on the main
            # thread (a slot).
            wires = device_pack.collect_wires(guid) if withBindings else None
            return device_zip.export_device(name, guid, _local(path), wires)
        except Exception as exc:  # noqa: BLE001 - shown, never raised into QML
            logging.getLogger("system").warning(f"Device export failed: {exc!r}")
            return f"Export failed ({exc})."

    @QtCore.Slot(str, bool, result=str)
    def importDevice(self, path: str, withBindings: bool) -> str:  # noqa: N802, N803
        try:
            key, error = device_zip.import_device(
                _local(path),
                put_wires=device_pack.put_gmap_wires if withBindings else None,
            )
        except Exception as exc:  # noqa: BLE001 - shown, never raised into QML
            logging.getLogger("system").warning(f"Device import failed: {exc!r}")
            return f"Import failed ({exc})."
        if key:
            self.deviceImported.emit(key)
            try:
                from gremlin.signal import signal

                signal.configChanged.emit()
            except Exception:  # noqa: BLE001 - no listeners yet
                pass
        return error

    @QtCore.Slot(str, str, result=str)
    def suggestedName(self, name: str, guid: str) -> str:  # noqa: N802
        """The file name Export suggests: "<shown name>.gmap"."""
        from gremlin.modules import store

        shown = store.shown_name_of(name, guid) or name or "Device"
        return store.folder_name_for(shown) + device_zip.GMAP_EXT
