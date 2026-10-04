// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Style

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
    Connections {
        target: _calib
        function onDataChanged() { _calibrationDialog.refreshUnsaved() }
        function onModelReset() { _calibrationDialog.refreshUnsaved() }
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
        if (_moduleSelection.count > 0 && _moduleSelection.indexOfValue(next) < 0) {
            waitingSlug = next
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
        onModelReset: Qt.callLater(function() {
            if (_calibrationDialog.waitingSlug.length
                    && _moduleSelection.indexOfValue(_calibrationDialog.waitingSlug) >= 0
                    && _moduleSelection.indexOfValue(_calibrationDialog.shownSlug) < 0) {
                var slug = _calibrationDialog.waitingSlug
                _calibrationDialog.waitingSlug = ""
                _calibrationDialog.shownSlug = ""
                _calibrationDialog.chooseModule(slug)
                return
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

        RowLayout {
            Layout.bottomMargin: Style.dp(15)

            Label {
                Layout.preferredWidth: Style.dp(150)
                text: "Input module"
            }

            ComboBox {
                id: _moduleSelection

                model: _modules
                textRole: "name"
                valueRole: "slug"
                implicitContentWidthPolicy: ComboBox.WidestText
                onActivated: _calibrationDialog.chooseModule(currentValue)
                onCurrentValueChanged: {
                    if (!_calibrationDialog.shownSlug.length && currentValue)
                        _calibrationDialog.shownSlug = String(currentValue)
                }
                // The list can finish loading after a card preselected a device.
                onCountChanged: {
                    if (count === 0)
                        return
                    if (indexOfValue(_calibrationDialog.shownSlug) >= 0)
                        _calibrationDialog.syncSelection()
                    else if (currentValue)
                        _calibrationDialog.shownSlug = String(currentValue)
                }
            }

            Item { Layout.fillWidth: true }

            // Every axis with unsaved changes at once (each axis also has its own).
            Button {
                text: "Save All"
                enabled: _calibrationDialog.anyUnsaved
                onClicked: {
                    var why = _calib.saveAllRefusedReason()
                    var ok = !why && _calib.saveAll()
                    var where = ok && _calib.moduleFilePath ? _calib.moduleFilePath() : ""
                    _saveGate.announce(ok, ok ? "Saved every axis to the module file."
                                              : (why || "Not written. It is still only on this screen."))
                    if (backend)
                        backend.noteSave(ok ? ("Saved the calibration to " + where)
                                            : "The calibration was not written.")
                    _calibrationDialog.refreshUnsaved()
                }
            }
        }

        Label {
            visible: _modules && _modules.moduleCount === 0
            text: "No connected input module."
            color: Style.fgMuted
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Label {
            visible: _modules && _axisView
                    && _modules.moduleCount > 0
                    && _calibrationDialog.shownSlug.length > 0
                    && _axisView.count === 0
            text: "This input module is not connected."
            color: Style.fgMuted
            wrapMode: Text.WordWrap
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
        required property var model

        // Display axis name and current raw value and axis type
        RowLayout {
            Layout.rightMargin: Style.dp(20)

            JGText {
                Layout.fillWidth: true

                text: identifier
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

                        onValueModified: model.low = Qt.binding(() => value)
                    }
                    LayoutHorizontalSpacer {
                    }
                    CalibrationSpinBox {
                        id: _sbCLow

                        visible: model.withCenter
                        value: centerLow
                        from: _sbLow.value
                        to: _sbCHigh.value

                        onValueModified: model.centerLow = Qt.binding(() => value)
                    }
                    CalibrationSpinBox {
                        id: _sbCHigh

                        visible: model.withCenter
                        value: centerHigh
                        from: _sbCLow.value
                        to: _sbHigh.value

                        onValueModified: model.centerHigh = Qt.binding(() => value)
                    }
                    LayoutHorizontalSpacer {
                    }
                    CalibrationSpinBox {
                        id: _sbHigh

                        value: high
                        from: _sbCHigh.value
                        to: 32767

                        onValueModified: model.high = Qt.binding(() => value)
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

                        onClicked: () => _axisView.model.reset(index)
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
                            _saveGate.announce(ok,
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
                _saveGate.announce(false, why || "Not written. It is still only on this screen.")
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
