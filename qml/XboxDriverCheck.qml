// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Device
import Gremlin.Style

// The ViGEmBus check, like HidHide's: whether the Xbox driver is installed
// and running, its version, what to do when it isn't, Get and Test. On the
// Xbox Viewer and the Xbox output page.
Rectangle {
    objectName: "xboxDriverRow"

    // Asks again (installed, running, version).
    function reload() { _status.reload() }

    XboxDriverStatus { id: _status }

    implicitHeight: _driverRow.implicitHeight + Style.dp(20)
    radius: Style.dp(3)
    color: Style.bgPage
    border.color: Style.line

    RowLayout {
        id: _driverRow
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.margins: Style.dp(10)
        spacing: Style.dp(10)
        Rectangle {
            Layout.preferredWidth: Style.dp(8)
            Layout.preferredHeight: Style.dp(8)
            radius: Style.dp(4)
            Layout.alignment: Qt.AlignVCenter
            color: _status.ready ? Style.ok : (_status.installed ? Style.warn : Style.fgMuted)
        }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0
            Label {
                objectName: "xboxDriverStatus"
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: Style.fg
                text: _status.statusText
            }
            Label {
                visible: _status.driverVersion.length > 0
                color: Style.fgMuted
                font.pixelSize: Style.dp(11)
                text: _status.driverVersion
            }
            Label {
                visible: _status.hint.length > 0
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: Style.fgMuted
                font.pixelSize: Style.dp(12)
                text: _status.hint
            }
        }
        RowLayout {
            spacing: Style.dp(4)
            Button {
                text: "Get ViGEmBus"
                onClicked: _status.openDownload()
            }
            Button {
                text: "Test ViGEmBus"
                onClicked: _status.openGameControllers()
            }
        }
    }
}
