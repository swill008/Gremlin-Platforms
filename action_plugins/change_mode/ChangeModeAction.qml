// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

import QtQuick.Controls.Universal as U

import Gremlin.Profile
import Gremlin.ActionPlugins
import Gremlin.Base
import "../../qml"
import Gremlin.Style


Item {
    id: _root

    property ChangeModeModel action

    ModeHierarchyModel {
        id: _modeHierarchyModel
    }

    implicitHeight: _content.height

    RowLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right


        ComboBox {
            id: _changeType

            Layout.alignment: Qt.AlignTop

            model: ["Switch", "Previous", "Unwind", "Cycle", "Temporary"]

            Component.onCompleted: function() {
                currentIndex = find(_root.action.changeType)
            }

            onActivated: function() {
                _root.action.changeType = currentValue
            }
        }

        // Mode switch selection UI
        RowLayout {
            visible: _changeType.currentValue === "Switch"

            Label {
                text: "Switch to mode"
            }

            TooltipComboBox {
                id: _switch_combo

                Layout.preferredWidth: Style.dp(200)

                model: ModeListModel {}
                textRole: "name"
                valueRole: "name"

                Component.onCompleted: function() {
                    currentIndex = find(_root.action.targetModes[0])
                }

                onActivated: function() {
                    _root.action.setTargetMode(currentValue, 0)
                }

                Connections {
                    target: _changeType
                    function onActivated() {
                        if(visible)
                        {
                            _switch_combo.currentIndex = _switch_combo.find(
                                _root.action.targetModes[0]
                            )
                        }
                    }
                }
            }
        }

        // Switch to previous mode UI
        RowLayout {
            visible: _changeType.currentValue === "Previous"

            Label {
                text: "Change to the previously active mode"
            }
        }

        // Unwind one mode from the stack UI
        RowLayout {
            visible: _changeType.currentValue === "Unwind"

            Label {
                text: "Unwind one mode in the stack"
            }
        }

        // Mode cycle setup UI
        RowLayout {
            visible: _changeType.currentValue === "Cycle"

            Label {
                Layout.alignment: Qt.AlignTop

                text: "Cycle through these modes"
            }

            ColumnLayout {
                Layout.fillWidth: true

                Repeater {
                    model: _root.action.targetModes

                    RowLayout {
                        required property int index

                        TooltipComboBox {
                            Layout.preferredWidth: Style.dp(200)

                            model: ModeListModel {}
                            textRole: "name"
                            valueRole: "name"

                            Component.onCompleted: function() {
                                currentIndex = find(_root.action.targetModes[index])
                            }

                            onActivated: function() {
                                _root.action.setTargetMode(currentValue, index)
                            }
                        }

                        IconButton {
                            text: bsi.icons.remove

                            onClicked: {
                                _root.action.deleteTargetMode(index)
                            }
                        }
                    }
                }

                Button {
                    text: "Add mode"

                    onClicked: function() {
                        _root.action.addTargetMode()
                    }
                }

            }
        }

        // Temporary mode switch UI
        RowLayout {
            visible: _changeType.currentValue === "Temporary"

            Label {
                text: "Temporarily switch to mode"
            }

            TooltipComboBox {
                id: temporary_combo

                Layout.preferredWidth: Style.dp(200)

                model: ModeListModel {}
                textRole: "name"
                valueRole: "name"

                Component.onCompleted: function() {
                    currentIndex = find(_root.action.targetModes[0])
                }

                onActivated: function() {
                    _root.action.setTargetMode(currentValue, 0)
                }

                Connections {
                    target: _changeType
                    function onActivated() {
                        if(visible)
                        {
                            temporary_combo.currentIndex = temporary_combo.find(
                                _root.action.targetModes[0]
                            )
                        }
                    }
                }
            }
        }

        LayoutHorizontalSpacer {}
    }
}
