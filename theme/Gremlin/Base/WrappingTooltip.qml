// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls

import Gremlin.Style

ToolTip {
    id: root

    property int maxWidth: Style.tooltipMaxWidth

    // The width is clamped to force word-wrap on long text with padding added
    // to have space on the end of the tooltip box.
    width: contentWidth > maxWidth ? maxWidth : contentWidth + Style.dp(20)
    delay: Style.tooltipDelayMs
}
