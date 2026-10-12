// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Device
import Gremlin.Menus
import Gremlin.Style
import Gremlin.UI

import "control_menu.js" as ControlMenu

// One pad's section on the Xbox Output View (03 S139, D-XBOX-PADS): a
// header that folds it ("Xbox 360 N", what drives it, how many controls are
// bound), drawn like the list's group rows from the page's Appearance, then
// the pad's face lit from what the pad really sends, its chip rows (one line
// per device that drives it) and its control list (the shared ControlTree,
// view only, as tall as its rows: the page scrolls). A thin border in the
// list's border colour goes round the whole section.
Rectangle {
    id: _root

    required property int padId
    required property string title
    required property string drivenBy
    required property int boundCount

    // Set by the page.
    property bool open: true
    property bool running: false
    property var appear: null
    property string findText: ""
    property string findType: "all"
    property bool findSending: false
    property bool filtering: false

    readonly property alias list: _list

    // The Appearance's Group row look, for the header (ControlTree's group
    // rows use the same values).
    readonly property color groupColor: appear ? appear.colorGroup : Style.bgRaised
    readonly property color borderColor: appear ? appear.colorBorder : Style.line
    readonly property color textColor: appear ? appear.colorText : Style.fg
    readonly property color mutedColor: appear ? appear.colorMuted : Style.fgMuted
    readonly property int groupRadius: appear ? appear.groupRadius : 3
    readonly property int groupFont: appear ? appear.groupFont : 15
    readonly property bool groupBold: appear ? appear.parentBold : true

    signal toggleRequested()
    signal clearFilters()

    // The Group padding on one side ("Top", "Left", ...), as ControlTree
    // pads its group rows.
    function _groupPad(side) {
        if (!appear)
            return 0
        return Style.dp(appear.groupPadShape === "box" ? appear.groupPad
                                                       : appear["groupPad" + side])
    }

    objectName: "xboxPadSection" + padId
    color: "transparent"
    border.color: borderColor
    border.width: Style.dp(1)
    radius: Style.dp(groupRadius)
    implicitHeight: _column.implicitHeight + 2 * border.width

    XboxOutputListModel {
        id: _list
        padId: _root.padId
        // Polls what the pad sends only while the profile runs and the
        // list shows bars or lights.
        liveActive: _root.running && !!_root.appear
                    && (_root.appear.showLiveBars || _root.appear.showLeds)
    }

    XboxPadChipsModel {
        id: _chips
        padId: _root.padId
    }

    XboxPadLive {
        id: _live
        padId: _root.padId
        active: _root.running && _root.open
    }

    // A control's right-click menu: Find uses… (D-01-SEARCH), Search on what
    // sends to this pad's control. Keys are "parent:<kind>:<target>".
    property string _menuKey: ""
    property string _menuTitle: ""

    function findQuery(key) {
        var parts = String(key).split(":")
        if (parts.length < 3 || parts[0] !== "parent")
            return null
        return { kind: "output", output: "xbox", outputId: _root.padId,
                 inputType: ControlMenu.inputTypeOf(parts[1]), inputId: parts.slice(2).join(":") }
    }

    function openRowMenu(key, title, item, x, y) {
        _menuKey = key
        _menuTitle = title
        _rowMenu.openAt(item, x, y)
    }

    ContextMenu {
        id: _rowMenu
        build: function() {
            return ControlMenu.findUsesMenu("xbox-output-row", _root._menuTitle,
                                            _root.findQuery(_root._menuKey))
        }
    }

    function _applyFind() {
        _list.setFilter(findText, findType, findSending)
    }
    onFindTextChanged: _applyFind()
    onFindTypeChanged: _applyFind()
    onFindSendingChanged: _applyFind()
    Component.onCompleted: _applyFind()

    // One chip: the input on the left, the pad's control on the right; each
    // half lights while it is on.
    component Chip: Rectangle {
        id: _chip
        objectName: "xboxChip"
        property string deviceGuid: ""
        property var chip: ({})
        readonly property string hwLabel: chip.label || ""
        readonly property string xbLabel: chip.xboxChip || ""
        readonly property bool isAxis: chip.kind === "axis"
        readonly property real hwValue: {
            if (_live.axisStamp < 0 || _live.buttonStamp < 0)
                return 0
            return isAxis ? _live.hwAxis(deviceGuid, chip.identifier || 0)
                          : _live.hwButton(deviceGuid, chip.identifier || 0)
        }
        readonly property real xbValue: _live.xboxStamp >= 0
            ? _live.xboxValue(_root.padId, chip.xboxTarget || "") : 0
        readonly property bool hwOn: isAxis ? Math.abs(hwValue) > 0.5 : hwValue > 0.5
        readonly property bool xbOn: isAxis ? Math.abs(xbValue) > 0.5 : xbValue > 0.5
        // Each half fits its text (a short "1 | A" chip keeps its size); a
        // long name is cut with "…".
        readonly property real hwHalf: Math.max(Style.dp(32),
            Math.min(Style.dp(120), _hwText.implicitWidth + Style.dp(6)))
        readonly property real xbHalf: Math.max(Style.dp(31),
            Math.min(Style.dp(120), _xbText.implicitWidth + Style.dp(6)))

        width: hwHalf + Style.dp(1) + xbHalf
        height: Style.dp(20)
        radius: Style.dp(3)
        color: Style.background
        border.color: (hwOn || xbOn) ? Style.ok : Style.medColor
        border.width: Style.dp(1)
        clip: true

        Row {
            anchors.fill: parent
            Rectangle {
                width: _chip.hwHalf
                height: parent.height
                color: _chip.hwOn ? Style.ok : "transparent"
                Label {
                    id: _hwText
                    objectName: "chipLeftText"
                    anchors.centerIn: parent
                    width: Math.min(implicitWidth, parent.width - Style.dp(4))
                    elide: Text.ElideRight
                    text: _chip.hwLabel
                    color: _chip.hwOn ? Style.okFillDeep : Style.foreground
                    font.pixelSize: Style.dp(11)
                }
                PointerTip { text: "Input " + _chip.hwLabel }
            }
            Rectangle { width: Style.dp(1); height: parent.height; color: Style.medColor }
            Rectangle {
                width: _chip.xbHalf
                height: parent.height
                color: _chip.xbOn ? Style.ok : "transparent"
                Label {
                    id: _xbText
                    objectName: "chipRightText"
                    anchors.centerIn: parent
                    width: Math.min(implicitWidth, parent.width - Style.dp(4))
                    elide: Text.ElideRight
                    text: _chip.xbLabel
                    color: _chip.xbOn ? Style.okFillDeep : Style.foreground
                    font.pixelSize: Style.dp(11)
                }
                PointerTip { text: _chip.chip.xboxLabel || "" }
            }
        }
    }

    // One line per device: its name, then its chips.
    component ChipLine: RowLayout {
        id: _line
        property string deviceGuid: ""
        property string deviceName: ""
        property var chips: []
        Layout.fillWidth: true
        spacing: Style.dp(10)
        Label {
            text: _line.deviceName
            color: Style.foreground
            font.pixelSize: Style.dp(12)
            Layout.preferredWidth: Style.dp(200)
            Layout.alignment: Qt.AlignTop
            elide: Text.ElideRight
        }
        Flow {
            Layout.fillWidth: true
            spacing: Style.dp(6)
            Repeater {
                model: _line.chips
                delegate: Chip {
                    required property var modelData
                    deviceGuid: _line.deviceGuid
                    chip: modelData
                }
            }
        }
    }

    ColumnLayout {
        id: _column
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: _root.border.width
        spacing: 0

        // The header: click to fold or open the section.
        AbstractButton {
            id: _heading
            objectName: "xboxPadHeading" + _root.padId
            Layout.fillWidth: true
            topPadding: _root._groupPad("Top")
            bottomPadding: _root._groupPad("Bottom")
            leftPadding: _root._groupPad("Left") + Style.dp(8)
            rightPadding: _root._groupPad("Right") + Style.dp(8)
            implicitHeight: Math.max(Style.dp(40),
                                     _headRow.implicitHeight + topPadding + bottomPadding)
            hoverEnabled: true
            Accessible.name: (_root.open ? "Fold " : "Open ") + _root.title
            onClicked: _root.toggleRequested()

            // Hover lightens the Group colour.
            background: Rectangle {
                objectName: "xboxPadHeadingBox" + _root.padId
                radius: Style.dp(_root.groupRadius)
                color: _heading.hovered ? Qt.lighter(_root.groupColor, 1.25)
                                        : _root.groupColor
                border.color: _root.borderColor
                border.width: Style.dp(1)
            }

            contentItem: RowLayout {
                id: _headRow
                spacing: Style.dp(8)

                Label {
                    text: _root.open ? "▾" : "▸"
                    color: _root.textColor
                    font.pixelSize: Style.dp(13)
                }
                Label {
                    objectName: "xboxPadTitle" + _root.padId
                    text: _root.title
                    color: _root.textColor
                    font.bold: _root.groupBold
                    font.pixelSize: Style.dp(_root.groupFont)
                }
                Label {
                    text: "Driven by: " + _root.drivenBy
                    color: _root.mutedColor
                    font.pixelSize: Style.dp(12)
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                Label {
                    text: _root.boundCount === 1
                          ? "1 control bound"
                          : _root.boundCount + " controls bound"
                    color: _root.mutedColor
                    font.pixelSize: Style.dp(12)
                }
            }
        }

        // Face, chips and list, inside the section's border.
        ColumnLayout {
            id: _body
            visible: _root.open
            Layout.fillWidth: true
            Layout.margins: Style.dp(8)
            spacing: Style.dp(6)

            // The pad's face, lit from what this pad sends.
            Item {
                visible: _root.open
                Layout.fillWidth: true
                Layout.preferredHeight: _face.implicitHeight
                Xbox360Face {
                    id: _face
                    objectName: "xboxPadFace" + _root.padId
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: Math.min(implicitWidth, parent.width)
                    height: implicitHeight
                    padId: _root.padId
                    live: _live
                    stamp: _live.xboxStamp
                }
            }

            JGText {
                visible: _root.open && _chips.axisLines > 0
                text: "Mapped axes"
                opacity: 0.7
                font.pixelSize: Style.dp(13)
            }
            Repeater {
                model: _chips
                delegate: ChipLine {
                    required property string guid
                    required property string name
                    required property var axes
                    objectName: "xboxAxisLine" + _root.padId
                    visible: _root.open && axes.length > 0
                    deviceGuid: guid
                    deviceName: name
                    chips: axes
                }
            }

            JGText {
                visible: _root.open && _chips.buttonLines > 0
                text: "Mapped buttons"
                opacity: 0.7
                font.pixelSize: Style.dp(13)
            }
            Repeater {
                model: _chips
                delegate: ChipLine {
                    required property string guid
                    required property string name
                    required property var buttons
                    objectName: "xboxButtonLine" + _root.padId
                    visible: _root.open && buttons.length > 0
                    deviceGuid: guid
                    deviceName: name
                    chips: buttons
                }
            }

            // The pad's controls in pad order, each with what sends to it (S139):
            // the shared list, view only, no groups, full height in the page scroll.
            ControlTree {
                id: _tree
                objectName: "xboxOutputTree" + _root.padId
                visible: _root.open
                Layout.fillWidth: true
                Layout.preferredHeight: _root.open ? Math.max(listHeight, Style.dp(80)) : 0
                ownScroll: false
                readOnly: true
                onParentMenu: (key, title, userName, groupName, item, x, y) => {
                    _root.openRowMenu(key, title, item, x, y)
                }
                showGroups: false
                layout: _list
                namePrefix: "xboxOutput" + _root.padId
                emptyText: "No Xbox controls."
                filtering: _root.filtering
                liveDecoration: true
                liveState: _list
                onClearFilters: _root.clearFilters()
                liveBars: _root.appear.showLiveBars
                liveLeds: _root.appear.showLeds
                colorLive: _root.appear.colorLive
                parentHeight: _root.appear.parentHeight
                childHeight: _root.appear.childHeight
                rowSpacing: _root.appear.rowSpacing
                groupInside: _root.appear.groupInside
                parentAlign: _root.appear.parentAlign
                parentWidthPct: _root.appear.parentWidthPct
                childAlign: _root.appear.childAlign
                childWidthPct: _root.appear.childWidthPct
                groupSpacing: _root.appear.groupSpacing
                listPadShape: _root.appear.listPadShape
                listPad: _root.appear.listPad
                listPadTop: _root.appear.listPadTop
                listPadRight: _root.appear.listPadRight
                listPadBottom: _root.appear.listPadBottom
                listPadLeft: _root.appear.listPadLeft
                groupPadShape: _root.appear.groupPadShape
                groupPad: _root.appear.groupPad
                groupPadTop: _root.appear.groupPadTop
                groupPadRight: _root.appear.groupPadRight
                groupPadBottom: _root.appear.groupPadBottom
                groupPadLeft: _root.appear.groupPadLeft
                groupRadius: _root.appear.groupRadius
                colorGroup: _root.appear.colorGroup
                parentPadShape: _root.appear.parentPadShape
                parentPad: _root.appear.parentPad
                parentPadTop: _root.appear.parentPadTop
                parentPadRight: _root.appear.parentPadRight
                parentPadBottom: _root.appear.parentPadBottom
                parentPadLeft: _root.appear.parentPadLeft
                parentRadius: _root.appear.parentRadius
                colorParent: _root.appear.colorParent
                parentIndent: _root.appear.parentIndent
                childIndent: _root.appear.childIndent
                childPadShape: _root.appear.childPadShape
                childPad: _root.appear.childPad
                childPadTop: _root.appear.childPadTop
                childPadRight: _root.appear.childPadRight
                childPadBottom: _root.appear.childPadBottom
                childPadLeft: _root.appear.childPadLeft
                childRadius: _root.appear.childRadius
                colorChild: _root.appear.colorChild
                showChildren: _root.appear.showChildren
                showSummary: _root.appear.showSummary
                summaryFont: _root.appear.summaryFont
                parentFont: _root.appear.parentFont
                groupFont: _root.appear.groupFont
                childFont: _root.appear.childFont
                targetFont: _root.appear.targetFont
                colorActionTarget: _root.appear.colorActionTarget
                parentBold: _root.appear.parentBold
                colorText: _root.appear.colorText
                colorMuted: _root.appear.colorMuted
                colorSelected: _root.appear.colorSelected
                colorSelectBorder: _root.appear.colorSelectBorder
                colorBorder: _root.appear.colorBorder
                caretSize: _root.appear.caretSize
                colorCaret: _root.appear.colorCaret
                gripWidth: _root.appear.gripWidth
                gripHeight: _root.appear.gripHeight
                gripRadius: _root.appear.gripRadius
                colorGrip: _root.appear.colorGrip
            }
        }
    }
}
