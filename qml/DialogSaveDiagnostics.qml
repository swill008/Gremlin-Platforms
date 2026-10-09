// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Style
import Gremlin.UI

// Help → Save Diagnostics… and the Live Log Reader's Debug tab (01 S132):
// one zip with the logs, the settings, the device list and the versions,
// and the open profile only when the box is ticked. Written in the
// background (gremlin/ui/diagnostics.py); the result shows here.
ApplicationWindow {
    id: _win

    EscapeCloses { host: _win }
    font.pixelSize: Style.fontSize
    width: Style.fitWidth(Style.dp(560), Screen)
    height: Style.fitHeight(Style.dp(340), Screen)
    minimumWidth: Style.fitWidth(Style.dp(420), Screen)
    minimumHeight: Style.fitHeight(Style.dp(280), Screen)
    color: Style.background
    U.Universal.theme: Style.theme
    title: qsTr("Save Diagnostics")

    property bool _failed: false

    // Starts writing the zip at url (the Save dialog's choice).
    function saveTo(url) {
        _failed = false
        return _diag.saveAsync(String(url), _includeProfile.checked)
    }

    Diagnostics {
        id: _diag
        onSaved: (ok, message) => { _win._failed = !ok }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Style.dp(16)
        spacing: Style.dp(10)

        Label {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            text: "Saves one zip to send with a problem report: the program's logs, "
                + "its settings, the device list (names, ids, kinds, connected) and "
                + "the program and Windows versions. Your user name in folder paths "
                + "is replaced by <user>."
            textFormat: Text.PlainText
        }

        CheckBox {
            id: _includeProfile
            text: "Include the open profile"
            checked: false
            ToolTip.visible: hovered
            ToolTip.text: "Add the open profile as it is now, unsaved changes included"
        }

        RowLayout {
            spacing: Style.dp(8)
            Button {
                text: qsTr("Save…")
                enabled: !_diag.busy
                onClicked: {
                    _saveDialog.currentFile = _diag.defaultFileUrl()
                    _saveDialog.open()
                }
            }
            BusyIndicator {
                visible: _diag.busy
                running: _diag.busy
                Layout.preferredWidth: Style.dp(28)
                Layout.preferredHeight: Style.dp(28)
            }
            Label {
                visible: _diag.busy
                text: "Saving…"
                color: Style.fgMuted
            }
        }

        Label {
            id: _result
            Layout.fillWidth: true
            wrapMode: Text.WrapAnywhere
            textFormat: Text.PlainText
            text: _diag.busy ? "" : _diag.message
            color: _win._failed ? Style.dangerText : Style.fg
        }

        Item { Layout.fillHeight: true }

        RowLayout {
            Layout.alignment: Qt.AlignRight
            Button {
                text: qsTr("Close")
                onClicked: _win.close()
            }
        }
    }

    // Opens in the last folder diagnostics were saved to, else the
    // Desktop (01 S132, S143).
    FilePicker {
        id: _saveDialog
        kind: "diagnostics"
        mode: "save"
        title: "Save Diagnostics"
        folder: _diag.desktopUrl
        defaultSuffix: "zip"
        nameFilters: ["Zip files (*.zip)"]
        onPicked: (selected) => _win.saveTo(selected)
    }
}
