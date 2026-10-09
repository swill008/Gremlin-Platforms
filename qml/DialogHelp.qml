// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// The one Help window (01 S128, S137; D-01-ONE-HELP): the book of chapters
// from help/index.js. chapter "" shows the whole book; an area's Help (F1)
// opens it on that area's chapter only, with View Full Help to widen it.
// Open › / Show me › links (S139) go to the program through Style.helpLinks.

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Style
import Gremlin.UI
import "help/index.js" as Book
import "help_search.js" as HelpSearch
import "help_links.js" as HelpLinks

ApplicationWindow {
    font.pixelSize: Style.fontSize
    id: _win

    EscapeCloses { host: _win }
    // ToolWindowMemory sets the saved or default size when the window opens.
    width: 980
    height: 680
    minimumWidth: Style.fitWidth(Style.dp(760), Screen)
    minimumHeight: Style.fitHeight(Style.dp(480), Screen)
    title: chapter.length ? qsTr("Help") + " — " + _chapterTitle(chapter) : qsTr("Help")
    color: Style.background
    U.Universal.theme: Style.theme

    ToolWindowMemory {
        host: _win
        name: "help"
        defaultWidth: Style.dp(980)
        defaultHeight: Style.dp(680)
    }

    // The chapter shown ("" = the whole book). Set by whoever opens Help.
    property string chapter: ""
    // A topic to show on opening (its id), optional.
    property string topicId: ""

    // The chapter View Full Help widened from, for the way back.
    property string _backChapter: ""
    property bool _widening: false

    // The chapter's topics (the whole book when chapter is "").
    property var _topics: Book.topics(chapter)
    // The whole book: what the search bar searches.
    readonly property var _book: Book.topics("")
    property string _currentId: ""
    readonly property var _current: _currentId.length ? Book.find(_currentId) : null

    // Search state: [{topic, count, bodyTotal}] in list order, scoped
    // chapter first, then (Search all of Help) the other chapters.
    // Set in Component.onCompleted: a [] here is a binding, and assigning
    // later would overwrite it (qt.qml.binding.removal).
    property var _results: null
    readonly property bool _searching: HelpSearch.words(_search.text).length > 0
    property int _match: 0

    readonly property var _rows: _buildRows(_searching ? (_results || []) : _topics,
                                             _searching, _folded || {}, !chapter.length)

    // The list's width (S138): dragged with the handle, one width for all
    // of Help, kept for next time. Set in Component.onCompleted.
    property int listWidth: 0
    readonly property int _listMin: Style.dp(180)

    // Folded chapters (S138), {chapterId: true}, kept while Help is open.
    property var _folded: null

    // Program links (S139): why each open:/show: link of the open topic
    // can't be shown now ({href: reason}; none = it can), and the reason
    // from the last click that failed, shown under the title.
    property var _linkReasons: ({})
    property string _linkNote: ""
    readonly property string hoverReason: _body.hoveredLink.length
                                          ? (_linkReasons[_body.hoveredLink] || "") : ""

    WindowPlacement { id: _place }

    function _defaultListWidth() {
        return Style.dp(290)
    }

    function _listMax() {
        return Math.max(_listMin, Math.floor(width / 2))
    }

    function _applyListWidth(w) {
        listWidth = Math.round(Math.max(_listMin, Math.min(_listMax(), w)))
    }

    function _saveListWidth() {
        var state = {}
        try {
            state = JSON.parse(_place.toolRowState("help-list")) || {}
        } catch (e) {
            state = {}
        }
        state.listWidth = listWidth
        _place.saveToolRowState("help-list", JSON.stringify(state))
    }

    function setListWidth(w) {
        _applyListWidth(w)
        _saveListWidth()
    }

    function resetListWidth() {
        setListWidth(_defaultListWidth())
    }

    function _restoreListWidth() {
        var saved = 0
        try {
            saved = Number((JSON.parse(_place.toolRowState("help-list")) || {}).listWidth) || 0
        } catch (e) {
            saved = 0
        }
        listWidth = Math.round(Math.max(_listMin, saved > 0 ? saved : _defaultListWidth()))
    }

    function isFolded(id) {
        return !!(_folded && _folded[id])
    }

    function toggleChapter(id) {
        var m = Object.assign({}, _folded || {})
        if (m[id])
            delete m[id]
        else
            m[id] = true
        _folded = m
        _scrollListToCurrent()
    }

    function _unfold(id) {
        if (!isFolded(id))
            return
        var m = Object.assign({}, _folded)
        delete m[id]
        _folded = m
    }

    function expandAll() {
        _folded = {}
        _scrollListToCurrent()
    }

    function collapseAll() {
        var m = {}
        var all = Book.chapters()
        for (var i = 0; i < all.length; ++i)
            m[all[i].id] = true
        _folded = m
    }

    // The whole book opens with only the open topic's chapter unfolded.
    function _foldAllButCurrent() {
        collapseAll()
        if (_current)
            _unfold(_current.chapterId)
        _scrollListToCurrent()
    }

    onChapterChanged: {
        if (!_widening)
            _backChapter = ""
        // Book.topics, not _topics: that binding may not have updated yet.
        var list = Book.topics(chapter)
        if (!_current || (chapter.length && _current.chapterId !== chapter && !_searching))
            _currentId = list.length ? list[0].id : ""
        if (!chapter.length)
            _foldAllButCurrent()
    }
    onTopicIdChanged: if (topicId.length) showTopic(topicId)

    on_CurrentIdChanged: {
        _linkNote = ""
        recheckLinks()
    }
    onActiveChanged: if (active) recheckLinks()

    Connections {
        target: Style
        function onHelpLinksChanged() { _win.recheckLinks() }
    }

    Component.onCompleted: {
        recheckLinks()
        _results = []
        _folded = {}
        _restoreListWidth()
        if (topicId.length && Book.find(topicId))
            _currentId = topicId
        else if (_topics.length)
            _currentId = _topics[0].id
        if (!chapter.length)
            _foldAllButCurrent()
    }

    function _chapterTitle(id) {
        var all = Book.chapters()
        for (var i = 0; i < all.length; ++i)
            if (all[i].id === id)
                return all[i].title
        return ""
    }

    // View Full Help: the whole book, keeping the topic; "Only <chapter>"
    // goes back.
    function viewFullHelp() {
        if (!chapter.length)
            return
        var back = chapter
        _widening = true
        chapter = ""
        _widening = false
        _backChapter = back
        _scrollListToCurrent()
    }

    function viewChapterOnly() {
        if (!_backChapter.length)
            return
        chapter = _backChapter
        _scrollListToCurrent()
    }

    // Shows a topic by id (links, Related topics, the list).
    function showTopic(id) {
        var t = Book.find(id)
        if (!t)
            return
        _currentId = t.id
        _unfold(t.chapterId)
        _match = 0
        _scrollListToCurrent()
        _scrollBodyToMatch()
    }

    // The list rows: a heading per chapter, then per section, then topics.
    // A folded chapter (S138) shows only its heading; while searching every
    // chapter with a match shows unfolded. canFold: the whole book is shown.
    function _buildRows(items, searching, folded, canFold) {
        var rows = []
        var lastChapter = null, lastSection = null
        for (var i = 0; i < items.length; ++i) {
            var t = searching ? items[i].topic : items[i]
            var shut = canFold && !searching && !!folded[t.chapterId]
            if (t.chapterId !== lastChapter) {
                rows.push({ kind: "chapter", text: t.chapter, id: "", count: 0,
                            chapterId: t.chapterId, folded: shut,
                            canFold: canFold && !searching })
                lastChapter = t.chapterId
                lastSection = null
            }
            if (shut)
                continue
            if (t.section !== lastSection) {
                rows.push({ kind: "section", text: t.section, id: "", count: 0,
                            chapterId: t.chapterId, first: lastSection === null })
                lastSection = t.section
            }
            rows.push({ kind: "topic", text: t.title, id: t.id, chapterId: t.chapterId,
                        count: searching ? items[i].count : 0 })
        }
        return rows
    }

    function _rowOf(id) {
        for (var i = 0; i < _rows.length; ++i)
            if (_rows[i].kind === "topic" && _rows[i].id === id)
                return i
        return -1
    }

    function _scrollListToCurrent() {
        Qt.callLater(function() {
            var r = _rowOf(_currentId)
            if (r >= 0)
                _list.positionViewAtIndex(r, ListView.Contain)
        })
    }

    // Find colours, as a browser's find: the same in both themes, dark text.
    function _matchColors() {
        return [String(Style.findMatch), String(Style.findCurrent), String(Style.onLight)]
    }

    function _highlight(body, current) {
        var c = _matchColors()
        return HelpSearch.highlight(body, _search.text, current, c[0], c[1], c[2])
    }

    // The bar's results (S137): [{index into the book, count, chapterId,
    // inScope}] in book order; [] = no search, every topic shows.
    function _applyResults(results) {
        // Read the text, not _searching: the bar sends its results from its
        // own textChanged, before that binding has caught up (a pasted word
        // showed an empty list).
        var searching = HelpSearch.words(_search.text).length > 0
        if (!searching || !results || !results.length) {
            _results = []
            _match = 0
            // Back to the folds as they were, with the open topic showing.
            if (!searching && _current)
                _unfold(_current.chapterId)
            return
        }
        var res = []
        for (var i = 0; i < results.length; ++i) {
            var t = _book[results[i].index]
            if (!t)
                continue
            res.push({ topic: t, count: results[i].count,
                       bodyTotal: _highlight(t.body, -1).total })
        }
        _results = res
        _match = 0
        // The open topic stays when it matches; else the first match opens.
        if (_resultIndex(_currentId) < 0 && res.length)
            _currentId = res[0].topic.id
        _scrollListToCurrent()
        _scrollBodyToMatch()
    }

    function _resultIndex(id) {
        for (var i = 0; i < _results.length; ++i)
            if (_results[i].topic.id === id)
                return i
        return -1
    }

    // Enter / F3 (+1), Shift+F3 (-1): the next match, on into the next topic.
    function step(d) {
        if (!_searching || !_results.length)
            return
        var nextMatch = _match + d
        if (nextMatch >= 0 && nextMatch < _bodyTotal) {
            _match = nextMatch
            _scrollBodyToMatch()
            return
        }
        var at = _resultIndex(_currentId)
        var len = _results.length
        for (var n = 1; n <= len; ++n) {
            var j = at < 0 ? (d > 0 ? n - 1 : len - n) : (((at + d * n) % len) + len) % len
            var r = _results[j]
            if (r.bodyTotal > 0 || n === len) {
                _currentId = r.topic.id
                _match = d > 0 ? 0 : Math.max(0, r.bodyTotal - 1)
                _scrollListToCurrent()
                _scrollBodyToMatch()
                return
            }
        }
    }

    // "k of n" over every listed topic's matches.
    readonly property int _matchTotal: {
        var n = 0
        for (var i = 0; i < _results.length; ++i)
            n += _results[i].bodyTotal
        return n
    }
    readonly property int _matchNumber: {
        if (!_searching || _bodyTotal === 0)
            return 0
        var at = _resultIndex(_currentId)
        if (at < 0)
            return 0
        var k = 0
        for (var i = 0; i < at; ++i)
            k += _results[i].bodyTotal
        return k + _match + 1
    }

    // The open topic's text, its matches highlighted while searching.
    readonly property var _shown: {
        if (!_current)
            return { html: "", total: 0 }
        var css = "<style>a { color: " + String(Style.accent) + "; text-decoration: none; }"
                + " h3 { margin-top: 14px; }</style>"
        var body = HelpLinks.decorate(_current.body, _linkReasons, String(Style.fgDisabled))
        if (!_searching)
            return { html: css + body, total: 0 }
        var h = _highlight(body, _match)
        return { html: css + h.html, total: h.total }
    }
    readonly property int _bodyTotal: _shown.total

    // Scrolls the body to the current match (or the top).
    function _scrollBodyToMatch() {
        Qt.callLater(function() {
            if (!_searching) {
                _bodyFlick.contentY = 0
                return
            }
            var pos = _matchPosition(_match)
            if (pos < 0) {
                _bodyFlick.contentY = 0
                return
            }
            var r = _body.positionToRectangle(pos)
            var y = _body.y + r.y
            var view = _bodyFlick.height
            if (y < _bodyFlick.contentY || y + r.height > _bodyFlick.contentY + view) {
                var maxY = Math.max(0, _bodyFlick.contentHeight - view)
                _bodyFlick.contentY = Math.max(0, Math.min(maxY, y - view / 3))
            }
        })
    }

    // The text position of the n-th match in the shown body.
    function _matchPosition(n) {
        var words = HelpSearch.words(_search.text)
        if (!words.length)
            return -1
        var text = String(_body.getText(0, _body.length)).toLowerCase()
        var hits = []
        for (var w = 0; w < words.length; ++w) {
            var from = 0
            while (true) {
                var at = text.indexOf(words[w], from)
                if (at < 0)
                    break
                hits.push([at, at + words[w].length])
                from = at + Math.max(1, words[w].length)
            }
        }
        hits.sort(function(a, b) { return a[0] - b[0] || b[1] - a[1] })
        var kept = [], end = -1
        for (var i = 0; i < hits.length; ++i) {
            if (hits[i][0] >= end) {
                kept.push(hits[i][0])
                end = hits[i][1]
            }
        }
        return n < kept.length ? kept[n] : (kept.length ? kept[kept.length - 1] : -1)
    }

    // Why a program link can't be shown now; "" when it can.
    function linkReason(link) {
        var p = HelpLinks.parse(link)
        if (p.kind === "open" && !HelpLinks.isAllowedOpen(p.parts[0]))
            return qsTr("Help can't open this window.")
        var bridge = Style.helpLinks
        if (!bridge)
            return qsTr("The main window isn't open.")
        try {
            return String(bridge.check(String(link)) || "")
        } catch (e) {
            return qsTr("This can't be shown now.")
        }
    }

    // Checks the open topic's program links again (topic opened, Help
    // activated, the bridge changed).
    function recheckLinks() {
        var reasons = {}
        // Book.find, not _current: that binding may not have updated yet.
        var topic = _currentId.length ? Book.find(_currentId) : null
        var links = topic ? HelpLinks.programLinks(topic.body) : []
        for (var i = 0; i < links.length; ++i) {
            var r = linkReason(links[i])
            if (r.length)
                reasons[links[i]] = r
        }
        _linkReasons = reasons
    }

    function _openLink(link) {
        var s = String(link)
        if (s.indexOf("topic:") === 0) {
            showTopic(s.substring(6))
        } else if (HelpLinks.isProgramLink(s)) {
            // Help stays open; the program shows the target beside it.
            var reason = linkReason(s)
            if (!reason.length) {
                try {
                    reason = String(Style.helpLinks.reveal(s) || "")
                } catch (e) {
                    reason = qsTr("This can't be shown now.")
                }
            }
            _linkNote = reason
            if (reason.length)
                recheckLinks()
        } else if (s.length) {
            Qt.openUrlExternally(s)
        }
    }

    // Ctrl+F: the search box's own (SearchBox, 01 S141).
    Shortcut { sequence: "F3"; onActivated: _win.step(1) }
    Shortcut { sequence: "Shift+F3"; onActivated: _win.step(-1) }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Style.dp(12)
        spacing: Style.dp(10)

        // The search bar (S137) and the book's scope.
        RowLayout {
            Layout.fillWidth: true
            spacing: Style.dp(12)

            HelpSearchBar {
                id: _search
                objectName: "helpSearchBar"
                Layout.fillWidth: true
                topics: _win._book
                scopedChapter: _win.chapter
                // 0-based ("k of n"); -1 when no match is shown.
                current: _win._matchNumber - 1
                total: _win._matchTotal
                onResultsChanged: (results) => _win._applyResults(results)
                onNext: _win.step(1)
                onPrevious: _win.step(-1)
                // View Full Help / Only <chapter> start the scope row, before
                // Search all of Help, where they are seen (S128).
                scopeButton: Component {
                    RowLayout {
                        spacing: 0
                        Button {
                            id: _full
                            objectName: "viewFullHelp"
                            visible: _win.chapter.length > 0
                            text: qsTr("View Full Help")
                            onClicked: _win.viewFullHelp()
                        }
                        Button {
                            id: _only
                            objectName: "viewChapterOnly"
                            visible: !_win.chapter.length && _win._backChapter.length > 0
                            text: qsTr("Only %1").arg(_win._chapterTitle(_win._backChapter))
                            onClicked: _win.viewChapterOnly()
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            // The contents: chapters, their sections, their topics (S138:
            // resizable, chapters fold).
            ColumnLayout {
                id: _listPane
                objectName: "helpListPane"
                Layout.preferredWidth: _win.listWidth
                Layout.maximumWidth: _win.listWidth
                Layout.fillHeight: true
                spacing: Style.dp(4)

                RowLayout {
                    Layout.fillWidth: true
                    visible: !_win.chapter.length && !_win._searching
                    spacing: Style.dp(4)
                    Button {
                        objectName: "expandAll"
                        flat: true
                        text: qsTr("Expand all")
                        font.pixelSize: Style.dp(12)
                        onClicked: _win.expandAll()
                    }
                    Button {
                        objectName: "collapseAll"
                        flat: true
                        text: qsTr("Collapse all")
                        font.pixelSize: Style.dp(12)
                        onClicked: _win.collapseAll()
                    }
                    Item { Layout.fillWidth: true }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: Style.bgPage
                    border.color: Style.line
                    radius: Style.dp(3)

                    ListView {
                        id: _list
                        objectName: "helpContents"
                        anchors.fill: parent
                        anchors.margins: Style.dp(6)
                        clip: true
                        model: _win._rows
                        boundsBehavior: Flickable.StopAtBounds
                        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                        delegate: Item {
                            id: _row
                            required property var modelData
                            required property int index
                            readonly property string kind: modelData.kind
                            width: _list.width
                            height: kind === "topic" ? _topicRow.height
                                  : kind === "chapter" ? _chapterRow.height
                                  : _sectionRow.height

                            // Chapter: a shaded band with an accent bar; a
                            // click folds or unfolds it.
                            Item {
                                id: _chapterRow
                                objectName: "helpChapterRow"
                                visible: _row.kind === "chapter"
                                width: parent.width
                                height: _band.height + (_row.index === 0 ? 0 : Style.dp(8))
                                Rectangle {
                                    id: _band
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.bottom: parent.bottom
                                    height: _chapterLabel.implicitHeight + Style.dp(12)
                                    color: _chapterMouse.containsMouse && _row.modelData.canFold
                                           ? Style.bgHover : Style.bgRaised
                                    radius: Style.dp(2)
                                    Rectangle {
                                        width: Style.dp(3)
                                        height: parent.height
                                        color: Style.accent
                                    }
                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: Style.dp(10)
                                        anchors.rightMargin: Style.dp(8)
                                        spacing: Style.dp(6)
                                        Label {
                                            visible: !!_row.modelData.canFold
                                            text: _row.modelData.folded ? "▸" : "▾"
                                            color: Style.fgMuted
                                            font.pixelSize: Style.dp(13)
                                        }
                                        Label {
                                            id: _chapterLabel
                                            Layout.fillWidth: true
                                            text: _row.modelData.text
                                            elide: Text.ElideRight
                                            color: Style.fgStrong
                                            font.pixelSize: Style.dp(16)
                                            font.bold: true
                                        }
                                    }
                                    MouseArea {
                                        id: _chapterMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        enabled: !!_row.modelData.canFold
                                        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                        onClicked: _win.toggleChapter(_row.modelData.chapterId)
                                    }
                                }
                            }

                            // Section: small capitals in the accent colour,
                            // a thin line above (not under the chapter band).
                            Item {
                                id: _sectionRow
                                visible: _row.kind === "section"
                                width: parent.width
                                height: _sectionLabel.implicitHeight + Style.dp(10)
                                Rectangle {
                                    visible: !_row.modelData.first
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.leftMargin: Style.dp(10)
                                    anchors.top: parent.top
                                    anchors.topMargin: Style.dp(3)
                                    height: 1
                                    color: Style.line
                                }
                                Label {
                                    id: _sectionLabel
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.bottom: parent.bottom
                                    leftPadding: Style.dp(10)
                                    bottomPadding: Style.dp(2)
                                    text: _row.modelData.text
                                    elide: Text.ElideRight
                                    color: Style.accent
                                    font.pixelSize: Style.dp(11)
                                    font.bold: true
                                    font.capitalization: Font.AllUppercase
                                    font.letterSpacing: Style.dp(0.6)
                                }
                            }

                            // Topic: a single-spaced row.
                            Rectangle {
                                id: _topicRow
                                objectName: "helpTopicRow"
                                visible: _row.kind === "topic"
                                readonly property bool current: _row.kind === "topic"
                                                                && _row.modelData.id === _win._currentId
                                width: parent.width
                                height: _topicLabel.implicitHeight + Style.dp(6)
                                radius: Style.dp(2)
                                color: current ? Style.accent
                                     : _topicMouse.containsMouse ? Style.bgHover : Style.clear
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: Style.dp(18)
                                    anchors.rightMargin: Style.dp(8)
                                    spacing: Style.dp(6)
                                    Label {
                                        id: _topicLabel
                                        Layout.fillWidth: true
                                        text: _row.modelData.text
                                        elide: Text.ElideRight
                                        color: _topicRow.current ? Style.onColor : Style.fg
                                        font.pixelSize: Style.dp(13)
                                    }
                                    Label {
                                        visible: _row.modelData.count > 0
                                        text: String(_row.modelData.count)
                                        color: _topicRow.current ? Style.onColor : Style.fgMuted
                                        font.pixelSize: Style.dp(12)
                                    }
                                }
                                MouseArea {
                                    id: _topicMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: _win.showTopic(_row.modelData.id)
                                }
                            }
                        }
                    }
                }
            }

            // The handle between the list and the topic (S138): drag to
            // resize, double-click for the default width.
            Item {
                id: _handle
                objectName: "helpListHandle"
                Layout.preferredWidth: Style.dp(12)
                Layout.fillHeight: true
                Rectangle {
                    anchors.centerIn: parent
                    width: Style.dp(2)
                    height: Style.dp(36)
                    radius: Style.dp(1)
                    color: _handleMouse.containsMouse || _handleMouse.pressed ? Style.accent : Style.lineStrong
                }
                MouseArea {
                    id: _handleMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.SplitHCursor
                    property real _startX: 0
                    property int _startWidth: 0
                    onPressed: (mouse) => {
                        _startX = mapToItem(null, mouse.x, 0).x
                        _startWidth = _win.listWidth
                    }
                    onPositionChanged: (mouse) => {
                        if (pressed)
                            _win._applyListWidth(_startWidth + mapToItem(null, mouse.x, 0).x - _startX)
                    }
                    onReleased: _win._saveListWidth()
                    onDoubleClicked: _win.resetListWidth()
                }
            }

            // The open topic: where it is, its title, its text, Related topics.
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: Style.dp(4)

                Label {
                    objectName: "topicPlace"
                    Layout.fillWidth: true
                    text: _win._current ? _win._current.chapter + "  ›  " + _win._current.section : ""
                    color: Style.fgMuted
                    font.pixelSize: Style.dp(12)
                    elide: Text.ElideRight
                }
                Label {
                    objectName: "topicTitle"
                    Layout.fillWidth: true
                    Layout.bottomMargin: Style.dp(6)
                    text: _win._current ? _win._current.title : ""
                    color: Style.fgStrong
                    font.pixelSize: Style.dp(22)
                    font.bold: true
                    wrapMode: Text.WordWrap
                }
                // Why the last Open › / Show me › click showed nothing.
                Label {
                    objectName: "linkNote"
                    Layout.fillWidth: true
                    Layout.bottomMargin: Style.dp(4)
                    visible: _win._linkNote.length > 0
                    text: _win._linkNote
                    color: Style.fgMuted
                    font.pixelSize: Style.dp(13)
                    wrapMode: Text.WordWrap
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: Style.bgPage
                    border.color: Style.line
                    radius: Style.dp(3)

                    Flickable {
                        id: _bodyFlick
                        anchors.fill: parent
                        anchors.margins: Style.dp(16)
                        clip: true
                        contentWidth: width
                        contentHeight: _bodyColumn.implicitHeight
                        boundsBehavior: Flickable.StopAtBounds
                        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                        ColumnLayout {
                            id: _bodyColumn
                            width: _bodyFlick.width - Style.dp(10)
                            spacing: Style.dp(10)

                            TextEdit {
                                id: _body
                                objectName: "topicBody"
                                Layout.fillWidth: true
                                readOnly: true
                                selectByMouse: true
                                activeFocusOnPress: false
                                text: _win._shown.html
                                textFormat: TextEdit.RichText
                                wrapMode: TextEdit.Wrap
                                color: Style.fg
                                selectionColor: Style.bgSelected
                                font.pixelSize: Style.dp(14)
                                onLinkActivated: (link) => _win._openLink(link)
                                HoverHandler {
                                    cursorShape: _body.hoveredLink.length ? Qt.PointingHandCursor : Qt.IBeamCursor
                                }
                                // A greyed link says why on hover (S139).
                                PointerTip {
                                    objectName: "linkTip"
                                    text: _win.hoverReason
                                }
                            }

                            // Related topics, as links under the body.
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.topMargin: Style.dp(6)
                                implicitHeight: 1
                                color: Style.line
                                visible: _related.count > 0
                            }
                            Label {
                                visible: _related.count > 0
                                text: qsTr("Related topics")
                                color: Style.fgStrong
                                font.pixelSize: Style.dp(14)
                                font.bold: true
                            }
                            Repeater {
                                id: _related
                                model: {
                                    var out = []
                                    var ids = _win._current && _win._current.related ? _win._current.related : []
                                    for (var i = 0; i < ids.length; ++i) {
                                        var t = Book.find(ids[i])
                                        if (t)
                                            out.push({ id: t.id, title: t.title })
                                    }
                                    return out
                                }
                                delegate: Label {
                                    id: _link
                                    required property var modelData
                                    objectName: "relatedLink"
                                    Layout.leftMargin: Style.dp(4)
                                    text: modelData.title
                                    color: Style.accent
                                    font.pixelSize: Style.dp(14)
                                    font.underline: _linkHover.hovered
                                    HoverHandler { id: _linkHover; cursorShape: Qt.PointingHandCursor }
                                    TapHandler { onTapped: _win.showTopic(_link.modelData.id) }
                                }
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.topMargin: Style.dp(6)
                    Item { Layout.fillWidth: true }
                    Button {
                        text: qsTr("Close")
                        onClicked: _win.close()
                    }
                }
            }
        }
    }
}
