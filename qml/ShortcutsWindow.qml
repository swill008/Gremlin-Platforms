// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Window
import QtQuick.Controls.Universal as U
import Gremlin.Style

// Keyboard Shortcuts (Help > Keyboard Shortcuts…, Ctrl+K, 07 S135): every
// key and what it does, read from the menu bar as the window opens, then
// the mouse moves ("Mouse") and the keys no menu shows ("Keys"). Read-only:
// nothing in it runs a command. Remembers its place and size; Esc or its ×
// closes it.
//
//   ShortcutsWindow { menuBar: _menuBar; keyRows: [...]; mouseRows: [...] }
//   _shortcutsWin.openFor(_editorWin)
Window {
    id: _win

    // The Device Mapping Editor window's ThemedMenuBar, or a list of its menus.
    property var menuBar: null
    // Keys with no menu item: [{ group: "Keys", text, keys }].
    property var keyRows: []
    // The mouse moves: [{ group: "Mouse", text, keys }].
    property var mouseRows: []

    // The list inside, for tests.
    readonly property alias list: _list
    // Pinned, it stays open when you click elsewhere; unpinned, a click
    // anywhere else closes it (user 2026-10-11). The owner keeps it.
    property bool pinned: false

    title: "Keyboard Shortcuts"
    // WindowSystemMenuHint: on Windows a Tool window draws its × only with
    // the system menu (Qt's windows plugin sets WS_SYSMENU from it; only a
    // Dialog gets one from the close hint alone).
    flags: Qt.Tool | Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowCloseButtonHint
    // No width/height binding: ToolWindowMemory sets the size once when
    // the window opens (saved size, or its default fitted to the screen).
    minimumWidth: Style.fitWidth(Style.dp(240), Screen)
    minimumHeight: Style.fitHeight(Style.dp(160), Screen)
    color: Style.background
    U.Universal.theme: Style.theme

    ToolWindowMemory {
        host: _win
        name: "device-mapping-editor-shortcuts"
        defaultWidth: Style.fitWidth(Style.dp(420), Screen)
        defaultHeight: Style.fitHeight(Style.dp(560), Screen)
    }

    // Shows it over the Device Mapping Editor window with the menus read again, the
    // search box ready, and brings it to the front.
    function openFor(parentWindow) {
        if (!visible && parentWindow)
            transientParent = parentWindow
        _list.refresh()
        show()
        raise()
        requestActivate()
        _list.focusSearch()
    }

    Shortcut {
        sequence: "Esc"
        onActivated: _win.close()
    }

    // A click outside it (the window loses focus) closes it unless pinned.
    onActiveChanged: {
        if (!active && visible && !pinned)
            close()
    }

    Label {
        id: _pin
        objectName: "shortcutsPin"
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: Style.dp(10)
        z: 2
        font.family: Style.iconFont
        font.pixelSize: Style.dp(14)
        text: _win.pinned ? "" : ""
        color: _win.pinned ? Style.accent : (_pinArea.containsMouse ? Style.fg : Style.fgMuted)
        MouseArea {
            id: _pinArea
            anchors.fill: parent
            anchors.margins: -Style.dp(4)
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: _win.pinned = !_win.pinned
        }
        ToolTip.visible: _pinArea.containsMouse
        ToolTip.text: _win.pinned ? "Unpin: closes when you click elsewhere" : "Pin: stays open when you click elsewhere"
    }

    ShortcutList {
        id: _list
        objectName: "shortcutsWindowList"
        anchors.fill: parent
        anchors.margins: Style.dp(8)
        anchors.topMargin: _pin.height + Style.dp(14)
        menuBar: _win.menuBar
        // Each row carries its group: Mouse, then Keys (glossary).
        mouseRows: (_win.mouseRows || []).concat(_win.keyRows || [])
    }
}
