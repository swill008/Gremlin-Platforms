// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

import QtQuick.Controls.Universal as U
import QtQuick.Shapes
import Qt.labs.qmlmodels

import QtCharts

import Gremlin.ActionPlugins
import Gremlin.Base
import Gremlin.Profile
import Gremlin.Style
import "../../qml"

import "render_helpers.js" as RH


Item {
    id: _root

    property ResponseCurveModel action
    property Deadzone deadzone: action.deadzone
    property alias widgetSize : _vis.size
    readonly property int handleOffset: Style.dp(5)

    implicitHeight: _content.height

    focus: true
    Keys.onDeletePressed: () => {
        action.removeControlPoint(action.selectedPoint)
    }

    function map2u(x) {
        return RH.x2u(x, _curve.x, _vis.size, handleOffset)
    }

    function map2v(y) {
        return RH.y2v(y, _curve.x, _vis.size, handleOffset)
    }

    function map2x(u, du) {
        return RH.u2x(
            du === null ? u : u + du - handleOffset,
            handleOffset,
            _vis.size
        )
    }
    function map2y(v, dv) {
        return RH.v2y(
            dv === null ? v : v + dv - handleOffset,
            handleOffset,
            _vis.size
        )
    }

    function updateControlPoint(cp_handle, evt, index) {
        let new_x = RH.clamp(map2x(cp_handle.x, evt.x), -1.0, 1.0)
        let new_y = RH.clamp(map2y(cp_handle.y, evt.y ), -1.0, 1.0)

        // Ensure the points at either end cannot be moved away from the edge
        if (index === 0) {
            new_x = -1.0
        }
        if (index === action.controlPoints.length - 1) {
            new_x = 1.0
        }

        // In symmetry mode moving the center point, if there is one is
        // not allowed
        if (_root.action.isSymmetric && _repeater.count % 2 !== 0 &&
            index * 2 + 1 === _repeater.count)
        {
            return null
        }

        // Prevent moving control point past neighoring ones
        let new_u = RH.clamp(map2u(new_x), -handleOffset, _vis.size + handleOffset)
        let new_v = RH.clamp(map2v(new_y), -handleOffset, _vis.size + handleOffset)

        let left = _repeater.itemAt(index - 1)
        let right = _repeater.itemAt(index + 1)
        if (left && left.item.x > new_u) {
            new_u = cp_handle.x
            new_x = map2x(cp_handle.x, null)
        }
        if (right && right.item.x < new_u) {
            new_u = cp_handle.x
            new_x = map2x(cp_handle.x, null)
        }

        // Move the actual marker
        cp_handle.x = new_u
        cp_handle.y = new_v

        // Handle symmetry mode, no need to update model as
        // the code does this behind the scenes with the
        // model update below
        if (_root.action.isSymmetric) {
            let mirror = _repeater.itemAt(_repeater.count - index - 1).item
            mirror.x = map2u(-new_x, null)
            mirror.y = map2v(-new_y, null)

        }

        // Return the computed new [x, y] coordinates in [-1, 1] to use on the
        // model side of things
        return [new_x, new_y]
    }

    ColumnLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right

        // Various controls to configure curve editing
        RowLayout {
            Layout.fillWidth: true

            ComboBox {
                Layout.preferredWidth: Style.dp(200)

                model: ["Piecewise Linear", "Cubic Spline", "Cubic Bezier Spline"]

                Component.onCompleted: () => {
                    currentIndex = find(_root.action.curveType)
                }
                onActivated: () => { _root.action.curveType = currentText }
            }

            Button {
                text: "Invert Curve"

                onClicked: () => { _root.action.invertCurve() }
            }

            CheckBox {
                text: "Symmetric"
                property bool shown: _root.action.isSymmetric
                onShownChanged: if (!pressed) checked = shown
                Component.onCompleted: checked = shown
                onClicked: _root.action.isSymmetric = checked
            }
        }

        // Response curve widget
        RowLayout {
            Layout.preferredWidth: Style.dp(475)

            Item {
                id: _vis

                property int size: Style.dp(450)
                property int border: Style.dp(2)

                Component.onCompleted: () => { action.setWidgetSize(size) }
                onSizeChanged: action.setWidgetSize(size)

                width: size + 2 * border
                height: size + 2 * border

                // Display the background image.
                Image {
                    width: _vis.size
                    height: _vis.size
                    x: _vis.border
                    y: _vis.border
                    source: Style.isDarkMode ? "grid_dark.svg" : "grid.svg"

                    Rectangle {
                        anchors.fill: parent
                        color: "transparent"
                        border.color: Style.foreground
                        border.width: Style.dp(1)
                    }
                }

                // Render the response curve itself without interactive elements.
                Shape {
                    id: _curve

                    width: _vis.size
                    height: _vis.size

                    anchors.centerIn: parent

                    preferredRendererType: Shape.CurveRenderer

                    ShapePath {
                        strokeColor: "#808080"

                        strokeWidth: Style.dp(2)
                        fillColor: "transparent"

                        PathPolyline {
                            path: action.linePoints
                        }
                    }

                    MouseArea {
                        anchors.fill: parent

                        onDoubleClicked: (evt) => {
                            action.addControlPoint(
                                2 * (evt.x / width) - 1,
                                -2 * (evt.y / height) + 1
                            )
                        }
                    }
                }

                // Render the individual control elements.
                Repeater {
                    id: _repeater

                    model: action.controlPoints

                    delegate: Component {
                        // Pick the correct control visualization to load and pass
                        // the repeater reference in.
                        Loader {
                            Component.onCompleted: () => {
                                let url = modelData.hasHandles ? "HandleControl.qml" : "PointControl.qml"
                                setSource(
                                    url,
                                    {
                                        "repeater": _repeater,
                                        "focusTarget": _root
                                    }
                                )
                            }
                        }
                    }
                }
            }

            GridLayout {
                columns: 2

                Label {
                    Layout.preferredWidth: Style.dp(30)

                    text: "X"
                }

                FloatSpinBox {
                    id: _coordX

                    minValue: -1.0
                    maxValue: 1.0
                    stepSize: 0.05
                    decimals: Style.decimalsPrecise
                    value: {
                        const _selected = _root.action.selectedPoint
                        return _root.action.selectedPointCoord.x
                    }

                    onValueModified: (newValue) => {
                        _root.action.updateSelectedPoint(newValue, _coordY.value)
                    }
                }

                Label {
                    text: "Y"
                }

                FloatSpinBox {
                    id: _coordY

                    minValue: -1.0
                    maxValue: 1.0
                    stepSize: 0.05
                    decimals: Style.decimalsPrecise
                    value: {
                        const _selected = _root.action.selectedPoint
                        return _root.action.selectedPointCoord.y
                    }

                    onValueModified: (newValue) => {
                        _root.action.updateSelectedPoint(_coordX.value, newValue)
                    }
                }
            }
        }

        Label {
            text: "Deadzone"
        }

        RowLayout {
            // Lower half axis.
            NumericalRangeSlider {
                id: _lowerDeadzone

                from: -1.0
                to: 0.0
                firstValue: deadzone.low
                secondValue: deadzone.centerLow
                stepSize: 0.05
                decimals: 3

                onFirstEdited: (value) => { deadzone.low = value }
                onSecondEdited: (value) => { deadzone.centerLow = value }
            }

            // Upper half axis.
            NumericalRangeSlider {
                id: _upperDeadzone

                from: 0.0
                to: 1.0
                firstValue: deadzone.centerHigh
                secondValue: deadzone.high
                stepSize: 0.05
                decimals: 3

                onFirstEdited: (value) => { deadzone.centerHigh = value }
                onSecondEdited: (value) => { deadzone.high = value }
            }
        }
    }
}
