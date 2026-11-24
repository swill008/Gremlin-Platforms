// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Device
import Gremlin.Style
import Gremlin.UI

Item {
    id: _root

    implicitHeight: _row.implicitHeight
    implicitWidth: Style.dp(420)

    // Only the reset; the card list itself lives on Home.
    // Made by ModelFactory (PYSIDE-1407); it lives as long as this row.
    readonly property CardSizes _sizes: ModelFactory.create("CardSizes", _root)

    RowLayout {
        id: _row
        anchors.fill: parent
        spacing: Style.dp(8)

        Button {
            text: "Reset All Card Sizes"
            onClicked: _sizes.resetAll()
        }
    }
}
