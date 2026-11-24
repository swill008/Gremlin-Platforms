# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""QML makes our Python types only through ModelFactory.create (plan
claude/plans/memory-qml-factory.md, section 2 "Guard", answer 4a).

PySide6 never frees the Python wrapper of an object QML instantiates
(PYSIDE-1407, gap PYSIDE-WRAPPERS on program map page 01). A QML file that
declares one of our ``@ta.QmlElement`` types as ``TypeName {`` brings that
leak back; this test fails on it. Declarations not converted yet are listed
in STAGE2_PENDING as (file, type) pairs; the list may only shrink: a pair
that no longer appears in its file fails too, so it is taken off.
"""

from __future__ import annotations

import importlib
import pathlib
import re

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_PY_FOLDERS = ("gremlin", "action_plugins", "theme")
_QML_FOLDERS = ("qml", "action_plugins", "theme")
_DECORATED = re.compile(r"@ta\.QmlElement\s*\n(?:\s*@.*\n)*\s*class\s+(\w+)")
_CREATE = re.compile(r"""ModelFactory\.create\(\s*["'](\w+)["']""")

# Stage 2 of the plan: declarations still to convert, (QML file, type).
# Only ever remove entries.
STAGE2_PENDING: frozenset[tuple[str, str]] = frozenset({
    ('qml/ActionPane.qml', 'WindowPlacement'),
    ('qml/AxesStateSeries.qml', 'DeviceAxisSeries'),
    ('qml/DebugFrame.qml', 'DebugMode'),
    ('qml/DeviceMapCard.qml', 'HardwareProfile'),
    ('qml/DeviceMapCard.qml', 'MappedAxisModel'),
    ('qml/DeviceMapCard.qml', 'MappedButtonModel'),
    ('qml/DeviceMapCard.qml', 'MappedHatModel'),
    ('qml/DeviceMapCard.qml', 'PairLiveThrottle'),
    ('qml/DevicePhotoHost.qml', 'HardwareProfile'),
    ('qml/DialogConfigureModule.qml', 'DriverInputModel'),
    ('qml/DialogConfigureModule.qml', 'HardwareProfile'),
    ('qml/DialogDeviceInformation.qml', 'DeviceListModel'),
    ('qml/DialogDeviceMappingEditor.qml', 'DeviceMapOptions'),
    ('qml/DialogDeviceMappingEditor.qml', 'DeviceMapSpaceKey'),
    ('qml/DialogDeviceMappingEditor.qml', 'DeviceNames'),
    ('qml/DialogDeviceMappingEditor.qml', 'HardwareProfile'),
    ('qml/DialogDeviceMappingEditor.qml', 'ModuleFileWatch'),
    ('qml/DialogDeviceMappingEditor.qml', 'ViewerDeviceModel'),
    ('qml/DialogDevicePack.qml', 'HardwareProfile'),
    ('qml/DialogHardwareHide.qml', 'HidHideModel'),
    ('qml/DialogHealth.qml', 'HealthModel'),
    ('qml/DialogHelp.qml', 'WindowPlacement'),
    ('qml/DialogHistory.qml', 'HistoryModel'),
    ('qml/DialogInputViewer.qml', 'ModulePairDeviceModel'),
    ('qml/DialogResetDevices.qml', 'ResetDevicesModel'),
    ('qml/DialogSaveDiagnostics.qml', 'Diagnostics'),
    ('qml/DialogSearch.qml', 'SearchModel'),
    ('qml/DialogXboxSetup.qml', 'XboxSetupModel'),
    ('qml/FilePicker.qml', 'FolderMemory'),
    ('qml/InputConfiguration.qml', 'EditLock'),
    ('qml/InputListener.qml', 'InputListenerModel'),
    ('qml/InputViewerCard.qml', 'ModulePairAxisModel'),
    ('qml/InputViewerCard.qml', 'ModulePairButtonModel'),
    ('qml/InputViewerCard.qml', 'PairLiveThrottle'),
    ('qml/KeyboardPage.qml', 'EditLock'),
    ('qml/KeyboardPage.qml', 'InputListenerModel'),
    ('qml/KeyboardPage.qml', 'KeyboardLayoutModel'),
    ('qml/ListAppearancePanel.qml', 'WindowPlacement'),
    ('qml/LogicalDeviceSelector.qml', 'LogicalDeviceSelectorModel'),
    ('qml/LogicalPage.qml', 'EditLock'),
    ('qml/LogicalPage.qml', 'LogicalLayoutModel'),
    ('qml/OptionActionSequenceOrdering.qml', 'ActionSequenceOrdering'),
    ('qml/OptionDeviceMapLibrary.qml', 'DeviceMapOptions'),
    ('qml/OptionDeviceMapLibrary.qml', 'HardwareProfile'),
    ('qml/OptionHighlightSpeed.qml', 'HighlightSpeedModel'),
    ('qml/OptionLogLevel.qml', 'LogLevelModel'),
    ('qml/OptionOscModuleSetup.qml', 'OscModuleSetupLink'),
    ('qml/OptionProfileAutoLoading.qml', 'ProcessListModel'),
    ('qml/OptionProfileAutoLoading.qml', 'ProfileAutoLoadingModel'),
    ('qml/OptionStatusCards.qml', 'CardSizes'),
    ('qml/OptionTTSVoiceSelection.qml', 'TTSVoiceSelectionModel'),
    ('qml/OptionUiScale.qml', 'UiScaleModel'),
    ('qml/OptionWindowsScale.qml', 'WindowsScaleModel'),
    ('qml/OscAddDialog.qml', 'OscBulkCapture'),
    ('qml/OscAddDialog.qml', 'OscSettingsInfo'),
    ('qml/OscFeedbackSection.qml', 'OscFeedbackModel'),
    ('qml/OscMonitorPanel.qml', 'OscMonitorModel'),
    ('qml/OscOutputTab.qml', 'OscCompanionCheck'),
    ('qml/OscPage.qml', 'EditLock'),
    ('qml/OscPage.qml', 'OscDeviceManagementModel'),
    ('qml/OscPage.qml', 'OscLayoutModel'),
    ('qml/OscPage.qml', 'WindowPlacement'),
    ('qml/OscSetupTabs.qml', 'OscServerModel'),
    ('qml/PageAppearance.qml', 'WindowPlacement'),
    ('qml/ProfileSettingsGeneral.qml', 'ProfileSettingsModel'),
    ('qml/ProfileSettingsGeneral.qml', 'StartupModeModel'),
    ('qml/ProfileSettingsVJoy.qml', 'OutputVJoyListModel'),
    ('qml/ProfileSettingsVJoy.qml', 'VJoyInputOrOutputModel'),
    ('qml/StatusCard.qml', 'OscCardStatus'),
    ('qml/StatusPage.qml', 'DriversModel'),
    ('qml/ToolWindowMemory.qml', 'WindowPlacement'),
    ('qml/VJoySelector.qml', 'OutputModuleDevices'),
    ('qml/WindowDrivers.qml', 'DriversModel'),
    ('qml/WindowOscMonitor.qml', 'OscDeviceManagementModel'),
    ('qml/WindowScreenSaverMode.qml', 'ScreenSaverModeModel'),
    ('qml/XboxDevice.qml', 'WindowPlacement'),
    ('qml/XboxDevice.qml', 'XboxDriverStatus'),
    ('qml/XboxDevice.qml', 'XboxPadSectionsModel'),
    ('qml/XboxDriverCheck.qml', 'XboxDriverStatus'),
    ('qml/XboxPadCard.qml', 'XboxOutputListModel'),
    ('qml/XboxPadCard.qml', 'XboxPadChipsModel'),
    ('qml/XboxPadCard.qml', 'XboxPadLive'),
})  # fmt: skip


def _registered() -> dict[str, str]:
    """Every ta.QmlElement class name and the module that defines it."""
    out: dict[str, str] = {}
    for folder in _PY_FOLDERS:
        for path in (_ROOT / folder).rglob("*.py"):
            text = path.read_text("utf-8", "replace")
            module = ".".join(path.relative_to(_ROOT).with_suffix("").parts)
            module = module.removesuffix(".__init__")
            for name in _DECORATED.findall(text):
                out[name] = module
    return out


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"(?m)^\s*//.*$", "", text)
    return re.sub(r"(?m)\s//[^\"'\n]*$", "", text)


def _qml_files() -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for folder in _QML_FOLDERS:
        files.extend(sorted((_ROOT / folder).rglob("*.qml")))
    return files


def _declarations(names: set[str]) -> set[tuple[str, str]]:
    """(file, type) for every `TypeName {` of a registered type."""
    pattern = re.compile(r"(?<![\w.])(" + "|".join(sorted(names)) + r")\s*\{")
    found: set[tuple[str, str]] = set()
    for path in _qml_files():
        text = _strip_comments(path.read_text("utf-8", "replace"))
        rel = path.relative_to(_ROOT).as_posix()
        for match in pattern.finditer(text):
            found.add((rel, match.group(1)))
    return found


def factory_made() -> list[str]:
    """Types QML makes only through the factory: used in a
    ModelFactory.create call and declared nowhere (test_leaks.py counts
    their shells)."""
    used: set[str] = set()
    for path in _qml_files():
        text = _strip_comments(path.read_text("utf-8", "replace"))
        used.update(_CREATE.findall(text))
    pending = {name for _, name in STAGE2_PENDING}
    return sorted(used - pending)


def test_the_scan_finds_the_registered_types() -> None:
    names = _registered()
    assert len(names) > 100, sorted(names)
    assert "HardwareLayoutModel" in names


def test_no_qml_file_declares_a_registered_type() -> None:
    found = _declarations(set(_registered()))
    new = sorted(found - STAGE2_PENDING)
    assert new == [], (
        'Make these with ModelFactory.create("TypeName", parent, props) '
        "(claude/plans/memory-qml-factory.md, section 2): " + repr(new)
    )


def test_the_pending_list_only_holds_what_is_still_declared() -> None:
    found = _declarations(set(_registered()))
    gone = sorted(STAGE2_PENDING - found)
    assert gone == [], "Converted: take these off STAGE2_PENDING: " + repr(gone)


def test_converted_types_are_uncreatable_in_qml() -> None:
    """Answer 4a: a type QML gets only from the factory is registered
    uncreatable, so a new `TypeName {}` fails at load; a type still
    declared somewhere can't be."""
    from gremlin.ui import model_factory

    only = set(model_factory.FACTORY_ONLY)
    assert sorted(set(factory_made()) - only) == []
    pending = {name for _, name in STAGE2_PENDING}
    assert sorted(only & pending) == []


def test_every_factory_call_names_a_registered_type() -> None:
    names = _registered()
    used: dict[str, list[str]] = {}
    for path in _qml_files():
        text = _strip_comments(path.read_text("utf-8", "replace"))
        for name in _CREATE.findall(text):
            used.setdefault(name, []).append(path.relative_to(_ROOT).as_posix())
    unknown = {name: files for name, files in used.items() if name not in names}
    assert unknown == {}
    # The registry ta.QmlElement fills holds them once their module loads.
    from gremlin.ui import type_aliases as ta

    for name in sorted(used):
        importlib.import_module(names[name])
        assert ta.QML_TYPES.get(name) is not None, name
