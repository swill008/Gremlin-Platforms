// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls

import Gremlin.Device
import Gremlin.Style

Button {
    id: _control

    property bool selected: false
    property Component deleteButton: null
    property Component editButton: null
    property string nameKey: ""
    property string defaultName: name
    property var liveState: null
    property bool runtimeActive: false
    property int liveIndex: index
    property int liveStamp: liveState && liveState.stamp !== undefined ? liveState.stamp : 0
    property string inputKind: liveStamp >= 0 && liveState && liveIndex !== undefined ? liveState.kindAt(liveIndex) : ""
    property real liveValue: liveStamp >= 0 && liveState && liveIndex !== undefined ? liveState.valueAt(liveIndex) : 0

    readonly property bool _buttonActive: inputKind === "button" && liveValue > 0.5
    readonly property bool _hatActive: inputKind === "hat" && liveValue > 0.5
    readonly property bool _axisActive: inputKind === "axis"
    readonly property bool _outputScreen: !!(liveState && liveState.liveWhileActive)
    readonly property bool _showLive: {
        liveStamp
        if (!_outputScreen)
            return true
        return runtimeActive && !!(liveState && liveState.driven)
    }
    readonly property bool _ledOn: _showLive && (_buttonActive || _hatActive)

    signal renameRequested()

    property int _descriptionWidth: 0
    property int _actionWidth: 0
    property bool _actionTruncated: false

    Connections {
        target: _control

        function onWidthChanged() {
            updateWidths()
        }
    }

    Connections {
        target: signal

        function onInputItemChanged(itemIndex) {
            if (itemIndex === liveIndex) {
                delayedUpdate.start()
            }
        }
    }

    Component.onCompleted: () => { updateWidths() }

    Timer {
        id: delayedUpdate
        interval: 50
        repeat: false
        onTriggered: updateWidths()
    }

    function updateWidths() {
        let imageWidth = _actionSequenceFull.item ? _actionSequenceFull.item.sourceSize.width : 0
        let widths = computeWidths(imageWidth, _inputDescription.text)

        _actionTruncated = widths[1] < imageWidth
        _descriptionWidth = widths[0]
        _actionWidth = widths[1]
    }

    function computeWidths(imageWidth, text) {
        let descriptionWidth = 0
        let actionWidth = 0

        let countWidth = Style.dp(15)
        let spacing = Style.dp(30)
        let textPadding = Style.dp(10)

        if (text.length == 0) {
            actionWidth = Math.min(_control.width, imageWidth)
        }
        else if (actionSequenceDisplayMode === "Count") {
            descriptionWidth = _control.width - countWidth - spacing
            actionWidth = countWidth
        }
        else {
            _textMetrics.text = text
            let textWidth = _textMetrics.width + textPadding

            let actionLimit = _control.width * 0.3
            let textLimit = _control.width * 0.7 - spacing

            if (imageWidth < actionLimit) {
                actionWidth = imageWidth
                descriptionWidth = Math.min(textWidth, _control.width - actionWidth - spacing)
            }
            else if (textWidth < textLimit) {
                descriptionWidth = textWidth + spacing
                actionWidth = Math.min(imageWidth, _control.width - descriptionWidth)
            }
            else {
                actionWidth = actionLimit
                descriptionWidth = textLimit
            }
        }

        return [descriptionWidth, actionWidth]
    }

    background: Rectangle {
        border.color: hovered ? Style.accent : selected ? Style.accent : Style.backgroundShade
        border.width: _ledOn ? Style.dp(2) : Style.dp(1)
        color: {
            if (_ledOn) {
                return Qt.rgba(0.133, 0.773, 0.369, selected ? 0.55 : 0.38)
            }
            if (selected) {
                return (Style.isDarkMode ? Universal.chromeMediumColor : Style._light.bar)
            }
            return Style.background
        }

        Rectangle {
            visible: _axisActive
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.leftMargin: Style.dp(1)
            anchors.rightMargin: Style.dp(1)
            anchors.bottomMargin: Style.dp(1)
            height: Style.dp(5)
            color: Style.lowColor

            Rectangle {
                width: _showLive
                       ? Math.max(0, Math.min(parent.width, parent.width * ((liveValue + 1.0) * 0.5)))
                       : 0
                height: parent.height
                color: Style.ok
            }
        }
    }

    contentItem: Item {
        Rectangle {
            id: _led
            visible: !_axisActive
            width: Style.dp(10)
            height: Style.dp(10)
            radius: Style.dp(5)
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.topMargin: Style.dp(4)
            color: _ledOn ? Style.ok : Style.lowColor
            border.width: Style.dp(1)
            border.color: _ledOn ? Style.okStrong : Style.medColor
        }

        JGText {
            id: _inputLabel
            text: name
            font.weight: 600

            width: Math.min(implicitWidth, parent.width - Style.dp(48))
            elide: Text.ElideRight

            anchors.top: parent.top
            anchors.left: _axisActive ? parent.left : _led.right
            anchors.leftMargin: _axisActive ? 0 : Style.dp(8)
        }

        Loader {
            sourceComponent: _control.editButton

            anchors.top: parent.top
            anchors.left: _inputLabel.right
            anchors.leftMargin: Style.dp(4)
        }

        Loader {
            active: actionSequenceDisplayMode === "Count"

            anchors.bottom: parent.bottom
            anchors.right: parent.right

            sourceComponent: Label {
                text: actionSequenceCount

                width: _actionWidth

                horizontalAlignment: Text.AlignRight
                verticalAlignment: Text.AlignVCenter
            }
        }

        Loader {
            id: _actionSequenceFull

            visible: actionSequenceDisplayMode === "Full"

            anchors.bottom: parent.bottom
            anchors.right: parent.right
            anchors.bottomMargin: _axisActive ? Style.dp(6) : 0

            sourceComponent: Image {
                // Drawn at the UI scale (s), so it is sharp at that size.
                source: "image://action_summary/" + actionSequenceDescriptor
                    + "?r=" + (uiState ? uiState.themeRevision : 0)
                    + "&s=" + Style.uiScale
                asynchronous: false
                cache: false
                clip: true

                width: _actionWidth
                height: sourceSize.height

                fillMode: Image.Pad
                horizontalAlignment: Image.AlignLeft

                // A new scale or theme gives a new width.
                onSourceSizeChanged: delayedUpdate.start()
            }
        }

        JGText {
            id: _inputDescription
            text: description
            font.italic: true

            width: _descriptionWidth
            elide: Text.ElideRight

            anchors.left: _axisActive ? parent.left : _led.right
            anchors.leftMargin: _axisActive ? 0 : Style.dp(8)
            anchors.bottom: parent.bottom
            anchors.bottomMargin: _axisActive ? Style.dp(6) : 0
        }

        TextMetrics {
            id: _textMetrics
            font: _inputDescription.font
        }

        Loader {
            sourceComponent: _control.deleteButton

            anchors.top: parent.top
            anchors.right: parent.right
        }
    }

    HoverHandler {
        id: _hover
    }

    TapHandler {
        acceptedButtons: Qt.LeftButton
        onDoubleTapped: _control.renameRequested()
    }

    ToolTip {
        visible: _hover.hovered && actionSequenceDisplayMode === "Full" && _actionTruncated
        delay: 400

        x: _hover.point.position.x - width / 2
        y: _hover.point.position.y - height - Style.dp(8)

        contentItem: Image {
            source: _actionSequenceFull.item ? _actionSequenceFull.item.source : ""
            fillMode: Image.PreserveAspectFit
            width: implicitWidth
            height: implicitHeight
        }
    }

}
