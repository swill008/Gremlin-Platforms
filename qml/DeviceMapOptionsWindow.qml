// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Window
import QtQuick.Controls.Universal as U
import Gremlin.Style

// Device Map Options (Edit > Device Map Options…, 07 S135): the Button
// Map's settings (RigOptionsPanel) in a small window of their own. Changes
// apply and are kept at once, as in the panel. Remembers its place and
// size; Esc or its × closes it. Unpinned, a click elsewhere closes it; the
// pin is kept for next time (D-FIXLIST-B1).
//
//   DeviceMapOptionsWindow { id: _optionsWin; opts: _opts
//       onColorRequested: (key, hex) => openColorField("printAreaColor", hex, null) }
//   _optionsWin.openFor(_editorWin)
Window {
    id: _win

    // The Device Mapping Editor window's DeviceMapOptions.
    property var opts: null
    // A color swatch was clicked: the Device Mapping Editor window opens its color
    // picker (it lives in that window, so no anchor from this one).
    signal colorRequested(string key, string hex)
    // Pinned, it stays open when you click elsewhere; unpinned, a click
    // anywhere else closes it. Kept with the panels (the "options" entry;
    // Reset Panels keeps it).
    property bool pinned: false
    property bool _pinRead: false

    function _readPin() {
        if (!opts || _pinRead)
            return
        pinned = !!opts.sidePanelState("options").pinned
        _pinRead = true
    }
    onOptsChanged: _readPin()
    Component.onCompleted: _readPin()
    onPinnedChanged: {
        if (opts && _pinRead)
            opts.setSidePanelState("options", { pinned: pinned })
    }

    title: "Device Map Options"
    // WindowSystemMenuHint: on Windows a Tool window draws its × only with
    // the system menu (Qt's windows plugin sets WS_SYSMENU from it; only a
    // Dialog gets one from the close hint alone).
    flags: Qt.Tool | Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowCloseButtonHint
    // No width/height binding: ToolWindowMemory sets the size once when
    // the window opens (saved size, or the panel's wanted size fitted to
    // the screen).
    minimumWidth: Style.fitWidth(Style.dp(320), Screen)
    minimumHeight: Style.fitHeight(Style.dp(120), Screen)
    color: Style.background
    U.Universal.theme: Style.theme

    ToolWindowMemory {
        host: _win
        name: "device-map-options"
        defaultWidth: Style.fitWidth(_panel.wantedW + 2 * Style.dp(8), Screen)
        defaultHeight: Style.fitHeight(Math.max(Style.dp(360), _panel.wanted + 2 * Style.dp(8)), Screen)
    }

    // Shows it over the Device Mapping Editor window and brings it to the front.
    function openFor(parentWindow) {
        if (!visible && parentWindow)
            transientParent = parentWindow
        show()
        raise()
        requestActivate()
    }

    Shortcut {
        sequence: "Esc"
        onActivated: _win.close()
    }

    // A click outside it (the window loses focus) closes it unless pinned.
    // As a transient child of the Device Mapping Editor window its `active` stays true
    // when the Device Mapping Editor takes the focus back, so its own focus decides as
    // well (as the Device Mapping Editor's keysHere does; checked off-screen).
    function _closeIfAway() {
        if (visible && !pinned && !(active && contentItem.activeFocus))
            close()
    }
    onActiveChanged: if (!active) _closeIfAway()
    Connections {
        target: _win.contentItem
        function onActiveFocusChanged() {
            if (!_win.contentItem.activeFocus)
                _win._closeIfAway()
        }
    }

    Label {
        id: _pin
        objectName: "optionsPin"
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: Style.dp(10)
        z: 2
        font.family: Style.iconFont
        font.pixelSize: Style.dp(14)
        // pin-fill when pinned, pin-angle when not.
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

    RigOptionsPanel {
        id: _panel
        objectName: "deviceMapOptionsPanel"
        anchors.fill: parent
        anchors.margins: Style.dp(8)
        anchors.topMargin: _pin.height + Style.dp(14)
        opts: _win.opts
        onColorRequested: (key, hex, anchor) => _win.colorRequested(key, hex)
    }
}
