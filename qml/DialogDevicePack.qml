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
    width: 720
    height: 640
    minimumWidth: 640
    minimumHeight: 560
    title: "Device Pack"

    Shortcut { sequence: "Esc"; onActivated: {} }
    Shortcut { sequence: "Return"; onActivated: {} }
    Shortcut { sequence: "Enter"; onActivated: {} }
    color: Style.background
    Universal.theme: Style.theme

    property string mode: "export"
    property string zipUrl: ""
    property string report: "Choose Export or Import. Nothing is written until you confirm."
    property var packInfo: ({})

    ListModel { id: _deviceModel }

    HardwareProfile { id: _hw }

    function _parse(raw) {
        try {
            return JSON.parse(raw)
        } catch (e) {
            return { ok: false, error: "Bad response" }
        }
    }

    function _yesNo(value) {
        return value ? "Yes" : "No"
    }

    function _counts(info) {
        if (!info)
            return ""
        return (info.buttons || 0) + " buttons, "
                + (info.axes || 0) + " axes, "
                + (info.hats || 0) + " hats"
    }

    function reloadDevices() {
        var info = _parse(_hw.packDevices())
        var rows = (info && info.devices) ? info.devices : []
        _deviceModel.clear()
        for (var i = 0; i < rows.length; ++i)
            _deviceModel.append(rows[i])
        if (_exportDevice.count > 0 && _exportDevice.currentIndex < 0)
            _exportDevice.currentIndex = 0
        refreshExport()
    }

    function refreshExport() {
        if (mode !== "export")
            return
        var name = _exportDevice.currentText || ""
        if (!name.length) {
            report = "Choose a device to pack."
            return
        }
        var info = _parse(_hw.peekPackDevice(name))
        if (!info.ok) {
            report = info.error || "This device has no module file yet."
            return
        }
        report = "Device: " + info.device
                + "\nModule file: " + (info.fileName || "")
                + "\nDevice id: " + (info.guid || "Not connected, and this profile has not seen it.")
                + "\n" + _counts(info)
                + "\nPicture: " + _yesNo(info.hasPhoto)
                + "\nButton map: " + _yesNo(info.hasMap)
                + "\nWires: not included"
                + "\n\nExport writes a zip only. The module file is not changed."
    }

    function refreshTarget() {
        if (mode !== "import" || !packInfo.ok)
            return
        var name = _saveAs.text || ""
        var target = name.length ? _parse(_hw.packTarget(name)) : { ok: false }
        var lines = [
            "Exported as: " + (packInfo.exportedName || ""),
            "Exported id: " + (packInfo.exportedGuid || "Not in this pack"),
            _counts(packInfo),
            "Picture: " + _yesNo(packInfo.hasPhoto),
            "Button map: " + _yesNo(packInfo.hasMap),
            "Wires: not included",
            ""
        ]
        if (!name.length) {
            lines.push("Type the device this pack is for, or pick one. Nothing is written yet.")
        } else if (target.hasFile) {
            lines.push("This will replace " + target.fileName + ".")
            lines.push("The current file will be saved in the imported folder first.")
        } else {
            lines.push("No module file exists for this name. A new file will be created.")
        }
        if (name.length && !(target.guid && target.guid.length))
            lines.push("No device id matches this name. The file can still be saved. Wires are not in this pack.")
        else if (name.length)
            lines.push("The file will use the id of the device you picked, not the id in the pack.")
        report = lines.join("\n")
    }

    function applySuggestion() {
        var suggested = packInfo.suggestedName || ""
        if (!suggested.length) {
            _saveAs.text = ""
            refreshTarget()
            return
        }
        for (var i = 0; i < _importDevice.count; i++) {
            if (_importDevice.textAt(i) === suggested) {
                _importDevice.currentIndex = i
                break
            }
        }
        _saveAs.text = suggested
        refreshTarget()
    }

    Component.onCompleted: reloadDevices()

    FileDialog {
        id: _save
        title: "Export device pack"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "zip"
        nameFilters: ["Device packs (*.zip)"]
        onAccepted: {
            var dest = Helpers.fileDialogUrl(_save)
            var name = _exportDevice.currentText || ""
            var info = _parse(_hw.exportPack(name, dest))
            report = info.ok ? ("Wrote " + info.path) : (info.error || "Export failed.")
        }
    }

    FileDialog {
        id: _pick
        title: "Open device pack"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Device packs (*.zip)"]
        onAccepted: {
            zipUrl = Helpers.fileDialogUrl(_pick)
            packInfo = _parse(_hw.peekPackZip(zipUrl))
            if (!packInfo.ok) {
                report = packInfo.error || "Could not read that pack."
                return
            }
            mode = "import"
            _pages.currentIndex = 1
            applySuggestion()
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        anchors.bottomMargin: 62
        spacing: 10

        Label {
            text: "Device Pack"
            font.pixelSize: 22
            font.bold: true
            color: Style.foreground
        }
        Label {
            text: "A pack is one device's module file and its pictures. It does not include wires."
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
            color: "#A1A1AA"
        }

        TabBar {
            id: _pages
            Layout.fillWidth: true
            onCurrentIndexChanged: {
                mode = currentIndex === 0 ? "export" : "import"
                if (mode === "export")
                    refreshExport()
                else
                    refreshTarget()
            }
            TabButton { text: "Export"; width: implicitWidth }
            TabButton { text: "Import"; width: implicitWidth }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 280
            currentIndex: _pages.currentIndex

            ColumnLayout {
                spacing: 8
                Label { text: "Device"; font.bold: true; color: Style.foreground }
                ComboBox {
                    id: _exportDevice
                    Layout.fillWidth: true
                    model: _deviceModel
                    textRole: "name"
                    onActivated: refreshExport()
                    onCurrentIndexChanged: refreshExport()
                }
                Button {
                    text: "Export…"
                    focusPolicy: Qt.NoFocus
                    enabled: (_exportDevice.currentText || "").length > 0
                    onClicked: {
                        var name = _exportDevice.currentText
                        var hint = _hw.defaultExportUrl(name)
                        if (hint && hint.length) {
                            try { _save.selectedFile = hint } catch (e) {}
                            try { _save.currentFile = hint } catch (e) {}
                        }
                        _save.open()
                    }
                }
            }

            ColumnLayout {
                spacing: 8
                Button {
                    text: "Choose zip…"
                    focusPolicy: Qt.NoFocus
                    onClicked: _pick.open()
                }
                Label { text: "Put this pack on"; font.bold: true; color: Style.foreground }
                ComboBox {
                    id: _importDevice
                    Layout.fillWidth: true
                    model: _deviceModel
                    textRole: "name"
                    onActivated: _saveAs.text = currentText
                }
                Label { text: "Save as"; color: Style.foreground }
                TextField {
                    id: _saveAs
                    Layout.fillWidth: true
                    placeholderText: "Device name on this machine"
                    onTextChanged: refreshTarget()
                }
                Label {
                    text: "The name and id in the pack are labels. The device you type here is the one that is written."
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                    color: "#A1A1AA"
                }
                Button {
                    text: "Import"
                    focusPolicy: Qt.NoFocus
                    enabled: zipUrl.length > 0 && packInfo.ok === true && _saveAs.text.length > 0
                    onClicked: {
                        var info = _parse(_hw.importPack(zipUrl, _saveAs.text))
                        report = info.ok ? (info.report || "Imported.") : (info.error || "Import failed.")
                        if (info.ok)
                            reloadDevices()
                    }
                }
            }
        }

        Rectangle {
            id: _reportBox
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#18181B"
            border.color: "#3F3F46"
            radius: 4
            ScrollView {
                anchors.fill: parent
                anchors.margins: 10
                TextArea {
                    text: report
                    wrapMode: Text.WordWrap
                    readOnly: true
                    selectByMouse: true
                    color: Style.foreground
                    width: _reportBox.width - 28
                    background: null
                }
            }
        }

        RowLayout {
            Item { Layout.fillWidth: true }
            Button { text: "Close"; focusPolicy: Qt.NoFocus; onClicked: _win.close() }
        }
    }

    DebugFileLine {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
    }
}
