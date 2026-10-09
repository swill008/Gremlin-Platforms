// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Config
import Gremlin.Util
import Gremlin.Style

import "confirm.js" as Confirm

Item {
    id: _root

    // Removes row index; an entry with a profile or program asks first
    // (01 S140). Settings changes are in History.
    function askRemove(index, profile, program) {
        if (!profile && !program) {
            _model.removeEntry(index)
            return
        }
        var name = function(path) {
            var s = String(path)
            return s.substring(Math.max(s.lastIndexOf("/"), s.lastIndexOf("\\")) + 1)
        }
        var what = profile && program
            ? "Profile " + name(profile) + " will no longer load for " + name(program) + "."
            : profile ? "Profile " + name(profile) + " goes from the list."
            : "Program " + name(program) + " goes from the list."
        Confirm.ask(_root, {
            title: "Remove auto-load entry?",
            text: what,
            undoable: true,
            action: "Remove Entry",
            onAccept: function() { _model.removeEntry(index) }
        })
    }

    ProfileAutoLoadingModel {
        id: _model
    }

    // The choosers open in the last folder used (01 S143): profiles in the
    // profiles folder at first, programs anywhere.
    FilePicker {
        id: _profileFileDialog
        objectName: "autoLoadProfilePicker"

        property var associatedField

        kind: "profile"
        nameFilters: ["Profile files (*.xml)"]
        title: "Choose Profile"
        folder: backend.profilesFolderUrl()

        onPicked: (selected) => {
            associatedField.text =
                String(selected).substring("file:///".length)
        }
    }

    FilePicker {
        id: _executableFileDialog
        objectName: "autoLoadProgramPicker"

        property var associatedField

        kind: "other"
        nameFilters: ["Executable files (*.exe)"]
        title: "Choose Program"

        onPicked: (selected) => {
            associatedField.text =
                String(selected).substring("file:///".length)
        }
    }

    Dialog {
        id: _executableSelectorDialog

        property int selectedIndex: -1
        property string selectedValue: ""
        property var associatedField

        title: "Choose Program"
        standardButtons: Dialog.Ok | Dialog.Cancel
        modal: true

        parent: Overlay.overlay
        anchors.centerIn: parent
        width: parent.width * 0.8
        height: parent.height * 0.8

        ColumnLayout {
            id: _dialogContent

            anchors.fill: parent

            JGListView {
                id: _processListViee

                Layout.fillWidth: true
                Layout.fillHeight: true

                spacing: Style.dp(5)

                model: ProcessListModel {}

                delegate: Button {
                    width: ListView.view.width

                    contentItem: Label {
                        text: model.display
                        horizontalAlignment: Text.AlignLeft
                    }

                    highlighted: index === _executableSelectorDialog.selectedIndex

                    onClicked: () => {
                        _executableSelectorDialog.selectedIndex = index
                        _executableSelectorDialog.selectedValue = model.display
                    }
                }
            }
        }

        onAccepted: () => {
            if (selectedIndex != -1) {
                associatedField.text = selectedValue
            }
        }

        onAboutToShow: () => {
            _processListViee.model.refresh()
        }
    }

    implicitHeight: _content.implicitHeight
    implicitWidth: _content.implicitWidth

    ColumnLayout {
        id: _content
        anchors.fill: parent

        Repeater {
            model: _model

            delegate: AutoLoadEntry {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignRight

                profile: model.profile
                executable: model.executable
                isEnabled: model.isEnabled
            }
        }

        Button {
            Layout.alignment: Qt.AlignCenter

            text: "New Entry"

            onClicked: () => { _model.newEntry() }
        }
    }

    component AutoLoadEntry : Item {
        property alias profile: _profile.text
        property alias executable: _executable.text
        property alias isEnabled: _isEnabled.checked

        implicitHeight: _item.implicitHeight

        ColumnLayout {
            id: _item

            anchors.fill: parent

            // Buttons to select the profile and executable file for the entry
            // as well as enable/disable the entry and delete it.
            // Tight padding so the row fits beside the 400 wide text column and
            // stays clear of the scrollbar, which would take clicks on the ×.
            RowLayout {
                spacing: Style.dp(4)

                Button {
                    horizontalPadding: Style.dp(4)
                    text: "Select Profile"
                    onClicked: () => {
                        _profileFileDialog.associatedField = _profile
                        _profileFileDialog.open()
                    }
                }

                Button {
                    horizontalPadding: Style.dp(4)
                    text: "Browse Executable"
                    onClicked: () => {
                        _executableFileDialog.associatedField = _executable
                        _executableFileDialog.open()
                    }
                }

                Button {
                    horizontalPadding: Style.dp(4)
                    text: "Select Executable"

                    onClicked: () => {
                        _executableSelectorDialog.associatedField = _executable
                        _executableSelectorDialog.open()
                    }
                }

                LayoutHorizontalSpacer {}

                Switch {
                    id: _isEnabled

                    text: checked ? "On" : "Off"

                    onToggled: () => { model.isEnabled = checked }
                }

                // Red (01 S140); asks first when the row holds anything.
                DangerButton {
                    objectName: "autoLoadRemove"
                    horizontalPadding: Style.dp(4)
                    text: bsi.icons.remove
                    font.family: Style.iconFont
                    font.pixelSize: Style.dp(17)
                    ToolTip.visible: hovered
                    ToolTip.text: "Remove this entry"

                    onClicked: () => { _root.askRemove(index, _profile.text, _executable.text) }
                }

            }

            JGTextField {
                id: _profile

                Layout.fillWidth: true

                readOnly: true
                onTextChanged: () => { model.profile = text }
            }

            // Executable path field with button to enable editing to support
            // usage of regular expressions.
            RowLayout {
                JGTextField {
                    id: _executable

                    Layout.fillWidth: true

                    readOnly: true
                    onTextChanged: () => { model.executable = text }
                }
                Button {
                    text: bsi.icons.edit
                    font.family: Style.iconFont

                    checkable: true

                    onToggled: () => { _executable.readOnly = !checked }
                }
            }

            LayoutVerticalSpacer {
                Layout.preferredHeight: Style.dp(10)
            }
        }
    }
}
