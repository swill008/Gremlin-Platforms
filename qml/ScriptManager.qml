// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Script

import "helpers.js" as Helpers
import "confirm.js" as Confirm
import Gremlin.Style


// The Scripts window's content (DialogScripts.qml; 04 S84-S89, S96): the
// profile's scripts in a card like the Options rows with Add Script under
// it on the left, the picked script's variables in a second card on the
// right. The window gives the heading; this fills the pane it is put in.
Item {
    id: _root

    // The script whose variables the second card shows.
    property string shownPath: ""
    property string shownName: ""

    property ScriptListModel scriptListModel : backend ? backend.scriptListModel : null

    // Own copy of the icon names: this sits in a window of its own, away
    // from Main.qml's bsi.
    BootstrapIcons {
        id: bsi
        resource: "qrc:///BootstrapIcons"
    }

    // Picks a script to add; opens in the last folder used for scripts (01 S143).
    FilePicker {
        id: _selectScript

        kind: "script"
        mode: "open"
        title: "Add Script"

        acceptLabel: "Load"
        defaultSuffix: "py"
        nameFilters: ["Script files (*.py)"]
        folder: backend ? backend.scriptsFolderUrl() : ""

        onPicked: (file) => scriptListModel.addScript(file)
    }

    // Dialog to rename a script
    TextInputDialog {
        id: _renameScriptDialog

        visible: false
        allowBlank: false
        width: Style.dp(300)

        property var callback: null

        onAccepted: function(value)
        {
            callback(value)
            visible = false
        }
    }

    // Left: the scripts and Add Script; right: the picked script's
    // variables (user 2026-11-23, 2a). Each side scrolls on its own.
    RowLayout {
        anchors.fill: parent
        spacing: 0

        ScrollView {
            id: _listScroll

            objectName: "scriptsListPane"
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredWidth: 1
            contentWidth: availableWidth
            clip: true

            ColumnLayout {
                width: _listScroll.availableWidth - Style.dp(30)
                x: Style.dp(20)
                spacing: Style.dp(4)

                Label {
                    Layout.fillWidth: true
                    Layout.topMargin: Style.dp(14)
                    wrapMode: Text.WordWrap
                    color: Style.fgMuted
                    font.pixelSize: Style.dp(12)
                    text: "Scripts are Python files that run with the profile. They can react to "
                        + "inputs and do what actions can't. Add one with Add Script."
                }

                Label {
                    Layout.topMargin: Style.dp(14)
                    text: "Scripts in this profile"
                    color: Style.fgMuted
                    font.pixelSize: Style.dp(12)
                }

                // The scripts: one row each, a divider between rows.
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: _rows.implicitHeight
                    radius: Style.dp(6)
                    color: Style.bgCard
                    border.color: Style.line
                    border.width: Style.dp(1)

                    ColumnLayout {
                        id: _rows

                        width: parent.width
                        spacing: 0

                        Label {
                            objectName: "scriptsEmpty"
                            Layout.fillWidth: true
                            Layout.margins: Style.dp(14)
                            visible: !_scripts.count
                            text: "No scripts yet."
                            color: Style.fgMuted
                            font.pixelSize: Style.dp(14)
                        }

                        Repeater {
                            id: _scripts

                            model: _root.scriptListModel
                            delegate: ScriptUI {
                                Layout.fillWidth: true
                            }
                        }
                    }
                }

                Button {
                    objectName: "scriptAddButton"
                    Layout.alignment: Qt.AlignLeft
                    Layout.topMargin: Style.dp(10)
                    Layout.bottomMargin: Style.dp(20)

                    text: "Add Script"

                    onClicked: () => _selectScript.open()
                }
            }
        }

        ScrollView {
            id: _varScroll

            objectName: "scriptVariablesPane"
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredWidth: 1
            contentWidth: availableWidth
            clip: true

            ColumnLayout {
                width: _varScroll.availableWidth - Style.dp(30)
                x: Style.dp(10)
                spacing: Style.dp(4)

                // The picked script's variables (its configure button).
                Label {
                    Layout.topMargin: Style.dp(14)
                    visible: _root.shownName !== ""
                    text: "Variables of " + _root.shownName
                    color: Style.fgMuted
                    font.pixelSize: Style.dp(12)
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.bottomMargin: Style.dp(20)
                    visible: _root.shownName !== ""
                    implicitHeight: _config.implicitHeight
                    radius: Style.dp(6)
                    color: Style.bgCard
                    border.color: Style.line
                    border.width: Style.dp(1)

                    ScriptConfiguration {
                        id: _config

                        objectName: "scriptVariables"
                        width: parent.width
                    }
                }
            }
        }
    }

    // One script: its icon, name and path (and why it can't load), then
    // rename, configure and remove on the right.
    component ScriptUI : Item {
        id: _item

        required property int index
        required property string path
        required property string name
        required property var variables
        // Why the script could not be loaded ("" when it loaded).
        required property string loadError
        // Its code is still starting (load and add don't wait for it).
        required property bool starting

        objectName: "scriptRow:" + name
        implicitHeight: _layout.implicitHeight + Style.dp(20)

        Rectangle {
            visible: _item.index > 0
            width: parent.width
            height: Style.dp(1)
            color: Style.line
        }

        RowLayout {
            id: _layout

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: Style.dp(14)
            anchors.rightMargin: Style.dp(14)
            spacing: Style.dp(12)

            Label {
                Layout.alignment: Qt.AlignTop
                text: bsi.icons.script
                font.family: Style.iconFont
                font.pixelSize: Style.dp(18)
                color: Style.fgSoft
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Style.dp(2)

                Label {
                    id: _name

                    objectName: "scriptName"
                    Layout.fillWidth: true
                    text: _item.name
                    color: Style.fgStrong
                    font.pixelSize: Style.dp(14)
                    elide: Text.ElideMiddle

                    ToolTip {
                        x: _hoverName.point.position.x - width / 2
                        y: _hoverName.point.position.y - height - Style.dp(8)
                        text: _name.text
                        visible: _hoverName.hovered && _name.truncated
                    }

                    HoverHandler {
                        id: _hoverName
                        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
                    }
                }

                Label {
                    id: _path

                    objectName: "scriptPath"
                    Layout.fillWidth: true
                    text: _item.path
                    color: Style.fgMuted
                    font.pixelSize: Style.dp(12)
                    elide: Text.ElideMiddle

                    ToolTip {
                        text: _path.text
                        visible: _hoverPath.hovered
                        x: _hoverPath.point.position.x - width / 2
                        y: _hoverPath.point.position.y - height - Style.dp(8)
                    }

                    HoverHandler {
                        id: _hoverPath
                        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
                    }
                }

                // 04 S29: why it can't load.
                Label {
                    objectName: "scriptLoadError"
                    Layout.fillWidth: true
                    visible: _item.loadError !== ""
                    text: "Can't load: " + _item.loadError + ". Fix the script; it is tried again at Run."
                    color: Style.error
                    font.pixelSize: Style.dp(12)
                    wrapMode: Text.Wrap
                }

                Label {
                    objectName: "scriptStarting"
                    Layout.fillWidth: true
                    visible: _item.starting
                    text: "Starting…"
                    color: Style.fgMuted
                    font.pixelSize: Style.dp(12)
                    wrapMode: Text.Wrap
                }
            }

            IconButton {
                objectName: "scriptRename"
                text: bsi.icons.edit

                onClicked: {
                    _renameScriptDialog.text = _item.name
                    _renameScriptDialog.callback = (value) => {
                        if (_root.shownPath === _item.path && _root.shownName === _item.name)
                            _root.shownName = value
                        scriptListModel.renameScript(_item.path, _item.name, value)
                    }
                    _renameScriptDialog.visible = true
                }
            }

            IconButton {
                objectName: "scriptConfigure"
                text: bsi.icons.configure
                enabled: _item.loadError === "" && !_item.starting

                onClicked: {
                    _config.model = _item.variables
                    _root.shownPath = _item.path
                    _root.shownName = _item.name
                }
            }

            IconButton {
                objectName: "scriptRemove"
                text: bsi.icons.trash

                onClicked: () => {
                    var p = _item.path
                    var n = _item.name
                    // 04 S85, 01 S140: the shared question.
                    Confirm.ask(_root, {
                        title: "Remove script " + n + "?",
                        text: "It leaves this profile with its settings here."
                            + " The script file itself is not deleted.",
                        undoable: false,
                        action: "Remove Script",
                        onAccept: function() {
                            if (_root.shownPath === p && _root.shownName === n) {
                                _config.model = []
                                _root.shownPath = ""
                                _root.shownName = ""
                            }
                            scriptListModel.removeScript(p, n)
                        }
                    })
                }
            }
        }
    }
}
