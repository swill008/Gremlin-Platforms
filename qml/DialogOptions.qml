// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Config
import Gremlin.Style
import "helpers.js" as Helpers

ApplicationWindow {
    font.pixelSize: Style.fontSize
    id: _options
    // ToolWindowMemory sets the saved or default size when the window opens.
    width: 1200
    height: 700
    // Never wider or taller than the screen, even at a high UI scale.
    minimumWidth: Style.fitWidth(Style.dp(900), Screen)
    minimumHeight: Style.fitHeight(Style.dp(600), Screen)

    U.Universal.theme: Style.theme
    color: Style.background

    title: "Options"

    ToolWindowMemory {
        host: _options
        name: "options"
        defaultWidth: Style.fitWidth(Style.dp(1000), Screen)
        defaultHeight: Style.fitHeight(Style.dp(700), Screen)
    }

    onClosing: () => {
        backend.emitConfigChanged()
    }

    ConfigSectionModel {
        id: _sectionModel
    }

    property int currentSection: 0

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
                    Layout.bottomMargin: Style.dp(10)
                    spacing: Style.dp(8)
                    Label {
                        text: "\uF3E5"
                        font.family: "bootstrap-icons"
                        font.pixelSize: Style.dp(18)
                        color: Style.fgSoft
                    }
                    Label {
                        text: "Options"
                        font.pixelSize: Style.dp(17)
                        color: Style.fgStrong
                    }
                }

                Repeater {
                    model: _sectionModel
                    delegate: ConfigSectionButton {}
                }

                Item { Layout.fillHeight: true }
            }
        }

        // The page: its title, the search box, and the settings.
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: Style.dp(20)
                Layout.rightMargin: Style.dp(20)
                Layout.topMargin: Style.dp(14)
                spacing: Style.dp(12)

                Label {
                    Layout.fillWidth: true
                    text: _search.text.trim().length
                        ? "Search"
                        : String(_sectionModel.data(_sectionModel.index(_options.currentSection, 0), Qt.UserRole + 1) || "")
                    color: Style.fgStrong
                    font.pixelSize: Style.dp(20)
                }
                TextField {
                    id: _search
                    Layout.preferredWidth: Style.dp(240)
                    placeholderText: "Search options"
                }
            }

            ConfigSection {
                Layout.fillWidth: true
                Layout.fillHeight: true
                sectionModel: _sectionModel
                currentIndex: _options.currentSection
                filterText: _search.text
            }
        }
    }
}
