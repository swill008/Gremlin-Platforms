// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Config
import Gremlin.Style
import "helpers.js" as Helpers

ApplicationWindow {
    font.pixelSize: Style.fontSize
    id: _options

    EscapeCloses { host: _options }
    // ToolWindowMemory sets the saved or default size when the window opens.
    width: 1200
    height: 700
    // Never wider or taller than the screen, even at a high UI scale.
    minimumWidth: Style.fitWidth(Style.dp(900), Screen)
    minimumHeight: Style.fitHeight(Style.dp(600), Screen)

    U.Universal.theme: Style.theme
    color: Style.background

    title: "Options"

    ToolWindowMemory {
        host: _options
        name: "options"
        defaultWidth: Style.fitWidth(Style.dp(1000), Screen)
        defaultHeight: Style.fitHeight(Style.dp(700), Screen)
    }

    onClosing: () => {
        backend.emitConfigChanged()
    }

    ConfigSectionModel {
        id: _sectionModel
    }

    property int currentSection: 0
    // The page's title ("General"), or "Search" while searching.
    readonly property string sectionTitle: _search.text.trim().length
        ? "Search"
        : String(_sectionModel.data(_sectionModel.index(currentSection, 0), Qt.UserRole + 1) || "")

    // Every setting's on-screen label (Help's show:option/<label> links).
    function settingLabels() {
        return _sectionModel.settingLabels()
    }

    // Help's "Show me ›" (01 S139): show the page holding the setting with
    // this label (any case), scroll it into view and pulse it. false if no
    // setting has that label.
    function revealSetting(label) {
        var hit = _sectionModel.findSetting(String(label || ""))
        if (!hit || hit.length < 3)
            return false
        _search.text = ""
        currentSection = hit[0]
        var card = _settingCard(hit[1], hit[2])
        if (!card)
            return false
        _scrollTo(card)
        // Again once the page has laid out (it may have just been built).
        Qt.callLater(_scrollTo, card)
        _pulse.createObject(card)
        return true
    }

    // The row (OptionEntryCard) titled name in the group titled group.
    function _settingCard(group, name) {
        var stack = [_page.contentItem]
        var inGroup = null
        while (stack.length) {
            var it = stack.pop()
            if (it.entryModel !== undefined && it.groupName === group && it.visible) {
                inGroup = it
                break
            }
            var kids = it.children || []
            for (var i = 0; i < kids.length; i++)
                stack.push(kids[i])
        }
        if (!inGroup)
            return null
        stack = [inGroup]
        while (stack.length) {
            var row = stack.pop()
            if (row.explanation !== undefined && row.title === name)
                return row
            var rows = row.children || []
            for (var j = 0; j < rows.length; j++)
                stack.push(rows[j])
        }
        return null
    }

    function _scrollTo(card) {
        var flick = _page.contentItem
        if (!card || !flick || flick.contentY === undefined)
            return
        var top = card.mapToItem(flick.contentItem, 0, 0).y
        var margin = Style.dp(24)
        var y = flick.contentY
        if (top - margin < y)
            y = top - margin
        else if (top + card.height + margin > y + flick.height)
            y = top + card.height + margin - flick.height
        var most = Math.max(0, flick.contentHeight - flick.height)
        flick.contentY = Math.max(0, Math.min(most, y))
    }

    // The pulse Help's other links use (Pulse.qml).
    Component {
        id: _pulse
        Pulse {}
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // Sidebar: the sections.
        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: Style.dp(200)
            color: Style.bgPage

            Rectangle {
                anchors.right: parent.right
                width: Style.dp(1)
                height: parent.height
                color: Style.line
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Style.dp(10)
                spacing: Style.dp(2)

                RowLayout {
                    Layout.leftMargin: Style.dp(6)
                    Layout.bottomMargin: Style.dp(10)
                    spacing: Style.dp(8)
                    Label {
                        text: "\uF3E5"
                        font.family: Style.iconFont
                        font.pixelSize: Style.dp(18)
                        color: Style.fgSoft
                    }
                    Label {
                        text: "Options"
                        font.pixelSize: Style.dp(17)
                        color: Style.fgStrong
                    }
                }

                Repeater {
                    model: _sectionModel
                    delegate: ConfigSectionButton {}
                }

                Item { Layout.fillHeight: true }
                // Earlier settings, to look at or put back (Tools > History).
                Button {
                    objectName: "optionsHistory"
                    text: "History"
                    focusPolicy: Qt.NoFocus
                    Layout.fillWidth: true
                    onClicked: Helpers.createComponent("DialogHistory.qml", {
                        filter: JSON.stringify({ area: "settings" })
                    })
                }
            }
        }

        // The page: its title, the search box, and the settings.
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: Style.dp(20)
                Layout.rightMargin: Style.dp(20)
                Layout.topMargin: Style.dp(14)
                spacing: Style.dp(12)

                Label {
                    Layout.fillWidth: true
                    text: _options.sectionTitle
                    color: Style.fgStrong
                    font.pixelSize: Style.dp(20)
                }
                TextField {
                    id: _search
                    Layout.preferredWidth: Style.dp(240)
                    placeholderText: "Search options"
                }
            }

            ConfigSection {
                id: _page
                Layout.fillWidth: true
                Layout.fillHeight: true
                sectionModel: _sectionModel
                currentIndex: _options.currentSection
                filterText: _search.text
            }
        }
    }
}
