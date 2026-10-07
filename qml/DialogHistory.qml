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

// Tools > History: every saved change, newest first. Pick one to see it
// before and after, and Restore either. An editor opens it filtered to
// what it shows (filter: {"area", "device", "inputType", "inputId", "mode"}).
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

    readonly property var areas: [
        { key: "", label: "All" },
        { key: "profile", label: "Profile" },
        { key: "modules", label: "Module files" },
        { key: "button-map", label: "Button Map" },
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

    function restore(which) {
        var what = which === "before" ? "the version before this change" : "the version this change saved"
        _gate.confirmThen("Restore?",
            "Put back " + what + "? " + (shown.note || ""),
            "Restore",
            function() {
                var entryId = selected
                var put = function() {
                    var result = JSON.parse(_model.restore(entryId, which))
                    _model.reload()
                    message = result.message || ""
                }
                // An input's actions go back into the profile: the action
                // panes close first, asking when one has changes (05 Q8).
                if (shown.closesPanes === true)
                    Helpers.closeActionPanes(put)
                else
                    put()
            }, null, false)
    }

    // A new filter drops the old one's label (whoever opens it sets its own).
    onFilterChanged: {
        filterLabel = ""
        applyFilter()
    }
    Component.onCompleted: applyFilter()
    // New changes appear when the window comes back to the front.
    onActiveChanged: {
        if (active) {
            var keep = selected
            _model.reload()
            if (keep.length)
                pick(keep)
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

    // A side's heading, its Restore button and its rows.
    component DiffSide: ColumnLayout {
        id: _diffSide
        property string side: "before"
        default property alias rows: _frame.data
        Layout.fillWidth: true
        Layout.fillHeight: true
        spacing: Style.dp(4)
        // The heading, a gap, its button; short of room the heading is
        // shortened (…), never drawn under the button.
        RowLayout {
            Layout.fillWidth: true
            spacing: Style.dp(8)
            Label {
                text: _diffSide.side === "before" ? "Before" : "After"
                color: Style.fg
                font.bold: true
                elide: Text.ElideRight
                Layout.fillWidth: true
                Layout.minimumWidth: 0
            }
            Button {
                objectName: _diffSide.side === "before" ? "historyRestoreBefore" : "historyRestoreAfter"
                text: _diffSide.side === "before" ? "Restore Before" : "Restore After"
                focusPolicy: Qt.NoFocus
                enabled: _diffSide.side === "before"
                         ? _root.shown.canRestoreBefore === true
                         : _root.shown.canRestoreAfter === true
                onClicked: _root.restore(_diffSide.side)
            }
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
            TextField {
                objectName: "historySearch"
                Layout.fillWidth: true
                placeholderText: "Search"
                onTextChanged: _model.setSearch(text)
            }
            Button {
                text: "Refresh"
                focusPolicy: Qt.NoFocus
                onClicked: {
                    _model.reload()
                    _root.pick("")
                }
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

            JGListView {
                id: _list
                objectName: "historyList"
                SplitView.preferredWidth: Style.dp(460)
                SplitView.minimumWidth: Style.dp(280)
                model: _model
                delegate: Rectangle {
                    required property string entryId
                    required property string when
                    required property string areaName
                    required property string title
                    width: ListView.view.width
                    height: _rowText.implicitHeight + Style.dp(12)
                    color: _root.selected === entryId ? Style.alpha(Style.accent, 0.25) : "transparent"
                    border.color: _root.selected === entryId ? Style.accent : "transparent"
                    ColumnLayout {
                        id: _rowText
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.margins: Style.dp(6)
                        spacing: 0
                        Label {
                            text: title
                            color: Style.fg
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                        Label {
                            text: when + " \u00b7 " + areaName
                            color: Style.fgMuted
                            font.pixelSize: Style.dp(11)
                        }
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: _root.pick(entryId)
                    }
                }
                Label {
                    anchors.centerIn: parent
                    visible: _list.count === 0
                    text: "No saved changes to show."
                    color: Style.fgMuted
                }
            }

            ColumnLayout {
                id: _detail
                SplitView.fillWidth: true
                SplitView.minimumWidth: Style.dp(320)
                spacing: Style.dp(8)
                Label {
                    visible: !_root.selected.length
                    text: "Pick a change to see it before and after."
                    color: Style.fgMuted
                }
                Label {
                    visible: _root.selected.length > 0
                    text: _root.shown.title || ""
                    color: Style.fg
                    font.bold: true
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
                RowLayout {
                    visible: _root.selected.length > 0
                    Layout.fillWidth: true
                    spacing: Style.dp(8)
                    Label {
                        text: (_root.shown.when || "") + " \u00b7 " + (_root.shown.area || "")
                        color: Style.fgMuted
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                    // 08 S104: both sides move together to a change.
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
                    visible: _root.selected.length > 0
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
                    visible: !_root.selected.length
                    Layout.fillHeight: true
                }
                Label {
                    visible: _root.selected.length > 0 && (_root.shown.note || "").length > 0
                    text: "Restore: " + (_root.shown.note || "")
                    color: Style.fgMuted
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
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
