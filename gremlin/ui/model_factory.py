# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Makes the Python objects QML pages use, so they are freed with their page.

PySide6 never frees a Python object that QML instantiates (`TypeName {}`,
PYSIDE-1407): the C++ side goes, an empty Python shell stays. Objects made
here are made in Python with the QML item as their Qt parent instead, so
Qt's parent deletion frees both. Once PYSIDE-1407 is fixed this can go.

Contract (claude/plans/memory-qml-factory.md section 2):

    import Gremlin.UI
    readonly property HardwareLayoutModel _layout:
        ModelFactory.create("HardwareLayoutModel", _root, { deviceType: "physical" })

1. A `readonly property <Type> <oldId>` on the item that held the
   declaration, named as the old id. Inline uses (`model: X {}`) become such
   a property on the enclosing item plus `model: <oldId>`.
2. Parent: the id of the item that held the declaration (a delegate's own
   root, never the view; for a Window file, the window).
3. `props` holds constants only, set in the literal's order. A value that
   can change would re-run the call and make a new object.
4. Changing values: `Binding { target: _x; property: "p"; value: ... }`;
   where the first assignment's order matters, put the first value in props
   as well.
5. `onX:` handlers on the object become `Connections { target: _x; function onX() {} }`.
6. `property alias a: _x.b` becomes `property <type> a` plus a `Binding`.
7. `Component.onDestruction` stays where an object must be stopped first.

Every `ta.QmlElement` type can be made (`QML_TYPES`). A converted type goes
on `FACTORY_ONLY` and is then registered uncreatable in QML, so a new
`TypeName {}` for it fails at load.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from PySide6 import (
    QtCore,
    QtQml,
)

from gremlin import threads
from gremlin.ui import type_aliases as ta

QML_IMPORT_NAME = "Gremlin.UI"
QML_IMPORT_MAJOR_VERSION = 1

# Types QML may only get from ModelFactory.create (registered uncreatable).
# The one list; a name goes on once no `TypeName {` is left in qml/, theme/
# or action_plugins/.
FACTORY_ONLY: frozenset[str] = frozenset(
    {
        # Stage 1 (claude/plans/memory-qml-factory.md section 3)
        "AutoMappingToolInputModel",
        "AutoMappingToolOutputModel",
        "AxisCalibration",
        "CalibrationModuleModel",
        "ConfigSectionModel",
        "DebugLog",
        "Device",
        "DeviceLiveState",
        "HardwareLayoutModel",
        "InputMonitor",
        "InputTesterLink",
        "LiveLog",
        "ModeHierarchyModel",
        "ModeListModel",
        "ModuleClaimedInputModel",
        "ModuleListModel",
        "Tools",
        "TraceSwitch",
        "TraceView",
        # Stage 2 (section 4)
        "ActionSequenceOrdering",
        "CardSizes",
        "DebugMode",
        "DeviceAxisSeries",
        "DeviceListModel",
        "DeviceMapOptions",
        "DeviceMapSpaceKey",
        "DeviceNames",
        "Diagnostics",
        "DriverInputModel",
        "DriversModel",
        "EditLock",
        "FolderMemory",
        "HardwareProfile",
        "HealthModel",
        "HidHideModel",
        "HighlightSpeedModel",
        "HistoryModel",
        "InputListenerModel",
        "KeyboardLayoutModel",
        "LogicalDeviceSelectorModel",
        "LogicalLayoutModel",
        "LogLevelModel",
        "MappedAxisModel",
        "MappedButtonModel",
        "MappedHatModel",
        "ModuleFileWatch",
        "ModulePairAxisModel",
        "ModulePairButtonModel",
        "ModulePairDeviceModel",
        "OscBulkCapture",
        "OscCardStatus",
        "OscCompanionCheck",
        "OscDeviceManagementModel",
        "OscFeedbackModel",
        "OscLayoutModel",
        "OscModuleSetupLink",
        "OscMonitorModel",
        "OscServerModel",
        "OscSettingsInfo",
        "OutputModuleDevices",
        "OutputVJoyListModel",
        "PairLiveThrottle",
        "ProcessListModel",
        "ProfileAutoLoadingModel",
        "ProfileSettingsModel",
        "ResetDevicesModel",
        "ScreenSaverModeModel",
        "SearchModel",
        "StartupModeModel",
        "TTSVoiceSelectionModel",
        "UiScaleModel",
        "ViewerDeviceModel",
        "VJoyInputOrOutputModel",
        "WindowPlacement",
        "WindowsScaleModel",
        "XboxDriverStatus",
        "XboxOutputListModel",
        "XboxPadChipsModel",
        "XboxPadLive",
        "XboxPadSectionsModel",
        "XboxSetupModel",
    }
)

