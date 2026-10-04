// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Layouts

import Gremlin.Compact as Compact
import Gremlin.Profile
import Gremlin.Style

Item {
    id: _root

    property HatDirectionModel directions

    implicitHeight: _checkboxes.height
    implicitWidth: _checkboxes.width

    RowLayout {
        id: _checkboxes

        Compact.CheckBox {
            font.family: Style.iconFont
            font.pixelSize: Style.dp(14)
            font.weight: 800
            text: bsi.icons.hat_n
            checked: directions.hatNorth
            onCheckedChanged: () => { directions.hatNorth = checked }
        }

        Compact.CheckBox {
            font.family: Style.iconFont
            font.pixelSize: Style.dp(14)
            font.weight: 800
            text: bsi.icons.hat_ne
            checked: directions.hatNorthEast
            onCheckedChanged: () => { directions.hatNorthEast = checked }
        }

        Compact.CheckBox {
            font.family: Style.iconFont
            font.pixelSize: Style.dp(14)
            font.weight: 800
            text: bsi.icons.hat_e
            checked: directions.hatEast
            onCheckedChanged: () => { directions.hatEast = checked }
        }

        Compact.CheckBox {
            font.family: Style.iconFont
            font.pixelSize: Style.dp(14)
            font.weight: 800
            text: bsi.icons.hat_se
            checked: directions.hatSouthEast
            onCheckedChanged: () => { directions.hatSouthEast = checked }
        }

        Compact.CheckBox {
            font.family: Style.iconFont
            font.pixelSize: Style.dp(14)
            font.weight: 800
            text: bsi.icons.hat_s
            checked: directions.hatSouth
            onCheckedChanged: () => { directions.hatSouth = checked }
        }

        Compact.CheckBox {
            font.family: Style.iconFont
            font.pixelSize: Style.dp(14)
            font.weight: 800
            text: bsi.icons.hat_sw
            checked: directions.hatSouthWest
            onCheckedChanged: () => { directions.hatSouthWest = checked }
        }

        Compact.CheckBox {
            font.family: Style.iconFont
            font.pixelSize: Style.dp(14)
            font.weight: 800
            text: bsi.icons.hat_w
            checked: directions.hatWest
            onCheckedChanged: () => { directions.hatWest = checked }
        }

        Compact.CheckBox {
            font.family: Style.iconFont
            font.pixelSize: Style.dp(14)
            font.weight: 800
            text: bsi.icons.hat_nw
            checked: directions.hatNorthWest
            onCheckedChanged: () => { directions.hatNorthWest = checked }
        }
    }
}
