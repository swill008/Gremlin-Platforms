// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Profile
import Gremlin.Tools
import Gremlin.Style
import Gremlin.Config

ApplicationWindow {
    font.pixelSize: Style.fontSize
    minimumWidth: 900
    minimumHeight: 400

    color: Style.background
    Universal.theme: Style.theme

    title: "Auto Mapper"

    Shortcut { sequence: "Esc"; onActivated: {} }
    Shortcut { sequence: "Return"; onActivated: {} }
    Shortcut { sequence: "Enter"; onActivated: {} }

    AutoMapInputModel {
        id: _inputModules
    }

    AutoMapOutputModel {
        id: _outputModules
    }

    Tools {
        id: tools
    }

    property var selectedInputModules: ({})
    property var selectedOutputModules: ({})

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        anchors.bottomMargin: 58

        RowLayout {
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.rightMargin: 10

                RowLayout {
                    Label {
                        text: "Input module"
                    }

                    LayoutHorizontalSpacer {
                        Layout.preferredHeight: 1
                        color: Style.accent
                    }
                }

                JGListView {
                    Layout.fillHeight: true
                    Layout.fillWidth: true

                    model: _inputModules
                    scrollbarAlwaysVisible: true

                    delegate: CheckBox {
                        width: ListView.view.width - 10

                        text: model.name
                        checked: false

                        onCheckedChanged: () => {
                            selectedInputModules[model.slug] = checked
                        }
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true

                RowLayout {
                    Label {
                        text: "Output module"
                    }

                    LayoutHorizontalSpacer {
                        Layout.preferredHeight: 1
                        color: Style.accent
                    }
                }

                JGListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    model: _outputModules
                    scrollbarAlwaysVisible: true

                    delegate: CheckBox {
                        width: ListView.view.width - 10

                        text: model.name
                        checked: false

                        onCheckedChanged: () => {
                            selectedOutputModules[model.slug] = checked
                        }
                    }
                }
            }
        }

        RowLayout {
            Label {
                text: "Select Mode"
            }

            ComboBox {
                id: _modeSelector

                model: ModeListModel {}

                textRole: "name"

                background: Rectangle {
                    implicitWidth: 120
                    implicitHeight: 32
                    border.width: 1
                    border.color: _modeSelector.down || _modeSelector.hovered
                            ? _modeSelector.Universal.baseMediumColor
                            : _modeSelector.Universal.baseMediumLowColor
                    color: _modeSelector.down
                            ? _modeSelector.Universal.listMediumColor
                            : _modeSelector.Universal.altMediumLowColor
                }

                delegate: ItemDelegate {
                    required property var model
                    required property int index

                    width: ListView.view ? ListView.view.width : implicitWidth
                    text: model[_modeSelector.textRole]
                    font.weight: _modeSelector.currentIndex === index ? Font.DemiBold : Font.Normal
                    highlighted: false
                    hoverEnabled: true

                    background: Rectangle {
                        color: (_modeSelector.highlightedIndex === index || parent.hovered)
                                ? _modeSelector.Universal.listMediumColor
                                : "transparent"
                    }
                }
            }

            LayoutHorizontalSpacer {}

            Switch {
                id: _overwriteNonEmpty

                text: "Overwrite used inputs"

                Component.onCompleted: checked = tools.lastOverwriteUsedInputs()
            }

            Switch {
                id: _repeatDevices

                text: "Combine onto Selected Outputs"
            }
        }

        RowLayout {
            Layout.topMargin: 10

            Button {
                text: "Create 1:1 mappings"

                onClicked: () => {
                    _statusMessage.text = tools.createMappings(
                        _modeSelector.currentText,
                        selectedInputModules,
                        selectedOutputModules,
                        _overwriteNonEmpty.checked,
                        _repeatDevices.checked
                    )

                    selectedInputModules = ({})
                    selectedOutputModules = ({})
                }
            }

            Label {
                id: _statusMessage

                Layout.fillWidth: true
                Layout.leftMargin: 10
                Layout.rightMargin: 10

                text: "Select an input module and an output module, then create 1:1 mappings."
            }

            IconButton {
                text: bsi.icons.help
                font.pixelSize: 24

                PointerTip {
                    text: "See Help, then Tools, then Mapping, then Auto Mapper, for the full Help Guide. The intent of this tool is to build a starting 1:1 mapping.\n\n"
                        + "Mode selection defaults to the default mode, change this if required for another mode.\n\n"
                        + "This tool does not match devices by name. It uses the order shown in the lists. The first checked input is wired to the first checked output. The second input is wired to the second output.\n\n"
                        + "Overwrite used inputs: Replaces wires that already exist on those controls in the selected mode. Leave it off, and those wires stay as they are.\n\n"
                        + "Combine onto Selected Outputs: This should stay off when each input should have its own output. Turn it on when you check more inputs than outputs."
                    delay: 500
                }
            }
        }
    }

    DebugFileLine {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
    }
}
