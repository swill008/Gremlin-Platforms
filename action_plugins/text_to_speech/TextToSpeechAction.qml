// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts

import Gremlin.ActionPlugins
import Gremlin.Base
import Gremlin.Profile
import "../../qml"
import Gremlin.Style


Item {
    id: _root

    property TextToSpeechModel action

    implicitHeight: _content.height

    ColumnLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right

        JGTextField {
            Layout.fillWidth: true

            wrapMode: TextArea.Wrap
            placeholderText: "Enter text to speak"
            text: _root.action !== null ? _root.action.text : ""
            selectByMouse: true

            onTextChanged: () => {
                if (_root.action !== null && _root.action.text !== text) {
                    _root.action.text = text
                }
            }
        }

        // Wraps onto more lines when the pane is narrow; each label stays
        // with its box.
        Flow {
            Layout.fillWidth: true
            spacing: Style.dp(10)

            ComboBox {
                implicitContentWidthPolicy: ComboBox.WidestText

                readonly property var _labels: ["Interrupt", "Queue Front", "Queue Back"]
                readonly property var _values: ["interrupt", "queue-front", "queue-back"]

                model: _labels

                currentIndex: _root.action !== null
                    ? _values.indexOf(_root.action.queueMode)
                    : _values.indexOf("queue-back")

                onActivated: (index) => {
                    if (_root.action !== null) {
                        _root.action.queueMode = _values[index]
                    }
                }
            }

            RowLayout {
                Label {
                    Layout.rightMargin: Style.dp(5)

                    text: "Volume (%)"
                }

                // Shown 0-100 like Play Sound's; the profile keeps 0-1.
                FloatSpinBox {
                    value: _root.action !== null ? _root.action.playbackVolume * 100 : 100
                    minValue: 0
                    maxValue: 100
                    stepSize: 5
                    decimals: 0

                    onValueModified: (val) => { _root.action.playbackVolume = val / 100 }
                }
            }

            RowLayout {
                Label {
                    Layout.rightMargin: Style.dp(5)

                    text: "Rate"
                    ToolTip.visible: _rateHover.hovered
                    ToolTip.text: "-1 slowest, 0 normal, 1 fastest"
                    HoverHandler { id: _rateHover }
                }

                FloatSpinBox {
                    value: _root.action !== null ? _root.action.playbackRate : 0.0
                    minValue: -1.0
                    maxValue: 1.0
                    stepSize: 0.1

                    onValueModified: (val) => { _root.action.playbackRate = val }
                }
            }

            RowLayout {
                Label {
                    Layout.rightMargin: Style.dp(5)

                    text: "Pitch"
                    ToolTip.visible: _pitchHover.hovered
                    ToolTip.text: "-1 lowest, 0 normal, 1 highest"
                    HoverHandler { id: _pitchHover }
                }

                FloatSpinBox {
                    value: _root.action !== null ? _root.action.playbackPitch : 0.0
                    minValue: -1.0
                    maxValue: 1.0
                    stepSize: 0.1

                    onValueModified: (val) => { _root.action.playbackPitch = val }
                }
            }
        }
    }
}
