// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Device
import Gremlin.Style

Item {
    id: _root

    implicitHeight: _row.implicitHeight
    implicitWidth: Style.dp(420)

    ModuleListModel { id: _modules }

    RowLayout {
        id: _row
        anchors.fill: parent
        spacing: Style.dp(8)

        Button {
            text: "Reset all card sizes"
            onClicked: _modules.resetAllCardSizes()
        }
    }
}
