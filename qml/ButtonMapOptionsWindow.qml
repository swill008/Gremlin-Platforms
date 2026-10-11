// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Window
import QtQuick.Controls.Universal as U
import Gremlin.Style

// Button Map Options (Edit > Button Map Options…, 07 S135): the Button
// Map's settings (RigOptionsPanel) in a small window of their own. Changes
// apply and are kept at once, as in the panel. Remembers its place and
// size; Esc closes it.
//
//   ButtonMapOptionsWindow { id: _optionsWin; opts: _opts
//       onColorRequested: (key, hex) => openColorField("printAreaColor", hex, null) }
//   _optionsWin.openFor(_buttonMap)
Window {
    id: _win

    // The Button Map window's ButtonMapOptions.
    property var opts: null
    // A color swatch was clicked: the Button Map window opens its color
    // picker (it lives in that window, so no anchor from this one).
    signal colorRequested(string key, string hex)

    title: "Button Map Options"
    flags: Qt.Tool | Qt.WindowTitleHint | Qt.WindowCloseButtonHint
    // No width/height binding: ToolWindowMemory sets the size once when
    // the window opens (saved size, or the panel's wanted size fitted to
    // the screen).
    minimumWidth: Style.fitWidth(Style.dp(320), Screen)
    minimumHeight: Style.fitHeight(Style.dp(120), Screen)
    color: Style.background
    U.Universal.theme: Style.theme

    ToolWindowMemory {
        host: _win
        name: "button-map-options"
        defaultWidth: Style.fitWidth(_panel.wantedW + 2 * Style.dp(8), Screen)
        defaultHeight: Style.fitHeight(Math.max(Style.dp(360), _panel.wanted + 2 * Style.dp(8)), Screen)
    }

    // Shows it over the Button Map window and brings it to the front.
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

    RigOptionsPanel {
        id: _panel
        objectName: "buttonMapOptionsPanel"
        anchors.fill: parent
        anchors.margins: Style.dp(8)
        opts: _win.opts
        onColorRequested: (key, hex, anchor) => _win.colorRequested(key, hex)
    }
}
