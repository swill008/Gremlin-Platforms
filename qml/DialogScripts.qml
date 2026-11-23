// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Style

// Scripts (04 S84-S89, S96): a window of its own in the Options look, the
// open profile's scripts on the left and the picked script's variables on
// the right (ScriptManager.qml). One window; it follows the open profile.
ApplicationWindow {
    id: _window
    objectName: "scriptsWindow"

    font.pixelSize: Style.fontSize

    EscapeCloses { host: _window }
    // ToolWindowMemory sets the saved or default size when the window opens.
    width: 1200
    height: 700
    minimumWidth: Style.fitWidth(Style.dp(900), Screen)
    minimumHeight: Style.fitHeight(Style.dp(500), Screen)

    U.Universal.theme: Style.theme
    color: Style.background

    title: "Scripts"

    ToolWindowMemory {
        host: _window
        name: "scripts"
        defaultWidth: Style.fitWidth(Style.dp(1100), Screen)
        defaultHeight: Style.fitHeight(Style.dp(700), Screen)
    }

    BootstrapIcons {
        id: _icons
        resource: "qrc:///BootstrapIcons"
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Heading: the window's name, the open profile and where the
        // changes go (as Profile Settings).
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: _heading.implicitHeight + Style.dp(20)
            color: Style.bgPage

            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: Style.dp(1)
                color: Style.line
            }

            ColumnLayout {
                id: _heading

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: Style.dp(16)
                anchors.rightMargin: Style.dp(16)
                spacing: Style.dp(2)

                RowLayout {
                    spacing: Style.dp(8)
                    Label {
                        text: _icons.icons.script
                        font.family: Style.iconFont
                        font.pixelSize: Style.dp(18)
                        color: Style.fgSoft
                    }
                    Label {
                        text: "Scripts"
                        font.pixelSize: Style.dp(17)
                        color: Style.fgStrong
                    }
                }

                // The open profile, and where the changes go.
                Label {
                    objectName: "scriptsProfileName"
                    Layout.fillWidth: true
                    Layout.topMargin: Style.dp(4)
                    text: backend ? backend.windowTitle : ""
                    color: Style.fgSoft
                    font.pixelSize: Style.dp(13)
                    elide: Text.ElideMiddle
                }
                Label {
                    objectName: "scriptsSavedNote"
                    Layout.fillWidth: true
                    text: "Saved with the profile (Save Profile)"
                    color: Style.fgMuted
                    font.pixelSize: Style.dp(12)
                    wrapMode: Text.WordWrap
                }
            }
        }

        ScriptManager {
            objectName: "scriptManager"
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }
}
