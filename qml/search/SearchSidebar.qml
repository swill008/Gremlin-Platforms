// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style

// The Search window's left side: Look in, Show (quick filters by kind),
// Health, Recent searches and the Suggestion list setting. Reads and sets
// the window's SearchModel (search).
Rectangle {
    id: _side

    // The SearchModel.
    required property var search

    // The quick filters (group "show") and the Health filters (group
    // "health"), as the model lists them: [{name, label, group, on, count}].
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

            Heading { text: "Health" }
            Repeater {
                model: _side.filtersOf("health")
                delegate: _filterRow
            }

            Heading {
                text: "Recent searches"
                visible: _recent.count > 0
            }
            Repeater {
                id: _recent
                model: _side.search ? (_side.search.recent || []) : []
                delegate: Label {
                    required property string modelData
                    required property int index
                    objectName: "searchRecent:" + index
                    Layout.fillWidth: true
                    text: modelData
                    color: _recentMouse.containsMouse ? Style.fgStrong : Style.fg
                    font.underline: _recentMouse.containsMouse
                    elide: Text.ElideRight
                    topPadding: Style.dp(2)
                    bottomPadding: Style.dp(2)
                    MouseArea {
                        id: _recentMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: _side.search.text = parent.modelData
                    }
                }
            }

            Item { Layout.preferredHeight: Style.dp(12) }
            CheckBox {
                objectName: "searchSuggestionsOn"
                Layout.fillWidth: true
                focusPolicy: Qt.NoFocus
                text: "Suggestion list while typing"
                checked: _side.search ? !!_side.search.suggestionsOn : false
                onToggled: {
                    _side.search.suggestionsOn = checked
                    checked = Qt.binding(() => _side.search ? !!_side.search.suggestionsOn : false)
                }
                ToolTip.visible: hovered
                ToolTip.text: "Show a list of matching names under the search box as you type"
            }
        }
    }
}
