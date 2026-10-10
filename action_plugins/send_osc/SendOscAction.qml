// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts

import Gremlin.ActionPlugins
import Gremlin.Base
import Gremlin.Style
import "../../qml"

// Send OSC (D-09-OSC-OUTPUT): target, address, the values sent and the
// range "Input value" is scaled to.
Item {
    id: _root

    property SendOscModel action

    readonly property var typeKeys: ["auto", "int", "float", "bool", "text"]
    readonly property var typeNames: ["Auto", "Int", "Float", "Bool", "Text"]

    implicitHeight: _content.height

    ColumnLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right

        RowLayout {
            Layout.fillWidth: true

            Label {
                Layout.preferredWidth: Style.dp(80)
                text: "Target"
            }

            ComboBox {
                id: _target
                objectName: "sendOscTarget"

                Layout.fillWidth: true
                Layout.minimumWidth: Style.dp(200)

                model: _root.action ? _root.action.targetChoices : []
                textRole: "name"
                valueRole: "id"
                currentIndex: {
                    if (!_root.action) {
                        return -1
                    }
                    let choices = _root.action.targetChoices
                    for (let i = 0; i < choices.length; i++) {
                        if (choices[i].id === _root.action.target) {
                            return i
                        }
                    }
                    return -1
                }

                onActivated: (index) => {
                    _root.action.target = model[index].id
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true

            Label {
                Layout.preferredWidth: Style.dp(80)
                text: "Address"
            }

            JGTextField {
                id: _address
                objectName: "sendOscAddress"

                Layout.fillWidth: true

                text: _root.action ? _root.action.address : ""
                placeholderText: "/fader/1"
                selectByMouse: true

                onTextChanged: () => {
                    if (_root.action && _root.action.address !== text) {
                        _root.action.address = text
                    }
                }
            }
        }

        // Why the address can't be sent to (S149: never a pattern).
        Label {
            objectName: "sendOscAddressError"

            Layout.fillWidth: true
            Layout.leftMargin: Style.dp(80)

            visible: text !== "" && _address.text !== ""
            text: _root.action ? _root.action.addressError : ""
            color: Style.warn
            wrapMode: Text.WordWrap
        }

        Label {
            text: "Values"
        }

        Repeater {
            model: _root.action ? _root.action.values : []

            delegate: RowLayout {
                id: _row

                required property int index
                required property var modelData

                Layout.fillWidth: true

                ComboBox {
                    Layout.preferredWidth: Style.dp(130)

                    model: ["Fixed", "Input value"]
                    currentIndex: _row.modelData.source === "input" ? 1 : 0

                    onActivated: (choice) => {
                        _root.action.setValueField(
                            _row.index, "source", choice === 1 ? "input" : "fixed"
                        )
                    }
                }

                JGTextField {
                    Layout.fillWidth: true

                    visible: _row.modelData.source !== "input"
                    text: _row.modelData.value
                    selectByMouse: true

                    onEditingFinished: () => {
                        if (text !== _row.modelData.value) {
                            _root.action.setValueField(_row.index, "value", text)
                        }
                    }
                }

                LayoutHorizontalSpacer {
                    visible: _row.modelData.source === "input"
                }

                ComboBox {
                    Layout.preferredWidth: Style.dp(90)

                    model: _root.typeNames
                    currentIndex: Math.max(
                        0, _root.typeKeys.indexOf(_row.modelData.type)
                    )

                    onActivated: (choice) => {
                        _root.action.setValueField(
                            _row.index, "type", _root.typeKeys[choice]
                        )
                    }
                }

                IconButton {
                    text: bsi.icons.remove

                    onClicked: () => { _root.action.removeValue(_row.index) }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true

            Button {
                objectName: "sendOscAddValue"
                text: "Add Value"

                onClicked: () => { _root.action.addValue() }
            }

            LayoutHorizontalSpacer {}

            Label {
                text: "Min:"
            }

            FloatSpinBox {
                // Full size when there is room; shrinks to fit a narrow pane.
                Layout.fillWidth: true
                Layout.minimumWidth: Style.dp(100)
                Layout.maximumWidth: implicitWidth

                minValue: -100000
                maxValue: 100000
                stepSize: 0.1
                value: _root.action ? _root.action.inputMin : 0

                onValueModified: (newValue) => {
                    _root.action.inputMin = newValue
                }
            }

            Label {
                text: "Max:"
            }

            FloatSpinBox {
                // Full size when there is room; shrinks to fit a narrow pane.
                Layout.fillWidth: true
                Layout.minimumWidth: Style.dp(100)
                Layout.maximumWidth: implicitWidth

                minValue: -100000
                maxValue: 100000
                stepSize: 0.1
                value: _root.action ? _root.action.inputMax : 1

                onValueModified: (newValue) => {
                    _root.action.inputMax = newValue
                }
            }
        }
    }
}
