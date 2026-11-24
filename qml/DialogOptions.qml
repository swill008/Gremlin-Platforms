// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Config
import Gremlin.Style
import Gremlin.UI
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

    // Made by ModelFactory (PYSIDE-1407); lives as long as this window.
    readonly property ConfigSectionModel _sectionModel:
        ModelFactory.create("ConfigSectionModel", _options)

    property int currentSection: 0
    onCurrentSectionChanged: profilePage = ""

    // The open profile's pages (04 S96), and the one shown ("" none: the
    // section is shown).
    readonly property var profilePages: [
        { id: "startup-macros", name: "Startup and macros", file: "ProfileSettingsGeneral.qml" },
        { id: "vjoy", name: "vJoy", file: "ProfileSettingsVJoy.qml" },
        { id: "scripts", name: "Scripts", file: "ScriptManager.qml" }
    ]
    property string profilePage: ""
    onProfilePageChanged: _page.contentItem.contentY = 0

    // Show one of the open profile's pages (and clear the search); false if
    // there is no page with that id.
    function showPage(id) {
        if (!profilePages.some((page) => page.id === id))
            return false
        _search.text = ""
        profilePage = id
        return true
    }

    // Show a section (and clear the search).
    function showSection(index) {
        _search.text = ""
        profilePage = ""
        currentSection = index
    }

    // The page's title ("General"), or "Search" while searching.
    readonly property bool searching: _search.text.trim().length > 0
    readonly property string sectionTitle: searching
        ? "Search"
        : profilePage !== ""
        ? profilePages.find((page) => page.id === profilePage).name
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
        showSection(hit[0])
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

    // Settings the search finds (the search box's "N found"); -1 when
    // not searching.
    property int _found: -1

    // The rows found on the open profile's pages.
    readonly property int _profileFound: {
        var n = 0
        for (var i = 0; i < _profilePages.count; i++) {
            var page = _profilePages.itemAt(i)
            if (page)
                n += page.found
        }
        return n
    }

    // Counts the rows the built pages show for the search: every group's
    // matching rows (ConfigGroup.matches), across all sections.
    function _countFound() {
        if (!_search.text.trim().length) {
            _found = -1
            return
        }
        var n = 0
        var stack = [_page.contentItem]
        while (stack.length) {
            var it = stack.pop()
            if (it.entryModel !== undefined && typeof it.matches === "function") {
                var rows = it.entryModel ? it.entryModel.rowCount() : 0
                for (var i = 0; i < rows; i++) {
                    if (it.matches(i))
                        n++
                }
                continue
            }
            var kids = it.children || []
            for (var j = 0; j < kids.length; j++)
                stack.push(kids[j])
        }
        _found = n
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
                    delegate: ConfigSectionButton {
                        required property int index
                        required property string name
                        required property ConfigGroupModel groupModel

                        text: name
                        current: _options.profilePage === ""
                            && _options.currentSection === index
                        onClicked: _options.showSection(index)
                    }
                }

                // The open profile's own pages.
                Rectangle {
                    Layout.fillWidth: true
                    Layout.topMargin: Style.dp(6)
                    implicitHeight: Style.dp(1)
                    color: Style.line
                }
                Label {
                    objectName: "optionsProfileHeading"
                    Layout.leftMargin: Style.dp(6)
                    Layout.topMargin: Style.dp(4)
                    text: "This profile"
                    color: Style.fgMuted
                    font.pixelSize: Style.dp(12)
                }
                Repeater {
                    model: _options.profilePages
                    delegate: ConfigSectionButton {
                        required property var modelData

                        objectName: "optionsSection:" + modelData.id
                        text: modelData.name
                        current: _options.profilePage === modelData.id
                        onClicked: _options.showPage(modelData.id)
                    }
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
                // The shared search box (01 S141): Ctrl+F, ×, Esc, "N found".
                SearchBox {
                    id: _search
                    objectName: "optionsSearch"
                    Layout.preferredWidth: Style.dp(240)
                    Layout.alignment: Qt.AlignTop
                    placeholder: "Search options"
                    count: _options._found < 0 ? -1
                        : _options._found + _options._profileFound
                    onTextChanged: Qt.callLater(_options._countFound)
                }
            }

            // The open profile's pages: its name, and where changes go.
            Rectangle {
                objectName: "optionsProfileStrip"
                visible: _options.profilePage !== "" && !_options.searching
                Layout.fillWidth: true
                Layout.leftMargin: Style.dp(20)
                Layout.rightMargin: Style.dp(20)
                Layout.topMargin: Style.dp(8)
                implicitHeight: _strip.implicitHeight + Style.dp(12)
                radius: Style.dp(6)
                color: Style.goldFill
                border.color: Style.goldLine
                border.width: Style.dp(1)

                RowLayout {
                    id: _strip
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.leftMargin: Style.dp(14)
                    anchors.rightMargin: Style.dp(14)
                    spacing: Style.dp(16)

                    Label {
                        objectName: "optionsProfileName"
                        Layout.fillWidth: true
                        text: backend ? backend.windowTitle : ""
                        color: Style.fgSoft
                        font.pixelSize: Style.dp(13)
                        elide: Text.ElideMiddle
                    }
                    Label {
                        objectName: "optionsProfileSavedNote"
                        text: "Saved with the profile (Save Profile)"
                        color: Style.fgMuted
                        font.pixelSize: Style.dp(12)
                    }
                }
            }

            ConfigSection {
                id: _page
                Layout.fillWidth: true
                Layout.fillHeight: true
                sectionModel: _sectionModel
                currentIndex: _options.profilePage === "" ? _options.currentSection : -1
                filterText: _search.text
                fillsView: _options.profilePage === "scripts" && !_options.searching

                // Loaded only while shown or searched.
                Repeater {
                    id: _profilePages
                    model: _options.profilePages

                    delegate: ColumnLayout {
                        id: _profilePage

                        required property var modelData
                        readonly property bool shown:
                            _options.profilePage === modelData.id
                        readonly property int found:
                            _options.searching && _pageLoader.item
                            ? _pageLoader.item.searchFound : 0

                        Layout.fillWidth: true
                        spacing: 0
                        visible: _options.searching ? found > 0 : shown

                        Label {
                            visible: _options.searching
                            Layout.topMargin: Style.dp(18)
                            text: _profilePage.modelData.name
                            color: Style.fgStrong
                            font.pixelSize: Style.dp(16)
                        }

                        Loader {
                            id: _pageLoader
                            objectName: "optionsPage:" + _profilePage.modelData.id

                            // Scripts fills the view; its panes scroll.
                            readonly property bool fills: !_options.searching
                                && _profilePage.modelData.id === "scripts"
                            readonly property real tall: item ? item.implicitHeight : 0

                            Layout.fillWidth: true
                            Layout.preferredHeight: fills ? _page.availableHeight : tall
                            active: _options.searching || _profilePage.shown
                            source: _profilePage.modelData.file
                            onLoaded: {
                                item.filterText = Qt.binding(() => _search.text)
                            }
                        }
                    }
                }
            }
        }
    }
}
