# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The viewers follow their facts' owners (D-01-OWNER-NOTICES): what drives
what from signal.bindingsChanged, the Logical Device's input names from
logicalDeviceModified, device names from deviceNamesChanged and the Auto
Mapping Tool list from moduleFilesChanged. Each test failed before: the
models kept their own lists of raw signals and missed these."""

from __future__ import annotations

import sys

sys.path.append(".")

from collections.abc import Callable

import pytest
from PySide6 import QtCore

from gremlin.signal import signal

_Make = Callable[[], QtCore.QAbstractItemModel]


@pytest.fixture(scope="session", autouse=True)
def terminate_event_listener(request: pytest.FixtureRequest) -> None:
    import gremlin.event_handler

    request.addfinalizer(lambda: gremlin.event_handler.EventListener().terminate())


class _Resets(QtCore.QObject):
    """Counts a model's resets through a bound slot."""

    def __init__(self, model: QtCore.QAbstractItemModel) -> None:
        super().__init__()
        self.count = 0
        self._model = model
        model.modelReset.connect(self.seen)

    @QtCore.Slot()
    def seen(self) -> None:
        self.count += 1

    def release(self) -> None:
        self._model.modelReset.disconnect(self.seen)


def _settle(qtbot: object) -> None:
    qtbot.wait(20)  # type: ignore[attr-defined]


def _resets_after(
    qtbot: object, model: QtCore.QAbstractItemModel, *signals: QtCore.SignalInstance
) -> int:
    _settle(qtbot)
    resets = _Resets(model)
    try:
        for sig in signals:
            sig.emit()
        _settle(qtbot)
        return resets.count
    finally:
        resets.release()
        model.deleteLater()


def _module_pair_device() -> QtCore.QAbstractItemModel:
    from gremlin.ui.module_pairing import ModulePairDeviceModel

    return ModulePairDeviceModel()


def _module_pair_buttons() -> QtCore.QAbstractItemModel:
    from gremlin.ui.module_pairing import ModulePairButtonModel

    return ModulePairButtonModel()


def _module_pair_axes() -> QtCore.QAbstractItemModel:
    from gremlin.ui.module_pairing import ModulePairAxisModel

    return ModulePairAxisModel()


def _viewer_devices() -> QtCore.QAbstractItemModel:
    from gremlin.ui.viewer_devices import ViewerDeviceModel

    return ViewerDeviceModel()


def _xbox_viewer_devices() -> QtCore.QAbstractItemModel:
    from gremlin.ui.xbox_viewer import XboxViewerDeviceModel

    return XboxViewerDeviceModel()


def _xbox_mapped_buttons() -> QtCore.QAbstractItemModel:
    from gremlin.ui.xbox_viewer import XboxMappedButtonModel

    return XboxMappedButtonModel()


def _xbox_pads() -> QtCore.QAbstractItemModel:
    from gremlin.ui.xbox_viewer import XboxPadListModel

    return XboxPadListModel()


def _xbox_page() -> QtCore.QAbstractItemModel:
    from gremlin.ui.xbox_device_model import XboxDeviceModel

    return XboxDeviceModel()


def _auto_mapping_tool_inputs() -> QtCore.QAbstractItemModel:
    from gremlin.ui.auto_mapping_tool_modules import AutoMappingToolInputModel

    return AutoMappingToolInputModel()


def _auto_mapping_tool_outputs() -> QtCore.QAbstractItemModel:
    from gremlin.ui.auto_mapping_tool_modules import AutoMappingToolOutputModel

    return AutoMappingToolOutputModel()


@pytest.mark.parametrize(
    "make",
    [
        _module_pair_device,
        _module_pair_buttons,
        _module_pair_axes,
        _viewer_devices,
        _xbox_viewer_devices,
        _xbox_mapped_buttons,
        _xbox_pads,
        _xbox_page,
    ],
)
def test_what_drives_what_follows_the_bindings_notice(
    qtbot: object, make: _Make
) -> None:
    # A Logical Device edit, an OSC undo, a Library Swap, Delete Mode: none
    # of them is a profileChanged; all of them are this one notice.
    assert _resets_after(qtbot, make(), signal.bindingsChanged) == 1


@pytest.mark.parametrize("make", [_module_pair_buttons, _module_pair_axes, _xbox_page])
def test_logical_device_names_follow_its_notice(qtbot: object, make: _Make) -> None:
    # The Input Viewer's paired-input labels and the Xbox page's "incoming"
    # show the Logical Device's input names ("Button 1 — Gear").
    assert _resets_after(qtbot, make(), signal.logicalDeviceModified) == 1


@pytest.mark.parametrize("make", [_module_pair_buttons, _xbox_page])
def test_a_logical_device_edit_is_read_once(qtbot: object, make: _Make) -> None:
    # Its own notice and the bindings notice that follows it: one read.
    count = _resets_after(
        qtbot, make(), signal.logicalDeviceModified, signal.bindingsChanged
    )
    assert count == 1


@pytest.mark.parametrize("make", [_viewer_devices, _xbox_viewer_devices, _xbox_page])
def test_device_names_follow_the_names_notice(qtbot: object, make: _Make) -> None:
    assert _resets_after(qtbot, make(), signal.deviceNamesChanged) == 1


@pytest.mark.parametrize(
    "make", [_auto_mapping_tool_inputs, _auto_mapping_tool_outputs]
)
def test_auto_mapping_tool_list_follows_module_files(
    qtbot: object, make: _Make
) -> None:
    assert _resets_after(qtbot, make(), signal.moduleFilesChanged) == 1


def test_device_mapping_editor_chips_follow_the_bindings_notice(qtbot: object) -> None:
    from gremlin.ui.hardware_profile import HardwareProfile

    hp = HardwareProfile()
    try:
        with qtbot.waitSignal(hp.profileLabelsChanged, timeout=2000):  # type: ignore[attr-defined]
            signal.bindingsChanged.emit()
    finally:
        hp.deleteLater()


def test_device_mapping_editor_pool_key_moves_on_the_bindings_notice() -> None:
    from gremlin.ui import hardware_profile

    hardware_profile._hook_profile_generation()
    before = hardware_profile._profile_generation
    signal.bindingsChanged.emit()
    assert hardware_profile._profile_generation != before


def test_a_deleted_model_stops_listening(qtbot: object) -> None:
    # Bound slots only: a model gone from the page is no longer reached.
    from gremlin.ui.viewer_devices import ViewerDeviceModel

    def flush() -> None:
        qtbot.wait(20)  # type: ignore[attr-defined]
        QtCore.QCoreApplication.sendPostedEvents(
            None, QtCore.QEvent.Type.DeferredDelete
        )

    flush()
    model = ViewerDeviceModel()
    receivers = signal.receivers(QtCore.SIGNAL("bindingsChanged()"))
    model.deleteLater()
    flush()
    assert signal.receivers(QtCore.SIGNAL("bindingsChanged()")) == receivers - 1
