// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts

import Gremlin.Device
import Gremlin.Style

ColumnLayout {
    id: _root

    property string deviceGuid: ""
    property string title: ""
    property string pairLabel: ""
    property int axisStamp: _live && _live.axisStamp !== undefined ? _live.axisStamp : 0
    property int buttonStamp: _live && _live.buttonStamp !== undefined ? _live.buttonStamp : 0
    property int xboxStamp: _live && _live.xboxStamp !== undefined ? _live.xboxStamp : 0
    property bool pairActive: backend && backend.gremlinActive

    spacing: Style.dp(4)

    XboxMappedAxisModel { id: _axes; guid: deviceGuid }
    XboxMappedButtonModel { id: _buttons; guid: deviceGuid }
    XboxMappedHatModel { id: _hats; guid: deviceGuid }
    XboxPadListModel { id: _xboxPads; guid: deviceGuid }
    XboxLiveThrottle { id: _live; guid: deviceGuid }

    function hwAxis(id) {
        if (!_live) return 0
        return axisStamp >= 0 ? _live.axisValue(id) : 0
    }
    function hwButton(id) {
        if (!_live) return 0
        return buttonStamp >= 0 ? _live.buttonValue(id) : 0
    }
    function xb(pad, target) {
        if (!_live) return 0
        return xboxStamp >= 0 ? _live.xboxValue(pad, target) : 0
    }
    function destAxis(pad, target) {
        var value = xb(pad, target)
        if (String(target).indexOf("trigger") >= 0)
            return value * 2.0 - 1.0
        return value
    }

    Rectangle {
        Layout.fillWidth: true
        implicitHeight: _inner.implicitHeight + Style.dp(16)
        color: pairActive ? Style.okFillDeep : Style.background
        border.color: pairActive ? Style.ok : Style.accent
        border.width: pairActive ? Style.dp(2) : Style.dp(1)
        radius: Style.dp(6)
        clip: false

        ColumnLayout {
            id: _inner
            width: parent.width - Style.dp(16)
            x: Style.dp(8)
            y: Style.dp(8)
            spacing: Style.dp(6)

            RowLayout {
                Layout.fillWidth: true
                JGText { text: title; font.pixelSize: Style.dp(16)}
                Rectangle {
                    visible: pairActive
                    width: Style.dp(8); height: Style.dp(8); radius: Style.dp(4); color: Style.ok
                }
                JGText {
                    visible: pairActive
                    text: "Running"
                    color: Style.ok
                    font.pixelSize: Style.dp(13)
                }
                Item { Layout.fillWidth: true }
                JGText {
                    visible: pairLabel.length > 0
                    text: "\u2192  " + pairLabel
                    color: pairActive ? Style.okText : Style.accent
                }
            }

            JGText {
                visible: !pairActive && _xboxPads.count > 0
                text: "Run the profile to plug in the virtual pad and light this face."
                color: Style.alert
                font.pixelSize: Style.dp(13)
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Item {
                visible: _xboxPads.count > 0
                Layout.fillWidth: true
                Layout.preferredHeight: Style.dp(410)
                Column {
                    id: _faces
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: Style.dp(8)
                    Repeater {
                        model: _xboxPads
                        delegate: Xbox360Face {
                            required property int padId
                            live: _live
                            stamp: xboxStamp
                        }
                    }
                }
            }

            JGText { text: "Mapped axes"; opacity: 0.7; font.pixelSize: Style.dp(13)}

            Repeater {
                model: _axes
                delegate: RowLayout {
                    required property int identifier
                    required property string label
                    required property int xboxPad
                    required property string xboxTarget
                    required property string xboxLabel
                    Layout.fillWidth: true
                    spacing: Style.dp(8)
                    Label { text: label; color: Style.foreground; Layout.preferredWidth: Style.dp(28); font.pixelSize: Style.dp(13)}
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Style.dp(4)
                        radius: Style.dp(2)
                        color: Style.lowColor
                        Rectangle {
                            height: parent.height
                            radius: Style.dp(2)
                            width: parent.width * Math.min(1.0, Math.max(0.0, (hwAxis(identifier) + 1.0) * 0.5))
                            color: Style.ok
                        }
                    }
                    Label {
                        text: xboxLabel
                        color: Style.okText
                        Layout.preferredWidth: Style.dp(110)
                        font.pixelSize: Style.dp(12)
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Style.dp(4)
                        radius: Style.dp(2)
                        color: Style.lowColor
                        Rectangle {
                            height: parent.height
                            radius: Style.dp(2)
                            width: parent.width * Math.min(1.0, Math.max(0.0, (destAxis(xboxPad, xboxTarget) + 1.0) * 0.5))
                            color: Style.ok
                        }
                    }
                }
            }

            JGText { text: "Mapped buttons"; opacity: 0.7; font.pixelSize: Style.dp(13)}

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: _btnFlow.implicitHeight + Style.dp(16)
                color: "transparent"
                border.color: Style.medColor
                border.width: Style.dp(1)
                radius: Style.dp(6)
                Flow {
                    id: _btnFlow
                    width: parent.width - Style.dp(16)
                    x: Style.dp(8); y: Style.dp(8); spacing: Style.dp(10)
                    Repeater {
                        model: _buttons
                        delegate: Rectangle {
                            required property int identifier
                            required property string label
                            required property int xboxPad
                            required property string xboxTarget
                            required property string xboxLabel
                            required property string xboxChip
                            property bool hwOn: buttonStamp >= 0 && hwButton(identifier) > 0.5
                            property bool xbOn: xboxStamp >= 0 && xb(xboxPad, xboxTarget) > 0.5
                            width: Style.dp(48); height: Style.dp(18); radius: Style.dp(3)
                            color: Style.background
                            border.color: (hwOn || xbOn) ? Style.ok : Style.medColor
                            border.width: Style.dp(1)
                            clip: true
                            Row {
                                anchors.fill: parent
                                Rectangle {
                                    width: parent.width / 2; height: parent.height
                                    color: hwOn ? Style.ok : "transparent"
                                    Label {
                                        anchors.centerIn: parent
                                        text: label
                                        color: hwOn ? Style.okFillDeep : Style.foreground
                                        font.pixelSize: Style.dp(11)
                                    }
                                    HoverHandler { id: _hwHover }
                                    PointerTip {
                                        text: "Hardware " + label
                                        delay: 200
                                        show: true
                                    }
                                }
                                Rectangle { width: Style.dp(1); height: parent.height; color: Style.medColor }
                                Rectangle {
                                    width: parent.width / 2 - Style.dp(1); height: parent.height
                                    color: xbOn ? Style.ok : "transparent"
                                    Label {
                                        anchors.centerIn: parent
                                        text: xboxChip
                                        color: xbOn ? Style.okFillDeep : Style.foreground
                                        font.pixelSize: Style.dp(11)
                                    }
                                    HoverHandler { id: _xbHover }
                                    PointerTip {
                                        text: xboxLabel
                                        delay: 200
                                        show: true
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Repeater {
                model: _hats
                delegate: RowLayout {
                    required property string label
                    required property string xboxLabel
                    Layout.fillWidth: true
                    JGText {
                        text: label + "  \u2192  " + xboxLabel
                        font.pixelSize: Style.dp(13)
                    }
                }
            }
        }
    }
}
