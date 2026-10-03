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

ApplicationWindow {
    font.pixelSize: Style.fontSize
    id: _win
    width: 720
    height: 640
    minimumWidth: Style.dp(640)
    minimumHeight: Style.dp(480)
    title: "HidHide"
    color: Style.background
    U.Universal.theme: Style.theme

    HidHideModel {
        id: _hh
    }

    Timer {
        id: _sizeSave
        interval: 400
        repeat: false
        onTriggered: _hh.saveWindowSize(_win.width, _win.height)
    }

    Component.onCompleted: {
        // The saved size, never below this window's own minimum (the one
        // limit that counts; the stored value only guards against nonsense).
        width = Math.max(_hh.windowWidth, minimumWidth)
        height = Math.max(_hh.windowHeight, minimumHeight)
    }
    onWidthChanged: if (visible) _sizeSave.restart()
    onHeightChanged: if (visible) _sizeSave.restart()
    onClosing: {
        _hh.saveWindowSize(width, height)
        _split.saveRatio()
    }

    function titleOf(row) {
        var n = (row && row.name) ? String(row.name) : ""
        var u = n.toUpperCase()
        if (!n || u.indexOf("HID\\") === 0 || u.indexOf("USB\\") === 0)
            return "HID-compliant game controller"
        return n
    }

    FileDialog {
        id: _pickPhoto
        title: "Device image"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Images (*.png *.jpg *.jpeg *.bmp *.webp)", "All files (*)"]
        property string targetId: ""
        onAccepted: {
            if (targetId)
                _hh.setDevicePhoto(targetId, selectedFile.toString())
        }
    }

    FileDialog {
        id: _pickExe
        title: "Add a game or program"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Programs (*.exe)", "All files (*)"]
        onAccepted: {
            var url = selectedFile
            var path = url.toString()
            if (path.startsWith("file:///"))
                path = path.substring(8)
            path = path.replace(/\//g, "\\")
            _hh.addGame("", path)
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Style.dp(16)
        spacing: Style.dp(10)

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: driverRow.implicitHeight + Style.dp(20)
            radius: Style.dp(3)
            color: Style.bgPage
            border.color: Style.line

            RowLayout {
                id: driverRow
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.margins: Style.dp(10)
                spacing: Style.dp(10)
                Rectangle {
                    width: Style.dp(8)
                    height: Style.dp(8)
                    radius: Style.dp(4)
                    Layout.alignment: Qt.AlignVCenter
                    color: _hh.installed ? Style.ok : Style.fgMuted
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 0
                    Label {
                        color: Style.fg
                        text: _hh.installed ? "HidHide driver found" : "HidHide is not installed"
                    }
                    Label {
                        visible: _hh.driverVersion.length > 0
                        color: Style.fgMuted
                        font.pixelSize: Style.dp(11)
                        text: _hh.driverVersion
                    }
                }
                RowLayout {
                    spacing: Style.dp(4)
                    Button {
                        text: "Get HidHide"
                        onClicked: _hh.openDownload()
                    }
                    Button {
                        text: "Test HidHide"
                        onClicked: _hh.openGameControllers()
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: optionRow.implicitHeight + Style.dp(20)
            radius: Style.dp(3)
            color: Style.bgPage
            border.color: Style.line

            RowLayout {
                id: optionRow
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.margins: Style.dp(10)
                spacing: Style.dp(10)
                Switch {
                    id: controlSwitch
                    enabled: _hh.installed
                    property bool shown: _hh.gremlinControl
                    onShownChanged: if (!pressed) checked = shown
                    Component.onCompleted: checked = shown
                    text: "Gremlin-Platforms controls HidHide"
                    onClicked: _hh.setGremlinControl(checked)
                }
                Switch {
                    id: cloakSwitch
                    enabled: _hh.installed && _hh.gremlinControl
                    property bool shown: _hh.cloakOn
                    onShownChanged: if (!pressed) checked = shown
                    Component.onCompleted: checked = shown
                    text: "HidHide Enabled"
                    // A refused change puts the switch back (shown may not change).
                    onClicked: if (!_hh.setCloak(checked)) checked = shown
                }
                Switch {
                    id: startSwitch
                    enabled: _hh.installed
                    property bool shown: _hh.startOn
                    onShownChanged: if (!pressed) checked = shown
                    Component.onCompleted: checked = shown
                    text: "Automatically Start"
                    onClicked: _hh.setStartOn(checked)
                }
                Item { Layout.fillWidth: true }
            }
        }

        Label {
            text: "HidHide"
            color: Style.fg
            font.pixelSize: Style.dp(16)
            font.bold: true
        }

        Label {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Style.fgMuted
            font.pixelSize: Style.dp(12)
            text: "HidHide Enabled means HidHide enforces the device list and the program list. Off means HidHide is installed but HidHide is not hiding anything. Automatically Start turns on both this control and HidHide Enabled each time this program starts. This program does not install HidHide. Click on Get HidHide to download the program."
        }

        // Why the switches and lists are greyed out, and what turns them on.
        Label {
            visible: _hh.installed && !_hh.gremlinControl
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Style.warn
            font.pixelSize: Style.dp(12)
            text: "Turn on 'Gremlin-Platforms controls HidHide' (above) to change HidHide from here. Until then the settings below are shown but can't be changed."
        }

        Label {
            visible: !_hh.installed
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
            color: Style.fgMuted
            font.pixelSize: Style.dp(12)
            text: "Install HidHide from the Nefarius releases page, then open this window again. This program does not download or bundle that installer."
        }

        Switch {
            id: _gamingOnly
            property bool shown: _hh.gamingOnly
            onShownChanged: if (!pressed) checked = shown
            Component.onCompleted: checked = shown
            text: "Gaming devices only"
            onClicked: _hh.setGamingOnly(checked)
        }

        SplitView {
            id: _split
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Vertical

            // Same pattern as the Home page split: the saved share (thousandths) sets
            // the device list height; only a finished drag or closing saves it.
            property bool applying: false

            function applyRatio() {
                if (height < 80)
                    return
                applying = true
                _devicesPane.SplitView.preferredHeight = Math.round(height * _hh.splitRatio / 1000)
                applying = false
            }

            function saveRatio() {
                if (applying || height < 80 || _devicesPane.height < 96)
                    return
                _hh.saveSplitRatio(Math.round(_devicesPane.height * 1000 / height))
            }

            onHeightChanged: if (visible) applyRatio()
            Component.onCompleted: Qt.callLater(applyRatio)
            onResizingChanged: if (!resizing && visible) saveRatio()
            handle: Rectangle {
                implicitWidth: Style.dp(8)
                implicitHeight: Style.dp(10)
                color: SplitHandle.pressed ? Style.line : (SplitHandle.hovered ? Style.bgRaised : Style.bgCard)
                Rectangle {
                    anchors.centerIn: parent
                    width: Style.dp(36)
                    height: Style.dp(3)
                    radius: Style.dp(1)
                    color: Style.fgDisabled
                }
            }

            ColumnLayout {
                id: _devicesPane
                SplitView.fillWidth: true
                SplitView.minimumHeight: Style.dp(96)
                spacing: Style.dp(6)

                Label {
                    text: "DEVICES"
                    color: Style.fgMuted
                    font.pixelSize: Style.dp(11)
                    font.capitalization: Font.AllUppercase
                }

                Label {
                    visible: _hh.lastError.length > 0
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                    color: Style.dangerTextSoft
                    font.pixelSize: Style.dp(12)
                    text: _hh.lastError
                }

                Label {
                    visible: _hh.deviceCount === 0
                    text: _hh.installed ? "No HID devices reported." : "Device list needs the HidHide driver."
                    color: Style.fgMuted
                }

                ListView {
                    id: _devs
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: Style.dp(48)
                    clip: true
                    spacing: Style.dp(6)
                    boundsBehavior: Flickable.StopAtBounds
                    model: _hh.deviceCount
                    ScrollBar.vertical: ScrollBar {
                        policy: ScrollBar.AlwaysOn
                        width: Style.dp(10)
                        contentItem: Rectangle {
                            implicitWidth: Style.dp(8)
                            radius: Style.dp(3)
                            color: parent.pressed ? Style.fg : (parent.hovered ? Style.fgMuted : Style.lineStrong)
                        }
                    }
                    delegate: Rectangle {
                        required property int index
                        width: ListView.view.width - Style.dp(12)
                        height: Style.dp(56)
                        radius: Style.dp(3)
                        color: Style.bgPage
                        border.color: Style.line
                        property int _gen: _hh.generation
                        property var row: _gen >= 0 ? _hh.deviceAt(index) : ({})
                        property bool confirmed: !!(row && row.confirmed)
                        clip: true
                        RowLayout {
                            z: 1
                            anchors.fill: parent
                            anchors.margins: Style.dp(8)
                            spacing: Style.dp(8)
                            opacity: confirmed ? 0.55 : 1
                            Rectangle {
                                width: Style.dp(40)
                                height: Style.dp(40)
                                radius: Style.dp(3)
                                color: Style.bgWell
                                border.color: Style.line
                                Image {
                                    anchors.fill: parent
                                    anchors.margins: Style.dp(2)
                                    source: row.photo || ""
                                    fillMode: Image.PreserveAspectFit
                                    visible: !!(row.photo)
                                    asynchronous: true
                                    cache: true
                                    sourceSize.width: Style.dp(80)
                                    sourceSize.height: Style.dp(80)
                                }
                            }
                            ColumnLayout {
                                spacing: 0
                                Layout.fillWidth: true
                                Label {
                                    text: titleOf(row)
                                    color: confirmed ? Style.fgMuted : Style.fg
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                                Label {
                                    text: {
                                        if (!row.canHide)
                                            return "Cannot hide (keyboard or mouse)"
                                        var bits = []
                                        if (row.openDenied)
                                            bits.push("Denied")
                                        if (confirmed)
                                            bits.push("Hidden")
                                        if (row.clientBlocked)
                                            bits.push("Client list")
                                        var prefix = bits.length ? bits.join(" · ") + "  " : ""
                                        return prefix + (row.instanceId || "")
                                    }
                                    color: confirmed ? Style.fgDisabled : Style.fgMuted
                                    font.pixelSize: Style.dp(11)
                                    elide: Text.ElideMiddle
                                    Layout.fillWidth: true
                                }
                            }
                            Button {
                                text: row.photo ? "Change image" : "Add image"
                                onClicked: {
                                    _pickPhoto.targetId = row.instanceId
                                    _pickPhoto.open()
                                }
                            }
                            Switch {
                                id: hideSwitch
                                enabled: _hh.installed && _hh.gremlinControl && row.canHide
                                property bool shown: !!(row && row.session)
                                onShownChanged: if (!pressed) checked = shown
                                Component.onCompleted: checked = shown
                                onClicked: _hh.setDeviceHidden(row.instanceId, checked)
                            }
                        }
                        Text {
                            anchors.centerIn: parent
                            visible: confirmed
                            enabled: false
                            z: 2
                            text: "HIDDEN"
                            font.bold: true
                            font.pixelSize: Style.dp(22)
                            color: Style.fgStrong
                        }
                    }
                }
            }

            ColumnLayout {
                SplitView.fillWidth: true
                SplitView.fillHeight: true
                SplitView.minimumHeight: Style.dp(120)
                spacing: Style.dp(6)

                Label {
                    text: "Programs that have been added to the Mask"
                    color: Style.fg
                    font.pixelSize: Style.dp(16)
                    font.bold: true
                }

                Button {
                    text: "Add Program"
                    enabled: _hh.installed
                    onClicked: _pickExe.open()
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Style.dp(16)
                    RadioButton {
                        id: allowList
                        autoExclusive: false
                        checkable: false
                        text: "Allow list"
                        enabled: _hh.installed && _hh.gremlinControl
                        property bool shown: !_hh.inverseOn
                        onShownChanged: if (!pressed) checked = shown
                        Component.onCompleted: checked = shown
                        onClicked: _hh.setInverse(false)
                    }
                    RadioButton {
                        id: blockList
                        autoExclusive: false
                        checkable: false
                        text: "Block list"
                        enabled: _hh.installed && _hh.gremlinControl
                        property bool shown: _hh.inverseOn
                        onShownChanged: if (!pressed) checked = shown
                        Component.onCompleted: checked = shown
                        onClicked: _hh.setInverse(true)
                    }
                }

                Label {
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                    color: Style.fgMuted
                    font.pixelSize: Style.dp(12)
                    text: "Allow list: only these programs can see the hidden controllers. Block list: these programs cannot see them. Gremlin-Platforms is allowed in both modes."
                }

                ListView {
                    id: _games
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: Style.dp(48)
                    clip: true
                    spacing: Style.dp(6)
                    boundsBehavior: Flickable.StopAtBounds
                    model: _hh.gameCount
                    ScrollBar.vertical: ScrollBar {
                        policy: ScrollBar.AlwaysOn
                        width: Style.dp(10)
                        contentItem: Rectangle {
                            implicitWidth: Style.dp(8)
                            radius: Style.dp(3)
                            color: parent.pressed ? Style.fg : (parent.hovered ? Style.fgMuted : Style.lineStrong)
                        }
                    }
                    delegate: Rectangle {
                        required property int index
                        width: ListView.view.width - Style.dp(12)
                        height: Style.dp(44)
                        radius: Style.dp(3)
                        color: Style.bgPage
                        border.color: Style.line
                        property var row: _hh.gameAt(index)
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: Style.dp(8)
                            ColumnLayout {
                                spacing: 0
                                Layout.fillWidth: true
                                Label {
                                    text: row.name
                                    color: Style.fg
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                                Label {
                                    text: row.path
                                    color: Style.fgMuted
                                    font.pixelSize: Style.dp(11)
                                    elide: Text.ElideMiddle
                                    Layout.fillWidth: true
                                }
                            }
                            Button {
                                text: "Remove"
                                onClicked: _hh.removeGame(row.path)
                            }
                        }
                    }
                }

                Label {
                    visible: _hh.gameCount === 0
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                    color: Style.fgMuted
                    font.pixelSize: Style.dp(12)
                    text: _hh.inverseOn
                          ? "Add a program here to block it from the hidden controllers."
                          : "Add a program here to let it see the hidden controllers. Gremlin-Platforms can still see them."
                }
            }
        }
    }
}
