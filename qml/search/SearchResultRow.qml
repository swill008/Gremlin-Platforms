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
// characters lit and its tags.
Rectangle {
    id: _row

    required property int index
    required property var model

    // The column widths, from the window's header.
    property real inputWidth: Style.dp(200)
    property real modeWidth: Style.dp(110)
    property bool current: false

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
            Layout.preferredWidth: _row.modeWidth
            Layout.maximumWidth: _row.modeWidth
            textFormat: Text.StyledText
            text: _row.lit("mode", _row.f("mode", ""))
            color: Style.fg
            elide: Text.ElideRight
        }
        // The action, in the Bindings number style.
        Rectangle {
            Layout.fillWidth: true
            Layout.maximumWidth: _actionText.implicitWidth + Style.dp(10)
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
                textFormat: Text.StyledText
                text: _row.lit("text", _row.f("text", ""))
                font.family: Style.monoFont
                color: Style.bindingText
                elide: Text.ElideRight
            }
        }
        Item { Layout.fillWidth: true }
        Repeater {
            model: [
                { on: _row.f("usedTwice", false), text: "Used twice", tone: Style.warn },
                { on: _row.f("notFound", false), text: "Binding output not found", tone: Style.danger },
                { on: _row.f("notPlugged", false), text: "Not plugged in", tone: Style.fgMuted }
            ]
            delegate: Rectangle {
                required property var modelData
                visible: !!modelData.on
                implicitWidth: _tag.implicitWidth + Style.dp(10)
                implicitHeight: _tag.implicitHeight + Style.dp(2)
                radius: height / 2
                color: Style.alpha(modelData.tone, 0.15)
                border.color: modelData.tone
                border.width: Style.dp(1)
                Label {
                    id: _tag
                    anchors.centerIn: parent
                    text: modelData.text
                    color: modelData.tone
                    font.pixelSize: Style.menuTextPx
                }
            }
        }
    }
}
