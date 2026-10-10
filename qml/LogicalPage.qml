// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window
import QtQuick.Dialogs

import Gremlin.Device
import Gremlin.Menus
import Gremlin.Style
import "helpers.js" as Helpers
import "confirm.js" as Confirm
import Gremlin.UI

Item {
    id: _root

    property string mode: "Default"
    // The action pane's state (ActionPane.qml saves its width and
    // "Close pane after OK").
    property alias paneUnits: _pane.paneUnits
    readonly property int paneWidth: _pane.paneWidth
    readonly property bool actionOpen: _pane.open
    readonly property string paneKey: _pane.paneKey
    readonly property string paneTitle: _pane.paneTitle
    property alias closeAfterOk: _pane.closeAfterOk
    property int parentHeight: 44
    property int childHeight: 32
    property bool displayOpen: false
    property int rowSpacing: 4
    property int groupInside: 0
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
    property string toastText: "Display Options Saved"
    property string savedDisplay: ""
    property bool openShown: false
    property bool openHandles: false
    property bool openList: false
    property bool openGroup: false
    property bool openParent: false
    property bool openChild: false
    property bool openText: false
    property bool openSelection: false
    property bool _ready: false
    // The list's open parents, folded groups and selection (ControlTree.qml).
    property alias _opened: _tree.opened
    property alias _collapsed: _tree.collapsed
    property alias _picked: _tree.picked

    // The one edit lock (06 S13, S82): nothing is edited while the profile runs.
    EditLock { id: _lock }
    readonly property bool editorLocked: _lock.locked

    // Same rules as the Undo and Redo menu items. A focused text field keeps these keys.
    readonly property bool _undoKeys: visible && !editorLocked && !actionOpen
    Shortcut {
        enabled: _root._undoKeys && _layout.canUndo
        sequences: [StandardKey.Undo]
        onActivated: _layout.undo()
    }
    // On Windows StandardKey.Redo is Ctrl+Y and Ctrl+Shift+Z; listing either
    // again makes that key ambiguous and it never fires.
    Shortcut {
        enabled: _root._undoKeys && _layout.canRedo
        sequences: [StandardKey.Redo]
        onActivated: _layout.redo()
    }

    signal leaveResolved()
    signal leaveCancelled()

    function setMode(next) {
        mode = next || "Default"
        _layout.setMode(mode)
    }

    // An open action pane with edits counts as unsaved work when leaving the page.
    property bool _leavingPage: false

    function hasUnsaved() { return _pane.hasUnsaved() }

    // Main.closeActionPanes() asks these before a tool changes bindings
    // behind the pane (05 Q8) or Run starts (06 Q6).
    function paneHasChanges() { return hasUnsaved() }

    function closeActionPane() { closePaneNow() }

    // OK for Run's "Save" (06 Q6): false when nothing could be written.
    function savePane() { return _pane.save() }

    function requestLeave() {
        if (!hasUnsaved()) {
            leaveResolved()
            return
        }
        _leavingPage = true
        _pane.askLeave("The action editor has changes that are not saved.")
    }

    function _finishLeave(resolved) {
        if (!_leavingPage)
            return
        _leavingPage = false
        if (resolved)
            leaveResolved()
        else
            leaveCancelled()
    }

    function _saveDisplayOpen() {
        if (!_ready)
            return
        _place.setDisplayPanelOpen("logical", "page", displayOpen)
    }

    function _toggleOpen(key) { _tree.toggleOpen(key) }

    function _toggleGroup(key) { _tree.toggleGroup(key) }

    function _select(key, shift) { _tree.select(key, shift) }

    function _openPane(key, seq, title) { _pane.openAt(key, seq, title) }

    function _openNewPane(key, title) { _pane.openNew(key, title) }

    function _closePane() { _pane.requestClose() }

    // After a profile change the pane belongs to a profile that is gone.
    function closePaneNow() { _pane.closeNow() }

    function _finishClose() { _pane.finishClose() }

    LogicalLayoutModel { id: _layout }
    // Its mode was deleted (the model said so and closed the draft).
    Connections {
        target: _layout
        function onPaneLost() { _root.closePaneNow() }
    }
    WindowPlacement { id: _place }

    Component.onCompleted: {
        reloadDisplay()
        displayOpen = _place.displayPanelOpen("logical", "page")
        _layout.setMode(mode)
        _ready = true
    }

    onDisplayOpenChanged: _saveDisplayOpen()
    onModeChanged: _layout.setMode(mode)

    RowLayout {
        anchors.fill: parent
        spacing: 0

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumWidth: Style.dp(360)
            spacing: Style.dp(6)

            ControlFindBar {
                id: _find
                layout: _layout
                namePrefix: "logical"
                placeholder: "System name, your name, or group"
                filters: [
                    { label: "Ungrouped", name: "ungrouped" },
                    { label: "No hardware writer", name: "noWriter" },
                    { label: "No actions in this mode", name: "noAction" }
                ]
                locked: _root.editorLocked
                paneOpen: _root.actionOpen
                onChanged: _root._applyFind()
                buttons: [
                    Button {
                        Layout.alignment: Qt.AlignTop
                        text: _root.displayOpen ? "Hide Appearance" : "Appearance…"
                        // Hiding asks about unsaved display options, like the panel's close.
                        onClicked: {
                            if (_root.displayOpen)
                                _root.requestCloseDisplay()
                            else
                                _root.displayOpen = true
                        }
                    }
                ]
            }

            ControlTree {
                id: _tree
                Layout.fillWidth: true
                Layout.fillHeight: true
                layout: _layout
                locked: _root.editorLocked
                namePrefix: "logical"
                dragMime: "application/x-gremlin-logical"
                dragLayer: _root
                emptyText: "No buttons, axes or hats yet. Right-click here to add some."
                filtering: _find.filtering
                rowExtras: _writerControls
                parentHeight: _root.parentHeight
                childHeight: _root.childHeight
                rowSpacing: _root.rowSpacing
                groupInside: _root.groupInside
                listPadShape: _root.listPadShape
                listPad: _root.listPad
                listPadTop: _root.listPadTop
                listPadRight: _root.listPadRight
                listPadBottom: _root.listPadBottom
                listPadLeft: _root.listPadLeft
                groupPadShape: _root.groupPadShape
                groupPad: _root.groupPad
                groupPadTop: _root.groupPadTop
                groupPadRight: _root.groupPadRight
                groupPadBottom: _root.groupPadBottom
                groupPadLeft: _root.groupPadLeft
                groupRadius: _root.groupRadius
                colorGroup: _root.colorGroup
                parentPadShape: _root.parentPadShape
                parentPad: _root.parentPad
                parentPadTop: _root.parentPadTop
                parentPadRight: _root.parentPadRight
                parentPadBottom: _root.parentPadBottom
                parentPadLeft: _root.parentPadLeft
                parentRadius: _root.parentRadius
                colorParent: _root.colorParent
                parentIndent: _root.parentIndent
                childIndent: _root.childIndent
                childPadShape: _root.childPadShape
                childPad: _root.childPad
                childPadTop: _root.childPadTop
                childPadRight: _root.childPadRight
                childPadBottom: _root.childPadBottom
                childPadLeft: _root.childPadLeft
                childRadius: _root.childRadius
                colorChild: _root.colorChild
                showChildren: _root.showChildren
                showSummary: _root.showSummary
                summaryFont: _root.summaryFont
                parentFont: _root.parentFont
                groupFont: _root.groupFont
                childFont: _root.childFont
                targetFont: _root.targetFont
                colorActionTarget: _root.colorActionTarget
                parentBold: _root.parentBold
                colorText: _root.colorText
                colorMuted: _root.colorMuted
                colorSelected: _root.colorSelected
                colorSelectBorder: _root.colorSelectBorder
                colorBorder: _root.colorBorder
                caretSize: _root.caretSize
                colorCaret: _root.colorCaret
                gripWidth: _root.gripWidth
                gripHeight: _root.gripHeight
                gripRadius: _root.gripRadius
                colorGrip: _root.colorGrip

                onClearFilters: _root._clearFind()
                onPageMenu: (item, x, y) => _root._openLayoutMenu(false, false, item, x, y)
                onParentMenu: (key, title, userName, groupName, item, x, y) => {
                    _root._menuKey = key
                    _root._menuTitle = title
                    _root._menuUser = userName
                    _root._menuGroup = groupName
                    _root._openLayoutMenu(true, false, item, x, y)
                }
                onGroupMenu: (groupName, item, x, y) => {
                    _root._groupName = groupName
                    _root._openLayoutMenu(false, true, item, x, y)
                }
                onActionMenu: (parentKey, seq, title, item, x, y) => {
                    _root._actionParent = parentKey
                    _root._actionSeq = seq
                    _root._actionTitle = title
                    _actionMenu.openAt(item, x, y)
                }
                onActionClicked: (parentKey, seq, title) => _root._openPane(parentKey, seq, title)
            }
        }

        ActionPane {
            id: _pane
            layout: _layout
            locked: _root.editorLocked
            namePrefix: "logical"
            onLeaveDone: (resolved) => _root._finishLeave(resolved)
        }

        Rectangle {
            visible: _root.displayOpen
            Layout.preferredWidth: Style.dp(360)
            Layout.maximumWidth: Style.dp(360)
            Layout.fillHeight: true
            color: Style.bgCard
            border.color: Style.line
            border.width: Style.dp(1)

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Style.dp(10)
                spacing: Style.dp(8)

                RowLayout {
                    Label {
                        text: "Logical Device — Appearance"
                        color: Style.fg
                        font.bold: true
                        font.pixelSize: Style.dp(13)
                        Layout.fillWidth: true
                    }
                    Button {
                        text: "×"
                        implicitWidth: Style.dp(28)
                        onClicked: _root.requestCloseDisplay()
                    }
                }
                RowLayout {
                    spacing: Style.dp(8)
                    Button { text: "Open All"; onClicked: _root.setAllSections(true) }
                    Button { text: "Close All"; onClicked: _root.setAllSections(false) }
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
                            open: _root.openShown
                            onToggled: (v) => { _root.openShown = v }
                            FlagBox { text: "Show action rows"; source: _root.showChildren; onUserSet: (v) => { _root.showChildren = v } }
                            FlagBox { text: "Show written by"; source: _root.showSummary; onUserSet: (v) => { _root.showSummary = v } }
                            RowLayout {
                                Label { text: "Written-by size"; color: Style.fg; Layout.fillWidth: true }
                                TrackSpin { from: 9; to: 20; source: _root.summaryFont; onUserSet: (v) => { _root.summaryFont = v } }
                            }
                        }
                        FoldSection {
                            title: "Handles"
                            open: _root.openHandles
                            onToggled: (v) => { _root.openHandles = v }
                            RowLayout {
                                Label { text: "Caret size"; color: Style.fg; Layout.fillWidth: true }
                                TrackSpin { from: 12; to: 36; source: _root.caretSize; onUserSet: (v) => { _root.caretSize = v } }
                            }
                            ColorPick { label: "Caret color"; swatch: _root.colorCaret; target: "caret" }
                            RowLayout {
                                Label { text: "Pad width"; color: Style.fg; Layout.fillWidth: true }
                                TrackSpin { from: 4; to: 36; source: _root.gripWidth; onUserSet: (v) => { _root.gripWidth = v } }
                            }
                            RowLayout {
                                Label { text: "Pad height"; color: Style.fg; Layout.fillWidth: true }
                                TrackSpin { from: 8; to: 42; source: _root.gripHeight; onUserSet: (v) => { _root.gripHeight = v } }
                            }
                            ColorPick { label: "Pad color"; swatch: _root.colorGrip; target: "grip" }
                            RowLayout {
                                Label { text: "Pad corner"; color: Style.fg; Layout.fillWidth: true }
                                TrackSpin { from: 0; to: 16; source: _root.gripRadius; onUserSet: (v) => { _root.gripRadius = v } }
                            }
                        }
                        FoldSection {
                            title: "List"
                            open: _root.openList
                            onToggled: (v) => { _root.openList = v }
                            RowLayout {
                                Label { text: "Space between rows"; color: Style.fg; Layout.fillWidth: true }
                                TrackSpin { from: 0; to: 48; source: _root.rowSpacing; onUserSet: (v) => { _root.rowSpacing = v } }
                            }
                            Label { text: "Padding"; color: Style.fgMuted; font.pixelSize: Style.dp(11) }
                            PadFields {
                                shape: _root.listPadShape
                                size: _root.listPad
                                padTop: _root.listPadTop
                                padRight: _root.listPadRight
                                padBottom: _root.listPadBottom
                                padLeft: _root.listPadLeft
                                onEdited: (shape, size, padTop, padRight, padBottom, padLeft) => {
                                    _root.listPadShape = shape
                                    _root.listPad = size
                                    _root.listPadTop = padTop
                                    _root.listPadRight = padRight
                                    _root.listPadBottom = padBottom
                                    _root.listPadLeft = padLeft
                                }
                            }
                        }
                        FoldSection {
                            title: "Group"
                            open: _root.openGroup
                            onToggled: (v) => { _root.openGroup = v }
                            RowLayout {
                                Label { text: "Space inside the group"; color: Style.fg; Layout.fillWidth: true }
                                TrackSpin { from: 0; to: 48; source: _root.groupInside; onUserSet: (v) => { _root.groupInside = v } }
                            }
                            Label { text: "Padding"; color: Style.fgMuted; font.pixelSize: Style.dp(11) }
                            PadFields {
                                shape: _root.groupPadShape
                                size: _root.groupPad
                                padTop: _root.groupPadTop
                                padRight: _root.groupPadRight
                                padBottom: _root.groupPadBottom
                                padLeft: _root.groupPadLeft
                                onEdited: (shape, size, padTop, padRight, padBottom, padLeft) => {
                                    _root.groupPadShape = shape
                                    _root.groupPad = size
                                    _root.groupPadTop = padTop
                                    _root.groupPadRight = padRight
                                    _root.groupPadBottom = padBottom
                                    _root.groupPadLeft = padLeft
                                }
                            }
                            RowLayout {
                                Label { text: "Corner radius"; color: Style.fg; Layout.fillWidth: true }
                                TrackSpin { from: 0; to: 16; source: _root.groupRadius; onUserSet: (v) => { _root.groupRadius = v } }
                            }
                            ColorPick { label: "Color"; swatch: _root.colorGroup; target: "group" }
                        }
                        FoldSection {
                            title: "Parent Row"
                            open: _root.openParent
                            onToggled: (v) => { _root.openParent = v }
                            RowLayout {
                                Label { text: "Height"; color: Style.fg; Layout.fillWidth: true }
                                TrackSpin { from: 32; to: 80; source: _root.parentHeight; onUserSet: (v) => { _root.parentHeight = v } }
                            }
                            RowLayout {
                                Label { text: "Indent inside group"; color: Style.fg; Layout.fillWidth: true }
                                TrackSpin { from: 0; to: 160; source: _root.parentIndent; onUserSet: (v) => { _root.parentIndent = v } }
                            }
                            Label { text: "Padding"; color: Style.fgMuted; font.pixelSize: Style.dp(11) }
                            PadFields {
                                shape: _root.parentPadShape
                                size: _root.parentPad
                                padTop: _root.parentPadTop
                                padRight: _root.parentPadRight
                                padBottom: _root.parentPadBottom
                                padLeft: _root.parentPadLeft
                                onEdited: (shape, size, padTop, padRight, padBottom, padLeft) => {
                                    _root.parentPadShape = shape
                                    _root.parentPad = size
                                    _root.parentPadTop = padTop
                                    _root.parentPadRight = padRight
                                    _root.parentPadBottom = padBottom
                                    _root.parentPadLeft = padLeft
                                }
                            }
                            RowLayout {
                                Label { text: "Corner radius"; color: Style.fg; Layout.fillWidth: true }
                                TrackSpin { from: 0; to: 16; source: _root.parentRadius; onUserSet: (v) => { _root.parentRadius = v } }
                            }
                            ColorPick { label: "Row color"; swatch: _root.colorParent; target: "parent" }
                        }
                        FoldSection {
                            title: "Action Row"
                            open: _root.openChild
                            onToggled: (v) => { _root.openChild = v }
                            RowLayout {
                                Label { text: "Height"; color: Style.fg; Layout.fillWidth: true }
                                TrackSpin { from: 24; to: 80; source: _root.childHeight; onUserSet: (v) => { _root.childHeight = v } }
                            }
                            RowLayout {
                                Label { text: "Indent past parent"; color: Style.fg; Layout.fillWidth: true }
                                TrackSpin { from: 0; to: 160; source: _root.childIndent; onUserSet: (v) => { _root.childIndent = v } }
                            }
                            Label { text: "Padding"; color: Style.fgMuted; font.pixelSize: Style.dp(11) }
                            PadFields {
                                shape: _root.childPadShape
                                size: _root.childPad
                                padTop: _root.childPadTop
                                padRight: _root.childPadRight
                                padBottom: _root.childPadBottom
                                padLeft: _root.childPadLeft
                                onEdited: (shape, size, padTop, padRight, padBottom, padLeft) => {
                                    _root.childPadShape = shape
                                    _root.childPad = size
                                    _root.childPadTop = padTop
                                    _root.childPadRight = padRight
                                    _root.childPadBottom = padBottom
                                    _root.childPadLeft = padLeft
                                }
                            }
                            RowLayout {
                                Label { text: "Corner radius"; color: Style.fg; Layout.fillWidth: true }
                                TrackSpin { from: 0; to: 16; source: _root.childRadius; onUserSet: (v) => { _root.childRadius = v } }
                            }
                            ColorPick { label: "Row color"; swatch: _root.colorChild; target: "child" }
                        }
                        FoldSection {
                            title: "Text"
                            open: _root.openText
                            onToggled: (v) => { _root.openText = v }
                            RowLayout {
                                Label { text: "Parent text size"; color: Style.fg; Layout.fillWidth: true }
                                TrackSpin { from: 10; to: 22; source: _root.parentFont; onUserSet: (v) => { _root.parentFont = v } }
                            }
                            RowLayout {
                                Label { text: "Group text size"; color: Style.fg; Layout.fillWidth: true }
                                TrackSpin { from: 10; to: 22; source: _root.groupFont; onUserSet: (v) => { _root.groupFont = v } }
                            }
                            FlagBox { text: "Bold names"; source: _root.parentBold; onUserSet: (v) => { _root.parentBold = v } }
                            RowLayout {
                                Label { text: "Action name size"; color: Style.fg; Layout.fillWidth: true }
                                TrackSpin { from: 9; to: 20; source: _root.childFont; onUserSet: (v) => { _root.childFont = v } }
                            }
                            RowLayout {
                                Label { text: "Action target size"; color: Style.fg; Layout.fillWidth: true }
                                TrackSpin { from: 9; to: 20; source: _root.targetFont; onUserSet: (v) => { _root.targetFont = v } }
                            }
                            ColorPick { label: "Text color"; swatch: _root.colorText; target: "text" }
                            ColorPick { label: "Muted text"; swatch: _root.colorMuted; target: "muted" }
                            ColorPick { label: "Action target"; swatch: _root.colorActionTarget; target: "actionTarget" }
                        }
                        FoldSection {
                            title: "Selection"
                            open: _root.openSelection
                            onToggled: (v) => { _root.openSelection = v }
                            ColorPick { label: "Fill of a selected row"; swatch: _root.colorSelected; target: "selected" }
                            ColorPick { label: "Line around a selected row"; swatch: _root.colorSelectBorder; target: "selectBorder" }
                        }
                    }
                }

                RowLayout {
                    spacing: Style.dp(6)
                    Button {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Style.dp(44)
                        text: "Reset\nAppearance"
                        onClicked: _root.resetDisplay()
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
                        onClicked: _root.saveDisplay()
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
        }

    }

    // A hardware writer row's axis mode, scale and Invert, at the right of
    // the row (ControlTree's rowExtras; the Loader gives rowModel).
    Component {
        id: _writerControls
        RowLayout {
            id: _writer
            readonly property var row: parent ? parent.rowModel : null
            readonly property string writerId: row && row.writerId ? row.writerId : ""
            readonly property string axisMode: row && row.axisMode ? row.axisMode : ""
            readonly property bool canInvert: !!row && row.canInvert === true
            readonly property bool wanted: writerId.length > 0 && (axisMode.length > 0 || canInvert)
            spacing: Style.dp(6)
            ComboBox {
                property bool ownsPress: true
                visible: _writer.writerId.length > 0 && _writer.axisMode.length > 0
                enabled: !_root.editorLocked
                Layout.alignment: Qt.AlignVCenter
                model: ["absolute", "relative"]
                currentIndex: _writer.axisMode === "relative" ? 1 : 0
                Layout.preferredWidth: Style.dp(110)
                onActivated: _layout.setAxisMode(_writer.writerId, currentText)
            }
            SpinBox {
                property bool ownsPress: true
                visible: _writer.writerId.length > 0 && _writer.axisMode.length > 0
                enabled: !_root.editorLocked
                Layout.alignment: Qt.AlignVCenter
                from: -500
                to: 500
                stepSize: 10
                value: Math.round((_writer.row ? _writer.row.axisScale : 1) * 100)
                editable: true
                Layout.preferredWidth: Style.dp(90)
                onValueModified: _layout.setAxisScale(_writer.writerId, value / 100.0)
            }
            CheckBox {
                property bool ownsPress: true
                visible: _writer.writerId.length > 0 && _writer.canInvert
                enabled: !_root.editorLocked
                Layout.alignment: Qt.AlignVCenter
                text: "Invert"
                checked: !!_writer.row && _writer.row.inverted === true
                onClicked: _layout.setInverted(_writer.writerId, checked)
            }
        }
    }



    property string _menuKey: ""
    property string _menuTitle: ""
    property string _menuUser: ""
    property string _menuGroup: ""
    property string _pendingGroup: ""
    property string _groupName: ""
    property string _hardwareKey: ""
    property bool _menuOnRow: false
    // Action row under the right-click menu.
    property string _actionParent: ""
    property int _actionSeq: -1
    property string _actionTitle: ""
    property bool _menuOnGroup: false

    function _clearFind() {
        _find.clear()
    }

    // 01 S140: deleting rows asks first (the page's Undo puts them back).
    function _askDeleteRows(keys, title) {
        var n = keys.length
        Confirm.ask(_root, {
            title: n === 1 ? "Delete " + title + "?" : "Delete " + n + " rows?",
            text: (n === 1 ? "Its hardware links and its actions go with it."
                           : "Their hardware links and their actions go with them."),
            undoable: true,
            action: n === 1 ? "Delete Row" : "Delete " + n + " Rows",
            onAccept: function() { _layout.deleteParents(keys) }
        })
    }

    function _askDeleteGroup(name) {
        Confirm.ask(_root, {
            title: "Delete group " + name + "?",
            text: "Its rows stay, in Ungrouped.",
            undoable: true,
            action: "Delete Group",
            onAccept: function() { _layout.removeGroup(name) }
        })
    }

    function _askClearName(key, title, user) {
        Confirm.ask(_root, {
            title: "Clear the name of " + title + "?",
            text: "Your name \u201c" + user + "\u201d goes; the system name stays.",
            undoable: true,
            action: "Clear Name",
            onAccept: function() { _layout.setUserName(key, "") }
        })
    }

    function _applyFind() {
        _layout.setFilter(
            _find.text,
            _find.typeValue,
            _find.isChecked("ungrouped"),
            _find.isChecked("noWriter"),
            _find.isChecked("noAction")
        )
    }

    // Opens the page's menu at a point in item's coordinates.
    function _openLayoutMenu(onRow, onGroup, item, px, py) {
        _menuOnRow = onRow
        _menuOnGroup = onGroup
        _pageMenu.openAt(item, px, py)
    }

    // Same rule as the model: group names ignore capitals and spacing.
    function _sameGroup(first, second) {
        var clean = (text) => String(text || "").split(/\s+/).filter(Boolean).join(" ").toLowerCase()
        return clean(first) === clean(second)
    }

    function _groupAs(name) {
        if (_picked.length === 1 && _menuGroup.length > 0 && !_sameGroup(_menuGroup, name)) {
            _pendingGroup = name
            _moveWarn.confirm(
                "Already in a Group",
                _menuTitle + " is already in " + _menuGroup + ". Move it to " + name + "?",
                "Move"
            )
            return
        }
        _layout.moveSelected(name)
    }

    // Adds n inputs of a kind from the right-click menu.
    function _addCounted(kind, n) {
        if (!editorLocked)
            _layout.addMany(kind, Math.max(1, Math.min(180, n)), "", "")
    }

    function _assignHardware() {
        _hardwareKey = _menuKey
        _hardwareTitle.text = _menuTitle
        _search.text = ""
        _hardware.moduleOpen = ({})
        _loadHardware()
        _hardware.open()
    }

    function _renameRow() {
        _nameDialog.lastAccepted = _menuUser
        _nameDialog.text = _menuUser
        _nameDialog.showOption = true
        _nameDialog.optionText = "Hide system name"
        _nameDialog.optionChecked = _layout.hidesSystem(_menuKey)
        _nameDialog.visible = true
    }

    function _renameGroup() {
        _groupDialog.text = _groupName
        _groupDialog.visible = true
    }

    // The page's right-click menu (Gremlin.Menus): on a row, a group or the
    // empty list. Quick rows first, then sections; Undo and Redo by the
    // title.
    // Tools > History, only this control's saved changes ("parent:button:3").
    function _openHistory() {
        var parts = String(_menuKey).split(":")
        if (parts.length < 3)
            return
        Helpers.createComponent("DialogHistory.qml", {
            filter: JSON.stringify({
                device: "Logical Device",
                inputType: parts[1],
                inputId: parts[2],
                mode: uiState ? uiState.currentMode : "Default"
            })
        })
    }

    function _layoutMenuModel() {
        var locked = editorLocked
        var onRow = _menuOnRow && !locked
        var onGroup = _menuOnGroup && !locked
        var many = _picked.length > 1
        var kind = onRow ? "logical-row" : (onGroup ? "logical-group" : "logical")
        var title = onRow ? (many ? _picked.length + " rows" : _menuTitle)
                          : (onGroup ? _groupName : "Logical Device")
        var header = locked ? [] : [
            { label: "Undo", enabled: _layout.canUndo && !actionOpen, run: function() { _layout.undo() } },
            { label: "Redo", enabled: _layout.canRedo && !actionOpen, run: function() { _layout.redo() } }
        ]
        var quick = []
        if (onRow) {
            quick.push(MenuModel.action("Add Action", function() { _openNewPane(_menuKey, _menuTitle) }))
            quick.push(MenuModel.action("Rename", _renameRow))
            quick.push(MenuModel.action("Assign Hardware", _assignHardware))
            if (!many)
                quick.push(MenuModel.action("History", _openHistory))
        }
        if (onGroup)
            quick.push(MenuModel.action("Rename Group", _renameGroup))
        quick.push(MenuModel.action("Appearance…", function() { displayOpen = true }))

        var moveTo = []
        if (onRow) {
            var groups = _layout.groups || []
            for (var i = 0; i < groups.length; i++) {
                (function(g) {
                    moveTo.push(MenuModel.action("Move to " + g.title, function() {
                        // After the menu has closed; the move rebuilds the list.
                        Qt.callLater(function() { _layout.moveSelected(g.name) })
                    }))
                })(groups[i])
            }
        }
        var add = function(label, what) {
            return MenuModel.number(label, 1, 1, 180, "", function(n) { _addCounted(what, n) }, !locked,
                                    { step: 1, go: "Add", integer: true })
        }
        return MenuModel.menu(kind, title, quick, [
            onRow ? MenuModel.section("row", "Row", [
                MenuModel.action("Clear Name", function() {
                    _askClearName(_menuKey, _menuTitle, _menuUser)
                }, _menuUser.length > 0),
                // Acts on the selection, like Group as and Move to.
                MenuModel.action(many ? "Delete " + _picked.length + " rows" : "Delete", function() {
                    _askDeleteRows(_picked.length > 0 ? _picked.slice() : [_menuKey], _menuTitle)
                }, true, { danger: true })
            ]) : null,
            onRow ? MenuModel.section("group", "Group", [
                MenuModel.entry("Group as", function(name) { _groupAs(name) }, true,
                                { placeholder: "Name, then Enter" })
            ].concat(moveTo)) : null,
            MenuModel.section("add", "Add Inputs", [
                add("Buttons", "button"),
                add("Axes", "axis"),
                add("Hats", "hat")
            ]),
            locked ? null : MenuModel.section("groups", "Groups", [
                MenuModel.entry("New Group", function(name) { _layout.addGroup(name) }, true,
                                { placeholder: "Name, then Enter", keepOpen: true }),
                onGroup ? MenuModel.action("Move Group Up", function() { _layout.moveGroupUp(_groupName) }) : null,
                onGroup ? MenuModel.action("Move Group Down", function() { _layout.moveGroupDown(_groupName) }) : null,
                onGroup ? MenuModel.action("Delete Group", function() { _askDeleteGroup(_groupName) }, true,
                                           { danger: true }) : null
            ]),
            locked ? null : MenuModel.section("order", "Order", [
                MenuModel.action("By System Name", function() { _layout.sortBySystem() }),
                MenuModel.action("By Your Name", function() { _layout.sortByName() }),
                MenuModel.action("Group Names A to Z", function() { _layout.sortGroupNames() })
            ])
        ], header)
    }

    ContextMenu {
        id: _pageMenu
        build: _root._layoutMenuModel
    }

    // An action row's right-click menu.
    ContextMenu {
        id: _actionMenu
        menuWidth: Style.dp(220)
        build: function() {
            return MenuModel.menu("logical-action", _root._actionTitle, [
                MenuModel.action("Open", function() {
                    _root._openPane(_root._actionParent, _root._actionSeq, _root._actionTitle)
                }),
                MenuModel.action("Delete", function() {
                    _root.deleteActionAsked(_root._actionParent, _root._actionSeq, _root._actionTitle)
                }, true, { danger: true })
            ])
        }
    }

    TextInputDialog {
        id: _nameDialog
        visible: false
        width: Style.dp(320)
        clearOnClick: false
        heading: "Your name"
        onAccepted: (value) => {
            _layout.setRowLabel(_root._menuKey, value, optionChecked)
            visible = false
        }
    }
    TextInputDialog {
        id: _groupDialog
        visible: false
        width: Style.dp(320)
        clearOnClick: false
        heading: "Rename group"
        validator: function(value) { return value.trim().length > 0 }
        onAccepted: (value) => {
            _layout.renameGroup(_root._groupName, value.trim())
            visible = false
        }
    }

    Popup {
        id: _hardware
        parent: Overlay.overlay
        modal: true
        width: Style.dp(520)
        height: Style.dp(640)
        anchors.centerIn: parent
        padding: Style.dp(12)
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle { color: Style.bgCard; border.color: Style.line }
        property var devices: []
        property var moduleOpen: ({})
        function deviceOpen(name) {
            if (_search.text.length)
                return true
            return moduleOpen[name] === true
        }
        function toggleDevice(name) {
            var next = Object.assign({}, moduleOpen)
            next[name] = moduleOpen[name] !== true
            moduleOpen = next
        }
        ColumnLayout {
            anchors.fill: parent
            Label { id: _hardwareTitle; color: Style.fg; font.bold: true; font.pixelSize: Style.dp(16) }
            // The page's Find keeps Ctrl+F (one per window).
            SearchBox {
                id: _search
                objectName: "hardwareSearch"
                Layout.fillWidth: true
                placeholder: "Search"
                findShortcut: false
                count: _root._hardwareCount(_hardware.devices)
                onTextChanged: _loadHardware()
            }
            Flickable {
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentHeight: _hwCol.childrenRect.height
                clip: true
                Column {
                    id: _hwCol
                    width: parent.width
                    spacing: Style.dp(8)
                    Repeater {
                        model: _hardware.devices
                        delegate: Column {
                            width: _hwCol.width
                            required property var modelData
                            spacing: Style.dp(2)
                            RowLayout {
                                width: parent.width
                                // A full cell to click, not just the glyph. Dimmed while a
                                // search shows every device open.
                                Label {
                                    Layout.preferredWidth: Style.dp(24)
                                    Layout.preferredHeight: Style.dp(24)
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    text: _hardware.deviceOpen(modelData.name) ? "▾" : "▸"
                                    color: Style.fgMuted
                                    opacity: _search.text.length ? 0.35 : 1
                                    font.pixelSize: Style.dp(14)
                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: _hardware.toggleDevice(modelData.name)
                                    }
                                }
                                CheckBox {
                                    checkState: _deviceState(modelData.controls)
                                    tristate: true
                                    onClicked: {
                                        var on = 0
                                        var controls = modelData.controls
                                        for (var i = 0; i < controls.length; ++i)
                                            if (controls[i].on)
                                                on++
                                        _setDevice(controls, on !== controls.length)
                                    }
                                }
                                Label {
                                    text: modelData.name
                                    color: Style.fg
                                    font.bold: true
                                    Layout.fillWidth: true
                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: _hardware.toggleDevice(modelData.name)
                                    }
                                }
                            }
                            Repeater {
                                model: _hardware.deviceOpen(modelData.name) ? modelData.controls : []
                                delegate: CheckBox {
                                    required property var modelData
                                    text: modelData.label
                                    checked: modelData.on
                                    leftPadding: Style.dp(28)
                                    onClicked: {
                                        _layout.setLinks(_hardwareKey, [modelData.key], checked)
                                        _loadHardware()
                                    }
                                }
                            }
                        }
                    }
                }
            }
            Button { text: "Close"; onClicked: _hardware.close() }
        }
    }

    function _deviceState(controls) {
        var on = 0
        for (var i = 0; i < controls.length; ++i)
            if (controls[i].on)
                on++
        if (on === 0)
            return Qt.Unchecked
        if (on === controls.length)
            return Qt.Checked
        return Qt.PartiallyChecked
    }

    function _setDevice(controls, on) {
        var keys = []
        for (var i = 0; i < controls.length; ++i)
            keys.push(controls[i].key)
        _layout.setLinks(_hardwareKey, keys, on)
        _loadHardware()
    }

    function _hardwareCount(devices) {
        var n = 0
        for (var i = 0; i < (devices || []).length; ++i)
            n += (devices[i].controls || []).length
        return n
    }

    function _loadHardware() {
        _hardware.devices = _layout.hardware(_hardwareKey, _search.text)
    }

    DismissibleDialog {
        id: _moveWarn
        onConfirmed: {
            if (_root._pendingGroup.length)
                _layout.moveSelected(_root._pendingGroup)
            _root._pendingGroup = ""
        }
        onCancelled: _root._pendingGroup = ""
    }

    // 01 S140: deleting an action asks first. It closes the editor open
    // on its input; that editor's unsaved changes are named too.
    function deleteActionAsked(parentKey, seq, title) {
        var editing = actionOpen && paneKey === parentKey
        var dirty = editing && _layout.paneDirty()
        Confirm.ask(_root, {
            title: title ? "Delete action " + title + "?" : "Delete this action?",
            text: dirty
                ? "The action editor is open on this input with changes that are not saved."
                  + " Deleting the action closes it and drops those changes."
                : "It goes from this row in this mode.",
            undoable: true,
            action: "Delete Action",
            onAccept: function() {
                if (editing)
                    _finishClose()
                _layout.deleteAction(parentKey, seq)
            }
        })
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
            onClicked: { _root._colorTarget = target; _colorDlg.selectedColor = swatch; _colorDlg.open() }
            background: Rectangle { color: swatch; border.color: Style.line; border.width: 1; radius: 3 }
            // Dark text on a light swatch, white on a dark one.
            contentItem: Label { text: parent.text; color: swatch.hslLightness > 0.6 ? Style.onLight : Style.onColor; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
        }
        // Back to the colour that follows Dark mode.
        Button {
            readonly property string setName: _root.userColourOf(target)
            visible: setName.length > 0
            enabled: visible && _root[setName].length > 0
            text: "Default"
            onClicked: _root[setName] = ""
        }
    }

    function numVal(v, d) {
        var n = Number(v)
        return (v === undefined || v === null || v === "" || isNaN(n)) ? d : n
    }

    function displayPayload() {
        return {
            "rowSpacing": rowSpacing,
            "groupInside": groupInside,
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
            "colorGrip": colorGripSet
        }
    }

    function applyDisplay(v) {
        if (!v)
            return
        rowSpacing = numVal(v.rowSpacing, 4)
        groupInside = numVal(v.groupInside, 0)
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
    }

    function userColourOf(target) {
        var names = { group: "colorGroupSet", parent: "colorParentSet", child: "colorChildSet", actionTarget: "colorActionTargetSet", text: "colorTextSet", muted: "colorMutedSet", selected: "colorSelectedSet", selectBorder: "colorSelectBorderSet", border: "colorBorderSet", caret: "colorCaretSet", grip: "colorGripSet" }
        return names[target] || ""
    }

    function applyDisplayDefaults() {
        rowSpacing = 4
        groupInside = 0
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
        setAllSections(false)
    }

    function setAllSections(v) {
        openShown = v
        openHandles = v
        openList = v
        openGroup = v
        openParent = v
        openChild = v
        openText = v
        openSelection = v
    }

    function rememberDisplay() {
        savedDisplay = JSON.stringify(displayPayload())
    }

    function displayDirty() {
        return savedDisplay.length > 0 && JSON.stringify(displayPayload()) !== savedDisplay
    }

    function reloadDisplay() {
        var raw = _place.logicalValue("display")
        if (!raw.length) {
            applyDisplayDefaults()
            var h = parseInt(_place.logicalValue("parentHeight"))
            if (!isNaN(h) && h >= 32 && h <= 80)
                parentHeight = h
        } else {
            try {
                applyDisplay(JSON.parse(raw))
            } catch (e) {
                applyDisplayDefaults()
            }
        }
        rememberDisplay()
    }

    function saveDisplay() {
        _place.setLogicalValue("display", JSON.stringify(displayPayload()))
        rememberDisplay()
        toastText = "Saved for this page."
        _savedToast.open()
    }

    function resetDisplay() {
        applyDisplayDefaults()
        toastText = "Options have been reset"
        _savedToast.open()
    }

    function requestCloseDisplay() {
        if (!displayDirty()) {
            displayOpen = false
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
            else colorParentSet = c
        }
    }

    DismissibleDialog {
        id: _displayGate
        onSaveChosen: {
            saveDisplay()
            displayOpen = false
        }
        onDiscardChosen: {
            reloadDisplay()
            displayOpen = false
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
