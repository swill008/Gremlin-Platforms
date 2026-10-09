// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Style
import "helpers.js" as Helpers

ApplicationWindow {
    font.pixelSize: Style.fontSize
    id: _calibrationDialog

    // ToolWindowMemory sets the saved or default size when the window opens.
    width: 850
    height: 600
    minimumWidth: Style.fitWidth(Style.dp(850), Screen)
    minimumHeight: Style.fitHeight(Style.dp(600), Screen)

    color: Style.background
    U.Universal.theme: Style.theme

    title: "Calibration"

    property string shownSlug: ""
    property string pendingSlug: ""
    property string initialSlug: ""
    property bool allowClose: false

    // For the main window's quit: unsaved calibration this window would ask about.
    // Whether any axis has unsaved changes (for Save all).
    property bool anyUnsaved: false
    function refreshUnsaved() { anyUnsaved = _calib.hasUnsaved() }

    // 01 S143: the Undo / Redo pair says what the last change was.
    property string lastChangeText: ""
    property string undoneText: ""
    // The axis an Undo or Redo put back (its dataChanged, while it runs).
    property bool _stepping: false
    property int _steppedRow: -1

    function axisName(row) {
        if (row < 0 || row >= _calib.rowCount())
            return ""
        // The "identifier" role (device.py AxisCalibration.roles).
        return String(_calib.data(_calib.index(row, 0), Qt.UserRole + 1) || "")
    }

    function noteChange(row, what) {
        lastChangeText = "Last change: " + axisName(row) + ", " + what
        undoneText = ""
    }

    function forgetChanges() {
        lastChangeText = ""
        undoneText = ""
    }

    function _step(redo) {
        _stepping = true
        _steppedRow = -1
        if (redo)
            _calib.redo()
        else
            _calib.undo()
        _stepping = false
        if (_steppedRow >= 0) {
            var name = axisName(_steppedRow)
            if (redo) {
                lastChangeText = "Last change: " + name + ", redone"
                undoneText = ""
            } else {
                undoneText = "Undone: a change to " + name
            }
        }
        refreshUnsaved()
    }

    function undoEdit() {
        if (_calib.canUndo)
            _step(false)
    }

    function redoEdit() {
        if (_calib.canRedo)
            _step(true)
    }

    // 01 S142: what a Save or Save All did, on the message line.
    function report(ok, text) {
        _message.show(text, !ok)
    }

    // A value being typed keeps its own Ctrl+Z.
    Shortcut { sequences: [StandardKey.Undo]; onActivated: _calibrationDialog.undoEdit() }
    // On Windows StandardKey.Redo is Ctrl+Y and Ctrl+Shift+Z; listing either
    // again makes that key ambiguous and it never fires.
    Shortcut { sequences: [StandardKey.Redo]; onActivated: _calibrationDialog.redoEdit() }
    Connections {
        target: _calib
        function onDataChanged(topLeft) {
            if (_calibrationDialog._stepping && topLeft)
                _calibrationDialog._steppedRow = topLeft.row
            _calibrationDialog.refreshUnsaved()
        }
        function onModelReset() { _calibrationDialog.refreshUnsaved() }
        // Another module: its steps start again (03 S106).
        function onUndoChanged() {
            if (!_calib.canUndo && !_calib.canRedo)
                _calibrationDialog.forgetChanges()
        }
    }

    function hasUnsavedWork() {
        return !allowClose && _calib.hasUnsaved()
    }

    ToolWindowMemory {
        host: _calibrationDialog
        name: "calibration"
        defaultWidth: Style.dp(850)
        defaultHeight: Style.dp(600)
    }

    // A card's device that wasn't connected yet: shown when it connects.
    property string waitingSlug: ""

    function chooseModule(slug) {
        var next = slug ? String(slug) : ""
        if (!next.length || next === shownSlug)
            return
        // A device that isn't in the list (not connected) waits for it.
        // With nothing shown yet it is the one shown ("not connected", the
        // drop-down blank), not the first stick in the list.
        if (_moduleSelection.count > 0 && _moduleSelection.indexOfValue(next) < 0) {
            waitingSlug = next
            if (!shownSlug.length) {
                shownSlug = next
                _moduleSelection.currentIndex = -1
            }
            return
        }
        waitingSlug = ""
        if (_calib.hasUnsaved()) {
            pendingSlug = next
            var back = _moduleSelection.indexOfValue(shownSlug)
            if (back < 0)
                back = _moduleSelection.currentIndex
            if (back >= 0)
                _moduleSelection.currentIndex = back
            _saveGate.detail = "Calibration is not saved. Change input module and it will be lost."
            _saveGate.ask()
            return
        }
        shownSlug = next
        syncSelection()
    }

    // Nothing shown and no device asked for (by a card, or waited for):
    // the drop-down's first device is shown.
    function mayPickFirst() {
        return !shownSlug.length && !waitingSlug.length
            && !(initialSlug.length && !_ready)
    }

    // The drop-down names the device whose axes are shown.
    function syncSelection() {
        var index = _moduleSelection.indexOfValue(shownSlug)
        if (index >= 0 && _moduleSelection.currentIndex !== index)
            _moduleSelection.currentIndex = index
    }

    function finishLeave() {
        if (pendingSlug.length) {
            shownSlug = pendingSlug
            pendingSlug = ""
            var next = _moduleSelection.indexOfValue(shownSlug)
            if (next >= 0)
                _moduleSelection.currentIndex = next
            return
        }
        allowClose = true
        close()
    }

    onClosing: (close) => {
        if (!allowClose && _calib.hasUnsaved()) {
            close.accepted = false
            pendingSlug = ""
            _saveGate.detail = "Calibration is not saved. Close this window and it will be lost."
            _saveGate.ask()
            return
        }
        if (_axisView && _axisView.model)
            _axisView.model.destroy()
        if (_axisView)
            _axisView.destroy()
        if (_modules)
            _modules.destroy()
        backend.resumeInputHighlighting("calibration")
    }

    property bool _ready: false

    Component.onCompleted: () => {
        _ready = true
        backend.pauseInputHighlighting("calibration")
        if (initialSlug.length)
            chooseModule(initialSlug)
    }

    onInitialSlugChanged: {
        if (_ready && initialSlug.length)
            chooseModule(initialSlug)
    }

    CalibrationModuleModel {
        id: _modules
        // Sticks came or went: the drop-down keeps naming the device shown
        // (blank while its stick is unplugged; its axes and unsaved work stay).
        // The device a card asked for connected: it is shown (asking first
        // when another one has unsaved work).
        onModelReset: Qt.callLater(function() {
            var slug = _calibrationDialog.waitingSlug
            if (slug.length && _moduleSelection.indexOfValue(slug) >= 0) {
                _calibrationDialog.waitingSlug = ""
                if (slug !== _calibrationDialog.shownSlug) {
                    _calibrationDialog.chooseModule(slug)
                    return
                }
            }
            var index = _moduleSelection.indexOfValue(_calibrationDialog.shownSlug)
            if (index >= 0)
                _moduleSelection.currentIndex = index
            else if (_calibrationDialog.shownSlug.length)
                _moduleSelection.currentIndex = -1
        })
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: Style.dp(10)
        anchors.topMargin: Style.dp(10)

        // The header keeps off the window's right edge; the list below runs
        // to it (its scroll bar sits there).
        RowLayout {
            Layout.rightMargin: Style.dp(10)
            Layout.bottomMargin: Style.dp(15)

            Label {
                Layout.preferredWidth: Style.dp(150)
                text: "Input module"
            }

            ComboBox {
                id: _moduleSelection

                model: _modules
                textRole: "name"
                // Each stick by its own key: two on one file are two entries.
                valueRole: "key"
                implicitContentWidthPolicy: ComboBox.WidestText
                onActivated: _calibrationDialog.chooseModule(currentValue)
                onCurrentValueChanged: {
                    if (_calibrationDialog.mayPickFirst() && currentValue)
                        _calibrationDialog.shownSlug = String(currentValue)
                }
                // The list can finish loading after a card preselected a device.
                // A device shown or waited for that isn't in it is kept, not
                // swapped for the first one.
                onCountChanged: {
                    if (count === 0)
                        return
                    if (indexOfValue(_calibrationDialog.shownSlug) >= 0)
                        _calibrationDialog.syncSelection()
                    else if (_calibrationDialog.mayPickFirst() && currentValue)
                        _calibrationDialog.shownSlug = String(currentValue)
                    else if (_calibrationDialog.shownSlug.length)
                        currentIndex = -1
                }
            }

            // Undo and Redo for the axes' changes (until the device changes),
            // with the last change beside them (01 S143).
            UndoBar {
                objectName: "calibrationUndoBar"
                Layout.fillWidth: true
                Layout.leftMargin: Style.dp(12)
                // _calib is made with the list below, after these buttons.
                canUndo: _calib ? _calib.canUndo : false
                canRedo: _calib ? _calib.canRedo : false
                undoTip: "Undo (Ctrl+Z)"
                redoTip: "Redo (Ctrl+Y)"
                lastChange: _calibrationDialog.lastChangeText
                undone: _calibrationDialog.undoneText
                onUndo: _calibrationDialog.undoEdit()
                onRedo: _calibrationDialog.redoEdit()
            }

            // This module's saved changes (Tools > History).
            Button {
                objectName: "calibrationHistory"
                text: "History"
                focusPolicy: Qt.NoFocus
                enabled: _moduleSelection.currentText.length > 0
                // By the module's own file: twin sticks share a name.
                onClicked: Helpers.createComponent("DialogHistory.qml", {
                    filter: JSON.stringify({ fileName: String(_moduleSelection.currentValue) + ".json" }),
                    filterLabel: _moduleSelection.currentText
                })
            }

            // Every axis with unsaved changes at once (each axis also has its own).
            Button {
                text: "Save All"
                enabled: _calibrationDialog.anyUnsaved
                onClicked: {
                    var why = _calib.saveAllRefusedReason()
                    var ok = !why && _calib.saveAll()
                    var where = ok && _calib.moduleFilePath ? _calib.moduleFilePath() : ""
                    _calibrationDialog.report(ok, ok ? "Saved every axis to the module file."
                                              : (why || "Not written. It is still only on this screen."))
                    if (backend)
                        backend.noteSave(ok ? ("Saved the calibration to " + where)
                                            : "The calibration was not written.")
                    _calibrationDialog.refreshUnsaved()
                }
            }
        }

        // 01 S142: what Save and Save All did.
        MessageLine {
            id: _message
            objectName: "calibrationMessage"
            Layout.fillWidth: true
            Layout.rightMargin: Style.dp(10)
            Layout.bottomMargin: visible ? Style.dp(8) : 0
        }

        EmptyState {
            objectName: "calibrationNoModule"
            visible: _modules && _modules.moduleCount === 0
            text: "No connected input module."
            Layout.fillWidth: true
        }

        EmptyState {
            objectName: "calibrationNotConnected"
            visible: _modules && _axisView
                    && _modules.moduleCount > 0
                    && _calibrationDialog.shownSlug.length > 0
                    && _axisView.count === 0
            text: "This input module is not connected."
            Layout.fillWidth: true
        }

        JGListView {
            id: _axisView

            scrollbarAlwaysVisible: true
            spacing: Style.dp(10)
            Layout.fillWidth: true
            Layout.fillHeight: true

            model: AxisCalibration {
                id: _calib
                moduleSlug: _calibrationDialog.shownSlug
            }

            delegate: CalibrationItem {
                width: ListView.view.width
            }
        }
    }


    component CalibrationItem : ColumnLayout {

        // Specify all properties we need from the model
        required property int index
        required property string identifier
        required property int calibratedValue
        required property int rawValue
        required property int low
        required property int centerLow
        required property int centerHigh
        required property int high
        required property bool withCenter
        required property bool unsavedChanges
        required property bool claimed
        required property var model

        // Display axis name and current raw value and axis type
        RowLayout {
            Layout.rightMargin: Style.dp(20)

            JGText {
                Layout.fillWidth: true

                // Every axis is listed; one the module doesn't claim is marked.
                text: claimed ? identifier : identifier + " (not claimed)"
                wrapMode: Text.Wrap
            }

            JGText {
                Layout.preferredWidth: Style.dp(75)
                Layout.rightMargin: Style.dp(5)

                text: "Raw"
                horizontalAlignment: Text.AlignRight
            }

            JGTextField {
                Layout.preferredWidth: Style.dp(100)

                text: rawValue
            }

            JGText {
                Layout.preferredWidth: Style.dp(100)

                text: "With center"
                horizontalAlignment: Text.AlignRight
            }
            Switch {
                Layout.preferredWidth: Style.dp(100)

                text: checked ? "Yes" : "No"
                checked: model.withCenter
                onToggled: {
                    model.withCenter = checked
                    _calibrationDialog.noteChange(index, checked ? "With center on" : "With center off")
                }
            }
        }


        RowLayout {

            Layout.rightMargin: Style.dp(20)

            // Show live axis sliders and calibration values
            ColumnLayout {
                Layout.fillWidth: true

                BetterProgressBar {
                    id: _progressRaw

                    Layout.preferredHeight: Style.dp(30)
                    Layout.fillWidth: true

                    value: rawValue
                    from: -32768
                    to: 32767
                }
                BetterProgressBar {
                    id: _progressCalibrated

                    Layout.preferredHeight: Style.dp(30)
                    Layout.fillWidth: true

                    value: calibratedValue
                    from: -32768
                    to: 32767
                }

                Rectangle {
                    Layout.fillHeight: true
                }

                // Show calibration values
                RowLayout {
                    CalibrationSpinBox {
                        id: _sbLow

                        value: low
                        from: -32768
                        to: _sbCLow.value

                        onValueModified: {
                            model.low = Qt.binding(() => value)
                            _calibrationDialog.noteChange(index, "lowest value")
                        }
                    }
                    LayoutHorizontalSpacer {
                    }
                    CalibrationSpinBox {
                        id: _sbCLow

                        visible: model.withCenter
                        value: centerLow
                        from: _sbLow.value
                        to: _sbCHigh.value

                        onValueModified: {
                            model.centerLow = Qt.binding(() => value)
                            _calibrationDialog.noteChange(index, "center")
                        }
                    }
                    CalibrationSpinBox {
                        id: _sbCHigh

                        visible: model.withCenter
                        value: centerHigh
                        from: _sbCLow.value
                        to: _sbHigh.value

                        onValueModified: {
                            model.centerHigh = Qt.binding(() => value)
                            _calibrationDialog.noteChange(index, "center")
                        }
                    }
                    LayoutHorizontalSpacer {
                    }
                    CalibrationSpinBox {
                        id: _sbHigh

                        value: high
                        from: _sbCHigh.value
                        to: 32767

                        onValueModified: {
                            model.high = Qt.binding(() => value)
                            _calibrationDialog.noteChange(index, "highest value")
                        }
                    }
                }
            }

            // Buttons to control calibration
            ColumnLayout {
                Layout.preferredWidth: Style.dp(150)
                Layout.alignment: Qt.AlignBottom

                RowLayout {
                    Button {
                        Layout.fillWidth: true

                        text: bsi.icons.reload
                        font.family: Style.iconFont
                        font.pixelSize: Style.dp(20)
                        font.bold: true

                        onClicked: () => {
                            _axisView.model.reset(index)
                            _calibrationDialog.noteChange(index, "reset")
                        }
                    }
                    Button {
                        Layout.fillWidth: true

                        text: bsi.icons.save
                        font.pixelSize: Style.dp(20)
                        font.family: Style.iconFont
                        font.bold: true

                        onClicked: {
                            var why = _axisView.model.saveRefusedReason(index)
                            var ok = !why && _axisView.model.save(index)
                            var where = ok && _axisView.model.moduleFilePath ? _axisView.model.moduleFilePath() : ""
                            _calibrationDialog.report(ok,
                                ok ? "Saved to the module file."
                                   : (why || "Not written. It is still only on this screen."))
                            if (backend)
                                backend.noteSave(ok
                                    ? ("Saved the calibration to " + where)
                                    : "The calibration was not written.")
                        }

                        // A gold ring, so the save icon stays visible.
                        Rectangle {
                            anchors.fill: parent
                            color: "transparent"
                            border.width: Style.dp(2)
                            border.color: unsavedChanges ? "gold" : "transparent"
                        }
                    }
                }
                Label {
                    // Always takes its space; showing it must not move the controls
                    // below (the next click would land on the gap above the arrows).
                    opacity: unsavedChanges ? 1 : 0
                    text: "Not saved"
                    color: Style.warn
                    font.pixelSize: Style.dp(11)
                }

                Button {
                    id: _btnCenterCalibration

                    Layout.preferredWidth: Style.dp(150)
                    text: "Calibrate Center"
                    visible: model.withCenter

                    checkable: true
                    // One calibration at a time: turn the other one off for real,
                    // not only its button (setting checked doesn't run onToggled).
                    onToggled: () => {
                        if (checked && _btnExtremaCalibration.checked) {
                            _btnExtremaCalibration.checked = false
                            _axisView.model.calibrateExtrema(index, false)
                        }
                        _axisView.model.calibrateCenter(index, checked)
                        if (checked)
                            _calibrationDialog.noteChange(index, "Calibrate Center")
                    }
                }
                LayoutVerticalSpacer {
                    visible: !model.withCenter
                }
                Button {
                    id: _btnExtremaCalibration

                    Layout.preferredWidth: Style.dp(150)
                    text: "Calibrate Extrema"

                    checkable: true
                    onToggled: {
                        if (checked && _btnCenterCalibration.checked) {
                            _btnCenterCalibration.checked = false
                            _axisView.model.calibrateCenter(index, false)
                        }
                        _axisView.model.calibrateExtrema(index, checked)
                        if (checked)
                            _calibrationDialog.noteChange(index, "Calibrate Extrema")
                    }
                }
                // Undo or Redo stopped this axis's capture: the buttons follow.
                Connections {
                    target: _axisView.model
                    function onCaptureStopped(axis) {
                        if (axis !== index)
                            return
                        _btnCenterCalibration.checked = false
                        _btnExtremaCalibration.checked = false
                    }
                }
            }
        }

        // Spacer at the bottom to leave some empty space below the ListView
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: Style.dp(10)
        }
    }

    component CalibrationSpinBox : JGSpinBox {
        from: -32768
        to: 32767
        value: 0
    }

    DismissibleDialog {
        id: _saveGate
        onSaveChosen: {
            var why = _calib.saveAllRefusedReason()
            if (why || !_calib.saveAll()) {
                _calibrationDialog.report(false, why || "Not written. It is still only on this screen.")
                if (backend)
                    backend.noteSave("The calibration was not written.")
                return
            }
            if (backend && _calib.moduleFilePath)
                backend.noteSave("Saved the calibration to " + _calib.moduleFilePath())
            _calibrationDialog.finishLeave()
        }
        onDiscardChosen: {
            _calib.discard()
            _calibrationDialog.finishLeave()
        }
        onCancelled: _calibrationDialog.pendingSlug = ""
    }
}
