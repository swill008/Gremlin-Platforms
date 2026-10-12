// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQml
import QtQuick.Controls
import QtQuick.Layouts
import Gremlin.Style

// The Device Mapping Editor's Properties panel: the selected item's exact place,
// size, angle and style (rig_props.js lists the fields). Type a number and
// press Enter, click a value, or click a colour to open the colour picker.
// A picture also has its Look: sliders for brightness, contrast, greyscale
// and opacity, and a Reset Picture button.
// A locked item's fields show but do not change.
Rectangle {
    id: _panel

    property var ed: null
    readonly property var model: (ed && ed.propsModel) ? ed.propsModel() : ({ title: "", locked: false, fields: [] })
    readonly property real rowH: Style.dp(26)
    readonly property int textPx: Style.dp(13)

    signal closeRequested()

    color: Style.bgCard
    border.color: Style.lineStrong
    border.width: 1
    radius: Style.dp(8)
    implicitHeight: _column.implicitHeight + Style.dp(12)

    // Keeps clicks and the wheel off the map underneath.
    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.AllButtons
        onWheel: (w) => { w.accepted = true }
    }

    ColumnLayout {
        id: _column
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: Style.dp(6)
        spacing: Style.dp(2)

        RowLayout {
            Layout.fillWidth: true
            Label {
                Layout.fillWidth: true
                text: "Properties"
                font.pixelSize: _panel.textPx
                font.bold: true
                color: Style.fgStrong
            }
            Label {
                text: "×"
                font.pixelSize: Style.dp(16)
                color: _closeArea.containsMouse ? Style.fgStrong : Style.fgMuted
                MouseArea {
                    id: _closeArea
                    anchors.fill: parent
                    anchors.margins: -Style.dp(4)
                    hoverEnabled: true
                    onClicked: _panel.closeRequested()
                }
            }
        }
        Label {
            Layout.fillWidth: true
            text: _panel.model.title + (_panel.model.locked ? "  (locked)" : "")
            font.pixelSize: _panel.textPx
            color: Style.fgSoft
            elide: Text.ElideRight
        }

        Repeater {
            id: _repeater
            model: _panel.model.fields
            delegate: RowLayout {
                id: _row
                required property var modelData
                readonly property var field: modelData
                Layout.fillWidth: true
                Layout.minimumHeight: _panel.rowH
                spacing: Style.dp(4)
                enabled: !_panel.model.locked
                // The link button hangs down to the Height row: keep it on top.
                z: _row.field.key === "w" ? 1 : 0

                // A heading (a picture's Look) is its title only.
                Label {
                    visible: _row.field.kind !== "button"
                    Layout.preferredWidth: _row.field.kind === "heading" ? -1 : Style.dp(86)
                    Layout.topMargin: _row.field.kind === "heading" ? Style.dp(4) : 0
                    text: _row.field.label
                    font.pixelSize: _panel.textPx
                    font.bold: _row.field.kind === "heading"
                    color: !_row.enabled ? Style.fgDisabled
                           : (_row.field.kind === "heading" ? Style.fgStrong : Style.fgSoft)
                    elide: Text.ElideRight
                }

                // A number: type it and press Enter (or leave the box).
                TextField {
                    id: _num
                    visible: _row.field.kind === "number"
                    Layout.preferredWidth: Style.dp(72)
                    Layout.preferredHeight: _panel.rowH
                    topPadding: 0
                    bottomPadding: 0
                    font.pixelSize: _panel.textPx
                    text: _row.field.kind === "number" ? "" + _row.field.value : ""
                    selectByMouse: true
                    validator: DoubleValidator {
                        bottom: _row.field.min !== undefined ? _row.field.min : -1e9
                        top: _row.field.max !== undefined ? _row.field.max : 1e9
                        notation: DoubleValidator.StandardNotation
                    }
                    // Enter, Esc or a click outside (01 S134) all end here; a
                    // box left unchanged (or already applied by Enter) sets nothing.
                    onEditingFinished: {
                        var key = _row.field.key
                        var v = Number(text)
                        if (v === v && v !== Number(_row.field.value))
                            _panel.ed.setProp(key, v)
                    }
                }
                Label {
                    visible: _row.field.kind === "number"
                    text: _row.field.suffix || ""
                    font.pixelSize: _panel.textPx
                    color: Style.fgSoft
                }

                // Width and Height linked (07 S155): on by default; with it
                // on, changing one scales the other at the item's ratio. The
                // icon sits between the Width and Height rows.
                Item {
                    visible: _row.field.key === "w"
                    Layout.preferredWidth: Style.dp(22)
                    Layout.preferredHeight: _panel.rowH
                    Label {
                        id: _link
                        objectName: "propLinkSize"
                        readonly property bool on: !!(_panel.ed && _panel.ed.linkSize)
                        width: parent.width
                        height: _panel.rowH
                        y: _panel.rowH / 2 + Style.dp(1)
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        text: ""
                        font.family: Style.iconFont
                        font.pixelSize: Style.dp(13)
                        color: !_row.enabled ? Style.fgDisabled
                             : (on ? Style.accent : (_linkArea.containsMouse ? Style.fg : Style.fgMuted))
                        MouseArea {
                            id: _linkArea
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: if (_panel.ed) _panel.ed.linkSize = !_panel.ed.linkSize
                        }
                        ToolTip.visible: _linkArea.containsMouse
                        ToolTip.text: "Keep proportions"
                    }
                }

                // A slider (a picture's Look): applied as it moves; a run
                // of moves is one Undo step.
                Slider {
                    id: _slider
                    objectName: "propSlider_" + _row.field.key
                    visible: _row.field.kind === "slider"
                    Layout.fillWidth: true
                    Layout.preferredHeight: _panel.rowH
                    from: _row.field.kind === "slider" ? _row.field.min : 0
                    to: _row.field.kind === "slider" ? _row.field.max : 1
                    stepSize: _row.field.step || 1
                    value: _row.field.kind === "slider" ? _row.field.value : 0
                    onMoved: _panel.ed.setProp(_row.field.key, Math.round(value))
                }
                Label {
                    visible: _row.field.kind === "slider"
                    Layout.preferredWidth: Style.dp(40)
                    horizontalAlignment: Text.AlignRight
                    text: _row.field.kind === "slider" ? Math.round(_slider.value) + (_row.field.suffix || "") : ""
                    font.pixelSize: _panel.textPx - Style.dp(1)
                    color: Style.fgSoft
                }

                // A choice: the values as small buttons.
                Flow {
                    visible: _row.field.kind === "choice"
                    Layout.fillWidth: true
                    spacing: Style.dp(3)
                    Repeater {
                        model: _row.field.kind === "choice" ? _row.field.options : []
                        delegate: Rectangle {
                            required property var modelData
                            readonly property bool on: _row.field.value === modelData.value
                            implicitWidth: _optText.implicitWidth + Style.dp(10)
                            implicitHeight: _panel.rowH - Style.dp(4)
                            radius: Style.dp(4)
                            color: on ? Style.accent : (_optArea.containsMouse ? Style.bgSelected : Style.clear)
                            border.color: on ? Style.accent : Style.line
                            Label {
                                id: _optText
                                anchors.centerIn: parent
                                text: modelData.text
                                font.pixelSize: _panel.textPx - Style.dp(1)
                                color: parent.on ? Style.onColor : Style.fg
                            }
                            MouseArea {
                                id: _optArea
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: _panel.ed.setProp(_row.field.key, modelData.value)
                            }
                        }
                    }
                }

                // A button (Reset Picture): runs the field's key.
                Button {
                    objectName: "propButton_" + _row.field.key
                    visible: _row.field.kind === "button"
                    enabled: _row.field.kind === "button" && !!_row.field.enabled
                    Layout.preferredHeight: _panel.rowH
                    text: _row.field.kind === "button" ? _row.field.label : ""
                    font.pixelSize: _panel.textPx - Style.dp(1)
                    onClicked: _panel.ed.setProp(_row.field.key, "")
                }

                // A colour: its swatch and hex; click to open the picker.
                Rectangle {
                    visible: _row.field.kind === "colour"
                    Layout.preferredWidth: Style.dp(22)
                    Layout.preferredHeight: Style.dp(18)
                    radius: Style.dp(3)
                    color: _row.field.kind === "colour" ? _row.field.value : Style.clear
                    border.color: Style.lineStrong
                    MouseArea {
                        anchors.fill: parent
                        onClicked: _panel.ed.setProp(_row.field.key, "")
                    }
                }
                Label {
                    visible: _row.field.kind === "colour"
                    text: _row.field.kind === "colour" ? String(_row.field.value).toUpperCase() : ""
                    font.pixelSize: _panel.textPx - Style.dp(1)
                    color: Style.fgMuted
                }
                Item { Layout.fillWidth: _row.field.kind !== "choice" && _row.field.kind !== "slider" }
            }
        }
    }

    // Text lines of the fields, for tests.
    function describe() {
        var out = [model.title + (model.locked ? " (locked)" : "")]
        var f = model.fields
        for (var i = 0; i < f.length; i++) {
            var v = f[i].value
            if (f[i].kind === "heading" || f[i].kind === "button") {
                out.push(f[i].label)
                continue
            }
            out.push(f[i].label + ": " + (typeof v === "string" ? v : Math.round(v * 100) / 100) + (f[i].suffix || ""))
        }
        return out
    }

    // A field's number box, in window coordinates.
    function fieldRect(label) {
        for (var i = 0; i < _repeater.count; i++) {
            var row = _repeater.itemAt(i)
            if (row && row.field.label === label) {
                var box = row.children[1]
                var p = box.mapToItem(null, 0, 0)
                return { x: p.x, y: p.y, w: box.width, h: box.height }
            }
        }
        return null
    }
}
