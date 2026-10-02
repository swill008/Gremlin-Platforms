// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import Qt.labs.qmlmodels

import Gremlin.Base
import Gremlin.Profile
import Gremlin.Style
import "helpers.js" as Helpers

Item {
    id: _root

    readonly property int userEntryColumnWidth: Style.dp(350)
    readonly property int userEntryColumnPadding: Style.dp(50)

    property ProfileSettingsModel settingsModel


    ScrollView {
        anchors.fill: parent

        contentWidth: availableWidth
        padding: Style.dp(10)

        ScrollBar.vertical.interactive: true
        Component.onCompleted: {
            contentItem.boundsMovement = Flickable.StopAtBounds
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Style.dp(10)

            ColumnLayout {
                Layout.fillWidth: true

                UIHeader {
                    text: "Startup Mode"
                }

                RowLayout {
                    ComboBox {
                        Layout.alignment: Qt.AlignTop
                        Layout.preferredWidth: userEntryColumnWidth
                        Layout.rightMargin: userEntryColumnPadding

                        model: StartupModeModel {}

                        textRole: "label"
                        valueRole: "value"
                        currentIndex: model.currentSelectionIndex

                        onActivated: () => {
                            model.currentSelectionIndex = currentIndex
                        }
                    }

                    UIText {
                        Layout.fillWidth: true

                        text: "The mode the profile is in when it is loaded. Use Heuristic picks the first mode, in alphabetical order, that has no parent. Last Active picks the mode this profile was using the last time it ran. Choosing a mode by name picks that mode. Toggle starts in the mode shown in the toolbar."
                    }
                }

            }

            ColumnLayout {
                Layout.fillWidth: true

                UIHeader {
                    text: "Macro Default Delay"
                }

                RowLayout {
                    FloatSpinBox {
                        Layout.alignment: Qt.AlignTop
                        Layout.preferredWidth: userEntryColumnWidth
                        Layout.rightMargin: userEntryColumnPadding

                        // Following Options: shows that value, greyed out.
                        enabled: settingsModel ? !settingsModel.macroDelayFromOptions : false
                        minValue: 0.0
                        maxValue: 10.0
                        stepSize: 0.1
                        decimals: 3

                        value: settingsModel ? settingsModel.macroDefaultDelay : 0
                        onValueModified: (newValue) => {
                            if (settingsModel) {
                                settingsModel.macroDefaultDelay = newValue
                            }
                        }
                    }

                    UIText {
                        Layout.fillWidth: true

                        text: "Delay inserted between macro actions in " +
                            "seconds if no pause action is present."
                    }
                }

                CheckBox {
                    text: "Use the Options default (Options → Action → Macro)"
                    property bool shown: settingsModel ? settingsModel.macroDelayFromOptions : true
                    onShownChanged: checked = shown
                    Component.onCompleted: checked = shown
                    onToggled: {
                        if (settingsModel)
                            settingsModel.macroDelayFromOptions = checked
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true

                UIHeader {
                    text: "vJoy Behavior"
                }

                RowLayout {
                    ListView {
                        Layout.alignment: Qt.AlignTop
                        Layout.preferredWidth: userEntryColumnWidth
                        Layout.rightMargin: userEntryColumnPadding
                        implicitHeight: contentHeight

                        model: VJoyInputOrOutputModel {}

                        delegate: RowLayout {
                            Label {
                                text: `vJoy ${vid} is`
                                Layout.preferredWidth: Style.dp(75)
                            }
                            Switch {
                                text: checked ? "Input" : "Output"

                                checked: isInput
                                onToggled: () => { isInput = checked }
                            }
                        }
                    }

                    UIText {
                        Layout.fillWidth: true

                        text: "Determines whether vJoy devices are treated as " +
                            "input or output devices by Gremlin. If treated " +
                            "as an output device, it can be used with the " +
                            "'Map to vJoy' action. If treated as an input device, " +
                            "the vJoy device is treated like any other " +
                            "joystick. This is useful when multiple vJoy " +
                            "devices exist and are used by different programs."
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true

                UIHeader {
                    text: "vJoy Initial Values"
                }

                RowLayout {
                    JGListView {
                        Layout.preferredWidth: userEntryColumnWidth
                        Layout.rightMargin: userEntryColumnPadding
                        implicitHeight: contentHeight

                        spacing: Style.dp(20)

                        model: OutputVJoyListModel {}

                        delegate: ColumnLayout {
                            Layout.fillWidth: true

                            Label {
                                text: `vJoy ${vjoyId}`
                            }

                            HorizontalDivider {
                                Layout.fillWidth: true

                                dividerColor: Style.lowColor
                                lineWidth: Style.dp(2)
                                spacing: Style.dp(2)
                            }

                            OutputVJoyInitialValueEntryDelegate {
                                dataModel: initialValuesModel
                            }
                        }
                    }

                    UIText {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignTop

                        text: "Defines the initial values for vJoy axes to use " +
                            "when a profile is activated."
                    }
                }
            }

            ColumnLayout {
                Layout.fillHeight: true
            }
        }
    }

    component UIHeader : JGText {
        font.pixelSize: Style.dp(19)
        font.weight: 500
        font.family: "Segoe UI"
    }

    component UIText : JGText {
        Layout.fillWidth: true
        horizontalAlignment: Text.AlignJustify
        wrapMode: Text.Wrap

        font.pixelSize: Style.dp(15)
        font.family: "Segoe UI"
    }

    component OutputVJoyInitialValueEntryDelegate : ColumnLayout {
        property alias dataModel : _repeater.model

        Repeater {
            id: _repeater

            delegate: RowLayout {
                JGText {
                    text: label
                    Layout.preferredWidth: Style.dp(100)
                }

                FloatSpinBox {
                    minValue: -1.0
                    maxValue: 1.0
                    stepSize: 0.05

                    value: model.value
                    onValueModified: (newValue) => { model.value = newValue }
                }
            }
        }
    }
}
