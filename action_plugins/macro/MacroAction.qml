// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window
import Qt.labs.qmlmodels

import Gremlin.ActionPlugins
import Gremlin.Base
import Gremlin.Compact as Compact
import Gremlin.Profile
import Gremlin.Style
import "../../qml"
import "../../qml/helpers.js" as Helpers


Item {
    id: _root

    property MacroModel action

    implicitHeight: _content.height

    ColumnLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right

        // Macro repeat configuration settings.
        RowLayout {
            Layout.fillWidth: true

            Label {
                Layout.preferredWidth: Style.dp(125)

                text: "<b>Repeat Mode</b>"
            }

            ComboBox {
                id: _repeatMode

                textRole: "text"
                valueRole: "value"

                Component.onCompleted: () => {
                    currentIndex = indexOfValue(_root.action.repeatMode)
                }

                onActivated: () => { _root.action.repeatMode = currentValue }

                model: [
                    {value: "single", text: "Single"},
                    {value: "count", text: "Count"},
                    {value: "toggle", text: "Toggle"},
                    {value: "hold", text: "Hold"},
                ]
            }

            Label {
                visible: ["count", "toggle", "hold"].includes(_repeatMode.currentValue)
                text: "Delay (sec)"
            }

            FloatSpinBox {
                visible: ["count", "toggle", "hold"].includes(_repeatMode.currentValue)

                value: _root.action.repeatDelay
                minValue: 0.0
                maxValue: 3600.0

                onValueModified: (newValue) => {
                    _root.action.repeatDelay = newValue
                }
            }

            Label {
                visible: _repeatMode.currentValue === "count"
                text: "Times"
            }

            JGSpinBox {
                visible: _repeatMode.currentValue === "count"

                value: _root.action.repeatCount
                from: 1
                to: 100

                onValueModified: () => { _root.action.repeatCount = value }
            }

            LayoutHorizontalSpacer {}

        }

        RowLayout {
            Layout.fillWidth: true

            Switch {
                text: "Exclusive"

                checked: _root.action.isExclusive
                onClicked: () => { _root.action.isExclusive = checked }
            }

            Switch {
                text: "Pre-Emptive"

                visible: _root.action.isExclusive
                checked: _root.action.isPreemptive
                onClicked: () => { _root.action.isPreemptive = checked }
            }
        }

        // Action recording configuration settings.
        RowLayout {
            Layout.fillWidth: true

            Label {
                Layout.preferredWidth: Style.dp(125)

                text: "<b>Record Inputs</b>"
            }

            CheckBox {
                text: "Keyboard"
                checked: _root.action.recordKeyboard
                onToggled: () => { _root.action.recordKeyboard = checked }
                enabled: !_root.action.isRecording
            }
            CheckBox {
                text: "Mouse"
                checked: _root.action.recordMouse
                onToggled: () => { _root.action.recordMouse = checked }
                enabled: !_root.action.isRecording
            }
            CheckBox {
                text: "Axis"
                checked: _root.action.recordJoystickAxis
                onToggled: () => { _root.action.recordJoystickAxis = checked }
                enabled: !_root.action.isRecording
            }
            CheckBox {
                text: "Button"
                checked: _root.action.recordJoystickButton
                onToggled: () => { _root.action.recordJoystickButton = checked }
                enabled: !_root.action.isRecording
            }
            CheckBox {
                text: "Hat"
                checked: _root.action.recordJoystickHat
                onToggled: () => { _root.action.recordJoystickHat = checked }
                enabled: !_root.action.isRecording
            }
            CheckBox {
                text: "Timings"
                checked: _root.action.recordTimings
                onToggled: () => { _root.action.recordTimings = checked }
                enabled: !_root.action.isRecording
            }

            LayoutHorizontalSpacer {}

            Compact.RecordButton {
                visible: !_root.action.isRecording
                description: "Start Recording"
                onClicked: () => { _root.action.startRecording() }
            }
            Compact.RecordButton {
                visible: _root.action.isRecording
                highlighted: true
                description: "Stop Recording"
                onPressed: () => { _root.action.stopRecording() }
            }
        }


        ActionDrop {
            targetIndex: 0
            insertionMode: "prepend"

            Layout.bottomMargin: -Style.dp(10)
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(_actionList.contentHeight, Style.dp(400))
            clip: true

            JGListView {
                id: _actionList

                width: parent.width
                spacing: Style.dp(2)
                scrollbarAlwaysVisible: true

                model: _root.action.actions
                delegate: _delegateChooser

                Connections {
                    target: _actionList.model

                    function onActionAdded() {
                        // Reposition the view at the bottom of the list when
                        // an action is added but not when deleted.
                        Qt.callLater(_actionList.positionViewAtEnd)
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: Style.dp(10)

            ComboBox {
                id: _macroAction

                Layout.preferredWidth: Style.dp(150)

                textRole: "text"
                valueRole: "value"

                model: [
                    {value: "joystick", text: "Joystick"},
                    {value: "key", text: "Keyboard"},
                    {value: "logical-device", text: "Logical Device"},
                    {value: "mouse-button", text: "Mouse Button"},
                    {value: "mouse-motion", text: "Mouse Motion"},
                    {value: "pause", text: "Pause"},
                    {value: "vjoy", text: "vJoy"}
                ]
            }

            Button {
                text: "Add Step"

                onClicked: () => {
                    _root.action.addAction(_macroAction.currentValue)
                }
            }

            LayoutHorizontalSpacer {}
        }
    }

    // Renders the correct delegate based on the action type
    DelegateChooser {
        id: _delegateChooser

        role: "actionType"

        // Joystick action.
        DelegateChoice {
            roleValue: "joystick"

            DraggableAction {
                icon_qrc: "qrc:/icons/physical_joystick"
                label: "Joystick"

                actionItem: RowLayout {
                    InputListener {
                        Layout.fillWidth: true

                        text: Helpers.safeText(
                            modelData.label, "Record Input"
                        )
                        callback: (inputs) => {
                            modelData.updateJoystick(inputs)
                        }
                        multipleInputs: false
                        eventTypes: ["axis", "button", "hat"]
                    }

                    // Show different components based on input
                    Compact.ButtonStateSelector {
                        visible: modelData.inputType === "button"

                        isPressed: modelData.isPressed
                        onStateModified: (isPressed) => {
                            modelData.isPressed = isPressed
                        }
                    }
                    Compact.FloatSpinBox {
                        visible: modelData.inputType === "axis"

                        minValue: -1.0
                        maxValue: 1.0
                        decimals: Style.decimalsPrecise
                        value: modelData.axisValue

                        onValueModified: (newValue) => {
                            modelData.axisValue = newValue
                        }
                    }
                    Compact.ComboBox {
                        visible: modelData.inputType === "hat"

                        textRole: "text"
                        valueRole: "value"

                        model: [
                            {value: "center", text: "Center"},
                            {value: "north", text: "North"},
                            {value: "north-east", text: "North East"},
                            {value: "east", text: "East"},
                            {value: "south-east", text: "South East"},
                            {value: "south", text: "South"},
                            {value: "south-west", text: "South West"},
                            {value: "west", text: "West"},
                            {value: "north-west", text: "North West"}
                        ]

                        Component.onCompleted: () => {
                            currentIndex = Qt.binding(
                                () => indexOfValue(modelData.hatDirection)
                            )
                        }

                        onActivated: function () {
                            modelData.hatDirection = currentValue
                        }
                    }
                }
            }
        }

        // Key action.
        DelegateChoice {
            roleValue: "key"

            DraggableAction {
                icon: bsi.icons.icon_keyboard
                label: "Keyboard"

                actionItem: RowLayout {
                    InputListener {
                        Layout.fillWidth: true

                        text: Helpers.safeText(
                            modelData.key, "Record Input"
                        )
                        callback: (inputs) => { modelData.updateKey(inputs) }
                        multipleInputs: false
                        eventTypes: ["key"]
                    }

                    Compact.ButtonStateSelector {
                        isPressed: modelData.isPressed
                        onStateModified: (isPressed) => {
                            modelData.isPressed = isPressed
                        }
                    }
                }
            }
        }

        // Logical device action.
        DelegateChoice {
            roleValue: "logical-device"

            DraggableAction {
                icon: bsi.icons.icon_logical_device
                label: "Logical device"

                actionItem: RowLayout {
                    LogicalDeviceSelector {
                        // The ordering is important, swapping it will result in the
                        // wrong item being displayed.
                        validTypes: ["axis", "button", "hat"]
                        logicalInputIdentifier: modelData.logicalInputIdentifier
                        useCompact: true

                        onLogicalInputIdentifierChanged: () => {
                            modelData.logicalInputIdentifier = logicalInputIdentifier
                        }
                    }

                    LayoutHorizontalSpacer {}

                    // Show different components based on input
                    Compact.ButtonStateSelector {
                        visible: modelData.inputType === "button"

                        isPressed: modelData.isPressed
                        onStateModified: (isPressed) => {
                            modelData.isPressed = isPressed
                        }
                    }
                    RowLayout {
                        visible: modelData.inputType === "axis"

                        Compact.FloatSpinBox {
                            minValue: -1.0
                            maxValue: 1.0
                            decimals: Style.decimalsPrecise
                            value: modelData.axisValue

                            onValueModified: (newValue) => {
                                modelData.axisValue = newValue
                            }
                        }

                        Compact.ComboBox {
                            model: ["Absolute", "Relative"]

                            Component.onCompleted: () => {
                                currentIndex = find(
                                    Helpers.capitalize(modelData.axisMode)
                                )
                            }

                            onActivated: () => {
                                modelData.axisMode = currentValue
                            }
                        }
                    }
                    Compact.ComboBox {
                        visible: modelData.inputType === "hat"

                        textRole: "text"
                        valueRole: "value"

                        model: [
                            {value: "center", text: "Center"},
                            {value: "north", text: "North"},
                            {value: "north-east", text: "North East"},
                            {value: "east", text: "East"},
                            {value: "south-east", text: "South East"},
                            {value: "south", text: "South"},
                            {value: "south-west", text: "South West"},
                            {value: "west", text: "West"},
                            {value: "north-west", text: "North West"}
                        ]

                        currentIndex: indexOfValue(modelData.hatDirection)
                        Component.onCompleted: () => {
                            currentIndex = Qt.binding(
                                () => {return indexOfValue(modelData.hatDirection)}
                            )
                        }

                        onActivated: () => {
                            modelData.hatDirection = currentValue
                        }
                    }
                }
            }
        }

        // Mouse button.
        DelegateChoice {
            roleValue: "mouse-button"

            DraggableAction {
                icon: bsi.icons.icon_mouse
                label: "Mouse Button"

                actionItem: RowLayout {
                    InputListener {
                        Layout.fillWidth: true

                        text: Helpers.safeText(
                            modelData.button, "Record Input"
                        )
                        callback: (inputs) => { modelData.updateButton(inputs) }
                        multipleInputs: false
                        eventTypes: ["mouse"]
                    }

                    LayoutHorizontalSpacer {}

                    Compact.ButtonStateSelector {
                        isPressed: modelData.isPressed
                        onStateModified: (isPressed) => {
                            modelData.isPressed = isPressed
                        }
                    }
                }
            }
        }

        // Mouse motion.
        DelegateChoice {
            roleValue: "mouse-motion"

            DraggableAction {
                icon: bsi.icons.icon_mouse
                label: "Mouse Motion"

                actionItem: RowLayout {
                    Label {
                        Layout.leftMargin: Style.dp(5)

                        text: "X-Axis"
                    }
                    Compact.SpinBox {
                        from: -10000
                        to: 10000
                        stepSize: 5
                        value: modelData.dx

                        onValueModified: () => { modelData.dx = value }
                    }

                    Label {
                        text: "Y-Axis"

                        leftPadding: Style.dp(25)
                    }
                    Compact.SpinBox {
                        from: -10000
                        to: 10000
                        stepSize: 5
                        value: modelData.dy

                        onValueModified: () => { modelData.dy = value }
                    }

                    LayoutHorizontalSpacer {}
                }
            }
        }

        // Pause action.
        DelegateChoice {
            roleValue: "pause"

            DraggableAction {
                icon: bsi.icons.icon_pause
                label: "Pause"

                actionItem: RowLayout {
                    Compact.FloatSpinBox {
                        minValue: 0.0
                        maxValue: 10.0
                        value: modelData.duration

                        onValueModified: (newValue) => {
                            modelData.duration = newValue
                        }
                    }
                    Label {
                        text: "seconds"
                    }
                    LayoutHorizontalSpacer {}
                }
            }
        }

        // vJoy action.
        DelegateChoice {
            roleValue: "vjoy"

            DraggableAction {
                icon: bsi.icons.icon_joystick
                label: "vJoy"

                actionItem: RowLayout {
                    VJoySelector {
                        Layout.alignment: Qt.AlignTop

                        validTypes: ["axis", "button", "hat"]
                        useCompact: true

                        onSelectionChanged: (vjoyId, inputType, inputId) => {
                            modelData.vjoyId = vjoyId
                            modelData.inputType = inputType
                            modelData.inputId = inputId
                        }

                        Component.onCompleted: () => {
                            initialize(
                                modelData.vjoyId,
                                modelData.inputType,
                                modelData.inputId
                            )
                        }
                    }

                    LayoutHorizontalSpacer {}

                    // Show different components based on input.
                    Compact.ButtonStateSelector {
                        visible: modelData.inputType === "button"

                        isPressed: modelData.isPressed
                        onStateModified: (isPressed) => {
                            modelData.isPressed = isPressed
                        }
                    }
                    ColumnLayout {
                        visible: modelData.inputType === "axis"

                        Compact.FloatSpinBox {
                            minValue: -1.0
                            maxValue: 1.0
                            decimals: Style.decimalsPrecise
                            value: modelData.axisValue

                            onValueModified: (newValue) => {
                                modelData.axisValue = newValue
                            }
                        }

                        Compact.ComboBox {
                            model: ["Absolute", "Relative"]

                            Component.onCompleted: () => {
                                currentIndex = find(
                                    Helpers.capitalize(modelData.axisMode)
                                )
                            }

                            onActivated: () => {
                                modelData.axisMode = currentValue
                            }
                        }
                    }
                    Compact.ComboBox {
                        visible: modelData.inputType === "hat"

                        textRole: "text"
                        valueRole: "value"

                        model: [
                            {value: "center", text: "Center"},
                            {value: "north", text: "North"},
                            {value: "north-east", text: "North East"},
                            {value: "east", text: "East"},
                            {value: "south-east", text: "South East"},
                            {value: "south", text: "South"},
                            {value: "south-west", text: "South West"},
                            {value: "west", text: "West"},
                            {value: "north-west", text: "North West"}
                        ]

                        currentIndex: indexOfValue(modelData.hatDirection)
                        Component.onCompleted: () => {
                            currentIndex = Qt.binding(
                                () => {return indexOfValue(modelData.hatDirection)}
                            )
                        }

                        onActivated: () => {
                            modelData.hatDirection = currentValue
                        }
                    }
                }
            }
        }
    }

    // Predefined button that removes a given action.
    component DeleteButton : IconButton {
        text: bsi.icons.remove
        font.pixelSize: Style.dp(16)

        onClicked: () => { _root.action.removeAction(index) }
    }

    // Displays an icon and also acts as the drag handle for the drag&drop
    // implementation.
    component Icon : Item {
        property string iconName: ""
        property string iconSource: ""
        property string label: ""
        property var target

        property alias dragActive: _dragArea.drag.active

        implicitWidth: _iconRow.implicitWidth
        implicitHeight: _iconRow.implicitHeight

        Row {
            id: _iconRow

            Label {
                text: bsi.icons.drag_handle
                font.family: Style.iconFont
                font.pixelSize: Style.dp(16)
            }
            Label {
                visible: iconName !== ""
                text: iconName
                font.family: Style.iconFont
                font.pixelSize: Style.dp(16)
            }
            Image {
                visible: iconSource !== ""
                source: iconSource
                width: Style.dp(16)
                height: Style.dp(16)
                fillMode: Image.PreserveAspectFit
            }
        }

        MouseArea {
            id: _dragArea

            anchors.fill: parent

            drag.target: target
            drag.axis: Drag.YAxis

            // Create a visualization of the dragged item.
            onPressed: () => {
                parent.parent.grabToImage(function(result) {
                    target.Drag.imageSource = result.url
                })
            }
        }

        HoverHandler {
            id: _iconHover
        }

        ToolTip {
            visible: _iconHover.hovered && label !== ""
            text: label
            delay: 500
        }
    }

    component ActionDrop : DropArea {
        property int targetIndex
        property string insertionMode: "append"

        height: Style.dp(8)

        Layout.fillWidth: true

        onDropped: (drop) => {
            drop.accept()
            _marker.opacity = 0.0
            _root.action.dropCallback(targetIndex, drop.text, insertionMode)
        }

        onEntered: () => { _marker.opacity = 1.0 }
        onExited: () => { _marker.opacity = 0.0 }

        Rectangle {
            anchors.fill: parent
            color: "transparent"

            Rectangle {
                id: _marker

                y: parent.y+Style.dp(5)
                height: Style.dp(10)
                anchors.left: parent.left
                anchors.right: parent.right

                opacity: 0.0
                color: Style.accent
            }
        }
    }

    component DraggableAction : ColumnLayout {
        id: _draggableAction

        // Widget properties.
        property string icon: ""
        property string icon_qrc: ""
        property string label: ""
        property alias actionItem: _actionLoader.sourceComponent

        // Ensure entire width is taken up.
        width: ListView.view ? ListView.view.width : 0
        spacing: Style.dp(1)

        // Define drag&drop behavior.
        Drag.dragType: Drag.Automatic
        Drag.active: _icon.dragActive
        Drag.supportedActions: Qt.MoveAction
        Drag.proposedAction: Qt.MoveAction
        Drag.mimeData: {
            "text/plain": index.toString()
        }
        Drag.onDragFinished: function (action) {
            // If the drop action ought to be ignored, reset the UI by calling
            // the InputConfiguration.qml reload function.
            if (action === Qt.IgnoreAction) {
                reload();
            }
        }

        // Widget content assembly.
        RowLayout {
            id: _actionContent
            spacing: Style.dp(4)

            Icon {
                id: _icon

                Layout.alignment: Qt.AlignVCenter
                Layout.rightMargin: Style.dp(10)

                iconName: icon
                iconSource: icon_qrc
                label: _draggableAction.label
                target: _draggableAction
            }

            // Holds action specific UI elements.
            Loader {
                id: _actionLoader

                Layout.alignment: Qt.AlignTop | Qt.AlignLeft
                Layout.fillWidth: true
            }

            LayoutHorizontalSpacer {}

            DeleteButton {
                Layout.rightMargin: Style.dp(10)
            }
        }

        ActionDrop {
            Layout.bottomMargin: -Style.dp(4)
            Layout.topMargin: -Style.dp(4)

            targetIndex: index
        }
    }

}
