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
import "confirm.js" as Confirm
import "helpers.js" as Helpers
import "search"
import "search/search_text.js" as SearchText

// Search (D-01-SEARCH-INDEX): type to find keys, actions, names and outputs
// in every profile, the open one and the Device Library, as you type. The
// SearchModel (gremlin/ui/search_model.py) does the searching; this window
// shows it (01 S196): Listen, the box with Aa / ab / .*, the status line
// with the Suggestion list tick, recent searches in the drop-down under the
// empty box, Look in / Show on the left, results grouped profile › device in
// the middle, the picked result on the right. Search shows no health marks
// (those are Health's, 01 S197). A result opens through
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

    readonly property SearchModel search: _model
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

    // Made by ModelFactory (PYSIDE-1407: PySide6 never frees a Python object
    // QML declares); it lives as long as this window.
    readonly property SearchModel _model: ModelFactory.create("SearchModel", _root)
    Connections {
        target: _root._model
        function onModelReset() { _root.current = -1; _root.detailRevision++ }
        // An edit or undo that can't be made says why (01 S195).
        function onEditRefused(title, why) { _root.tell(title, why) }
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
        // An unplugged device has no page (01 S195): say so instead.
        var why = String(_model.openMessage(index) || "")
        if (why.length) {
            _root.tell("", why)
            return
        }
        main.goToSearchRow(row)
    }

    // The window's notice box (one OK): Open's message, a refused edit.
    function tell(title, text) {
        _openMessage.title = String(title || "")
        _openMessage.text = String(text || "")
        _openMessage.open()
    }

    // What the picked row's menu and side panel offer (01 S195).
    function fixesOf(index) {
        return index >= 0 ? (_model.fixes(index) || {}) : {}
    }

    // Remove binding…: asks, then removes.
    function askRemove(index) {
        var question = String(_model.removeQuestion(index) || "")
        if (!question.length)
            return null
        return Confirm.ask(_root, {
            title: question,
            note: "Undo (Ctrl+Z) in this window puts it back until the profile is saved or closed.",
            action: "Remove",
            onAccept: function() { _model.removeBinding(index) }
        })
    }

    // Change target…: the vJoy pickers the action editor uses.
    function askChangeTarget(index) {
        var start = _model.changeTargetOf(index) || {}
        if (start.vjoyId === undefined)
            return
        _targetBox.row = index
        _targetBox.start = start
        _targetBox.open()
    }

    function undo() {
        return _model.undo()
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

    // Enter: the picked drop-down line (a suggestion, a recent search or
    // Clear recent searches), else the picked (or first) result.
    function enter() {
        if (_suggest.visible && _suggestAt >= 0) {
            if (showingRecent && _suggestAt >= dropList.length)
                clearRecent()
            else
                takeSuggestion(dropList[_suggestAt])
        } else
            open(current)
    }

    function clearRecent() {
        _model.clearRecent()
        _suggestAt = -1
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
        if (_targetBox.visible) { _targetBox.close(); return }
        if (_openMessage.visible) { _openMessage.close(); return }
        if (_help.visible) { _help.close(); return }
        if (_unreadablePopup.visible) { _unreadablePopup.close(); return }
        if (_suggest.visible) { _suggest.close(); _suggestDismissed = true; return }
        if (listening) { _model.stopListen(); return }
        if (String(_box.text).length) {
            // Esc again closes: the recent list stays shut until asked for.
            _suggestDismissed = true
            _model.text = ""
            _box.text = ""
            focusBox()
            return
        }
        _root.close()
    }

    // The drop-down under the box: recent searches while the box is empty
    // (with Clear recent searches at the end), suggestions while typing
    // (only when the setting is on).
    property bool _suggestDismissed: false
    property int _suggestAt: -1
    readonly property var suggestionList: _model.suggestionsOn ? (_model.suggestions || []) : []
    readonly property var recentList: _model.recent || []
    readonly property bool showingRecent: String(_box.text).length === 0
    readonly property var dropList: showingRecent ? recentList : suggestionList
    // The lines arrow keys move through (Clear recent searches included).
    readonly property int dropCount: dropList.length + (showingRecent && dropList.length > 0 ? 1 : 0)
    onShowingRecentChanged: _suggestAt = -1

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
    // Undo of this window's binding edits (01 S195).
    Shortcut {
        sequences: [StandardKey.Undo]
        enabled: !!_model.canUndo && !_box.activeFocus
        onActivated: _root.undo()
    }

    Component.onCompleted: {
        _box.text = _model.text || ""
        Qt.callLater(focusBox)
    }
    onClosing: _model.close()
    onActiveChanged: if (active && !_box.activeFocus && current < 0) focusBox()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Style.dp(10)
        spacing: Style.dp(6)

        // The box, the match toggles, ? and Listen.
        RowLayout {
            Layout.fillWidth: true
            spacing: Style.dp(4)

            Button {
                objectName: "searchListenButton"
                text: _root.listening ? "Stop" : "Listen"
                highlighted: _root.listening
                focusPolicy: Qt.NoFocus
                ToolTip.visible: hovered
                ToolTip.text: "Press a control, a key or an OSC button to search for it"
                onClicked: _root.toggleListen()
            }
            TextField {
                id: _box
                objectName: "searchBox"
                Layout.fillWidth: true
                placeholderText: "Search keys, actions, names and outputs…"
                selectByMouse: true
                onPressed: _root._suggestDismissed = false
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
                        _root._suggestAt = Math.min(_root.dropCount - 1,
                                                    _root._suggestAt + 1)
                    else
                        _root.move(1)
                }
                Keys.onReturnPressed: _root.enter()
                Keys.onEnterPressed: _root.enter()
                // Ctrl+Z: the box's own typing first, then Search's edits.
                Keys.onPressed: (event) => {
                    if (event.matches(StandardKey.Undo) && !_box.canUndo && !!_model.canUndo) {
                        _root.undo()
                        event.accepted = true
                    }
                }
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
                // The status line already gives the counts when it has text.
                visible: _root.typed && String(_model.statusText || "").length === 0
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
            CheckBox {
                objectName: "searchSuggestionsOn"
                focusPolicy: Qt.NoFocus
                text: "Suggestion list while typing"
                checked: !!_model.suggestionsOn
                onToggled: {
                    _model.suggestionsOn = checked
                    checked = Qt.binding(() => !!_model.suggestionsOn)
                }
                ToolTip.visible: hovered
                ToolTip.text: "Show a list of matching names under the search box as you type"
            }
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
                clip: true

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
                                    readonly property real fixedWidth: column === "input"
                                        ? _list.inputWidth - Style.dp(38)
                                        : (column === "mode" ? _list.modeWidth : -1)
                                    Layout.preferredWidth: fixedWidth
                                    Layout.minimumWidth: fixedWidth < 0 ? 0 : fixedWidth
                                    Layout.maximumWidth: fixedWidth < 0 ? Number.POSITIVE_INFINITY : fixedWidth
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
                        // One width for every row and the headings (01 S196);
                        // a narrow list still leaves the action room.
                        readonly property real inputWidth: Math.min(Math.max(Style.dp(160), width * 0.32),
                                                                    width * 0.4)
                        readonly property real modeWidth: Math.min(Math.max(Style.dp(80), width * 0.14),
                                                                   width * 0.2)
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

                // First open: what Search does and examples, only while
                // nothing is typed and no results show (01 S196).
                ColumnLayout {
                    objectName: "searchFirstOpen"
                    visible: !_root.typed && !_root.listening && _list.count === 0
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
                fixes: { _root.detailRevision; return _root.fixesOf(_root.current) }
                canUndo: !!_model.canUndo
                onRemoveClicked: _root.askRemove(_root.current)
                onChangeTargetClicked: _root.askChangeTarget(_root.current)
                onUndoClicked: _root.undo()
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

    // The drop-down under the box: recent searches (box empty) or the
    // suggestion list (setting, off by default) while typing.
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
                 && _root.dropList.length > 0
        background: Rectangle { color: Style.menuBg; border.color: Style.menuLine }
        contentItem: ColumnLayout {
            spacing: 0
            Repeater {
                model: _root.dropList
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
            Rectangle {
                objectName: "searchClearRecent"
                visible: _root.showingRecent
                Layout.fillWidth: true
                implicitHeight: _clearText.implicitHeight + Style.dp(6)
                readonly property bool lit: _root._suggestAt === _root.dropList.length
                                            || _clearMouse.containsMouse
                color: lit ? Style.menuHover : Style.clear
                Rectangle {
                    anchors.top: parent.top
                    width: parent.width
                    height: Style.dp(1)
                    color: Style.menuLine
                }
                Label {
                    id: _clearText
                    anchors.verticalCenter: parent.verticalCenter
                    x: Style.dp(8)
                    text: "Clear recent searches"
                    color: Style.menuTextSoft
                }
                MouseArea {
                    id: _clearMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: _root.clearRecent()
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
        property var fixes: ({})
        onAboutToShow: fixes = _root.fixesOf(_root.current)
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
        ThemedMenuItem {
            objectName: "searchRemoveBinding"
            text: "Remove binding…"
            visible: !!_rowMenu.fixes.remove
            height: visible ? implicitHeight : 0
            onTriggered: _root.askRemove(_root.current)
        }
        ThemedMenuItem {
            objectName: "searchChangeTarget"
            text: "Change target…"
            visible: !!_rowMenu.fixes.changeTarget
            height: visible ? implicitHeight : 0
            onTriggered: _root.askChangeTarget(_root.current)
        }
        ThemedMenuItem {
            objectName: "searchUndo"
            text: "Undo"
            hint: "Ctrl+Z"
            visible: !!_model.canUndo
            height: visible ? implicitHeight : 0
            onTriggered: _root.undo()
        }
    }

    // Open on an unplugged device, a refused edit (01 S195).
    Popup {
        id: _openMessage
        objectName: "searchOpenMessage"
        property alias text: _openMessageText.text
        property alias title: _openMessageTitle.text
        modal: true
        anchors.centerIn: Overlay.overlay
        width: Math.min(_root.width - Style.dp(40), Style.dp(460))
        padding: Style.dp(16)
        background: Rectangle { color: Style.background; border.color: Style.line; radius: Style.dp(4) }
        contentItem: ColumnLayout {
            spacing: Style.dp(12)
            Label {
                id: _openMessageTitle
                objectName: "searchOpenMessageTitle"
                Layout.fillWidth: true
                visible: text.length > 0
                wrapMode: Text.Wrap
                font.bold: true
                color: Style.fg
            }
            Label {
                id: _openMessageText
                objectName: "searchOpenMessageText"
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: Style.fg
            }
            Button {
                Layout.alignment: Qt.AlignRight
                text: "OK"
                onClicked: _openMessage.close()
            }
        }
    }

    // Change target…: a Map to vJoy action's vJoy device and input, only
    // what can be sent (01 S195).
    Popup {
        id: _targetBox
        objectName: "searchTargetBox"
        property int row: -1
        property var start: ({})
        property int vjoyId: 0
        property string inputType: ""
        property int inputId: 0
        modal: true
        anchors.centerIn: Overlay.overlay
        width: Math.min(_root.width - Style.dp(40), Style.dp(460))
        padding: Style.dp(16)
        onOpened: {
            vjoyId = Number(start.vjoyId || 0)
            inputType = String(start.inputType || "")
            inputId = Number(start.inputId || 0)
            _targetPicker.active = false
            _targetPicker.active = true
        }
        onClosed: _targetPicker.active = false
        background: Rectangle { color: Style.background; border.color: Style.line; radius: Style.dp(4) }
        contentItem: ColumnLayout {
            spacing: Style.dp(12)
            Label {
                Layout.fillWidth: true
                text: "Change target"
                font.bold: true
                color: Style.fg
            }
            Loader {
                id: _targetPicker
                active: false
                Layout.fillWidth: true
                Layout.minimumWidth: Style.dp(220)
                sourceComponent: VJoySelector {
                    validTypes: [String(_targetBox.start.inputType || "button")]
                    onSelectionChanged: (vjoyId, inputType, inputId) => {
                        _targetBox.vjoyId = vjoyId
                        _targetBox.inputType = inputType
                        _targetBox.inputId = inputId
                    }
                    Component.onCompleted: initialize(Number(_targetBox.start.vjoyId || 0),
                                                      String(_targetBox.start.inputType || ""),
                                                      Number(_targetBox.start.inputId || 0))
                }
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: Style.dp(8)
                Button {
                    objectName: "searchTargetOk"
                    text: "Change"
                    enabled: _targetBox.vjoyId > 0
                    onClicked: {
                        _model.changeTarget(_targetBox.row, _targetBox.vjoyId,
                                            _targetBox.inputType, _targetBox.inputId)
                        _targetBox.close()
                    }
                }
                Button {
                    objectName: "searchTargetCancel"
                    text: "Cancel"
                    onClicked: _targetBox.close()
                }
            }
        }
    }
}
