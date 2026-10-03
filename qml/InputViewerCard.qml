// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts

import Gremlin.Device
import Gremlin.Style

ColumnLayout {
    id: _root

    property string deviceGuid: ""
    property string deviceName: ""
    property string title: ""
    property string pairLabel: ""
    property bool destEmpty: false
    property int axisStamp: _live && _live.axisStamp !== undefined ? _live.axisStamp : (_live ? _live.stamp : 0)
    property int buttonStamp: _live && _live.buttonStamp !== undefined ? _live.buttonStamp : (_live ? _live.stamp : 0)
    property bool pairActive: backend && backend.gremlinActive

    spacing: Style.dp(4)

    ModulePairAxisModel {
        id: _axes
        guid: deviceGuid
        deviceName: _root.deviceName
    }

    ModulePairButtonModel {
        id: _buttons
        guid: deviceGuid
        deviceName: _root.deviceName
    }

    PairLiveThrottle {
        id: _live
        guid: deviceGuid
    }

    function hwAxis(id) {
        if (!_live)
            return 0
        return axisStamp >= 0 ? _live.axisValue(id) : 0
    }
    function vjAxis(g, id) {
        if (!_live)
            return 0
        return axisStamp >= 0 ? _live.vjoyAxisValue(g, id) : 0
    }
    function hwButton(id) {
        if (!_live)
            return 0
        return buttonStamp >= 0 ? _live.buttonValue(id) : 0
    }
    function vjButton(g, id) {
        if (!_live)
            return 0
        return buttonStamp >= 0 ? _live.vjoyButtonValue(g, id) : 0
    }

    Rectangle {
        Layout.fillWidth: true
        implicitHeight: _inner.implicitHeight + Style.dp(16)
        color: pairActive ? Style.okFillDeep : Style.background
        border.color: pairActive ? Style.ok : Style.accent
        border.width: pairActive ? Style.dp(2) : Style.dp(1)
        radius: Style.dp(6)
        clip: true

        ColumnLayout {
            id: _inner
            width: parent.width - Style.dp(16)
            x: Style.dp(8)
            y: Style.dp(8)
            spacing: Style.dp(6)

            RowLayout {
                Layout.fillWidth: true

                JGText {
                    text: title
                    font.pixelSize: Style.dp(16)
                }

                Rectangle {
                    visible: pairActive
                    width: Style.dp(8)
                    height: Style.dp(8)
                    radius: Style.dp(4)
                    color: Style.ok
                }

                JGText {
                    visible: pairActive
                    text: "Running"
                    color: Style.ok
                    font.pixelSize: Style.dp(13)
                }

                Item { Layout.fillWidth: true }

                JGText {
                    visible: pairLabel.length > 0
                    text: "\u2192  " + pairLabel
                    color: pairActive ? Style.okText : Style.accent
                }

                Switch {
                    id: _temporal
                    text: "Axes - Temporal"
                }
            }

            JGText {
                visible: destEmpty
                text: "Output module has no claimed controls. Output Module Setup to fill the right half."
                color: Style.fgMuted
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                font.pixelSize: Style.dp(13)
            }

            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: _temporal.checked ? Style.dp(200) : 0
                visible: _temporal.checked
                clip: true

                Loader {
                    anchors.fill: parent
                    active: _temporal.checked
                    source: Qt.resolvedUrl("AxesStateSeries.qml")
                    onLoaded: {
                        if (item) {
                            item.deviceGuid = _root.deviceGuid
                            item.title = ""
                        }
                    }
                }
            }

            JGText {
                text: "Mapped axes"
                opacity: 0.7
                font.pixelSize: Style.dp(13)
            }

            JGText {
                visible: _axes.count === 0
                text: destEmpty ? "No dest-claimed axes." : "No claimed axes send to this output."
                opacity: 0.45
                font.pixelSize: Style.dp(13)
            }

            Repeater {
                model: _axes

                delegate: RowLayout {
                    required property int identifier
                    required property string label
                    required property string vjoyLabel
                    required property string vjoyGuid
                    required property int vjoyInput
                    required property bool destClaimed
                    Layout.fillWidth: true
                    spacing: Style.dp(8)

                    Label {
                        text: label
                        color: Style.foreground
                        Layout.preferredWidth: Style.dp(28)
                        font.pixelSize: Style.dp(13)
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Style.dp(4)
                        radius: Style.dp(2)
                        color: Style.lowColor

                        Rectangle {
                            height: parent.height
                            radius: Style.dp(2)
                            width: parent.width * Math.min(1.0, Math.max(0.0, (hwAxis(identifier) + 1.0) * 0.5))
                            color: Style.ok
                        }
                    }

                    Label {
                        text: vjoyLabel.length ? vjoyLabel : "—"
                        color: destClaimed ? Style.accent : Style.fgDisabled
                        Layout.preferredWidth: Style.dp(88)
                        font.pixelSize: Style.dp(12)
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Style.dp(4)
                        radius: Style.dp(2)
                        color: Style.lowColor

                        Rectangle {
                            visible: destClaimed
                            height: parent.height
                            radius: Style.dp(2)
                            width: parent.width * Math.min(1.0, Math.max(0.0, (vjAxis(vjoyGuid, vjoyInput) + 1.0) * 0.5))
                            color: Style.live
                        }
                    }
                }
            }

            JGText {
                text: "Mapped buttons"
                opacity: 0.7
                font.pixelSize: Style.dp(13)
            }

            JGText {
                visible: _buttons.count === 0
                text: destEmpty ? "No dest-claimed buttons." : "No claimed buttons send to this output."
                opacity: 0.45
                font.pixelSize: Style.dp(13)
            }

            Rectangle {
                Layout.fillWidth: true
                visible: _buttons.count > 0
                implicitHeight: _btnFlow.implicitHeight + Style.dp(16)
                color: "transparent"
                border.color: Style.medColor
                border.width: Style.dp(1)
                radius: Style.dp(6)

                Flow {
                    id: _btnFlow
                    width: parent.width - Style.dp(16)
                    x: Style.dp(8)
                    y: Style.dp(8)
                    spacing: Style.dp(10)

                    Repeater {
                        model: _buttons

                        delegate: Rectangle {
                            required property int identifier
                            required property string label
                            required property string vjoyLabel
                            required property string vjoyGuid
                            required property int vjoyInput
                            required property bool destClaimed

                            property bool hwOn: hwButton(identifier) > 0.5
                            property bool vjOn: destClaimed && vjButton(vjoyGuid, vjoyInput) > 0.5

                            width: Style.dp(40)
                            height: Style.dp(18)
                            radius: Style.dp(3)
                            color: Style.background
                            border.color: (hwOn || vjOn) ? Style.ok : Style.medColor
                            border.width: Style.dp(1)
                            clip: true

                            Row {
                                anchors.fill: parent

                                Rectangle {
                                    width: parent.width / 2
                                    height: parent.height
                                    color: hwOn ? Style.ok : "transparent"

                                    Label {
                                        anchors.centerIn: parent
                                        text: label
                                        color: hwOn ? Style.okFillDeep : Style.foreground
                                        font.pixelSize: Style.dp(11)
                                    }

                                    HoverHandler { id: _hwHover }
                                    PointerTip {
                                        text: "Input " + label
                                        delay: 200
                                        show: true
                                    }
                                }

                                Rectangle {
                                    width: Style.dp(1)
                                    height: parent.height
                                    color: Style.medColor
                                }

                                Rectangle {
                                    width: parent.width / 2 - Style.dp(1)
                                    height: parent.height
                                    color: vjOn ? Style.live : "transparent"

                                    Label {
                                        anchors.centerIn: parent
                                        text: destClaimed ? String(vjoyInput) : "—"
                                        color: vjOn ? Style.onLive : (destClaimed ? Style.foreground : Style.fgDisabled)
                                        font.pixelSize: Style.dp(11)
                                    }

                                    HoverHandler { id: _vjHover }
                                    PointerTip {
                                        text: destClaimed ? vjoyLabel : "Dest not claimed"
                                        delay: 200
                                        show: true
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
