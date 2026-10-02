// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Config
import Gremlin.Style
import "helpers.js" as Helpers

ApplicationWindow {
    font.pixelSize: Style.fontSize
    id: _options
    // ToolWindowMemory sets the saved or default size when the window opens.
    width: 1200
    height: 700
    minimumWidth: Style.dp(1200)
    minimumHeight: Style.dp(600)

    U.Universal.theme: Style.theme
    color: Style.background

    title: "Options"

    ToolWindowMemory {
        host: _options
        name: "options"
        defaultWidth: Style.dp(1200)
        defaultHeight: Style.dp(700)
    }

    // Opens on this section (its display name, e.g. "Button Map").
    property string initialSection: ""

    function showSection(name) {
        // Roles of ConfigSectionModel: UserRole + 1 name, + 2 groupModel.
        for (var i = 0; i < _sectionModel.rowCount(); i++) {
            var index = _sectionModel.index(i, 0)
            if (_sectionModel.data(index, Qt.UserRole + 1) === name) {
                _sectionSelector.currentIndex = i
                _configSection.groupModel = _sectionModel.data(index, Qt.UserRole + 2)
                _sectionSelector.positionViewAtIndex(i, ListView.Contain)
                return
            }
        }
    }

    onClosing: () => {
        backend.emitConfigChanged()
    }

    ConfigSectionModel {
        id: _sectionModel
    }

    RowLayout {
        id: _root

        anchors.fill: parent

        // Shows the list of all option sections.
        JGListView {
            id: _sectionSelector

            Layout.preferredWidth: Style.dp(200)
            Layout.fillHeight: true

            model: _sectionModel
            delegate: ConfigSectionButton {}

            Component.onCompleted: () => {
                currentItem.clicked()
                if (_options.initialSection)
                    Qt.callLater(function() { _options.showSection(_options.initialSection) })
            }
        }

        // Shows the contents of the currently selected section.
        ConfigSection {
            id: _configSection

            Layout.fillHeight: true
            Layout.fillWidth: true
        }
    }
}
