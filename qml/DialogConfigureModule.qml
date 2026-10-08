// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Dialogs
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Style
import "helpers.js" as Helpers

ApplicationWindow {
    font.pixelSize: Style.fontSize
    id: _win

    // Opens at the size it was left at (capped to the screen).
    ToolWindowMemory {
        host: _win
        name: "moduleSetup"
        defaultWidth: Style.fitWidth(Style.dp(980), Screen)
        defaultHeight: Style.fitHeight(Style.dp(640), Screen)
    }

    property string direction: "source"
    property string deviceName: ""
    property string deviceGuid: ""
    property string photoUrl: ""
    property var moduleModel: null

    property string moduleFileLabel: ""
    property string moduleFileMessage: ""
    property bool moduleFileError: false
    property string moduleFileNotice: ""
    property bool claimDirty: false
    property bool allowClose: false

    // For the main window's quit: unsaved edits this window would ask about.
    function hasUnsavedWork() {
        return claimDirty && !allowClose
    }
    property string saveIntent: "close"
    property string pendingFileSlug: ""
    property var moduleFileChoices: []
    property bool _moduleFileQuiet: false

    function refreshModuleFileLabel() {
        if (!moduleModel || !deviceName.length) {
            moduleFileLabel = ""
            moduleFileChoices = []
            return
        }
        var slug = String(moduleModel.moduleFileFor(deviceGuid, deviceName) || "")
        var saved = moduleModel.moduleFileExists(deviceGuid, deviceName)
        var names = moduleModel.moduleFileNames(deviceGuid, deviceName) || []
        var foreign = String(moduleModel.foreignModuleFile(deviceGuid, deviceName) || "")
        var choices = []
        var i
        moduleFileLabel = slug + ".json" + (saved ? "" : " (not saved yet)")
        moduleFileNotice = foreign.length
            ? ("This stick still opens " + foreign + ".json. Import that file to copy it here.")
            : ""
        for (i = 0; i < names.length; i++) {
            var item = String(names[i] || "")
            if (!item.length)
                continue
            choices.push(item + ".json")
        }
        _moduleFileQuiet = true
        moduleFileChoices = choices
        if (_moduleFilePick)
            _moduleFilePick.currentIndex = -1
        _moduleFileQuiet = false
    }

    function reloadModuleControls() {
        if (_hw.setDeviceGuid)
            _hw.setDeviceGuid(deviceGuid)
        _driver.loadDevice(deviceGuid, deviceName)
        claimDirty = false
        var url = _hw.profilePhotoUrl(deviceName)
        photoUrl = url.length ? (url.split("?")[0] + "?t=" + Date.now()) : ""
    }

    width: Style.fitWidth(Style.dp(980), Screen)
    height: Style.fitHeight(Style.dp(640), Screen)
    minimumWidth: Style.fitWidth(Style.dp(800), Screen)
    minimumHeight: Style.fitHeight(Style.dp(480), Screen)
    title: direction === "dest" ? "Output Module Setup" : "Input Module Setup"
    color: Style.background
    U.Universal.theme: Style.theme
    flags: Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowSystemMenuHint
    modality: Qt.NonModal

    // Stick HID often synthesizes Esc/Return. Do not let those click Cancel/Save.
    Shortcut { sequence: "Esc"; onActivated: {} }
    // Undo and Redo for the checks and names (a name being typed keeps its
    // own Ctrl+Z).
    Shortcut { sequences: [StandardKey.Undo]; onActivated: _win.undoEdit() }
    Shortcut { sequences: [StandardKey.Redo, "Ctrl+Y"]; onActivated: _win.redoEdit() }
    Shortcut { sequence: "Return"; onActivated: {} }
    Shortcut { sequence: "Enter"; onActivated: {} }

    HardwareProfile { id: _hw }
    DriverInputModel { id: _driver }
    Connections {
        target: _driver
        function onUserEdited() { claimDirty = true }
    }

    Component.onCompleted: {
        if (_hw.setDeviceGuid)
            _hw.setDeviceGuid(deviceGuid)
        // A picture imported in a session that never finished (the program
        // closed first) was never saved: the saved one goes back. Only with
        // this window's own safety copy (the Button Map keeps its own).
        if (_hw.restorePhotoFor)
            _hw.restorePhotoFor(deviceName, "setup")
        _driver.loadDevice(deviceGuid, deviceName)
        claimDirty = false
        _win.photoUrl = _hw.profilePhotoUrl(deviceName)
    }

    // Import Image changes the photo files at once; the starting photo is
    // kept so Cancel can put it back, as in the Button Map (03 Q2, 07 Q5).
    // TODO(batch1): the "setup" owner slots (stashPhotoFor, restorePhotoFor,
    // dropPhotoStashFor) are asked of hardware_profile.py; until then the
    // Button Map's safety copy is shared.
    function stashPhoto() {
        if (_hw.stashPhotoFor)
            _hw.stashPhotoFor(deviceName, "setup")
        else
            _hw.stashPhoto(deviceName)
    }

    function dropPhotoStash() {
        if (_hw.dropPhotoStashFor)
            _hw.dropPhotoStashFor(deviceName, "setup")
        else
            _hw.dropPhotoStash(deviceName)
    }

    function putPhotoBack() {
        var back = _hw.restorePhotoFor ? _hw.restorePhotoFor(deviceName, "setup")
                                       : _hw.restorePhoto(deviceName)
        if (!back)
            return
        var url = _hw.profilePhotoUrl(deviceName)
        photoUrl = url.length ? (url.split("?")[0] + "?t=" + Date.now()) : ""
    }

    function commitModule() {
        // The photo Import Image put in the device's folder is named by this
        // save: one write, and the library got its copy once, at Import
        // Image (03 Q3).
        if (!_driver.saveClaim(deviceName, direction)) {
            _saveGate.announce(false, _driver.saveBlockedReason()
                               || "Not written. It is still only on this screen.")
            if (backend)
                backend.noteSave("The module file was not written.")
            return false
        }
        // Saved: the photo this session started with is no longer needed.
        dropPhotoStash()
        var profilePath = backend ? backend.profilePath() : ""
        // A profile save would leave out unfinished actions without asking:
        // keep the profile unsaved and say so; the main window's Save asks.
        var unfinished = (direction === "dest" && profilePath !== "") ? backend.unfinishedActions() : []
        if (unfinished.length) {
            if (moduleModel && moduleModel.notifyClaims)
                moduleModel.notifyClaims()
            claimDirty = false
            refreshModuleFileLabel()
            _saveGate.announce(true, "Saved to the module file. The profile was not saved: "
                + (unfinished.length === 1 ? "1 action is" : unfinished.length + " actions are")
                + " not finished. Save the profile from the main window to choose what to do.")
            backend.noteSave("Saved the module file to " + _driver.lastSavedPath() + ". The profile was not saved (unfinished actions).")
            return true
        }
        if (direction === "dest" && profilePath !== "") {
            if (!backend.saveProfile(profilePath)) {
                _saveGate.announce(false, "Saved to the module file. The profile was not written.")
                backend.noteSave("Saved the module file to " + _driver.lastSavedPath() + ". The profile was not written.")
                return false
            }
        }
        if (moduleModel && moduleModel.notifyClaims)
            moduleModel.notifyClaims()
        claimDirty = false
        refreshModuleFileLabel()
        _saveGate.announce(true, direction === "dest" && profilePath !== ""
            ? "Saved to the module file and the profile." : "Saved to the module file.")
        if (backend) {
            var note = "Saved the module file to " + _driver.lastSavedPath()
            if (direction === "dest" && profilePath !== "")
                note += ". Saved the profile to " + profilePath
            backend.noteSave(note)
        }
        return true
    }

    function undoEdit() {
        if (!_driver.canUndo)
            return
        _driver.undo()
    }

    function redoEdit() {
        if (!_driver.canRedo)
            return
        _driver.redo()
    }

    function showImportResult(message) {
        moduleFileError = message.indexOf("Imported ") !== 0
        refreshModuleFileLabel()
        moduleFileMessage = moduleFileError ? message : ("Imported into " + moduleFileLabel)
        if (!moduleFileError)
            reloadModuleControls()
        _importNotice.failed = moduleFileError
        _importNotice.titleText = moduleFileError ? "Import Failed" : "Imported"
        _importNotice.messageText = message
        _importNotice.canUndo = !moduleFileError && moduleModel && moduleModel.importCanUndo(deviceGuid, deviceName)
        _importNotice.open()
    }

    function applyPendingFile() {
        if (!pendingFileSlug.length || !moduleModel)
            return
        var message = moduleModel.importModuleFile(deviceGuid, deviceName, pendingFileSlug, direction)
        pendingFileSlug = ""
        showImportResult(message)
    }

    onClosing: function(close) {
        if (!claimDirty || allowClose)
            return
        close.accepted = false
        saveIntent = "close"
        _saveGate.detail = "Checks, names, and the picture on this screen are not saved. Close without saving and they will be lost."
        _saveGate.ask()
    }

    FileDialog {
        id: _imageDialog
        title: "Import Image"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Images (*.png *.jpg *.jpeg *.webp *.bmp)"]
        currentFolder: _hw.imagesFolderUrl()
        onAccepted: {
            var src = ""
            if (selectedFile)
                src = selectedFile.toString ? selectedFile.toString() : ("" + selectedFile)
            if ((!src || !src.length) && selectedFiles && selectedFiles.length)
                src = selectedFiles[0].toString ? selectedFiles[0].toString() : ("" + selectedFiles[0])
            if (!src || !src.length)
                src = currentFile && currentFile.toString ? currentFile.toString() : currentFile
            // The starting photo is kept first (once per session).
            _win.stashPhoto()
            var rel = _hw.copyImage(src, deviceName)
            var url = rel.length ? _hw.imageUrl(rel) : ""
            if (!url.length)
                url = _hw.profilePhotoUrl(deviceName)
            _win.photoUrl = url.length ? (url.split("?")[0] + "?t=" + Date.now()) : ""
            claimDirty = true
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Style.dp(12)
        anchors.bottomMargin: Style.dp(78)
        spacing: Style.dp(10)

        RunningNote { appliesAtOnce: true }

        Label {
            text: deviceName.length ? deviceName : "Unnamed device"
            font.pixelSize: Style.dp(16)
            font.bold: true
        }

        Label {
            // An output can't be pressed: its controls are ticked. A pressed
            // key is found (or added) and ticked (_on_key).
            text: direction === "dest"
                ? "Tick the outputs this module may use; clear a check box to let it go. "
                  + "Names and marks are set in the Button Map."
                : deviceName.toLowerCase() === "keyboard"
                ? "Press a key to find it and claim it for this module; clear its check box to let it go."
                : "Press a control on the device to claim it for this module; clear its check box to let it go. "
                  + "Names, marks and 5-way hats are set in the Button Map."
            color: Style.fgMuted
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Style.dp(12)

            Rectangle {
                Layout.preferredWidth: Style.dp(320)
                Layout.fillHeight: true
                color: Style.bgCard
                border.color: Style.line
                radius: Style.dp(4)

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Style.dp(8)
                    Image {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        source: photoUrl
                        fillMode: Image.PreserveAspectFit
                        visible: photoUrl && photoUrl.length
                    }
                    Label {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        visible: !(photoUrl && photoUrl.length)
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        wrapMode: Text.WordWrap
                        color: Style.fgMuted
                        text: "No photo for this module.\nImport image…"
                    }
                    Button {
                        text: "Import Image…"
                        onClicked: _imageDialog.open()
                    }
                }
            }

            Frame {
                Layout.fillWidth: true
                Layout.fillHeight: true

                ListView {
                    id: _list
                    anchors.fill: parent
                    clip: true
                    model: _driver
                    currentIndex: -1
                    highlightMoveDuration: 80
                    Connections {
                        target: _driver
                        function onRowActivated(row) {
                            _list.currentIndex = row
                            _list.positionViewAtIndex(row, ListView.Contain)
                        }
                    }
                    delegate: Rectangle {
                        width: ListView.view.width
                        height: Style.dp(34)
                        color: model.lit ? Style.okFill : (index === _list.currentIndex ? Style.bgRaised : "transparent")

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Style.dp(4)
                            anchors.rightMargin: Style.dp(8)
                            spacing: Style.dp(8)

                        CheckBox {
                            checked: model.claimed
                            onClicked: {
                                claimDirty = true
                                if (checked)
                                    _driver.setClaimed(index, true)
                                else
                                    _driver.setClaimed(index, false)
                            }
                        }
                        Label {
                            text: model.label
                            Layout.preferredWidth: Style.dp(120)
                            color: model.lit ? Style.okTextStrong : Style.foreground
                        }
                        TextField {
                            Layout.fillWidth: true
                            text: model.friendly
                            placeholderText: "Friendly name"
                            onEditingFinished: {
                                claimDirty = true
                                _driver.setFriendly(index, text)
                            }
                        }
                        }
                    }
                    ScrollBar.vertical: ScrollBar {}
                }
                Label {
                    anchors.centerIn: parent
                    visible: _list.count === 0
                    color: Style.fgMuted
                    wrapMode: Text.WordWrap
                    width: parent.width - Style.dp(24)
                    horizontalAlignment: Text.AlignHCenter
                    text: deviceName.toLowerCase() === "keyboard"
                          ? "Press a key to add it."
                          : "No controls reported. For a stick, check that Windows sees it (Set up USB game controllers)."
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Button {
                text: "Module File"
                focusPolicy: Qt.NoFocus
                onClicked: {
                    refreshModuleFileLabel()
                    moduleFileMessage = ""
                    _moduleFileDialog.open()
                }
            }
            Button {
                objectName: "moduleUndo"
                text: "Undo"
                focusPolicy: Qt.NoFocus
                enabled: _driver.canUndo
                onClicked: _win.undoEdit()
            }
            Button {
                objectName: "moduleRedo"
                text: "Redo"
                focusPolicy: Qt.NoFocus
                enabled: _driver.canRedo
                onClicked: _win.redoEdit()
            }
            // This device's saved changes (Tools > History).
            Button {
                objectName: "moduleHistory"
                text: "History"
                focusPolicy: Qt.NoFocus
                enabled: deviceName.length > 0
                // By the device's own file: twin sticks share a name.
                onClicked: Helpers.createComponent("DialogHistory.qml", {
                    filter: JSON.stringify({
                        fileName: String(moduleModel ? moduleModel.moduleFileFor(deviceGuid, deviceName) : "") + ".json"
                    }),
                    filterLabel: deviceName
                })
            }
            Item { Layout.fillWidth: true }
            Button {
                text: "Cancel"
                focusPolicy: Qt.NoFocus
                onClicked: _win.close()
            }
            Button {
                // Output modules keep their claims in the profile too.
                text: direction === "dest" && backend && backend.profilePath() !== ""
                    ? "Save Module and Profile" : "Save Module"
                focusPolicy: Qt.NoFocus
                onClicked: {
                    saveIntent = "stay"
                    commitModule()
                }
            }
        }
    }

    Dialog {
        id: _moduleFileDialog
        title: "Module File"
        modal: true
        anchors.centerIn: parent
        width: Style.dp(460)
        padding: Style.dp(16)
        standardButtons: Dialog.Close

        contentItem: ColumnLayout {
            spacing: Style.dp(10)
            Label {
                text: "Current file"
                color: Style.fgMuted
                font.pixelSize: Style.dp(12)
            }
            Label {
                Layout.fillWidth: true
                text: moduleFileLabel.length ? moduleFileLabel : "None"
                wrapMode: Text.WordWrap
                font.pixelSize: Style.dp(14)
            }
            Label {
                Layout.fillWidth: true
                text: "Import copies the chosen file into this device's file. The chosen file is left where it was."
                color: Style.fgMuted
                wrapMode: Text.WordWrap
                font.pixelSize: Style.dp(12)
            }
            Label {
                Layout.fillWidth: true
                visible: moduleFileNotice.length > 0
                text: moduleFileNotice
                color: Style.fgMuted
                wrapMode: Text.WordWrap
                font.pixelSize: Style.dp(12)
            }
            Label {
                text: "Import from"
                color: Style.fgMuted
                font.pixelSize: Style.dp(12)
            }
            ComboBox {
                id: _moduleFilePick
                Layout.fillWidth: true
                model: moduleFileChoices
                onActivated: function(index) {
                    if (_moduleFileQuiet || !moduleModel)
                        return
                    var label = String(currentText || "")
                    var slug = label.replace(/\.json$/i, "")
                    if (claimDirty) {
                        pendingFileSlug = slug
                        saveIntent = "file"
                        _saveGate.detail = "Checks on this screen are not saved. Import without saving and they will be lost."
                        _saveGate.ask()
                        return
                    }
                    pendingFileSlug = slug
                    applyPendingFile()
                }
            }
            Button {
                text: "Browse for File"
                Layout.fillWidth: true
                onClicked: {
                    if (moduleModel)
                        _moduleLoadDialog.currentFolder = moduleModel.importedFolderUrl()
                    _moduleLoadDialog.open()
                }
            }
            Button {
                text: "Open Modules Folder"
                Layout.fillWidth: true
                onClicked: {
                    if (moduleModel)
                        Qt.openUrlExternally(moduleModel.mapsFolderUrl())
                }
            }
            Button {
                text: "Delete File"
                Layout.fillWidth: true
                onClicked: {
                    if (!moduleModel)
                        return
                    _deleteGate.confirmThen("Delete Module File",
                        "Delete " + moduleFileLabel + "? It holds this device's claimed inputs, calibration and Button Map layout.\n\n"
                        + "An autosave of it (\"Autosave: module file deleted\") is kept in the Device Library first; if it can't be kept, nothing is deleted. "
                        + "The device's pictures are kept.",
                        "Delete file", function() {
                            moduleFileMessage = moduleModel.deleteModuleFile(deviceGuid, deviceName)
                            moduleFileError = moduleFileMessage.length > 0
                            refreshModuleFileLabel()
                            if (!moduleFileMessage.length) {
                                // The file is gone (its pictures stay, 03
                                // Q14): a kept starting photo must not come
                                // back later.
                                dropPhotoStash()
                                reloadModuleControls()
                            }
                        }, null, true)
                }
            }
            Label {
                Layout.fillWidth: true
                visible: moduleFileMessage.length > 0
                text: moduleFileMessage
                color: moduleFileError ? Style.dangerText : Style.fgMuted
                wrapMode: Text.WordWrap
            }
        }
    }

    FileDialog {
        id: _moduleLoadDialog
        title: "Choose Module File"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Module files (*.json)"]
        onAccepted: {
            if (!moduleModel)
                return
            var src = selectedFile
            if (src && src.toString)
                src = src.toString()
            moduleFileMessage = moduleModel.importModuleFile(deviceGuid, deviceName, src || "", direction)
            showImportResult(moduleFileMessage)
        }
    }

    Popup {
        id: _importNotice

        property string titleText: "Imported"
        property string messageText: ""
        property bool canUndo: false
        // The import or its undo failed: the border shows it.
        property bool failed: false

        parent: Overlay.overlay
        anchors.centerIn: parent
        modal: true
        focus: true
        closePolicy: Popup.NoAutoClose
        padding: Style.dp(16)

        background: Rectangle {
            color: Style.background
            border.color: _importNotice.failed ? Style.danger : Style.accent
            border.width: Style.dp(1)
            radius: Style.dp(4)
        }

        contentItem: ColumnLayout {
            spacing: Style.dp(12)

            Label {
                text: _importNotice.titleText
                font.bold: true
                font.pixelSize: Style.dp(16)
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                Layout.preferredWidth: Style.dp(560)
            }

            Label {
                text: _importNotice.messageText
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                Layout.preferredWidth: Style.dp(560)
            }

            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: Style.dp(8)

                Button {
                    visible: _importNotice.canUndo
                    text: "Undo"
                    onClicked: {
                        if (!moduleModel)
                            return
                        var message = moduleModel.undoLastImport(deviceGuid, deviceName)
                        var ok = message.indexOf("Undone") === 0
                        _importNotice.failed = !ok
                        _importNotice.titleText = ok ? "Undone" : "Undo Failed"
                        _importNotice.messageText = message
                        _importNotice.canUndo = false
                        refreshModuleFileLabel()
                        if (ok)
                            reloadModuleControls()
                    }
                }

                Button {
                    text: "OK"
                    highlighted: true
                    onClicked: {
                        if (moduleModel && _importNotice.titleText === "Imported")
                            moduleModel.dropImportUndo(deviceGuid, deviceName)
                        _importNotice.close()
                    }
                }
            }
        }
    }

    // Asks before Delete file.
    DismissibleDialog {
        id: _deleteGate
    }

    DismissibleDialog {
        id: _saveGate
        onSaveChosen: {
            if (!_win.commitModule())
                return
            if (saveIntent === "file")
                applyPendingFile()
        }
        onDiscardChosen: {
            claimDirty = false
            _win.putPhotoBack()
            if (saveIntent === "close") {
                allowClose = true
                _win.close()
            } else if (saveIntent === "file") {
                applyPendingFile()
            }
        }
        onCancelled: refreshModuleFileLabel()
        onAcknowledged: {
            if (claimDirty)
                return
            if (saveIntent === "close" || saveIntent === "stay") {
                allowClose = true
                _win.close()
            }
        }
    }
}
