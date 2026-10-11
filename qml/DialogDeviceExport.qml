// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Export and Import of one device's folder as a ".gmap" file (08 S111,
// D-03-DEVICE-FOLDERS). The bindings are an optional part, ticked here.
//
//   DialogDeviceExport { id: _deviceExport }
//   _deviceExport.exportFolder(name, guid)   // tick, then a Save dialog
//   _deviceExport.importFolder()             // tick, then an Open dialog
//
// Or made with its properties set, it opens itself (StatusPage):
//   component.createObject(parent, {mode: "export", deviceName, deviceGuid,
//                                   shownName})   // or {mode: "import"}
//
// The work is gremlin/ui/device_export.py (DeviceExport); a refusal or
// failure is shown in the same box.

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style
import Gremlin.UI

Popup {
    id: _root

    objectName: "deviceExportDialog"

    // "export" or "import".
    property string mode: "export"
    property string deviceName: ""
    property string deviceGuid: ""
    // The device's name as the program shows it (title); deviceName if "".
    property string shownName: ""
    // Opens itself once made (createObject with mode set); false when the
    // caller opens it with exportFolder() / importFolder().
    property bool autoOpen: true
    property bool withBindings: false
    // The last result: "" when it worked, else why not.
    property string message: ""
    property bool done: false

    signal finished(bool ok, string message)

    Component.onCompleted: {
        if (!autoOpen)
            return
        // Called after the creator's properties are set.
        if (mode === "export" && deviceName !== "")
            exportFolder(deviceName, deviceGuid)
        else if (mode === "import")
            importFolder()
    }

    function exportFolder(name, guid) {
        mode = "export"
        if (String(name || "") !== deviceName)
            shownName = ""
        deviceName = String(name || "")
        deviceGuid = String(guid || "")
        withBindings = false
        message = ""
        done = false
        open()
    }

    function importFolder() {
        mode = "import"
        deviceName = ""
        deviceGuid = ""
        shownName = ""
        withBindings = false
        message = ""
        done = false
        open()
    }

    function _choose() {
        if (mode === "export") {
            _save.currentFile = "file:///" + _export.suggestedName(deviceName, deviceGuid)
            _save.open()
        } else {
            _open.open()
        }
    }

    function _result(error) {
        message = error
        done = true
        finished(error === "", error)
        if (error === "")
            close()
    }

    DeviceExport { id: _export }

    FilePicker {
        id: _save
        objectName: "deviceExportSave"
        kind: "export"
        mode: "save"
        title: "Export Device Folder"
        defaultSuffix: "gmap"
        nameFilters: ["Device folders (*.gmap)"]
        onPicked: (selected) => _root._result(
            _export.exportDevice(_root.deviceName, _root.deviceGuid,
                                 String(selected), _root.withBindings))
    }

    FilePicker {
        id: _open
        objectName: "deviceExportOpen"
        kind: "export"
        mode: "open"
        title: "Import Device Folder"
        nameFilters: ["Device folders (*.gmap)"]
        onPicked: (selected) => _root._result(
            _export.importDevice(String(selected), _root.withBindings))
    }

    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape
    padding: Style.dp(16)
    x: parent ? Math.round((parent.width - width) / 2) : 0
    y: parent ? Math.round((parent.height - height) / 2) : 0
    width: parent ? Math.min(parent.width - Style.dp(40), Style.dp(460)) : Style.dp(460)

    background: Rectangle {
        color: Style.background
        border.color: Style.fg
        border.width: Style.dp(1)
        radius: Style.dp(4)
    }

    contentItem: ColumnLayout {
        spacing: Style.dp(12)

        Label {
            Layout.fillWidth: true
            text: _root.mode === "export"
                ? "Export " + (_root.shownName || _root.deviceName)
                : "Import Device Folder"
            font.bold: true
            font.pixelSize: Style.dp(16)
            wrapMode: Text.Wrap
            color: Style.fg
        }

        Label {
            Layout.fillWidth: true
            text: _root.mode === "export"
                ? "Saves the device's folder (settings, map and pictures) as one .gmap file."
                : "Unpacks a .gmap file into a new device folder. A name that is taken gets \"(2)\"."
            wrapMode: Text.Wrap
            color: Style.fg
        }

        CheckBox {
            objectName: "deviceExportBindings"
            text: "Include bindings"
            checked: _root.withBindings
            onToggled: _root.withBindings = checked
        }

        Label {
            objectName: "deviceExportMessage"
            Layout.fillWidth: true
            visible: _root.done && _root.message !== ""
            text: _root.message
            wrapMode: Text.Wrap
            color: Style.danger
        }

        RowLayout {
            Layout.alignment: Qt.AlignRight
            spacing: Style.dp(8)

            Button {
                objectName: "deviceExportChoose"
                text: _root.mode === "export" ? "Save As…" : "Choose File…"
                onClicked: _root._choose()
            }

            Button {
                text: "Cancel"
                onClicked: _root.close()
            }
        }
    }
}
