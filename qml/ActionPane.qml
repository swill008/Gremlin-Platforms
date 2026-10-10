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

    function openAt(key, seq, title) {
        if (locked)
            return
        if (open && editor)
            finishClose()
        _useActionEditor()
        layout.beginPane(key, seq)
        paneKey = key
        paneTitle = title
        open = true
    }

    function openNew(key, title) {
        if (locked)
            return
        if (open && editor)
            finishClose()
        _useActionEditor()
        layout.beginNewAction(key)
        paneKey = key
        paneTitle = title
        open = true
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
                originW = _pane.paneWidth
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
        Layout.preferredWidth: _pane.paneWidth
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
                holdModel: true
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
