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
import Gremlin.Style


Item {
    id: _root

    property ReferenceModel action

    property LabelValueSelectionModel referencesModel : action.actions

    implicitHeight: _content.height

    RowLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right

        LabelValueComboBox {
            id: _selection

            Layout.fillWidth: true

            model: referencesModel
        }

        IconButton {
            text: bsi.icons.share
            font.pixelSize: Style.dp(20)

            onClicked: function () {
                _root.action.referenceAction(_root.referencesModel.currentValue)
            }
        }

        IconButton {
            text: bsi.icons.duplicate
            font.pixelSize: Style.dp(20)

            onClicked: function () {
                _root.action.duplicateAction(_root.referencesModel.currentValue)
            }
        }
    }
}
