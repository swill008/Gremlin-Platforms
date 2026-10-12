// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Style

import "confirm.js" as Confirm

// Xbox Setup (D-XBOX-PADS): the ViGEmBus check and how many Xbox pads the
// program sends to (1-4). OK applies, Cancel leaves it. Lowering the count
// while a removed pad still has Map to Xbox bindings asks first; the
// bindings are kept either way.
ApplicationWindow {
    font.pixelSize: Style.fontSize
    id: _win
    objectName: "xboxSetupWindow"

    // Opens at the size it was left at (capped to the screen).
    ToolWindowMemory {
        host: _win
        name: "xboxSetup"
        defaultWidth: _win.minimumWidth
        defaultHeight: _win.minimumHeight
    }
    width: 620
    height: 300
    minimumWidth: Style.fitWidth(Style.dp(560), Screen)
    minimumHeight: Style.fitHeight(Style.dp(280), Screen)
    title: "Xbox Setup"
    color: Style.background
    U.Universal.theme: Style.theme

    EscapeCloses { host: _win }

    XboxSetupModel { id: _setup }

    // The open lowering question (01 S140), for tests.
    property var _question: null
    readonly property alias setup: _setup
    readonly property alias chosenCount: _count.value

    // OK: applies the count; lowering past bound pads asks first.
    function accept() {
        var n = _count.value
        var left = n < _setup.padCount ? _setup.bindingsOutside(n) : []
        if (left.length === 0) {
            _setup.apply(n)
            _win.close()
            return
        }
        _question = Confirm.ask(_body, {
            title: "Use " + n + (n === 1 ? " Xbox pad?" : " Xbox pads?"),
            text: (left.length === 1 ? "This binding sends to a pad that will be off:"
                                     : "These bindings send to pads that will be off:")
                  + "\n\n" + left.join("\n"),
            note: "The bindings are kept: Map to Xbox shows ⚠ until they are moved "
                  + "or the number of pads is raised.",
            action: "Yes",
            onAccept: function() {
                _win._question = null
                _setup.apply(n)
                _win.close()
            },
            onCancel: function() { _win._question = null }
        })
    }

    ColumnLayout {
        id: _body
        anchors.fill: parent
        anchors.margins: Style.dp(16)
        spacing: Style.dp(12)

        XboxDriverCheck {
            Layout.fillWidth: true
        }

        RowLayout {
            spacing: Style.dp(10)
            Label { text: "Number of Xbox pads"; color: Style.fg }
            SpinBox {
                id: _count
                objectName: "xboxSetupPadCount"
                from: 1
                to: _setup.maxPads
                value: _setup.padCount
            }
        }
        Label {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            color: Style.fgMuted
            font.pixelSize: Style.dp(12)
            text: "Pad 1 is the Xbox 360 Controller; pads 2-4 are Xbox 360 2, 3 and 4. "
                  + "Only the pads that are on are sent to."
        }

        Item { Layout.fillHeight: true }

        RowLayout {
            Layout.alignment: Qt.AlignRight
            spacing: Style.dp(8)
            Button {
                objectName: "xboxSetupOk"
                text: "OK"
                onClicked: _win.accept()
            }
            Button {
                objectName: "xboxSetupCancel"
                text: "Cancel"
                onClicked: _win.close()
            }
        }
    }
}
