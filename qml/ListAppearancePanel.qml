// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

import Gremlin.Style
import Gremlin.UI
import "helpers.js" as Helpers

// The Appearance panel of the control lists (05 S125): each page
// (Device Bindings, Logical Device, Keyboard, OSC) keeps its own look in
// program settings (WindowPlacement listAppearance(pageKey), AP2). The page binds its
// ControlTree's appearance properties to this panel's properties of the
// same names, calls load() once, and closes the panel on closed().
Rectangle {
    id: _panel

    property string title: "Appearance"
    // Whose look this is: "device-bindings", "logical", "keyboard" or "osc".
    required property string pageKey
    // The live bars / LED dots rows (the Device Bindings page).
    property bool liveOptions: false

    // The panel asks to be hidden (× with nothing unsaved, or after the
    // unsaved-changes question).
    signal closed()

    property int parentHeight: 44
    property int childHeight: 32
    property int rowSpacing: 4
    property int groupInside: 0
    // Row placement (AP3): alignment and width % of input and action rows,
    // and extra space above each group after the first.
    property string parentAlign: "left"
    property int parentWidthPct: 100
    property string childAlign: "left"
    property int childWidthPct: 100
    property int groupSpacing: 0
    property string listPadShape: "sides"
    property int listPad: 0
    property int listPadTop: 0
    property int listPadRight: 0
    property int listPadBottom: 0
    property int listPadLeft: 0
    property string groupPadShape: "sides"
    property int groupPad: 0
    property int groupPadTop: 0
    property int groupPadRight: 8
    property int groupPadBottom: 0
    property int groupPadLeft: 8
    property int groupRadius: 3
    // Display colours: colorXSet is the user's choice ("" when never changed);
    // colorX is shown and follows Dark mode until a choice is made.
    property string colorGroupSet: ""
    readonly property color colorGroup: colorGroupSet.length ? colorGroupSet : Style.bgRaised
    property string parentPadShape: "sides"
    property int parentPad: 0
    property int parentPadTop: 0
    property int parentPadRight: 8
    property int parentPadBottom: 0
    property int parentPadLeft: 24
    property int parentRadius: 3
    property string colorParentSet: ""
    readonly property color colorParent: colorParentSet.length ? colorParentSet : Style.bgCard
    property int parentIndent: 16
    property int childIndent: 32
    property string childPadShape: "sides"
    property int childPad: 0
    property int childPadTop: 0
    property int childPadRight: 8
    property int childPadBottom: 0
    property int childPadLeft: 0
    property int childRadius: 3
    property string colorChildSet: ""
    readonly property color colorChild: colorChildSet.length ? colorChildSet : Style.bgCard
    property bool showChildren: true
    property bool showSummary: true
    // "N actions · targets" after each input's name (05 S142).
    property bool showActionSummary: true
    property int summaryFont: 11
    property int parentFont: 13
    property int groupFont: 15
    property int childFont: 13
    property int targetFont: 11
    property string colorActionTargetSet: ""
    readonly property color colorActionTarget: colorActionTargetSet.length ? colorActionTargetSet : Style.fgMuted
    property bool parentBold: true
    property string colorTextSet: ""
    readonly property color colorText: colorTextSet.length ? colorTextSet : Style.fg
    property string colorMutedSet: ""
    readonly property color colorMuted: colorMutedSet.length ? colorMutedSet : Style.fgMuted
    property string colorSelectedSet: ""
    readonly property color colorSelected: colorSelectedSet.length ? colorSelectedSet : Style.infoFill
    property string colorSelectBorderSet: ""
    readonly property color colorSelectBorder: colorSelectBorderSet.length ? colorSelectBorderSet : Style.line
    property string colorBorderSet: ""
    readonly property color colorBorder: colorBorderSet.length ? colorBorderSet : Style.line
    property int caretSize: 18
    property string colorCaretSet: ""
    readonly property color colorCaret: colorCaretSet.length ? colorCaretSet : Style.fg
    property int gripWidth: 8
    property int gripHeight: 18
    property int gripRadius: 2
    property string colorGripSet: ""
    readonly property color colorGrip: colorGripSet.length ? colorGripSet : Style.lineStrong
    property string _colorTarget: "parent"
    property string toastText: ""
    property string savedDisplay: ""
    property bool openShown: false
    property bool openHandles: false
    property bool openList: false
    property bool openRows: false
    property bool openGroup: false
    property bool openParent: false
    property bool openChild: false
    property bool openText: false
    property bool openSelection: false
    property bool openLive: false
    // Live lights and bars (Device Bindings only; ControlTree liveDecoration).
    property bool showLiveBars: true
    property bool showLeds: true
    property string colorLiveSet: ""
    readonly property color colorLive: colorLiveSet.length ? colorLiveSet : Style.ok

    WindowPlacement { id: _place }

    color: Style.bgCard
    border.color: Style.line
    border.width: Style.dp(1)

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Style.dp(10)
        spacing: Style.dp(8)

        RowLayout {
            Label {
                text: _panel.title
                color: Style.fg
                font.bold: true
                font.pixelSize: Style.dp(13)
                Layout.fillWidth: true
            }
            Button {
                text: "×"
                implicitWidth: Style.dp(28)
                onClicked: _panel.requestClose()
            }
        }
        RowLayout {
            spacing: Style.dp(8)
            Button { text: "Open All"; onClicked: _panel.setAllSections(true) }
            Button { text: "Close All"; onClicked: _panel.setAllSections(false) }
            Item { Layout.fillWidth: true }
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            ColumnLayout {
                width: Style.dp(330)
                spacing: Style.dp(12)

                FoldSection {
                    title: "Shown"
                    open: _panel.openShown
                    onToggled: (v) => { _panel.openShown = v }
                    FlagBox { text: "Show action rows"; source: _panel.showChildren; onUserSet: (v) => { _panel.showChildren = v } }
                    FlagBox { text: "Show written by"; source: _panel.showSummary; onUserSet: (v) => { _panel.showSummary = v } }
                    // Not on the Xbox Output View: its rows list their sources.
                    FlagBox { visible: _panel.pageKey !== "xbox-output"; text: "Show action summary"; source: _panel.showActionSummary; onUserSet: (v) => { _panel.showActionSummary = v } }
                    RowLayout {
                        Label { text: "Written-by size"; color: Style.fg; Layout.fillWidth: true }
                        TrackSpin { from: 9; to: 20; source: _panel.summaryFont; onUserSet: (v) => { _panel.summaryFont = v } }
                    }
                }
                FoldSection {
                    title: "Live"
                    visible: _panel.liveOptions
                    open: _panel.openLive
                    onToggled: (v) => { _panel.openLive = v }
                    FlagBox { text: "Show live bars"; source: _panel.showLiveBars; onUserSet: (v) => { _panel.showLiveBars = v } }
                    FlagBox { text: "Show LED dots"; source: _panel.showLeds; onUserSet: (v) => { _panel.showLeds = v } }
                    ColorPick { label: "Live bar"; swatch: _panel.colorLive; target: "live" }
                }
                FoldSection {
                    title: "Handles"
                    open: _panel.openHandles
                    onToggled: (v) => { _panel.openHandles = v }
                    RowLayout {
                        Label { text: "Caret size"; color: Style.fg; Layout.fillWidth: true }
                        TrackSpin { from: 12; to: 36; source: _panel.caretSize; onUserSet: (v) => { _panel.caretSize = v } }
                    }
                    ColorPick { label: "Caret color"; swatch: _panel.colorCaret; target: "caret" }
                    RowLayout {
                        Label { text: "Pad width"; color: Style.fg; Layout.fillWidth: true }
                        TrackSpin { from: 4; to: 36; source: _panel.gripWidth; onUserSet: (v) => { _panel.gripWidth = v } }
                    }
                    RowLayout {
                        Label { text: "Pad height"; color: Style.fg; Layout.fillWidth: true }
                        TrackSpin { from: 8; to: 42; source: _panel.gripHeight; onUserSet: (v) => { _panel.gripHeight = v } }
                    }
                    ColorPick { label: "Pad color"; swatch: _panel.colorGrip; target: "grip" }
                    RowLayout {
                        Label { text: "Pad corner"; color: Style.fg; Layout.fillWidth: true }
                        TrackSpin { from: 0; to: 16; source: _panel.gripRadius; onUserSet: (v) => { _panel.gripRadius = v } }
                    }
                }
                FoldSection {
                    title: "List"
                    open: _panel.openList
                    onToggled: (v) => { _panel.openList = v }
                    RowLayout {
                        Label { text: "Space between rows"; color: Style.fg; Layout.fillWidth: true }
                        TrackSpin { from: 0; to: 48; source: _panel.rowSpacing; onUserSet: (v) => { _panel.rowSpacing = v } }
                    }
                    Label { text: "Padding"; color: Style.fgMuted; font.pixelSize: Style.dp(11) }
                    PadFields {
                        shape: _panel.listPadShape
                        size: _panel.listPad
                        padTop: _panel.listPadTop
                        padRight: _panel.listPadRight
                        padBottom: _panel.listPadBottom
                        padLeft: _panel.listPadLeft
                        onEdited: (shape, size, padTop, padRight, padBottom, padLeft) => {
                            _panel.listPadShape = shape
                            _panel.listPad = size
                            _panel.listPadTop = padTop
                            _panel.listPadRight = padRight
                            _panel.listPadBottom = padBottom
                            _panel.listPadLeft = padLeft
                        }
                    }
                }
                FoldSection {
                    title: "Rows"
                    open: _panel.openRows
                    onToggled: (v) => { _panel.openRows = v }
                    Label { text: "Input rows"; color: Style.fgMuted; font.pixelSize: Style.dp(11) }
                    AlignPick { objectName: "appearanceParentAlign"; source: _panel.parentAlign; onUserSet: (v) => { _panel.parentAlign = v } }
                    RowLayout {
                        Label { text: "Width %"; color: Style.fg; Layout.fillWidth: true }
                        TrackSpin { from: 20; to: 100; source: _panel.parentWidthPct; onUserSet: (v) => { _panel.parentWidthPct = v } }
                    }
                    Label { text: "Action rows"; color: Style.fgMuted; font.pixelSize: Style.dp(11) }
                    AlignPick { objectName: "appearanceChildAlign"; source: _panel.childAlign; onUserSet: (v) => { _panel.childAlign = v } }
                    RowLayout {
                        Label { text: "Width %"; color: Style.fg; Layout.fillWidth: true }
                        TrackSpin { from: 20; to: 100; source: _panel.childWidthPct; onUserSet: (v) => { _panel.childWidthPct = v } }
                    }
                    RowLayout {
                        Label { text: "Space between groups"; color: Style.fg; Layout.fillWidth: true }
                        TrackSpin { from: 0; to: 48; source: _panel.groupSpacing; onUserSet: (v) => { _panel.groupSpacing = v } }
                    }
                }
                FoldSection {
                    title: "Group"
                    open: _panel.openGroup
                    onToggled: (v) => { _panel.openGroup = v }
                    RowLayout {
                        Label { text: "Space inside the group"; color: Style.fg; Layout.fillWidth: true }
                        TrackSpin { from: 0; to: 48; source: _panel.groupInside; onUserSet: (v) => { _panel.groupInside = v } }
                    }
                    Label { text: "Padding"; color: Style.fgMuted; font.pixelSize: Style.dp(11) }
                    PadFields {
                        shape: _panel.groupPadShape
                        size: _panel.groupPad
                        padTop: _panel.groupPadTop
                        padRight: _panel.groupPadRight
                        padBottom: _panel.groupPadBottom
                        padLeft: _panel.groupPadLeft
                        onEdited: (shape, size, padTop, padRight, padBottom, padLeft) => {
                            _panel.groupPadShape = shape
                            _panel.groupPad = size
                            _panel.groupPadTop = padTop
                            _panel.groupPadRight = padRight
                            _panel.groupPadBottom = padBottom
                            _panel.groupPadLeft = padLeft
                        }
                    }
                    RowLayout {
                        Label { text: "Corner radius"; color: Style.fg; Layout.fillWidth: true }
                        TrackSpin { from: 0; to: 16; source: _panel.groupRadius; onUserSet: (v) => { _panel.groupRadius = v } }
                    }
                    ColorPick { label: "Color"; swatch: _panel.colorGroup; target: "group" }
                }
                FoldSection {
                    title: "Parent Row"
                    open: _panel.openParent
                    onToggled: (v) => { _panel.openParent = v }
                    RowLayout {
                        Label { text: "Height"; color: Style.fg; Layout.fillWidth: true }
                        TrackSpin { from: 32; to: 80; source: _panel.parentHeight; onUserSet: (v) => { _panel.parentHeight = v } }
                    }
                    RowLayout {
                        Label { text: "Indent inside group"; color: Style.fg; Layout.fillWidth: true }
                        TrackSpin { from: 0; to: 160; source: _panel.parentIndent; onUserSet: (v) => { _panel.parentIndent = v } }
                    }
                    Label { text: "Padding"; color: Style.fgMuted; font.pixelSize: Style.dp(11) }
                    PadFields {
                        shape: _panel.parentPadShape
                        size: _panel.parentPad
                        padTop: _panel.parentPadTop
                        padRight: _panel.parentPadRight
                        padBottom: _panel.parentPadBottom
                        padLeft: _panel.parentPadLeft
                        onEdited: (shape, size, padTop, padRight, padBottom, padLeft) => {
                            _panel.parentPadShape = shape
                            _panel.parentPad = size
                            _panel.parentPadTop = padTop
                            _panel.parentPadRight = padRight
                            _panel.parentPadBottom = padBottom
                            _panel.parentPadLeft = padLeft
                        }
                    }
                    RowLayout {
                        Label { text: "Corner radius"; color: Style.fg; Layout.fillWidth: true }
                        TrackSpin { from: 0; to: 16; source: _panel.parentRadius; onUserSet: (v) => { _panel.parentRadius = v } }
                    }
                    ColorPick { label: "Row color"; swatch: _panel.colorParent; target: "parent" }
                }
                FoldSection {
                    title: "Action Row"
                    open: _panel.openChild
                    onToggled: (v) => { _panel.openChild = v }
                    RowLayout {
                        Label { text: "Height"; color: Style.fg; Layout.fillWidth: true }
                        TrackSpin { from: 24; to: 80; source: _panel.childHeight; onUserSet: (v) => { _panel.childHeight = v } }
                    }
                    RowLayout {
                        Label { text: "Indent past parent"; color: Style.fg; Layout.fillWidth: true }
                        TrackSpin { from: 0; to: 160; source: _panel.childIndent; onUserSet: (v) => { _panel.childIndent = v } }
                    }
                    Label { text: "Padding"; color: Style.fgMuted; font.pixelSize: Style.dp(11) }
                    PadFields {
                        shape: _panel.childPadShape
                        size: _panel.childPad
                        padTop: _panel.childPadTop
                        padRight: _panel.childPadRight
                        padBottom: _panel.childPadBottom
                        padLeft: _panel.childPadLeft
                        onEdited: (shape, size, padTop, padRight, padBottom, padLeft) => {
                            _panel.childPadShape = shape
                            _panel.childPad = size
                            _panel.childPadTop = padTop
                            _panel.childPadRight = padRight
                            _panel.childPadBottom = padBottom
                            _panel.childPadLeft = padLeft
                        }
                    }
                    RowLayout {
                        Label { text: "Corner radius"; color: Style.fg; Layout.fillWidth: true }
                        TrackSpin { from: 0; to: 16; source: _panel.childRadius; onUserSet: (v) => { _panel.childRadius = v } }
                    }
                    ColorPick { label: "Row color"; swatch: _panel.colorChild; target: "child" }
                }
                FoldSection {
                    title: "Text"
                    open: _panel.openText
                    onToggled: (v) => { _panel.openText = v }
                    RowLayout {
                        Label { text: "Parent text size"; color: Style.fg; Layout.fillWidth: true }
                        TrackSpin { from: 10; to: 22; source: _panel.parentFont; onUserSet: (v) => { _panel.parentFont = v } }
                    }
                    RowLayout {
                        Label { text: "Group text size"; color: Style.fg; Layout.fillWidth: true }
                        TrackSpin { from: 10; to: 22; source: _panel.groupFont; onUserSet: (v) => { _panel.groupFont = v } }
                    }
                    FlagBox { text: "Bold names"; source: _panel.parentBold; onUserSet: (v) => { _panel.parentBold = v } }
                    RowLayout {
                        Label { text: "Action name size"; color: Style.fg; Layout.fillWidth: true }
                        TrackSpin { from: 9; to: 20; source: _panel.childFont; onUserSet: (v) => { _panel.childFont = v } }
                    }
                    RowLayout {
                        Label { text: "Action target size"; color: Style.fg; Layout.fillWidth: true }
                        TrackSpin { from: 9; to: 20; source: _panel.targetFont; onUserSet: (v) => { _panel.targetFont = v } }
                    }
                    ColorPick { label: "Text color"; swatch: _panel.colorText; target: "text" }
                    ColorPick { label: "Muted text"; swatch: _panel.colorMuted; target: "muted" }
                    ColorPick { label: "Action target"; swatch: _panel.colorActionTarget; target: "actionTarget" }
                }
                FoldSection {
                    title: "Selection"
                    open: _panel.openSelection
                    onToggled: (v) => { _panel.openSelection = v }
                    ColorPick { label: "Fill of a selected row"; swatch: _panel.colorSelected; target: "selected" }
                    ColorPick { label: "Line around a selected row"; swatch: _panel.colorSelectBorder; target: "selectBorder" }
                }
            }
        }

        RowLayout {
            spacing: Style.dp(6)
            Button {
                Layout.fillWidth: true
                Layout.preferredHeight: Style.dp(44)
                text: "Reset\nAppearance"
                onClicked: _panel.reset()
                contentItem: Text {
                    text: parent.text
                    color: Style.onColor
                    font.pixelSize: Style.dp(12)
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle {
                    implicitHeight: Style.dp(44)
                    color: parent.down ? Style.dangerPressed : (parent.hovered ? Style.dangerBright : Style.danger)
                    border.width: Style.dp(1)
                    border.color: parent.hovered ? Style.dangerTextSoft : Style.dangerHover
                }
            }
            Button {
                Layout.fillWidth: true
                Layout.preferredHeight: Style.dp(44)
                text: "Save\nAppearance"
                highlighted: true
                onClicked: _panel.save()
                contentItem: Text {
                    text: parent.text
                    color: Style.onColor
                    font.pixelSize: Style.dp(12)
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }
    }

    component FoldSection: ColumnLayout {
        id: fold
        property string title: ""
        property bool open: false
        signal toggled(bool value)
        default property alias body: _body.data
        Layout.fillWidth: true
        spacing: Style.dp(4)

        Rectangle {
            Layout.fillWidth: true
            height: Style.dp(26)
            color: Style.bgRaised
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Style.dp(8)
                anchors.rightMargin: Style.dp(8)
                spacing: Style.dp(6)
                Label {
                    text: fold.open ? "\u25BC" : "\u25B6"
                    color: Style.fg
                    font.pixelSize: Style.dp(10)
                }
                Label {
                    text: fold.title
                    color: Style.fg
                    font.pixelSize: Style.dp(11)
                    font.bold: true
                    Layout.fillWidth: true
                }
            }
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: fold.toggled(!fold.open)
            }
        }
        ColumnLayout {
            id: _body
            visible: fold.open
            Layout.fillWidth: true
            spacing: Style.dp(4)
        }
    }

    component TrackSpin: SpinBox {
        property int source: 0
        signal userSet(int value)
        editable: true
        Component.onCompleted: value = source
        onSourceChanged: if (value !== source) value = source
        onValueModified: userSet(value)
    }

    component FlagBox: CheckBox {
        property bool source: false
        signal userSet(bool value)
        Component.onCompleted: checked = source
        onSourceChanged: if (!pressed) checked = source
        onClicked: userSet(checked)
    }

    component AlignPick: RowLayout {
        id: _alignRow
        property string source: "left"
        signal userSet(string value)
        readonly property var values: ["left", "center", "right"]
        Layout.fillWidth: true
        Label { text: "Alignment"; color: Style.fg; Layout.preferredWidth: Style.dp(70) }
        ComboBox {
            id: _alignBox
            Layout.fillWidth: true
            model: ["Left", "Center", "Right"]
            Component.onCompleted: currentIndex = Math.max(0, _alignRow.values.indexOf(_alignRow.source))
            onActivated: _alignRow.userSet(_alignRow.values[currentIndex])
        }
        onSourceChanged: _alignBox.currentIndex = Math.max(0, _alignRow.values.indexOf(_alignRow.source))
    }

    component PadFields: ColumnLayout {
        property string shape: "box"
        property int size: 8
        property int padTop: 0
        property int padRight: 8
        property int padBottom: 0
        property int padLeft: 8
        signal edited(string shape, int size, int padTop, int padRight, int padBottom, int padLeft)
        onShapeChanged: if (_shapePick) _shapePick.currentIndex = _shapePick.pick(shape)
        Layout.fillWidth: true
        spacing: Style.dp(4)

        RowLayout {
            Label { text: "Shape"; color: Style.fg; Layout.preferredWidth: Style.dp(70) }
            ComboBox {
                id: _shapePick
                Layout.fillWidth: true
                model: ["Same on all sides", "Each side"]
                function pick(value) { return value === "sides" ? 1 : 0 }
                Component.onCompleted: currentIndex = pick(shape)
                onActivated: {
                    if (currentIndex === 0)
                        edited("box", size, size, size, size, size)
                    else
                        edited("sides", size, padTop, padRight, padBottom, padLeft)
                }
            }
        }
        RowLayout {
            visible: shape !== "sides"
            Label { text: "Size"; color: Style.fg; Layout.fillWidth: true }
            TrackSpin { from: 0; to: 48; source: size; onUserSet: (v) => { edited("box", v, v, v, v, v) } }
        }
        RowLayout {
            visible: shape === "sides"
            Label { text: "Top"; color: Style.fg; Layout.fillWidth: true }
            TrackSpin { from: 0; to: 48; source: padTop; onUserSet: (v) => { edited("sides", size, v, padRight, padBottom, padLeft) } }
        }
        RowLayout {
            visible: shape === "sides"
            Label { text: "Right"; color: Style.fg; Layout.fillWidth: true }
            TrackSpin { from: 0; to: 48; source: padRight; onUserSet: (v) => { edited("sides", size, padTop, v, padBottom, padLeft) } }
        }
        RowLayout {
            visible: shape === "sides"
            Label { text: "Bottom"; color: Style.fg; Layout.fillWidth: true }
            TrackSpin { from: 0; to: 48; source: padBottom; onUserSet: (v) => { edited("sides", size, padTop, padRight, v, padLeft) } }
        }
        RowLayout {
            visible: shape === "sides"
            Label { text: "Left"; color: Style.fg; Layout.fillWidth: true }
            TrackSpin { from: 0; to: 48; source: padLeft; onUserSet: (v) => { edited("sides", size, padTop, padRight, padBottom, v) } }
        }
    }

    component ColorPick: RowLayout {
        property string label: ""
        property color swatch: Style.bgCard
        property string target: ""
        Layout.fillWidth: true
        Label {
            text: label
            color: Style.fg
            wrapMode: Text.WordWrap
            Layout.preferredWidth: Style.dp(150)
            Layout.maximumWidth: Style.dp(160)
        }
        Button {
            Layout.fillWidth: true
            text: "Choose\u2026"
            onClicked: { _panel._colorTarget = target; _colorDlg.selectedColor = swatch; _colorDlg.open() }
            background: Rectangle { color: swatch; border.color: Style.line; border.width: 1; radius: 3 }
            // Dark text on a light swatch, white on a dark one.
            contentItem: Label { text: parent.text; color: swatch.hslLightness > 0.6 ? Style.onLight : Style.onColor; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
        }
        // Back to the colour that follows Dark mode.
        Button {
            readonly property string setName: _panel.userColourOf(target)
            visible: setName.length > 0
            enabled: visible && _panel[setName].length > 0
            text: "Default"
            onClicked: _panel[setName] = ""
        }
    }

    function numVal(v, d) {
        var n = Number(v)
        return (v === undefined || v === null || v === "" || isNaN(n)) ? d : n
    }

    function alignVal(v) {
        return (v === "center" || v === "right") ? v : "left"
    }

    function displayPayload() {
        return {
            "rowSpacing": rowSpacing,
            "groupInside": groupInside,
            "parentAlign": parentAlign,
            "parentWidthPct": parentWidthPct,
            "childAlign": childAlign,
            "childWidthPct": childWidthPct,
            "groupSpacing": groupSpacing,
            "listPadShape": listPadShape,
            "listPad": listPad,
            "listPadTop": listPadTop,
            "listPadRight": listPadRight,
            "listPadBottom": listPadBottom,
            "listPadLeft": listPadLeft,
            "groupPadShape": groupPadShape,
            "groupPad": groupPad,
            "groupPadTop": groupPadTop,
            "groupPadRight": groupPadRight,
            "groupPadBottom": groupPadBottom,
            "groupPadLeft": groupPadLeft,
            "groupRadius": groupRadius,
            "colorGroup": colorGroupSet,
            "parentHeight": parentHeight,
            "parentPadShape": parentPadShape,
            "parentPad": parentPad,
            "parentPadTop": parentPadTop,
            "parentPadRight": parentPadRight,
            "parentPadBottom": parentPadBottom,
            "parentPadLeft": parentPadLeft,
            "parentRadius": parentRadius,
            "colorParent": colorParentSet,
            "parentIndent": parentIndent,
            "childHeight": childHeight,
            "childIndent": childIndent,
            "childPadShape": childPadShape,
            "childPad": childPad,
            "childPadTop": childPadTop,
            "childPadRight": childPadRight,
            "childPadBottom": childPadBottom,
            "childPadLeft": childPadLeft,
            "childRadius": childRadius,
            "colorChild": colorChildSet,
            "showChildren": showChildren,
            "showSummary": showSummary,
            "showActionSummary": showActionSummary,
            "summaryFont": summaryFont,
            "parentFont": parentFont,
            "groupFont": groupFont,
            "childFont": childFont,
            "targetFont": targetFont,
            "colorActionTarget": colorActionTargetSet,
            "parentBold": parentBold,
            "colorText": colorTextSet,
            "colorMuted": colorMutedSet,
            "colorSelected": colorSelectedSet,
            "colorSelectBorder": colorSelectBorderSet,
            "colorBorder": colorBorderSet,
            "caretSize": caretSize,
            "colorCaret": colorCaretSet,
            "gripWidth": gripWidth,
            "gripHeight": gripHeight,
            "gripRadius": gripRadius,
            "colorGrip": colorGripSet,
            "showLiveBars": showLiveBars,
            "showLeds": showLeds,
            "colorLive": colorLiveSet
        }
    }

    function applyDisplay(v) {
        if (!v)
            return
        rowSpacing = numVal(v.rowSpacing, 4)
        groupInside = numVal(v.groupInside, 0)
        parentAlign = alignVal(v.parentAlign)
        parentWidthPct = Math.max(20, Math.min(100, numVal(v.parentWidthPct, 100)))
        childAlign = alignVal(v.childAlign)
        childWidthPct = Math.max(20, Math.min(100, numVal(v.childWidthPct, 100)))
        groupSpacing = numVal(v.groupSpacing, 0)
        listPadShape = v.listPadShape || "sides"
        listPad = numVal(v.listPad, 0)
        listPadTop = numVal(v.listPadTop, 0)
        listPadRight = numVal(v.listPadRight, 0)
        listPadBottom = numVal(v.listPadBottom, 0)
        listPadLeft = numVal(v.listPadLeft, 0)
        groupPadShape = v.groupPadShape || "sides"
        groupPad = numVal(v.groupPad, 0)
        groupPadTop = numVal(v.groupPadTop, 0)
        groupPadRight = numVal(v.groupPadRight, 8)
        groupPadBottom = numVal(v.groupPadBottom, 0)
        groupPadLeft = numVal(v.groupPadLeft, 8)
        groupRadius = numVal(v.groupRadius, 3)
        colorGroupSet = Helpers.userColour(v.colorGroup, "#27272A")
        parentHeight = numVal(v.parentHeight, 44)
        parentPadShape = v.parentPadShape || "sides"
        parentPad = numVal(v.parentPad, 0)
        parentPadTop = numVal(v.parentPadTop, 0)
        parentPadRight = numVal(v.parentPadRight, 8)
        parentPadBottom = numVal(v.parentPadBottom, 0)
        parentPadLeft = numVal(v.parentPadLeft, 24)
        parentRadius = numVal(v.parentRadius, 3)
        colorParentSet = Helpers.userColour(v.colorParent, "#18181B")
        parentIndent = numVal(v.parentIndent, 16)
        childHeight = numVal(v.childHeight, 32)
        childIndent = numVal(v.childIndent, 32)
        childPadShape = v.childPadShape || "sides"
        childPad = numVal(v.childPad, 0)
        childPadTop = numVal(v.childPadTop, 0)
        childPadRight = numVal(v.childPadRight, 8)
        childPadBottom = numVal(v.childPadBottom, 0)
        childPadLeft = numVal(v.childPadLeft, 0)
        childRadius = numVal(v.childRadius, 3)
        colorChildSet = Helpers.userColour(v.colorChild, "#18181B")
        showChildren = v.showChildren !== false
        showSummary = v.showSummary !== false
        showActionSummary = v.showActionSummary !== false
        summaryFont = numVal(v.summaryFont, 11)
        parentFont = numVal(v.parentFont, 13)
        groupFont = numVal(v.groupFont, 15)
        childFont = numVal(v.childFont, 13)
        targetFont = numVal(v.targetFont, 11)
        colorActionTargetSet = Helpers.userColour(v.colorActionTarget, "#A1A1AA")
        parentBold = v.parentBold !== false
        colorTextSet = Helpers.userColour(v.colorText, "#E4E4E7")
        colorMutedSet = Helpers.userColour(v.colorMuted, "#A1A1AA")
        colorSelectedSet = Helpers.userColour(v.colorSelected, "#1E3A5F")
        colorSelectBorderSet = Helpers.userColour(v.colorSelectBorder, "#3F3F46")
        colorBorderSet = Helpers.userColour(v.colorBorder, "#3F3F46")
        caretSize = numVal(v.caretSize, 18)
        colorCaretSet = Helpers.userColour(v.colorCaret, "#E4E4E7")
        gripWidth = numVal(v.gripWidth, 8)
        gripHeight = numVal(v.gripHeight, 18)
        gripRadius = numVal(v.gripRadius, 2)
        colorGripSet = Helpers.userColour(v.colorGrip, "#52525B")
        showLiveBars = v.showLiveBars !== false
        showLeds = v.showLeds !== false
        colorLiveSet = Helpers.userColour(v.colorLive, "#22C55E")
    }

    function userColourOf(target) {
        var names = { group: "colorGroupSet", parent: "colorParentSet", child: "colorChildSet", actionTarget: "colorActionTargetSet", text: "colorTextSet", muted: "colorMutedSet", selected: "colorSelectedSet", selectBorder: "colorSelectBorderSet", border: "colorBorderSet", caret: "colorCaretSet", grip: "colorGripSet", live: "colorLiveSet" }
        return names[target] || ""
    }

    function applyDisplayDefaults() {
        rowSpacing = 4
        groupInside = 0
        parentAlign = "left"
        parentWidthPct = 100
        childAlign = "left"
        childWidthPct = 100
        groupSpacing = 0
        listPadShape = "sides"
        listPad = 0
        listPadTop = 0
        listPadRight = 0
        listPadBottom = 0
        listPadLeft = 0
        groupPadShape = "sides"
        groupPad = 0
        groupPadTop = 0
        groupPadRight = 8
        groupPadBottom = 0
        groupPadLeft = 8
        groupRadius = 3
        colorGroupSet = ""
        parentHeight = 44
        parentPadShape = "sides"
        parentPad = 0
        parentPadTop = 0
        parentPadRight = 8
        parentPadBottom = 0
        parentPadLeft = 24
        parentRadius = 3
        colorParentSet = ""
        parentIndent = 16
        childHeight = 32
        childIndent = 32
        childPadShape = "sides"
        childPad = 0
        childPadTop = 0
        childPadRight = 8
        childPadBottom = 0
        childPadLeft = 0
        childRadius = 3
        colorChildSet = ""
        showChildren = true
        showSummary = true
        showActionSummary = true
        summaryFont = 11
        parentFont = 13
        groupFont = 15
        childFont = 13
        targetFont = 11
        colorActionTargetSet = ""
        parentBold = true
        colorTextSet = ""
        colorMutedSet = ""
        colorSelectedSet = ""
        colorSelectBorderSet = ""
        colorBorderSet = ""
        caretSize = 18
        colorCaretSet = ""
        gripWidth = 8
        gripHeight = 18
        gripRadius = 2
        colorGripSet = ""
        showLiveBars = true
        showLeds = true
        colorLiveSet = ""
        setAllSections(false)
    }

    function setAllSections(v) {
        openShown = v
        openHandles = v
        openList = v
        openRows = v
        openGroup = v
        openParent = v
        openChild = v
        openText = v
        openSelection = v
        openLive = v
    }

    function rememberDisplay() {
        savedDisplay = JSON.stringify(displayPayload())
    }

    function dirty() {
        return savedDisplay.length > 0 && JSON.stringify(displayPayload()) !== savedDisplay
    }

    // Reads this page's setting; keys it doesn't have take their defaults.
    function load() {
        var v = {}
        try {
            v = JSON.parse(_place.listAppearance(pageKey))
        } catch (e) {
            v = {}
        }
        if (!v || typeof v !== "object" || Array.isArray(v) || Object.keys(v).length === 0)
            applyDisplayDefaults()
        else
            applyDisplay(v)
        rememberDisplay()
    }

    function save() {
        _place.setListAppearance(pageKey, JSON.stringify(displayPayload()))
        rememberDisplay()
        toastText = "Saved for this page."
        _savedToast.open()
    }

    function reset() {
        applyDisplayDefaults()
        toastText = "Options have been reset"
        _savedToast.open()
    }

    function requestClose() {
        if (!dirty()) {
            _panel.closed()
            return
        }
        _displayGate.ask("Appearance changes are not saved. Close this panel and they will be lost.")
    }

    ColorDialog {
        id: _colorDlg
        title: "Choose Color"
        onAccepted: {
            var c = selectedColor.toString()
            if (_colorTarget === "child") colorChildSet = c
            else if (_colorTarget === "selected") colorSelectedSet = c
            else if (_colorTarget === "text") colorTextSet = c
            else if (_colorTarget === "muted") colorMutedSet = c
            else if (_colorTarget === "actionTarget") colorActionTargetSet = c
            else if (_colorTarget === "selectBorder") colorSelectBorderSet = c
            else if (_colorTarget === "border") colorBorderSet = c
            else if (_colorTarget === "group") colorGroupSet = c
            else if (_colorTarget === "grip") colorGripSet = c
            else if (_colorTarget === "caret") colorCaretSet = c
            else if (_colorTarget === "live") colorLiveSet = c
            else colorParentSet = c
        }
    }

    DismissibleDialog {
        id: _displayGate
        onSaveChosen: {
            save()
            _panel.closed()
        }
        onDiscardChosen: {
            load()
            _panel.closed()
        }
    }

    Popup {
        id: _savedToast
        parent: Overlay.overlay
        anchors.centerIn: parent
        modal: true
        dim: true
        Overlay.modal: Rectangle { color: Style.dim }
        closePolicy: Popup.CloseOnPressOutside | Popup.CloseOnEscape
        padding: Style.dp(18)
        background: Rectangle {
            color: Style.bgRaised
            border.color: Style.lineStrong
            radius: Style.dp(6)
        }
        contentItem: Label {
            text: toastText
            color: Style.fgStrong
            font.pixelSize: Style.dp(14)
            horizontalAlignment: Text.AlignHCenter
        }
        Timer {
            id: _savedTimer
            interval: 1400
            onTriggered: _savedToast.close()
        }
        onOpened: _savedTimer.restart()
        onClosed: _savedTimer.stop()
    }

}
