// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Profile
import Gremlin.Style

Item {
    id: _root

    property InputItemModel inputItemModel
    property int inputIndex
    property bool isOutput: false
    property bool holdModel: false
    property bool inlineMode: false
    property bool hideControlSetup: false
    property bool catalogSequence: false
    property int onlySequence: -1
    property color editorFill: Style.infoFillDeep
    property color editorEdge: Style.info
    property color editorAccent: Style.info
    property int editorRadius: Style.dp(3)
    property int editorBorderW: Style.dp(1)
    property int editorAccentW: Style.dp(3)
    property bool showAccent: true
    property int editorPad: Style.dp(10)
    property int editorPadTop: Style.dp(10)
    property int editorPadRight: Style.dp(10)
    property int editorPadBottom: Style.dp(10)
    property int editorPadLeft: Style.dp(10)
    // The one edit lock (06 S13): nothing is edited while the profile runs.
    // Output pages are not locked.
    EditLock { id: _lock }
    readonly property bool editorLocked: _lock.locked && !isOutput
    // The Keyboard page edits a draft of the key: OK writes it, Undo and
    // Redo step through each OK, as on the Configuration page (05 Q5).
    readonly property bool keyboardDraft: !holdModel && !isOutput && !inlineMode
                                          && !!uiState && uiState.currentTab === "keyboard"
    readonly property var shownModel: keyboardDraft ? _kb.paneModel : inputItemModel
    enabled: true
    opacity: editorLocked ? 0.55 : 1.0
    implicitHeight: inlineMode ? Math.max(Style.dp(80), _content.implicitHeight) + editorPadTop + editorPadBottom : Style.dp(200)

    Rectangle {
        visible: inlineMode
        anchors.fill: parent
        color: editorFill
        border.color: editorEdge
        border.width: editorBorderW
        radius: editorRadius
    }

    Rectangle {
        visible: inlineMode && showAccent && editorAccentW > 0
        width: editorAccentW
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.margins: Math.max(Style.dp(1), editorBorderW)
        color: editorAccent
    }

    KeyboardPaneModel { id: _kb }

    // The key shown in the Keyboard page's draft. A draft with changes stays
    // on its key (OK writes there) until it is saved or discarded.
    function showKey(force) {
        if (!keyboardDraft || !uiState)
            return
        if (!force && _kb.paneDirty())
            return
        _kb.showInput(uiState.currentInput, uiState.currentInputIndex, uiState.currentMode)
    }

    // Main.closeActionPanes() asks these before a tool changes bindings
    // behind the pane (05 Q8) or Run starts (06 Q6).
    function paneHasChanges() {
        return keyboardDraft && _kb.paneDirty()
    }

    function closeActionPane() {
        if (keyboardDraft)
            _kb.revert()
    }

    // OK for Run's "Save" (06 Q6): false when nothing could be written.
    function savePane() {
        return !paneHasChanges() || _kb.commitPane() >= 0
    }

    // Undo and Redo replace the draft: changes not saved are asked about.
    function _step(back) {
        var go = function() { if (back) _kb.undo(); else _kb.redo() }
        if (!_kb.paneDirty()) {
            go()
            return
        }
        _discardGate.confirmThen("Unsaved Changes",
            "The action editor has changes that are not saved.", "Discard", go, null, false)
    }

    DismissibleDialog { id: _discardGate }

    onKeyboardDraftChanged: showKey(false)

    Connections {
        target: signal
        function onProfileChanged() {
            // The draft belonged to the profile that was open.
            if (_root.keyboardDraft)
                _root.showKey(true)
        }
    }

    Connections {
        target: uiState
        function onModeChanged() { _root.showKey(false) }
    }

    Component.onCompleted: {
        if (keyboardDraft) {
            showKey(true)
            return
        }
        if (holdModel || !backend || !uiState)
            return
        _root.inputItemModel = backend.getInputItem(
            uiState.currentInput,
            uiState.currentInputIndex
        )
    }

    Connections {
        target: uiState

        function onInputChanged() {
            if (_root.keyboardDraft) {
                _root.showKey(false)
                return
            }
            if (_root.holdModel || !backend || !uiState)
                return
            _root.inputItemModel = backend.getInputItem(
                uiState.currentInput,
                uiState.currentInputIndex
            )
        }
    }

    Connections {
        target: signal

        function onReloadCurrentInputItem() {
            if (_root.keyboardDraft) {
                _root.showKey(false)
                return
            }
            if (_root.holdModel || !backend || !uiState)
                return
            _root.inputItemModel = backend.getInputItem(
                uiState.currentInput,
                uiState.currentInputIndex
            )
        }
    }

    DismissibleDialog {
        id: _selectInputDialog

        titleText: "Select an Input"
        messageText: "Select an input first, then add an action."
        confirmText: "OK"
    }

    ColumnLayout {
        id: _content

        anchors.fill: inlineMode ? undefined : parent
        x: inlineMode ? editorPadLeft : 0
        y: inlineMode ? editorPadTop : 0
        width: parent.width - (inlineMode ? editorPadLeft + editorPadRight : 0)
        spacing: Style.dp(8)

        Repeater {
            id: _inlineRepeater
            model: _root.inlineMode && _root.onlySequence < 0 ? _root.inputItemModel : null

            delegate: InputItemBinding {
                Layout.fillWidth: true
                enabled: !editorLocked
                inputBinding: modelData
                inputItemModel: _root.inputItemModel
                hideControlSetup: _root.hideControlSetup
                catalogSequence: _root.catalogSequence
            }
        }

        Loader {
            Layout.fillWidth: true
            active: _root.inlineMode && _root.onlySequence >= 0 && _root.inputItemModel
                    && _root.onlySequence < _root.inputItemModel.rowCount()
            sourceComponent: InputItemBinding {
                width: _content.width
                enabled: !editorLocked
                inputItemModel: _root.inputItemModel
                inputBinding: _root.inputItemModel.data(_root.inputItemModel.index(_root.onlySequence, 0))
                hideControlSetup: _root.hideControlSetup
                catalogSequence: _root.catalogSequence
            }
        }

        JGListView {
            id: _listView
            visible: !_root.inlineMode
            Layout.fillHeight: true
            Layout.fillWidth: true
            scrollbarAlwaysVisible: true
            enabled: !editorLocked
            model: _root.inlineMode ? null : _root.shownModel
            delegate: _entryDelegate
        }

        // The Keyboard page's draft: OK writes it (05 Q5). While the
        // profile runs it is read-only, with no OK (05 Q11).
        RowLayout {
            visible: _root.keyboardDraft
            Layout.fillWidth: true
            spacing: Style.dp(6)
            Label {
                Layout.fillWidth: true
                elide: Text.ElideRight
                color: Style.fgMuted
                text: _root.editorLocked
                      ? "Profile running: stop it to edit"
                      : (_kb.keyName.length && uiState && _kb.paneMode.length
                         && _kb.paneMode !== uiState.currentMode
                         ? _kb.keyName + " (in " + _kb.paneMode + ")" : "")
            }
            Button {
                objectName: "keyboardUndo"
                text: "Undo"
                focusPolicy: Qt.NoFocus
                enabled: _kb.canUndo && !_root.editorLocked
                onClicked: _root._step(true)
            }
            Button {
                objectName: "keyboardRedo"
                text: "Redo"
                focusPolicy: Qt.NoFocus
                enabled: _kb.canRedo && !_root.editorLocked
                onClicked: _root._step(false)
            }
            Button {
                objectName: "keyboardCancel"
                text: "Cancel"
                visible: !_root.editorLocked
                enabled: !!_kb.paneModel
                onClicked: _kb.revert()
            }
            Button {
                objectName: "keyboardOk"
                text: "OK"
                visible: !_root.editorLocked
                enabled: !!_kb.paneModel
                highlighted: true
                onClicked: _kb.commitPane()
            }
        }

        Component {
            id: _entryDelegate

            Item {
                id: _delegate

                height: _binding.height
                width: _binding.width

                required property int index
                required property var modelData
                property ListView view: ListView.view

                InputItemBinding {
                    id: _binding

                    implicitWidth: view.width
                    enabled: !editorLocked

                    inputBinding: modelData
                    inputItemModel: _root.shownModel
                    hideControlSetup: _root.hideControlSetup
                }
            }
        }
    }
}
