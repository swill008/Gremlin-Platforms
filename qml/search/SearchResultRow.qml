// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style
import "search_text.js" as SearchText

// One row of the Search window's results (SearchModel rowKind): a profile
// heading, a device heading under it (both with a count and a fold arrow),
// or a result with its Input / Mode / Action columns, the matched
// characters lit and its tags. Search shows no health marks (01 S196);
// Health (01 S197) sets showStatus and passes notFound / why / notPlugged /
// usedTwice to draw the ⚠ (hover: why) and the chips.
Rectangle {
    id: _row

    required property int index
    required property var model

    // The column widths, from the window's header.
    property real inputWidth: Style.dp(200)
    property real modeWidth: Style.dp(110)
    property bool current: false

    // Health's marks (off in Search): the caller passes the findings.
    property bool showStatus: false
    property bool notFound: false
    property string why: ""
    property bool notPlugged: false
    property bool usedTwice: false

    signal picked(int index)
    signal opened(int index)
    signal menuAsked(int index, real x, real y)
    signal foldClicked(int index)

    readonly property string kind: SearchText.field(model, "rowKind", "result")
    readonly property bool heading: kind !== "result"

    function f(name, fallback) {
        return SearchText.field(_row.model, name, fallback)
    }

    function lit(name, text) {
        return SearchText.highlight(text, SearchText.spans(_row.model, name),
                                    Style.findMatch, Style.ink)
    }

    // The typed notes that matched, lit, so the row says why it was found.
    readonly property string matchedNotes: {
        var notes = f("notes", [])
        var out = []
        for (var i = 0; i < (notes ? notes.length : 0); i++) {
            var spans = SearchText.spans(_row.model, "notes:" + i)
            if (spans.length)
                out.push(SearchText.highlight(notes[i], spans, Style.findMatch, Style.ink))
        }
        return out.join(" · ")
    }
    readonly property string inheritedFrom: String(f("inheritedFrom", ""))

    objectName: "searchRow:" + index
    width: ListView.view ? ListView.view.width : implicitWidth
    implicitHeight: (heading ? _headingRow.implicitHeight : _resultRow.implicitHeight)
                    + Style.dp(heading ? 8 : 10)
    color: current ? Style.bgSelected
         : (_mouse.containsMouse && !heading ? Style.bgHover
         : (kind === "profile" ? Style.bgRaised : Style.clear))

    MouseArea {
        id: _mouse
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        cursorShape: _row.heading ? Qt.ArrowCursor : Qt.PointingHandCursor
        onClicked: (mouse) => {
            if (_row.heading) {
                _row.foldClicked(_row.index)
                return
            }
            _row.picked(_row.index)
            if (mouse.button === Qt.RightButton)
                _row.menuAsked(_row.index, mouse.x, mouse.y)
        }
        onDoubleClicked: (mouse) => {
            if (!_row.heading && mouse.button === Qt.LeftButton)
                _row.opened(_row.index)
        }
    }

    // A profile or device heading: ▸/▾, the name and its count.
    RowLayout {
        id: _headingRow
        visible: _row.heading
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: Style.dp(_row.kind === "device" ? 22 : 6)
        anchors.rightMargin: Style.dp(8)
        spacing: Style.dp(6)

        Label {
            text: _row.f("folded", false) ? "▸" : "▾"
            color: Style.fgMuted
        }
        Label {
            objectName: "searchHeading:" + _row.index
            Layout.fillWidth: true
            text: _row.f("title", "")
            color: Style.fgStrong
            font.bold: _row.kind === "profile"
            elide: Text.ElideRight
        }
        Label {
            text: String(_row.f("count", 0))
            color: Style.fgMuted
        }
    }

    // A result: Input · Mode · Action, then its tags.
    RowLayout {
        id: _resultRow
        visible: !_row.heading
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: Style.dp(38)
        anchors.rightMargin: Style.dp(8)
        spacing: Style.dp(8)

        ColumnLayout {
            Layout.preferredWidth: _row.inputWidth - Style.dp(38)
            Layout.minimumWidth: _row.inputWidth - Style.dp(38)
            Layout.maximumWidth: _row.inputWidth - Style.dp(38)
            spacing: 0
            Label {
                Layout.fillWidth: true
                textFormat: Text.StyledText
                text: _row.lit("inputLabel", _row.f("inputLabel", ""))
                color: Style.fg
                elide: Text.ElideRight
            }
            Label {
                Layout.fillWidth: true
                visible: String(_row.f("customName", "")).length > 0
                textFormat: Text.StyledText
                text: _row.lit("customName", _row.f("customName", ""))
                color: Style.fgMuted
                elide: Text.ElideRight
            }
        }
        Label {
            objectName: "searchRowMode:" + _row.index
            Layout.preferredWidth: _row.modeWidth
            Layout.minimumWidth: _row.modeWidth
            Layout.maximumWidth: _row.modeWidth
            textFormat: Text.StyledText
            text: _row.lit("mode", _row.f("mode", ""))
            color: Style.fg
            elide: Text.ElideRight
        }
        // The action, in the Bindings number style, and the notes that matched.
        ColumnLayout {
            Layout.fillWidth: true
            // Takes all the slack, so Input and Mode never drift off their
            // headings when the action is short (01 S196).
            Layout.maximumWidth: Number.POSITIVE_INFINITY
            spacing: Style.dp(2)
            RowLayout {
            Layout.fillWidth: true
            spacing: Style.dp(4)
            // Health only: the binding's output is not there; hover says why.
            Label {
                objectName: "searchRowWarn:" + _row.index
                visible: _row.showStatus && _row.notFound
                // Text form (U+FE0E), so it takes the danger colour, not emoji colours.
                text: "⚠︎"
                color: Style.danger
                font.bold: true
                font.family: Style.symbolFont
                ToolTip.visible: _warnMouse.containsMouse && _row.why.length > 0
                ToolTip.text: _row.why
                MouseArea {
                    id: _warnMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    acceptedButtons: Qt.NoButton
                }
            }
            TextMetrics {
                id: _actionMetrics
                font: _actionText.font
                text: _row.f("text", "")
            }
            Rectangle {
                objectName: "searchRowAction:" + _row.index
                Layout.fillWidth: true
                Layout.preferredWidth: _actionMetrics.advanceWidth + Style.dp(12)
                Layout.maximumWidth: _actionMetrics.advanceWidth + Style.dp(12)
                implicitHeight: _actionText.implicitHeight + Style.dp(4)
                radius: Style.dp(5)
                color: Style.bindingBg
                border.color: Style.bindingBorder
                border.width: Style.dp(1)
                Label {
                    id: _actionText
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.leftMargin: Style.dp(5)
                    anchors.rightMargin: Style.dp(5)
                    anchors.verticalCenter: parent.verticalCenter
                    // In full when it fits (matches lit); else plain, cut
                    // in the middle so the number at its end stays (01 S196).
                    readonly property bool fits: _actionMetrics.advanceWidth <= width + 1
                    textFormat: fits ? Text.StyledText : Text.PlainText
                    text: fits ? _row.lit("text", _row.f("text", "")) : _row.f("text", "")
                    font.family: Style.monoFont
                    color: Style.bindingText
                    elide: Text.ElideMiddle
                }
                // Health: a cut action shows in full on hover (01 S197).
                HoverHandler {
                    id: _actionHover
                    enabled: _row.showStatus && !_actionText.fits
                }
                ToolTip {
                    objectName: "searchRowActionTip:" + _row.index
                    visible: _actionHover.hovered && _actionHover.enabled
                    text: _row.f("text", "")
                }
            }
            // The space after a short action, so the box stays at the
            // Action heading (01 S196).
            Item {
                Layout.fillWidth: true
            }
            }
            Label {
                objectName: "searchRowNotes:" + _row.index
                Layout.fillWidth: true
                visible: _row.matchedNotes.length > 0
                textFormat: Text.StyledText
                text: _row.matchedNotes
                color: Style.fgMuted
                font.pixelSize: Style.menuTextPx
                elide: Text.ElideRight
            }
        }
        Repeater {
            model: [
                { on: _row.showStatus && _row.usedTwice, text: "Used twice", tone: Style.warn,
                  name: "searchRowUsedTwice:" + _row.index },
                { on: _row.showStatus && _row.notPlugged, text: "Not plugged in", tone: Style.fgMuted,
                  name: "searchRowNotPlugged:" + _row.index },
                { on: _row.inheritedFrom.length > 0, text: "Inherited from " + _row.inheritedFrom,
                  tone: Style.fgSoft, name: "searchRowInherited:" + _row.index }
            ]
            delegate: Rectangle {
                required property var modelData
                visible: !!modelData.on
                objectName: modelData.name ? modelData.name + ":tag" : ""
                implicitWidth: _tag.implicitWidth + Style.dp(10)
                implicitHeight: _tag.implicitHeight + Style.dp(2)
                // A chip never shrinks below its words; the action text gives way.
                Layout.minimumWidth: implicitWidth
                radius: height / 2
                color: Style.alpha(modelData.tone, 0.15)
                border.color: modelData.tone
                border.width: Style.dp(1)
                Label {
                    id: _tag
                    objectName: modelData.name || ""
                    anchors.centerIn: parent
                    text: modelData.text
                    color: modelData.tone
                    font.pixelSize: Style.menuTextPx
                }
            }
        }
    }
}
