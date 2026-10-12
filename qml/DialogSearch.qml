// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Menus
import Gremlin.Style
import Gremlin.UI
import Gremlin.Util
import "helpers.js" as Helpers
import "search"
import "search/search_text.js" as SearchText

// Search (D-01-SEARCH-INDEX): type to find keys, actions, names and outputs
// in every profile, the open one and the Device Library, as you type. The
// SearchModel (gremlin/ui/search_model.py) does the searching; this window
// shows it: the box with Aa / ab / .* and Listen, a status line, Look in /
// Show / Health / Recent on the left, results grouped profile › device in
// the middle, the picked result on the right. A result opens through
// Main.goToSearchRow(row) (another profile or the Device Library included).
// Opened by Main.openSearch(text) from the toolbar, Tools › Mapping ›
// Search…, Ctrl+Shift+F and Find uses… menus.
ApplicationWindow {
    font.pixelSize: Style.fontSize
    id: _root

    ToolWindowMemory {
        host: _root
        name: "search"
        defaultWidth: Style.fitWidth(Style.dp(1100), Screen)
        defaultHeight: Style.fitHeight(Style.dp(700), Screen)
    }

    // Esc is this window's own (clear, then close; stops Listen), in the
    // box too (gremlin/ui/leave_text.py).
    property bool leaveTextOnEscape: false

    minimumWidth: Style.fitWidth(Style.dp(640), Screen)
    minimumHeight: Style.fitHeight(Style.dp(420), Screen)
    color: Style.background
    U.Universal.theme: Style.theme
    title: "Search"

    readonly property alias search: _model
    // The picked result's row in the model (-1: none).
    property int current: -1
    property string sortColumn: ""
    property int sortOrder: Qt.AscendingOrder
    property bool allFolded: false
    // The detail pane, remembered by the model when it can.
    property bool _detailLocal: true
    readonly property bool detailOpen: _model.detailOpen === undefined
                                       ? _detailLocal : !!_model.detailOpen
    // Bumped to read the picked result's detail again.
    property int detailRevision: 0

    readonly property bool listening: !!_model.listening
    readonly property bool typed: String(_model.text || "").trim().length > 0
    readonly property bool nothingFound: typed && !listening && _model.resultCount === 0

    SearchModel {
        id: _model
        onModelReset: { _root.current = -1; _root.detailRevision++ }
    }

    Connections {
        target: _model
        function onTextChanged() {
            if (_box.text !== _model.text)
                _box.text = _model.text
        }
    }

    // Fills the box (Main.openSearch: text, or {text}) and searches.
    function fill(textOrQuery) {
        var t = textOrQuery
        if (t !== null && typeof t === "object")
            t = t.text
        if (t !== undefined && t !== null)
            _model.text = String(t)
        focusBox()
    }

    // Main.openSearch: fills the box and searches now.
    function searchFor(text) {
        _model.searchFor(String(text))
        focusBox()
    }

    function focusBox() {
        _box.forceActiveFocus()
        _box.selectAll()
    }

    function setDetailOpen(on) {
        if (_model.detailOpen === undefined)
            _detailLocal = on
        else
            _model.detailOpen = on
    }

    function itemOf(index) {
        if (index < 0 || index >= _list.count)
            return null
        _list.positionViewAtIndex(index, ListView.Contain)
        return _list.itemAtIndex(index)
    }

    function isResult(index) {
        var item = itemOf(index)
        return !!item && item.kind === "result"
    }

    // Moves the pick to the next result up (-1) or down (+1).
    function move(step) {
        var i = current < 0 ? (step > 0 ? -1 : _list.count) : current
        for (i += step; i >= 0 && i < _list.count; i += step) {
            if (isResult(i)) {
                pick(i)
                return
            }
        }
    }

    function pick(index) {
        current = index
        detailRevision++
        if (index >= 0)
            _list.positionViewAtIndex(index, ListView.Contain)
    }

    // A result's fields, for Main.goToSearchRow.
    function rowOf(index) {
        var item = itemOf(index)
        if (!item || item.kind !== "result")
            return null
        // Main.goToSearchRow reads the SearchRow field names (snake_case).
        var roles = _model.get(index) || {}
        var row = { row: index }
        for (var name in roles)
            row[SearchText.snake(name)] = roles[name]
        return row
    }

    function open(index) {
        if (index < 0)
            index = firstResult()
        var row = rowOf(index)
        var main = Helpers.mainWindow()
        if (!row || !main)
            return
        pick(index)
        main.goToSearchRow(row)
    }

    function firstResult() {
        for (var i = 0; i < _list.count; i++)
            if (isResult(i))
                return i
        return -1
    }

    function openInMappingEditor(index) {
        var row = rowOf(index)
        var main = Helpers.mainWindow()
        if (row && main && String(row.device_name || "").length)
            main.openDeviceMappingEditorForCard({ name: row.device_name, guid: row.device_guid })
    }

    function searchForTarget(index) {
        var row = rowOf(index)
        if (!row)
            return
        if (typeof _model.searchForTarget === "function") {
            _model.searchForTarget(index)
            return
        }
        var targets = row.targets || []
        if (targets.length)
            _model.searchFor("\"" + String(targets[0]) + "\"")
    }

    function copyRow(index) {
        if (index >= 0)
            _model.copyText(index)
    }

    // Enter: the picked suggestion, else the picked (or first) result.
    function enter() {
        if (_suggest.visible && _suggestAt >= 0)
            takeSuggestion(suggestionList[_suggestAt])
        else
            open(current)
    }

    function toggleListen() {
        if (listening)
            _model.stopListen()
        else
            _model.listen()
    }

    function setSort(column) {
        if (sortColumn === column)
            sortOrder = sortOrder === Qt.AscendingOrder ? Qt.DescendingOrder : Qt.AscendingOrder
        else {
            sortColumn = column
            sortOrder = Qt.AscendingOrder
        }
        _model.setSort(column, sortOrder)
    }

    // Esc: a menu or popup closes, then Listen stops, then the box clears,
    // then the window closes.
    function escapePressed() {
        if (_rowMenu.visible) { _rowMenu.close(); return }
        if (_help.visible) { _help.close(); return }
        if (_unreadablePopup.visible) { _unreadablePopup.close(); return }
        if (_suggest.visible) { _suggest.close(); _suggestDismissed = true; return }
        if (listening) { _model.stopListen(); return }
        if (String(_box.text).length) {
            _model.text = ""
            _box.text = ""
            focusBox()
            return
        }
        _root.close()
    }

    // Suggestions (only when the setting is on).
    property bool _suggestDismissed: false
    property int _suggestAt: -1
    readonly property var suggestionList: _model.suggestionsOn ? (_model.suggestions || []) : []

    function takeSuggestion(text) {
        _model.text = String(text)
        _suggest.close()
        _suggestDismissed = true
        focusBox()
        _box.deselect()
        _box.cursorPosition = _box.text.length
    }

    Shortcut {
        sequences: [StandardKey.Cancel]
        onActivated: _root.escapePressed()
    }
    Shortcut {
        sequences: ["Ctrl+F"]
        onActivated: _root.focusBox()
    }

    Component.onCompleted: {
        _box.text = _model.text || ""
        Qt.callLater(focusBox)
    }
    onActiveChanged: if (active && !_box.activeFocus && current < 0) focusBox()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Style.dp(10)
        spacing: Style.dp(6)

        // The box, the match toggles, ? and Listen.
        RowLayout {
            Layout.fillWidth: true
            spacing: Style.dp(4)

            TextField {
                id: _box
                objectName: "searchBox"
                Layout.fillWidth: true
                placeholderText: "Search keys, actions, names and outputs…"
                selectByMouse: true
                onTextEdited: {
                    _root._suggestDismissed = false
                    _root._suggestAt = -1
                    _model.text = text
                }
                Keys.onUpPressed: (event) => {
                    if (_suggest.visible && _root._suggestAt > 0)
                        _root._suggestAt--
                    else
                        _root.move(-1)
                }
                Keys.onDownPressed: (event) => {
                    if (_suggest.visible)
                        _root._suggestAt = Math.min(_root.suggestionList.length - 1,
                                                    _root._suggestAt + 1)
                    else
                        _root.move(1)
                }
                Keys.onReturnPressed: _root.enter()
                Keys.onEnterPressed: _root.enter()
            }

            component Toggle: Button {
                checkable: true
                focusPolicy: Qt.NoFocus
                font.family: Style.monoFont
                implicitWidth: Style.dp(38)
                ToolTip.visible: hovered
            }
            Toggle {
                objectName: "searchMatchCase"
                text: "Aa"
                checked: !!_model.matchCase
                onToggled: { _model.matchCase = checked; checked = Qt.binding(() => !!_model.matchCase) }
                ToolTip.text: "Match case"
            }
            Toggle {
                objectName: "searchWholeWord"
                text: "ab"
                font.underline: true
                checked: !!_model.wholeWord
                onToggled: { _model.wholeWord = checked; checked = Qt.binding(() => !!_model.wholeWord) }
                ToolTip.text: "Whole word"
            }
            Toggle {
                objectName: "searchRegex"
                text: ".*"
                checked: !!_model.regex
                onToggled: { _model.regex = checked; checked = Qt.binding(() => !!_model.regex) }
                ToolTip.text: "Regular expression"
            }
            Button {
                id: _helpButton
                objectName: "searchHelp"
                text: "?"
                focusPolicy: Qt.NoFocus
                implicitWidth: Style.dp(32)
                ToolTip.visible: hovered
                ToolTip.text: "How to search"
                onClicked: _help.visible ? _help.close() : _help.open()
            }
            Button {
                objectName: "searchListenButton"
                text: _root.listening ? "Stop" : "Listen"
                highlighted: _root.listening
                focusPolicy: Qt.NoFocus
                ToolTip.visible: hovered
                ToolTip.text: "Press a control, a key or an OSC button to search for it"
                onClicked: _root.toggleListen()
            }
        }

        // The status line: the index, the counts, profiles that could not be read.
        RowLayout {
            Layout.fillWidth: true
            spacing: Style.dp(10)
            Label {
                objectName: "searchStatus"
                text: String(_model.statusText || "")
                visible: text.length > 0
                color: Style.fgMuted
            }
            Label {
                objectName: "searchCount"
                visible: _root.typed
                text: {
                    var n = Number(_model.resultCount || 0)
                    var p = Number(_model.profileCount || 0)
                    return (n === 1 ? "1 use" : n + " uses") + " in "
                        + (p === 1 ? "1 profile" : p + " profiles")
                }
                color: Style.fgMuted
            }
            Label {
                id: _unreadableLink
                objectName: "searchUnreadable"
                readonly property var list: _model.unreadable || []
                visible: list.length > 0
                text: list.length === 1 ? "1 profile could not be read"
                                        : list.length + " profiles could not be read"
                color: Style.warn
                font.underline: true
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: _unreadablePopup.open()
                }
            }
            Item { Layout.fillWidth: true }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Style.dp(6)

            SearchSidebar {
                objectName: "searchSidebar"
                Layout.fillHeight: true
                Layout.preferredWidth: implicitWidth
                search: _model
            }

            // The results: column headings, the grouped rows, the states.
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: Style.bgWell
                border.color: Style.line

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Style.dp(1)
                    spacing: 0

                    // Sortable column headings and Fold all.
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: _headings.implicitHeight + Style.dp(6)
                        color: Style.bgRaised
                        visible: _list.count > 0

                        RowLayout {
                            id: _headings
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.leftMargin: Style.dp(38)
                            anchors.rightMargin: Style.dp(8)
                            spacing: Style.dp(8)

                            Repeater {
                                model: [{ column: "input", label: "Input" },
                                        { column: "mode", label: "Mode" },
                                        { column: "action", label: "Action" }]
                                delegate: Label {
                                    required property var modelData
                                    readonly property string column: modelData.column
                                    objectName: "searchSort:" + column
                                    Layout.preferredWidth: column === "input"
                                        ? _list.inputWidth - Style.dp(38)
                                        : (column === "mode" ? _list.modeWidth : -1)
                                    Layout.fillWidth: column === "action"
                                    text: modelData.label + (_root.sortColumn !== column ? ""
                                          : (_root.sortOrder === Qt.AscendingOrder ? " ▲" : " ▼"))
                                    color: Style.fgStrong
                                    font.bold: true
                                    elide: Text.ElideRight
                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: _root.setSort(parent.column)
                                    }
                                }
                            }
                            Label {
                                objectName: "searchFoldAll"
                                text: _root.allFolded ? "Unfold all" : "Fold all"
                                color: Style.fgMuted
                                font.underline: true
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        _root.allFolded = !_root.allFolded
                                        _model.foldAll(_root.allFolded)
                                    }
                                }
                            }
                        }
                    }

                    JGListView {
                        id: _list
                        objectName: "searchResults"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        visible: !_root.listening
                        model: _model
                        readonly property real inputWidth: Math.max(Style.dp(160), width * 0.32)
                        readonly property real modeWidth: Math.max(Style.dp(80), width * 0.14)
                        delegate: SearchResultRow {
                            inputWidth: _list.inputWidth
                            modeWidth: _list.modeWidth
                            current: index === _root.current
                            onPicked: (i) => _root.pick(i)
                            onOpened: (i) => _root.open(i)
                            onFoldClicked: (i) => _model.toggleFold(i)
                            onMenuAsked: (i, x, y) => _rowMenu.popup()
                        }
                    }
                }

                // First open: what Search does, examples and recent searches.
                ColumnLayout {
                    objectName: "searchFirstOpen"
                    visible: !_root.typed && !_root.listening
                    anchors.centerIn: parent
                    width: Math.min(parent.width - Style.dp(40), Style.dp(520))
                    spacing: Style.dp(8)

                    Label {
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                        color: Style.fg
                        text: "Type to find a key, an action, a name or an output in every "
                            + "profile, the open profile and the Device Library. Each result "
                            + "says which profile, device and mode it is in; Enter or a "
                            + "double-click opens it. Listen finds what you press."
                    }
                    Label { text: "Try:"; color: Style.fgMuted }
                    Flow {
                        Layout.fillWidth: true
                        spacing: Style.dp(6)
                        Repeater {
                            model: ["F5", "key:F5", "vjoy:", "xbox:A", "osc:", "mode:Default",
                                    "gr tog"]
                            delegate: Button {
                                required property string modelData
                                objectName: "searchExample:" + modelData
                                text: modelData
                                font.family: Style.monoFont
                                focusPolicy: Qt.NoFocus
                                onClicked: { _model.text = modelData; _root.focusBox() }
                            }
                        }
                    }
                    Label {
                        text: "Recent searches"
                        color: Style.fgMuted
                        visible: (_model.recent || []).length > 0
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: Style.dp(6)
                        Repeater {
                            model: _model.recent || []
                            delegate: Button {
                                required property string modelData
                                text: modelData
                                focusPolicy: Qt.NoFocus
                                onClicked: { _model.text = modelData; _root.focusBox() }
                            }
                        }
                    }
                }

                // Listening: what was heard; Esc stops.
                ColumnLayout {
                    objectName: "searchListening"
                    visible: _root.listening
                    anchors.centerIn: parent
                    width: Math.min(parent.width - Style.dp(40), Style.dp(480))
                    spacing: Style.dp(8)
                    Label {
                        Layout.alignment: Qt.AlignHCenter
                        text: "Press a control, a key or an OSC button…"
                        color: Style.fgStrong
                        font.bold: true
                    }
                    Label {
                        objectName: "searchHeard"
                        Layout.alignment: Qt.AlignHCenter
                        visible: text.length > 0
                        text: String(_model.heardText || "")
                        color: Style.fg
                    }
                    Label {
                        objectName: "searchListenError"
                        Layout.fillWidth: true
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.Wrap
                        visible: text.length > 0
                        text: String(_model.listenError || "")
                        color: Style.warn
                    }
                    Label {
                        Layout.alignment: Qt.AlignHCenter
                        text: "Esc stops listening."
                        color: Style.fgMuted
                    }
                }

                // Nothing found: what and where, Did you mean, one-click fixes.
                ColumnLayout {
                    id: _nothing
                    objectName: "searchNothingFound"
                    visible: _root.nothingFound
                    anchors.centerIn: parent
                    width: Math.min(parent.width - Style.dp(40), Style.dp(520))
                    spacing: Style.dp(8)

                    Label {
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                        color: Style.fgStrong
                        text: String(_model.nothingFoundText || "")
                    }
                    Label {
                        objectName: "searchDidYouMean"
                        visible: String(_model.didYouMean || "").length > 0
                        text: "Did you mean <a href=\"x\">" + SearchText.escape(_model.didYouMean)
                            + "</a>?"
                        textFormat: Text.StyledText
                        color: Style.fg
                        linkColor: Style.accent
                        onLinkActivated: { _model.text = String(_model.didYouMean); _root.focusBox() }
                        MouseArea {
                            anchors.fill: parent
                            acceptedButtons: Qt.NoButton
                            cursorShape: parent.hoveredLink ? Qt.PointingHandCursor : Qt.ArrowCursor
                        }
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: Style.dp(6)
                        Repeater {
                            model: _model.nothingFoundHints || []
                            delegate: Button {
                                required property var modelData
                                objectName: "searchFix:" + modelData.action
                                text: modelData.text
                                focusPolicy: Qt.NoFocus
                                onClicked: { _model.applyHint(modelData.action); _root.focusBox() }
                            }
                        }
                    }
                }
            }

            // The picked result; closable, remembered.
            SearchDetail {
                objectName: "searchDetail"
                visible: _root.detailOpen
                Layout.fillHeight: true
                Layout.preferredWidth: implicitWidth
                row: {
                    _root.detailRevision
                    var item = _root.current >= 0 ? _list.itemAtIndex(_root.current) : null
                    return item && item.kind === "result" ? item.model : null
                }
                info: {
                    _root.detailRevision
                    return _root.current >= 0 && row ? (_model.detail(_root.current) || {}) : {}
                }
                onOpenClicked: _root.open(_root.current)
                onMappingEditorClicked: _root.openInMappingEditor(_root.current)
                onSearchTargetClicked: _root.searchForTarget(_root.current)
                onCloseClicked: _root.setDetailOpen(false)
            }
            Button {
                objectName: "searchDetailShow"
                visible: !_root.detailOpen
                Layout.alignment: Qt.AlignTop
                text: "‹"
                focusPolicy: Qt.NoFocus
                implicitWidth: Style.dp(24)
                ToolTip.visible: hovered
                ToolTip.text: "Show the details"
                onClicked: _root.setDetailOpen(true)
            }
        }

        Label {
            objectName: "searchHints"
            Layout.fillWidth: true
            text: "↑↓ move · Enter open · Esc clear · Esc again close"
            color: Style.fgMuted
            font.pixelSize: Style.menuTextPx
        }
    }

    // The suggestion list (setting, off by default) under the box.
    Popup {
        id: _suggest
        objectName: "searchSuggestions"
        parent: _box
        y: _box.height
        width: _box.width
        padding: Style.dp(2)
        focus: false
        closePolicy: Popup.CloseOnPressOutsideParent
        visible: _box.activeFocus && !_root._suggestDismissed && !_root.listening
                 && _root.suggestionList.length > 0
        background: Rectangle { color: Style.menuBg; border.color: Style.menuLine }
        contentItem: ColumnLayout {
            spacing: 0
            Repeater {
                model: _root.suggestionList
                delegate: Rectangle {
                    required property var modelData
                    required property int index
                    Layout.fillWidth: true
                    implicitHeight: _suggestText.implicitHeight + Style.dp(6)
                    color: index === _root._suggestAt || _suggestMouse.containsMouse
                           ? Style.menuHover : Style.clear
                    Label {
                        id: _suggestText
                        anchors.verticalCenter: parent.verticalCenter
                        x: Style.dp(8)
                        text: String(modelData)
                        color: Style.menuText
                    }
                    MouseArea {
                        id: _suggestMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: _root.takeSuggestion(parent.modelData)
                    }
                }
            }
        }
    }

    // ? : prefixes, toggles and keys.
    Popup {
        id: _help
        objectName: "searchHelpPopup"
        parent: _helpButton
        y: _helpButton.height + Style.dp(4)
        x: _helpButton.width - width
        width: Style.dp(440)
        padding: Style.dp(12)
        background: Rectangle { color: Style.menuBg; border.color: Style.menuLine; radius: Style.dp(4) }
        contentItem: ColumnLayout {
            spacing: Style.dp(6)
            Label {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: Style.menuText
                text: "Type any part of a name: letters in order find it (gr tog finds "
                    + "Gear toggle); whole words and starts of words come first."
            }
            Label { text: "Look for one thing only:"; color: Style.menuTextStrong; font.bold: true }
            Repeater {
                model: _model.prefixes || []
                delegate: Label {
                    required property var modelData
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    textFormat: Text.StyledText
                    color: Style.menuText
                    text: "<b>" + SearchText.escape(SearchText.field(modelData, "name", modelData))
                        + ":</b> " + SearchText.escape(SearchText.field(modelData, "description", ""))
                }
            }
            Label {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: Style.menuText
                text: "Aa matches case, ab matches whole words, .* takes a regular "
                    + "expression. Put a name with spaces in quotes: device:\"T.16000M\"."
            }
            Label {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: Style.menuTextSoft
                text: "↑↓ move · Enter open · Esc clear · Esc again close"
            }
        }
    }

    // Profiles the index could not read, with the reason.
    Popup {
        id: _unreadablePopup
        objectName: "searchUnreadablePopup"
        parent: _unreadableLink
        y: _unreadableLink.height + Style.dp(4)
        width: Style.dp(480)
        padding: Style.dp(10)
        background: Rectangle { color: Style.menuBg; border.color: Style.menuLine; radius: Style.dp(4) }
        contentItem: ColumnLayout {
            spacing: Style.dp(4)
            Repeater {
                model: _unreadableLink.list
                delegate: Label {
                    required property var modelData
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    color: Style.menuText
                    text: {
                        var path = modelData.length !== undefined && typeof modelData !== "string"
                                   ? modelData[0] : SearchText.field(modelData, "path", modelData)
                        var why = modelData.length !== undefined && typeof modelData !== "string"
                                  ? modelData[1] : SearchText.field(modelData, "reason", "")
                        var file = String(path).split(/[\/]/).pop()
                        return "Could not read " + file + (String(why).length ? ": " + why : "")
                    }
                }
            }
        }
    }

    // A result's right-click menu.
    ThemedMenu {
        id: _rowMenu
        objectName: "searchRowMenu"
        ThemedMenuItem {
            text: "Open"
            onTriggered: _root.open(_root.current)
        }
        ThemedMenuItem {
            text: "Open in Device Mapping Editor"
            onTriggered: _root.openInMappingEditor(_root.current)
        }
        ThemedMenuItem {
            text: "Copy as text"
            onTriggered: _root.copyRow(_root.current)
        }
        ThemedMenuItem {
            text: "Search for this target"
            onTriggered: _root.searchForTarget(_root.current)
        }
    }
}
