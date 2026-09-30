// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

import QtQuick.Controls.Universal as U

import Gremlin.ActionPlugins
import Gremlin.Base as Base
import Gremlin.Compact as Compact
import Gremlin.Profile
import "../../qml"
import Gremlin.Style


Item {
    id: _root

    property MapToMouseModel action
    property bool useCompact: false

    property int limitLow: 0
    property int limitHigh: 100000

    implicitHeight: _content.height

    Component { id: _baseSpinBox;         Base.SpinBox         {} }
    Component { id: _compactSpinBox;      Compact.SpinBox      {} }
    Component { id: _baseFloatSpinBox;    Base.FloatSpinBox    {} }
    Component { id: _compactFloatSpinBox; Compact.FloatSpinBox {} }

    ColumnLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right

        RowLayout {
            Label {
                id: _label

                Layout.preferredWidth: Style.dp(50)

                text: "<B>Mode</B>"
            }

            // Radio buttons to select the desired mapping mode.
            RadioButton {
                autoExclusive: false
                id: _mode_button

                text: "Button"
                visible: inputBinding && inputBinding.behavior === "button"

                checked: _root.action.mode === "Button"
                onClicked: () => { _root.action.mode = "Button" }
            }

            RadioButton {
                autoExclusive: false
                id: _mode_motion

                Layout.fillWidth: true

                text: "Motion"

                checked: _root.action.mode === "Motion"
                onClicked: () => { _root.action.mode = "Motion" }
            }
        }

        // Button configuration.
        RowLayout {
            visible: _mode_button.checked

            Label {
                text: "Mouse Button"
            }

            InputListener {
                callback: (inputs) => { _root.action.updateInputs(inputs) }
                multipleInputs: false
                eventTypes: ["mouse"]

                text: _root.action.button
            }

        }

        // Motion configuration for button-like inputs.
        GridLayout {
            visible: _mode_motion.checked && inputBinding && inputBinding.behavior === "button"

            columns: 5

            Label {
                Layout.fillWidth: true

                text: "Minimum speed"
            }

            Loader {
                id: _min_speed_button

                Layout.fillWidth: true

                sourceComponent: _root.useCompact ? _compactSpinBox : _baseSpinBox

                onLoaded: {
                    item.from  = _root.limitLow
                    item.to    = Qt.binding(() => _max_speed_button.item ? _max_speed_button.item.value : _root.limitHigh)
                    item.value = Qt.binding(() => _root.action.minSpeed)
                    item.onValueModified.connect(() => { _root.action.minSpeed = item.value })
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.horizontalStretchFactor: 1
            }

            Label {
                Layout.fillWidth: true

                text: "Maximum speed"
            }

            Loader {
                id: _max_speed_button

                Layout.fillWidth: true

                sourceComponent: _root.useCompact ? _compactSpinBox : _baseSpinBox

                onLoaded: {
                    item.from  = Qt.binding(() => _min_speed_button.item ? _min_speed_button.item.value : _root.limitLow)
                    item.to    = _root.limitHigh
                    item.value = Qt.binding(() => _root.action.maxSpeed)
                    item.onValueModified.connect(() => { _root.action.maxSpeed = item.value })
                }
            }

            Label {
                text: "Time to maximum speed"
            }

            Loader {
                sourceComponent: _root.useCompact ? _compactFloatSpinBox : _baseFloatSpinBox

                onLoaded: {
                    item.minValue = 0
                    item.maxValue = 60
                    item.stepSize = 1.0
                    item.decimals = 1
                    item.value    = Qt.binding(() => _root.action.timeToMaxSpeed)
                    item.onValueModified.connect((newValue) => { _root.action.timeToMaxSpeed = newValue })
                }
            }

            Rectangle {}

            Label {
                text: "Direction"
            }

            Loader {
                sourceComponent: _root.useCompact ? _compactSpinBox : _baseSpinBox

                onLoaded: {
                    item.from     = 0
                    item.to       = 360
                    item.stepSize = 15
                    item.value    = Qt.binding(() => _root.action.direction)
                    item.onValueModified.connect(() => { _root.action.direction = item.value })
                }
            }
        }

        // Motion configuration for axis inputs.
        ColumnLayout {
            visible: _mode_motion.checked && inputBinding && inputBinding.behavior === "axis"

            RowLayout {
                Label {
                    text: "Control motion of"
                }

                RadioButton {
                    autoExclusive: false
                autoExclusive: false
                    text: "X Axis"

                    checked: _root.action.direction === 90
                    onClicked: () => { _root.action.direction = 90 }
                }

                RadioButton {
                    autoExclusive: false
                autoExclusive: false
                    text: "Y Axis"

                    checked: _root.action.direction === 0
                    onClicked: () => { _root.action.direction = 0 }
                }
            }

            RowLayout {

                Label {
                    Layout.rightMargin: Style.dp(10)

                    text: "Minimum speed"
                }

                Loader {
                    id: _min_speed_axis

                    Layout.preferredWidth: Style.dp(150)

                    sourceComponent: _root.useCompact ? _compactSpinBox : _baseSpinBox

                    onLoaded: {
                        item.from  = _root.limitLow
                        item.to    = Qt.binding(() => _max_speed_axis.item ? _max_speed_axis.item.value : _root.limitHigh)
                        item.value = Qt.binding(() => _root.action.minSpeed)
                        item.onValueModified.connect(() => { _root.action.minSpeed = item.value })
                    }
                }

                Label {
                    Layout.leftMargin: Style.dp(50)
                    Layout.rightMargin: Style.dp(10)

                    text: "Maximum speed"
                }

                Loader {
                    id: _max_speed_axis

                    Layout.preferredWidth: Style.dp(150)

                    sourceComponent: _root.useCompact ? _compactSpinBox : _baseSpinBox

                    onLoaded: {
                        item.from  = Qt.binding(() => _min_speed_axis.item ? _min_speed_axis.item.value : _root.limitLow)
                        item.to    = _root.limitHigh
                        item.value = Qt.binding(() => _root.action.maxSpeed)
                        item.onValueModified.connect(() => { _root.action.maxSpeed = item.value })
                    }
                }
            }
        }

        // Motion configuration for hat inputs.
        GridLayout {
            visible: _mode_motion.checked && inputBinding && inputBinding.behavior === "hat"

            columns: 4

            Label {
                Layout.fillWidth: true

                text: "Minimum speed"
            }

            Loader {
                id: _min_speed_hat

                Layout.fillWidth: true

                sourceComponent: _root.useCompact ? _compactSpinBox : _baseSpinBox

                onLoaded: {
                    item.from  = _root.limitLow
                    item.to    = Qt.binding(() => _max_speed_hat.item ? _max_speed_hat.item.value : _root.limitHigh)
                    item.value = Qt.binding(() => _root.action.minSpeed)
                    item.onValueModified.connect(() => { _root.action.minSpeed = item.value })
                }
            }

            Label {
                Layout.fillWidth: true

                text: "Maximum speed"
            }

            Loader {
                id: _max_speed_hat

                Layout.fillWidth: true

                sourceComponent: _root.useCompact ? _compactSpinBox : _baseSpinBox

                onLoaded: {
                    item.from  = Qt.binding(() => _min_speed_hat.item ? _min_speed_hat.item.value : _root.limitLow)
                    item.to    = _root.limitHigh
                    item.value = Qt.binding(() => _root.action.maxSpeed)
                    item.onValueModified.connect(() => { _root.action.maxSpeed = item.value })
                }
            }

            Label {
                text: "Time to maximum speed"
            }

            Loader {
                sourceComponent: _root.useCompact ? _compactFloatSpinBox : _baseFloatSpinBox

                onLoaded: {
                    item.minValue = 0
                    item.maxValue = 30
                    item.stepSize = 1.0
                    item.decimals = 1
                    item.value    = Qt.binding(() => _root.action.timeToMaxSpeed)
                    item.onValueModified.connect((newValue) => { _root.action.timeToMaxSpeed = newValue })
                }
            }
        }
    }
}
