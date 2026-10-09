// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Options → Button Map → Library: the saved styles and layout templates, to
// rename or delete. They are made in the Button Map itself.

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Device
import Gremlin.Style

Item {
    id: _library

    implicitHeight: _content.implicitHeight
    implicitWidth: Style.dp(420)

    ButtonMapOptions { id: _opts }
    HardwareProfile { id: _hw }

    property var templateList: _hw.templates()
    property string renaming: ""

    readonly property var _kindNames: ({ chip: "Chip", shape: "Shape", line: "Line", text: "Text" })

    function refreshTemplates() {
        templateList = _hw.templates()
    }

    ColumnLayout {
        id: _content
        width: parent.width
        spacing: Style.dp(4)

        Label {
            text: "Styles"
            font.bold: true
            color: Style.fg
        }
        Label {
            visible: _opts.styles.length === 0
            text: "None yet. Right-click a chip, shape, line or text box in the Button Map → Saved styles → Save this style."
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
            color: Style.fgMuted
        }
        Repeater {
            model: _opts.styles
            RowLayout {
                required property var modelData
                readonly property string key: "style:" + modelData.kind + ":" + modelData.name
                Layout.fillWidth: true
                spacing: Style.dp(6)
                Label {
                    text: _library._kindNames[modelData.kind] || modelData.kind
                    color: Style.fgMuted
                    Layout.preferredWidth: Style.dp(48)
                }
                TextField {
                    visible: _library.renaming === parent.key
                    Layout.fillWidth: true
                    text: modelData.name
                    // Enter, Esc or a click away (01 S134) saves the rename
                    // once; hiding the box ends the edit.
                    onEditingFinished: {
                        if (_library.renaming !== parent.key)
                            return
                        _library.renaming = ""
                        _opts.renameStyle(modelData.name, modelData.kind, text)
                    }
                }
                Label {
                    visible: _library.renaming !== parent.key
                    Layout.fillWidth: true
                    text: modelData.name
                    color: Style.fg
                    elide: Text.ElideRight
                }
                Button {
                    text: "Rename"
                    onClicked: _library.renaming = parent.key
                }
                Button {
                    text: "Delete"
                    onClicked: {
                        var name = modelData.name
                        var kind = modelData.kind
                        _deleteGate.confirmThen("Delete Saved Style",
                            "Delete the saved style “" + name + "”? Items that use it keep their look.",
                            "Delete", function() { _opts.deleteStyle(name, kind) }, null, true)
                    }
                }
            }
        }

        Label {
            text: "Templates"
            font.bold: true
            color: Style.fg
            Layout.topMargin: Style.dp(8)
        }
        Label {
            visible: _library.templateList.length === 0
            text: "None yet. In the Button Map: File → Templates → Save Layout as Template…. Export and import are there too."
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
            color: Style.fgMuted
        }
        Repeater {
            model: _library.templateList
            RowLayout {
                required property var modelData
                readonly property string key: "template:" + modelData.name
                Layout.fillWidth: true
                spacing: Style.dp(6)
                TextField {
                    visible: _library.renaming === parent.key
                    Layout.fillWidth: true
                    text: modelData.name
                    // As the style rename: saved once, however it is left.
                    onEditingFinished: {
                        if (_library.renaming !== parent.key)
                            return
                        _library.renaming = ""
                        var to = text.trim()
                        if (to.length && to !== modelData.name && !_hw.renameTemplate(modelData.name, to)) {
                            _failNotice.announce(false, "Could not rename " + modelData.name + " to " + to
                                + ". A template may have that name already, or its file could not be written.")
                            _failNotice.titleText = "Rename Failed"
                        }
                        _library.refreshTemplates()
                    }
                }
                Label {
                    visible: _library.renaming !== parent.key
                    Layout.fillWidth: true
                    text: modelData.name + "  ·  " + modelData.count + (modelData.count === 1 ? " item" : " items")
                    color: Style.fg
                    elide: Text.ElideRight
                }
                Button {
                    text: "Rename"
                    onClicked: _library.renaming = parent.key
                }
                Button {
                    text: "Delete"
                    onClicked: {
                        var name = modelData.name
                        _deleteGate.confirmThen("Delete Template",
                            "Delete the template “" + name + "”? Layouts made from it are not changed.",
                            "Delete", function() {
                                _hw.deleteTemplate(name)
                                _library.refreshTemplates()
                            }, null, true)
                    }
                }
            }
        }
    }

    // Asks before a style or template is deleted.
    DismissibleDialog {
        id: _deleteGate
    }

    DismissibleDialog {
        id: _failNotice
    }
}
