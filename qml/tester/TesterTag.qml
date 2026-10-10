// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// A small coloured label on a device row or header: kind "ok", "bad", "q"
// (not known to Gremlin) or "e"/"" (plain).

import QtQuick

import Gremlin.Style

Rectangle {
    id: _tag

    property string text: ""
    property string kind: ""

    implicitWidth: _label.implicitWidth + Style.dp(14)
    implicitHeight: _label.implicitHeight + Style.dp(2)
    radius: Style.dp(3)
    visible: text !== ""
    color: kind === "ok" ? Style.okFill
        : kind === "bad" ? Style.dangerFill
        : kind === "q" ? Style.alpha(Style.warn, 0.3)
        : Style.bgRaised

    Text {
        id: _label
        anchors.centerIn: parent
        text: _tag.text
        font.family: Style.uiFont
        font.pixelSize: Style.dp(11)
        font.bold: true
        color: _tag.kind === "ok" ? Style.okText
            : _tag.kind === "bad" ? Style.dangerTextSoft
            : _tag.kind === "q" ? Style.warn
            : Style.fgMuted
    }
}
