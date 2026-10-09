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
import "helpers.js" as Helpers
import "confirm.js" as Confirm

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

    // Off while the Overwrite question is open: there Enter and Esc cancel.
    Shortcut { sequence: "Esc"; enabled: !_mapper._question; onActivated: {} }
    Shortcut { sequence: "Return"; enabled: !_mapper._question; onActivated: {} }
    Shortcut { sequence: "Enter"; enabled: !_mapper._question; onActivated: {} }

    AutoMapInputModel {
        id: _inputModules
    }

    AutoMapOutputModel {
        id: _outputModules
    }

    Tools {
        id: tools
    }

    // The open Overwrite question (01 S140), for tests.
    property var _question: null
    property var selectedInputModules: ({})
    property var selectedOutputModules: ({})
    // The card it was opened from: its module starts ticked.
    property string initialSlug: ""
    // The toolbar's mode (the one being edited), and the mode picked here.
    readonly property string toolbarMode:
        (typeof uiState !== "undefined" && uiState) ? uiState.currentMode : ""
    property string chosenMode: toolbarMode
    onChosenModeChanged: _modeSelector.showChosen()

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
                        // A tick stays when the list is rebuilt (a stick
                        // plugged in or out); else the card's own module.
                        checked: (model.slug in selectedInputModules)
                                 ? selectedInputModules[model.slug]
                                 : model.slug === _mapper.initialSlug

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
                        // A tick stays when the list is rebuilt (a stick
                        // plugged in or out); else the card's own module.
                        checked: (model.slug in selectedOutputModules)
                                 ? selectedOutputModules[model.slug]
                                 : model.slug === _mapper.initialSlug

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

                model: ModeListModel {
                    // Rebuilt when the profile changes (Create does): the
                    // picked mode stays picked.
                    onModelReset: Qt.callLater(_modeSelector.showChosen)
                }

                textRole: "name"

                // Starts on the toolbar's mode (08 S108, D-08-AUTOMAP-MODE).
                function showChosen() {
                    var index = find(_mapper.chosenMode)
                    if (index >= 0)
                        currentIndex = index
                }

                Component.onCompleted: showChosen()
                onActivated: _mapper.chosenMode = currentText

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

                text: "Combine onto selected outputs"
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
                    var create = function() {
                        _statusMessage.text = tools.createMappings(
                            _modeSelector.currentText,
                            selectedInputModules,
                            selectedOutputModules,
                            _overwriteNonEmpty.checked,
                            _repeatDevices.checked,
                            _claimOutputs.checked,
                            _mapper.toolbarMode
                        )
                        // The ticked modules stay ticked and selected, so
                        // Create again uses them (08 S105, D-08-AUTOMAP-KEEP).
                    }
                    // The action panes close first, asking when one has
                    // changes, or a later OK would undo these (05 Q8).
                    var run = function() { Helpers.closeActionPanes(create) }
                    if (!_overwriteNonEmpty.checked) {
                        run()
                        return
                    }
                    // Overwrite removes every action already on those inputs
                    // (08 S95): the shared question (01 S140).
                    _mapper._question = Confirm.ask(_statusMessage, {
                        title: "Replace the actions in mode " + _modeSelector.currentText + "?",
                        text: "Overwrite used inputs is on. Every action already on the selected "
                            + "inputs in that mode, macros included, is removed and replaced "
                            + "with the new actions.",
                        note: "Nothing is saved yet: to undo, load the profile again without saving.",
                        action: "Replace Actions",
                        onAccept: function() {
                            _mapper._question = null
                            run()
                        },
                        onCancel: function() { _mapper._question = null }
                    })
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
                    text: "More in Help (F1): Tools › Auto Mapper. This tool builds starting 1:1 Map to vJoy actions.\n\n"
                        + "Select Mode starts on the toolbar's mode; pick another to make actions there.\n\n"
                        + "This tool does not match devices by name. It uses the order shown in the lists. The first checked input gets an action to the first checked output, the second input to the second output, and so on.\n\n"
                        + "Overwrite used inputs: replaces the actions those controls already have in the selected mode. Leave it off, and those actions stay as they are.\n\n"
                        + "Combine onto selected outputs: This should stay off when each input should have its own output. Turn it on when you check more inputs than outputs.\n\n"
                        + "Also claim the matching outputs: off, actions are made only for outputs the output module already claims; the rest are listed as skipped. On, the outputs the new actions need are claimed on the output module first."
                }
            }
        }
    }
}
