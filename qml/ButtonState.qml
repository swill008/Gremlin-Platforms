// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Style

Item {
    id: _root

    property string deviceGuid
    property string title

    implicitHeight: _content.implicitHeight

    function computeButtonHeight() {
        let columns = Math.floor(
            Math.max(_button_grid.width, _button_grid.Layout.minimumWidth) /
            _button_grid.cellWidth
        )
        if (columns < 1) {
            columns = 1
        }
        let rows = Math.ceil(_button_grid.count / columns)
        return rows * _button_grid.cellHeight
    }

    function computeHatHeight(cellHeight) {
        return Math.ceil(_hat_grid.count / 2) * cellHeight
    }

    DeviceButtonState {
        id: _button_state

        guid: deviceGuid
    }

    DeviceHatState {
        id: _hat_state

        guid: deviceGuid
    }

    ColumnLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right

        RowLayout {
            id: _header

            JGText {
                text: title + " - Buttons & Hats"
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignVCenter

                height: Style.dp(2)
                color: Style.lowColor
            }
        }

        RowLayout {
            GridView {
                id: _button_grid

                Layout.fillWidth: true
                Layout.minimumWidth: Style.dp(400)
                Layout.preferredWidth: Style.dp(600)
                Layout.minimumHeight: computeButtonHeight()
                Layout.alignment: Qt.AlignTop

                boundsMovement: Flickable.StopAtBounds
                boundsBehavior: Flickable.StopAtBounds
                interactive: false

                cellWidth: Style.dp(56)
                cellHeight: Style.dp(22)

                model: _button_state
                delegate: Item {
                    required property int identifier
                    required property bool value

                    width: _button_grid.cellWidth
                    height: _button_grid.cellHeight

                    Row {
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: Style.dp(6)

                        Rectangle {
                            width: Style.dp(12)
                            height: Style.dp(12)
                            radius: Style.dp(6)
                            anchors.verticalCenter: parent.verticalCenter

                            color: value ? Style.ok : Style.lowColor
                            border.width: Style.dp(1)
                            border.color: value ? Style.okStrong : Style.medColor
                        }

                        JGText {
                            anchors.verticalCenter: parent.verticalCenter
                            text: identifier
                            font.pixelSize: Style.dp(13)
                        }
                    }
                }
            }

            GridView {
                id: _hat_grid

                Layout.fillWidth: true
                Layout.minimumWidth: Style.dp(200)
                Layout.preferredWidth: Style.dp(200)
                Layout.minimumHeight: computeHatHeight(cellHeight)
                Layout.alignment: Qt.AlignTop

                boundsMovement: Flickable.StopAtBounds
                boundsBehavior: Flickable.StopAtBounds

                cellWidth: Style.dp(100)
                cellHeight: Style.dp(100)

                model: _hat_state
                delegate: Component {
                    HatView {
                        required property int identifier
                        required property point value

                        height: _hat_grid.cellHeight - Style.dp(20)
                        width: _hat_grid.cellWidth - Style.dp(20)

                        text: identifier
                        currentValue: value
                    }
                }
            }
        }
    }
}