UNCREATABLE_REASON = (
    'made by ModelFactory: ModelFactory.create("{name}", parent, {{...}}) '
    "(gremlin/ui/model_factory.py)"
)


def make(
    type_name: str, parent: QtCore.QObject | None, props: dict[str, Any] | None = None
) -> QtCore.QObject:
    """Builds a registered type with `parent` as its Qt parent.

    Props are set in their given order. Raises on an unknown type or
    property, a missing parent, or a call off the main thread.
    """
    if threading.current_thread() is not threading.main_thread():
        raise threads.WrongThread(
            f"ModelFactory.create({type_name!r}) must run on the main thread, "
            f"not on {threading.current_thread().name}"
        )
    cls = ta.QML_TYPES.get(type_name)
    if cls is None:
        if type_name in ta.QML_AMBIGUOUS:
            raise ValueError(
                f"ModelFactory: type name {type_name!r} is registered by more "
                "than one class"
            )
        raise ValueError(
            f"ModelFactory: unknown type {type_name!r} (not a ta.QmlElement type)"
        )
    if parent is None:
        raise ValueError(f"ModelFactory.create({type_name!r}): parent is required")
    obj = cls(parent)
    QtQml.QQmlEngine.setObjectOwnership(
        obj, QtQml.QQmlEngine.ObjectOwnership.CppOwnership
    )
    # The class's meta object, not obj.metaObject(): PySide 6.11.2 marks the
    # type's QMetaObject wrapper deleted when obj.metaObject() is read inside
    # a Slot QML calls, and every later metaObject() in Python then raises.
    meta = cls.staticMetaObject
    for name, value in (props or {}).items():
        if meta.indexOfProperty(name) < 0:
            obj.setParent(None)
            obj.deleteLater()
            raise ValueError(
                f"ModelFactory.create({type_name!r}): {cls.__name__} has no "
                f"property {name!r}"
            )
        obj.setProperty(name, value)
    return obj


def _props_from_js(value: QtQml.QJSValue) -> dict[str, Any]:
    # QVariantMap would sort the keys; the iterator keeps the literal's order.
    if value.isUndefined() or value.isNull():
        return {}
    if not value.isObject():
        raise ValueError("ModelFactory.create: props must be an object literal")
    props: dict[str, Any] = {}
    it = QtQml.QJSValueIterator(value)
    while it.next():
        props[it.name()] = it.value().toVariant()
    return props


@QtQml.QmlElement
@QtQml.QmlSingleton
class ModelFactory(QtCore.QObject):
    """QML singleton: `ModelFactory.create("TypeName", parent, {props})`."""

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)

    @QtCore.Slot(str, QtCore.QObject, result=QtCore.QObject)
    @QtCore.Slot(str, QtCore.QObject, QtQml.QJSValue, result=QtCore.QObject)
    def create(
        self,
        type_name: str,
        parent: QtCore.QObject | None,
        props: QtQml.QJSValue | dict[str, Any] | None = None,
    ) -> QtCore.QObject | None:
        try:
            values = (
                _props_from_js(props) if isinstance(props, QtQml.QJSValue) else props
            )
            return make(type_name, parent, values)
        except Exception as e:
            logging.getLogger("system").error(str(e))
            engine = QtQml.qmlEngine(self)
            if engine is not None:
                engine.throwError(str(e))
                return None
            raise
