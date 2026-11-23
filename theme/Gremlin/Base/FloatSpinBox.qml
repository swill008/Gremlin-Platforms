// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import Gremlin.Style


Item {
    id: _root

    // Set the SpinBox component to use with the FloatSpinBox.
    property Component spinboxComponent: _defaultSpinboxComponent

    property real minValue: -10.0
    property real maxValue: 10.0
    property real stepSize: 0.1
    property real value: 0.0
    property int decimals: 2
    property bool _internalUpdate: false

    readonly property int decimalFactor: Math.pow(10, _root.decimals)

    signal valueModified(real value)

    implicitWidth: _textMetrics.boundingRect.width + Style.dp(10) + (
        _loader.item ? _loader.item.leftPadding + _loader.item.rightPadding : 0)
    implicitHeight: _loader.implicitHeight

    function toFloat(value) {
        return value / decimalFactor
    }

    function toInt(value) {
        return Math.round(value * decimalFactor)
    }

    Component {
        id: _defaultSpinboxComponent
        SpinBox {}
    }

    Loader {
        id: _loader
        anchors.fill: parent
        sourceComponent: _root.spinboxComponent

        onLoaded: () => {
            item.editable = true

            item.validator = Qt.createQmlObject(
                "import QtQuick; DoubleValidator { " +
                    "decimals: " + _root.decimals + "; " +
                    "notation: DoubleValidator.StandardNotation " +
                "}",
                _loader
            )
            _root._applyLimits()

            // Set conversion functions before value so the initial displayText
            // is formatted correctly (setting value triggers displayText to
            // re-evaluate textFromValue, which must already be the custom one).
            item.textFromValue = (value, locale) => {
                return Number(value / decimalFactor)
                    .toLocaleString(locale, "f", _root.decimals)
            }

            item.valueFromText = (text, locale) => {
                return Math.round(
                    Number.fromLocaleString(locale, text) * decimalFactor)
            }

            // Setting textFromValue doesn't redraw the shown text, and
            // setting the value it already has (0) doesn't either: "0"
            // showed instead of "0.00" (04 S98). Step off the value once
            // so the text is drawn with the format above.
            var start = toInt(_root.value)
            item.value = start + 1 <= item.to ? start + 1 : start - 1
            item.value = start

            item.valueChanged.connect(() => {
                if (_root._internalUpdate)
                    return
                var next = toFloat(item.value)
                // Same number means the inner box echoed the bound value.
                // Assigning here would remove the caller's binding.
                if (Math.abs(next - _root.value) < (0.5 / decimalFactor))
                    return
                _root.valueModified(next)
            })
        }
    }

    // Limits can follow other values (a lower bound that must stay below an
    // upper one), so re-apply them whenever they change, not only at load.
    function _applyLimits() {
        var box = _loader.item
        if (!box)
            return
        box.from = toInt(minValue)
        box.to = toInt(maxValue)
        box.stepSize = toInt(stepSize)
        if (box.validator) {
            box.validator.bottom = toInt(minValue)
            box.validator.top = toInt(maxValue)
        }
    }

    onMinValueChanged: _applyLimits()
    onMaxValueChanged: _applyLimits()
    onStepSizeChanged: _applyLimits()
    onDecimalsChanged: _applyLimits()

    onValueChanged: () => {
        if (_loader.item && !_root._internalUpdate) {
            _internalUpdate = true
            _loader.item.value = toInt(value)
            Qt.callLater(() => { _internalUpdate = false })
        }
    }

    TextMetrics {
        id: _textMetrics

        font: _loader.item ? _loader.item.font : font
        text: (() => {
            let low = _root.minValue.toFixed(_root.decimals)
            let high = _root.maxValue.toFixed(_root.decimals)
            return low.length > high.length ? low : high
        })()
    }
}
