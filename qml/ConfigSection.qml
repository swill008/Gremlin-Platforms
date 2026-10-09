// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Config
import Gremlin.Style

// An Options page: the groups (ConfigGroup) of the chosen section. While
// searching (filterText set) it shows every section's matching settings,
// each under its section's title. Used by the main Options window and the
// Button Map's own options window.
//
// A section's groups are built the first time it shows (it is the current
// section, or the search matches it) and then kept: building every section
// at open made the window slow to open.
ScrollView {
    id: _page

    property ConfigSectionModel sectionModel
    property int currentIndex: 0
    property string filterText: ""
    readonly property bool searching: filterText.trim().length > 0

    // While searching: the indexes of the sections with a match, or null
    // (not known: build them all).
    readonly property var matching: searching && sectionModel
        && typeof sectionModel.matchingSections === "function"
        ? sectionModel.matchingSections(filterText) : null

    contentWidth: availableWidth
    clip: true

    ColumnLayout {
        width: _page.availableWidth - Style.dp(40)
        x: Style.dp(20)
        spacing: 0

        Repeater {
            model: _page.sectionModel

            delegate: ColumnLayout {
                id: _section

                required property int index
                required property string name
                required property ConfigGroupModel groupModel

                Layout.fillWidth: true
                spacing: 0
                visible: _page.searching ? hasMatch() : index === _page.currentIndex

                // Shown now: the current section, or one the search matches.
                readonly property bool wanted: _page.searching
                    ? (_page.matching === null || _page.matching.indexOf(index) >= 0)
                    : index === _page.currentIndex
                property bool built: false

                // While searching: some group of this section shows.
                function hasMatch() {
                    _page.filterText
                    var body = _groups.item
                    if (!body)
                        return false
                    for (var i = 0; i < body.children.length; i++) {
                        var g = body.children[i]
                        if (g.firstMatch !== undefined && g.firstMatch >= 0)
                            return true
                    }
                    return false
                }

                Label {
                    // Section titles only while searching (the sidebar names
                    // the section otherwise).
                    visible: _page.searching
                    Layout.topMargin: Style.dp(18)
                    text: _section.name
                    color: Style.fgStrong
                    font.pixelSize: Style.dp(16)
                }

                Loader {
                    id: _groups

                    Layout.fillWidth: true
                    active: _section.wanted || _section.built
                    onLoaded: _section.built = true

                    sourceComponent: ColumnLayout {
                        spacing: 0

                        Repeater {
                            model: _section.groupModel

                            delegate: ConfigGroup {
                                Layout.fillWidth: true
                                filterText: _page.filterText
                            }
                        }
                    }
                }
            }
        }

        // No "No setting matches" line here: the shared search box says
        // "Nothing matches" under itself (01 S141).

        Item { implicitHeight: Style.dp(20) }
    }

    // Any setting matches the search (some group shows).
    function anyMatch() {
        filterText
        var stack = [contentItem]
        while (stack.length) {
            var item = stack.pop()
            if (item.firstMatch !== undefined && item.firstMatch >= 0)
                return true
            var kids = item.children || []
            for (var i = 0; i < kids.length; i++)
                stack.push(kids[i])
        }
        return false
    }
}
