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
import Gremlin.UI

Item {
    id: _root

    property string mode: "Default"
    // Action pane width at 100%. It is saved in these units.
    property int paneUnits: 560
    readonly property int paneWidth: Style.dp(paneUnits)
    property bool actionOpen: false
    property string paneKey: ""
    property string paneTitle: ""
    property bool closeAfterOk: false
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
    property var _opened: ({})
    property var _collapsed: ({})
    property var _picked: ([])

    readonly property bool editorLocked: backend && backend.gremlinActive

    // Same rules as the Undo and Redo menu items. A focused text field keeps these keys.
    readonly property bool _undoKeys: visible && !editorLocked && !actionOpen
    Shortcut {
        enabled: _root._undoKeys && _layout.canUndo
        sequences: [StandardKey.Undo]
        onActivated: _layout.undo()
    }
    // On Windows StandardKey.Redo is Ctrl+Y; Ctrl+Shift+Z is added so both work.
    Shortcut {
        enabled: _root._undoKeys && _layout.canRedo
        sequences: [StandardKey.Redo, "Ctrl+Shift+Z"]
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

    function hasUnsaved() { return actionOpen && _layout.paneDirty() }

    function requestLeave() {
        if (!hasUnsaved()) {
            leaveResolved()
            return
        }
        _leavingPage = true
        _leave.ask("The action editor has changes that are not saved.")
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

    function _saveDock() {
        if (!_ready)
            return
        _place.setActionPaneWidth(paneUnits)
        _place.setClosePaneAfterOk(closeAfterOk)
    }

    function _saveDisplayOpen() {
        if (!_ready)
            return
        _place.setDisplayPanelOpen("logical", "page", displayOpen)
    }

    function _toggleOpen(key) {
        var next = Object.assign({}, _opened)
        next[key] = !next[key]
        _opened = next
    }

    function _toggleGroup(key) {
        var next = Object.assign({}, _collapsed)
        next[key] = !next[key]
        _collapsed = next
    }

    function _hasList(kind, childCount, extraWriters) {
        if (kind === "group")
            return childCount > 0
        if (kind !== "parent" || !showChildren)
            return false
        if (childCount > 0)
            return true
        return showSummary && extraWriters > 0
    }

    function _rowVisible(kind, groupKey, parentKey) {
        if (kind !== "group" && _collapsed[groupKey])
            return false
        if (kind === "writer" && !showSummary)
            return false
        if (kind === "writer" || kind === "child")
            return showChildren && !!_opened[parentKey]
        return true
    }

    function _select(key, shift) {
        var next = _picked.slice()
        if (!shift) {
            next = [key]
        } else {
            var at = next.indexOf(key)
            if (at < 0)
                next.push(key)
            else
                next.splice(at, 1)
        }
        _picked = next
        _layout.setSelection(next)
    }

    function _openPane(key, seq, title) {
        if (editorLocked)
            return
        _layout.beginPane(key, seq)
        paneKey = key
        paneTitle = title
        actionOpen = true
    }

    function _openNewPane(key, title) {
        if (editorLocked)
            return
        _layout.beginNewAction(key)
        paneKey = key
        paneTitle = title
        actionOpen = true
    }

    function _closePane() {
        if (_layout.paneDirty()) {
            _leave.ask("The action editor has changes that are not saved.")
            return
        }
        _finishClose()
    }

    // After a profile change the pane belongs to a profile that is gone.
    function closePaneNow() {
        if (actionOpen)
            _finishClose()
    }

    function _finishClose() {
        _layout.endPane()
        actionOpen = false
        paneKey = ""
    }

    LogicalLayoutModel { id: _layout }
    WindowPlacement { id: _place }

    Component.onCompleted: {
        paneUnits = _place.actionPaneWidth()
        closeAfterOk = _place.closePaneAfterOk()
        reloadDisplay()
        displayOpen = _place.displayPanelOpen("logical", "page")
        _layout.setMode(mode)
        _ready = true
    }

    // The pane width is saved when the grip is let go, not per pixel.
    onCloseAfterOkChanged: _saveDock()
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

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: Style.dp(8)
                Layout.rightMargin: Style.dp(8)
                Layout.topMargin: Style.dp(8)
                spacing: Style.dp(8)
                Label { text: "Find"; color: Style.fgMuted }
                TextField {
                    id: _findText
                    Layout.fillWidth: true
                    Layout.minimumWidth: Style.dp(160)
                    placeholderText: "System name, your name, or group"
                    color: Style.fg
                    onTextChanged: _root._applyFind()
                }
                ComboBox {
                    id: _findType
                    model: ["All types", "Buttons", "Axes", "Hats"]
                    onActivated: _root._applyFind()
                }
                Button {
                    text: "Clear"
                    onClicked: {
                        _findText.text = ""
                        _findType.currentIndex = 0
                        _findUngrouped.checked = false
                        _findNoWriter.checked = false
                        _findNoAction.checked = false
                        _root._applyFind()
                    }
                }
                Button {
                    text: _root.displayOpen ? "Hide Appearance" : "Appearance…"
                    // Hiding asks about unsaved display options, like the panel's close.
                    onClicked: {
                        if (_root.displayOpen)
                            _root.requestCloseDisplay()
                        else
                            _root.displayOpen = true
                    }
                }
                Label {
                    // Why nothing here can be changed, and how to change it.
                    text: _root.editorLocked ? "Profile running: stop it to edit" : ""
                    color: Style.fgMuted
                }
            }
            // The filters, on a line of their own: they wrap when the page is
            // narrow instead of running under the Appearance panel.
            Flow {
                Layout.fillWidth: true
                Layout.leftMargin: Style.dp(8)
                Layout.rightMargin: Style.dp(8)
                spacing: Style.dp(8)
                CheckBox { id: _findUngrouped; text: "Ungrouped"; onClicked: _root._applyFind() }
                CheckBox { id: _findNoWriter; text: "No hardware writer"; onClicked: _root._applyFind() }
                CheckBox { id: _findNoAction; text: "No actions in this mode"; onClicked: _root._applyFind() }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0

                ListView {
                    id: _list
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.leftMargin: _root.padPx(_root.listPadShape, _root.listPad, _root.listPadLeft)
                    Layout.rightMargin: _root.padPx(_root.listPadShape, _root.listPad, _root.listPadRight)
                    Layout.topMargin: _root.padPx(_root.listPadShape, _root.listPad, _root.listPadTop)
                    Layout.bottomMargin: _root.padPx(_root.listPadShape, _root.listPad, _root.listPadBottom)
                    clip: true
                    spacing: 0
                    model: _layout
                    boundsBehavior: Flickable.StopAtBounds
                    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn }

                    MouseArea {
                        z: -1
                        anchors.fill: parent
                        acceptedButtons: Qt.RightButton
                        onClicked: (mouse) => _root._openLayoutMenu(false, false, _list, mouse.x, mouse.y)
                    }

                    // Nothing listed: say why, and how to start.
                    Label {
                        anchors.centerIn: parent
                        width: Math.min(parent.width - Style.dp(32), Style.dp(360))
                        visible: _list.count === 0
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                        color: Style.fgMuted
                        text: _findText.text.length || _findType.currentIndex > 0
                              || _findUngrouped.checked || _findNoWriter.checked
                            ? "Nothing matches the Find filters."
                            : "No buttons, axes or hats yet. Right-click here to add some."
                    }

                    delegate: Rectangle {
                        id: _row
                        required property int index
                        required property string rowKind
                        required property string key
                        required property string title
                        required property string subtitle
                        required property string parentKey
                        required property string groupKey
                        required property string groupName
                        required property string systemName
                        required property string userName
                        required property string writerId
                        required property string axisMode
                        required property double axisScale
                        required property bool inverted
                        required property int sequenceIndex
                        required property int indent
                        required property bool canInvert
                        required property int childCount
                        required property int extraWriters

                        readonly property bool shown: _root._rowVisible(rowKind, groupKey, parentKey)
                        width: _list.width - Style.dp(16)
                        readonly property int rowGap: rowKind === "group" ? 0 : Style.dp(_root.groupInside)
                        readonly property int rowMin: Style.dp(rowKind === "group" ? 40 : (rowKind === "parent" ? _root.parentHeight : _root.childHeight))
                        readonly property int rowPadY: _root.rowTop(rowKind) + _root.rowBottom(rowKind)
                        readonly property int rowNeed: _line.implicitHeight + rowPadY
                        readonly property int rowBody: Math.max(rowMin, rowNeed)
                        height: shown ? implicitHeight : 0
                        visible: shown
                        clip: true
                        implicitHeight: shown ? (rowBody + rowGap + Style.dp(_root.rowSpacing)) : 0
                        color: "transparent"
                        border.width: 0

                        Rectangle {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.leftMargin: _root.rowIndent(rowKind)
                            height: _row.rowBody
                            color: _root._picked.indexOf(key) >= 0 ? _root.colorSelected : (rowKind === "group" ? _root.colorGroup : (rowKind === "parent" ? _root.colorParent : _root.colorChild))
                            border.color: _root._picked.indexOf(key) >= 0 ? _root.colorSelectBorder : _root.colorBorder
                            border.width: Style.dp(1)
                            radius: Style.dp(rowKind === "group" ? _root.groupRadius : (rowKind === "parent" ? _root.parentRadius : _root.childRadius))
                        }

                        RowLayout {
                            id: _line
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.leftMargin: _root.rowIndent(rowKind) + _root.rowLeft(rowKind)
                            anchors.rightMargin: _root.rowRight(rowKind)
                            anchors.topMargin: _root.rowTop(rowKind)
                            height: Math.max(implicitHeight, _row.rowMin - _row.rowPadY)
                            spacing: Style.dp(6)

                            Label {
                                id: _caret
                                visible: _root._hasList(rowKind, childCount, extraWriters)
                                text: (rowKind === "group" ? _root._collapsed[groupKey] : !_root._opened[key]) ? "▸" : "▾"
                                color: _root.colorCaret
                                font.pixelSize: Style.dp(_root.caretSize)
                                Layout.alignment: Qt.AlignVCenter
                                Layout.preferredWidth: visible ? implicitWidth : 0
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: {
                                        if (rowKind === "group")
                                            _root._toggleGroup(groupKey)
                                        else
                                            _root._toggleOpen(key)
                                    }
                                }
                            }
                            Rectangle {
                                visible: rowKind === "parent" || rowKind === "group"
                                implicitWidth: visible ? Style.dp(_root.gripWidth) : 0
                                implicitHeight: visible ? Style.dp(_root.gripHeight) : 0
                                Layout.preferredWidth: visible ? Style.dp(_root.gripWidth) : 0
                                Layout.preferredHeight: visible ? Style.dp(_root.gripHeight) : 0
                                Layout.alignment: Qt.AlignVCenter
                                radius: Style.dp(_root.gripRadius)
                                color: _root.colorGrip
                                MouseArea {
                                    id: _grip
                                    anchors.fill: parent
                                    anchors.margins: -Style.dp(6)
                                    enabled: !_root.editorLocked
                                    cursorShape: rowKind === "parent" ? Qt.OpenHandCursor : Qt.SizeAllCursor
                                    preventStealing: true
                                    onPressed: (mouse) => {
                                        if (rowKind !== "parent") {
                                            _root._dragFrom = key
                                            return
                                        }
                                        // The ghost is held where the row was pressed.
                                        var inRow = mapToItem(_row, mouse.x, mouse.y)
                                        _payload.Drag.hotSpot.x = inRow.x
                                        _payload.Drag.hotSpot.y = inRow.y
                                        _payload.pressAt = mapToItem(_root, mouse.x, mouse.y)
                                        _row.grabToImage(function(result) {
                                            _payload.ghost = result.url
                                        }, Qt.size(_row.width, _row.height))
                                    }
                                    // In-app drag: it starts while the button is held, never
                                    // after release, so it cannot swallow the next click.
                                    onPositionChanged: (mouse) => {
                                        if (rowKind !== "parent")
                                            return
                                        var pos = mapToItem(_root, mouse.x, mouse.y)
                                        if (!_payload.Drag.active
                                                && Math.abs(pos.x - _payload.pressAt.x) + Math.abs(pos.y - _payload.pressAt.y) < Style.dp(4))
                                            return
                                        _payload.x = pos.x - _payload.Drag.hotSpot.x
                                        _payload.y = pos.y - _payload.Drag.hotSpot.y
                                        _payload.Drag.active = true
                                    }
                                    onReleased: (mouse) => {
                                        if (rowKind === "parent") {
                                            if (_payload.Drag.active)
                                                _payload.Drag.drop()
                                            return
                                        }
                                        var pos = mapToItem(_list.contentItem, mouse.x, mouse.y)
                                        var hit = _list.indexAt(pos.x, pos.y)
                                        var from = _root._dragFrom
                                        _root._dragFrom = ""
                                        if (hit >= 0)
                                            _root.moveLater("row", from, _layout.keyAt(hit), "")
                                    }
                                    onCanceled: {
                                        if (_payload.Drag.active)
                                            _payload.Drag.cancel()
                                        _root._dragFrom = ""
                                    }
                                }
                            }
                            Item {
                                visible: rowKind === "parent"
                                Layout.preferredWidth: visible ? Style.dp(16) : 0
                                Layout.preferredHeight: Style.dp(16)
                                Layout.alignment: Qt.AlignVCenter

                                Rectangle {
                                    visible: key.indexOf(":button:") >= 0
                                    anchors.centerIn: parent
                                    width: Style.dp(14)
                                    height: Style.dp(14)
                                    radius: Style.dp(7)
                                    color: "transparent"
                                    border.color: _root.colorText
                                    border.width: Style.dp(2)
                                    Rectangle {
                                        anchors.centerIn: parent
                                        width: Style.dp(6)
                                        height: Style.dp(6)
                                        radius: Style.dp(3)
                                        color: _root.colorText
                                    }
                                }
                                Item {
                                    visible: key.indexOf(":axis:") >= 0
                                    anchors.fill: parent
                                    Rectangle {
                                        anchors.centerIn: parent
                                        width: Style.dp(2)
                                        height: Style.dp(14)
                                        color: _root.colorText
                                    }
                                    Rectangle {
                                        anchors.centerIn: parent
                                        width: Style.dp(8)
                                        height: Style.dp(6)
                                        radius: Style.dp(2)
                                        color: _root.colorText
                                    }
                                }
                                Item {
                                    visible: key.indexOf(":hat:") >= 0
                                    anchors.fill: parent
                                    Rectangle { width: Style.dp(4); height: Style.dp(4); radius: Style.dp(1); color: _root.colorText; anchors.horizontalCenter: parent.horizontalCenter; anchors.top: parent.top }
                                    Rectangle { width: Style.dp(4); height: Style.dp(4); radius: Style.dp(1); color: _root.colorText; anchors.horizontalCenter: parent.horizontalCenter; anchors.bottom: parent.bottom }
                                    Rectangle { width: Style.dp(4); height: Style.dp(4); radius: Style.dp(1); color: _root.colorText; anchors.verticalCenter: parent.verticalCenter; anchors.left: parent.left }
                                    Rectangle { width: Style.dp(4); height: Style.dp(4); radius: Style.dp(1); color: _root.colorText; anchors.verticalCenter: parent.verticalCenter; anchors.right: parent.right }
                                }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                Layout.alignment: Qt.AlignVCenter
                                spacing: Style.dp(2)
                                Label {
                                    text: title
                                    color: _root.colorText
                                    font.bold: rowKind === "child" ? false : _root.parentBold
                                    font.pixelSize: Style.dp(rowKind === "group" ? _root.groupFont : (rowKind === "parent" ? _root.parentFont : _root.childFont))
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                    HoverHandler { id: _nameHover }
                                    ToolTip {
                                        visible: _nameHover.hovered && rowKind === "parent" && userName.length > 0
                                        delay: 400
                                        text: systemName
                                        x: _nameHover.point.position.x - width / 2
                                        y: _nameHover.point.position.y - height - Style.dp(8)
                                    }
                                }
                                Label {
                                    visible: _root.showSummary && subtitle.length > 0 && rowKind !== "writer"
                                    text: subtitle
                                    color: rowKind === "child" ? _root.colorActionTarget : _root.colorMuted
                                    font.pixelSize: Style.dp(rowKind === "child" ? _root.targetFont : _root.summaryFont)
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                    Layout.bottomMargin: visible ? Style.dp(4) : 0
                                }
                            }
                            ComboBox {
                                property bool ownsPress: true
                                visible: writerId.length > 0 && axisMode.length > 0
                                enabled: !_root.editorLocked
                                Layout.alignment: Qt.AlignVCenter
                                model: ["absolute", "relative"]
                                currentIndex: axisMode === "relative" ? 1 : 0
                                Layout.preferredWidth: Style.dp(110)
                                onActivated: _layout.setAxisMode(writerId, currentText)
                            }
                            SpinBox {
                                property bool ownsPress: true
                                visible: writerId.length > 0 && axisMode.length > 0
                                enabled: !_root.editorLocked
                                Layout.alignment: Qt.AlignVCenter
                                from: -500
                                to: 500
                                stepSize: 10
                                value: Math.round(axisScale * 100)
                                editable: true
                                Layout.preferredWidth: Style.dp(90)
                                onValueModified: _layout.setAxisScale(writerId, value / 100.0)
                            }
                            CheckBox {
                                property bool ownsPress: true
                                visible: writerId.length > 0 && canInvert
                                enabled: !_root.editorLocked
                                Layout.alignment: Qt.AlignVCenter
                                text: "Invert"
                                checked: inverted
                                onClicked: _layout.setInverted(writerId, checked)
                            }
                        }

                        DropArea {
                            id: _drop
                            anchors.fill: parent
                            anchors.bottomMargin: _row.rowGap
                            z: 4
                            enabled: !_root.editorLocked && (rowKind === "parent" || rowKind === "group")
                            keys: ["application/x-gremlin-logical"]
                            property bool placeBefore: true
                            onPositionChanged: (drag) => {
                                var source = drag.source && drag.source.dragKey ? drag.source.dragKey : ""
                                if (!source || source === key || source.indexOf("parent:") !== 0) {
                                    _insertLine.visible = false
                                    return
                                }
                                if (rowKind === "group") {
                                    placeBefore = false
                                    _insertLine.y = Math.max(0, height - 2)
                                } else {
                                    placeBefore = drag.y < height / 2
                                    _insertLine.y = placeBefore ? 0 : Math.max(0, height - 2)
                                }
                                _insertLine.visible = true
                            }
                            onExited: _insertLine.visible = false
                            onDropped: (drop) => {
                                _insertLine.visible = false
                                var source = drop.source && drop.source.dragKey ? drop.source.dragKey : ""
                                if (!source || source === key)
                                    return
                                drop.accept(Qt.MoveAction)
                                _root.moveLater("parent", source, key,
                                                rowKind === "group" ? "into" : (placeBefore ? "before" : "after"))
                            }
                            Rectangle {
                                id: _insertLine
                                visible: false
                                z: 6
                                anchors.left: parent.left
                                anchors.right: parent.right
                                height: Style.dp(2)
                                color: Style.info
                            }
                        }

                        Item {
                            id: _payload
                            // On the page, not the row, so the list never clips it.
                            parent: _root
                            z: 100
                            width: Style.dp(1)
                            height: Style.dp(1)
                            property string dragKey: key
                            property url ghost
                            property point pressAt
                            Drag.dragType: Drag.Internal
                            Drag.keys: ["application/x-gremlin-logical"]
                            Drag.supportedActions: Qt.MoveAction
                            Drag.proposedAction: Qt.MoveAction
                            Image {
                                visible: _payload.Drag.active
                                source: _payload.ghost
                                width: _row.width
                                height: _row.height
                                opacity: 0.85
                            }
                        }

                        MouseArea {
                            z: 1
                            anchors.fill: parent
                            anchors.bottomMargin: _row.rowGap
                            acceptedButtons: Qt.LeftButton | Qt.RightButton
                            propagateComposedEvents: true
                            onPressed: (mouse) => {
                                // Leave presses on the caret, the grip and the axis controls to them.
                                if (mouse.button !== Qt.LeftButton)
                                    return
                                var at = mapToItem(_line, mouse.x, mouse.y)
                                var hit = _line.childAt(at.x, at.y)
                                if (hit && (hit === _caret || hit === _grip.parent || hit.ownsPress))
                                    mouse.accepted = false
                            }
                            onClicked: (mouse) => {
                                if (mouse.button === Qt.RightButton) {
                                    if (rowKind === "parent") {
                                        _root._menuKey = key
                                        _root._menuTitle = title
                                        _root._menuUser = userName
                                        _root._menuGroup = groupName
                                        if (_root._picked.indexOf(key) < 0)
                                            _root._select(key, false)
                                        _root._openLayoutMenu(true, false, _row, mouse.x, mouse.y)
                                    } else if (rowKind === "group" && groupName.length > 0) {
                                        _root._groupName = groupName
                                        _root._openLayoutMenu(false, true, _row, mouse.x, mouse.y)
                                    } else if (rowKind === "child" && !_root.editorLocked) {
                                        _root._actionParent = parentKey
                                        _root._actionSeq = sequenceIndex
                                        _root._actionTitle = title
                                        _actionMenu.openAt(_row, mouse.x, mouse.y)
                                    } else {
                                        _root._openLayoutMenu(false, false, _row, mouse.x, mouse.y)
                                    }
                                    return
                                }
                                if (rowKind === "parent")
                                    _root._select(key, mouse.modifiers & Qt.ShiftModifier)
                                else if (rowKind === "child")
                                    _root._openPane(parentKey, sequenceIndex, title)
                                else if (rowKind === "group")
                                    _root._toggleGroup(groupKey)
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            visible: _root.actionOpen
            Layout.preferredWidth: Style.dp(6)
            Layout.fillHeight: true
            color: _actGrip.containsMouse ? Style.info : Style.line
            MouseArea {
                id: _actGrip
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.SplitHCursor
                property int originW: 560
                property real originX: 0
                onPressed: (mouse) => {
                    originW = _root.paneWidth
                    originX = mapToItem(_root, mouse.x, mouse.y).x
                }
                onPositionChanged: (mouse) => {
                    if (!pressed)
                        return
                    var x = mapToItem(_root, mouse.x, mouse.y).x
                    _root.paneUnits = Math.round(Math.max(Style.dp(420), Math.min(Style.dp(1600), originW - (x - originX))) * 100 / Style.uiScale)
                }
                onReleased: _root._saveDock()
            }
        }

        Rectangle {
            visible: _root.actionOpen
            Layout.preferredWidth: _root.paneWidth
            Layout.minimumWidth: visible ? Style.dp(420) : 0
            Layout.fillHeight: true
            color: Style.bgCard
            border.color: Style.line
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Style.dp(10)
                RowLayout {
                    Label {
                        text: _root.paneTitle.length ? _root.paneTitle : "Action Editor"
                        color: Style.fg
                        font.bold: true
                        font.pixelSize: Style.dp(16)
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                    Button { text: "×"; implicitWidth: Style.dp(28); onClicked: _root._closePane() }
                }
                InputConfiguration {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    holdModel: true
                    inputItemModel: _layout.paneModel
                }
                RowLayout {
                    CheckBox {
                        text: "Close pane after OK"
                        checked: _root.closeAfterOk
                        onClicked: _root.closeAfterOk = checked
                    }
                    Item { Layout.fillWidth: true }
                    Button {
                        text: "OK"
                        highlighted: true
                        onClicked: {
                            _layout.commitPane()
                            if (_root.closeAfterOk)
                                _root._finishClose()
                        }
                    }
                }
            }
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


    property string _dragFrom: ""

    // Moves run after the mouse and drop handlers finish: the move rebuilds the
    // rows, and a handler still running in a destroyed row loses its names.
    function moveLater(kind, from, to, where) {
        if (!from || !to)
            return
        var layout = _layout
        Qt.callLater(function() {
            if (kind === "row")
                layout.moveRow(from, to)
            else
                layout.moveParent(from, to, where)
        })
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

    function _applyFind() {
        var types = ["all", "button", "axis", "hat"]
        _layout.setFilter(
            _findText.text,
            types[_findType.currentIndex],
            _findUngrouped.checked,
            _findNoWriter.checked,
            _findNoAction.checked
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
                MenuModel.action("Clear Name", function() { _layout.setUserName(_menuKey, "") }, _menuUser.length > 0),
                // Acts on the selection, like Group as and Move to.
                MenuModel.action(many ? "Delete " + _picked.length + " rows" : "Delete", function() {
                    _layout.deleteParents(_picked.length > 0 ? _picked : [_menuKey])
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
                onGroup ? MenuModel.action("Delete Group", function() { _layout.removeGroup(_groupName) }, true,
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
                    _root.deleteActionAsked(_root._actionParent, _root._actionSeq)
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
            TextField {
                id: _search
                Layout.fillWidth: true
                placeholderText: "Search"
                color: Style.fg
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

    // Deleting an action closes the editor open on its input: when that
    // editor has unsaved changes, ask first.
    function deleteActionAsked(parentKey, seq) {
        var editing = actionOpen && paneKey === parentKey
        function go() {
            if (editing)
                _finishClose()
            _layout.deleteAction(parentKey, seq)
        }
        if (editing && _layout.paneDirty()) {
            _deleteGate.confirmThen("Delete Action?",
                "The action editor is open on this input with changes that are not saved."
                    + " Deleting the action closes it and drops those changes.",
                "Delete", go, null, true)
            return
        }
        go()
    }

    DismissibleDialog {
        id: _deleteGate
    }

    DismissibleDialog {
        id: _leave
        onSaveChosen: {
            _layout.commitPane()
            _finishClose()
            _root._finishLeave(true)
        }
        onDiscardChosen: {
            _layout.discardPane()
            _finishClose()
            _root._finishLeave(true)
        }
        onCancelled: _root._finishLeave(false)
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

    function padEdge(shape, size, side) {
        return shape === "box" ? size : side
    }

    function padPx(shape, size, side) {
        return Style.dp(padEdge(shape, size, side))
    }

    // How far a row's box starts from the list's left edge.
    function rowIndent(kind) {
        if (kind === "group")
            return 0
        if (kind === "parent")
            return Style.dp(parentIndent)
        return Style.dp(parentIndent + childIndent)
    }

    // Text inset inside the row's box. Action text lines up with its parent's text.
    function rowLeft(kind) {
        if (kind === "group")
            return padPx(groupPadShape, groupPad, groupPadLeft)
        var parentLeft = padPx(parentPadShape, parentPad, parentPadLeft)
        if (kind === "parent")
            return parentLeft
        return parentLeft + padPx(childPadShape, childPad, childPadLeft)
    }

    function rowRight(kind) {
        if (kind === "group")
            return padPx(groupPadShape, groupPad, groupPadRight)
        if (kind === "parent")
            return padPx(parentPadShape, parentPad, parentPadRight)
        return padPx(childPadShape, childPad, childPadRight)
    }

    function rowTop(kind) {
        if (kind === "group")
            return padPx(groupPadShape, groupPad, groupPadTop)
        if (kind === "parent")
            return padPx(parentPadShape, parentPad, parentPadTop)
        return padPx(childPadShape, childPad, childPadTop)
    }

    function rowBottom(kind) {
        if (kind === "group")
            return padPx(groupPadShape, groupPad, groupPadBottom)
        if (kind === "parent")
            return padPx(parentPadShape, parentPad, parentPadBottom)
        return padPx(childPadShape, childPad, childPadBottom)
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
        colorGroupSet = userColour(v.colorGroup, "#27272A")
        parentHeight = numVal(v.parentHeight, 44)
        parentPadShape = v.parentPadShape || "sides"
        parentPad = numVal(v.parentPad, 0)
        parentPadTop = numVal(v.parentPadTop, 0)
        parentPadRight = numVal(v.parentPadRight, 8)
        parentPadBottom = numVal(v.parentPadBottom, 0)
        parentPadLeft = numVal(v.parentPadLeft, 24)
        parentRadius = numVal(v.parentRadius, 3)
        colorParentSet = userColour(v.colorParent, "#18181B")
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
        colorChildSet = userColour(v.colorChild, "#18181B")
        showChildren = v.showChildren !== false
        showSummary = v.showSummary !== false
        summaryFont = numVal(v.summaryFont, 11)
        parentFont = numVal(v.parentFont, 13)
        groupFont = numVal(v.groupFont, 15)
        childFont = numVal(v.childFont, 13)
        targetFont = numVal(v.targetFont, 11)
        colorActionTargetSet = userColour(v.colorActionTarget, "#A1A1AA")
        parentBold = v.parentBold !== false
        colorTextSet = userColour(v.colorText, "#E4E4E7")
        colorMutedSet = userColour(v.colorMuted, "#A1A1AA")
        colorSelectedSet = userColour(v.colorSelected, "#1E3A5F")
        colorSelectBorderSet = userColour(v.colorSelectBorder, "#3F3F46")
        colorBorderSet = userColour(v.colorBorder, "#3F3F46")
        caretSize = numVal(v.caretSize, 18)
        colorCaretSet = userColour(v.colorCaret, "#E4E4E7")
        gripWidth = numVal(v.gripWidth, 8)
        gripHeight = numVal(v.gripHeight, 18)
        gripRadius = numVal(v.gripRadius, 2)
        colorGripSet = userColour(v.colorGrip, "#52525B")
    }

    // A saved colour equal to the old fixed (dark) default was never changed by
    // the user, so it follows Dark mode like a colour that was never set.
    function userColour(saved, oldDefault) {
        var text = String(saved || "")
        return text.toLowerCase() === oldDefault.toLowerCase() ? "" : text
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
