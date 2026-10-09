// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// The Help window's search row (01 S137): the search box, "N topics match",
// the Search all of Help tick box (only when Help shows one chapter) and
// "k of n" with previous / next. The search box (SearchBox) gives Ctrl+F;
// the window owns F3 / Shift+F3,
// the topic list and the highlighting (help_search.highlight).
//
// topics: the whole book's topics ({title, body, chapterId, chapter}); the
// bar searches the scoped chapter's topics, or all of them with allOfHelp.
// resultsChanged(results): [{index, count, chapterId, inScope}] with index
// into topics, in topic order; [] for a blank search (show every topic).

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style
import "help_search.js" as HelpSearch

Item {
    id: _bar

    property var topics: []
    property string scopedChapter: ""
    property alias text: _field.text
    property bool allOfHelp: false
    // The current match (0-based) and the number of matches; set by the window.
    property int current: -1
    property int total: 0

    // The last results sent (read only for callers).
    readonly property var matches: _matches || []
    readonly property bool searching: HelpSearch.words(text).length > 0
    readonly property int topicCount: _inScopeCount

    // No [] here: an array literal is a binding, and _search() assigns it
    // (qt.qml.binding.removal).
    property var _matches: null
    property int _inScopeCount: 0

    signal resultsChanged(var results)
    signal next()
    signal previous()

    function focusField() {
        _field.focusField()
    }

    function clear() {
        _field.clear()
    }

    function _inScope(topic) {
        return _bar.scopedChapter === "" || _bar.allOfHelp
            || !topic || topic.chapterId === undefined
            || topic.chapterId === _bar.scopedChapter
    }

    function _search() {
        var all = HelpSearch.filter(_bar.topics || [], _field.text)
        var out = []
        var n = 0
        for (var i = 0; i < all.length; ++i) {
            var topic = _bar.topics[all[i].index]
            if (!_inScope(topic))
                continue
            var own = _bar.scopedChapter === "" || !topic
                || topic.chapterId === undefined || topic.chapterId === _bar.scopedChapter
            out.push({
                index: all[i].index,
                count: all[i].count,
                chapterId: topic && topic.chapterId !== undefined ? topic.chapterId : "",
                inScope: own
            })
            n += 1
        }
        _bar._inScopeCount = n
        _bar._matches = out
        _bar.resultsChanged(out)
    }

    onTopicsChanged: _search()
    onScopedChapterChanged: _search()
    onAllOfHelpChanged: {
        _allBox.checked = allOfHelp
        _search()
    }

    implicitHeight: _row.implicitHeight
    implicitWidth: _row.implicitWidth

    ColumnLayout {
        id: _row
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: Style.dp(4)

        // The shared search box (01 S141): its own Ctrl+F, × and Esc
        // (clears; the program then leaves the box, 01 S134). Its count line
        // stays off: the summary below says "N topics match".
        SearchBox {
            id: _field
            objectName: "helpSearchBox"
            Layout.fillWidth: true
            placeholder: "Search Help…"

            onTextChanged: _bar._search()
            onAccepted: if (_bar.total > 0) _bar.next()
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Style.dp(6)
            visible: _bar.searching || _allBox.visible

            Label {
                id: _summary
                objectName: "helpSearchSummary"
                Layout.fillWidth: true
                elide: Text.ElideRight
                visible: _bar.searching
                color: _bar._inScopeCount === 0 ? Style.fgMuted : Style.fgSoft
                text: _bar._inScopeCount === 0
                    ? "No topic mentions '" + _field.text.trim() + "'"
                    : _bar._inScopeCount === 1 ? "1 topic matches"
                    : _bar._inScopeCount + " topics match"
            }

            Item {
                Layout.fillWidth: true
                visible: !_summary.visible
            }

            Label {
                objectName: "helpSearchPosition"
                visible: _bar.searching && _bar.total > 0
                color: Style.fgSoft
                text: (_bar.current >= 0 ? _bar.current + 1 : 0) + " of " + _bar.total
            }

            IconButton {
                objectName: "helpSearchPrevious"
                visible: _bar.searching
                enabled: _bar.total > 0
                focusPolicy: Qt.NoFocus
                text: ""
                font.pixelSize: Style.dp(13)
                implicitWidth: Style.dp(24)
                implicitHeight: Style.dp(24)
                ToolTip.visible: hovered
                ToolTip.text: "Previous match (Shift+F3)"
                onClicked: _bar.previous()
            }

            IconButton {
                objectName: "helpSearchNext"
                visible: _bar.searching
                enabled: _bar.total > 0
                focusPolicy: Qt.NoFocus
                text: ""
                font.pixelSize: Style.dp(13)
                implicitWidth: Style.dp(24)
                implicitHeight: Style.dp(24)
                ToolTip.visible: hovered
                ToolTip.text: "Next match (F3)"
                onClicked: _bar.next()
            }
        }

        CheckBox {
            id: _allBox
            objectName: "helpSearchAll"
            visible: _bar.scopedChapter !== ""
            text: "Search all of Help"
            checked: _bar.allOfHelp
            focusPolicy: Qt.NoFocus
            onToggled: _bar.allOfHelp = checked
            ToolTip.visible: hovered
            ToolTip.text: "Also list matching topics from the other chapters, under their chapter's name"
        }
    }
}
