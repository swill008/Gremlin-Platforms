// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Templates as T
import QtQuick.Window

import Gremlin.Style

// A menu (a menu bar's, or a submenu) in the program's style. Each time it
// opens it shows only what can be used now: rows that are disabled, not
// shown or whose command is unavailable are hidden with no gap left, as are
// submenus with nothing in them and separators with nothing on one side.
// It is as wide as its widest row.
T.Menu {
    id: control

    // Hide what cannot be used (true), or grey it out (false).
    property bool compact: true
    // Called just before the rows are checked, to fill dynamic lists.
    property var beforeShow: null
    // Rows showing after the last compactNow(). (A closed menu's rows always
    // report visible false, so a parent menu asks this instead.)
    property int shownCount: 0

    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             implicitContentHeight + topPadding + bottomPadding)

    margins: 0
    padding: Style.menuPad
    overlap: Style.dp(2)
    font.pixelSize: Style.menuTextPx

    delegate: ThemedMenuItem {}

    contentItem: ListView {
        implicitHeight: contentHeight
        model: control.contentModel
        interactive: Window.window
                     ? contentHeight + control.topPadding + control.bottomPadding > control.height
                     : false
        clip: true
        currentIndex: control.currentIndex
    }

    background: MenuSurface {
        implicitWidth: Style.dp(160)
        implicitHeight: Style.menuRowH
    }

    function _show(item, on) {
        item.visible = on
        item.height = on ? item.implicitHeight : 0
    }

    // Whether any row shows (after compactNow()).
    function hasShown() {
        return shownCount > 0
    }

    // Plain text of the rows showing, for tests: submenus end in " >".
    function describe() {
        var out = []
        for (var i = 0; i < count; i++) {
            var item = itemAt(i)
            if (!item || !item.visible)
                continue
            if (item.text === undefined)
                out.push("-")
            else
                out.push(item.text + (item.subMenu ? " >" : "") + (item.hint ? " (" + item.hint + ")" : ""))
        }
        return out
    }

    // Brings every row up to date and hides what cannot be used.
    function compactNow() {
        if (typeof beforeShow === "function")
            beforeShow()
        var pendingSep = null
        var seenItem = false
        var widest = Style.dp(160)
        var shown = 0
        for (var i = 0; i < count; i++) {
            var item = itemAt(i)
            if (!item)
                continue
            // A separator has no text.
            if (item.text === undefined) {
                _show(item, false)
                if (seenItem)
                    pendingSep = item
                continue
            }
            if (typeof item.refresh === "function")
                item.refresh()
            var on
            if (item.subMenu) {
                if (typeof item.subMenu.compactNow === "function")
                    item.subMenu.compactNow()
                on = item.subMenu.enabled && (typeof item.subMenu.hasShown !== "function" || item.subMenu.hasShown())
            } else {
                on = item.shown !== false && (item.enabled || !compact)
            }
            _show(item, on)
            if (!on)
                continue
            widest = Math.max(widest, item.implicitWidth)
            shown++
            if (pendingSep) {
                _show(pendingSep, true)
                pendingSep = null
            }
            seenItem = true
        }
        width = widest + leftPadding + rightPadding
        shownCount = shown
    }

    onAboutToShow: compactNow()
}
