// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// The one Help window (01 S128, S137; D-01-ONE-HELP): the book of chapters
// from help/index.js. chapter "" shows the whole book; an area's Help (F1)
// opens it on that area's chapter only, with View Full Help to widen it.

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Style
import "help/index.js" as Book
import "help_search.js" as HelpSearch

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
    property var _results: []
    readonly property bool _searching: HelpSearch.words(_search.text).length > 0
    property int _match: 0

    readonly property var _rows: _buildRows(_searching ? _results : _topics, _searching)

    onChapterChanged: {
        if (!_widening)
            _backChapter = ""
        // Book.topics, not _topics: that binding may not have updated yet.
        var list = Book.topics(chapter)
        if (!_current || (chapter.length && _current.chapterId !== chapter && !_searching))
            _currentId = list.length ? list[0].id : ""
    }
    onTopicIdChanged: if (topicId.length) showTopic(topicId)

    Component.onCompleted: {
        if (topicId.length && Book.find(topicId))
            _currentId = topicId
        else if (_topics.length)
            _currentId = _topics[0].id
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
        _match = 0
        _scrollListToCurrent()
        _scrollBodyToMatch()
    }

    // The list rows: a heading per chapter, then per section, then topics.
    function _buildRows(items, searching) {
        var rows = []
        var lastChapter = null, lastSection = null
        for (var i = 0; i < items.length; ++i) {
            var t = searching ? items[i].topic : items[i]
            if (t.chapterId !== lastChapter) {
                rows.push({ kind: "chapter", text: t.chapter, id: "", count: 0 })
                lastChapter = t.chapterId
                lastSection = null
            }
            if (t.section !== lastSection) {
                rows.push({ kind: "section", text: t.section, id: "", count: 0 })
                lastSection = t.section
            }
            rows.push({ kind: "topic", text: t.title, id: t.id,
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
        if (!_searching || !results || !results.length) {
            _results = []
            _match = 0
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
        if (!_searching)
            return { html: css + _current.body, total: 0 }
        var h = _highlight(_current.body, _match)
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

    function _openLink(link) {
        var s = String(link)
        if (s.indexOf("topic:") === 0)
            showTopic(s.substring(6))
        else if (s.length)
            Qt.openUrlExternally(s)
    }

    Shortcut { sequences: [StandardKey.Find]; onActivated: _search.focusField() }
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
            }

            Button {
                objectName: "viewFullHelp"
                Layout.alignment: Qt.AlignTop
                visible: _win.chapter.length > 0
                text: qsTr("View Full Help")
                onClicked: _win.viewFullHelp()
            }
            Button {
                objectName: "viewChapterOnly"
                Layout.alignment: Qt.AlignTop
                visible: !_win.chapter.length && _win._backChapter.length > 0
                text: qsTr("Only %1").arg(_win._chapterTitle(_win._backChapter))
                onClicked: _win.viewChapterOnly()
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Style.dp(12)

            // The contents: chapters, their sections, their topics.
            Rectangle {
                Layout.preferredWidth: Style.dp(290)
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
                        readonly property bool isTopic: modelData.kind === "topic"
                        width: _list.width
                        height: isTopic ? _topicRow.implicitHeight : _heading.implicitHeight

                        Label {
                            id: _heading
                            visible: !_row.isTopic
                            width: parent.width
                            text: _row.modelData.text
                            elide: Text.ElideRight
                            color: _row.modelData.kind === "chapter" ? Style.fgStrong : Style.fgMuted
                            font.pixelSize: _row.modelData.kind === "chapter" ? Style.dp(17) : Style.dp(12)
                            font.bold: true
                            font.capitalization: _row.modelData.kind === "section" ? Font.AllUppercase : Font.MixedCase
                            font.letterSpacing: _row.modelData.kind === "section" ? Style.dp(0.5) : 0
                            leftPadding: Style.dp(8)
                            topPadding: _row.modelData.kind === "chapter" ? (_row.index === 0 ? Style.dp(4) : Style.dp(18)) : Style.dp(10)
                            bottomPadding: Style.dp(4)
                        }

                        ItemDelegate {
                            id: _topicRow
                            visible: _row.isTopic
                            width: parent.width
                            highlighted: _row.isTopic && _row.modelData.id === _win._currentId
                            leftPadding: Style.dp(16)
                            onClicked: _win.showTopic(_row.modelData.id)
                            contentItem: RowLayout {
                                spacing: Style.dp(6)
                                Label {
                                    Layout.fillWidth: true
                                    text: _row.modelData.text
                                    elide: Text.ElideRight
                                    color: Style.fg
                                    font.pixelSize: Style.dp(13)
                                }
                                Label {
                                    visible: _row.modelData.count > 0
                                    text: String(_row.modelData.count)
                                    color: Style.fgMuted
                                    font.pixelSize: Style.dp(12)
                                }
                            }
                        }
                    }
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
