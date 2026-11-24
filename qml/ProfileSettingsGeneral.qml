// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Base
import Gremlin.Profile
import Gremlin.Style
import Gremlin.UI

// Profile Settings › General (04 S62-S64, S96, S98): Startup Mode and the
// Macro Default Delay, in Options' cards and rows.
ScrollView {
    id: _root

    readonly property ProfileSettingsModel settingsModel:
        ModelFactory.create("ProfileSettingsModel", _root)

    contentWidth: availableWidth
    ScrollBar.vertical.interactive: true
    Component.onCompleted: {
        contentItem.boundsMovement = Flickable.StopAtBounds
    }

    ColumnLayout {
        width: _root.availableWidth - Style.dp(40)
        x: Style.dp(20)
        spacing: Style.dp(4)

        GroupLabel { text: "Startup" }
        Card {
            OptionEntryCard {
                Layout.fillWidth: true
                title: "Startup Mode"
                explanation: "The mode the profile opens in when it is loaded. "
                    + "Last Active opens the mode the profile last ran in, or, "
                    + "if there is none yet, the top mode in Manage Modes. "
                    + "Choosing a mode by name opens that mode. Run starts in "
                    + "the mode shown in the toolbar."

                ComboBox {
                    id: _startupBox
                    objectName: "startupModeBox"
                    Layout.preferredWidth: Style.dp(240)

                    readonly property StartupModeModel _startupModes:
                        ModelFactory.create("StartupModeModel", _startupBox)
                    model: _startupModes

                    textRole: "label"
                    valueRole: "value"
                    currentIndex: model.currentSelectionIndex

                    onActivated: () => {
                        model.currentSelectionIndex = currentIndex
                    }
                }
            }
        }

        GroupLabel { text: "Macros" }
        Card {
            OptionEntryCard {
                Layout.fillWidth: true
                title: "Macro Default Delay"
                explanation: "Delay between macro actions that have no Pause."

                RowLayout {
                    spacing: Style.dp(6)

                    FloatSpinBox {
                        objectName: "macroDefaultDelayBox"
                        // Following Options: shows that value, greyed out.
                        enabled: _root.settingsModel ? !_root.settingsModel.macroDelayFromOptions : false
                        minValue: 0.0
                        maxValue: 10.0
                        stepSize: 0.1
                        decimals: 3

                        value: _root.settingsModel ? _root.settingsModel.macroDefaultDelay : 0
                        onValueModified: (newValue) => {
                            if (_root.settingsModel) {
                                _root.settingsModel.macroDefaultDelay = newValue
                            }
                        }
                    }
                    // The unit (S98).
                    Label {
                        text: "s"
                        color: Style.fgSoft
                        font.pixelSize: Style.dp(14)
                    }
                }
            }
            OptionEntryCard {
                Layout.fillWidth: true
                divider: true
                title: "Use the Options default (Options › Actions › Macro)"

                CheckBox {
                    objectName: "macroDelayFromOptionsBox"
                    property bool shown: _root.settingsModel ? _root.settingsModel.macroDelayFromOptions : true
                    onShownChanged: checked = shown
                    Component.onCompleted: checked = shown
                    onToggled: {
                        if (_root.settingsModel)
                            _root.settingsModel.macroDelayFromOptions = checked
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
