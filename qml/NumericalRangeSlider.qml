// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls

import Gremlin.Style

Item {
    id: _root

    property real from
    property real to
    property real firstValue
    property real secondValue
    property real stepSize
    property int decimals

    signal firstEdited(real value)
    signal secondEdited(real value)

    height: Math.max(_slider.height, _firstValue.height, _secondValue.height)
    width: _slider.width + _firstValue.width + _secondValue.width

    property var validator: DoubleValidator {
        bottom: Math.min(_root.from, _root.to)
        top:  Math.max(_root.from, _root.to)
    }

    function textFromValue(value) {
        return Number(value).toLocaleString(Qt.locale(), "f", _root.decimals)
    }

    function valueFromText(text) {
            return Number.fromLocaleString(Qt.locale(), text)
    }

    function _showFirst() {
        if (!_slider || !_firstValueInput)
            return
        if (!_firstValueInput.activeFocus)
            _firstValueInput.text = textFromValue(firstValue)
        if (Math.abs(_slider.first.value - firstValue) > 0.0000001)
            _slider.first.value = firstValue
    }

    function _showSecond() {
        if (!_slider || !_secondValueInput)
            return
        if (!_secondValueInput.activeFocus)
            _secondValueInput.text = textFromValue(secondValue)
        if (Math.abs(_slider.second.value - secondValue) > 0.0000001)
            _slider.second.value = secondValue
    }

    onFirstValueChanged: _showFirst()
    onSecondValueChanged: _showSecond()

    Component.onCompleted: {
        _slider.first.value = firstValue
        _slider.second.value = secondValue
        _firstValueInput.text = textFromValue(firstValue)
        _secondValueInput.text = textFromValue(secondValue)
    }


    Rectangle {
        id: _firstValue

        anchors.verticalCenter: _slider.verticalCenter

        border.color: Style.lowColor
        border.width: Style.dp(2)
        width: _firstValueInput.width
        height: _firstValueInput.height

        JGTextField {
            id: _firstValueInput

            padding: Style.dp(10)

            font: _slider.font
            horizontalAlignment: Qt.AlignHCenter
            verticalAlignment: Qt.AlignVCenter

            readOnly: false
            selectByMouse: true
            validator: _root.validator
            inputMethodHints: Qt.ImhFormattedNumbersOnly

            onTextEdited: () => {
                let value = valueFromText(text)
                if(value >= _root.secondValue) {
                    value = _root.secondValue
                }
                _root.firstEdited(value)
            }
        }
    }

    RangeSlider {
        id: _slider

        anchors.left: _firstValue.right

        from: _root.from
        to: _root.to
        stepSize: _root.stepSize

        first.onMoved: _root.firstEdited(first.value)
        second.onMoved: _root.secondEdited(second.value)
    }

    Rectangle {
        id: _secondValue

        anchors.left: _slider.right
        anchors.verticalCenter: _slider.verticalCenter

        border.color: Style.lowColor
        border.width: Style.dp(2)
        width: _secondValueInput.width
        height: _secondValueInput.height

        JGTextField {
            id: _secondValueInput

            padding: Style.dp(10)

            font: _slider.font
            horizontalAlignment: Qt.AlignHCenter
            verticalAlignment: Qt.AlignVCenter

            readOnly: false
            selectByMouse: true
            validator: _root.validator
            inputMethodHints: Qt.ImhFormattedNumbersOnly

            onTextEdited: () => {
                let value = valueFromText(text)
                if(value <= _root.firstValue) {
                    value = _root.firstValue
                }
                _root.secondEdited(value)
            }
        }
    }

}
