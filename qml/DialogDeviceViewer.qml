// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Style

ApplicationWindow {
    font.pixelSize: Style.fontSize
    id: _deviceViewer

    // ToolWindowMemory sets the saved or default size when the window opens.
    width: 1400
    height: 800
    minimumWidth: Style.dp(900)
    minimumHeight: Style.dp(500)

    color: Style.background
    U.Universal.theme: Style.theme

    title: "Device Viewer"

    ToolWindowMemory {
        host: _deviceViewer
        name: "device-viewer"
        defaultWidth: Style.dp(1400)
        defaultHeight: Style.dp(800)
    }

    Shortcut { sequence: "Esc"; onActivated: {} }
    Shortcut { sequence: "Return"; onActivated: {} }
    Shortcut { sequence: "Enter"; onActivated: {} }

    property string hardwareTip: ""

    DeviceNames { id: _names }

    function displayName(guid, hardwareName) {
        if (!_names) {
            return hardwareName
        }
        return _names.display(guid, hardwareName)
    }

    Connections {
        target: _deviceViewer

        function onClosing() {
            _stateDisplay.children.forEach((child) => {
                child.destroy()
            })
            _deviceData.destroy()
            backend.resumeInputHighlighting()
        }
    }

    Component.onCompleted: () => {
        backend.pauseInputHighlighting()
    }

    DeviceListModel {
        id: _deviceData

        deviceType: "all"
    }

    function create_widget(qml_path, guid, name) {
        let component = Qt.createComponent(Qt.resolvedUrl(qml_path))
        if (component.status == Component.Ready) {
            var widget = component.createObject(
                _stateDisplay,
                {
                    deviceGuid: guid,
                    title: name,
                    "Layout.fillWidth": true
                }
            );
        }

        return widget
    }

    Popup {
        id: _hardwareTip

        visible: _deviceViewer.hardwareTip.length > 0
        modal: false
        focus: false
        padding: Style.dp(8)
        closePolicy: Popup.NoAutoClose
        parent: Overlay.overlay

        background: Rectangle {
            color: Style.background
            border.color: Style.accent
            border.width: Style.dp(1)
            radius: Style.dp(3)
        }

        contentItem: Label {
            text: _deviceViewer.hardwareTip
            color: Style.foreground
            font.pixelSize: Style.dp(15)
        }
    }

    RowLayout {
        id: _root

        anchors.fill: parent
        anchors.bottomMargin: Style.dp(58)

        ScrollView {
            id: _deviceScroll
            Layout.alignment: Qt.AlignTop
            Layout.rightMargin: Style.dp(10)
            Layout.minimumWidth: Style.dp(360)
            Layout.preferredWidth: Style.dp(420)
            Layout.maximumWidth: Style.dp(560)
            Layout.fillHeight: true

            ColumnLayout {
                width: Math.max(_deviceScroll.availableWidth, Style.dp(360))

                Repeater {
                    model: _deviceData
                    delegate: _deviceDelegate
                }
            }
        }

        ScrollView  {
            id: _dynamicScroll

            Layout.fillWidth: true
            Layout.fillHeight: true

            Component.onCompleted: () => {
                _dynamicScroll.contentItem.boundsMovement = Flickable.StopAtBounds
                _dynamicScroll.contentItem.boundsBehavior = Flickable.StopAtBounds
            }

            ColumnLayout {
                id: _stateDisplay

                anchors.left: parent.left
                anchors.right: parent.right
            }
        }
    }

    Component {
        id: _deviceDelegate

        ColumnLayout {
            id: _delegateContent

            required property int index
            required property string name
            required property string guid

            readonly property string shownName: _deviceViewer.displayName(guid, name)
            readonly property bool hasFriendlyName: shownName !== name
            Layout.fillWidth: true

            property var widget_btn_hat
            property var widget_axis_temp
            property var widget_axis_cur

            RowLayout {
                Layout.fillWidth: true

                IconButton {
                    id: _foldButton

                    checkable: true
                    checked: false
                    text: checked ? bsi.icons.folded : bsi.icons.unfolded
                }

                Label {
                    id: _nameLabel
                    Layout.fillWidth: true
                    text: shownName
                    color: Style.foreground
                    font.pixelSize: Style.dp(16)
                    font.family: "Segoe UI"
                    wrapMode: Text.WrapAnywhere
                    maximumLineCount: 3

                    HoverHandler {
                        id: _hover
                        onHoveredChanged: {
                            if (hovered && hasFriendlyName) {
                                _deviceViewer.hardwareTip = name
                                var pos = _nameLabel.mapToItem(Overlay.overlay, 8, _nameLabel.height + 4)
                                _hardwareTip.x = pos.x
                                _hardwareTip.y = pos.y
                            } else if (_deviceViewer.hardwareTip === name) {
                                _deviceViewer.hardwareTip = ""
                            }
                        }
                    }
                }
            }

            ColumnLayout {
                visible: _foldButton.checked
                Layout.fillWidth: true
                Layout.leftMargin: _foldButton.width

                Switch {
                    text: "Axes - Temporal"

                    onClicked: () => {
                        if(checked) {
                            widget_axis_temp = create_widget(
                                "AxesStateSeries.qml",
                                guid,
                                shownName
                            )
                        } else {
                            widget_axis_temp.destroy()
                        }
                    }
                }
                Switch {
                    text: "Axes - Current"

                    onClicked: () => {
                        if(checked) {
                            widget_axis_cur = create_widget(
                                "AxesStateCurrent.qml",
                                guid,
                                shownName
                            )
                        } else {
                            widget_axis_cur.destroy()
                        }
                    }
                }
                Switch {
                    text: "Buttons & Hats"

                    onClicked: () => {
                        if(checked) {
                            widget_btn_hat = create_widget(
                                "ButtonState.qml",
                                guid,
                                shownName
                            )
                        } else {
                            widget_btn_hat.destroy()
                        }
                    }
                }
            }
        }
    }

    DebugFileLine {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
    }
}
