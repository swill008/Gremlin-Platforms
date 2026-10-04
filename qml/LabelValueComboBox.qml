// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

import QtQuick.Controls.Universal as U

import Gremlin.Profile
import Gremlin.Style
import Gremlin.Menus as Menus


Item {
    id: _root

    property LabelValueSelectionModel model
    property alias value: _selection.currentValue
    signal selectionChanged()

    implicitHeight: _content.height
    implicitWidth: _content.implicitWidth

    RowLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right
        spacing: Style.dp(10)

        ComboBox {
            id: _selection

            Layout.minimumWidth: Style.dp(250)
            Layout.fillWidth: true

            model: _root.model
            textRole: "label"
            currentIndex: model ? model.currentSelectionIndex : 0
            delegate: OptionDelegate {}
        }
    }

    // Delegate rendering the selection item using its label but using the
    // associated value for storage
    component OptionDelegate : ItemDelegate {
        id: _option
        required property int index
        required property string label
        required property string value
        required property string bootstrap
        required property string imageIcon

        width: parent.width
        // The menus' row look (Gremlin.Menus).
        background: Menus.MenuRowBackground {
            hot: _option.hovered || _selection.highlightedIndex === _option.index
            marked: _selection.currentIndex === _option.index
        }
        contentItem: Row {
             Label {
                 text: bootstrap

                 width: bootstrap.length > 0 ? Style.dp(30) : 0
                 verticalAlignment: Text.AlignBottom

                 font.family: Style.iconFont
                 font.pixelSize: Style.dp(20)
             }
             Label {
                text: label
             }
        }

        onClicked: function()
        {
            _root.model.currentValue = value
            selectionChanged()
        }
    }

}

