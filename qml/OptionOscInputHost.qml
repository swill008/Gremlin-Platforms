// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Config
import Gremlin.Style

Item {
    id: _root

    implicitHeight: _row.implicitHeight
    implicitWidth: Style.dp(420)

    // Saved on leaving the field or Enter, and when Options closes with the
    // cursor still in a box, like every other Options text box (01 S44).
    function commit() {
        if (_combo.editText.trim() !== "" && _combo.editText !== _combo.currentText)
            _model.setHost(_combo.editText)
        if (_port.text !== _model.port)
            _model.setPort(_port.text)
    }
    Component.onDestruction: commit()

    OscInputHostModel {
        id: _model
    }

    RowLayout {
        id: _row

        anchors.fill: parent
        spacing: Style.dp(6)

        ComboBox {
            id: _combo

            Layout.fillWidth: true
            model: _model
            textRole: "name"
            editable: true
            selectTextByMouse: true
            currentIndex: _model.currentIndex
            implicitContentWidthPolicy: ComboBox.WidestText
            onActivated: (index) => { _model.currentIndex = index }
            onAccepted: () => { _model.setHost(editText) }

            Component.onCompleted: () => {
                if (_combo.contentItem && _combo.contentItem.editingFinished) {
                    _combo.contentItem.editingFinished.connect(
                        () => { _model.setHost(_combo.editText) }
                    )
                }
            }
        }

        Button {
            Layout.preferredWidth: Style.dp(36)
            Layout.preferredHeight: _combo.height
            text: "\u21bb"
            PointerTip {
                text: "Rescan this PC's IP addresses"
                delay: 400
                show: true
            }
            onClicked: () => { _model.refresh() }
        }

        Label {
            text: "Port"
        }

        TextField {
            id: _port

            Layout.preferredWidth: Style.dp(72)
            text: _model.port
            selectByMouse: true
            inputMethodHints: Qt.ImhDigitsOnly
            onEditingFinished: () => { _model.setPort(text) }
            onAccepted: () => { _model.setPort(text) }
        }
    }
}
