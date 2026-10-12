# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from PySide6 import QtCore

from gremlin import common


def display_error(message: str, details: str = "") -> None:
    """Display an error message in the UI.

    Args:
        message (str): The error message to display.
    """
    signal.showError.emit(message, details)


@common.SingletonDecorator
class Signal(QtCore.QObject):
    reloadCurrentInputItem = QtCore.Signal()

    inputItemChanged = QtCore.Signal(int)

    setInputIndex = QtCore.Signal(int)

    modesChanged = QtCore.Signal()
    # A mode renamed (old, new) or deleted (name): what names a mode follows.
    modeRenamed = QtCore.Signal(str, str)
    modeDeleted = QtCore.Signal(str)

    profileChanged = QtCore.Signal()

    logicalDeviceModified = QtCore.Signal()

    # The Logical Device was read again from its file (Discard, Restore,
    # Import, History Restore): its Undo steps no longer apply (D-04-LD-FILE).
    logicalDeviceReloaded = QtCore.Signal()

    # OSC's address list (its own file) changed in memory (D-09-OSC-FILE).
    oscDeviceModified = QtCore.Signal()
    # OSC's file was read again (Discard, Restore, Import, History Restore).
    oscDeviceReloaded = QtCore.Signal()
    # OSC's server settings (its file's "server" part) changed.
    oscServerSettingsChanged = QtCore.Signal()
    # What can't be sent may have changed (claims, vJoy driver, Xbox modules,
    # OSC settings, Logical Device file). Sent only by the output layer,
    # once per burst, on the main thread; every red ⚠ listens to it
    # (D-05-CANT-SEND-LIVE).
    cantSendChanged = QtCore.Signal()
    # Which inputs drive which outputs may have changed. Sent only by
    # gremlin.ui.input_pairing, once per burst, on the main thread
    # (D-01-OWNER-NOTICES).
    bindingsChanged = QtCore.Signal()
    # A device's shown name (the user's name for it, a twin name) may have
    # changed. Sent only by gremlin.device_aliases, once per burst, on the
    # main thread (D-01-OWNER-NOTICES).
    deviceNamesChanged = QtCore.Signal()
    # A module file was saved, deleted or moved aside. Sent only by
    # gremlin.modules.store, once per burst, on the main thread
    # (D-01-OWNER-NOTICES).
    moduleFilesChanged = QtCore.Signal()
    # Xbox Setup's number of pads changed (D-XBOX-PADS). Sent only by
    # gremlin.modules.output.set_xbox_pad_count.
    xboxPadsChanged = QtCore.Signal()
    # Options' "OSC settings are in OSC › Module Setup" button: the main
    # window opens OSC's Module Setup, as its card does.
    openOscModuleSetup = QtCore.Signal()
    # The OSC page's "Feedback settings…": OSC's Module Setup on the named
    # tab ("Feedback") (09 S154).
    openOscModuleSetupAt = QtCore.Signal(str)
    # OSC Setup's Feedback tab "Edit on the OSC page": the main window shows
    # the OSC page (09 S154).
    openOscPage = QtCore.Signal()
    # OSC's feedback rows (its file's "feedback" part) changed
    # (D-09-OSC-FEEDBACK).
    oscFeedbackChanged = QtCore.Signal()
    # "Find OSC devices" found or lost a device (D-09-OSC-DISCOVERY).
    oscDevicesFound = QtCore.Signal()

    # An input's actions changed where inputItemChanged isn't sent (the
    # Logical Device's action editor): summaries of the profile's actions,
    # such as a card's Driven by, check again.
    actionsChanged = QtCore.Signal()

    configChanged = QtCore.Signal()

    uiScaleChanged = QtCore.Signal()

    showError = QtCore.Signal(str, str)

    showNotification = QtCore.Signal(str, str)


signal = Signal()
