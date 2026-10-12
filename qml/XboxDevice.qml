// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts

import Gremlin.Device
import Gremlin.Style
import Gremlin.UI

// The Xbox output's Output View: the ViGEmBus check, the live pad of each
// device that drives it (one card per device, in a section that folds and
// remembers it), then who targets each control. One scroll for all of it.
Item {
    id: _root

    // The pad cards' section, open unless the user folded it.
    property bool padsOpen: true

    XboxDeviceModel {
        id: _model
    }

    XboxViewerDeviceModel {
        id: _devices
    }

    WindowPlacement { id: _place }

    function _loadPadsOpen() {
        var state = {}
        try {
            state = JSON.parse(_place.toolRowState("xboxOutput")) || {}
        } catch (e) {
            state = {}
        }
        padsOpen = state.padsOpen !== false
    }

    function setPadsOpen(open) {
        padsOpen = open
        _place.saveToolRowState("xboxOutput", JSON.stringify({ padsOpen: open }))
    }

    function pairTitle(guid, name) {
        return name && name.length ? name : guid
    }

    Component.onCompleted: {
        _loadPadsOpen()
        _devices.reload()
    }

    ScrollView {
        id: _scroll
        objectName: "xboxOutputScroll"
        anchors.fill: parent
        anchors.margins: Style.dp(10)
        contentWidth: availableWidth
        ScrollBar.vertical.policy: ScrollBar.AlwaysOn

        Component.onCompleted: {
            _scroll.contentItem.boundsMovement = Flickable.StopAtBounds
            _scroll.contentItem.boundsBehavior = Flickable.StopAtBounds
        }

        ColumnLayout {
            id: _column
            width: _scroll.availableWidth - Style.dp(16)
            spacing: Style.dp(8)

            XboxDriverCheck {
                Layout.fillWidth: true
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Style.dp(8)

                Label {
                    text: _model ? _model.moduleName : "Xbox 360 Controller"
                    font.bold: true
                    font.pixelSize: Style.dp(16)
                }

                Label {
                    text: "Pad " + (_model ? _model.padId : 1)
                    opacity: 0.7
                }

                Item { Layout.fillWidth: true }
            }

            Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: "This is the Xbox output module: every control goes straight to the Xbox driver. Map hardware, Keyboard, OSC or Logical Device inputs to it with the Map to Xbox action. Rows show who already targets each control."
                opacity: 0.7
                font.pixelSize: Style.dp(12)
            }

            // The pad cards' section heading: click to fold or open it.
            AbstractButton {
                id: _padsHeading
                objectName: "xboxPadsHeading"
                Layout.fillWidth: true
                implicitHeight: _headRow.implicitHeight + Style.dp(8)
                hoverEnabled: true
                Accessible.name: (_root.padsOpen ? "Fold " : "Open ") + "Live pads"
                onClicked: _root.setPadsOpen(!_root.padsOpen)

                background: Rectangle {
                    radius: Style.dp(3)
                    color: _padsHeading.hovered ? Style.bgWell : "transparent"
                }

                contentItem: RowLayout {
                    id: _headRow
                    spacing: Style.dp(6)

                    Label {
                        text: _root.padsOpen ? "▾" : "▸"
                        font.pixelSize: Style.dp(13)
                    }
                    Label {
                        text: "Live pads"
                        font.bold: true
                        font.pixelSize: Style.dp(13)
                    }
                    Label {
                        text: _devices ? "(" + _devices.count + ")" : ""
                        opacity: 0.55
                        font.pixelSize: Style.dp(11)
                    }
                    Item { Layout.fillWidth: true }
                }
            }

            JGText {
                visible: _root.padsOpen && (!_devices || _devices.count === 0)
                text: "No Map to Xbox actions on connected devices."
                opacity: 0.65
            }

            Repeater {
                model: _root.padsOpen ? _devices : null
                delegate: XboxViewerCard {
                    required property string guid
                    required property string name
                    // The card's own property, filled from the row.
                    required pairLabel

                    Layout.fillWidth: true
                    deviceGuid: guid
                    title: _root.pairTitle(guid, name)
                }
            }

            Repeater {
                id: _rows
                model: _model

                delegate: Rectangle {
                    required property string label
                    required property string kind
                    required property string incoming
                    required property int index

                    Layout.fillWidth: true
                    implicitHeight: _row.implicitHeight + Style.dp(12)
                    radius: Style.dp(4)
                    color: Style.background
                    border.color: incoming.length ? Style.accent : Style.lowColor
                    border.width: Style.dp(1)

                    ColumnLayout {
                        id: _row
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.margins: Style.dp(8)
                        spacing: Style.dp(2)

                        RowLayout {
                            Layout.fillWidth: true

                            Label {
                                text: label
                                font.bold: true
                                font.pixelSize: Style.dp(13)
                            }

                            Item { Layout.fillWidth: true }

                            Label {
                                text: kind
                                opacity: 0.55
                                font.pixelSize: Style.dp(11)
                            }
                        }

                        Label {
                            visible: incoming.length > 0
                            text: incoming
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                            color: Style.accent
                            font.pixelSize: Style.dp(11)
                        }

                        Label {
                            visible: incoming.length === 0
                            text: "No actions"
                            opacity: 0.45
                            font.pixelSize: Style.dp(11)
                        }
                    }
                }
            }
        }
    }
}
