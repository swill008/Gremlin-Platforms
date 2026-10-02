// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick

import Gremlin.Style

// The surface every menu, dropdown list and the command palette sit on.
Rectangle {
    color: Style.menuBg
    border.color: Style.menuLine
    border.width: 1
    radius: Style.menuRadius
}
