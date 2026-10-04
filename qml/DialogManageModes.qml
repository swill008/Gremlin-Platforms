// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Profile
import Gremlin.Menus as Menus
import Gremlin.Style

ApplicationWindow {
    font.pixelSize: Style.fontSize
    id: _root

    EscapeCloses { host: _root }

    minimumWidth: Style.fitWidth(Style.dp(900), Screen)
    minimumHeight: Style.fitHeight(Style.dp(500), Screen)

    color: Style.background
    U.Universal.theme: Style.theme

    title: "Manage Modes"

    property ModeHierarchyModel modeHierarchy : ModeHierarchyModel {}
    property ModeListModel modeList : ModeListModel {}

    function confirmDelete(mode) {
        var n = modeHierarchy.bindingCount(mode)
        var what = n === 0 ? "It has no bindings."
            : "Its " + (n === 1 ? "binding" : n + " bindings") + " will be deleted too."
        _deleteGate.confirmThen("Delete Mode \"" + mode + "\"?",
            what + " Modes under it move up one level.",
            "Delete mode", function() { modeHierarchy.deleteMode(mode) }, null, true)
    }

    DismissibleDialog {
        id: _deleteGate
    }

    TextInputDialog {
        id: _textInput

        visible: false
        width: Style.dp(500)
        allowBlank: false

        property var callback: null

        onAccepted: (value) => {
            callback(value)
            visible = false
        }
    }

    ColumnLayout {
        id: _content

        anchors.fill: parent
        anchors.topMargin: Style.dp(10)

        RunningNote { Layout.leftMargin: Style.dp(12) }

        Label {
            Layout.fillWidth: true
            Layout.leftMargin: Style.dp(12)
            Layout.rightMargin: Style.dp(12)
            wrapMode: Text.WordWrap
            color: Style.fg
            text: "The mode list is the map you edit and the map that runs. Modes are stored in the profile."
        }

        Label {
            Layout.fillWidth: true
            Layout.leftMargin: Style.dp(12)
            Layout.rightMargin: Style.dp(12)
            wrapMode: Text.WordWrap
            color: Style.fgMuted
            text: "A mode uses its parent's actions for any input that has none in this mode."
        }

        JGListView  {
            Layout.fillWidth: true
            Layout.fillHeight: true

            scrollbarAlwaysVisible: true
            spacing: Style.dp(10)

            model: modeList
            delegate: _delegate

            // Column headings, laid out like a row so they line up with it.
            header: RowLayout {
                width: ListView.view.width
                height: implicitHeight + Style.dp(6)

                Label {
                    Layout.fillWidth: true
                    Layout.leftMargin: Style.dp(10)
                    padding: Style.dp(4)
                    text: "Mode"
                    color: Style.fgMuted
                }
                IconButton {
                    text: bsi.icons.edit
                    Layout.leftMargin: Style.dp(10)
                    opacity: 0
                    enabled: false
                }
                Label {
                    Layout.preferredWidth: Style.dp(200)
                    Layout.leftMargin: Style.dp(10)
                    Layout.rightMargin: Style.dp(10)
                    text: "Inherits from"
                    color: Style.fgMuted
                }
                IconButton {
                    text: bsi.icons.trash
                    Layout.rightMargin: Style.dp(10)
                    opacity: 0
                    enabled: false
                }
            }
        }

        Button {
            Layout.alignment: Qt.AlignHCenter

            text: "Add Mode"

            onClicked: () => {
                _textInput.heading = "Add new mode"
                _textInput.text = "New mode"
                // Refuses blank names and look-alikes such as "test mode" next to "Test Mode".
                _textInput.validator = function(value)
                {
                    return !modeHierarchy.nameTaken(value, "")
                }
                _textInput.callback = function(name) {
                    modeHierarchy.newMode(name)
                }
                _textInput.visible = true
            }
        }
    }

    Component {
        id: _delegate

        RowLayout {
            required property string name
            required property string parentName

            width: ListView.view.width
            height: _parentMode.height

            Label {
                Layout.fillWidth: true
                Layout.leftMargin: Style.dp(10)

                padding: Style.dp(4)

                text: name
            }

            IconButton {
                text: bsi.icons.edit

                Layout.leftMargin: Style.dp(10)

                onClicked: () => {
                    _textInput.heading = "Rename existing mode"
                    _textInput.text = name
                    _textInput.callback = function(value) {
                        modeHierarchy.renameMode(name, value)
                    }
                    // A mode may change the capitals of its own name.
                    _textInput.validator = function(value) {
                        return !modeHierarchy.nameTaken(value, name)
                    }
                    _textInput.visible = true
                }
            }

            ComboBox {
                id: _parentMode

                Layout.preferredWidth: Style.dp(200)
                Layout.leftMargin: Style.dp(10)
                Layout.rightMargin: Style.dp(10)

                model: modeHierarchy.validParents(name)

                textRole: "value"
                valueRole: "value"
                // "" means no parent.
                displayText: currentIndex < 0 || currentValue === "" ? "(none)" : currentText

                background: Rectangle {
                    implicitWidth: Style.dp(120)
                    implicitHeight: Style.dp(32)
                    border.width: Style.dp(1)
                    border.color: _parentMode.down || _parentMode.hovered
                            ? _parentMode.U.Universal.baseMediumColor
                            : _parentMode.U.Universal.baseMediumLowColor
                    color: _parentMode.down
                            ? _parentMode.U.Universal.listMediumColor
                            : (Style.isDarkMode ? _parentMode.U.Universal.altMediumLowColor : Style._light.item)
                }

                delegate: Menus.DropdownRow {
                    combo: _parentMode
                    // "" means no parent.
                    labelFor: (i) => _parentMode.textAt(i) === "" ? "(none)" : _parentMode.textAt(i)
                }

                onActivated: (index) => {
                    modeHierarchy.setParent(name, currentValue)
                }

                Component.onCompleted: () => {
                    currentIndex = indexOfValue(parentName)
                }
            }

            IconButton {
                text: bsi.icons.trash

                Layout.rightMargin: Style.dp(10)

                onClicked: () => { _root.confirmDelete(name) }
            }
        }
    }
}
