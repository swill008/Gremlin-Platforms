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

    // Opens at the size it was left at (capped to the screen).
    ToolWindowMemory {
        host: _mapper
        name: "autoMapper"
        defaultWidth: _mapper.minimumWidth
        defaultHeight: _mapper.minimumHeight
    }
    font.pixelSize: Style.fontSize
    minimumWidth: Style.fitWidth(Style.dp(900), Screen)
    minimumHeight: Style.fitHeight(Style.dp(400), Screen)

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
                ToolTip.text: "Off: make actions only for outputs the output module already claims. On: claim the outputs the new actions need on the output module first."
            }
        }

        RowLayout {
            Layout.topMargin: Style.dp(10)

            Button {
                text: "Create 1:1 Actions"

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
                    _overwriteGate.confirmThen("Replace Existing Actions",
                        "Overwrite used inputs is on. Every action already on the selected inputs in the "
                        + _modeSelector.currentText + " mode, macros included, will be removed and replaced "
                        + "with the new actions.\n\nNothing is saved yet: to undo, load the profile again "
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

                text: "Select an input module and an output module, then create 1:1 actions."
            }

            IconButton {
                text: bsi.icons.help
                font.pixelSize: Style.dp(24)

                PointerTip {
                    text: "Full guide: Help → User Guide → Tools → Auto Mapper. This tool builds starting 1:1 Map to vJoy actions.\n\n"
                        + "Mode starts on the default mode; pick another to make actions there.\n\n"
                        + "This tool does not match devices by name. It uses the order shown in the lists. The first checked input gets an action to the first checked output, the second input to the second output, and so on.\n\n"
                        + "Overwrite used inputs: replaces the actions those controls already have in the selected mode. Leave it off, and those actions stay as they are.\n\n"
                        + "Combine onto Selected Outputs: This should stay off when each input should have its own output. Turn it on when you check more inputs than outputs.\n\n"
                        + "Also claim the matching outputs: off, actions are made only for outputs the output module already claims; the rest are listed as skipped. On, the outputs the new actions need are claimed on the output module first."
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
