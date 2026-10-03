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

    font.pixelSize: Style.fontSize
    minimumWidth: Style.dp(520)
    minimumHeight: Style.dp(230)
    width: Style.dp(560)
    height: Style.dp(250)

    color: Style.background
    U.Universal.theme: Style.theme

    // The same words as the Help menu item that opens it.
    title: qsTr("Check for Updates")

    readonly property string state_: updater ? updater.state : "idle"

    // Closing the window is the same as Cancel: no download left running unseen.
    onClosing: if (updater && state_ === "downloading") updater.cancel()

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
        }
        return ""
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Style.dp(16)
        spacing: Style.dp(12)

        Label {
            Layout.fillWidth: true
            Layout.fillHeight: true
            wrapMode: Text.WordWrap
            textFormat: Text.StyledText
            text: _root.message()
        }

        Label {
            visible: _root.state_ === "available"
            text: "<a href='notes'>Release notes</a>"
            textFormat: Text.StyledText
            onLinkActivated: () => { updater.openReleasePage() }
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
                text: _root.state_ === "available" || _root.state_ === "ready"
                    ? qsTr("Later") : qsTr("Close")
                visible: _root.state_ !== "downloading"
                onClicked: () => { _root.close() }
            }
        }
    }
}
