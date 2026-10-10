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
//
// Too narrow (D-05-APPEARANCE-NARROW): when the row's other columns at
// their least width (the list's 360, the open pane's 420 plus grip) leave
// this panel less than its 360, it closes; Appearance… reopens it. A reopen
// while still too narrow stays until the next change of room (a resize,
// the pane opening): the user's click isn't undone.
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

    // Room the row leaves this panel: its width less each other shown
    // column's least width (Layout.minimumWidth, else its implicit width).
    readonly property real _room: {
        var row = parent
        if (!row)
            return 0
        var used = 0
        for (var i = 0; i < row.children.length; ++i) {
            var c = row.children[i]
            if (c === _part || !c.visible)
                continue
            var least = c.Layout.minimumWidth
            used += (least > 0 ? least : c.implicitWidth) + (row.spacing || 0)
        }
        return row.width - used
    }

    function _closeIfNarrow() {
        var row = parent
        if (!_openReady || !displayOpen || !row || !row.visible || row.width <= 0)
            return
        if (_room < Style.dp(360))
            displayOpen = false
    }

    on_RoomChanged: _closeIfNarrow()

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
