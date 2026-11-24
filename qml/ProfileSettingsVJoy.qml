// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Base
import Gremlin.Profile
import Gremlin.Style
import Gremlin.UI

// Profile Settings › vJoy (04 S62, S96-S98): each vJoy as output or input,
// and the initial axis values used when the profile runs.
ScrollView {
    id: _root

    contentWidth: availableWidth
    ScrollBar.vertical.interactive: true
    Component.onCompleted: {
        contentItem.boundsMovement = Flickable.StopAtBounds
    }

    ColumnLayout {
        width: _root.availableWidth - Style.dp(40)
        x: Style.dp(20)
        spacing: Style.dp(4)

        GroupLabel { text: "vJoy Behavior" }
        Card {
            Repeater {
                id: _modeRepeater
                readonly property VJoyInputOrOutputModel _vjoyModes:
                    ModelFactory.create("VJoyInputOrOutputModel", _modeRepeater)
                model: _vjoyModes

                delegate: OptionEntryCard {
                    Layout.fillWidth: true
                    divider: index > 0
                    title: `vJoy ${vid}`

                    RowLayout {
                        spacing: Style.dp(8)

                        Label {
                            text: "Output"
                            color: Style.fgSoft
                            font.pixelSize: Style.dp(14)
                        }
                        Switch {
                            objectName: `vjoyIsInput:${vid}`
                            text: "Input"

                            checked: isInput
                            onToggled: () => { isInput = checked }
                        }
                    }
                }
            }
        }
        Label {
            Layout.fillWidth: true
            Layout.topMargin: Style.dp(2)
            text: "Output: used by 'Map to vJoy'. Input: read like any other "
                + "joystick, useful when several vJoy devices are used by "
                + "different programs."
            color: Style.fgMuted
            font.pixelSize: Style.dp(12)
            wrapMode: Text.WordWrap
        }

        GroupLabel { text: "vJoy Initial Values (used when the profile runs)" }
        Repeater {
            id: _initialRepeater
            readonly property OutputVJoyListModel _outputVJoys:
                ModelFactory.create("OutputVJoyListModel", _initialRepeater)
            model: _outputVJoys

            delegate: Card {
                id: _card
                required property int vjoyId
                required property var initialValuesModel
                Layout.bottomMargin: Style.dp(12)

                Label {
                    Layout.fillWidth: true
                    Layout.leftMargin: Style.dp(14)
                    Layout.topMargin: Style.dp(10)
                    Layout.bottomMargin: Style.dp(10)
                    text: `vJoy ${_card.vjoyId}`
                    color: Style.fgStrong
                    font.pixelSize: Style.dp(14)
                }
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: Style.dp(1)
                    color: Style.line
                }

                // The axes, in two columns.
                GridLayout {
                    Layout.fillWidth: true
                    Layout.margins: Style.dp(14)
                    columns: 2
                    columnSpacing: Style.dp(24)
                    rowSpacing: Style.dp(8)

                    Repeater {
                        model: _card.initialValuesModel

                        delegate: RowLayout {
                            Layout.fillWidth: true
                            Layout.preferredWidth: 1
                            spacing: Style.dp(12)

                            Label {
                                text: label
                                color: Style.fgStrong
                                font.pixelSize: Style.dp(14)
                                Layout.preferredWidth: Style.dp(110)
                                elide: Text.ElideRight
                            }

                            // Named for the control API (13 D-13-INITIAL-VALUES).
                            FloatSpinBox {
                                objectName: `vjoyInitialValue:${_card.vjoyId}:${label}`
                                minValue: -1.0
                                maxValue: 1.0
                                stepSize: 0.05

                                value: model.value
                                onValueModified: (newValue) => { model.value = newValue }
                            }

                            Item { Layout.fillWidth: true }
                        }
                    }
                }
            }
        }

        Item { Layout.preferredHeight: Style.dp(16) }
    }

    // A small heading over a card, as ConfigGroup's.
    component GroupLabel : Label {
        Layout.topMargin: Style.dp(14)
        color: Style.fgMuted
        font.pixelSize: Style.dp(12)
    }

    // The card rows sit in, as ConfigGroup's.
    component Card : Rectangle {
        default property alias rows: _rows.data
        Layout.fillWidth: true
        implicitHeight: _rows.implicitHeight
        radius: Style.dp(6)
        color: Style.bgCard
        border.color: Style.line
        border.width: Style.dp(1)

        ColumnLayout {
            id: _rows
            width: parent.width
            spacing: 0
        }
    }
}
