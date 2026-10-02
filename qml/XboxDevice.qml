// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts

import Gremlin.Device
import Gremlin.Style

Item {
    id: _root

    XboxDeviceModel {
        id: _model
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Style.dp(10)
        spacing: Style.dp(8)

        RowLayout {
            Layout.fillWidth: true
            spacing: Style.dp(8)

            Label {
                text: _model ? _model.moduleName : "Xbox 360 Controller"
                font.bold: true
                font.pixelSize: Style.dp(16)
            }

            Label {
                text: "Pad " + (_model ? _model.padId : 1)
                opacity: 0.7
            }

            Item { Layout.fillWidth: true }
        }

        Label {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            text: _model ? _model.statusText : ""
            color: (_model && _model.available) ? Style.foreground : Style.alert
            opacity: 0.9
        }

        Label {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            text: "This is the Xbox output module for the pad. Only claimed controls reach the Xbox driver, and only they can be picked in Map to Xbox. Rows show who already targets each control."
            opacity: 0.7
            font.pixelSize: Style.dp(12)
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Style.dp(8)
            visible: _model && _model.hasModule

            Label {
                text: _model ? ("Claimed " + _model.claimedCount + " of " + _list.count) : ""
            }

            Item { Layout.fillWidth: true }

            Button {
                text: "Claim all"
                onClicked: _model.setAllClaimed(true)
            }

            Button {
                text: "Clear all"
                onClicked: _model.setAllClaimed(false)
            }
        }

        Label {
            Layout.fillWidth: true
            visible: _model && !_model.hasModule
            wrapMode: Text.WordWrap
            text: "There is no Xbox output module (\"Xbox 360 Controller\"), so nothing is sent to the Xbox pad."
            color: Style.alert
        }

        JGListView {
            id: _list
            Layout.fillWidth: true
            Layout.fillHeight: true
            scrollbarAlwaysVisible: true
            spacing: Style.dp(4)
            model: _model

            delegate: Rectangle {
                required property string label
                required property string kind
                required property string incoming
                required property string target
                required property bool claimed
                required property int index

                width: _list.width - Style.dp(16)
                implicitHeight: _row.implicitHeight + Style.dp(12)
                radius: Style.dp(4)
                color: Style.background
                border.color: incoming.length ? Style.accent : Style.lowColor
                border.width: Style.dp(1)
                opacity: claimed ? 1.0 : 0.6

                ColumnLayout {
                    id: _row
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.margins: Style.dp(8)
                    spacing: Style.dp(2)

                    RowLayout {
                        Layout.fillWidth: true

                        Label {
                            text: label
                            font.bold: true
                            font.pixelSize: Style.dp(13)
                        }

                        Item { Layout.fillWidth: true }

                        Label {
                            text: kind
                            opacity: 0.55
                            font.pixelSize: Style.dp(11)
                        }

                        CheckBox {
                            text: "Claimed"
                            enabled: _model && _model.hasModule
                            checked: claimed
                            onToggled: _model.setClaimed(target, checked)
                        }
                    }

                    Label {
                        visible: incoming.length > 0 && !claimed
                        text: "Not claimed: these wires send nothing"
                        color: Style.alert
                        font.pixelSize: Style.dp(11)
                    }

                    Label {
                        visible: incoming.length > 0
                        text: incoming
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        color: Style.accent
                        font.pixelSize: Style.dp(11)
                    }

                    Label {
                        visible: incoming.length === 0
                        text: "Unmapped"
                        opacity: 0.45
                        font.pixelSize: Style.dp(11)
                    }
                }
            }
        }
    }
}
