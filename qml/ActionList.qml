// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

import QtQuick.Controls.Universal as U

import Gremlin.Profile
import Gremlin.Style


Item {
    id: idRoot

    property ProfileModel profileModel

    RowLayout {
        anchors.fill: parent

        JGText {
            text: "Action"
            width: Style.dp(300)
        }
        ComboBox {
            id: idActionLlist
            model: backend.action_list
        }
        Button {
            text: "Add"
            font.pixelSize: Style.dp(13)
        }
    }

}
