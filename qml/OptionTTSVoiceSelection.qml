// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls

import Gremlin.Config
import Gremlin.UI

Item {
    id: _root

    implicitHeight: _combo.implicitHeight
    implicitWidth: _combo.implicitWidth

    // Made by ModelFactory (PYSIDE-1407: PySide6 never frees a Python object
    // QML declares); it lives as long as this row.
    readonly property TTSVoiceSelectionModel _model:
        ModelFactory.create("TTSVoiceSelectionModel", _root)

    ComboBox {
        id: _combo

        anchors.fill: parent

        model: _model
        textRole: "name"
        currentIndex: _model.currentIndex

        onActivated: (index) => { _model.currentIndex = index }
    }
}
