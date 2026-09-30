// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

import QtQuick.Controls.Universal as U
import Gremlin.Style


Item {
    implicitHeight: _layout.height
    implicitWidth: _layout.width

    property alias pressChecked: _press.checked
    property alias releaseChecked: _release.checked

    RowLayout {
        id: _layout

        spacing: Style.dp(4)

        JGText {
            id: _description

            text: "Activation"
            font.pixelSize: Style.dp(13)
        }

        CompactSwitch {
            id: _press

            text: "Press"
            font: _description.font
        }
        CompactSwitch {
            id: _release

            text: "Release"
            font: _description.font
        }
    }
}
