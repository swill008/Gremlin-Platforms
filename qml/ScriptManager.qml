// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import Qt.labs.qmlmodels

import Gremlin.Script

import "helpers.js" as Helpers
import Gremlin.Style


Item {
    id: _root

    // The script whose variables the right panel shows.
    property string shownPath: ""
    property string shownName: ""

    property ScriptListModel scriptListModel : backend.scriptListModel

    // Dialog to select a script to add
    FileDialog {
        id: _selectScript

        title: "Add Script"

        acceptLabel: "Load"
        defaultSuffix: "py"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Script files (*.py)"]
        currentFolder: backend.scriptsFolderUrl()

        onAccepted: function()
        {
            scriptListModel.addScript(selectedFile)
        }
    }

    // Dialog to rename a script
    DismissibleDialog {
        id: _removeGate
    }

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

    SplitView {
        anchors.fill: parent
        anchors.leftMargin: Style.dp(10)

        ColumnLayout {
            SplitView.fillHeight: true
            SplitView.fillWidth: true
            SplitView.minimumWidth: Style.dp(400)

            JGListView {
                id: _view

                Layout.fillHeight: true
                Layout.fillWidth: true
                Layout.rightMargin: Style.dp(5)

                spacing: Style.dp(10)
                scrollbarAlwaysVisible: true

                model: scriptListModel
                delegate: ScriptUI {
                    Layout.margins: Style.dp(10)
                    width: _view.width
                }
            }

            Button {
                Layout.alignment: Qt.AlignHCenter | Qt.AlignBottom
                Layout.preferredHeight: Style.dp(30)
                Layout.bottomMargin: Style.dp(10)

                text: "Add Script"

                onClicked: () => _selectScript.open()
            }
        }

        ScriptConfiguration {
            id: _config

            SplitView.fillHeight: true
            SplitView.minimumWidth: Style.dp(500)
        }
    }

    component ScriptUI : RowLayout {
        id: _item

        required property string path
        required property string name
        required property var variables
        // Why the script could not be loaded ("" when it loaded).
        required property string loadError

        JGText {
            Layout.leftMargin: Style.dp(10)
            text: bsi.icons.script
            font.pixelSize: Style.dp(18)
        }

        ColumnLayout {
            Layout.alignment: Qt.AlignVCenter
            Layout.preferredWidth: _view.width - Style.dp(400)
            spacing: 0

        JGText {
            id: _path

            Layout.fillWidth: true

            text: _item.path
            leftPadding: Style.dp(10)
            elide: Text.ElideMiddle

            ToolTip {
                text: _path.text
                width: contentWidth > Style.dp(500) ? Style.dp(500) : contentWidth + Style.dp(20)
                visible: _hoverPath.hovered
                delay: 500
                x: _hoverPath.point.position.x - width / 2
                y: _hoverPath.point.position.y - height - Style.dp(8)
            }

            HoverHandler {
                id: _hoverPath
                acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
            }
        }

        JGText {
            Layout.fillWidth: true
            visible: _item.loadError !== ""
            text: "Can't load: " + _item.loadError + ". Fix the script; it is tried again at Run."
            leftPadding: Style.dp(10)
            color: Style.error
            wrapMode: Text.Wrap
        }
        }

        LayoutHorizontalSpacer {}

        JGText {
            id: _name

            Layout.preferredWidth: Style.dp(200)
            Layout.alignment: Qt.AlignVCenter

            text: _item.name
            rightPadding: Style.dp(50)
            elide: Text.ElideMiddle

            ToolTip {
                x: _hoverName.point.position.x - width / 2
                y: _hoverName.point.position.y - height - Style.dp(8)
                text: _name.text
                // Set an upper width of the tooltip to force word wrap on
                // long texts.
                width: contentWidth > Style.dp(500) ? Style.dp(500) : contentWidth + Style.dp(20)
                visible: _hoverName.hovered
                delay: 500
            }

            HoverHandler {
                id: _hoverName
                acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
            }
        }

        IconButton {
            text: bsi.icons.edit

            onClicked: {
                _renameScriptDialog.text = name
                _renameScriptDialog.callback = (value) => {
                    if (_root.shownPath === path && _root.shownName === name)
                        _root.shownName = value
                    scriptListModel.renameScript(path, name, value)
                }
                _renameScriptDialog.visible = true
            }
        }

        IconButton {
            text: bsi.icons.configure
            enabled: _item.loadError === ""

            onClicked: {
                _config.model = variables
                _root.shownPath = path
                _root.shownName = name
            }
        }

        IconButton {
            Layout.rightMargin: Style.dp(20)
            text: bsi.icons.trash

            onClicked: () => {
                var p = path
                var n = name
                _removeGate.confirmThen("Remove Script?",
                    "Remove " + n + " from this profile? Its settings here go with it."
                        + " The script file itself is not deleted.",
                    "Remove", function() {
                        if (_root.shownPath === p && _root.shownName === n) {
                            _config.model = []
                            _root.shownPath = ""
                            _root.shownName = ""
                        }
                        scriptListModel.removeScript(p, n)
                    }, null, true)
            }
        }
    }
}
