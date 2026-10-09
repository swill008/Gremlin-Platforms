// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Options → Button Map → Library: the saved styles and layout templates, to
// rename or delete. They are made in the Button Map itself.

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Device
import Gremlin.Style

import "confirm.js" as Confirm

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

        SectionHeading {
            objectName: "stylesHeading"
            Layout.fillWidth: true
            text: "Styles"
        }
        EmptyState {
            objectName: "stylesEmpty"
            visible: _opts.styles.length === 0
            Layout.fillWidth: true
            text: "None yet. Right-click a chip, shape, line or text box in the Button Map → Saved styles → Save this style."
        }
        Repeater {
            model: _opts.styles
            RowLayout {
                id: _styleRow
                required property var modelData
                readonly property string key: "style:" + modelData.kind + ":" + modelData.name
                Layout.fillWidth: true
                spacing: Style.dp(6)
                Label {
                    text: _library._kindNames[modelData.kind] || modelData.kind
                    color: Style.fgMuted
                    Layout.preferredWidth: Style.dp(48)
                }
                // The shared Rename box (01 S135): Enter or a click away
                // saves once, Esc cancels.
                RenameField {
                    Layout.fillWidth: true
                    name: modelData.name
                    open: _library.renaming === _styleRow.key
                    // Saved after the edit ends: the save rebuilds this row.
                    property string _newName: ""
                    onRenamed: (newName) => _newName = newName
                    onEnded: {
                        _library.renaming = ""
                        open = Qt.binding(() => _library.renaming === _styleRow.key)
                        var to = _newName
                        _newName = ""
                        if (to.length)
                            _opts.renameStyle(modelData.name, modelData.kind, to)
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
                DangerButton {
                    objectName: "styleDelete"
                    text: "Delete"
                    onClicked: {
                        var name = modelData.name
                        var kind = modelData.kind
                        Confirm.ask(_library, {
                            title: "Delete saved style “" + name + "”?",
                            text: "Items that use it keep their look.",
                            undoable: false,
                            action: "Delete Style",
                            onAccept: function() { _opts.deleteStyle(name, kind) }
                        })
                    }
                }
            }
        }

        SectionHeading {
            objectName: "templatesHeading"
            Layout.fillWidth: true
            Layout.topMargin: Style.dp(8)
            text: "Templates"
        }
        EmptyState {
            objectName: "templatesEmpty"
            visible: _library.templateList.length === 0
            Layout.fillWidth: true
            text: "None yet. In the Button Map: File → Templates → Save Layout as Template…. Export and import are there too."
        }
        Repeater {
            model: _library.templateList
            RowLayout {
                id: _templateRow
                required property var modelData
                readonly property string key: "template:" + modelData.name
                Layout.fillWidth: true
                spacing: Style.dp(6)
                // As the style rename.
                RenameField {
                    Layout.fillWidth: true
                    name: modelData.name
                    open: _library.renaming === _templateRow.key
                    onRenamed: (newName) => {
                        if (!_hw.renameTemplate(modelData.name, newName)) {
                            _failNotice.announce(false, "Could not rename " + modelData.name + " to " + newName
                                + ". A template may have that name already, or its file could not be written.")
                            _failNotice.titleText = "Rename Failed"
                        }
                    }
                    onEnded: {
                        _library.renaming = ""
                        open = Qt.binding(() => _library.renaming === _templateRow.key)
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
                DangerButton {
                    objectName: "templateDelete"
                    text: "Delete"
                    onClicked: {
                        var name = modelData.name
                        Confirm.ask(_library, {
                            title: "Delete template “" + name + "”?",
                            text: "Layouts made from it are not changed.",
                            undoable: false,
                            action: "Delete Template",
                            onAccept: function() {
                                _hw.deleteTemplate(name)
                                _library.refreshTemplates()
                            }
                        })
                    }
                }
            }
        }
    }

    DismissibleDialog {
        id: _failNotice
    }
}
