// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Config
import Gremlin.Style

Item {
    id: _root
    implicitHeight: _row.implicitHeight
    implicitWidth: Style.dp(420)

    WindowsScaleModel { id: _model }

    // Saved value before the last click, restored by Cancel.
    property bool _before: false

    RowLayout {
        id: _row
        anchors.fill: parent
        spacing: Style.dp(8)

        CheckBox {
            id: _box
            text: "Disable Windows scaling"
            checked: _model ? _model.disabled : false
            onClicked: {
                if (!_model)
                    return
                _before = _model.disabled
                _model.setDisabled(checked)
                if (checked !== _model.runningDisabled)
                    _restartAsk.choose(
                        "Restart Required",
                        "Windows scaling changes when Gremlin-Platforms starts. "
                        + "Restart now to use the new setting, choose Later to use it "
                        + "at the next start, or Cancel to undo the change.",
                        "Restart",
                        "Later"
                    )
            }
        }
    }

    DismissibleDialog {
        id: _restartAsk
        confirmColor: Style.danger

        onConfirmed: {
            if (!backend)
                return
            // Close Options so a save question on the main window is in front.
            var win = _root.Window.window
            backend.requestRestart()
            if (win)
                win.close()
        }
        onCancelled: {
            _model.setDisabled(_before)
            _box.checked = _before
        }
    }
}
