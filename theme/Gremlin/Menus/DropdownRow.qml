// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Templates as T

import Gremlin.Style

// One entry in a dropdown list, in the menus' style: lit with an accent bar
// under the pointer or the keyboard; the chosen entry is bold with the bar.
// Hidden while the list's search box has text it does not contain.
T.ItemDelegate {
    id: control

    required property int index
    // The ComboBox this row belongs to.
    property var combo: null
    // function(index) -> the row's text, for lists that show more than
    // the ComboBox's text (the default).
    property var labelFor: null
    // The popup (DropdownPopup) when it has a search box.
    property var list: combo ? combo.popup : null
    readonly property bool current: !!combo && combo.currentIndex === index
    readonly property bool matches: {
        var f = list && list.filter !== undefined ? String(list.filter).toLowerCase() : ""
        return !f.length || String(text).toLowerCase().indexOf(f) >= 0
    }
    readonly property bool hot: !!combo && (list && list.keyIndex !== undefined && list.keyIndex >= 0
                                            ? list.keyIndex === index : combo.highlightedIndex === index)

    width: ListView.view ? ListView.view.width : implicitWidth
    text: !combo ? "" : (typeof labelFor === "function" ? labelFor(index) : combo.textAt(index))
    visible: matches
    height: matches ? implicitHeight : 0
    highlighted: hot
    hoverEnabled: combo ? combo.hoverEnabled : true

    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             implicitContentHeight + topPadding + bottomPadding)

    leftPadding: Style.dp(10)
    rightPadding: Style.dp(8)
    topPadding: Style.dp(3)
    bottomPadding: Style.dp(3)
    font.pixelSize: combo ? combo.font.pixelSize : Style.menuTextPx

    contentItem: Text {
        text: control.text
        font.pixelSize: control.font.pixelSize
        font.bold: control.current
        color: control.enabled ? Style.menuText : Style.menuTextOff
        elide: Text.ElideRight
        verticalAlignment: Text.AlignVCenter
    }

    background: MenuRowBackground {
        implicitHeight: Style.menuRowH
        hot: control.hot || control.hovered
        marked: control.current
    }

    HoverHandler {
        cursorShape: Qt.PointingHandCursor
    }
}
