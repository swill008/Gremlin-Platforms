// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Profile
import Gremlin.Tools
import Gremlin.Menus as Menus
import Gremlin.Style
import Gremlin.Config

ApplicationWindow {
    id: _mapper
    font.pixelSize: Style.fontSize
    minimumWidth: Style.dp(900)
    minimumHeight: Style.dp(400)

    color: Style.background
    U.Universal.theme: Style.theme

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
    // The card it was opened from: its module starts ticked.
    property string initialSlug: ""

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Style.dp(10)

        RunningNote {}

        RowLayout {
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.rightMargin: Style.dp(10)

                RowLayout {
                    Label {
                        text: "Input module"
                    }

                    LayoutHorizontalSpacer {
                        Layout.preferredHeight: Style.dp(1)
                        color: Style.accent
                    }
                }

                JGListView {
                    Layout.fillHeight: true
                    Layout.fillWidth: true

                    model: _inputModules
                    scrollbarAlwaysVisible: true

                    delegate: CheckBox {
                        width: ListView.view.width - Style.dp(10)

                        text: model.name
                        checked: model.slug === _mapper.initialSlug

                        onCheckedChanged: () => {
                            selectedInputModules[model.slug] = checked
                        }
                        Component.onCompleted: selectedInputModules[model.slug] = checked
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
                        Layout.preferredHeight: Style.dp(1)
                        color: Style.accent
                    }
                }

                JGListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    model: _outputModules
                    scrollbarAlwaysVisible: true

                    delegate: CheckBox {
                        width: ListView.view.width - Style.dp(10)

                        text: model.name
                        checked: model.slug === _mapper.initialSlug

                        onCheckedChanged: () => {
                            selectedOutputModules[model.slug] = checked
                        }
                        Component.onCompleted: selectedOutputModules[model.slug] = checked
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
                    implicitWidth: Style.dp(120)
                    implicitHeight: Style.dp(32)
                    border.width: Style.dp(1)
                    border.color: _modeSelector.down || _modeSelector.hovered
                            ? _modeSelector.U.Universal.baseMediumColor
                            : _modeSelector.U.Universal.baseMediumLowColor
                    color: _modeSelector.down
                            ? _modeSelector.U.Universal.listMediumColor
                            : (Style.isDarkMode ? _modeSelector.U.Universal.altMediumLowColor : Style._light.item)
                }

                delegate: Menus.DropdownRow {
                    combo: _modeSelector
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
            Switch {
                id: _claimOutputs

                text: "Also claim the matching outputs on the output module"
                checked: false
                ToolTip.visible: hovered
                ToolTip.text: "Off: map only to outputs the output module already claims. On: claim the outputs the mappings need on the output module first."
            }
        }

        RowLayout {
            Layout.topMargin: Style.dp(10)

            Button {
                text: "Create 1:1 mappings"

                onClicked: () => {
                    var run = function() {
                        _statusMessage.text = tools.createMappings(
                            _modeSelector.currentText,
                            selectedInputModules,
                            selectedOutputModules,
                            _overwriteNonEmpty.checked,
                            _repeatDevices.checked,
                            _claimOutputs.checked
                        )

                        selectedInputModules = ({})
                        selectedOutputModules = ({})
                    }
                    if (!_overwriteNonEmpty.checked) {
                        run()
                        return
                    }
                    // Overwrite removes every action already on those inputs.
                    _overwriteGate.confirmThen("Replace existing actions",
                        "Overwrite used inputs is on. Every action already on the selected inputs in the "
                        + _modeSelector.currentText + " mode, macros included, will be removed and replaced "
                        + "with the new mappings.\n\nNothing is saved yet: to undo, load the profile again "
                        + "without saving.",
                        "Replace them", run, null, true)
                }
            }

            Label {
                id: _statusMessage

                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                Layout.leftMargin: Style.dp(10)
                Layout.rightMargin: Style.dp(10)

                text: "Select an input module and an output module, then create 1:1 mappings."
            }

            IconButton {
                text: bsi.icons.help
                font.pixelSize: Style.dp(24)

                PointerTip {
                    text: "Full guide: Help → User Guide → Tools → Auto Mapper. This tool builds a starting 1:1 mapping.\n\n"
                        + "Mode selection defaults to the default mode, change this if required for another mode.\n\n"
                        + "This tool does not match devices by name. It uses the order shown in the lists. The first checked input is wired to the first checked output. The second input is wired to the second output.\n\n"
                        + "Overwrite used inputs: Replaces wires that already exist on those controls in the selected mode. Leave it off, and those wires stay as they are.\n\n"
                        + "Combine onto Selected Outputs: This should stay off when each input should have its own output. Turn it on when you check more inputs than outputs.\n\n"
                        + "Also claim the matching outputs: Off, mappings are made only to outputs the output module already claims; the rest are listed as skipped. On, the outputs the mappings need are claimed on the output module first."
                    delay: 500
                }
            }
        }
    }

    // Asks before Overwrite used inputs replaces existing actions.
    DismissibleDialog {
        id: _overwriteGate
    }
}
