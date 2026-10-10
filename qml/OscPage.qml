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
import Gremlin.UI

// The OSC page (09 S129-S140): the Logical Device page on the shared base
// (ControlFindBar, ControlTree, ActionPane) with OSC's own pieces: the
// address is the input's identity, the Add window, Import and Listen, OSC
// Setup, and the OSC Monitor docked at the bottom. No footer and no
// Appearance panel. Feedback rows (09 S153-S156) sit under their input,
// after its actions, or in "Feedback not tied to an input"; they open in
// the same pane (OscFeedbackEditor) and stay editable while a profile runs.
Item {
    id: _root

    property string mode: "Default"
    readonly property bool actionOpen: _pane.open
    readonly property string paneKey: _pane.paneKey
    readonly property string paneTitle: _pane.paneTitle
    readonly property alias layout: _layout
    readonly property alias monitorPanel: _monitor
    readonly property alias addWindow: _addDialog
    readonly property alias deviceModel: _devices
    // The list's open parents, folded groups and selection (ControlTree.qml).
    property alias _picked: _tree.picked

    // The one edit lock (06 S13, S82): nothing is edited while the profile runs.
    EditLock { id: _lock }
    readonly property bool editorLocked: _lock.locked

    readonly property bool _undoKeys: visible && !editorLocked && !actionOpen
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
        _layout.setMode(mode)
        _devices.setMode(mode)
    }

    property bool _leavingPage: false

    function hasUnsaved() { return _pane.hasUnsaved() }

    // Main.closeActionPanes() asks these before a tool changes bindings
    // behind the pane (05 Q8) or Run starts (06 Q6).
    function paneHasChanges() { return hasUnsaved() }

    function closeActionPane() { closePaneNow() }

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

    function closePaneNow() { _pane.closeNow() }

    function _openPane(key, seq, title) { _pane.openAt(key, seq, title) }

    function _openNewPane(key, title) { _pane.openNew(key, title) }

    // +---------------------------------------------------------------------
    // | The docked OSC Monitor (09 S137-S139)

    // Shown (the × hides it; Monitor shows it again). Folded by default.
    property bool monitorShown: true
    // Height of the unfolded panel, dragged with the grip.
    property int monitorUnits: 300

    // The Monitor's height is kept between sessions (S137).
    WindowPlacement { id: _monitorPlace }

    function _loadMonitorHeight() {
        var state = {}
        try {
            state = JSON.parse(_monitorPlace.toolRowState("oscPage"))
        } catch (e) {
            state = {}
        }
        if (state && state.monitorUnits > 0)
            monitorUnits = state.monitorUnits
    }

    function _saveMonitorHeight() {
        _monitorPlace.saveToolRowState("oscPage", JSON.stringify({ monitorUnits: monitorUnits }))
    }
    property var _popWin: null

    // Tools > OSC Monitor: the page with the Monitor shown, unfolded.
    function showMonitor() {
        if (_popWin) {
            _popWin.raise()
            _popWin.requestActivate()
            return
        }
        monitorShown = true
        _monitor.folded = false
    }

    function toggleMonitor() {
        if (_popWin) {
            _popWin.raise()
            _popWin.requestActivate()
            return
        }
        if (!monitorShown || _monitor.folded)
            showMonitor()
        else
            _monitor.folded = true
    }

    // Pop out: the same panel in its own window; the dock steps aside
    // while it is open (only one of them holds the port).
    function popOutMonitor() {
        var win = Helpers.createComponent("WindowOscMonitor.qml")
        if (!win)
            return
        _popWin = win
        monitorShown = false
        win.closing.connect(function() {
            if (_root._popWin === win)
                _root._popWin = null
        })
    }

    // +---------------------------------------------------------------------
    // | OSC's own actions

    // The Add window, empty.
    function openAdd() {
        if (editorLocked)
            return false
        _addDialog.resetFields()
        _addDialog.open()
        return true
    }

    // The Add window filled in from a settings map (the OSC Monitor's
    // "Add as Input…", OscMonitorModel.addSettings): adds, never edits.
    function openAddWith(settings) {
        if (editorLocked || !settings || !settings.address)
            return false
        _addDialog.openForEdit("", settings)
        _addDialog.lastParameters = settings.values || ""
        return true
    }

    // Add Inputs > Listen: the Add window, listening straight away.
    function listen() {
        if (!openAdd())
            return false
        _addDialog.startListen()
        return true
    }

    function openImport() {
        if (editorLocked)
            return false
        _importDialog.resetFields()
        _importDialog.open()
        return true
    }

    // Add Inputs > From TouchOSC Layout… (S162): the Import window, choosing
    // a .tosc file straight away.
    function openTouchOsc() {
        if (!openImport())
            return false
        _importDialog.chooseFile()
        return true
    }

    // OSC's Module Setup (D-09-OSC-TABS), as Options' OSC line opens it.
    function openSetup() {
        if (typeof signal !== "undefined" && signal && signal.openOscModuleSetup) {
            signal.openOscModuleSetup()
            return true
        }
        return false
    }

    // Page menu "Feedback settings…": OSC Setup on its Feedback tab.
    function openFeedbackSettings() {
        if (typeof signal !== "undefined" && signal && signal.openOscModuleSetupAt) {
            signal.openOscModuleSetupAt("Feedback")
            return true
        }
        return openSetup()
    }

    // +---------------------------------------------------------------------
    // | Feedback rows (09 S153-S156)

    property string _fbKey: ""
    property string _fbTitle: ""
    property bool _fbEnabled: false
    // A feedback row waiting for the open action editor's unsaved question.
    property var _pendingOpen: null

    function _showFeedbackMessage() {
        var text = String(_layout.feedbackMessage || "")
        if (text.length)
            _message.show(text, false)
    }

    function _openParent(parentKey) {
        var next = Object.assign({}, _tree.opened)
        next[parentKey] = true
        _tree.opened = next
    }

    // The row's editor in the shared pane (S155: also while running).
    function openFeedback(key, title) {
        if (_pane.open && _pane.paneKey === key)
            return true
        if (_pane.hasUnsaved()) {
            _pendingOpen = { key: key, title: title }
            _pane.askLeave("The action editor has changes that are not saved.")
            return false
        }
        if (_pane.open)
            _pane.closeNow()
        var draft = _layout.beginFeedback(key)
        if (!draft || !draft.key)
            return false
        _pane.openCustom(key, title, _feedbackEditor, {
            dirty: function() { return _layout.feedbackDirty() },
            commit: function() { return _layout.commitFeedback() },
            discard: function() { _layout.discardFeedback() },
            end: function() { _layout.endFeedback() },
            lockExempt: true
        })
        return true
    }

    function addFeedback(parentKey) {
        var key = String(_layout.addFeedback(parentKey) || "")
        if (!key.length) {
            _message.show(String(_layout.feedbackMessage || "Feedback could not be added."), true)
            return ""
        }
        _openParent(parentKey)
        return key
    }

    function addCompanionFeedback(parentKey, kind) {
        var key = String(_layout.addCompanionFeedback(parentKey, kind) || "")
        if (!key.length) {
            _message.show(String(_layout.feedbackMessage || "Feedback could not be added."), true)
            return ""
        }
        _openParent(parentKey)
        _showFeedbackMessage()
        return key
    }

    // Deleting a feedback row asks first (01 S140); Undo puts it back.
    function deleteFeedbackAsked(key, title) {
        Confirm.ask(_root, {
            title: "Delete this feedback?",
            text: title + ". Nothing more is sent for it.",
            undoable: true,
            action: "Delete Feedback",
            onAccept: function() {
                if (_pane.open && _pane.paneKey === key)
                    _pane.finishClose()
                _layout.deleteFeedback(key)
            }
        })
    }

    // An address with OSC pattern characters (S147).
    function isPattern(text) {
        return /[*?\[\]{}]/.test(String(text || ""))
    }

    // Change Address…'s live lines (S152): why the address is refused, and
    // how many of the Monitor's recent addresses a pattern matches.
    function _checkAddress(value) {
        var text = String(value || "").trim()
        _addressDialog.errorText = text.length ? String(_layout.addressError(text) || "") : ""
        if (!text.length || _addressDialog.errorText.length || !isPattern(text)) {
            _addressDialog.hintText = ""
            return
        }
        var n = Number(_layout.matchesSeen(text) || 0)
        _addressDialog.hintText = "Matches " + n + " of the addresses seen"
    }

    // Change Address… (one Undo step); the model's error shows on the message line.
    function changeAddress(key, value) {
        var err = _layout.changeAddress(key, value)
        if (err && String(err).length) {
            _message.show(String(err), true)
            return false
        }
        _message.clear()
        return true
    }

    function _askChangeAddress(key) {
        _addressDialog.errorText = ""
        _addressDialog.hintText = ""
        _addressDialog.key = key
        _addressDialog.text = String(_layout.addressOf(key) || "")
        _addressDialog.visible = true
    }

    // Edit Settings… on one input, or on every selected input (OX6, 09 S146):
    // what they share is filled in, what differs is blank; OK applies only
    // what was changed, as one Undo step.
    function editSettings(keys) {
        if (editorLocked || !keys || keys.length === 0)
            return false
        return _addDialog.openForKeys(keys, _layout.editSettingsFor(keys))
    }

    // Copy for Companion (D-09-OSC-COMPANION): Generic OSC settings and the
    // key actions for one input, on the clipboard.
    function copyForCompanion(key) {
        var text = String(_layout.copyForCompanion(key) || "")
        if (text.length) {
            _message.show("Copied. Paste it where you set up Companion.", false)
            return true
        }
        _message.show("Nothing to copy.", true)
        return false
    }

    // Send Test Press / Send Test Value (OX5, 09 S145): the live value
    // always; the actions only while the profile runs.
    function sendTestPress(key) {
        return _layout.sendTest(key, "press", 1.0)
    }

    function sendTestValue(key, value) {
        return _layout.sendTest(key, "value", Number(value))
    }

    // Clear: the shared question (01 S140).
    function askClear() {
        var n = _devices.rowCount()
        return Confirm.ask(_root, {
            title: "Clear OSC inputs?",
            text: n === 1 ? "The one OSC input goes from OSC's list, which every profile uses, with its actions."
                : "All " + n + " OSC inputs go from OSC's list, which every profile uses, with their actions.",
            undoable: true,
            action: "Clear OSC Inputs",
            onAccept: function() {
                if (!editorLocked)
                    _layout.clearAll()
            }
        })
    }

    // 01 S140: deleting rows asks first (the page's Undo puts them back).
    function _askDeleteRows(keys, title) {
        var n = keys.length
        Confirm.ask(_root, {
            title: n === 1 ? "Delete " + title + "?" : "Delete " + n + " OSC inputs?",
            text: n === 1 ? "The OSC input goes, with its actions."
                          : "The OSC inputs go, with their actions.",
            undoable: true,
            action: n === 1 ? "Delete Input" : "Delete " + n + " Inputs",
            onAccept: function() { _layout.deleteParents(keys) }
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

    function _askClearName(key, title, user) {
        Confirm.ask(_root, {
            title: "Clear the name of " + title + "?",
            text: "Your name “" + user + "” goes; the address stays.",
            undoable: true,
            action: "Clear Name",
            onAccept: function() { _layout.setUserName(key, "") }
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

    function _applyFind() {
        _layout.setFilter(
            _find.text,
            _find.typeValue,
            _find.isChecked("ungrouped"),
            false,
            _find.isChecked("noAction")
        )
        _layout.setPatternsOnly(_find.isChecked("patterns"))
    }

    OscLayoutModel { id: _layout }
    Connections {
        target: _layout
        function onPaneLost() { _root.closePaneNow() }
        // A feedback row that is gone (deleted, Undo) closes its editor.
        function onFeedbackEditorChanged() {
            if (_pane.open && _layout.isFeedbackKey(_pane.paneKey) && !(_layout.feedbackEditor || {}).key)
                _pane.closeNow()
        }
    }

    // The Add window, Import, Listen and the input's settings work on OSC's
    // list through this model (shared with every profile).
    OscDeviceManagementModel { id: _devices }
    // A new input from Add / Listen / one import line is selected (S12).
    Connections {
        target: _devices
        ignoreUnknownSignals: true
        function onInputAdded(uid) {
            Qt.callLater(function() {
                var key = String(_layout.keyOfUid(uid) || "")
                if (key.length)
                    _tree.select(key, false)
            })
        }
    }

    Component.onCompleted: {
        _layout.setMode(mode)
        _devices.setMode(mode)
        _loadMonitorHeight()
    }

    onModeChanged: _layout.setMode(mode)

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumWidth: Style.dp(360)
                spacing: Style.dp(6)

                ControlFindBar {
                    id: _find
                    layout: _layout
                    namePrefix: "osc"
                    placeholder: "Address, your name, or group"
                    typeChoices: [
                        { label: "All types", value: "all" },
                        { label: "Buttons", value: "button" },
                        { label: "Axes", value: "axis" }
                    ]
                    filters: [
                        { label: "Ungrouped", name: "ungrouped" },
                        { label: "No actions in this mode", name: "noAction" },
                        { label: "Patterns", name: "patterns" }
                    ]
                    locked: _root.editorLocked
                    paneOpen: _root.actionOpen
                    onChanged: _root._applyFind()
                    buttons: [
                        Button {
                            objectName: "oscSetup"
                            Layout.alignment: Qt.AlignTop
                            text: "OSC Setup…"
                            onClicked: _root.openSetup()
                        },
                        Button {
                            objectName: "oscMonitor"
                            Layout.alignment: Qt.AlignTop
                            text: "Monitor"
                            highlighted: !!_root._popWin || (_root.monitorShown && !_monitor.folded)
                            onClicked: _root.toggleMonitor()
                        }
                    ]
                }

                ControlTree {
                    id: _tree
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    layout: _layout
                    locked: _root.editorLocked
                    namePrefix: "osc"
                    dragMime: "application/x-gremlin-osc"
                    dragLayer: _root
                    emptyText: "No OSC inputs yet. Right-click here to add some."
                    filtering: _find.filtering
                    rowExtras: _rowExtras

                    onClearFilters: _find.clear()
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
                    onFeedbackClicked: (key, title) => _root.openFeedback(key, title)
                    onFeedbackMenu: (key, title, enabled, item, x, y) => {
                        _root._fbKey = key
                        _root._fbTitle = title
                        _root._fbEnabled = enabled
                        _feedbackMenu.openAt(item, x, y)
                    }
                }

                MessageLine {
                    id: _message
                    Layout.fillWidth: true
                    Layout.leftMargin: Style.dp(10)
                    Layout.rightMargin: Style.dp(10)
                }
            }

            ActionPane {
                id: _pane
                layout: _layout
                locked: _root.editorLocked
                namePrefix: "osc"
                onLeaveDone: (resolved) => {
                    var next = _root._pendingOpen
                    _root._pendingOpen = null
                    if (next && resolved)
                        _root.openFeedback(next.key, next.title)
                    _root._finishLeave(resolved)
                }
            }
        }

        // The grip: drag to size the unfolded Monitor.
        Rectangle {
            objectName: "oscMonitorGrip"
            visible: _monitor.visible && !_monitor.folded
            Layout.fillWidth: true
            Layout.preferredHeight: Style.dp(6)
            color: _dockGrip.containsMouse || _dockGrip.pressed ? Style.info : Style.line
            Row {
                anchors.centerIn: parent
                spacing: Style.dp(3)
                Repeater {
                    model: 5
                    Rectangle {
                        width: Style.dp(3)
                        height: Style.dp(2)
                        color: Style.fgMuted
                    }
                }
            }
            MouseArea {
                id: _dockGrip
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.SplitVCursor
                property int originH: 0
                property real originY: 0
                onPressed: (mouse) => {
                    originH = _monitor.height
                    originY = mapToItem(_root, mouse.x, mouse.y).y
                }
                onPositionChanged: (mouse) => {
                    if (!pressed)
                        return
                    var y = mapToItem(_root, mouse.x, mouse.y).y
                    var px = Math.max(Style.dp(140), Math.min(_root.height - Style.dp(200), originH - (y - originY)))
                    _root.monitorUnits = Math.round(px * 100 / Style.uiScale)
                }
                onReleased: _root._saveMonitorHeight()
            }
        }

        OscMonitorPanel {
            id: _monitor
            visible: _root.monitorShown
            Layout.fillWidth: true
            Layout.preferredHeight: folded ? foldedHeight : Style.dp(_root.monitorUnits)
            docked: true
            folded: true
            // The port is held only while the OSC page is the page shown (OP8).
            pageOpen: _root.visible
            onPopOutRequested: _root.popOutMonitor()
            onCloseRequested: _root.monitorShown = false
            onAddAsInputRequested: (settings) => _root.openAddWith(settings)
        }
    }

    // The input's live value and when it was last seen (OX1, 09 S141), at
    // the right of its row. Last seen ticks once a second while shown.
    property int _tick: 0
    Timer {
        interval: 1000
        repeat: true
        running: _root.visible
        onTriggered: _root._tick++
    }

    // Right end of a row: the live value and, on an axis input, Invert
    // (S161, Logical's writer-row Invert); the on/off box on a feedback row
    // (S153; usable while running, S155).
    Component {
        id: _rowExtras
        Loader {
            readonly property var rowModel: parent ? parent.rowModel : null
            readonly property bool feedback: !!rowModel && rowModel.rowKind === "feedback"
            readonly property bool wanted: !!item && item.wanted === true
            sourceComponent: feedback ? _feedbackOn : _inputExtras
        }
    }

    Component {
        id: _inputExtras
        RowLayout {
            id: _inputRow
            readonly property var rowModel: parent ? parent.rowModel : null
            readonly property bool canInvert: !!rowModel && rowModel.rowKind === "parent"
                                              && rowModel.canInvert === true
            readonly property bool wanted: canInvert || (!!_live.item && _live.item.wanted === true)
            spacing: Style.dp(10)
            Loader {
                id: _live
                readonly property var rowModel: _inputRow.rowModel
                visible: !!item && item.wanted === true
                Layout.alignment: Qt.AlignVCenter
                sourceComponent: _liveValue
            }
            CheckBox {
                property bool ownsPress: true
                objectName: "oscRowInvert"
                visible: _inputRow.canInvert
                enabled: !_root.editorLocked
                Layout.alignment: Qt.AlignVCenter
                text: "Invert"
                checked: !!_inputRow.rowModel && _inputRow.rowModel.inverted === true
                onClicked: {
                    if (_inputRow.rowModel)
                        _layout.setInverted(_inputRow.rowModel.key, checked)
                }
            }
        }
    }

    Component {
        id: _feedbackOn
        CheckBox {
            objectName: "oscFeedbackRowOn"
            readonly property var row: parent ? parent.rowModel : null
            readonly property bool wanted: true
            checked: !!row && !!row.enabled
            padding: 0
            onClicked: {
                if (row)
                    _layout.setFeedbackEnabled(row.key, checked)
            }
            PointerTip {
                text: "Send this feedback"
                show: parent.hovered
            }
        }
    }

    Component {
        id: _feedbackEditor
        OscFeedbackEditor {
            layout: _layout
        }
    }

    Component {
        id: _liveValue
        ColumnLayout {
            id: _live
            readonly property var row: parent ? parent.rowModel : null
            readonly property string value: row && row.liveValue ? String(row.liveValue) : ""
            readonly property real seenAt: row && row.lastSeenAt ? Number(row.lastSeenAt) : 0
            readonly property string seen: {
                _root._tick
                return seenAt > 0 ? String(_layout.lastSeenText(seenAt)) : ""
            }
            readonly property bool wanted: !!row && row.rowKind === "parent" && seenAt > 0
            spacing: 0
            Label {
                objectName: "oscLiveValue"
                Layout.alignment: Qt.AlignRight
                text: _live.value + (_live.row && _live.row.liveSynthetic ? " (test)" : "")
                visible: _live.value.length > 0
                color: Style.fg
                font.pixelSize: Style.dp(12)
            }
            Label {
                objectName: "oscLastSeen"
                Layout.alignment: Qt.AlignRight
                text: _live.seen
                visible: text.length > 0
                color: Style.fgMuted
                font.pixelSize: Style.dp(10)
            }
        }
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
    property string _actionParent: ""
    property int _actionSeq: -1
    property string _actionTitle: ""

    function _openLayoutMenu(onRow, onGroup, item, px, py) {
        _menuOnRow = onRow
        _menuOnGroup = onGroup
        _pageMenu.openAt(item, px, py)
    }

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

    function _renameRow() {
        _nameDialog.lastAccepted = _menuUser
        _nameDialog.text = _menuUser
        _nameDialog.visible = true
    }

    function _renameGroup() {
        _groupDialog.text = _groupName
        _groupDialog.visible = true
    }

    // Tools > History, only this input's saved changes ("parent:button:3").
    function _openHistory() {
        var parts = String(_menuKey).split(":")
        if (parts.length < 3)
            return
        Helpers.createComponent("DialogHistory.qml", {
            filter: JSON.stringify({
                device: "OSC",
                inputType: parts[1],
                inputId: parts[2],
                mode: uiState ? uiState.currentMode : "Default"
            })
        })
    }

    function _selectedKeys() {
        return _picked.length > 0 ? _picked.slice() : [_menuKey]
    }

    function _layoutMenuModel() {
        var locked = editorLocked
        var onRow = _menuOnRow && !locked
        var onGroup = _menuOnGroup && !locked
        var many = _picked.length > 1
        var kind = onRow ? "osc-row" : (onGroup ? "osc-group" : "osc")
        var title = onRow ? (many ? _picked.length + " inputs" : _menuTitle)
                          : (onGroup ? _groupName : "OSC")
        var header = locked ? [] : [
            { label: "Undo", enabled: _layout.canUndo && !actionOpen, run: function() { _layout.undo() } },
            { label: "Redo", enabled: _layout.canRedo && !actionOpen, run: function() { _layout.redo() } }
        ]
        var quick = []
        if (onRow) {
            if (!many) {
                quick.push(MenuModel.action("Add Action", function() { _openNewPane(_menuKey, _menuTitle) }))
                quick.push(MenuModel.action("Add Feedback", function() { addFeedback(_menuKey) }))
                quick.push(MenuModel.action("Rename", _renameRow))
                quick.push(MenuModel.action("Change Address…", function() { _askChangeAddress(_menuKey) }))
            }
            quick.push(MenuModel.action(many ? "Edit Settings of " + _picked.length + " Inputs…" : "Edit Settings…",
                                        function() { editSettings(_selectedKeys()) }))
            if (!many) {
                quick.push(MenuModel.action("Copy for Companion", function() { copyForCompanion(_menuKey) }))
                if (_menuKey.indexOf(":axis:") >= 0)
                    quick.push(MenuModel.number("Send Test Value", 0.5, -1, 1, "", function(v) {
                        sendTestValue(_menuKey, v)
                    }, true, { step: 0.1, go: "Send" }))
                else
                    quick.push(MenuModel.action("Send Test Press", function() { sendTestPress(_menuKey) }))
                quick.push(MenuModel.action("History", _openHistory))
            }
        }
        if (onGroup)
            quick.push(MenuModel.action("Rename Group", _renameGroup))
        if (!_menuOnRow && !_menuOnGroup)
            quick.push(MenuModel.action("Feedback settings…", function() { openFeedbackSettings() }))

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
        return MenuModel.menu(kind, title, quick, [
            onRow && !many ? MenuModel.section("companion", "Companion feedback", [
                MenuModel.action("Key text", function() { addCompanionFeedback(_menuKey, "text") }),
                MenuModel.action("Key color", function() { addCompanionFeedback(_menuKey, "colour") })
            ]) : null,
            onRow ? MenuModel.section("row", "Row", [
                MenuModel.action("Clear Name", function() {
                    _askClearName(_menuKey, _menuTitle, _menuUser)
                }, _menuUser.length > 0 && !many),
                MenuModel.action(many ? "Delete " + _picked.length + " inputs…" : "Delete…", function() {
                    _askDeleteRows(_selectedKeys(), _menuTitle)
                }, true, { danger: true })
            ]) : null,
            onRow ? MenuModel.section("group", "Group", [
                MenuModel.entry("Group as", function(name) { _groupAs(name) }, true,
                                { placeholder: "Name, then Enter" })
            ].concat(moveTo)) : null,
            locked ? null : MenuModel.section("add", "Add Inputs", [
                MenuModel.action("Add…", function() { openAdd() }),
                MenuModel.action("Import…", function() { openImport() }),
                MenuModel.action("From TouchOSC Layout…", function() { openTouchOsc() }),
                MenuModel.action("Listen", function() { listen() }),
                MenuModel.action("Clear…", function() { askClear() }, _devices.rowCount() > 0,
                                 { danger: true })
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
                MenuModel.action("By Address", function() { _layout.sortBySystem() }),
                MenuModel.action("By Your Name", function() { _layout.sortByName() }),
                MenuModel.action("Group Names A to Z", function() { _layout.sortGroupNames() })
            ])
        ], header)
    }

    ContextMenu {
        id: _pageMenu
        build: _root._layoutMenuModel
    }

    ContextMenu {
        id: _actionMenu
        menuWidth: Style.dp(220)
        build: function() {
            return MenuModel.menu("osc-action", _root._actionTitle, [
                MenuModel.action("Open", function() {
                    _root._openPane(_root._actionParent, _root._actionSeq, _root._actionTitle)
                }),
                MenuModel.action("Delete", function() {
                    _root.deleteActionAsked(_root._actionParent, _root._actionSeq, _root._actionTitle)
                }, true, { danger: true })
            ])
        }
    }

    // A feedback row's menu: offered while running too (S155).
    ContextMenu {
        id: _feedbackMenu
        menuWidth: Style.dp(220)
        build: function() {
            var key = _root._fbKey
            return MenuModel.menu("osc-feedback", _root._fbTitle, [
                MenuModel.action("Open", function() { _root.openFeedback(key, _root._fbTitle) }),
                MenuModel.action(_root._fbEnabled ? "Turn Off" : "Turn On", function() {
                    _layout.setFeedbackEnabled(key, !_root._fbEnabled)
                }),
                MenuModel.action("Duplicate", function() { _layout.duplicateFeedback(key) }),
                MenuModel.action("Delete…", function() {
                    _root.deleteFeedbackAsked(key, _root._fbTitle)
                }, true, { danger: true })
            ])
        }
    }

    // +---------------------------------------------------------------------
    // | Windows

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

    TextInputDialog {
        id: _addressDialog
        objectName: "oscAddressDialog"
        property string key: ""
        visible: false
        width: Style.dp(360)
        clearOnClick: false
        heading: "OSC address"
        validator: function(value) { return value.trim().length > 0 }
        onEdited: (value) => _root._checkAddress(value)
        onAccepted: (value) => {
            if (!_root.editorLocked)
                _root.changeAddress(key, value.trim())
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

    OscImportDialog {
        id: _importDialog
        deviceModel: _devices
        onAccepted: (text) => {
            if (!_root.editorLocked) {
                var result = _devices.importInputs(text)
                _message.show(result ? String(result) : "", false)
            }
        }
        onChooseFileRequested: _importPicker.open()
        // A TouchOSC layout's ticked controls (S162): the same add path.
        onTouchOscAccepted: (path, chosen) => {
            if (!_root.editorLocked) {
                var result = _devices.importTouchOsc(path, chosen)
                _message.show(result ? String(result) : "", false)
            }
        }
    }

    // Import's file: a .txt fills the box, a .tosc shows the preview (S162).
    FilePicker {
        id: _importPicker
        kind: "other"
        mode: "open"
        title: "Import OSC Inputs"
        nameFilters: ["OSC messages or TouchOSC layouts (*.txt *.tosc)",
                      "TouchOSC layouts (*.tosc)", "Text files (*.txt)", "All files (*)"]
        onPicked: (selected) => _importDialog.loadFile(selected.toString())
    }

    OscAddDialog {
        id: _addDialog
        objectName: "oscAdd"
        deviceModel: _devices
        applySettings: function(keys, changed) { return _layout.applySettings(keys, changed) }
        onAccepted: (settings) => {
            if (!_root.editorLocked)
                _devices.createConfiguredInput(settings)
        }
    }
}
