// Copyright (C) 2017 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Templates as T
import QtQuick.Controls.Universal as U

import Gremlin.Menus as Menus
import Gremlin.Style

T.ToolTip {
    id: control

    x: parent ? (parent.width - implicitWidth) / 2 : 0
    y: -implicitHeight - Style.dp(16)

    // Text wraps at the program's one tooltip width (S136); a tooltip that
    // shows something else (an image) keeps its own size.
    implicitWidth: {
        const w = Math.max(implicitBackgroundWidth + leftInset + rightInset,
                           implicitContentWidth + leftPadding + rightPadding)
        return contentItem && contentItem.wrapMode !== undefined
            ? Math.min(w, Style.tooltipMaxWidth) : w
    }
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             implicitContentHeight + topPadding + bottomPadding)

    // The program's one delay (S136). The attached ToolTip sets the shared
    // tooltip's delay to its own (0 unless set) on every show, so "no delay
    // set" (0) is turned into Style.tooltipDelayMs here, before it opens.
    // Set by code, never bound: a binding here would be overwritten by the
    // line below (Qt logs "Overwriting binding on ToolTip ... delay").
    Component.onCompleted: if (delay <= 0) delay = Style.tooltipDelayMs
    onDelayChanged: if (delay <= 0) delay = Style.tooltipDelayMs

    margins: Style.dp(8)
    padding: Style.dp(8)
    topPadding: padding - Style.dp(3)
    bottomPadding: padding - Style.dp(1)

    closePolicy: T.Popup.CloseOnEscape | T.Popup.CloseOnPressOutsideParent | T.Popup.CloseOnReleaseOutsideParent

    contentItem: Text {
        text: control.text
        font: control.font
        wrapMode: Text.Wrap
        opacity: enabled ? 1.0 : 0.2
        color: Style.menuText
    }

    // The menus' surface (Gremlin.Menus), so every popup matches.
    background: Menus.MenuSurface {}
}
