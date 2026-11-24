// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Script

import "helpers.js" as Helpers
import "confirm.js" as Confirm
import Gremlin.Style


// Options › Scripts (04 S84-S89, S96): the profile's scripts in a card like
// the Options rows with Add Script under it on the left, the picked script's
// variables in a second card on the right. Each side scrolls on its own;
// while Options searches it is as tall as its matching rows.
Item {
    id: _root
    objectName: "scriptManager"

    // The script whose variables the second card shows.
    property string shownPath: ""
    property string shownName: ""

    // Options' search: only the rows it matches show.
    property string filterText: ""
    readonly property bool searching: filterText.trim() !== ""
    readonly property string _groupText: "Scripts in this profile"
    readonly property bool _addFound: matches(
        _groupText + " Add Script " + _about.text)
    readonly property int _scriptsFound: {
        _scripts.revision
        var n = 0
        for (var i = 0; i < _scripts.count; i++) {
            var row = _scripts.itemAt(i)
            if (row && row.found)
                n++
        }
        return n
    }
    readonly property bool _variablesShown: shownName !== ""
        && (!searching || _config.searchFound > 0)
    readonly property int searchFound: _scriptsFound + (_addFound ? 1 : 0)
        + (shownName !== "" ? _config.searchFound : 0)

    function matches(text) {
        var needle = filterText.trim().toLowerCase()
        return needle === "" || String(text).toLowerCase().indexOf(needle) >= 0
    }

    implicitHeight: Math.max(_list.implicitHeight,
        _variablesShown ? _variables.implicitHeight : 0)

    property ScriptListModel scriptListModel : backend ? backend.scriptListModel : null

    // Own copy of the icon names: Options is away from Main.qml's bsi.
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
                id: _list

                width: _listScroll.availableWidth - Style.dp(10)
                spacing: Style.dp(4)

                Label {
                    id: _about

                    visible: _root._addFound
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
                    visible: !_root.searching || _root._scriptsFound > 0
                    text: _root._groupText
                    color: Style.fgMuted
                    font.pixelSize: Style.dp(12)
                }

                // The scripts: one row each, a divider between rows.
                Rectangle {
                    visible: !_root.searching || _root._scriptsFound > 0
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

                            // Goes up as rows come or go.
                            property int revision: 0
                            onItemAdded: revision++
                            onItemRemoved: revision++

                            // The first row that shows (no divider above it).
                            readonly property int firstFound: {
                                revision
                                for (var i = 0; i < count; i++) {
                                    var row = itemAt(i)
                                    if (row && row.found)
                                        return i
                                }
                                return -1
                            }

                            model: _root.scriptListModel
                            delegate: ScriptUI {
                                Layout.fillWidth: true
                            }
                        }
                    }
                }

                Button {
                    objectName: "scriptAddButton"
                    visible: _root._addFound
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
            // Half the page, or more when its controls need it (the vJoy
            // picker with a warning); the list keeps at least dp(220).
            Layout.preferredWidth: Math.max(_root.width / 2,
                Math.min(_root.width - Style.dp(220),
                    Math.max(Style.dp(410), _config.implicitWidth + Style.dp(20))))
            Layout.fillHeight: true
            contentWidth: availableWidth
            clip: true

            ColumnLayout {
                id: _variables

                width: _varScroll.availableWidth - Style.dp(10)
                x: Style.dp(10)
                spacing: Style.dp(4)

                // The picked script's variables (its configure button).
                Label {
                    Layout.topMargin: Style.dp(14)
                    visible: _root._variablesShown
                    text: "Variables of " + _root.shownName
                    color: Style.fgMuted
                    font.pixelSize: Style.dp(12)
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.bottomMargin: Style.dp(20)
                    visible: _root._variablesShown
                    implicitHeight: _config.implicitHeight
                    radius: Style.dp(6)
                    color: Style.bgCard
                    border.color: Style.line
                    border.width: Style.dp(1)

                    ScriptConfiguration {
                        id: _config

                        objectName: "scriptVariables"
                        filterText: _root.filterText
                        groupText: _root._groupText + " Variables of "
                            + _root.shownName + " " + _root.shownPath
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

        readonly property bool found: _root.matches(
            _root._groupText + " " + name + " " + path)

        objectName: "scriptRow:" + name
        visible: found
        implicitHeight: _layout.implicitHeight + Style.dp(20)

        Rectangle {
            visible: _item.index > _scripts.firstFound
            width: parent.width
            height: Style.dp(1)
            color: Style.line
        }

        GridLayout {
            id: _layout

            // Narrow: the buttons go under the name.
            readonly property bool narrow: _item.width < Style.dp(330)
            columns: narrow ? 2 : 3

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: Style.dp(14)
            anchors.rightMargin: Style.dp(14)
            columnSpacing: Style.dp(12)
            rowSpacing: Style.dp(4)

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

            RowLayout {
                Layout.columnSpan: _layout.narrow ? 2 : 1
                Layout.alignment: Qt.AlignRight
                spacing: Style.dp(12)

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
}
