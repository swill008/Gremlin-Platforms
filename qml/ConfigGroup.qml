// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import Qt.labs.qmlmodels

import Gremlin.Base
import Gremlin.Config
import "helpers.js" as Helpers
import Gremlin.Style

// One group of settings in an Options window: a small heading over a card
// of rows (OptionEntryCard). With filterText set (the search box), only the
// rows whose name or description contain it show, and a group with none
// hides.
ColumnLayout {
    id: _group

    required property int index
    required property string groupName
    required property ConfigEntryModel entryModel
    property string filterText: ""

    spacing: Style.dp(4)
    visible: firstMatch >= 0

    // UserRole + 3 description, + 5 name (ConfigEntryModel).
    function matches(row) {
        var needle = filterText.trim().toLowerCase()
        if (!needle.length)
            return true
        var ix = entryModel.index(row, 0)
        var name = String(entryModel.data(ix, Qt.UserRole + 5) || "")
        var text = String(entryModel.data(ix, Qt.UserRole + 3) || "")
        return (name + " " + text).toLowerCase().indexOf(needle) >= 0
    }

    // The first row that shows (it has no divider above it), or -1.
    readonly property int firstMatch: {
        filterText
        for (var i = 0; i < (entryModel ? entryModel.rowCount() : 0); i++) {
            if (matches(i))
                return i
        }
        return -1
    }

    Label {
        // A page with one group may leave it untitled.
        visible: groupName.length > 0
        Layout.topMargin: Style.dp(14)
        // Display groups are already titled; stored ones ("labels") are not.
        text: /^[a-z]/.test(groupName) ? Helpers.capitalize(groupName) : groupName
        color: Style.fgMuted
        font.pixelSize: Style.dp(12)
    }

    Rectangle {
        Layout.fillWidth: true
        // Untitled: a gap above the card stands in for the heading.
        Layout.topMargin: groupName.length > 0 ? 0 : Style.dp(16)
        implicitHeight: _rows.implicitHeight
        radius: Style.dp(6)
        color: Style.bgCard
        border.color: Style.line
        border.width: Style.dp(1)

        ColumnLayout {
            id: _rows
            width: parent.width
            spacing: 0

            Repeater {
                model: _group.entryModel

                delegate: _entryDelegateChooser
            }
        }
    }

    DelegateChooser {
        id: _entryDelegateChooser
        role: "data_type"

        DelegateChoice {
            roleValue: "bool"

            OptionEntryCard {
                Layout.fillWidth: true
                visible: _group.matches(index)
                divider: index > _group.firstMatch

                title: name
                explanation: name === "Input highlighting"
                    ? "Select the input in the UI by using an input on the physical device."
                    : description

                RowLayout {
                    spacing: Style.dp(8)

                    OptionHighlightSpeed {
                        visible: name === "Input highlighting"
                        Layout.preferredWidth: visible ? Style.dp(252) : 0
                        Layout.minimumWidth: visible ? Style.dp(180) : 0
                    }

                    Switch {
                        Layout.alignment: Qt.AlignRight

                        checked: model.value

                        onToggled: () => { model.value = checked }
                    }
                }
            }
        }
        DelegateChoice {
            roleValue: "float"

            OptionEntryCard {
                Layout.fillWidth: true
                visible: _group.matches(index)
                divider: index > _group.firstMatch

                title: name
                explanation: description

                FloatSpinBox {
                    Layout.alignment: Qt.AlignRight

                    value: model.value
                    minValue: properties.min
                    maxValue: properties.max

                    onValueModified: (newValue) => { model.value = newValue }
                }
            }
        }
        DelegateChoice {
            roleValue: "int"

            OptionEntryCard {
                Layout.fillWidth: true
                visible: _group.matches(index)
                divider: index > _group.firstMatch

                title: name
                explanation: description

                JGSpinBox {
                    Layout.alignment: Qt.AlignRight

                    value: model.value
                    from: properties.min
                    to: properties.max

                    onValueModified: () => { model.value = value }
                }
            }
        }
        DelegateChoice {
            roleValue: "path"

            OptionEntryCard {
                Layout.fillWidth: true
                wide: true
                visible: _group.matches(index)
                divider: index > _group.firstMatch

                title: name
                explanation: description

                function _folderRoot() {
                    var raw = String(model.value || "")
                    if (!raw || raw === ".")
                        return String(properties["default_path"] || "")
                    return raw
                }

                function _child(folderName) {
                    var root = _folderRoot()
                    if (!root)
                        return folderName
                    var slash = root.indexOf("/") >= 0 && root.indexOf("\\") < 0 ? "/" : "\\"
                    if (root.endsWith("/") || root.endsWith("\\"))
                        return root + folderName
                    return root + slash + folderName
                }

                function _folderUrl(path) {
                    var text = String(path || "").replace(/\\/g, "/")
                    if (!text || text === ".")
                        return ""
                    if (text.startsWith("//"))
                        return "file:" + text
                    return "file:///" + text
                }

                RowLayout {
                    JGTextField {
                        id: _pathVariable

                        Layout.fillWidth: true
                        text: model.value
                        readOnly: true
                    }
                    Button {
                        text: "Select"
                        onClicked: () => {
                            if (properties["is_folder"]) {
                                var start = _folderUrl(_folderRoot())
                                if (start)
                                    _pathFolderDialog.currentFolder = start
                                _pathFolderDialog.associatedField = _pathVariable
                                _pathFolderDialog.open()
                            } else {
                                _pathVariableFileDialog.associatedField = _pathVariable
                                _pathVariableFileDialog.open()
                            }
                        }
                    }
                    Button {
                        visible: properties["allow_reset"] === true
                        text: "Reset"
                        onClicked: () => {
                            // The field follows model.value; writing its text would
                            // break that binding.
                            model.value = String(properties["default_path"] || "")
                        }
                    }
                }

                FileDialog {
                    id: _pathVariableFileDialog

                    property var associatedField

                    title: "Select a File"

                    onAccepted: () => {
                        model.value = selectedFile.toString().substring("file:///".length)
                    }
                }

                FolderDialog {
                    id: _pathFolderDialog

                    property var associatedField

                    title: "Select a Folder"

                    onAccepted: () => {
                        model.value = selectedFolder.toString().substring("file:///".length)
                    }
                }
            }
        }
        DelegateChoice {
            roleValue: "string"

            OptionEntryCard {
                Layout.fillWidth: true
                wide: true
                visible: _group.matches(index)
                divider: index > _group.firstMatch

                title: name
                explanation: description

                JGTextField {
                    Layout.alignment: Qt.AlignRight
                    Layout.fillWidth: true

                    text: model.value

                    onTextEdited: () => { model.value = text }

                    PointerTip {
                        text: parent.text
                    }
                }
            }
        }
        DelegateChoice {
            roleValue: "selection"

            OptionEntryCard {
                Layout.fillWidth: true
                visible: _group.matches(index)
                divider: index > _group.firstMatch

                title: name
                explanation: description

                ComboBox {
                    Layout.alignment: Qt.AlignRight

                    model: properties.valid_options

                    implicitContentWidthPolicy: ComboBox.WidestText

                    Component.onCompleted: () => { currentIndex = find(value) }
                    onActivated: () => { value = currentValue }
                }
            }
        }
        DelegateChoice {
            roleValue: "meta_option"

            OptionEntryCard {
                Layout.fillWidth: true
                wide: true
                visible: _group.matches(index)
                divider: index > _group.firstMatch

                title: name
                explanation: description

                DynamicItemLoader {
                    Layout.alignment: Qt.AlignRight
                    Layout.fillWidth: true

                    qmlPath: model.value

                    onLoadError: (err) => {
                        console.warn("Meta option load error:", err)
                    }
                }
            }
        }
    }

}
