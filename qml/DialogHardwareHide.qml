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
    title: "HiDHide"
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

    Timer {
        id: _splitSave
        interval: 400
        repeat: false
        onTriggered: _split.saveRatio()
    }

    Component.onCompleted: {
        var w = _hh.windowWidth
        var h = _hh.windowHeight
        width = w >= 640 ? w : Style.dp(720)
        height = h >= 480 ? h : Style.dp(640)
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
            color: "#111113"
            border.color: "#3F3F46"

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
                    color: _hh.installed ? "#22C55E" : "#A1A1AA"
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 0
                    Label {
                        color: "#E4E4E7"
                        text: _hh.installed ? "HiDHide driver found" : "HiDHide is not installed"
                    }
                    Label {
                        visible: _hh.driverVersion.length > 0
                        color: "#A1A1AA"
                        font.pixelSize: Style.dp(11)
                        text: _hh.driverVersion
                    }
                }
                RowLayout {
                    spacing: Style.dp(4)
                    Button {
                        text: "Get HiDHide"
                        onClicked: _hh.openDownload()
                    }
                    Button {
                        text: "Test HiDHide"
                        onClicked: _hh.openGameControllers()
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: optionRow.implicitHeight + Style.dp(20)
            radius: Style.dp(3)
            color: "#111113"
            border.color: "#3F3F46"

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
                    text: "Gremlin control"
                    onClicked: _hh.setGremlinControl(checked)
                }
                Switch {
                    id: cloakSwitch
                    enabled: _hh.installed && _hh.gremlinControl
                    property bool shown: _hh.cloakOn
                    onShownChanged: if (!pressed) checked = shown
                    Component.onCompleted: checked = shown
                    text: "HiDHide Enabled"
                    onClicked: _hh.setCloak(checked)
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
            text: "HiDHide"
            color: "#E4E4E7"
            font.pixelSize: Style.dp(16)
            font.bold: true
        }

        Label {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: "#A1A1AA"
            font.pixelSize: Style.dp(12)
            text: "HiDHide Enabled means HiDHide enforces the device list and the program list. Off means HiDHide is installed but HiDHide is not hiding anything. Automatically Start turns Gremlin control and HiDHide Enabled on each time this program starts. This program does not install HiDHide. Click on Get HiDHide to download the program."
        }

        Label {
            visible: !_hh.installed
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
            color: "#A1A1AA"
            font.pixelSize: Style.dp(12)
            text: "Install HiDHide from the Nefarius releases page, then open this window again. Gremlin will not download or bundle that installer."
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
            function saveRatio() {
                if (height < 80 || _devicesPane.height < 96)
                    return
                _hh.saveSplitRatio(Math.round(_devicesPane.height * 1000 / height))
            }
            handle: Rectangle {
                implicitWidth: Style.dp(8)
                implicitHeight: Style.dp(10)
                color: SplitHandle.pressed ? "#3F3F46" : (SplitHandle.hovered ? "#27272A" : "#18181B")
                Rectangle {
                    anchors.centerIn: parent
                    width: Style.dp(36)
                    height: Style.dp(3)
                    radius: Style.dp(1)
                    color: "#71717A"
                }
            }

            ColumnLayout {
                id: _devicesPane
                SplitView.fillWidth: true
                SplitView.fillHeight: true
                SplitView.preferredHeight: Math.max(Style.dp(96), _hh.splitRatio)
                SplitView.minimumHeight: Style.dp(96)
                spacing: Style.dp(6)
                onHeightChanged: if (_win.visible) _splitSave.restart()

                Label {
                    text: "DEVICES"
                    color: "#A1A1AA"
                    font.pixelSize: Style.dp(11)
                    font.capitalization: Font.AllUppercase
                }

                Label {
                    visible: _hh.lastError.length > 0
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                    color: "#FCA5A5"
                    font.pixelSize: Style.dp(12)
                    text: _hh.lastError
                }

                Label {
                    visible: _hh.deviceCount === 0
                    text: _hh.installed ? "No HID devices reported." : "Device list needs the HiDHide driver."
                    color: "#A1A1AA"
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
                            color: parent.pressed ? "#E4E4E7" : (parent.hovered ? "#A1A1AA" : "#52525B")
                        }
                    }
                    delegate: Rectangle {
                        required property int index
                        width: ListView.view.width - Style.dp(12)
                        height: Style.dp(56)
                        radius: Style.dp(3)
                        color: "#111113"
                        border.color: "#3F3F46"
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
                                color: "#09090B"
                                border.color: "#3F3F46"
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
                                    color: confirmed ? "#A1A1AA" : "#E4E4E7"
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
                                    color: confirmed ? "#71717A" : "#A1A1AA"
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
                            color: "#F4F4F5"
                        }
                    }
                }
            }

            ColumnLayout {
                SplitView.fillWidth: true
                SplitView.fillHeight: true
                SplitView.preferredHeight: Math.max(Style.dp(120), 1000 - _hh.splitRatio)
                SplitView.minimumHeight: Style.dp(120)
                spacing: Style.dp(6)

                Label {
                    text: "Programs that have been added to the Mask"
                    color: "#E4E4E7"
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
                    color: "#A1A1AA"
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
                            color: parent.pressed ? "#E4E4E7" : (parent.hovered ? "#A1A1AA" : "#52525B")
                        }
                    }
                    delegate: Rectangle {
                        required property int index
                        width: ListView.view.width - Style.dp(12)
                        height: Style.dp(44)
                        radius: Style.dp(3)
                        color: "#111113"
                        border.color: "#3F3F46"
                        property var row: _hh.gameAt(index)
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: Style.dp(8)
                            ColumnLayout {
                                spacing: 0
                                Layout.fillWidth: true
                                Label {
                                    text: row.name
                                    color: "#E4E4E7"
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                                Label {
                                    text: row.path
                                    color: "#A1A1AA"
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
                    color: "#A1A1AA"
                    font.pixelSize: Style.dp(12)
                    text: _hh.inverseOn
                          ? "Add a program here to block it from the hidden controllers."
                          : "Add a program here to let it see the hidden controllers. Gremlin-Platforms can still see them."
                }
            }
        }
    }
}
