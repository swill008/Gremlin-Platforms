// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Menus
import Gremlin.Style
import "helpers.js" as Helpers
import "confirm.js" as Confirm
import "control_menu.js" as ControlMenu
import Gremlin.UI

// The Device Bindings page of a joystick (05 S121-S131): the Logical Device
// page on the shared base (ControlFindBar, ControlTree, ActionPane) over the
// module's claimed inputs. Rows can't be added or removed here (Module Setup
// owns the claims); groups, order and names are kept in the input module
// file. Live lights/bars and jump-to-pressed decorate the tree (S131).
Item {
    id: _root

    // The device shown (Main sets them; uiState.currentDevice and its title).
    property string guid: ""
    property string deviceName: ""
    property string mode: "Default"

    readonly property alias layout: _layout
    readonly property bool actionOpen: _pane.open
    readonly property string paneKey: _pane.paneKey
    readonly property string paneTitle: _pane.paneTitle
    property alias paneUnits: _pane.paneUnits
    readonly property int paneWidth: _pane.paneWidth
    property alias closeAfterOk: _pane.closeAfterOk
    // The list's open parents, folded groups and selection (ControlTree.qml).
    property alias _opened: _tree.opened
    property alias _picked: _tree.picked

    // The pane and its leave/save functions (ActionPane.qml, to-do 91).
    property alias actionPane: _pane

    // The page's Appearance part (PageAppearance.qml, to-do 91).
    property alias displayOpen: _appear.displayOpen
    readonly property Component pageBar: _appear.pageBar
    function toggleAppearance() { _appear.toggleAppearance() }
    function requestCloseDisplay() { _appear.requestCloseDisplay() }
    readonly property alias appearance: _appear

    property bool _ready: false

    // The one edit lock (06 S13, S82): nothing is edited while the profile runs.
    EditLock { id: _lock }
    readonly property bool editorLocked: _lock.locked

    // Same rules as the Undo and Redo menu items (S36). A focused text field keeps these keys.
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

    // +---------------------------------------------------------------------
    // | Main's hooks (same names as the Logical Device and OSC pages)

    function setMode(next) {
        mode = next || "Default"
    }

    // Another device (S127: switching device clears every Undo step).
    // Both values at once: one rebuild, never the new id with the old name.
    function setDevice(nextGuid, nextName) {
        var was = _ready
        _ready = false
        guid = String(nextGuid || "")
        deviceName = String(nextName || "")
        _ready = was
        if (was)
            _applyDevice()
    }

    // Jump to pressed input (S131): the input with this device index is
    // unfolded, scrolled to and flashed. False when it isn't listed.
    function showIndex(index) {
        if (index === undefined || index < 0)
            return false
        var key = String(_layout.keyForDeviceIndex(index) || "")
        if (!key.length)
            return false
        return !!_tree.showKey(key)
    }

    // Opens the pane on an input (all its actions) or one action.
    function openInput(key, title) { _pane.openAt(key, -1, title) }

    function openAction(key, seq, title) { _pane.openAt(key, seq, title) }

    function addAction(key, title) { _pane.openNew(key, title) }

    // The page menu's "Module Setup…": this device's Module Setup, as its
    // Home card opens it (claims belong there, 03).
    function openModuleSetup() {
        var win = Window.window
        if (win && typeof win.openConfigureModule === "function"
                && typeof win._cardForGuid === "function") {
            var card = win._cardForGuid(guid)
            if (card) {
                win.openConfigureModule("source", card)
                return true
            }
        }
        return false
    }

    // +---------------------------------------------------------------------
    // | Models

    HardwareLayoutModel { id: _layout }
    Connections {
        target: _layout
        // Its mode was deleted, or the device changed (the model closed the draft).
        function onPaneLost() { _pane.closeNow() }
    }

    DeviceLiveState {
        id: _live
        guid: _root.guid
        deviceName: _root.deviceName
        locked: _root.editorLocked
        liveWhileActive: false
    }

    // The device's inputs by index: the program's current input (uiState)
    // follows the selected row, as the highlight of a pressed input needs
    // it to be on this device (backend._highlight_input).
    Device {
        id: _device
        guid: _root.guid
    }

    // The device index of a listed parent key ("parent:button:3"); -1 when
    // not listed.
    function deviceIndexOf(key) {
        if (!key)
            return -1
        for (var i = 0; i < 1024; i++) {
            var found = String(_layout.keyForDeviceIndex(i) || "")
            if (found === key)
                return i
        }
        return -1
    }

    function _noteCurrentInput(key) {
        if (typeof uiState === "undefined" || !uiState)
            return
        var index = deviceIndexOf(key)
        if (index < 0)
            return
        var ident = _device.inputIdentifier(index)
        if (ident)
            uiState.setCurrentInput(ident, index)
    }

    // On load and after a device change: the program's current input on
    // this device is shown, else the first input becomes the current one.
    function _showCurrent() {
        var index = (typeof uiState !== "undefined" && uiState) ? uiState.currentInputIndex : -1
        if (index >= 0 && String(_layout.keyForDeviceIndex(index) || "").length) {
            showIndex(index)
            _noteCurrentInput(String(_layout.keyForDeviceIndex(index)))
            return
        }
        for (var i = 0; i < 1024; i++) {
            var key = String(_layout.keyForDeviceIndex(i) || "")
            if (key.length) {
                _noteCurrentInput(key)
                return
            }
        }
    }

    Connections {
        target: _tree
        function onPickedChanged() {
            if (_tree.picked.length === 1)
                _root._noteCurrentInput(_tree.picked[0])
        }
    }

    function _applyDevice() {
        _layout.setDevice(guid, deviceName)
        _showCurrentLater.restart()
    }

    // _showCurrent on the next pass of the event loop. A Timer, not
    // Qt.callLater: an unloading Loader invalidates the page's context
    // before it deletes the page, and a queued callLater would still run.
    Timer {
        id: _showCurrentLater
        interval: 0
        onTriggered: _root._showCurrent()
    }

    onGuidChanged: if (_ready) _applyDevice()
    onDeviceNameChanged: if (_ready) _applyDevice()
    onModeChanged: if (_ready) _layout.setMode(mode)

    Component.onCompleted: {
        if (uiState)
            mode = uiState.currentMode || mode
        _layout.setMode(mode)
        _applyDevice()
        _ready = true
    }

    Connections {
        target: typeof uiState !== "undefined" ? uiState : null
        ignoreUnknownSignals: true
        function onModeChanged() { _root.setMode(uiState.currentMode) }
    }

    // The backend's highlight of a pressed input (backend._highlight_input).
    Connections {
        target: typeof signal !== "undefined" ? signal : null
        ignoreUnknownSignals: true
        function onSetInputIndex(index) { _root.showIndex(index) }
    }

    // A parent row's click opens the pane on all its actions (S126).
    Connections {
        target: _tree
        ignoreUnknownSignals: true
        function onParentClicked(key, title, shift) {
            if (!shift)
                _root.openInput(key, title)
        }
    }

    // +---------------------------------------------------------------------
    // | The page

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
                namePrefix: "deviceBindings"
                placeholder: "System name, your name, or group"
                // Inputs by kind; the action Type box comes after Clear.
                typeChoices: [
                    { label: "All inputs", value: "all" },
                    { label: "Buttons", value: "button" },
                    { label: "Axes", value: "axis" },
                    { label: "Hats", value: "hat" }
                ]
                filters: [
                    { label: "Ungrouped", name: "ungrouped" },
                    { label: "No actions in this mode", name: "noAction" }
                ]
                locked: _root.editorLocked
                paneOpen: _root.actionOpen
                onChanged: _root._applyFind()
                onCleared: _root._resetActionFilters()
                // The action Type and Output boxes (S124).
                buttons: [
                    ComboBox {
                        id: _actionType
                        objectName: "deviceBindingsActionType"
                        Layout.alignment: Qt.AlignTop
                        Layout.preferredWidth: Style.dp(140)
                        model: _layout.typeFilterNames
                        onActivated: _root._applyActionFilters()
                        PointerTip { text: "Show only actions of this type"; show: true }
                    },
                    ComboBox {
                        id: _output
                        objectName: "deviceBindingsOutputFilter"
                        Layout.alignment: Qt.AlignTop
                        Layout.preferredWidth: Style.dp(140)
                        model: _layout.destChoices
                        onActivated: _root._applyActionFilters()
                        PointerTip { text: "Show only actions sending to this output"; show: true }
                    }
                ]
            }

            ControlTree {
                id: _tree
                Layout.fillWidth: true
                Layout.fillHeight: true
                layout: _layout
                locked: _root.editorLocked
                namePrefix: "deviceBindings"
                dragMime: "application/x-gremlin-device-bindings"
                dragLayer: _root
                emptyText: "No inputs are claimed for this device. Right-click here and choose Module Setup… to claim its controls."
                filtering: _find.filtering || _root._actionFiltering
                liveDecoration: true
                liveState: _live
                liveBars: _appear.showLiveBars
                liveLeds: _appear.showLeds
                colorLive: _appear.colorLive
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
                onActionClicked: (parentKey, seq, title) => _root.openAction(parentKey, seq, title)
            }
        }

        ActionPane {
            id: _pane
            layout: _layout
            locked: _root.editorLocked
            tree: _tree
            namePrefix: "deviceBindings"
        }

        // This page's own list Appearance (05 S125, AP2).
        PageAppearance {
            id: _appear
            objectName: "deviceBindingsAppearance"
            pageKey: "device-bindings"
            buttonName: "deviceBindingsAppearanceButton"
            title: "Device Bindings — Appearance"
            liveOptions: true
        }
    }

    // +---------------------------------------------------------------------
    // | Find

    readonly property bool _actionFiltering: _actionType.currentIndex > 0 || _output.currentIndex > 0

    function _applyFind() {
        _layout.setFilter(
            _find.text,
            _find.typeValue,
            _find.isChecked("ungrouped"),
            false,
            _find.isChecked("noAction")
        )
    }

    function _applyActionFilters() {
        var keys = _layout.typeFilterKeys || []
        var typeKey = keys[_actionType.currentIndex] || "all"
        var dest = _output.currentIndex > 0 ? _output.currentText : "All devices"
        _layout.setActionFilters(typeKey, dest)
    }

    // Clear and Clear Filters reset every Find filter (S124); the bar's
    // cleared() brings its Clear here too.
    function _clearFind() {
        _find.clear()
    }

    function _resetActionFilters() {
        _actionType.currentIndex = 0
        _output.currentIndex = 0
        _applyActionFilters()
    }

    // +---------------------------------------------------------------------
    // | Right-click menus

    property string _menuKey: ""
    property string _menuTitle: ""
    property string _menuUser: ""
    property string _menuGroup: ""
    property string _pendingGroup: ""
    property string _groupName: ""
    property bool _menuOnRow: false
    property bool _menuOnGroup: false
    // Action row under the right-click menu.
    property string _actionParent: ""
    property int _actionSeq: -1
    property string _actionTitle: ""

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

    // Rename writes the module's friendly name (S129).
    function _renameRow() {
        _nameDialog.lastAccepted = _menuUser
        _nameDialog.text = _menuUser
        _nameDialog.visible = true
    }

    function _renameGroup() {
        _groupDialog.text = _groupName
        _groupDialog.visible = true
    }

    // Tools > History, only this input in this mode and this profile (08 Q16).
    function historyFilter(key) {
        var parts = String(key).split(":")
        if (parts.length < 3)
            return ""
        var w = {
            deviceId: guid,
            inputType: parts[1],
            inputId: parts[2],
            mode: mode
        }
        var path = (typeof backend !== "undefined" && backend) ? backend.profilePath() : ""
        if (path.length)
            w.profile = path
        return JSON.stringify(w)
    }

    function _openHistory() {
        var filter = historyFilter(_menuKey)
        if (!filter.length)
            return
        Helpers.createComponent("DialogHistory.qml", {
            filter: filter,
            // After the filter: a new filter clears the label.
            filterLabel: deviceName
        })
    }

    // Delete actions… asks first (01 S140); Undo puts them back.
    function _askDeleteActions(key, title) {
        Confirm.ask(_root, {
            title: "Delete the actions of " + title + "?",
            text: "Every action of this input in this mode goes. The input stays.",
            undoable: true,
            action: "Delete Actions",
            onAccept: function() { _layout.deleteActions(key) }
        })
    }

    function _askDeleteGroup(name) {
        Confirm.ask(_root, {
            title: "Delete group " + name + "?",
            text: "Its inputs stay, in Ungrouped.",
            undoable: true,
            action: "Delete Group",
            onAccept: function() { _layout.removeGroup(name) }
        })
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
                : "It goes from this input in this mode.",
            undoable: true,
            action: "Delete Action",
            onAccept: function() {
                if (editing)
                    _pane.finishClose()
                _layout.deleteAction(parentKey, seq)
            }
        })
    }

    // Clear Name (PB2, like the Logical Device page): the module's friendly
    // name goes (S129); Undo puts it back.
    function _askClearName(key, title, user) {
        Confirm.ask(_root, {
            title: "Clear the name of " + title + "?",
            text: "Your name \u201c" + user + "\u201d goes; the system name stays.",
            undoable: true,
            action: "Clear Name",
            onAccept: function() { _layout.setUserName(key, "") }
        })
    }

    // The page's right-click menu (control_menu.js): on a row, a group or the
    // empty list. No Add Inputs: claims come from Module Setup.
    function _layoutMenuModel() {
        return ControlMenu.standardMenu(_root, {
            layout: _layout, kind: "device-bindings",
            pageTitle: deviceName.length ? deviceName : "Device Bindings", manyNoun: "inputs",
            addAction: function() { addAction(_menuKey, _menuTitle) },
            quickEnd: function(st) { return [MenuModel.action("Module Setup…", function() { openModuleSetup() })] },
            // S31: not for the input open in the pane (OK would bring it back).
            rowItems: function(st) {
                return [!st.many && _layout.canDelete(_menuKey)
                    ? MenuModel.action("Delete actions…", function() { _askDeleteActions(_menuKey, _menuTitle) },
                                       true, { danger: true })
                    : null]
            }
        })
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
            return ControlMenu.actionMenu({ kind: "device-bindings", title: _root._actionTitle,
                open: function() { _root.openAction(_root._actionParent, _root._actionSeq, _root._actionTitle) },
                remove: function() { _root.deleteActionAsked(_root._actionParent, _root._actionSeq, _root._actionTitle) } })
        }
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
}
