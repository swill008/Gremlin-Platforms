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

    ColumnLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right

        RowLayout {
            Layout.fillWidth: true

            Label {
                Layout.preferredWidth: Style.dp(110)

                text: "Executable"
            }

            JGTextField {
                id: _executable

                Layout.fillWidth: true

                text: null !== _root.action ? _root.action.executable : ""
                placeholderText: null !== _root.action
                    ? "Path to the program to run."
                    : null

                selectByMouse: true

                onTextChanged: () => {
                    if (null !== _root.action && _root.action.executable !== text) {
                        _root.action.executable = text
                    }
                }
            }

            Button {
                text: "Select File"

                onClicked: () => { _fileDialog.open() }
            }
        }

        RowLayout {
            Layout.fillWidth: true

            Label {
                Layout.preferredWidth: Style.dp(110)

                text: "Arguments"
            }

            JGTextField {
                Layout.fillWidth: true

                text: null !== _root.action ? _root.action.arguments : ""
                placeholderText: "Arguments split on spaces; quote values containing spaces."

                selectByMouse: true

                onTextChanged: () => {
                    if (null !== _root.action && _root.action.arguments !== text) {
                        _root.action.arguments = text
                    }
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
