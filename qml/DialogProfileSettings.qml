// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Style

// Profile Settings (04 S96-S98): a twin of Options for the settings saved
// with the open profile. One window; its models follow the open profile.
ApplicationWindow {
    id: _window
    objectName: "profileSettingsWindow"

    font.pixelSize: Style.fontSize

    EscapeCloses { host: _window }
    // ToolWindowMemory sets the saved or default size when the window opens.
    width: 1200
    height: 700
    minimumWidth: Style.fitWidth(Style.dp(900), Screen)
    minimumHeight: Style.fitHeight(Style.dp(600), Screen)

    U.Universal.theme: Style.theme
    color: Style.background

    title: "Profile Settings"

    // The page shown: "general" or "vjoy" (anything else shows General).
    property string section: "general"

    readonly property var sections: [
        { id: "general", name: "General" },
        { id: "vjoy", name: "vJoy" }
    ]

    readonly property string sectionTitle: {
        for (var i = 0; i < sections.length; i++) {
            if (sections[i].id === section)
                return sections[i].name
        }
        return sections[0].name
    }

    ToolWindowMemory {
        host: _window
        name: "profileSettings"
        defaultWidth: Style.fitWidth(Style.dp(1000), Screen)
        defaultHeight: Style.fitHeight(Style.dp(700), Screen)
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // Sidebar: the sections.
        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: Style.dp(200)
            color: Style.bgPage

            Rectangle {
                anchors.right: parent.right
                width: Style.dp(1)
                height: parent.height
                color: Style.line
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Style.dp(10)
                spacing: Style.dp(2)

                RowLayout {
                    Layout.leftMargin: Style.dp(6)
                    spacing: Style.dp(8)
                    Label {
                        text: ""
                        font.family: Style.iconFont
                        font.pixelSize: Style.dp(18)
                        color: Style.fgSoft
                    }
                    Label {
                        text: "Profile Settings"
                        font.pixelSize: Style.dp(17)
                        color: Style.fgStrong
                    }
                }

                // The open profile, and where the changes go.
                Label {
                    objectName: "profileSettingsProfileName"
                    Layout.fillWidth: true
                    Layout.leftMargin: Style.dp(6)
                    Layout.topMargin: Style.dp(4)
                    text: backend ? backend.windowTitle : ""
                    color: Style.fgSoft
                    font.pixelSize: Style.dp(13)
                    elide: Text.ElideMiddle
                }
                Label {
                    objectName: "profileSettingsSavedNote"
                    Layout.fillWidth: true
                    Layout.leftMargin: Style.dp(6)
                    Layout.bottomMargin: Style.dp(10)
                    text: "Saved with the profile (Save Profile)"
                    color: Style.fgMuted
                    font.pixelSize: Style.dp(12)
                    wrapMode: Text.WordWrap
                }

                Repeater {
                    model: _window.sections
                    delegate: SectionButton {}
                }

                Item { Layout.fillHeight: true }
            }
        }

        // The page: its title and the section.
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            Label {
                Layout.fillWidth: true
                Layout.leftMargin: Style.dp(20)
                Layout.rightMargin: Style.dp(20)
                Layout.topMargin: Style.dp(14)
                text: _window.sectionTitle
                color: Style.fgStrong
                font.pixelSize: Style.dp(20)
            }

            Loader {
                id: _page
                Layout.fillWidth: true
                Layout.fillHeight: true
                source: _window.section === "vjoy" ? "ProfileSettingsVJoy.qml"
                    : "ProfileSettingsGeneral.qml"
            }
        }
    }

    // A section in the sidebar, styled as Options' (ConfigSectionButton).
    component SectionButton : AbstractButton {
        id: _button

        required property var modelData
        // Any other section shows General, so General is then the chosen one.
        readonly property bool current: _window.section === modelData.id
            || (modelData.id === "general" && _window.section !== "vjoy")

        objectName: "profileSettingsSection:" + modelData.id
        text: modelData.name
        Layout.fillWidth: true
        implicitHeight: Style.dp(36)
        hoverEnabled: true

        background: Rectangle {
            radius: Style.dp(6)
            color: _button.current ? Style.bgSelected
                : (_button.hovered ? Style.bgHover : "transparent")

            Rectangle {
                visible: _button.current
                x: Style.dp(4)
                width: Style.dp(3)
                height: Style.dp(18)
                radius: Style.dp(2)
                anchors.verticalCenter: parent.verticalCenter
                color: Style.accent
            }
        }

        contentItem: Label {
            leftPadding: Style.dp(16)
            text: _button.text
            color: _button.current ? Style.fgStrong : Style.fgSoft
            font.pixelSize: Style.dp(14)
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }

        onClicked: _window.section = modelData.id
    }
}
