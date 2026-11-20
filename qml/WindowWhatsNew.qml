// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Style

// The What's New window (01 S183): the banner's What's New link and
// Help > What's New… open it. The notes are the model's HTML, shown the
// way Check for Updates shows them.
ApplicationWindow {
    id: _root

    EscapeCloses { host: _root }

    // Opens where it was left, first on the main window's screen.
    ToolWindowMemory {
        host: _root
        name: "whatsNew"
        defaultWidth: Style.fitWidth(Style.dp(560), Screen)
        defaultHeight: Style.fitHeight(Style.dp(440), Screen)
    }

    font.pixelSize: Style.fontSize
    minimumWidth: Style.fitWidth(Style.dp(420), Screen)
    minimumHeight: Style.fitHeight(Style.dp(240), Screen)

    color: Style.background
    U.Universal.theme: Style.theme

    title: qsTr("What's New")

    function _css(c) {
        return "rgba(" + Math.round(c.r * 255) + "," + Math.round(c.g * 255) + ","
            + Math.round(c.b * 255) + "," + c.a.toFixed(3) + ")"
    }
    // The same small headings and muted version lines as Check for Updates.
    function notesStyle() {
        return "<style>"
            + "p { margin-top: 0px; margin-bottom: " + Style.dp(4) + "px; }"
            + "p.kind { margin-top: " + Style.dp(8) + "px; margin-bottom: " + Style.dp(2) + "px; }"
            + "p.ver { color: " + _css(Style.fgMuted) + "; font-size: "
            + Math.round(Style.fontSize * 0.87) + "px; margin-top: " + Style.dp(6) + "px; }"
            + "p.none { color: " + _css(Style.fgMuted) + "; }"
            + "ul { margin-top: 0px; margin-bottom: " + Style.dp(2) + "px; margin-left: -20px; }"
            + "li { margin-bottom: " + Style.dp(2) + "px; }"
            + "hr { background-color: " + _css(Style.line) + "; margin-top: "
            + Style.dp(14) + "px; margin-bottom: " + Style.dp(14) + "px; }"
            + "code { font-family: '" + Style.monoFont + "'; }"
            + "</style>"
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: Style.dp(16)
        color: Style.bgWell
        border.color: Style.line
        border.width: 1
        radius: Style.dp(4)

        ScrollView {
            objectName: "whatsNewView"
            anchors.fill: parent
            anchors.margins: Style.dp(1)
            clip: true

            TextArea {
                objectName: "whatsNewNotes"
                readOnly: true
                selectByMouse: true
                wrapMode: TextEdit.Wrap
                background: null
                U.Universal.theme: Style.theme
                leftPadding: Style.dp(10)
                rightPadding: Style.dp(10)
                topPadding: Style.dp(8)
                bottomPadding: Style.dp(4)
                readonly property string notes: whatsNew ? whatsNew.notesHtml : ""
                textFormat: notes ? TextEdit.RichText : TextEdit.PlainText
                text: notes ? _root.notesStyle() + notes : qsTr("Release notes unavailable.")
                onTextChanged: Qt.callLater(update)
                onLinkActivated: (link) => {
                    if (/^https:\/\//.test(link))
                        Qt.openUrlExternally(link)
                }
            }
        }
    }
}
