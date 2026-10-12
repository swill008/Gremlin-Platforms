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
import "control_menu.js" as ControlMenu
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
    // Leaving the page and Run ask the pane (ActionPane.qml, to-do 91).
    property alias actionPane: _pane
    // The page's Appearance part (PageAppearance.qml, to-do 91).
    property alias displayOpen: _appear.displayOpen
    readonly property Component pageBar: _appear.pageBar
    function toggleAppearance() { _appear.toggleAppearance() }
    function requestCloseDisplay() { _appear.requestCloseDisplay() }
    // The list's open parents, folded groups and selection (ControlTree.qml).
    property alias _opened: _tree.opened
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

    function setMode(next) {
        mode = next || "Default"
        _layout.setMode(mode)
    }

    function _openPane(key, seq, title) { _pane.openAt(key, seq, title) }

    function _openNewPane(key, title) { _pane.openNew(key, title) }

    function _finishClose() { _pane.finishClose() }

    LogicalLayoutModel { id: _layout }
    // Its mode was deleted (the model said so and closed the draft).
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

    Component.onCompleted: _layout.setMode(mode)

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
                placeholder: "System name, custom name, or group"
                filters: [
                    { label: "Ungrouped", name: "ungrouped" },
                    { label: "No hardware writer", name: "noWriter" },
                    { label: "No bindings in this mode", name: "noAction" }
                ]
                locked: _root.editorLocked
                paneOpen: _root.actionOpen
                onChanged: _root._applyFind()
            }

            ControlTree {
                id: _tree
                objectName: "logicalTree"
                // A held input's row tints, an axis shows its bar (05 S131,
                // D-05-FOLLOW-ALL-PAGES); the model is the live state.
                liveDecoration: true
                liveState: _layout
                liveBars: _appear.showLiveBars
                liveLeds: _appear.showLeds
                colorLive: _appear.colorLive
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
                showBindings: _appear.showBindings
                bindingsWordSize: _appear.bindingsWordSize
                bindingsWordColor: _appear.bindingsWordColor
                bindingsNumberSize: _appear.bindingsNumberSize
                bindingsNumberMono: _appear.bindingsNumberMono
                bindingsNumberColor: _appear.bindingsNumberColor
                bindingsBrackets: _appear.bindingsBrackets
                bindingTargetSize: _appear.bindingTargetSize
                bindingTargetMono: _appear.bindingTargetMono
                bindingTargetTextColor: _appear.bindingTargetTextColor
                bindingTargetBgColor: _appear.bindingTargetBgColor
                bindingTargetBorderColor: _appear.bindingTargetBorderColor
                bindingTargetBorderWidth: _appear.bindingTargetBorderWidth
                bindingTargetRounded: _appear.bindingTargetRounded
                bindingTargetRadius: _appear.bindingTargetRadius
                bindingTargetSpacing: _appear.bindingTargetSpacing
                groupControlsByType: _appear.groupControlsByType
                groupBindingsByType: _appear.groupBindingsByType
                groupNoBindings: _appear.groupNoBindings
                groupOutputNotFound: _appear.groupOutputNotFound
                groupOutputDevices: _appear.groupOutputDevices
                groupActionTypes: _appear.groupActionTypes
                groupCustomNames: _appear.groupCustomNames
                groupOtherModes: _appear.groupOtherModes
                groupWrapDetails: _appear.groupWrapDetails
                groupHideEmpty: _appear.groupHideEmpty
                rowActionTypes: _appear.rowActionTypes
                rowOutputNotFound: _appear.rowOutputNotFound
                rowOtherModes: _appear.rowOtherModes
                rowSystemName: _appear.rowSystemName
                rowHasCondition: _appear.rowHasCondition
                rowNoBindings: _appear.rowNoBindings
                rowWrapDetails: _appear.rowWrapDetails
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
                onActionClicked: (parentKey, seq, title) => _root._openPane(parentKey, seq, title)
            }
        }

        ActionPane {
            id: _pane
            layout: _layout
            locked: _root.editorLocked
            namePrefix: "logical"
        }

        // This page's own list Appearance (05 S125, AP2).
        PageAppearance {
            id: _appear
            pageKey: "logical"
            buttonName: "logicalAppearanceButton"
            title: "Logical Device — Appearance"
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
        return ControlMenu.standardMenu(_root, {
            layout: _layout, kind: "logical", pageTitle: "Logical Device", manyNoun: "rows",
            addAction: function() { _openNewPane(_menuKey, _menuTitle) },
            quickBeforeHistory: function(st) { return [MenuModel.action("Assign Hardware", _assignHardware)] },
            rowItems: function(st) {
                // Acts on the selection, like Group as and Move to.
                return [MenuModel.action(st.many ? "Delete " + st.count + " rows" : "Delete", function() {
                    _askDeleteRows(_picked.length > 0 ? _picked.slice() : [_menuKey], _menuTitle)
                }, true, { danger: true })]
            },
            extraSections: function(st) {
                var add = function(label, what) {
                    return MenuModel.number(label, 1, 1, 180, "", function(n) { _addCounted(what, n) }, !st.locked,
                                            { step: 1, go: "Add", integer: true })
                }
                return [{ at: "afterGroup", section: MenuModel.section("add", "Add Inputs",
                          [add("Buttons", "button"), add("Axes", "axis"), add("Hats", "hat")]) }]
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
            return ControlMenu.actionMenu({ kind: "logical", title: _root._actionTitle,
                open: function() { _root._openPane(_root._actionParent, _root._actionSeq, _root._actionTitle) },
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
        // Open devices ({name: true}); null = none. No {} here: a literal
        // is a binding, and opening the list resets it
        // (qt.qml.binding.removal).
        property var moduleOpen: null
        function deviceOpen(name) {
            if (_search.text.length)
                return true
            return (moduleOpen || {})[name] === true
        }
        function toggleDevice(name) {
            var next = Object.assign({}, moduleOpen)
            next[name] = next[name] !== true
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

}
