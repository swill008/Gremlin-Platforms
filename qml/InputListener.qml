// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import QtQml.StateMachine as DSM

import Gremlin.Util
import Gremlin.Compact as Compact
import Gremlin.Style
import Gremlin.UI


Item {
    id: _root

    // Passed on to the listener (set only from QML, notified only on change).
    property var eventTypes: []
    property bool multipleInputs: false
    property alias text: _name.text
    property var callback
    signal listenFinished()

    implicitWidth: _button.implicitWidth
    implicitHeight: _button.implicitHeight

    // Made by ModelFactory (PySide6 never frees QML-made Python objects,
    // PYSIDE-1407); freed with this item.
    readonly property InputListenerModel _listener: ModelFactory.create("InputListenerModel", _root, {})
    Binding { target: _listener; property: "eventTypes"; value: _root.eventTypes }
    Binding { target: _listener; property: "multipleInputs"; value: _root.multipleInputs }
    Connections {
        target: _listener

        function onListeningTerminated(inputs) {
            if (_root.callback) {
                _root.callback(inputs)
            }
            _root.listenFinished()
        }
    }

    DSM.StateMachine {
        id: _stateMachine

        initialState: disabled
        running: true

        DSM.State {
            id: disabled

            DSM.SignalTransition {
                targetState: enabled
                signal: _popup.aboutToShow
            }

            onEntered: function() {
                if (_listener) {
                    _listener.enabled = false
                }
                _popup.close()
            }
        }

        DSM.State {
            id: enabled

            DSM.SignalTransition {
                targetState: disabled
                signal: _popup.closed
            }

            DSM.SignalTransition {
                targetState: disabled
                signal: _root.listenFinished
            }

            onEntered: function() {
                if (_listener) {
                    _listener.enabled = true
                }
            }
        }
    }

    RowLayout {
        id: _button

        anchors.left: parent.left
        anchors.right: parent.right

        Compact.RecordButton {
            onClicked: () => { _popup.open() }
        }

        Label {
            id: _name

            Layout.fillWidth: true
            text: "Record Inputs"

            ToolTip {
                text: _name.text
                visible: _hoverHandler.hovered
                x: _hoverHandler.point.position.x - width / 2
                y: _hoverHandler.point.position.y - height - Style.dp(8)
            }

            HoverHandler {
                id: _hoverHandler
                acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
            }
        }
    }

    Popup {
        id: _popup

        parent: Overlay.overlay

        anchors.centerIn: Overlay.overlay

        dim: true
        modal: true
        focus: true
        closePolicy: Popup.NoAutoClose

        ColumnLayout {
            id: _layout
            anchors.fill: parent

            RowLayout {
                Label {
                    text: "Waiting for user input. Hold ESC to abort."
                }
                Label {
                    text: _listener ? _listener.currentInput : ""
                }
            }
        }
    }
}
