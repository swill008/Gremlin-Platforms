// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Config
import Gremlin.Style

import "confirm.js" as Confirm

// OSC Module Setup's "Output" tab (D-09-OSC-OUTPUT, D-09-OSC-TABS,
// D-09-OSC-COMPANION): OSC output, Reply to sender and the targets Send OSC
// and feedback send to, with Add Companion. Each change is written to OSC's
// file at once.
Flickable {
    id: _root
    objectName: "oscOutputTab"

    required property OscServerModel server

    clip: true
    contentWidth: width
    contentHeight: _column.implicitHeight + Style.dp(24)
    boundsBehavior: Flickable.StopAtBounds
    ScrollBar.vertical: ScrollBar {
        policy: _root.contentHeight > _root.height ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
    }

    // The Button Map's small outline button.
    component SmallButton: Rectangle {
        id: _small
        property alias text: _smallText.text
        readonly property alias hovered: _smallArea.containsMouse
        signal clicked()
        implicitWidth: _smallText.implicitWidth + Style.dp(14)
        implicitHeight: Style.dp(24)
        radius: Style.dp(4)
        color: _smallArea.containsMouse ? Style.bgSelected : Style.clear
        border.color: Style.line
        Label {
            id: _smallText
            anchors.centerIn: parent
            font.pixelSize: Style.dp(12)
            color: Style.fg
        }
        MouseArea {
            id: _smallArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: _small.clicked()
        }
    }

    ColumnLayout {
        id: _column
        x: Style.dp(14)
        y: Style.dp(12)
        width: _root.width - Style.dp(28)
        spacing: Style.dp(10)

        SectionHeading {
            text: "Output"
            Layout.fillWidth: true
        }

        CheckBox {
            objectName: "oscOutputEnabled"
            text: "OSC output (Send OSC actions and feedback)"
            checked: _root.server.outputEnabled
            onClicked: _root.server.setValue("output_enabled", checked)
        }

        CheckBox {
            objectName: "oscReplyToSender"
            text: "Reply to sender"
            checked: _root.server.replyToSender
            onClicked: _root.server.setValue("reply_to_sender", checked)
            PointerTip {
                text: "The \"Reply\" target sends to the computer the last "
                      + "OSC message came from."
                show: parent.hovered
            }
        }

        // The targets, in a card with its header row.
        Rectangle {
            Layout.fillWidth: true
            Layout.topMargin: Style.dp(8)
            color: Style.bgCard
            border.color: Style.lineStrong
            border.width: 1
            radius: Style.dp(8)
            implicitHeight: _targets.implicitHeight + Style.dp(16)

            ColumnLayout {
                id: _targets
                anchors {
                    left: parent.left
                    right: parent.right
                    top: parent.top
                    margins: Style.dp(8)
                }
                spacing: Style.dp(4)

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Style.dp(6)
                    Label {
                        text: "Targets"
                        font.pixelSize: Style.dp(13)
                        font.bold: true
                        color: Style.fgStrong
                        Layout.fillWidth: true
                    }
                    SmallButton {
                        objectName: "oscAddCompanion"
                        text: "Add Companion"
                        onClicked: _root.server.addCompanionTarget()
                        PointerTip {
                            text: "Adds the target \"Companion\" (127.0.0.1:12321), "
                                  + "Bitfocus Companion on this PC."
                            show: parent.hovered
                        }
                    }
                }

                EmptyState {
                    objectName: "oscTargetsEmpty"
                    visible: _root.server.targets.length === 0
                    text: "No targets yet. Add one below."
                    Layout.fillWidth: true
                }

                Repeater {
                    model: _root.server.targets
                    delegate: Rectangle {
                        id: _row
                        required property var modelData
                        required property int index
                        objectName: "oscTarget" + index
                        Layout.fillWidth: true
                        implicitHeight: Style.dp(34)
                        radius: Style.dp(4)
                        color: _rowHover.hovered ? Style.bgRaised : Style.clear
                        HoverHandler { id: _rowHover }

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Style.dp(6)
                            anchors.rightMargin: Style.dp(4)
                            spacing: Style.dp(6)
                            Label {
                                objectName: "oscTargetName" + _row.index
                                text: _row.modelData.name
                                font.bold: true
                                color: Style.fg
                                Layout.preferredWidth: Style.dp(140)
                                elide: Text.ElideRight
                            }
                            Label {
                                objectName: "oscTargetAddress" + _row.index
                                text: _row.modelData.host + ":" + _row.modelData.port
                                font.family: Style.monoFont
                                color: Style.fgMuted
                                Layout.fillWidth: true
                                elide: Text.ElideMiddle
                            }
                            Button {
                                objectName: "oscTargetEdit" + _row.index
                                text: "Edit"
                                implicitHeight: Style.dp(28)
                                onClicked: _targetForm.edit(_row.modelData)
                            }
                            DangerButton {
                                objectName: "oscTargetRemove" + _row.index
                                text: "Remove"
                                implicitHeight: Style.dp(28)
                                onClicked: {
                                    var target = _row.modelData
                                    Confirm.ask(_root, {
                                        title: "Remove target " + target.name + "?",
                                        text: "Send OSC actions and feedback rows that "
                                              + "use it will have no target.",
                                        undoable: true,
                                        action: "Remove",
                                        onAccept: function() {
                                            _root.server.removeTarget(target.id)
                                            if (_targetForm.editId === target.id)
                                                _targetForm.reset()
                                        }
                                    })
                                }
                            }
                        }
                    }
                }

                // Add a target, or change the one being edited.
                RowLayout {
                    id: _targetForm
                    property string editId: ""
                    spacing: Style.dp(6)
                    Layout.fillWidth: true
                    Layout.topMargin: Style.dp(4)

                    function edit(target) {
                        editId = target.id
                        _targetName.text = target.name
                        _targetHost.text = target.host
                        _targetPort.text = String(target.port)
                        _targetName.forceActiveFocus()
                    }
                    function reset() {
                        editId = ""
                        _targetName.text = ""
                        _targetHost.text = ""
                        _targetPort.text = "8000"
                    }
                    function submit() {
                        var done = editId.length
                            ? _root.server.editTarget(editId, _targetName.text,
                                                      _targetHost.text, _targetPort.text)
                            : _root.server.addTarget(_targetName.text, _targetHost.text,
                                                     _targetPort.text)
                        if (done)
                            reset()
                    }

                    JGTextField {
                        id: _targetName
                        objectName: "oscTargetNameField"
                        placeholderText: "Name"
                        selectByMouse: true
                        Layout.preferredWidth: Style.dp(140)
                        onAccepted: _targetForm.submit()
                    }
                    JGTextField {
                        id: _targetHost
                        objectName: "oscTargetHostField"
                        placeholderText: "IP address or computer name"
                        selectByMouse: true
                        Layout.fillWidth: true
                        onAccepted: _targetForm.submit()
                    }
                    JGTextField {
                        id: _targetPort
                        objectName: "oscTargetPortField"
                        text: "8000"
                        selectByMouse: true
                        inputMethodHints: Qt.ImhDigitsOnly
                        Layout.preferredWidth: Style.dp(90)
                        onAccepted: _targetForm.submit()
                    }
                    Button {
                        objectName: "oscTargetSave"
                        text: _targetForm.editId.length ? "Save Target" : "Add Target"
                        implicitHeight: Style.dp(28)
                        onClicked: _targetForm.submit()
                    }
                    Button {
                        objectName: "oscTargetCancel"
                        visible: _targetForm.editId.length > 0
                        text: "Cancel"
                        implicitHeight: Style.dp(28)
                        onClicked: _targetForm.reset()
                    }
                }
            }
        }
    }
}
