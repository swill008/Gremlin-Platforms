// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Menus
import Gremlin.Style

// Options, UI section: every part of the program's menu style in
// the current mode, and live samples to try.
Item {
    id: _root
    implicitHeight: _col.implicitHeight
    implicitWidth: Style.dp(560)

    property string sampleSize: "Medium"
    property bool sampleSnap: true
    // The live samples, for tests.
    readonly property alias sample: _sample
    readonly property alias menuButton: _menuButton

    ColumnLayout {
        id: _col
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: Style.dp(10)

        // The rows as they look: plain, under the pointer, chosen, a delete.
        MenuSurface {
            Layout.preferredWidth: Style.menuWidth
            Layout.preferredHeight: _rows.implicitHeight + 2 * Style.menuPad
            Column {
                id: _rows
                x: Style.menuPad
                y: Style.menuPad
                width: parent.width - 2 * Style.menuPad
                Repeater {
                    model: [
                        { text: "A row", hot: false, marked: false, hint: "Ctrl+S" },
                        { text: "Under the pointer", hot: true, marked: false, hint: "" },
                        { text: "The chosen value", hot: false, marked: true, hint: "" },
                        { text: "▸  A section", hot: false, marked: false, hint: "" },
                        { text: "Delete", hot: false, marked: false, hint: "", danger: true }
                    ]
                    delegate: MenuRowBackground {
                        required property var modelData
                        width: _rows.width
                        height: Style.menuRowH
                        hot: modelData.hot
                        marked: modelData.marked
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            x: Style.dp(10)
                            text: modelData.text
                            font.pixelSize: Style.menuTextPx
                            font.bold: !!modelData.danger || modelData.marked
                            color: modelData.danger ? Style.menuDanger : Style.menuText
                        }
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.right: parent.right
                            anchors.rightMargin: Style.dp(8)
                            text: modelData.hint
                            font.pixelSize: Style.menuTextPx - Style.dp(1)
                            color: Style.menuHint
                        }
                    }
                }
            }
        }

        RowLayout {
            spacing: Style.dp(8)
            Button {
                id: _menuButton
                text: "Right-click Menu…"
                onClicked: _sample.openBelow(_menuButton)
            }
            Button {
                text: "Command Palette…"
                onClicked: _palette.open()
            }
            ComboBox {
                Layout.preferredWidth: Style.dp(140)
                model: ["Small", "Medium", "Large"]
                currentIndex: 1
            }
            ComboBox {
                Layout.preferredWidth: Style.dp(160)
                // Long enough for the search box.
                model: ["Axis 1", "Axis 2", "Axis 3", "Axis 4", "Axis 5", "Axis 6", "Axis 7",
                        "Axis 8", "Slider 1", "Slider 2", "Dial 1", "Dial 2"]
            }
        }
    }

    ContextMenu {
        id: _sample
        build: function() {
            return MenuModel.menu("sample", "A sample", [
                MenuModel.action("Open", function() {}, true, { hint: "Enter" }),
                MenuModel.toggle("Snap", _root.sampleSnap, function() { _root.sampleSnap = !_root.sampleSnap })
            ], [
                MenuModel.section("look", "Look", [
                    MenuModel.pick("Size", ["Small", "Medium", "Large"], null, _root.sampleSize,
                                   function(v) { _root.sampleSize = v }),
                    MenuModel.number("Count", 1, 1, 9, "", function() {}, true, { step: 1, go: "Add", integer: true })
                ]),
                MenuModel.section("name", "Name", [
                    MenuModel.entry("Rename", function() {}, true, { placeholder: "Name, then Enter" })
                ]),
                MenuModel.section("remove", "Remove", [
                    MenuModel.action("Delete", function() {}, true, { danger: true })
                ])
            ])
        }
    }

    CommandPalette {
        id: _palette
    }
}
