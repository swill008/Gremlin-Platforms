// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Config
import Gremlin.Style

// Options' one OSC line: the settings live in OSC's file and are edited in
// OSC › Module Setup (D-09-OSC-FILE point 4).
Item {
    id: _root

    implicitHeight: _row.implicitHeight
    implicitWidth: Style.dp(420)

    OscModuleSetupLink {
        id: _link
    }

    RowLayout {
        id: _row

        anchors.fill: parent
        spacing: Style.dp(8)

        Label {
            Layout.fillWidth: true
            text: "OSC settings are in OSC › Module Setup."
            wrapMode: Text.WordWrap
        }

        Button {
            objectName: "oscOpenModuleSetup"
            text: "Open OSC Module Setup"
            onClicked: () => { _link.open() }
        }
    }
}
