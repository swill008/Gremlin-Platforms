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
    // Solid info blue with white text (Style.onColor) so it can't be missed.
    color: Style.info

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 1
        color: Style.infoFillDeep
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
            color: Style.onColor
        }

        Label {
            objectName: "whatsNewBannerText"
            Layout.fillWidth: true
            elide: Text.ElideRight
            color: Style.onColor
            font.pixelSize: Style.fontSize
            text: whatsNew ? whatsNew.bannerText : ""
        }

        Rectangle {
            id: _link
            objectName: "whatsNewBannerLink"
            readonly property string text: _linkText.text
            implicitWidth: _linkText.implicitWidth + Style.dp(16)
            implicitHeight: _linkText.implicitHeight + Style.dp(6)
            radius: Style.dp(4)
            color: _linkHover.hovered ? Qt.rgba(1, 1, 1, 0.22) : Style.clear
            border.width: 1
            border.color: Style.onColor
            Accessible.role: Accessible.Link
            Accessible.name: text
            function activate() {
                if (whatsNew)
                    whatsNew.showBannerNotes()
                _banner.openNotes()
            }
            Label {
                id: _linkText
                anchors.centerIn: parent
                text: qsTr("What's New")
                color: Style.onColor
                font.pixelSize: Style.fontSize
            }
            TapHandler { onTapped: _link.activate() }
            HoverHandler { id: _linkHover; cursorShape: Qt.PointingHandCursor }
        }

        ToolButton {
            objectName: "whatsNewBannerClose"
            text: "✕"
            font.pixelSize: Style.fontSize
            Accessible.name: qsTr("Close")
            contentItem: Label {
                text: parent.text
                font: parent.font
                color: Style.onColor
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle {
                radius: Style.dp(4)
                color: parent.hovered ? Qt.rgba(1, 1, 1, 0.22) : Style.clear
            }
            onClicked: if (whatsNew) whatsNew.dismissBanner()
        }
    }
}
