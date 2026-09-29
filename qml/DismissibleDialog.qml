// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style

Popup {
    id: _root

    property string titleText: ""
    property string messageText: ""
    property string detail: ""
    property string confirmText: "OK"
    property string discardText: ""
    property string cancelText: ""
    property bool destructive: false
    property bool holdOpen: false

    signal confirmed()
    signal cancelled()
    signal discarded()
    signal saveChosen()
    signal discardChosen()
    signal acknowledged()

    property string _choice: ""
    property string _mode: ""
    property bool _resultOk: false

    function ask(message) {
        if (message !== undefined && message !== null && String(message).length)
            detail = String(message)
        _mode = "ask"
        _resultOk = false
        titleText = "Unsaved changes"
        messageText = detail
        confirmText = "Save"
        discardText = "Discard"
        cancelText = "Cancel"
        destructive = false
        holdOpen = true
        open()
    }

    function confirm(title, message, acceptLabel) {
        _mode = "confirm"
        _choice = ""
        _resultOk = false
        titleText = title
        messageText = message ? String(message) : ""
        confirmText = acceptLabel && String(acceptLabel).length ? String(acceptLabel) : "OK"
        discardText = ""
        cancelText = "Cancel"
        destructive = false
        holdOpen = true
        open()
    }

    function announce(ok, message) {
        _mode = "result"
        _resultOk = !!ok
        titleText = ok ? "Saved" : "Save failed"
        messageText = message ? String(message) : ""
        confirmText = "OK"
        discardText = ""
        cancelText = ""
        destructive = !ok
        holdOpen = !ok
        open()
    }

    parent: Overlay.overlay
    anchors.centerIn: parent
    modal: true
    focus: true
    closePolicy: holdOpen ? Popup.NoAutoClose : (Popup.CloseOnEscape | Popup.CloseOnPressOutside)
    padding: 16

    onClosed: {
        var choice = _choice
        var mode = _mode
        var ok = _resultOk
        _choice = ""
        if (choice === "confirm" || choice === "save" || choice === "discard" || choice === "ack")
            return
        if (mode === "result") {
            if (ok)
                acknowledged()
            return
        }
        cancelled()
    }

    background: Rectangle {
        color: Style.background
        border.color: destructive ? "#DC2626" : Style.accent
        border.width: 1
        radius: 4
    }

    contentItem: ColumnLayout {
        spacing: 12

        Label {
            text: _root.titleText
            font.bold: true
            font.pixelSize: 16
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
            Layout.preferredWidth: 420
        }

        Label {
            text: _root.messageText
            wrapMode: Text.WordWrap
            Layout.preferredWidth: 420
            Layout.fillWidth: true
            visible: text.length > 0
        }

        RowLayout {
            Layout.alignment: Qt.AlignRight
            spacing: 8

            Button {
                visible: _root.cancelText.length > 0
                text: _root.cancelText
                onClicked: _root.close()
            }

            Button {
                visible: _root.discardText.length > 0
                text: _root.discardText
                onClicked: {
                    _root._choice = "discard"
                    _root.close()
                    Qt.callLater(function() {
                        _root.discarded()
                        _root.discardChosen()
                    })
                }
            }

            Button {
                text: _root.confirmText
                highlighted: !_root.destructive
                onClicked: {
                    var mode = _root._mode
                    if (mode === "ask")
                        _root._choice = "save"
                    else if (mode === "result")
                        _root._choice = "ack"
                    else
                        _root._choice = "confirm"
                    _root.close()
                    Qt.callLater(function() {
                        if (mode === "ask")
                            _root.saveChosen()
                        else if (mode === "result")
                            _root.acknowledged()
                        else
                            _root.confirmed()
                    })
                }
            }
        }
    }
}
