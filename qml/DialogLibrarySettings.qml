// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

import Gremlin.Style

// Device Library Settings (10 S36-S37): how many autosaves are kept per
// stick, what Copy and Swap tick by default, and the library folder.
// Autosaves are always on (D-10-STREAMLINE).
Dialog {
    id: _dlg
    objectName: "librarySettingsDialog"
    title: "Device Library Settings"
    anchors.centerIn: Overlay.overlay
    width: Math.min(parent ? parent.width - Style.dp(40) : Style.dp(560), Style.dp(560))
    modal: true

    property var lib: null
    property var parts: ({})
    property string folder: ""
    property string startFolder: ""

    function openNow() {
        if (!lib)
            return
        var s = lib.settings()
        _keep.value = s.keep || 10
        var p = {}
        for (var i = 0; i < lib.partList.length; i++)
            p[lib.partList[i].key] = (s.default_parts || []).indexOf(lib.partList[i].key) >= 0
        parts = p
        folder = s.folder || ""
        startFolder = folder
        open()
    }

    FolderDialog {
        id: _folderDlg
        title: "Choose the Library Folder"
        onAccepted: {
            var url = String(selectedFolder)
            _dlg.folder = decodeURIComponent(url.replace(/^file:\/{3}/, "")).replace(/\//g, "\\")
        }
    }

    ColumnLayout {
        width: parent.width
        spacing: Style.dp(8)

        RowLayout {
            spacing: Style.dp(10)
            Label { text: "Keep the newest"; color: Style.fg }
            SpinBox {
                id: _keep
                objectName: "librarySettingsKeep"
                from: 1
                to: 100
                editable: true
            }
            Label { text: "autosaves per stick"; color: Style.fg }
        }
        Label {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: "Setups you saved, renamed or described are never removed."
            font.pixelSize: Style.dp(12)
            color: Style.fgMuted
        }

        Label { text: "Copy and Swap tick by default"; font.bold: true; color: Style.fgStrong; Layout.topMargin: Style.dp(6) }
        Flow {
            Layout.fillWidth: true
            spacing: Style.dp(12)
            Repeater {
                model: _dlg.lib ? _dlg.lib.partList : []
                delegate: CheckBox {
                    required property var modelData
                    objectName: "librarySettingsPart_" + modelData.key
                    text: modelData.label
                    checked: _dlg.parts[modelData.key] === true
                    onToggled: {
                        var p = Object.assign({}, _dlg.parts)
                        p[modelData.key] = checked
                        _dlg.parts = p
                    }
                }
            }
        }

        Label { text: "Library folder"; font.bold: true; color: Style.fgStrong; Layout.topMargin: Style.dp(6) }
        RowLayout {
            Layout.fillWidth: true
            TextField {
                objectName: "librarySettingsFolder"
                Layout.fillWidth: true
                readOnly: true
                text: _dlg.folder
            }
            Button {
                text: "Move…"
                onClicked: _folderDlg.open()
            }
        }
        Label {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            visible: _dlg.folder !== _dlg.startFolder
            text: "The Library moves to this folder when you press OK."
            font.pixelSize: Style.dp(12)
            color: Style.fgMuted
        }
    }

    footer: DialogButtonBox {
        Button { text: "OK"; enabled: _dlg.lib && !_dlg.lib.busy; DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole }
        Button { text: "Cancel"; DialogButtonBox.buttonRole: DialogButtonBox.RejectRole }
    }
    onAccepted: {
        var chosen = []
        for (var i = 0; i < lib.partList.length; i++)
            if (parts[lib.partList[i].key])
                chosen.push(lib.partList[i].key)
        var values = { keep: _keep.value, default_parts: chosen }
        if (folder !== startFolder)
            values.folder = folder
        lib.setSettings(values)
    }
}
