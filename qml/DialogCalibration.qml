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
    minimumWidth: Style.dp(850)
    minimumHeight: Style.dp(600)

    color: Style.background
    U.Universal.theme: Style.theme

    title: "Calibration"

    property string shownSlug: ""
    property string pendingSlug: ""
    property string initialSlug: ""
    property bool allowClose: false

    ToolWindowMemory {
        host: _calibrationDialog
        name: "calibration"
        defaultWidth: Style.dp(850)
        defaultHeight: Style.dp(600)
    }

    function chooseModule(slug) {
        var next = slug ? String(slug) : ""
        if (!next.length || next === shownSlug)
            return
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
        backend.resumeInputHighlighting()
    }

    property bool _ready: false

    Component.onCompleted: () => {
        _ready = true
        backend.pauseInputHighlighting()
        if (initialSlug.length)
            chooseModule(initialSlug)
    }

    onInitialSlugChanged: {
        if (_ready && initialSlug.length)
            chooseModule(initialSlug)
    }

    CalibrationModuleModel {
        id: _modules
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
            }
        }

        Label {
            visible: _modules && _modules.moduleCount === 0
            text: "No connected input module."
            color: "#A1A1AA"
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Label {
            visible: _modules && _axisView
                    && _modules.moduleCount > 0
                    && _calibrationDialog.shownSlug.length > 0
                    && _axisView.count === 0
            text: "This input module is not connected."
            color: "#A1A1AA"
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
                        font.family: "bootstrap-icons"
                        font.pixelSize: Style.dp(20)
                        font.bold: true

                        onClicked: () => _axisView.model.reset(index)
                    }
                    Button {
                        Layout.fillWidth: true

                        text: bsi.icons.save
                        font.pixelSize: Style.dp(20)
                        font.family: "bootstrap-icons"
                        font.bold: true

                        onClicked: {
                            var ok = _axisView.model.save(index)
                            var where = ok && _axisView.model.moduleFilePath ? _axisView.model.moduleFilePath() : ""
                            _saveGate.announce(ok,
                                ok ? "Saved to the module file."
                                   : "Not written. It is still only on this screen.")
                            if (backend)
                                backend.noteSave(ok
                                    ? ("Saved the calibration to " + where)
                                    : "The calibration was not written.")
                        }

                        Rectangle {
                            anchors.fill: parent
                            color: unsavedChanges ? "gold" : "transparent"
                        }
                    }
                }
                Label {
                    visible: unsavedChanges
                    text: "Not saved"
                    color: "#FBBF24"
                    font.pixelSize: Style.dp(11)
                }

                Button {
                    id: _btnCenterCalibration

                    Layout.preferredWidth: Style.dp(150)
                    text: "Calibrate center"
                    visible: model.withCenter

                    checkable: true
                    onToggled: () => {
                        _axisView.model.calibrateCenter(index, checked)
                        _btnExtremaCalibration.checked = false
                    }
                }
                LayoutVerticalSpacer {
                    visible: !model.withCenter
                }
                Button {
                    id: _btnExtremaCalibration

                    Layout.preferredWidth: Style.dp(150)
                    text: "Calibrate extrema"

                    checkable: true
                    onToggled: {
                        _axisView.model.calibrateExtrema(index, checked)
                        _btnCenterCalibration.checked = false
                    }
                }
            }
        }

        // Spacer at the bottom to leave some empty space below the ListView
        Rectangle {
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
            if (!_calib.saveAll()) {
                _saveGate.announce(false, "Not written. It is still only on this screen.")
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
