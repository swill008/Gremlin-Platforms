// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Style

// Reset Devices (D-02-RESET-DEVICES): restarts the ticked USB game
// controllers so every program opens them again and HidHide checks them.
// The hidden ones are ticked each time it opens (Xbox pads never are);
// vJoy and Gremlin's Xbox pad are never listed. While open, the list
// follows plug/unplug. Opened from the HidHide page.
ApplicationWindow {
    id: _win
    objectName: "resetDevicesWindow"
    font.pixelSize: Style.fontSize
    title: "Reset Devices"
    color: Style.background
    U.Universal.theme: Style.theme
    modality: Qt.WindowModal
    visible: false
    width: Style.fitWidth(Style.dp(880), Screen)
    height: Style.fitHeight(Style.dp(480), Screen)
    minimumWidth: Style.fitWidth(Style.dp(560), Screen)
    minimumHeight: Style.fitHeight(Style.dp(320), Screen)

    property alias model: _m

    ResetDevicesModel {
        id: _m
    }

    // context: HidHideModel.resetContext().
    function openWith(context) {
        _m.load(context)
        show()
        raise()
        requestActivate()
    }

    // Stop following device changes once the window is closed.
    onVisibleChanged: if (!visible) _m.detach()

    EscapeCloses { host: _win }

    function resultColor(kind) {
        return kind === "ok" ? Style.okText
             : kind === "warn" ? Style.warn
             : kind === "bad" ? Style.dangerTextSoft
             : Style.fgMuted
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Style.dp(16)
        spacing: Style.dp(12)

        // The warning, a running listed game, and the permission line.
        Rectangle {
            Layout.fillWidth: true
            visible: !_m.done
            implicitHeight: _warnCol.implicitHeight + Style.dp(20)
            radius: Style.dp(6)
            color: Style.alpha(Style.warn, 0.14)
            border.color: Style.warn

            ColumnLayout {
                id: _warnCol
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.margins: Style.dp(12)
                spacing: Style.dp(4)

                Label {
                    objectName: "resetDevicesWarning"
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    color: Style.fgStrong
                    textFormat: Text.PlainText
                    text: _m.warningText
                    leftPadding: Style.dp(18)
                    Label {
                        color: Style.warn
                        font.bold: true
                        text: "⚠"
                    }
                }
                Repeater {
                    model: _m.gameLines
                    delegate: Label {
                        required property string modelData
                        objectName: "resetDevicesGame"
                        Layout.fillWidth: true
                        leftPadding: Style.dp(18)
                        wrapMode: Text.WordWrap
                        color: Style.warn
                        font.pixelSize: Style.dp(13)
                        text: modelData
                    }
                }
                Label {
                    objectName: "resetDevicesPermission"
                    Layout.fillWidth: true
                    leftPadding: Style.dp(18)
                    wrapMode: Text.WordWrap
                    color: Style.warn
                    font.pixelSize: Style.dp(13)
                    text: _m.permissionText
                }
            }
        }

        // The devices: header and one row each.
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: Style.dp(6)
            color: Style.bgCard
            border.color: Style.line
            clip: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 1
                spacing: 0

                RowLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: Style.dp(12)
                    Layout.rightMargin: Style.dp(12)
                    Layout.topMargin: Style.dp(7)
                    Layout.bottomMargin: Style.dp(7)
                    spacing: Style.dp(10)
                    Item { Layout.preferredWidth: Style.dp(30) }
                    Repeater {
                        model: [["Device", 16], ["VID · PID", 8], ["USB device", 14], ["Result", 10]]
                        delegate: Label {
                            required property var modelData
                            Layout.fillWidth: true
                            Layout.preferredWidth: modelData[1]
                            text: modelData[0].toUpperCase()
                            color: Style.fgMuted
                            font.pixelSize: Style.dp(11)
                            font.letterSpacing: Style.dp(1)
                        }
                    }
                }
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 1
                    color: Style.line
                }

                ListView {
                    id: _rows
                    objectName: "resetDevicesList"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    model: _m.rowCount
                    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                    Label {
                        anchors.centerIn: parent
                        visible: _m.rowCount === 0
                        color: Style.fgMuted
                        text: "No USB game controllers are plugged in."
                    }

                    delegate: Rectangle {
                        required property int index
                        property int _gen: _m.generation
                        property var row: _gen >= 0 ? _m.rowAt(index) : ({})
                        width: ListView.view.width
                        implicitHeight: _rowLine.implicitHeight + Style.dp(16)
                        color: "transparent"

                        Rectangle {
                            anchors.bottom: parent.bottom
                            width: parent.width
                            height: 1
                            color: Style.line
                            opacity: 0.5
                        }

                        RowLayout {
                            id: _rowLine
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.leftMargin: Style.dp(12)
                            anchors.rightMargin: Style.dp(12)
                            spacing: Style.dp(10)

                            CheckBox {
                                objectName: "resetDevicesTick"
                                Layout.preferredWidth: Style.dp(30)
                                padding: 0
                                checked: !!row.ticked
                                enabled: !_m.running && !_m.done
                                onToggled: _m.setTicked(index, checked)
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                Layout.preferredWidth: 16
                                spacing: Style.dp(1)
                                Label {
                                    objectName: "resetDevicesName"
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                    font.bold: true
                                    color: Style.fgStrong
                                    text: row.name || row.windowsName || ""
                                }
                                Flow {
                                    Layout.fillWidth: true
                                    spacing: Style.dp(4)
                                    Label {
                                        visible: !!row.windowsName
                                                 && row.windowsName !== row.name
                                        color: Style.fgMuted
                                        font.pixelSize: Style.dp(12)
                                        text: row.windowsName || ""
                                    }
                                    Repeater {
                                        model: [[!!row.hidden, "hidden", Style.infoFill, Style.infoText],
                                                [!!row.inProfile, "in the profile", Style.okFill, Style.okText]]
                                        delegate: Rectangle {
                                            required property var modelData
                                            objectName: "resetDevicesTag"
                                            property string text: modelData[1]
                                            visible: modelData[0]
                                            radius: Style.dp(3)
                                            color: modelData[2]
                                            implicitWidth: _tag.implicitWidth + Style.dp(12)
                                            implicitHeight: _tag.implicitHeight + Style.dp(2)
                                            Label {
                                                id: _tag
                                                anchors.centerIn: parent
                                                font.pixelSize: Style.dp(11)
                                                font.bold: true
                                                color: modelData[3]
                                                text: modelData[1]
                                            }
                                        }
                                    }
                                }
                                Label {
                                    objectName: "resetDevicesNote"
                                    Layout.fillWidth: true
                                    visible: !!row.note
                                    wrapMode: Text.WordWrap
                                    color: Style.warn
                                    font.pixelSize: Style.dp(12)
                                    text: row.note || ""
                                }
                            }
                            Label {
                                Layout.fillWidth: true
                                Layout.preferredWidth: 8
                                font.family: Style.monoFont
                                font.pixelSize: Style.dp(12)
                                color: Style.fgMuted
                                text: row.vidPid || ""
                            }
                            Label {
                                objectName: "resetDevicesUsbId"
                                property string usbId: row.usbId || ""
                                Layout.fillWidth: true
                                Layout.preferredWidth: 14
                                elide: Text.ElideMiddle
                                font.family: Style.monoFont
                                font.pixelSize: Style.dp(12)
                                color: Style.fgMuted
                                text: usbId
                                ToolTip.visible: _usbHover.hovered
                                ToolTip.text: usbId
                                HoverHandler { id: _usbHover }
                            }
                            Label {
                                objectName: "resetDevicesResult"
                                Layout.fillWidth: true
                                Layout.preferredWidth: 10
                                wrapMode: Text.WordWrap
                                font.pixelSize: Style.dp(12)
                                color: _win.resultColor(row.resultKind || "")
                                text: row.result || "—"
                            }
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Style.dp(10)

            Label {
                objectName: "resetDevicesCount"
                visible: !_m.done
                color: Style.fgMuted
                text: _m.running ? "Resetting… Windows may ask for permission." : _m.summary
            }
            Label {
                visible: _m.done
                color: Style.fgMuted
                text: "Also in the program log and in Trace (HidHide row)."
            }
            Item { Layout.fillWidth: true }
            Button {
                objectName: "resetDevicesCancel"
                visible: !_m.done
                enabled: !_m.running
                text: "Cancel"
                onClicked: _win.close()
            }
            DangerButton {
                objectName: "resetDevicesReset"
                visible: !_m.done
                enabled: _m.tickedCount > 0 && !_m.running
                text: "Reset " + _m.tickedCount + (_m.tickedCount === 1 ? " Device" : " Devices")
                onClicked: _m.startReset()
            }
            Button {
                objectName: "resetDevicesClose"
                visible: _m.done
                text: "Close"
                onClicked: _win.close()
            }
        }
    }
}
