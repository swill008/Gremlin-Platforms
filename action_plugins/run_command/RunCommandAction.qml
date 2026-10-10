// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Dialogs
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.ActionPlugins
import "../../qml"
import Gremlin.Style

Item {
    id: _root

    property RunCommandModel action

    implicitHeight: _content.height

    // Labels in the first column; too narrow for a label beside its box,
    // each box goes under its label.
    GridLayout {
        id: _content

        readonly property bool wide: width >= Style.dp(110)
            + Math.max(_executable.Layout.minimumWidth + _selectFile.implicitWidth + columnSpacing,
                       _arguments.Layout.minimumWidth)
            + columnSpacing

        anchors.left: parent.left
        anchors.right: parent.right
        columns: 3

        Label {
            Layout.row: 0
            Layout.column: 0
            Layout.columnSpan: _content.wide ? 1 : 3
            Layout.preferredWidth: _content.wide ? Style.dp(110) : -1

            text: "Executable"
        }

        JGTextField {
            id: _executable

            Layout.row: _content.wide ? 0 : 1
            Layout.column: _content.wide ? 1 : 0
            Layout.columnSpan: _content.wide ? 1 : 2
            Layout.fillWidth: true
            // The hint's width plus the field's side padding (20 px in this style).
            Layout.minimumWidth: Math.ceil(_executableHint.advanceWidth) + Style.dp(24)

            text: null !== _root.action ? _root.action.executable : ""
            placeholderText: null !== _root.action
                ? "Path to the program to run."
                : null

            TextMetrics {
                id: _executableHint
                font: _executable.font
                text: _executable.placeholderText
            }

            selectByMouse: true

            onTextChanged: () => {
                if (null !== _root.action && _root.action.executable !== text) {
                    _root.action.executable = text
                }
            }
        }

        Button {
            id: _selectFile

            Layout.row: _content.wide ? 0 : 1
            Layout.column: 2

            text: "Select File"

            onClicked: () => { _fileDialog.open() }
        }

        Label {
            Layout.row: _content.wide ? 1 : 2
            Layout.column: 0
            Layout.columnSpan: _content.wide ? 1 : 3
            Layout.preferredWidth: _content.wide ? Style.dp(110) : -1

            text: "Arguments"
        }

        JGTextField {
            id: _arguments

            Layout.row: _content.wide ? 1 : 3
            Layout.column: _content.wide ? 1 : 0
            Layout.columnSpan: _content.wide ? 2 : 3
            Layout.fillWidth: true
            // The hint's width plus the field's side padding (20 px in this style).
            Layout.minimumWidth: Math.ceil(_argumentsHint.advanceWidth) + Style.dp(24)

            text: null !== _root.action ? _root.action.arguments : ""
            // Short enough to show in a narrow box; the full hint on hover.
            placeholderText: "Quote values with spaces"
            ToolTip.visible: hovered && text.length === 0
            ToolTip.text: "Arguments split on spaces; quote values containing spaces."

            TextMetrics {
                id: _argumentsHint
                font: _arguments.font
                text: _arguments.placeholderText
            }

            selectByMouse: true

            onTextChanged: () => {
                if (null !== _root.action && _root.action.arguments !== text) {
                    _root.action.arguments = text
                }
            }
        }
    }

    FileDialog {
        id: _fileDialog

        nameFilters: ["Executables (*.exe *.bat *.cmd)", "All files (*)"]
        title: "Select an Executable"

        onAccepted: () => {
            _executable.text = selectedFile.toString().substring("file:///".length)
        }
    }
}
