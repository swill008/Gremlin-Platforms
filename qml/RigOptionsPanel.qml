// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Device
import Gremlin.Style

// Device Map Options as a pane (the Options tool, or Edit > Device Map
// Options...): the groups down the left, the chosen group's settings on the
// right in two columns, one row each (a switch, a choice, a number box or
// a color swatch; a long label goes onto more lines); each setting's
// description on its (i). Changes apply and are kept at once. Library
// lists the saved styles and templates. The divider between the groups and
// the settings drags; the group list starts as wide as its longest name.
Item {
    id: _panel

    // The window's DeviceMapOptions.
    property var opts: null
    // The print area color: the window opens its color picker.
    signal colorRequested(string key, string hex, var anchor)

    readonly property string group: opts ? opts.paneGroup : "labels"
    readonly property var shown: {
        if (!opts)
            return []
        var g = group
        return opts.entries.filter(function(e) { return e.group === g })
    }
    readonly property int columns: _settings.width >= Style.dp(560) ? 2 : 1

    // --- the group list's width (D-FIXLIST-B1) -----------------------------
    // A name's room: its text plus the padding either side.
    function _nameW(title) {
        return Math.ceil(_fm.advanceWidth(title)) + 2 * Style.dp(12)
    }
    // As wide as the longest group name, at any UI scale.
    readonly property real fitW: {
        var w = Style.dp(60)
        var gs = opts ? opts.groups : []
        for (var i = 0; i < gs.length; i++)
            w = Math.max(w, _nameW(gs[i].title))
        return w
    }
    // The narrowest that still shows a short name; the widest is half the pane.
    readonly property real minW: _nameW("Labels")
    readonly property real maxW: Math.max(minW, width / 2)
    // The dragged width, logical px at 100% (0: fit the names; scaled by
    // uiScale, not dp(1), which rounds: 2 at 175%); read once
    // from the panel store, saved when a drag ends.
    property real keptW: 0
    function _readKept() {
        keptW = opts ? Number(opts.optionsGroupsWidth()) || 0 : 0
    }
    onOptsChanged: _readKept()
    Component.onCompleted: _readKept()
    readonly property real groupsW: {
        var w = keptW > 0 ? keptW * Style.uiScale / 100 : fitW
        // Before the pane has its size, keep the wanted width unclamped.
        return width > 0 ? Math.max(minW, Math.min(maxW, w)) : Math.max(minW, w)
    }

    // As wide as two columns of settings need (Library: its lists).
    readonly property real wantedW: group === "library"
        ? Style.dp(560)
        : groupsW + 1 + 2 * Style.dp(14) + 2 * Style.dp(320) + Style.dp(24)

    // The group names' font, for fitW.
    Label { id: _probe; visible: false; text: "M" }
    FontMetrics { id: _fm; font: _probe.font }
    // As tall as the group needs (Library: room for its lists).
    readonly property real wanted: group === "library"
        ? Style.dp(300)
        : Math.max(_groups.implicitHeight, _grid.implicitHeight) + 2 * Style.dp(12)

    RowLayout {
        anchors.fill: parent
        anchors.margins: Style.dp(1)
        spacing: 0

        // The groups.
        Column {
            id: _groups
            objectName: "optionsGroups"
            Layout.alignment: Qt.AlignTop
            Layout.preferredWidth: _panel.groupsW
            Layout.maximumWidth: _panel.groupsW
            topPadding: Style.dp(8)
            bottomPadding: Style.dp(8)
            Repeater {
                model: _panel.opts ? _panel.opts.groups : []
                delegate: Rectangle {
                    required property var modelData
                    readonly property bool current: _panel.group === modelData.key
                    objectName: "optionsGroup:" + modelData.key
                    width: _panel.groupsW
                    height: Style.dp(28)
                    color: current ? Style.bgSelected : (_groupArea.containsMouse ? Style.bgCard : Style.clear)
                    Rectangle {
                        visible: parent.current
                        width: Style.dp(3)
                        height: parent.height
                        color: Style.accent
                    }
                    Label {
                        anchors.verticalCenter: parent.verticalCenter
                        x: Style.dp(12)
                        width: parent.width - 2 * Style.dp(12)
                        elide: Text.ElideRight
                        text: modelData.title
                        color: parent.current ? Style.fg : Style.fgMuted
                    }
                    MouseArea {
                        id: _groupArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: _panel.opts.paneGroup = modelData.key
                    }
                }
            }
        }

        // The divider: drag it to widen or narrow the group list.
        Rectangle {
            // Over the settings beside it, so its grab area takes the press.
            z: 1
            Layout.fillHeight: true
            Layout.preferredWidth: 1
            color: _divArea.containsMouse || _divArea.pressed ? Style.accent : Style.line
            MouseArea {
                id: _divArea
                objectName: "optionsDivider"
                anchors.fill: parent
                anchors.leftMargin: -Style.dp(3)
                anchors.rightMargin: -Style.dp(3)
                hoverEnabled: true
                cursorShape: Qt.SplitHCursor
                preventStealing: true
                property real startX: 0
                property real startW: 0
                onPressed: (mouse) => {
                    startX = mapToItem(_panel, mouse.x, 0).x
                    startW = _panel.groupsW
                }
                onPositionChanged: (mouse) => {
                    if (!pressed)
                        return
                    var w = startW + mapToItem(_panel, mouse.x, 0).x - startX
                    w = Math.max(_panel.minW, Math.min(_panel.maxW, w))
                    _panel.keptW = w * 100 / Style.uiScale
                }
                onReleased: {
                    if (_panel.opts)
                        _panel.opts.setOptionsGroupsWidth(_panel.keptW)
                }
            }
        }

        // The chosen group's settings, or the Library.
        Flickable {
            id: _settings
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: width
            contentHeight: _panel.group === "library" ? _library.implicitHeight + 2 * Style.dp(12)
                                                      : _grid.implicitHeight + 2 * Style.dp(12)
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {
                policy: _settings.contentHeight > _settings.height ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
            }

            GridLayout {
                id: _grid
                visible: _panel.group !== "library"
                x: Style.dp(14)
                y: Style.dp(12)
                width: _settings.width - 2 * Style.dp(14)
                columns: _panel.columns
                columnSpacing: Style.dp(24)
                rowSpacing: Style.dp(10)

                Repeater {
                    model: _panel.shown
                    delegate: RowLayout {
                        id: _row
                        required property var modelData
                        readonly property var value: _panel.opts ? _panel.opts.values[modelData.key] : undefined
                        objectName: "option:" + modelData.key
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        spacing: Style.dp(6)

                        // Short of room it goes onto more lines, never cut;
                        // it and the list or number box share what is left.
                        Label {
                            text: _row.modelData.title
                            color: Style.fg
                            wrapMode: Text.Wrap
                            Layout.fillWidth: true
                            Layout.minimumWidth: Math.min(implicitWidth, Style.dp(64))
                        }
                        // The description, on hover.
                        Label {
                            text: "\uF431"
                            font.family: Style.iconFont
                            font.pixelSize: Style.dp(12)
                            color: _info.containsMouse ? Style.fg : Style.fgMuted
                            MouseArea {
                                id: _info
                                anchors.fill: parent
                                anchors.margins: -Style.dp(4)
                                hoverEnabled: true
                            }
                            ToolTip.visible: _info.containsMouse
                            ToolTip.text: _row.modelData.description
                        }

                        Switch {
                            visible: _row.modelData.kind === "bool"
                            checked: _row.value === true
                            onToggled: _panel.opts.set(_row.modelData.key, checked)
                        }
                        ComboBox {
                            visible: _row.modelData.kind === "choice"
                            Layout.preferredWidth: Style.dp(150)
                            Layout.minimumWidth: Style.dp(90)
                            Layout.fillWidth: true
                            Layout.maximumWidth: Style.dp(150)
                            model: _row.modelData.choices
                            currentIndex: Math.max(0, _row.modelData.choices.indexOf(String(_row.value)))
                            onActivated: (i) => _panel.opts.set(_row.modelData.key, _row.modelData.choices[i])
                        }
                        SpinBox {
                            visible: _row.modelData.kind === "int"
                            Layout.preferredWidth: Style.dp(130)
                            Layout.minimumWidth: Style.dp(120)
                            Layout.fillWidth: true
                            Layout.maximumWidth: Style.dp(130)
                            from: _row.modelData.min
                            to: _row.modelData.max
                            editable: true
                            value: Number(_row.value) || 0
                            onValueModified: _panel.opts.set(_row.modelData.key, value)
                        }
                        Rectangle {
                            id: _swatch
                            visible: _row.modelData.kind === "color"
                            implicitWidth: Style.dp(44)
                            implicitHeight: Style.dp(22)
                            radius: Style.dp(3)
                            color: /^#[0-9A-Fa-f]{6}$/.test(String(_row.value)) ? String(_row.value) : Style.dangerBright
                            border.color: Style.lineStrong
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: _panel.colorRequested(_row.modelData.key, String(_swatch.color), _swatch)
                            }
                        }
                        TextField {
                            visible: _row.modelData.kind === "text"
                            Layout.preferredWidth: Style.dp(150)
                            Layout.minimumWidth: Style.dp(90)
                            Layout.fillWidth: true
                            Layout.maximumWidth: Style.dp(150)
                            text: String(_row.value === undefined ? "" : _row.value)
                            onEditingFinished: _panel.opts.set(_row.modelData.key, text)
                        }
                    }
                }
            }

            OptionDeviceMapLibrary {
                id: _library
                visible: _panel.group === "library"
                x: Style.dp(14)
                y: Style.dp(12)
                width: _settings.width - 2 * Style.dp(14)
            }
        }
    }
}
