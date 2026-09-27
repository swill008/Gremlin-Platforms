// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Style

Window {
    id: _calibrationDialog

    width: 850
    height: 600
    minimumWidth: 850
    minimumHeight: 600

    color: Style.background
    Universal.theme: Style.theme

    title: "Calibration"

    property string shownGuid: ""
    property string pendingGuid: ""
    property bool allowClose: false

    ToolWindowMemory {
        host: _calibrationDialog
        name: "calibration"
        defaultWidth: 850
        defaultHeight: 600
    }

    function chooseDevice(guid) {
        var next = guid ? String(guid) : ""
        if (!next.length || next === shownGuid)
            return
        if (_calib.hasUnsaved()) {
            pendingGuid = next
            var back = _deviceSelection.indexOfValue(shownGuid)
            if (back >= 0)
                _deviceSelection.currentIndex = back
            _saveGate.detail = "Calibration is not saved. Change device and it will be lost."
            _saveGate.ask()
            return
        }
        shownGuid = next
    }

    function finishLeave() {
        if (pendingGuid.length) {
            shownGuid = pendingGuid
            pendingGuid = ""
            var next = _deviceSelection.indexOfValue(shownGuid)
            if (next >= 0)
                _deviceSelection.currentIndex = next
            return
        }
        allowClose = true
        close()
    }

    onClosing: (close) => {
        if (!allowClose && _calib.hasUnsaved()) {
            close.accepted = false
            pendingGuid = ""
            _saveGate.detail = "Calibration is not saved. Close this window and it will be lost."
            _saveGate.ask()
            return
        }
        _axisView.model.destroy()
        _axisView.destroy()
        _deviceData.destroy()
        backend.resumeInputHighlighting()
    }

    Component.onCompleted: () => {
        backend.pauseInputHighlighting()
    }

    DeviceListModel {
        id: _deviceData

        deviceType: "physical"
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.bottomMargin: 58
        anchors.leftMargin: 10

        RowLayout {
            Layout.bottomMargin: 15

            Label {
                Layout.preferredWidth: 150
                text: "Device to calibrate"
            }

            ComboBox {
                id: _deviceSelection

                model: _deviceData
                textRole: "name"
                valueRole: "guid"
                implicitContentWidthPolicy: ComboBox.WidestText
                onActivated: _calibrationDialog.chooseDevice(currentValue)
                onCurrentValueChanged: {
                    if (!_calibrationDialog.shownGuid.length && currentValue)
                        _calibrationDialog.shownGuid = String(currentValue)
                }
            }
        }

        JGListView {
            id: _axisView

            scrollbarAlwaysVisible: true
            spacing: 10
            Layout.fillWidth: true
            Layout.fillHeight: true

            model: AxisCalibration {
                id: _calib
                guid: _calibrationDialog.shownGuid
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
            Layout.rightMargin: 20

            JGText {
                Layout.fillWidth: true

                text: identifier
                wrapMode: Text.Wrap
            }

            JGText {
                Layout.preferredWidth: 75
                Layout.rightMargin: 5

                text: "Raw"
                horizontalAlignment: Text.AlignRight
            }

            JGTextField {
                Layout.preferredWidth: 100

                text: rawValue
            }

            JGText {
                Layout.preferredWidth: 100

                text: "With center"
                horizontalAlignment: Text.AlignRight
            }
            Switch {
                Layout.preferredWidth: 100

                text: checked ? "Yes" : "No"
                checked: model.withCenter
                onToggled: {
                    model.withCenter = checked
                }
            }
        }


        RowLayout {

            Layout.rightMargin: 20

            // Show live axis sliders and calibration values
            ColumnLayout {
                Layout.fillWidth: true

                BetterProgressBar {
                    id: _progressRaw

                    Layout.preferredHeight: 30
                    Layout.fillWidth: true

                    value: rawValue
                    from: -32768
                    to: 32767
                }
                BetterProgressBar {
                    id: _progressCalibrated

                    Layout.preferredHeight: 30
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
                Layout.preferredWidth: 150
                Layout.alignment: Qt.AlignBottom

                RowLayout {
                    Button {
                        Layout.fillWidth: true

                        text: bsi.icons.reload
                        font.family: "bootstrap-icons"
                        font.pixelSize: 20
                        font.bold: true

                        onClicked: () => _axisView.model.reset(index)
                    }
                    Button {
                        Layout.fillWidth: true

                        text: bsi.icons.save
                        font.pixelSize: 20
                        font.family: "bootstrap-icons"
                        font.bold: true

                        onClicked: {
                            var ok = _axisView.model.save(index)
                            _saveGate.announce(ok,
                                ok ? "Calibration was written to the configuration file."
                                   : "Calibration was not written.")
                        }

                        Rectangle {
                            anchors.fill: parent
                            color: unsavedChanges ? "gold" : "transparent"
                        }
                    }
                }

                Button {
                    id: _btnCenterCalibration

                    Layout.preferredWidth: 150
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

                    Layout.preferredWidth: 150
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
            Layout.preferredHeight: 10
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
                _saveGate.announce(false, "Calibration was not written.")
                return
            }
            _calibrationDialog.finishLeave()
        }
        onDiscardChosen: {
            _calib.discard()
            _calibrationDialog.finishLeave()
        }
        onCancelled: _calibrationDialog.pendingGuid = ""
    }

    DebugFileLine {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
    }
}
