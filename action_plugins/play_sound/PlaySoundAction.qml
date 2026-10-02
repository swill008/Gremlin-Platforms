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
            placeholderText: "Input the name of the audio file to play."

            selectByMouse: true

            onTextChanged: () => { action.soundFilename = text }
        }

        Button {
            text: "Select File"

            onClicked: () => { _fileDialog.open() }
        }

        Label {
            Layout.preferredWidth: Style.dp(50)

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
