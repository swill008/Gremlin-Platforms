// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// A device's small picture: a 40 x 40 frame (as the HidHide rows) with the
// picture fitted inside, or the given icon glyph when it has none.

import QtQuick
import Gremlin.Style

Rectangle {
    id: _thumb
    // The picture's URL ("" for none) and the glyph shown without one.
    property string source: ""
    property string glyph: ""

    readonly property bool showsPicture: _pic.status === Image.Ready

    implicitWidth: Style.dp(40)
    implicitHeight: Style.dp(40)
    radius: Style.dp(3)
    color: Style.bgWell
    border.color: Style.line

    Image {
        id: _pic
        objectName: "deviceThumbImage"
        anchors.fill: parent
        anchors.margins: Style.dp(2)
        source: _thumb.source
        visible: _thumb.showsPicture
        fillMode: Image.PreserveAspectFit
        asynchronous: true
        cache: true
        sourceSize.width: Style.dp(80)
        sourceSize.height: Style.dp(80)
    }
    Text {
        objectName: "deviceThumbGlyph"
        anchors.centerIn: parent
        visible: !_thumb.showsPicture
        text: _thumb.glyph
        font.family: Style.iconFont
        font.pixelSize: Style.dp(17)
        color: Style.fgSoft
    }
}
