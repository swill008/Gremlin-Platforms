// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal
import QtQuick.Dialogs
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Style
import "helpers.js" as Helpers

Window {
    id: _win

    property string direction: "source"
    property string deviceName: ""
    property string deviceGuid: ""
    property string photoUrl: ""
    property var moduleModel: null

    property string moduleFileLabel: ""
    property string moduleFileMessage: ""
    property string shownModulePath: ""
    property bool claimDirty: false
    property bool allowClose: false
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
        var choices = []
        var pick = 0
        var i
        moduleFileLabel = slug + ".json" + (saved ? "" : " (not saved yet)")
        for (i = 0; i < names.length; i++) {
            var item = String(names[i] || "")
            if (!item.length)
                continue
            if (item === slug)
                pick = choices.length
            choices.push(item + ".json")
        }
        _moduleFileQuiet = true
        moduleFileChoices = choices
        if (_moduleFilePick)
            _moduleFilePick.currentIndex = pick
        _moduleFileQuiet = false
    }

    function reloadModuleControls() {
        if (_hw.setDeviceGuid)
            _hw.setDeviceGuid(deviceGuid)
        shownModulePath = _hw.defaultPath(deviceName)
        _driver.loadDevice(deviceGuid, deviceName)
        claimDirty = false
        var url = _hw.profilePhotoUrl(deviceName)
        photoUrl = url.length ? (url.split("?")[0] + "?t=" + Date.now()) : ""
    }

    width: 980
    height: 640
    minimumWidth: 800
    minimumHeight: 480
    title: direction === "dest" ? "Configure output module" : "Configure input module"
    color: Style.background
    Universal.theme: Style.theme
    flags: Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowSystemMenuHint
    modality: Qt.NonModal

    // Stick HID often synthesizes Esc/Return. Do not let those click Cancel/Save.
    Shortcut { sequence: "Esc"; onActivated: {} }
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
        shownModulePath = _hw.defaultPath(deviceName)
        _driver.loadDevice(deviceGuid, deviceName)
        claimDirty = false
        _win.photoUrl = _hw.profilePhotoUrl(deviceName)
    }

    function commitModule() {
        if (_win.photoUrl && _win.photoUrl.length)
            _hw.keepPhoto(deviceName, _win.photoUrl)
        if (!_driver.saveClaim(deviceName, direction)) {
            _saveGate.announce(false, "Not written. It is still only on this screen.")
            return false
        }
        if (direction === "dest" && backend && backend.profilePath() !== "") {
            if (!backend.saveProfile(backend.profilePath())) {
                _saveGate.announce(false, "Saved to the module file. The profile was not written.")
                return false
            }
        }
        if (moduleModel && moduleModel.notifyClaims)
            moduleModel.notifyClaims()
        claimDirty = false
        refreshModuleFileLabel()
        _saveGate.announce(true, "Saved to the module file.")
        return true
    }

    function applyPendingFile() {
        if (!pendingFileSlug.length || !moduleModel)
            return
        moduleModel.bindModuleFile(deviceGuid, deviceName, pendingFileSlug)
        pendingFileSlug = ""
        moduleFileMessage = ""
        refreshModuleFileLabel()
        reloadModuleControls()
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
        title: "Import image"
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
        anchors.margins: 12
        anchors.bottomMargin: 78
        spacing: 10

        Label {
            text: deviceName.length ? deviceName : "Unnamed device"
            font.pixelSize: 16
            font.bold: true
        }

        Label {
            text: "Device is a name line. Marks and 5-ways stay on Button Map. Press a control to claim it; uncheck to undo."
            color: "#A1A1AA"
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 12

            Rectangle {
                Layout.preferredWidth: 320
                Layout.fillHeight: true
                color: "#18181B"
                border.color: "#3F3F46"
                radius: 4

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 8
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
                        color: "#A1A1AA"
                        text: "No photo for this module.\nImport image…"
                    }
                    Button {
                        text: "Import image…"
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
                        height: 34
                        color: model.lit ? "#14532D" : (index === _list.currentIndex ? "#27272A" : "transparent")

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 4
                            anchors.rightMargin: 8
                            spacing: 8

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
                            Layout.preferredWidth: 120
                            color: model.lit ? "#BBF7D0" : Style.foreground
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
                    color: "#A1A1AA"
                    wrapMode: Text.WordWrap
                    width: parent.width - 24
                    horizontalAlignment: Text.AlignHCenter
                    text: deviceName.toLowerCase() === "keyboard"
                          ? "Press a key to add it."
                          : "No controls reported. For a stick, check DILL sees the device."
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Button {
                text: "Import devices…"
                focusPolicy: Qt.NoFocus
                onClicked: Helpers.createComponent("DialogImportDevices.qml")
            }
            Button {
                text: "Export devices…"
                focusPolicy: Qt.NoFocus
                onClicked: Helpers.createComponent("DialogExportDevices.qml", {"deviceName": deviceName})
            }
            Button {
                text: "Module file"
                visible: direction !== "dest"
                focusPolicy: Qt.NoFocus
                onClicked: {
                    refreshModuleFileLabel()
                    moduleFileMessage = ""
                    _moduleFileDialog.open()
                }
            }
            Item { Layout.fillWidth: true }
            Button {
                text: "Cancel"
                focusPolicy: Qt.NoFocus
                onClicked: _win.close()
            }
            Button {
                text: "Save module"
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
        title: "Module file"
        modal: true
        anchors.centerIn: parent
        width: 460
        padding: 16
        standardButtons: Dialog.Close

        contentItem: ColumnLayout {
            spacing: 10
            Label {
                text: "Current file"
                color: "#A1A1AA"
                font.pixelSize: 12
            }
            Label {
                Layout.fillWidth: true
                text: moduleFileLabel.length ? moduleFileLabel : "None"
                wrapMode: Text.WordWrap
                font.pixelSize: 14
            }
            Label {
                Layout.fillWidth: true
                text: "This stick's inputs and button map use this file."
                color: "#A1A1AA"
                wrapMode: Text.WordWrap
                font.pixelSize: 12
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
                        _saveGate.detail = "Checks on this screen are not saved. Switch files without saving and they will be lost."
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
                        _moduleLoadDialog.currentFolder = moduleModel.mapsFolderUrl()
                    _moduleLoadDialog.open()
                }
            }
            Button {
                text: "Delete file"
                Layout.fillWidth: true
                onClicked: {
                    if (!moduleModel)
                        return
                    moduleFileMessage = moduleModel.deleteModuleFile(deviceGuid, deviceName)
                    refreshModuleFileLabel()
                    if (!moduleFileMessage.length)
                        reloadModuleControls()
                }
            }
            Label {
                Layout.fillWidth: true
                visible: moduleFileMessage.length > 0
                text: moduleFileMessage
                color: "#F87171"
                wrapMode: Text.WordWrap
            }
        }
    }

    FileDialog {
        id: _moduleLoadDialog
        title: "Browse for file"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Module files (*.json)"]
        onAccepted: {
            if (!moduleModel)
                return
            var src = selectedFile
            if (src && src.toString)
                src = src.toString()
            moduleFileMessage = moduleModel.loadModuleFile(deviceGuid, deviceName, src || "")
            refreshModuleFileLabel()
            if (!moduleFileMessage.length)
                reloadModuleControls()
        }
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

    DebugFileLine {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        moduleFile: shownModulePath
    }
}
