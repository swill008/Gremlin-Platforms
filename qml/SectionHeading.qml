// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// 01 S143 (D-01-SHARED-PIECES): one section heading style inside windows,
// a bold title with a thin line under it.

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style

ColumnLayout {
    id: _root

    property alias text: _title.text

    spacing: Style.dp(4)

    Label {
        id: _title
        objectName: "sectionHeadingText"
        Layout.fillWidth: true
        elide: Text.ElideRight
        font.pixelSize: Style.dp(15)
        font.bold: true
        color: Style.fgStrong
    }

    Rectangle {
        objectName: "sectionHeadingRule"
        Layout.fillWidth: true
        Layout.preferredHeight: 1
        color: Style.line
    }
}
