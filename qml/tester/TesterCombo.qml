// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// A drop-down picker: shows the current choice; a click lists the choices
// below it (drawn over what follows; the parent must not clip).

import QtQuick

import Gremlin.Style

Rectangle {
    id: _combo

    // Choice labels, in order.
    property var choices: []
    property int currentIndex: 0
    property bool open: false
    signal picked(int index)

    implicitWidth: _shown.implicitWidth + Style.dp(40)
    implicitHeight: _shown.implicitHeight + Style.dp(12)
    z: open ? 100 : 0
    radius: Style.dp(3)
    color: Style.bgWell
    border.color: open ? Style.accent : Style.lineStrong

    Accessible.role: Accessible.ComboBox
    Accessible.name: _shown.text

    Text {
        id: _shown
        objectName: _combo.objectName + "Text"
        anchors.left: parent.left
        anchors.leftMargin: Style.dp(10)
        anchors.verticalCenter: parent.verticalCenter
        text: _combo.choices[_combo.currentIndex] || ""
        font.family: Style.uiFont
        font.pixelSize: Style.dp(13)
        color: Style.fg
    }
    Text {
        anchors.right: parent.right
        anchors.rightMargin: Style.dp(10)
        anchors.verticalCenter: parent.verticalCenter
        text: "⌄"
        font.family: Style.uiFont
        font.pixelSize: Style.dp(13)
        color: Style.fgMuted
    }
    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: _combo.open = !_combo.open
    }

    Rectangle {
        objectName: "comboList"
        visible: _combo.open
        y: parent.height + Style.dp(2)
        width: Math.max(parent.width, Style.dp(260))
        height: _list.implicitHeight
        color: Style.menuBg
        border.color: Style.menuLine
        radius: Style.dp(3)

        Column {
            id: _list
            width: parent.width
            padding: Style.dp(3)
            Repeater {
                model: _combo.choices
                delegate: Rectangle {
                    id: _choice
                    required property var modelData
                    required property int index
                    objectName: "comboChoice_" + index
                    width: _list.width - 2 * _list.padding
                    height: _choiceText.implicitHeight + Style.dp(10)
                    radius: Style.dp(3)
                    color: _choiceArea.containsMouse ? Style.menuHover
                        : index === _combo.currentIndex ? Style.bgSelected : Style.clear
                    Text {
                        id: _choiceText
                        anchors.left: parent.left
                        anchors.leftMargin: Style.dp(10)
                        anchors.verticalCenter: parent.verticalCenter
                        text: _choice.modelData
                        font.family: Style.uiFont
                        font.pixelSize: Style.dp(13)
                        color: Style.menuText
                    }
                    MouseArea {
                        id: _choiceArea
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: {
                            _combo.open = false
                            _combo.picked(_choice.index)
                        }
                    }
                }
            }
        }
    }
}
