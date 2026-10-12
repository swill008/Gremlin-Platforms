// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// The Keyboard page in the Logical Device style (05 S128, CF-Q7): Find bar,
// the shared tree of keys and their actions, the shared action pane.
// Rows open the pane; the right-click menu holds Add Action, Rename,
// History, Delete and Add Key.

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Device
import Gremlin.Menus
import Gremlin.Style
import Gremlin.Util
import "helpers.js" as Helpers
import "confirm.js" as Confirm
import "control_menu.js" as ControlMenu
import Gremlin.UI

Item {
    id: _root

    property string mode: "Default"
    property alias paneUnits: _pane.paneUnits
    readonly property int paneWidth: _pane.paneWidth
    readonly property bool actionOpen: _pane.open
    readonly property string paneKey: _pane.paneKey
    readonly property string paneTitle: _pane.paneTitle
    property alias closeAfterOk: _pane.closeAfterOk
    readonly property var layoutModel: _layout
    // Leave / unsaved questions go to the pane (ActionPane.qml, to-do 91).
    property alias actionPane: _pane

    // The page's Appearance part (PageAppearance.qml, to-do 91).
    property alias displayOpen: _appear.displayOpen
    readonly property Component pageBar: _appear.pageBar
    function toggleAppearance() { _appear.toggleAppearance() }
    function requestCloseDisplay() { _appear.requestCloseDisplay() }

    // The one edit lock (06 S13): nothing is edited while the profile runs.
    EditLock { id: _lock }
    readonly property bool editorLocked: _lock.locked

    readonly property bool _undoKeys: visible && !editorLocked && !actionOpen && !_listen.visible
    Shortcut {
        enabled: _root._undoKeys && _layout.canUndo
        sequences: [StandardKey.Undo]
        onActivated: _layout.undo()
    }
    Shortcut {
        enabled: _root._undoKeys && _layout.canRedo
        sequences: [StandardKey.Redo]
        onActivated: _layout.redo()
    }

    function setMode(next) {
        mode = next || "Default"
    }

    function openInput(key, title) { _pane.openAt(key, -1, title) }
    function openAction(key, seq, title) { _pane.openAt(key, seq, title) }
    function addAction(key, title) { _pane.openNew(key, title) }

    // Add Key (S73): listens for one key, adds it to the mode shown and
    // opens it, after any unsaved pane is asked about.
    function addKey() {
        if (editorLocked)
            return
        Helpers.closeActionPanes(function() { _listen.open() })
    }

    function _keyAdded(inputs) {
        var key = _layout.addKey(inputs, mode)
        if (!key.length)
            return
        _tree.select(key, false)
        _pane.openAt(key, -1, _layout.selectionLabel)
    }

    KeyboardLayoutModel { id: _layout }
    Connections {
        target: _layout
        function onPaneLost() { _pane.closeNow() }
        // An input pressed while stopped: show its row (D-05-FOLLOW-ALL-PAGES,
        // 05 S131; the model checks Run, the setting and the holds).
        function onFollowInput(key) {
            if (_root.visible)
                _tree.showKey(key)
        }
    }
    // A row's click opens the pane on all its actions (S126).
    Connections {
        target: _tree
        ignoreUnknownSignals: true
        function onParentClicked(key, title, shift) {
            if (!shift)
                _root.openInput(key, title)
        }
    }
    Connections {
        target: typeof uiState !== "undefined" ? uiState : null
        ignoreUnknownSignals: true
        function onModeChanged() { _root.setMode(uiState.currentMode) }
    }

    Component.onCompleted: {
        if (typeof uiState !== "undefined" && uiState)
            mode = uiState.currentMode
        _layout.setMode(mode)
    }

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
                namePrefix: "keyboard"
                placeholder: "Key name, your name, or group"
                typeChoices: [{ label: "All keys", value: "all" }]
                filters: [
                    { label: "Ungrouped", name: "ungrouped" },
                    { label: "No actions in this mode", name: "noAction" }
                ]
                locked: _root.editorLocked
                paneOpen: _root.actionOpen
                onChanged: _root._applyFind()
                buttons: [
                    Button {
                        objectName: "keyboardAddKey"
                        Layout.alignment: Qt.AlignTop
                        text: "Add Key…"
                        enabled: !_root.editorLocked
                        onClicked: _root.addKey()
                    }
                ]
            }

            ControlTree {
                id: _tree
                objectName: "keyboardTree"
                // A held input's row tints (05 S131,
                // D-05-FOLLOW-ALL-PAGES); the model is the live state.
                liveDecoration: true
                liveState: _layout
                liveBars: false
                liveLeds: _appear.showLeds
                colorLive: _appear.colorLive
                Layout.fillWidth: true
                Layout.fillHeight: true
                layout: _layout
                locked: _root.editorLocked
                namePrefix: "keyboard"
                dragMime: "application/x-gremlin-keyboard"
                dragLayer: _root
                emptyText: "No keys yet. Choose Add Key… or right-click here and press the key to add."
                filtering: _find.filtering
                parentHeight: _appear.parentHeight
                childHeight: _appear.childHeight
                rowSpacing: _appear.rowSpacing
                groupInside: _appear.groupInside
                parentAlign: _appear.parentAlign
                parentWidthPct: _appear.parentWidthPct
                childAlign: _appear.childAlign
                childWidthPct: _appear.childWidthPct
                groupSpacing: _appear.groupSpacing
                listPadShape: _appear.listPadShape
                listPad: _appear.listPad
                listPadTop: _appear.listPadTop
                listPadRight: _appear.listPadRight
                listPadBottom: _appear.listPadBottom
                listPadLeft: _appear.listPadLeft
                groupPadShape: _appear.groupPadShape
                groupPad: _appear.groupPad
                groupPadTop: _appear.groupPadTop
                groupPadRight: _appear.groupPadRight
                groupPadBottom: _appear.groupPadBottom
                groupPadLeft: _appear.groupPadLeft
                groupRadius: _appear.groupRadius
                colorGroup: _appear.colorGroup
                parentPadShape: _appear.parentPadShape
                parentPad: _appear.parentPad
                parentPadTop: _appear.parentPadTop
                parentPadRight: _appear.parentPadRight
                parentPadBottom: _appear.parentPadBottom
                parentPadLeft: _appear.parentPadLeft
                parentRadius: _appear.parentRadius
                colorParent: _appear.colorParent
                parentIndent: _appear.parentIndent
                childIndent: _appear.childIndent
                childPadShape: _appear.childPadShape
                childPad: _appear.childPad
                childPadTop: _appear.childPadTop
                childPadRight: _appear.childPadRight
                childPadBottom: _appear.childPadBottom
                childPadLeft: _appear.childPadLeft
                childRadius: _appear.childRadius
                colorChild: _appear.colorChild
                showChildren: _appear.showChildren
                showSummary: _appear.showSummary
                showActionSummary: _appear.showActionSummary
                summaryFont: _appear.summaryFont
                parentFont: _appear.parentFont
                groupFont: _appear.groupFont
                childFont: _appear.childFont
                targetFont: _appear.targetFont
                colorActionTarget: _appear.colorActionTarget
                parentBold: _appear.parentBold
                colorText: _appear.colorText
                colorMuted: _appear.colorMuted
                colorSelected: _appear.colorSelected
                colorSelectBorder: _appear.colorSelectBorder
                colorBorder: _appear.colorBorder
                caretSize: _appear.caretSize
                colorCaret: _appear.colorCaret
                gripWidth: _appear.gripWidth
                gripHeight: _appear.gripHeight
                gripRadius: _appear.gripRadius
                colorGrip: _appear.colorGrip

                onClearFilters: _find.clear()
                onPageMenu: (item, x, y) => _root._openMenu(false, false, item, x, y)
                onParentMenu: (key, title, userName, groupName, item, x, y) => {
                    _root._menuKey = key
                    _root._menuTitle = title
                    _root._menuUser = userName
                    _root._menuGroup = groupName
                    _root._openMenu(true, false, item, x, y)
                }
                onGroupMenu: (groupName, item, x, y) => {
                    _root._groupName = groupName
                    _root._openMenu(false, true, item, x, y)
                }
                onActionMenu: (parentKey, seq, title, item, x, y) => {
                    _root._actionParent = parentKey
                    _root._actionSeq = seq
                    _root._actionTitle = title
                    _actionMenu.openAt(item, x, y)
                }
                onActionClicked: (parentKey, seq, title) => _root.openAction(parentKey, seq, title)
            }
        }

        ActionPane {
            id: _pane
            layout: _layout
            locked: _root.editorLocked
            tree: _tree
            namePrefix: "keyboard"
        }

        // The list Appearance (05 S125), this page's own (AP2).
        PageAppearance {
            id: _appear
            objectName: "keyboardAppearance"
            pageKey: "keyboard"
            buttonName: "keyboardAppearanceButton"
            title: "Keyboard — Appearance"
        }
    }

    property string _menuKey: ""
    property string _menuTitle: ""
    property string _menuUser: ""
    property string _menuGroup: ""
    property string _groupName: ""
    property string _pendingGroup: ""
    property bool _menuOnRow: false
    property bool _menuOnGroup: false
    property string _actionParent: ""
    property int _actionSeq: -1
    property string _actionTitle: ""

    function _applyFind() {
        _layout.setFilter(_find.text, "all", _find.isChecked("ungrouped"), false,
                          _find.isChecked("noAction"))
    }

    function _openMenu(onRow, onGroup, item, px, py) {
        _menuOnRow = onRow
        _menuOnGroup = onGroup
        _pageMenu.openAt(item, px, py)
    }

    function _sameGroup(first, second) {
        var clean = (text) => String(text || "").split(/\s+/).filter(Boolean).join(" ").toLowerCase()
        return clean(first) === clean(second)
    }

    function _groupAs(name) {
        if (_tree.picked.length === 1 && _menuGroup.length > 0 && !_sameGroup(_menuGroup, name)) {
            _pendingGroup = name
            _moveWarn.confirm("Already in a Group",
                _menuTitle + " is already in " + _menuGroup + ". Move it to " + name + "?", "Move")
            return
        }
        _layout.moveSelected(name)
    }

    // Delete (S75): this mode's actions of the key; Undo puts them back.
    // The pane open on a deleted key closes (S76).
    function _askDelete(keys, title) {
        var n = keys.length
        Confirm.ask(_root, {
            title: n === 1 ? "Delete key " + title + "?" : "Delete " + n + " keys?",
            text: n === 1 ? "Its actions in this mode go with it."
                          : "Their actions in this mode go with them.",
            undoable: true,
            action: n === 1 ? "Delete Key" : "Delete " + n + " Keys",
            onAccept: function() {
                if (actionOpen && keys.indexOf(paneKey) >= 0)
                    _pane.closeNow()
                _layout.deleteParents(keys)
            }
        })
    }

    function _askDeleteGroup(name) {
        Confirm.ask(_root, {
            title: "Delete group " + name + "?",
            text: "Its keys stay, in Ungrouped.",
            undoable: true,
            action: "Delete Group",
            onAccept: function() { _layout.removeGroup(name) }
        })
    }

    // Rename (S129): the key's friendly name in the Keyboard's input module
    // file, the one Module Setup edits; saved with File > Save.
    function _renameRow() {
        _nameDialog.lastAccepted = _menuUser
        _nameDialog.text = _menuUser
        _nameDialog.visible = true
    }

    function _openHistory() {
        Helpers.createComponent("DialogHistory.qml", {
            filter: JSON.stringify({
                device: "Keyboard",
                mode: typeof uiState !== "undefined" && uiState ? uiState.currentMode : "Default"
            })
        })
    }

    function _deletable() {
        var keys = _tree.picked.length > 0 ? _tree.picked.slice() : [_menuKey]
        return keys.filter(function(k) { return _layout.canDelete(k) })
    }

    function _layoutMenuModel() {
        return ControlMenu.standardMenu(_root, {
            layout: _layout, kind: "keyboard", pageTitle: "Keyboard", manyNoun: "keys",
            picked: _tree.picked,
            addAction: function() { addAction(_menuKey, _menuTitle) },
            renameGroup: function() {
                _groupDialog.text = _groupName
                _groupDialog.visible = true
            },
            clearName: function() { _layout.setUserName(_menuKey, "") },
            rowTitle: "Key", sortSystemLabel: "By Key Name",
            rowItems: function(st) {
                // Only where it does something (S75): this mode's actions,
                // or a key with none in any mode.
                var doomed = _deletable()
                return [MenuModel.action(doomed.length > 1 ? "Delete " + doomed.length + " keys" : "Delete",
                                         function() { _askDelete(doomed, _menuTitle) },
                                         doomed.length > 0, { danger: true })]
            },
            extraSections: function(st) {
                return [{ at: "afterGroup", section: MenuModel.section("add", "Add Inputs", [
                    MenuModel.action("Add Key… (press the key)", function() { Qt.callLater(_root.addKey) },
                                     !st.locked)
                ]) }]
            }
        })
    }

    ContextMenu {
        id: _pageMenu
        build: _root._layoutMenuModel
    }

    ContextMenu {
        id: _actionMenu
        menuWidth: Style.dp(220)
        build: function() {
            return ControlMenu.actionMenu({ kind: "keyboard", title: _root._actionTitle,
                open: function() { _root.openAction(_root._actionParent, _root._actionSeq, _root._actionTitle) },
                remove: function() { _root._askDeleteAction(_root._actionParent, _root._actionSeq, _root._actionTitle) } })
        }
    }

    function _askDeleteAction(parentKey, seq, title) {
        var editing = actionOpen && paneKey === parentKey
        var dirty = editing && _layout.paneDirty()
        Confirm.ask(_root, {
            title: title ? "Delete action " + title + "?" : "Delete this action?",
            text: dirty
                ? "The action editor is open on this key with changes that are not saved."
                  + " Deleting the action closes it and drops those changes."
                : "It goes from this key in this mode.",
            undoable: true,
            action: "Delete Action",
            onAccept: function() {
                if (editing)
                    _pane.closeNow()
                _layout.deleteAction(parentKey, seq)
            }
        })
    }

    TextInputDialog {
        id: _nameDialog
        visible: false
        width: Style.dp(320)
        clearOnClick: false
        heading: "Your name"
        onAccepted: (value) => {
            _layout.setUserName(_root._menuKey, value)
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

    DismissibleDialog {
        id: _moveWarn
        onConfirmed: {
            if (_root._pendingGroup.length)
                _layout.moveSelected(_root._pendingGroup)
            _root._pendingGroup = ""
        }
        onCancelled: _root._pendingGroup = ""
    }

    // Add Key: waits for one key press (hold Esc to stop).
    InputListenerModel {
        id: _listener
        eventTypes: ["key"]
        multipleInputs: false
        enabled: false
        onListeningTerminated: function(inputs) {
            _listener.enabled = false
            _listen.close()
            if (inputs && inputs.length)
                _root._keyAdded(inputs)
        }
    }

    Popup {
        id: _listen
        objectName: "keyboardListen"
        parent: Overlay.overlay
        anchors.centerIn: Overlay.overlay
        dim: true
        modal: true
        focus: true
        closePolicy: Popup.NoAutoClose
        onOpened: _listener.enabled = true
        onClosed: _listener.enabled = false
        RowLayout {
            Label { text: "Press the key to add. Hold Esc to stop." }
            Label { text: _listener.currentInput }
        }
    }
}
