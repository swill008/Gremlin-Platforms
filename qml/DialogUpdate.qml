// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Style

// Help > Check for Updates, and the offer after a startup check.
ApplicationWindow {
    id: _root

    EscapeCloses { host: _root }

    font.pixelSize: Style.fontSize
    minimumWidth: Style.fitWidth(Style.dp(520), Screen)
    minimumHeight: Style.fitHeight(Style.dp(230), Screen)
    width: Style.fitWidth(Style.dp(600), Screen)
    // Room for the release notes (01 S133); they scroll inside the window.
    height: Style.fitHeight(Style.dp(460), Screen)

    color: Style.background
    U.Universal.theme: Style.theme

    // The same words as the Help menu item that opens it.
    title: qsTr("Check for Updates")

    readonly property string state_: updater ? updater.state : "idle"

    // Closing the window is the same as Cancel: no download left running unseen.
    onClosing: if (updater && state_ === "downloading") updater.cancel()

    // The notes' small headings and muted version lines (01 S133).
    function _css(c) {
        return "rgba(" + Math.round(c.r * 255) + "," + Math.round(c.g * 255) + ","
            + Math.round(c.b * 255) + "," + c.a.toFixed(3) + ")"
    }
    function notesStyle() {
        return "<style>"
            + "p { margin-top: 0px; margin-bottom: " + Style.dp(4) + "px; }"
            + "p.kind { margin-top: " + Style.dp(8) + "px; margin-bottom: " + Style.dp(2) + "px; }"
            + "p.ver { color: " + _css(Style.fgMuted) + "; font-size: "
            + Math.round(Style.fontSize * 0.87) + "px; margin-top: " + Style.dp(6) + "px; }"
            + "p.none { color: " + _css(Style.fgMuted) + "; }"
            // Half the usual list indent at every level (Qt indents 40 px a
            // level; a negative margin adds up the same way).
            + "ul { margin-top: 0px; margin-bottom: " + Style.dp(2) + "px; margin-left: -20px; }"
            + "li { margin-bottom: " + Style.dp(2) + "px; }"
            // About a line of space above and below the rule between
            // versions (D-01-UPDATE-VERSION-LINE).
            + "hr { background-color: " + _css(Style.line) + "; margin-top: "
            + Style.dp(14) + "px; margin-bottom: " + Style.dp(14) + "px; }"
            + "code { font-family: '" + Style.monoFont + "'; }"
            + "</style>"
    }

    function message() {
        if (!updater)
            return ""
        switch (state_) {
        case "checking":
            return "Checking GitHub for a newer version…"
        case "upToDate":
            return "You have the latest version, " + updater.currentVersion + "."
        case "available":
            var text = "<b>Gremlin-Platforms " + updater.latestVersion + "</b> is available. "
                + "You have " + updater.currentVersion + ".<br><br>"
            if (updater.canInstall)
                return text + "Update now downloads it, closes the program, installs it and starts it again. "
                    + "Your profiles and settings are kept."
            if (updater.installKind === "installed")
                return text + "This release has no installer this copy can check, so get it from the release page."
            return text + "This copy is not installed by the installer, so it cannot update itself. "
                + "Get the installer or the zip from the release page."
        case "downloading":
            return "Downloading Gremlin-Platforms " + updater.latestVersion + "…"
        case "ready":
            return "Downloaded and checked. The program will close, install "
                + updater.latestVersion + " and start again."
        case "error":
            return updater.errorText
        case "failed":
            var failed = "The update to <b>Gremlin-Platforms " + updater.failedVersion
                + "</b> didn't finish, so the previous version (" + updater.currentVersion
                + ") was put back. Your profiles and settings are unchanged.<br><br>"
                + "Try Again installs it again."
            if (updater.failedLog)
                failed += " Setup's log: " + updater.failedLog
            return failed
        }
        return ""
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Style.dp(16)
        spacing: Style.dp(12)

        Label {
            Layout.fillWidth: true
            Layout.fillHeight: !_notesBox.visible
            wrapMode: Text.WordWrap
            textFormat: Text.StyledText
            text: _root.message()
        }

        // What's new in the offered release, and in the versions between,
        // newest first, then the link to the full notes (01 S133,
        // D-01-UPDATE-WHATSNEW). The HTML comes from updater.notes_html:
        // nothing from the release body runs or loads.
        Rectangle {
            id: _notesBox
            objectName: "releaseNotesBox"
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: _root.state_ === "available"
            color: Style.bgWell
            border.color: Style.line
            border.width: 1
            radius: Style.dp(4)

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Style.dp(1)
                spacing: 0

                ScrollView {
                    id: _notesView
                    objectName: "releaseNotesView"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true

                    TextArea {
                        objectName: "releaseNotes"
                        readOnly: true
                        selectByMouse: true
                        wrapMode: TextEdit.Wrap
                        background: null
                        // The style turns a focused text area to its light
                        // look (black text) whatever the theme; clicking
                        // into the notes keeps the program's theme.
                        U.Universal.theme: Style.theme
                        leftPadding: Style.dp(10)
                        rightPadding: Style.dp(10)
                        topPadding: Style.dp(8)
                        bottomPadding: Style.dp(4)
                        readonly property string notes: updater ? updater.releaseNotes : ""
                        textFormat: notes ? TextEdit.RichText : TextEdit.PlainText
                        // Filled once, before the window shows (the model
                        // waits for the list: D-01-UPDATE-NOTES-CACHE).
                        text: notes ? _root.notesStyle() + notes
                            : qsTr("Release notes unavailable.")
                        // Safety net: should the text ever change while
                        // shown, redraw all of it once it is laid out (a
                        // refill once left the added part blank until a
                        // resize).
                        onTextChanged: Qt.callLater(update)
                        onLinkActivated: (link) => {
                            if (/^https:\/\//.test(link))
                                Qt.openUrlExternally(link)
                        }
                    }
                }

                // The newest release's page: install files, install steps
                // and everything else.
                Label {
                    objectName: "fullReleaseNotes"
                    Layout.fillWidth: true
                    Layout.leftMargin: Style.dp(10)
                    Layout.rightMargin: Style.dp(10)
                    Layout.topMargin: Style.dp(4)
                    Layout.bottomMargin: Style.dp(8)
                    text: "<a href='open'>" + qsTr("Full release notes on GitHub") + "</a> ↗"
                    textFormat: Text.StyledText
                    onLinkActivated: () => { updater.openReleasePage() }

                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                }
            }
        }

        ProgressBar {
            Layout.fillWidth: true
            visible: _root.state_ === "downloading"
            from: 0
            to: 1
            value: updater ? updater.progress : 0
        }

        RowLayout {
            Layout.alignment: Qt.AlignRight
            spacing: Style.dp(8)

            Button {
                objectName: "updateNow"
                text: qsTr("Update Now")
                visible: _root.state_ === "available" && updater.canInstall
                highlighted: true
                onClicked: () => { updater.download() }
            }
            Button {
                text: qsTr("Open Release Page")
                visible: _root.state_ === "available" && !updater.canInstall
                highlighted: true
                onClicked: () => { updater.openReleasePage() }
            }
            Button {
                text: qsTr("Skip This Version")
                visible: _root.state_ === "available"
                onClicked: () => {
                    updater.skipVersion()
                    _root.close()
                }
            }
            Button {
                text: qsTr("Install and Restart")
                visible: _root.state_ === "ready"
                highlighted: true
                onClicked: () => { updater.install() }
            }
            Button {
                text: qsTr("Cancel")
                visible: _root.state_ === "downloading"
                onClicked: () => { updater.cancel() }
            }
            Button {
                text: qsTr("Try Again")
                visible: _root.state_ === "error"
                onClicked: () => { updater.check(true) }
            }
            Button {
                text: qsTr("Try Again")
                visible: _root.state_ === "failed"
                highlighted: true
                onClicked: () => { updater.retryUpdate() }
            }
            Button {
                text: _root.state_ === "available" || _root.state_ === "ready"
                    ? qsTr("Later") : qsTr("Close")
                visible: _root.state_ !== "downloading"
                onClicked: () => { _root.close() }
            }
        }
    }
}
