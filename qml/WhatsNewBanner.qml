// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style

// The thin bar under the toolbar after Gremlin starts on a newer version
// than last ran (01 S183): a dot, "Updated — now 1.0.40", a What's New
// link and a close button. The model is the context property whatsNew
// (null in some tests); the window is opened by whoever listens to
// openNotes.
Rectangle {
    id: _banner
    objectName: "whatsNewBanner"

    signal openNotes()

    readonly property bool shown: whatsNew ? whatsNew.bannerVisible : false

    visible: shown
    Layout.fillWidth: true
    implicitHeight: shown ? _row.implicitHeight + Style.dp(8) : 0
    color: Style.bgWell

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 1
        color: Style.line
    }

    RowLayout {
        id: _row
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: Style.dp(12)
        anchors.rightMargin: Style.dp(8)
        spacing: Style.dp(8)

        Rectangle {
            Layout.preferredWidth: Style.dp(8)
            Layout.preferredHeight: Style.dp(8)
            radius: width / 2
            color: Style.ok
        }

        Label {
            objectName: "whatsNewBannerText"
            Layout.fillWidth: true
            elide: Text.ElideRight
            color: Style.fgSoft
            font.pixelSize: Style.fontSize
            text: whatsNew ? whatsNew.bannerText : ""
        }

        Label {
            id: _link
            objectName: "whatsNewBannerLink"
            text: qsTr("What's New")
            color: Style.fgStrong
            font.pixelSize: Style.fontSize
            font.underline: true
            Accessible.role: Accessible.Link
            Accessible.name: text
            function activate() {
                if (whatsNew)
                    whatsNew.showBannerNotes()
                _banner.openNotes()
            }
            TapHandler { onTapped: _link.activate() }
            HoverHandler { cursorShape: Qt.PointingHandCursor }
        }

        ToolButton {
            objectName: "whatsNewBannerClose"
            text: "✕"
            font.pixelSize: Style.fontSize
            Accessible.name: qsTr("Close")
            onClicked: if (whatsNew) whatsNew.dismissBanner()
        }
    }
}
