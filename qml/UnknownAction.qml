// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// An action of a type this program doesn't have (a user plugin removed or
// failed to load): kept as it is, saved with the profile, does nothing.

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style

Item {
    property var action

    implicitHeight: _note.implicitHeight

    Label {
        id: _note

        anchors.left: parent.left
        anchors.right: parent.right

        text: action ? action.note : ""
        color: Style.fgMuted
        wrapMode: Text.WordWrap
    }
}
