// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick

import Gremlin.Style

// A menu row's background: lit with an accent bar on the left while it is
// under the pointer or the keyboard. Every menu row in the program uses it.
Rectangle {
    // Under the pointer or the keyboard.
    property bool hot: false
    // The chosen value (a dropdown's current entry): the accent bar alone.
    property bool marked: false
    // Rows of values and typed values light without the bar.
    property bool bar: true

    color: hot ? Style.menuHover : Style.clear

    Rectangle {
        visible: parent.bar && (parent.hot || parent.marked)
        width: Style.menuBarW
        height: parent.height
        color: Style.menuAccent
    }
}
