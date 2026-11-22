// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style

// The Search window's left side: Look in and Show (quick filters by kind).
// Names wrap instead of being cut (01 S196). Reads and sets the window's
// SearchModel (search).
Rectangle {
    id: _side

    // The SearchModel.
    required property var search

    // The quick filters (group "show"), as the model lists them:
    // [{name, label, group, on, count}].
    function filtersOf(group) {
        var all = search ? (search.filters || []) : []
        return all.filter(function(f) { return f.group === group })
    }

    readonly property var scopes: [
        { name: "all", label: "All profiles" },
        { name: "this", label: "This profile only" },
        { name: "library", label: "Device Library" }
    ]

    color: Style.bgWell
    border.color: Style.line
    implicitWidth: Style.dp(210)

    component Heading: Label {
        color: Style.fgMuted
        font.bold: true
        font.pixelSize: Style.menuTextPx
        topPadding: Style.dp(10)
        bottomPadding: Style.dp(2)
    }

    // A filter row: a check box with the name and its count.
    Component {
        id: _filterRow
        CheckBox {
            required property var modelData
            objectName: "searchFilter:" + modelData.name
            Layout.fillWidth: true
            focusPolicy: Qt.NoFocus
            checked: !!modelData.on
            text: modelData.label + " (" + modelData.count + ")"
            onToggled: _side.search.setFilter(modelData.name, checked)
            contentItem: Label {
                text: parent.text
                wrapMode: Text.Wrap
                verticalAlignment: Text.AlignVCenter
                leftPadding: parent.indicator.width + parent.spacing
                color: Style.fg
            }
        }
    }

    ScrollView {
        anchors.fill: parent
        anchors.margins: Style.dp(8)
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: parent.width
            spacing: Style.dp(2)

            Heading { text: "Look in"; topPadding: 0 }
            Repeater {
                model: _side.scopes
                delegate: RadioButton {
                    required property var modelData
                    objectName: "searchLookIn:" + modelData.name
                    Layout.fillWidth: true
                    focusPolicy: Qt.NoFocus
                    text: modelData.label
                    contentItem: Label {
                        text: parent.text
                        wrapMode: Text.Wrap
                        verticalAlignment: Text.AlignVCenter
                        leftPadding: parent.indicator.width + parent.spacing
                        color: Style.fg
                    }
                    checked: _side.search && _side.search.lookIn === modelData.name
                    onClicked: {
                        _side.search.lookIn = modelData.name
                        checked = Qt.binding(() => _side.search && _side.search.lookIn === modelData.name)
                    }
                }
            }

            Heading { text: "Show" }
            Repeater {
                model: _side.filtersOf("show")
                delegate: _filterRow
            }
        }
    }
}
