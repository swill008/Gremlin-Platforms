// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Device
import Gremlin.Style
import Gremlin.UI

// The action editor docked at the right of a control page (Logical Device,
// OSC): its width grip, the shared editor on the model's pane draft, OK and
// "Close pane after OK", and the question about unsaved changes.
RowLayout {
    id: _pane

    property var layout: null
    property bool locked: false
    property string namePrefix: "control"

    property bool open: false
    property string paneKey: ""
    property string paneTitle: ""
    // Pane width at 100%. It is saved in these units, with "Close pane
    // after OK", for every page that has the pane.
    property int paneUnits: 560
    readonly property int paneWidth: Style.dp(paneUnits)
    // The width shown: the saved width while it fits beside the page's
    // other columns, less when the window is too narrow for it (never below
    // the pane's minimum). The saved width is not changed (05 S23).
    readonly property int shownWidth: Math.max(Style.dp(420), Math.min(paneWidth, _room()))
    property bool closeAfterOk: false
    property bool _ready: false

    // A page's own editor in place of the action editor (OSC's Feedback
    // editor, 09 S153). Set through openCustom; null shows the action
    // editor. The hooks replace the model's pane draft calls: dirtyFn() ->
    // bool, commitFn() -> bool, discardFn(), endFn().
    property Component editor: null
    property var dirtyFn: null
    property var commitFn: null
    property var discardFn: null
    property var endFn: null
    // The editor stays editable while a profile runs (OSC feedback, S155).
    property bool lockExempt: false

    // After the unsaved-changes question: true when the pane was saved or
    // dropped (and closed), false when the user stayed.
    signal leaveDone(bool resolved)

    // Width left for the pane: the row's width less each other visible
    // column's least width (its minimum when it stretches, else its width).
    function _room() {
        var row = _pane.parent
        if (!row)
            return paneWidth
        var used = Style.dp(6)
        for (var i = 0; i < row.children.length; ++i) {
            var c = row.children[i]
            if (c === _pane || !c.visible)
                continue
            var lay = c.Layout
            if (lay.fillWidth)
                used += Math.max(0, lay.minimumWidth)
            else
                used += lay.preferredWidth >= 0 ? lay.preferredWidth : c.implicitWidth
            used += row.spacing || 0
        }
        return row.width - used
    }

    function _dirty() { return dirtyFn ? !!dirtyFn() : layout.paneDirty() }

    function _commit() { return commitFn ? !!commitFn() : layout.commitPane() >= 0 }

    function _discard() {
        if (discardFn)
            discardFn()
        else
            layout.discardPane()
    }

    function _useActionEditor() {
        editor = null
        dirtyFn = null
        commitFn = null
        discardFn = null
        endFn = null
        lockExempt = false
    }

    function hasUnsaved() { return open && _dirty() }

    // OK for Run's "Save" (06 Q6): false when nothing could be written.
    function save() { return !hasUnsaved() || _commit() }

    // Leaving the page (Main.continueDisplayLeave): an open pane with edits
    // asks Save / Discard / Cancel; leaveResolved() lets Main go on to the
    // next page, leaveCancelled() stops the leave. A page exposes this pane
    // as `property alias actionPane: <pane id>` and Main calls these on it.
    signal leaveResolved()
    signal leaveCancelled()

    property bool _leavingPage: false

    function requestLeave() {
        if (!hasUnsaved()) {
            leaveResolved()
            return
        }
        _leavingPage = true
        askLeave("The action editor has changes that are not saved.")
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

    // Main.closeActionPanes() asks these before a tool changes bindings
    // behind the pane (05 Q8) or Run starts (06 Q6).
    function paneHasChanges() { return hasUnsaved() }

    function closeActionPane() { closeNow() }

    function savePane() { return save() }

    // After a profile change the pane belongs to a profile that is gone.
    function closePaneNow() { closeNow() }

    Connections {
        target: _pane
        function onLeaveDone(resolved) {
            _pane._finishLeave(resolved)
            _pane._finishOpen(resolved)
        }
    }

    // The page's ControlTree, when a row click selects before it opens the
    // pane: Cancel puts the selection back on the pane's input.
    property var tree: null

    property int _paneSeq: -1
    property bool _paneNew: false
    // Another input asked to open while the pane had unsaved edits (05 S26).
    property var _pendingOpen: null

    function openAt(key, seq, title) { _open(key, seq, title, false) }

    function openNew(key, title) { _open(key, -1, title, true) }

    // Opening another input with unsaved edits asks Save / Discard / Cancel
    // first (05 S26); the open goes on after Save or Discard.
    function _open(key, seq, title, isNew) {
        if (locked)
            return
        if (hasUnsaved()) {
            // The row being edited clicked again: keep editing.
            if (!editor && !isNew && !_paneNew && key === paneKey && seq === _paneSeq)
                return
            _pendingOpen = { key: key, seq: seq, title: title, isNew: isNew }
            askLeave("The action editor has changes that are not saved.")
            return
        }
        if (open && editor)
            finishClose()
        _useActionEditor()
        if (isNew)
            layout.beginNewAction(key)
        else
            layout.beginPane(key, seq)
        paneKey = key
        paneTitle = title
        _paneSeq = seq
        _paneNew = isNew
        open = true
    }

    function _finishOpen(resolved) {
        var next = _pendingOpen
        _pendingOpen = null
        if (!next)
            return
        if (resolved) {
            _open(next.key, next.seq, next.title, next.isNew)
            return
        }
        // Cancel: the pane stays on its input; so does the selection.
        if (tree && open && paneKey.length && next.key !== paneKey
                && tree.picked.length === 1 && tree.picked[0] === next.key)
            tree.select(paneKey, false)
    }

    // The page's own editor; hooks: {dirty, commit, discard, end, lockExempt}.
    // The page has opened its draft already.
    function openCustom(key, title, component, hooks) {
        if (open && !editor)
            layout.endPane()
        editor = component
        dirtyFn = hooks.dirty || null
        commitFn = hooks.commit || null
        discardFn = hooks.discard || null
        endFn = hooks.end || null
        lockExempt = !!hooks.lockExempt
        paneKey = key
        paneTitle = title
        open = true
    }

    function askLeave(text) {
        _leave.ask(text)
    }

    function requestClose() {
        if (_dirty()) {
            askLeave("The action editor has changes that are not saved.")
            return
        }
        finishClose()
    }

    // After a profile change the pane belongs to a profile that is gone.
    function closeNow() {
        if (open)
            finishClose()
    }

    function finishClose() {
        if (endFn)
            endFn()
        else
            layout.endPane()
        open = false
        paneKey = ""
        _useActionEditor()
    }

    function _saveDock() {
        if (!_ready)
            return
        _place.setActionPaneWidth(paneUnits)
        _place.setClosePaneAfterOk(closeAfterOk)
    }

    WindowPlacement { id: _place }

    Component.onCompleted: {
        paneUnits = _place.actionPaneWidth()
        closeAfterOk = _place.closePaneAfterOk()
        _ready = true
    }

    // The width is saved when the grip is let go, not per pixel.
    onCloseAfterOkChanged: _saveDock()

    visible: open
    Layout.fillWidth: false
    // Grip plus the pane's least width; the Appearance panel reads it
    // (D-05-APPEARANCE-NARROW).
    Layout.minimumWidth: Style.dp(6) + Style.dp(420)
    Layout.fillHeight: true
    spacing: 0

    Rectangle {
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
                originW = _pane.shownWidth
                originX = mapToItem(_pane, mouse.x, mouse.y).x
            }
            onPositionChanged: (mouse) => {
                if (!pressed)
                    return
                var x = mapToItem(_pane, mouse.x, mouse.y).x
                _pane.paneUnits = Math.round(Math.max(Style.dp(420), Math.min(Style.dp(1600), originW - (x - originX))) * 100 / Style.uiScale)
            }
            onReleased: _pane._saveDock()
        }
    }

    Rectangle {
        Layout.preferredWidth: _pane.shownWidth
        Layout.minimumWidth: Style.dp(420)
        Layout.fillHeight: true
        color: Style.bgCard
        border.color: Style.line
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Style.dp(10)
            RowLayout {
                Label {
                    text: _pane.paneTitle.length ? _pane.paneTitle : "Action Editor"
                    color: Style.fg
                    font.bold: true
                    font.pixelSize: Style.dp(16)
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
                Button { text: "×"; implicitWidth: Style.dp(28); onClicked: _pane.requestClose() }
            }
            InputConfiguration {
                visible: !_pane.editor
                Layout.fillWidth: true
                Layout.fillHeight: true
                inputItemModel: _pane.layout.paneModel
            }
            ScrollView {
                visible: !!_pane.editor
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentWidth: availableWidth
                clip: true
                Loader {
                    width: parent ? parent.width : 0
                    active: !!_pane.editor
                    sourceComponent: _pane.editor
                }
            }
            // A pane open when Run starts turns read-only: no OK (06 Q6, 05 Q11).
            Label {
                objectName: _pane.namePrefix + "PaneLocked"
                visible: _pane.locked && !_pane.lockExempt
                text: "Profile running: stop it to edit"
                color: Style.fgMuted
                Layout.fillWidth: true
                elide: Text.ElideRight
            }
            RowLayout {
                visible: !_pane.locked || _pane.lockExempt
                CheckBox {
                    text: "Close pane after OK"
                    checked: _pane.closeAfterOk
                    onClicked: _pane.closeAfterOk = checked
                }
                Item { Layout.fillWidth: true }
                Button {
                    text: "OK"
                    highlighted: true
                    onClicked: {
                        // A page editor's refused draft stays open (its error line says why).
                        if (!_pane._commit() && _pane.commitFn)
                            return
                        if (_pane.closeAfterOk)
                            _pane.finishClose()
                    }
                }
            }
        }
    }

    DismissibleDialog {
        id: _leave
        onSaveChosen: {
            if (!_pane._commit() && _pane.commitFn) {
                _pane.leaveDone(false)
                return
            }
            _pane.finishClose()
            _pane.leaveDone(true)
        }
        onDiscardChosen: {
            _pane._discard()
            _pane.finishClose()
            _pane.leaveDone(true)
        }
        onCancelled: _pane.leaveDone(false)
    }
}
