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

ColumnLayout {
    required property int index
    required property string groupName
    required property ConfigEntryModel entryModel

    width: parent ? parent.width - Style.dp(40) : implicitWidth
    anchors.left: parent ? parent.left : undefined
    anchors.right: parent ? parent.right : undefined
    anchors.rightMargin: Style.dp(40)

    JGText {
        Layout.fillWidth: true
        Layout.preferredHeight: Style.dp(50)

        text: Helpers.capitalize(groupName)

        font.pixelSize: Style.dp(21)
        font.weight: 500
        font.family: "Segoe UI"
        verticalAlignment: Text.AlignBottom
    }

    Repeater {
        model: entryModel

        delegate: _entryDelegateChooser
    }

    LayoutVerticalSpacer {
        Layout.preferredHeight: Style.dp(5)
    }

    DelegateChooser {
        id: _entryDelegateChooser
        role: "data_type"

        DelegateChoice {
            roleValue: "bool"

            OptionEntryCard {
                Layout.fillWidth: true

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

                        text: checked ? "On" : "Off"

                        onToggled: () => { model.value = checked }
                    }
                }
            }
        }
        DelegateChoice {
            roleValue: "float"

            OptionEntryCard {
                Layout.fillWidth: true

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
                            var path = String(properties["default_path"] || "")
                            _pathVariable.text = path
                            model.value = path
                        }
                    }
                }

                FileDialog {
                    id: _pathVariableFileDialog

                    property var associatedField

                    title: "Select a File"

                    onAccepted: () => {
                        var path = selectedFile.toString().substring("file:///".length)
                        associatedField.text = path
                        model.value = path
                    }
                }

                FolderDialog {
                    id: _pathFolderDialog

                    property var associatedField

                    title: "Select a Folder"

                    onAccepted: () => {
                        var path = selectedFolder.toString().substring("file:///".length)
                        associatedField.text = path
                        model.value = path
                    }
                }
            }
        }
        DelegateChoice {
            roleValue: "string"

            OptionEntryCard {
                Layout.fillWidth: true

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

                title: name === "Input highlight source" ? "Highlight source" : name
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
