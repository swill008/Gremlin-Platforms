// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style

// The What's New notice under the toolbar after Gremlin starts on a newer
// version than last ran (01 S183), styled like a Windows 11 InfoBar in the gold of SuperCargo: a
// floating card inset from the window edges with a solid stripe on its
// left, a sparkle, a bold title and a softer message, a filled What's New
// button and a quiet close. The model is the context property whatsNew
// (null in some tests); the window is opened by whoever listens to
// openNotes.
Item {
    id: _banner
    objectName: "whatsNewBanner"

    signal openNotes()

    readonly property bool shown: whatsNew ? whatsNew.bannerVisible : false
    property bool _animated: false
    readonly property real _radius: Style.dp(6)
    readonly property real _stripe: Style.dp(4)

    visible: shown
    Layout.fillWidth: true
    implicitHeight: shown ? _row.implicitHeight + Style.dp(16) + Style.dp(16) : 0

    // Fade and slide in once, when the card first appears.
    function _playIn() {
        if (_animated || !shown)
            return
        _animated = true
        _intro.restart()
    }
    onShownChanged: _playIn()
    Component.onCompleted: _playIn()

    ParallelAnimation {
        id: _intro
        NumberAnimation {
            target: _card; property: "opacity"
            from: 0; to: 1; duration: 200; easing.type: Easing.OutCubic
        }
        NumberAnimation {
            target: _slide; property: "y"
            from: -Style.dp(6); to: 0; duration: 200; easing.type: Easing.OutCubic
        }
    }

    // The whole card; its stripe is the info-coloured shape behind the fill.
    Item {
        id: _card
        anchors.fill: parent
        anchors.margins: Style.dp(8)
        transform: Translate { id: _slide }

        Rectangle {
            objectName: "whatsNewBannerStripe"
            anchors.fill: parent
            radius: _banner._radius
            color: Style.gold
        }

        Rectangle {
            objectName: "whatsNewBannerCard"
            anchors.fill: parent
            anchors.leftMargin: _banner._stripe
            radius: _banner._radius
            color: Style.goldFill

            // Squares off the fill's left corners so the stripe shows whole.
            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: _banner._radius * 2
                color: parent.color
            }
        }

        Rectangle {
            anchors.fill: parent
            radius: _banner._radius
            color: Style.clear
            border.width: 1
            border.color: Style.goldLine
        }

        RowLayout {
            id: _row
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: _banner._stripe + Style.dp(12)
            anchors.rightMargin: Style.dp(8)
            spacing: Style.dp(10)

            Label {
                text: "✦"
                color: Style.gold
                font.pixelSize: Style.fontSize + Style.dp(2)
                Accessible.ignored: true
            }

            Label {
                objectName: "whatsNewBannerTitle"
                font.bold: true
                color: Style.fgStrong
                font.pixelSize: Style.fontSize
                text: whatsNew ? whatsNew.bannerTitle : ""
            }

            // Hidden first when the window is narrow.
            Label {
                objectName: "whatsNewBannerMessage"
                Layout.fillWidth: true
                visible: _card.width > Style.dp(480)
                elide: Text.ElideRight
                color: Style.fgSoft
                font.pixelSize: Style.fontSize
                text: whatsNew ? whatsNew.bannerMessage : ""
            }

            Item {
                Layout.fillWidth: true
                visible: !_banner.shown || _card.width <= Style.dp(480)
            }

            Rectangle {
                id: _link
                objectName: "whatsNewBannerLink"
                readonly property string text: _linkText.text
                implicitWidth: _linkText.implicitWidth + Style.dp(20)
                implicitHeight: _linkText.implicitHeight + Style.dp(8)
                radius: Style.dp(4)
                border.width: 1
                border.color: Style.gold
                color: _linkHover.hovered ? Style.gold : Style.goldFillStrong
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
                    color: _linkHover.hovered ? Style.onGold : Style.fgStrong
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
                    color: parent.hovered ? Style.fgStrong : Style.fgSoft
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle {
                    radius: Style.dp(4)
                    color: parent.hovered ? Qt.rgba(1, 1, 1, 0.12) : Style.clear
                }
                onClicked: if (whatsNew) whatsNew.dismissBanner()
            }
        }
    }
}
