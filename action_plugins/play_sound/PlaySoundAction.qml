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
    property PlaySoundModel action

    implicitHeight: _content.height

    RowLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right

        Label {
            Layout.preferredWidth: Style.dp(110)

            text: "Audio filename"
        }

        JGTextField {
            id: _soundFilename

            Layout.fillWidth: true

            text: action.soundFilename
            // Short enough to show in a narrow box; the full hint on hover.
            placeholderText: "File to play"
            // The hint's width plus the field's side padding (20 px in this style).
            Layout.minimumWidth: Math.ceil(_hint.advanceWidth) + Style.dp(24)
            ToolTip.visible: hovered && text.length === 0
            ToolTip.text: "The audio file to play (.wav, .mp3 or .ogg)."

            TextMetrics {
                id: _hint
                font: _soundFilename.font
                text: _soundFilename.placeholderText
            }

            selectByMouse: true

            onTextChanged: () => { action.soundFilename = text }
        }

        Button {
            text: "Select File"

            onClicked: () => { _fileDialog.open() }
        }

        Label {
            text: "Volume"
        }

        JGSpinBox {
            Layout.preferredWidth: Style.dp(100)

            value: action.soundVolume
            from: 0
            to: 100

            onValueModified: () => { action.soundVolume = value }
        }
   }

   FileDialog {
        id: _fileDialog

        nameFilters: ["Audio files (*.wav *.mp3 *.ogg)"]
        title: "Select a File"

        onAccepted: () => {
            _soundFilename.text = selectedFile.toString().substring("file:///".length)
        }
    }
}
