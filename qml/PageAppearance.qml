// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style
import Gremlin.UI

// The Appearance part shared by the four list pages (Configuration,
// Logical Device, Keyboard, OSC; to-do 91, PB1 from the Logical Device
// page): the page's ListAppearancePanel (05 S125, AP2), whether it is shown,
// remembered as displayPanelOpen(pageKey, "page"), and the page-bar button
// Appearance… / Hide Appearance (01 S58a). The page puts it where the panel
// goes, binds its ControlTree's appearance properties to this item's
// properties of the same names and re-exposes pageBar.
ListAppearancePanel {
    id: _part

    // objectName of the page-bar button, e.g. "logicalAppearanceButton".
    property string buttonName: ""
    property bool displayOpen: false
    property bool _openReady: false

    visible: displayOpen
    Layout.preferredWidth: Style.dp(360)
    Layout.maximumWidth: Style.dp(360)
    Layout.fillHeight: true

    // Hiding asks about unsaved changes, like the panel's ×.
    function toggleAppearance() {
        if (displayOpen)
            requestCloseDisplay()
        else
            displayOpen = true
    }

    function requestCloseDisplay() { requestClose() }

    // The page's own controls on the bar under the toolbar (01 S58a).
    property Component pageBar: Component {
        RowLayout {
            Layout.fillWidth: true
            Item { Layout.fillWidth: true }
            Button {
                objectName: _part.buttonName
                text: _part.displayOpen ? "Hide Appearance" : "Appearance…"
                onClicked: _part.toggleAppearance()
            }
        }
    }

    onClosed: displayOpen = false
    onDisplayOpenChanged: {
        if (_openReady)
            _openPlace.setDisplayPanelOpen(pageKey, "page", displayOpen)
    }

    WindowPlacement { id: _openPlace }

    Component.onCompleted: {
        load()
        displayOpen = _openPlace.displayPanelOpen(pageKey, "page")
        _openReady = true
    }
}
