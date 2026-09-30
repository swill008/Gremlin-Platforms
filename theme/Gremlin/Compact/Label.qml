// Copyright (C) 2017 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Modified by Joystick Gremlin Contributors

import QtQuick
import QtQuick.Templates as T
import QtQuick.Controls.Universal as U
import Gremlin.Style

T.Label {
    id: control

    font.pixelSize: Style.dp(14)

    opacity: enabled ? 1.0 : 0.2
    color: control.U.Universal.foreground
    linkColor: U.Universal.accent
}
