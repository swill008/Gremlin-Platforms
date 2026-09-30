// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Profile
import Gremlin.Style

Item {
    id: _root

    property VirtualButtonModel virtualButton

    implicitHeight: _checkboxes.height
    implicitWidth: _checkboxes.width

    RowLayout {
        id: _checkboxes

        spacing: Style.dp(10)

        IconCheckBox {
            text: bsi.icons.hat_n

            checked: virtualButton.hatNorth
            onCheckedChanged: () => { virtualButton.hatNorth = checked }
        }

        IconCheckBox {
            text: bsi.icons.hat_ne

            checked: virtualButton.hatNorthEast
            onCheckedChanged: () => { virtualButton.hatNorthEast = checked }
        }

        IconCheckBox {
            text: bsi.icons.hat_e

            checked: virtualButton.hatEast
            onCheckedChanged: () => { virtualButton.hatEast = checked }
        }

        IconCheckBox {
            text: bsi.icons.hat_se

            checked: virtualButton.hatSouthEast
            onCheckedChanged: () => { virtualButton.hatSouthEast = checked }
        }

        IconCheckBox {
            text: bsi.icons.hat_s

            checked: virtualButton.hatSouth
            onCheckedChanged: () => { virtualButton.hatSouth = checked }
        }

        IconCheckBox {
            text: bsi.icons.hat_sw

            checked: virtualButton.hatSouthWest
            onCheckedChanged: () => { virtualButton.hatSouthWest = checked }
        }

        IconCheckBox {
            text: bsi.icons.hat_w

            checked: virtualButton.hatWest
            onCheckedChanged: () => { virtualButton.hatWest = checked }
        }

        IconCheckBox {
            text: bsi.icons.hat_nw

            checked: virtualButton.hatNorthWest
            onCheckedChanged: () => { virtualButton.hatNorthWest = checked }
        }
    }
}
