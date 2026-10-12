// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Style
import Gremlin.UI
import "helpers.js" as Helpers
import "confirm.js" as Confirm

// Tools > History: every saved change, newest first, under day headings,
// repeated changes to one thing folded into one row. Pick one to read what
// restoring does, and restore to before (or after) it. The list never moves
// under the user (D-TESTLIST-1 13): a restore tags its entry in place and new
// changes wait behind the "N new changes · Show" bar. An editor opens it
// filtered to what it shows (filter: {"area", "device", "inputType",
// "inputId", "mode"}).
ApplicationWindow {
    font.pixelSize: Style.fontSize
    id: _root

    ToolWindowMemory {
        host: _root
        name: "history"
        defaultWidth: Style.fitWidth(Style.dp(1100), Screen)
        defaultHeight: Style.fitHeight(Style.dp(720), Screen)
    }

    EscapeCloses { host: _root }

    minimumWidth: Style.fitWidth(Style.dp(760), Screen)
    minimumHeight: Style.fitHeight(Style.dp(480), Screen)
    color: Style.background
    U.Universal.theme: Style.theme
    title: "History"

    // Set by whoever opens the window (JSON text).
    property string filter: ""
    // The device's name for the "Only ..." line when the filter has only its id.
    property string filterLabel: ""
    property string selected: ""
    // Bumped by pick() so the selected change's details are read again.
    property int shownRevision: 0
    // The selected change's details (HistoryModel.detail), or {}.
    readonly property var shown: {
        shownRevision
        return selected ? JSON.parse(_model.detail(selected)) : ({})
    }
    property string message: ""
    // 08 S12b: a "History cleared" entry is selected (no Restore, no
    // Previous/Next Change).
    readonly property bool isCleared: selected.length > 0 && shown.danger === true
    // "Show full before/after": today's two-column view of the change.
    property bool showFull: false

    readonly property var areas: [
        { key: "", label: "All" },
        { key: "profile", label: "Profile" },
        { key: "modules", label: "Module files" },
        { key: "device-mapping-editor", label: "Device Mapping Editor" },
        { key: "settings", label: "Settings" }
    ]

    HistoryModel { id: _model }

    function wanted() {
        try {
            var w = JSON.parse(filter || "{}")
            return (w && typeof w === "object") ? w : {}
        } catch (e) {
            return {}
        }
    }

    // What the filter is about, besides the area ("Test Stick Button 1 in Default").
    function aboutText() {
        var w = wanted()
        var parts = []
        if (w.device)
            parts.push(w.device)
        else if (filterLabel.length)
            parts.push(filterLabel)
        if (w.inputType && w.inputId)
            parts.push(w.inputType.charAt(0).toUpperCase() + w.inputType.slice(1) + " " + w.inputId)
        var text = parts.join(" ")
        if (w.mode)
            text += " in " + w.mode
        if (w.deviceName && !text.length)
            text = w.deviceName
        if (w.fileName && !text.length)
            text = w.fileName
        return text
    }

    function applyFilter() {
        var w = wanted()
        for (var i = 0; i < areas.length; ++i) {
            if (areas[i].key === (w.area || ""))
                _area.currentIndex = i
        }
        _model.setFilter(JSON.stringify(w))
        _model.reload()
        pick("")
    }

    function setArea(key) {
        var w = wanted()
        if (key)
            w.area = key
        else
            delete w.area
        filter = JSON.stringify(w)
    }

    function showAll() {
        var w = wanted()
        filter = w.area ? JSON.stringify({ area: w.area }) : ""
    }

    function pick(entryId) {
        selected = entryId
        shownRevision++
        diffAt = -1
        message = ""
    }

    // The selected entry read again (its tag after a restore) without
    // moving the list or dropping the selection.
    function reread() {
        shownRevision++
    }

    // Done after a restore: tags change in place, the rows stay (no reload).
    function restored(text) {
        _model.refresh()
        reread()
        message = text || ""
    }

    // "N new changes · Show": the waiting entries go on top; the selection
    // stays on its entry.
    function showNew() {
        if (_model.newCount <= 0)
            return
        _model.showNew()
        reread()
        _list.positionViewAtBeginning()
    }

    function restore(which) {
        var effect = which === "before" ? (shown.effect || "") : (shown.effectAfter || "")
        _gate.confirmThen("Restore?",
            effect || (shown.note || ""),
            "Restore",
            function() {
                var entryId = selected
                var put = function() {
                    var result = JSON.parse(_model.restore(entryId, which))
                    // 08 S45a (AD6): a profile copy outside the usual
                    // folders is asked about first; nothing is written yet.
                    if (result.ask === true) {
                        Qt.callLater(function() {
                            _gate.confirmThen("Restore?", result.message, "Write Here",
                                function() {
                                    var done = JSON.parse(_model.restoreOutside(entryId, which))
                                    _root.restored(done.message)
                                }, null, true)
                        })
                        return
                    }
                    _root.restored(result.message)
                }
                // An input's actions go back into the profile: the action
                // panes close first, asking when one has changes (05 Q8).
                if (shown.closesPanes === true)
                    Helpers.closeActionPanes(put)
                else
                    put()
            }, null, false)
    }

    // 08 S12b: "38 MB", "0.4 MB".
    function sizeText(bytes) {
        var mb = Math.max(0, Number(bytes) || 0) / (1024 * 1024)
        var shown = mb >= 10 ? Math.round(mb) : Math.round(mb * 10) / 10
        return shown + " MB"
    }

    // 08 S12b: what Clear History deletes, asked first with the shared
    // question (01 S140), whose last line says "This can't be undone."
    function clearQuestion(summary) {
        var n = Number(summary.entries) || 0
        var what = n === 1 ? "The 1 change in History is deleted"
                           : "All " + n + " changes in History are deleted"
        return what + ", along with the " + sizeText(summary.bytes)
            + " of kept copies used to restore them. You won't be able to restore"
            + " or undo any earlier change, including the Device Library's Undo"
            + " for this session. Your profiles, module files and Device Library"
            + " stay as they are."
    }

    function askClear() {
        var summary = {}
        try {
            summary = JSON.parse(_model.summary()) || {}
        } catch (e) {
            summary = {}
        }
        Confirm.ask(_root, {
            title: "Clear History?",
            text: clearQuestion(summary),
            undoable: false,
            action: "Clear History",
            onAccept: function() { _root.clearAll() }
        })
    }

    function clearAll() {
        var result = {}
        try {
            result = JSON.parse(_model.clearAll()) || {}
        } catch (e) {
            result = { ok: false, error: String(e) }
        }
        _model.reload()
        pick("")
        message = result.ok ? "History cleared." : (result.error || "History couldn't be cleared.")
    }

    // A new filter drops the old one's label (whoever opens it sets its own).
    onFilterChanged: {
        filterLabel = ""
        applyFilter()
    }
    Component.onCompleted: applyFilter()
    // Back at the front: tags and the new-changes count are read again; the
    // rows, selection and scroll stay (new changes wait for Show).
    onActiveChanged: {
        if (active) {
            _model.refresh()
            reread()
        }
    }

    // 08 S104: the selected change row for row (text_diff.rows) and the
    // first row of each change block; diffAt is the block last moved to.
    readonly property var diffRows: shown.diffRows || []
    readonly property var diffBlocks: shown.diffBlocks || []
    property int diffAt: -1

    function goToChange(index) {
        if (index < 0 || index >= diffBlocks.length)
            return
        diffAt = index
        // A couple of rows above it stay in view, for context.
        var row = Math.max(0, diffBlocks[index] - 2)
        _beforeList.positionViewAtIndex(row, ListView.Beginning)
        _afterList.positionViewAtIndex(row, ListView.Beginning)
    }

    function escaped(text) {
        return text.replace(/&/g, "&amp;").replace(/</g, "&lt;")
                   .replace(/>/g, "&gt;").replace(/"/g, "&quot;")
    }

    // A changed line as rich text, its changed words on a stronger tint.
    function markedWords(text, spans, tint) {
        var out = ""
        var at = 0
        for (var i = 0; i < spans.length; ++i) {
            var start = Math.max(spans[i][0], at)
            var end = Math.min(spans[i][1], text.length)
            if (end <= start)
                continue
            out += escaped(text.slice(at, start))
                + "<span style=\"background-color:" + tint + "\">"
                + escaped(text.slice(start, end)) + "</span>"
            at = end
        }
        out += escaped(text.slice(at))
        return "<div style=\"white-space:pre-wrap\">" + out + "</div>"
    }

    // One side's line of a row, as plain or rich text.
    component RowText: TextEdit {
        property var row: ({})
        property string side: "before"
        readonly property var spans: row[side + "Spans"] || []
        readonly property string line: row[side] || ""
        readOnly: true
        selectByMouse: true
        wrapMode: TextEdit.Wrap
        font.family: Style.monoFont
        font.pixelSize: Style.fontSize
        color: Style.fg
        selectionColor: Style.accent
        selectedTextColor: Style.onColor
        textFormat: spans.length ? TextEdit.RichText : TextEdit.PlainText
        text: spans.length
              ? _root.markedWords(line, spans, side === "before" ? Style.diffRemovedWord : Style.diffAddedWord)
              : line
    }

    // One side's rows. A row is as tall as the taller of its two sides, so
    // the sides line up; scrolling one scrolls the other.
    component DiffList: JGListView {
        id: _diffList
        property string side: "before"
        property var twin: null
        // The side's whole text.
        readonly property string text: _root.shown[side] || ""
        objectName: "history:" + side
        anchors.fill: parent
        anchors.margins: 1
        model: _root.diffRows
        onContentYChanged: {
            if (twin && Math.abs(twin.contentY - contentY) > 0.5)
                twin.contentY = contentY
        }
        delegate: Rectangle {
            id: _diffRow
            required property var modelData
            required property int index
            readonly property string kind: modelData.kind
            readonly property bool before: _diffList.side === "before"
            readonly property bool marked: kind === "changed"
                || kind === (before ? "removed" : "added")
            objectName: "historyRow:" + _diffList.side + ":" + index
            width: ListView.view.width
            height: Math.max(_mine.implicitHeight, _other.implicitHeight) + Style.dp(2)
            color: marked ? (before ? Style.diffRemovedBg : Style.diffAddedBg) : Style.clear
            Rectangle {
                visible: _diffRow.marked
                width: Style.dp(3)
                height: parent.height
                color: _diffRow.before ? Style.diffRemovedBar : Style.diffAddedBar
            }
            RowText {
                id: _mine
                row: _diffRow.modelData
                side: _diffList.side
                x: Style.dp(8)
                y: Style.dp(1)
                width: parent.width - Style.dp(12)
            }
            // The other side's line, unseen, for the row's height.
            RowText {
                id: _other
                visible: false
                row: _diffRow.modelData
                side: _diffRow.before ? "after" : "before"
                width: _mine.width
            }
        }
    }

    // A side's heading and its rows.
    component DiffSide: ColumnLayout {
        id: _diffSide
        property string side: "before"
        default property alias rows: _frame.data
        Layout.fillWidth: true
        Layout.fillHeight: true
        spacing: Style.dp(4)
        Label {
            text: _diffSide.side === "before" ? "Before" : "After"
            color: Style.fg
            font.bold: true
            elide: Text.ElideRight
            Layout.fillWidth: true
            Layout.minimumWidth: 0
        }
        Rectangle {
            id: _frame
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: Style.bgCard
            border.color: Style.line
        }
    }

    DismissibleDialog { id: _gate }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Style.dp(12)
        spacing: Style.dp(8)

        // 08 Q4: a Restore changes the profile and files while it runs.
        RunningNote {}

        RowLayout {
            Layout.fillWidth: true
            spacing: Style.dp(8)
            Label { text: "Show"; color: Style.fg }
            ComboBox {
                id: _area
                objectName: "historyArea"
                model: _root.areas
                textRole: "label"
                onActivated: _root.setArea(_root.areas[currentIndex].key)
            }
            // 01 S141: the shared search box (Ctrl+F, the ×, Esc clears).
            SearchBox {
                id: _search
                objectName: "historySearch"
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                placeholder: "Search"
                count: _list.count
                onTextChanged: _model.setSearch(text)
            }
            // 08 S35: as Show on the new-changes bar; the selection and the
            // rows already shown stay.
            Button {
                objectName: "historyRefresh"
                text: "Refresh"
                focusPolicy: Qt.NoFocus
                onClicked: {
                    _model.refresh()
                    _root.showNew()
                }
            }
            // 08 S12b: refused while the profile runs.
            DangerButton {
                id: _clearButton
                objectName: "historyClear"
                text: "Clear History\u2026"
                focusPolicy: Qt.NoFocus
                enabled: !(backend && backend.gremlinActive)
                ToolTip.visible: hovered
                ToolTip.text: _clearButton.enabled
                    ? "Deletes every change in History and its kept copies"
                    : "Stop the profile to clear History"
                onClicked: _root.askClear()
            }
        }

        RowLayout {
            Layout.fillWidth: true
            visible: _root.aboutText().length > 0
            Label {
                objectName: "historyAbout"
                text: "Only " + _root.aboutText()
                color: Style.fg
                Layout.fillWidth: true
                elide: Text.ElideRight
            }
            Button {
                text: "Show All"
                focusPolicy: Qt.NoFocus
                onClicked: _root.showAll()
            }
        }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal

            ColumnLayout {
                SplitView.preferredWidth: Style.dp(460)
                SplitView.minimumWidth: Style.dp(280)
                spacing: Style.dp(4)

                // Changes made since the list was shown wait here; the
                // list itself never changes under the user.
                Rectangle {
                    id: _newBar
                    objectName: "historyNewBar"
                    visible: _model.newCount > 0
                    Layout.fillWidth: true
                    implicitHeight: _newText.implicitHeight + Style.dp(10)
                    color: Style.alpha(Style.accent, 0.18)
                    border.color: Style.accent
                    radius: Style.dp(3)
                    Label {
                        id: _newText
                        objectName: "historyNewText"
                        anchors.centerIn: parent
                        textFormat: Text.StyledText
                        text: (_model.newCount === 1 ? "1 new change"
                                                     : _model.newCount + " new changes")
                              + " · <a href=\"show\">Show</a>"
                        color: Style.fg
                        linkColor: Style.accent
                        onLinkActivated: _root.showNew()
                    }
                }

                JGListView {
                    id: _list
                    objectName: "historyList"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    model: _model
                    // Today / Yesterday / the date.
                    section.property: "day"
                    section.criteria: ViewSection.FullString
                    section.delegate: Label {
                        required property string section
                        objectName: "historyDay:" + section
                        width: ListView.view.width
                        text: section
                        color: Style.fgMuted
                        font.bold: true
                        topPadding: Style.dp(8)
                        bottomPadding: Style.dp(2)
                        leftPadding: Style.dp(6)
                    }
                    delegate: Rectangle {
                        id: _entryRow
                        required property var model
                        required property string entryId
                        required property string when
                        required property string areaName
                        required property string title
                        // 08 S12b: "History cleared" in the danger colour.
                        readonly property bool danger: model.danger === true
                        readonly property string groupKey: model.groupKey || ""
                        readonly property int groupSize: model.groupSize || 1
                        readonly property bool groupFirst: model.groupFirst !== false
                        readonly property bool groupOpen: model.groupOpen === true
                        readonly property string tag: model.tag || ""
                        // A row of an open run, under its head.
                        readonly property bool inner: !groupFirst
                        objectName: "historyEntry:" + entryId
                        width: ListView.view.width
                        height: _rowText.implicitHeight + Style.dp(12)
                        color: _root.selected === entryId ? Style.alpha(Style.accent, 0.25) : "transparent"
                        border.color: _root.selected === entryId ? Style.accent : "transparent"
                        MouseArea {
                            anchors.fill: parent
                            onClicked: _root.pick(_entryRow.entryId)
                        }
                        RowLayout {
                            id: _rowText
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.margins: Style.dp(6)
                            anchors.leftMargin: _entryRow.inner ? Style.dp(28) : Style.dp(6)
                            spacing: Style.dp(6)
                            // A run's head: ▸ / ▾ opens or closes it.
                            ToolButton {
                                objectName: "historyGroupToggle:" + _entryRow.entryId
                                visible: _entryRow.groupFirst && _entryRow.groupSize > 1
                                text: _entryRow.groupOpen ? "▾" : "▸"
                                focusPolicy: Qt.NoFocus
                                Layout.alignment: Qt.AlignTop
                                implicitWidth: Style.dp(22)
                                implicitHeight: Style.dp(22)
                                onClicked: _model.toggleGroup(_entryRow.groupKey)
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 0
                                Label {
                                    text: _entryRow.title
                                    color: _entryRow.danger ? Style.dangerText : Style.fg
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                }
                                Label {
                                    text: (_entryRow.model.time || _entryRow.when) + " · " + _entryRow.areaName
                                          + (_entryRow.groupFirst && _entryRow.groupSize > 1
                                             ? " · " + _entryRow.groupSize + " changes" : "")
                                    color: Style.fgMuted
                                    font.pixelSize: Style.dp(11)
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }
                            }
                            // "Restored · 19:47" / "Reapplied · 19:48".
                            Label {
                                objectName: "historyTag:" + _entryRow.entryId
                                visible: _entryRow.tag.length > 0
                                text: _entryRow.tag
                                color: Style.fg
                                font.pixelSize: Style.dp(11)
                                leftPadding: Style.dp(6)
                                rightPadding: Style.dp(6)
                                topPadding: Style.dp(2)
                                bottomPadding: Style.dp(2)
                                Layout.alignment: Qt.AlignTop
                                background: Rectangle {
                                    color: Style.alpha(Style.accent, 0.2)
                                    border.color: Style.accent
                                    radius: Style.dp(3)
                                }
                            }
                        }
                    }
                    EmptyState {
                        anchors.centerIn: parent
                        width: _list.width - Style.dp(24)
                        visible: _list.count === 0
                        text: "No saved changes to show."
                    }
                }
            }

            ColumnLayout {
                id: _detail
                SplitView.fillWidth: true
                SplitView.minimumWidth: Style.dp(320)
                spacing: Style.dp(8)
                Label {
                    visible: !_root.selected.length
                    text: "Pick a change to see what restoring it does."
                    color: Style.fgMuted
                }
                Label {
                    visible: _root.selected.length > 0
                    text: _root.shown.title || ""
                    color: _root.isCleared ? Style.dangerText : Style.fg
                    font.bold: true
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
                Label {
                    objectName: "historyWhen"
                    visible: _root.selected.length > 0
                    text: (_root.shown.when || "") + " · " + (_root.shown.area || "")
                          + ((_root.shown.tag || "").length ? " · " + _root.shown.tag : "")
                    color: Style.fgMuted
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                // 08 S12b: what a clearing deleted, and that nothing
                // before it can be restored.
                Label {
                    objectName: "historyClearedWhat"
                    visible: _root.isCleared
                    text: _root.shown.after || ""
                    color: Style.fg
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
                Label {
                    objectName: "historyClearedNote"
                    visible: _root.isCleared
                    text: _root.shown.note || ""
                    color: Style.dangerText
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
                // What restoring does, in plain words.
                Label {
                    objectName: "historyEffect"
                    visible: _root.selected.length > 0 && !_root.isCleared
                    text: _root.shown.effect || _root.shown.note || ""
                    color: Style.fg
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
                RowLayout {
                    visible: _root.selected.length > 0 && !_root.isCleared
                    Layout.fillWidth: true
                    spacing: Style.dp(12)
                    Button {
                        objectName: "historyRestoreBefore"
                        text: "Restore to before this change"
                        highlighted: true
                        focusPolicy: Qt.NoFocus
                        enabled: _root.shown.canRestoreBefore === true
                        onClicked: _root.restore("before")
                    }
                    Label {
                        objectName: "historyRestoreAfter"
                        readonly property bool enabledLink: _root.shown.canRestoreAfter === true
                        textFormat: Text.StyledText
                        text: enabledLink ? "<a href=\"after\">Restore to after this change</a>"
                                          : "Restore to after this change"
                        color: enabledLink ? Style.fg : Style.fgMuted
                        linkColor: Style.accent
                        onLinkActivated: _root.restore("after")
                        ToolTip.visible: _afterHover.hovered && (_root.shown.effectAfter || "").length > 0
                        ToolTip.text: _root.shown.effectAfter || ""
                        HoverHandler { id: _afterHover }
                    }
                    Item { Layout.fillWidth: true }
                    Label {
                        objectName: "historyShowFull"
                        textFormat: Text.StyledText
                        text: "<a href=\"full\">" + (_root.showFull ? "Hide full before/after"
                                                                     : "Show full before/after") + "</a>"
                        linkColor: Style.accent
                        onLinkActivated: _root.showFull = !_root.showFull
                    }
                }
                // 08 S104: both sides move together to a change.
                RowLayout {
                    visible: _root.selected.length > 0 && !_root.isCleared && _root.showFull
                    Layout.fillWidth: true
                    spacing: Style.dp(8)
                    Item { Layout.fillWidth: true }
                    Button {
                        objectName: "historyPreviousChange"
                        text: "Previous Change"
                        focusPolicy: Qt.NoFocus
                        enabled: _root.diffAt > 0
                        onClicked: _root.goToChange(_root.diffAt - 1)
                    }
                    Button {
                        objectName: "historyNextChange"
                        text: "Next Change"
                        focusPolicy: Qt.NoFocus
                        enabled: _root.diffAt < _root.diffBlocks.length - 1
                        onClicked: _root.goToChange(_root.diffAt + 1)
                    }
                }
                RowLayout {
                    id: _sides
                    visible: _root.selected.length > 0 && !_root.isCleared && _root.showFull
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: Style.dp(8)
                    DiffSide {
                        side: "before"
                        Layout.preferredWidth: (_sides.width - _sides.spacing) / 2
                        DiffList { id: _beforeList; side: "before"; twin: _afterList }
                    }
                    DiffSide {
                        side: "after"
                        Layout.preferredWidth: (_sides.width - _sides.spacing) / 2
                        DiffList { id: _afterList; side: "after"; twin: _beforeList }
                    }
                }
                Item {
                    visible: !_sides.visible
                    Layout.fillHeight: true
                }
                Label {
                    objectName: "historyMessage"
                    visible: _root.message.length > 0
                    text: _root.message
                    color: Style.fg
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
            }
        }
    }
}
