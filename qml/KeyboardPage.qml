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
    property bool displayOpen: false
    property bool _ready: false
    readonly property var layoutModel: _layout

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

    signal leaveResolved()
    signal leaveCancelled()

    function setMode(next) {
        mode = next || "Default"
    }

    // Main asks these before a tool changes bindings behind the pane
    // (05 Q8), Run starts (06 Q6) or the page is left.
    function hasUnsaved() { return _pane.hasUnsaved() }
    function paneHasChanges() { return hasUnsaved() }
    function closeActionPane() { closePaneNow() }
    function savePane() { return _pane.save() }
    function closePaneNow() { _pane.closeNow() }

    property bool _leavingPage: false
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
        function onPaneLost() { _root.closePaneNow() }
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
    WindowPlacement { id: _place }

    Component.onCompleted: {
        if (typeof uiState !== "undefined" && uiState)
            mode = uiState.currentMode
        _appear.load()
        displayOpen = _place.displayPanelOpen("keyboard", "page")
        _layout.setMode(mode)
        _ready = true
    }

    onDisplayOpenChanged: {
        if (_ready)
            _place.setDisplayPanelOpen("keyboard", "page", displayOpen)
    }
    onModeChanged: _layout.setMode(mode)

    // The page's own controls on the bar under the toolbar (01 S58a).
    property Component pageBar: Component {
        RowLayout {
            Layout.fillWidth: true
            Item { Layout.fillWidth: true }
            Button {
                objectName: "keyboardAppearanceButton"
                text: _root.displayOpen ? "Hide Appearance" : "Appearance…"
                onClicked: _root.toggleAppearance()
            }
        }
    }

    // Hiding asks about unsaved display options, like the panel's close.
    function toggleAppearance() {
        if (displayOpen)
            _appear.requestClose()
        else
            displayOpen = true
    }

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
            namePrefix: "keyboard"
            onLeaveDone: (resolved) => _root._finishLeave(resolved)
        }

        // The list Appearance (05 S125), this page's own (AP2).
        ListAppearancePanel {
            id: _appear
            objectName: "keyboardAppearance"
            pageKey: "keyboard"
            visible: _root.displayOpen
            title: "Keyboard — Appearance"
            Layout.preferredWidth: Style.dp(360)
            Layout.maximumWidth: Style.dp(360)
            Layout.fillHeight: true
            onClosed: _root.displayOpen = false
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

    function _menuModel() {
        var locked = editorLocked
        var onRow = _menuOnRow && !locked
        var onGroup = _menuOnGroup && !locked
        var many = _tree.picked.length > 1
        var kind = onRow ? "keyboard-row" : (onGroup ? "keyboard-group" : "keyboard")
        var title = onRow ? (many ? _tree.picked.length + " keys" : _menuTitle)
                          : (onGroup ? _groupName : "Keyboard")
        var header = locked ? [] : [
            { label: "Undo", enabled: _layout.canUndo && !actionOpen, run: function() { _layout.undo() } },
            { label: "Redo", enabled: _layout.canRedo && !actionOpen, run: function() { _layout.redo() } }
        ]
        var quick = []
        if (onRow) {
            quick.push(MenuModel.action("Add Action", function() { addAction(_menuKey, _menuTitle) }))
            quick.push(MenuModel.action("Rename", _renameRow))
            if (!many)
                quick.push(MenuModel.action("History", _openHistory))
        }
        if (onGroup)
            quick.push(MenuModel.action("Rename Group", function() {
                _groupDialog.text = _groupName
                _groupDialog.visible = true
            }))
        quick.push(MenuModel.action("Appearance…", function() { displayOpen = true }))

        var moveTo = []
        if (onRow) {
            var groups = _layout.groups || []
            for (var i = 0; i < groups.length; i++) {
                (function(g) {
                    moveTo.push(MenuModel.action("Move to " + g.title, function() {
                        Qt.callLater(function() { _layout.moveSelected(g.name) })
                    }))
                })(groups[i])
            }
        }
        var doomed = onRow ? _deletable() : []
        return MenuModel.menu(kind, title, quick, [
            onRow ? MenuModel.section("row", "Key", [
                MenuModel.action("Clear Name", function() { _layout.setUserName(_menuKey, "") },
                                 _menuUser.length > 0),
                // Only where it does something (S75): this mode's actions,
                // or a key with none in any mode.
                MenuModel.action(doomed.length > 1 ? "Delete " + doomed.length + " keys" : "Delete",
                                 function() { _askDelete(doomed, _menuTitle) },
                                 doomed.length > 0, { danger: true })
            ]) : null,
            onRow ? MenuModel.section("group", "Group", [
                MenuModel.entry("Group as", function(name) { _groupAs(name) }, true,
                                { placeholder: "Name, then Enter" })
            ].concat(moveTo)) : null,
            MenuModel.section("add", "Add Inputs", [
                MenuModel.action("Add Key… (press the key)", function() { Qt.callLater(_root.addKey) },
                                 !locked)
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
                MenuModel.action("By Key Name", function() { _layout.sortBySystem() }),
                MenuModel.action("By Your Name", function() { _layout.sortByName() }),
                MenuModel.action("Group Names A to Z", function() { _layout.sortGroupNames() })
            ])
        ], header)
    }

    ContextMenu {
        id: _pageMenu
        build: _root._menuModel
    }

    ContextMenu {
        id: _actionMenu
        menuWidth: Style.dp(220)
        build: function() {
            return MenuModel.menu("keyboard-action", _root._actionTitle, [
                MenuModel.action("Open", function() {
                    _root.openAction(_root._actionParent, _root._actionSeq, _root._actionTitle)
                }),
                MenuModel.action("Delete", function() {
                    _root._askDeleteAction(_root._actionParent, _root._actionSeq, _root._actionTitle)
                }, true, { danger: true })
            ])
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
