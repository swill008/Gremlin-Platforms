// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Dialogs
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Profile
import Gremlin.ActionPlugins
import "../../qml"
import Gremlin.Style

Item {
    property LoadProfileModel action

    implicitHeight: _content.height

    RowLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right

        Label {
            Layout.preferredWidth: Style.dp(150)

            text: "Profile filename"
        }

        JGTextField {
            id: _profileFilename

            Layout.fillWidth: true

            placeholderText: "Enter a profile filename"
            text: action.profile_filename
            selectByMouse: true

            onTextChanged: () => { action.profile_filename = text }
        }

        Button {
            text: "Select File"
            onClicked: () => { _fileDialog.open() }
        }
   }

   FileDialog {
        id: _fileDialog
        nameFilters: ["Profile files (*.xml)"]
        title: "Choose Profile"
        currentFolder: backend.profilesFolderUrl()
        onAccepted: () =>{
            _profileFilename.text = selectedFile.toString().substring("file:///".length)
        }
    }
}
