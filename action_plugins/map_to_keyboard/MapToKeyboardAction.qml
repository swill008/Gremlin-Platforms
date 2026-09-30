// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

import QtQuick.Controls.Universal as U

import Gremlin.Profile
import Gremlin.ActionPlugins
import "../../qml"
import "../../qml/helpers.js" as Helpers
import Gremlin.Style


Item {
    id: _root

    property MapToKeyboardModel action

    implicitHeight: _content.height

    ColumnLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right

        RowLayout {
            Label {
                Layout.preferredWidth: Style.dp(150)

                text: "<B>Key Combination</B>"
            }

            InputListener {
                Layout.fillWidth: true

                callback: (inputs) => { _root.action.updateInputs(inputs) }
                multipleInputs: true
                eventTypes: ["key"]

                text: Helpers.safeText(
                    _root.action.keyCombination,
                    "Record Keys"
                )
            }
        }
    }
}
