// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Templates as T

import Gremlin.Style
import "commands.js" as Commands

// A menu row in the program's style: lit with an accent bar under the
// pointer, its shortcut on the right. Given a command id it takes its name,
// shortcut, check mark and availability from the command list (commands.js).
T.MenuItem {
    id: control

    // A program-wide command; when set it supplies text, hint and enabled.
    property string command: ""
    // Shown on the right, e.g. a shortcut.
    property string hint: ""
    // Red text, for deletes.
    property bool danger: false
    // Wanted in the menu at all (ThemedMenu hides the row when false or when
    // it cannot be used).
    property bool shown: true

    // Takes the command's current state. ThemedMenu calls this as it opens.
    function refresh() {
        if (!command.length)
            return
        text = Commands.textOf(command)
        hint = Commands.shortcutOf(command)
        checkable = Commands.isCheckable(command)
        checked = Commands.isChecked(command)
        shown = Commands.isVisible(command)
        enabled = Commands.isEnabled(command)
    }

    Component.onCompleted: refresh()
    onTriggered: {
        if (command.length)
            Commands.trigger(command)
    }

    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             implicitContentHeight + topPadding + bottomPadding)

    leftPadding: Style.dp(10)
    rightPadding: Style.dp(8)
    topPadding: 0
    bottomPadding: 0
    font.pixelSize: Style.menuTextPx

    contentItem: Item {
        implicitWidth: _label.implicitWidth + (_right.text.length ? _right.implicitWidth + Style.dp(24) : Style.dp(12))
        implicitHeight: Style.menuRowH
        Text {
            id: _label
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width - (_right.text.length ? _right.implicitWidth + Style.dp(12) : 0)
            text: control.text
            font: control.font
            color: !control.enabled ? Style.menuTextOff : (control.danger ? Style.menuDanger : Style.menuText)
            elide: Text.ElideRight
        }
        // The shortcut, a check mark or a submenu's arrow.
        Text {
            id: _right
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: parent.right
            text: control.subMenu ? "›" : (control.checkable ? (control.checked ? "✓" : "") : control.hint)
            font.pixelSize: control.subMenu || control.checkable ? Style.menuTextPx + Style.dp(1) : Style.menuTextPx - Style.dp(1)
            color: control.checkable && !control.subMenu ? Style.menuAccent : Style.menuHint
        }
    }

    // Drawn by the row above; MenuItem's own slots stay empty.
    arrow: Item {}
    indicator: Item {}

    background: MenuRowBackground {
        implicitWidth: Style.dp(160)
        implicitHeight: Style.menuRowH
        hot: control.enabled && (control.highlighted || control.hovered)
    }

    HoverHandler {
        cursorShape: control.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
    }
}
