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

    // After the unsaved-changes question: true when the pane was saved or
    // dropped (and closed), false when the user stayed.
    signal leaveDone(bool resolved)

    function hasUnsaved() { return open && layout.paneDirty() }

    // OK for Run's "Save" (06 Q6): false when nothing could be written.
    function save() { return !hasUnsaved() || layout.commitPane() >= 0 }

    function openAt(key, seq, title) {
        if (locked)
            return
        layout.beginPane(key, seq)
        paneKey = key
        paneTitle = title
        open = true
    }

    function openNew(key, title) {
        if (locked)
            return
        layout.beginNewAction(key)
        paneKey = key
        paneTitle = title
        open = true
    }

    function askLeave(text) {
        _leave.ask(text)
    }

    function requestClose() {
        if (layout.paneDirty()) {
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
        layout.endPane()
        open = false
        paneKey = ""
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
                Layout.fillWidth: true
                Layout.fillHeight: true
                holdModel: true
                inputItemModel: _pane.layout.paneModel
            }
            // A pane open when Run starts turns read-only: no OK (06 Q6, 05 Q11).
            Label {
                objectName: _pane.namePrefix + "PaneLocked"
                visible: _pane.locked
                text: "Profile running: stop it to edit"
                color: Style.fgMuted
                Layout.fillWidth: true
                elide: Text.ElideRight
            }
            RowLayout {
                visible: !_pane.locked
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
                        _pane.layout.commitPane()
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
            _pane.layout.commitPane()
            _pane.finishClose()
            _pane.leaveDone(true)
        }
        onDiscardChosen: {
            _pane.layout.discardPane()
            _pane.finishClose()
            _pane.leaveDone(true)
        }
        onCancelled: _pane.leaveDone(false)
    }
}
