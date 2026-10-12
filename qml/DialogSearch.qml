// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Style
import Gremlin.UI
import Gremlin.Util
import "helpers.js" as Helpers

// Search (D-01-SEARCH): every use of an input, an output, a mode or an
// action type in the profile, grouped by how it is used. A result opens its
// device's page in its mode on its row (Main.goToBinding); the window stays
// open. Opened from the toolbar, Tools › Mapping › Search… and a row's
// Find uses… (Main.openSearch fills it).
ApplicationWindow {
    font.pixelSize: Style.fontSize
    id: _root

    ToolWindowMemory {
        host: _root
        name: "search"
        defaultWidth: Style.fitWidth(Style.dp(820), Screen)
        defaultHeight: Style.fitHeight(Style.dp(640), Screen)
    }

    EscapeCloses { host: _root }

    minimumWidth: Style.fitWidth(Style.dp(560), Screen)
    minimumHeight: Style.fitHeight(Style.dp(380), Screen)
    color: Style.background
    U.Universal.theme: Style.theme
    title: "Search"

    readonly property alias usages: _model
    readonly property var kinds: ["input", "output", "mode", "action"]
    readonly property var kindLabels: ["Input", "Output", "Mode", "Action type"]
    // The result picked with a click or Previous / Next (-1: none).
    property int current: -1
    // Bumped when the picker lists must be read again.
    property int choicesRevision: 0

    UsagesModel {
        id: _model
        onResultsChanged: _root.current = -1
    }

    // Fills the window from a query ({kind, deviceGuid, inputType, inputId,
    // output, outputId, mode, actionTag}) and searches.
    function fill(query) {
        var q = query || {}
        var kind = String(q.kind || "")
        if (kinds.indexOf(kind) < 0)
            return
        _model.kind = kind
        if (kind === "input")
            _model.setFromInput(String(q.deviceGuid || ""), _type(q.inputType), q.inputId)
        else if (kind === "output")
            _model.setFromOutput(String(q.output || ""), Number(q.outputId || 0),
                                 _type(q.inputType), q.inputId)
        else if (kind === "mode")
            _model.setFromMode(String(q.mode || ""))
        else
            _model.setFromAction(String(q.actionTag || ""))
        choicesRevision++
    }

    function _type(value) {
        return value === undefined || value === null ? -1 : Number(value)
    }

    function setKind(kind) {
        if (_model.kind === kind)
            return
        _model.clear()
        _model.kind = kind
        choicesRevision++
    }

    // A picker's rows ({label, value}).
    function choices(kind) {
        choicesRevision
        return _model.choices(kind)
    }

    function indexOfValue(rows, test) {
        for (var i = 0; i < rows.length; i++)
            if (test(rows[i].value))
                return i
        return -1
    }

    function sameId(a, b) {
        return JSON.stringify(a) === JSON.stringify(b)
    }

    function countText(n) {
        return n === 1 ? "1 use" : n + " uses"
    }

    function groupCount(role) {
        var groups = _model.groups || []
        for (var i = 0; i < groups.length; i++)
            if (groups[i].role === role)
                return groups[i].count
        return 0
    }

    // Opens a result in the main window.
    function go(index) {
        if (index < 0 || index >= _list.count)
            return
        current = index
        _list.positionViewAtIndex(index, ListView.Contain)
        var item = _list.itemAtIndex(index)
        var main = Helpers.mainWindow()
        if (!item || !main)
            return
        main.goToBinding(item.deviceGuid, item.mode, item.inputType, item.inputId,
                         item.bindingIndex, item.inputLabel)
    }

    // Listen (Input): the next input pressed fills the search.
    InputListenerModel {
        id: _listener
        eventTypes: ["axis", "button", "hat", "key"]
        multipleInputs: false
        enabled: false
        onListeningTerminated: function(inputs) {
            _listener.enabled = false
            _listen.close()
            if (inputs && inputs.length && typeof _model.setFromListened === "function") {
                _model.setFromListened(inputs)
                _root.choicesRevision++
            }
        }
    }

    Popup {
        id: _listen
        objectName: "searchListen"
        parent: Overlay.overlay
        anchors.centerIn: Overlay.overlay
        dim: true
        modal: true
        focus: true
        closePolicy: Popup.NoAutoClose
        onOpened: _listener.enabled = true
        onClosed: _listener.enabled = false
        RowLayout {
            Label { text: "Press the input to find. Hold Esc to stop."; color: Style.fg }
            Label { text: _listener.currentInput; color: Style.fg }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Style.dp(12)
        spacing: Style.dp(8)

        TabBar {
            id: _kindBar
            objectName: "searchKinds"
            Layout.fillWidth: true
            currentIndex: Math.max(0, _root.kinds.indexOf(_model.kind))
            Repeater {
                model: _root.kindLabels
                TabButton {
                    required property int index
                    required property string modelData
                    objectName: "searchKind:" + _root.kinds[index]
                    text: modelData
                    onClicked: _root.setKind(_root.kinds[index])
                }
            }
        }

        // The pickers of the chosen kind.
        RowLayout {
            Layout.fillWidth: true
            spacing: Style.dp(8)

            // Input: device, control, Listen.
            ComboBox {
                id: _device
                objectName: "searchDevice"
                visible: _model.kind === "input" || _model.kind === ""
                Layout.fillWidth: true
                textRole: "label"
                model: visible ? _root.choices("device") : []
                currentIndex: _root.indexOfValue(model, function(v) {
                    return String(v) === _model.deviceGuid })
                displayText: currentIndex < 0 ? "Choose a device" : currentText
                onActivated: (i) => {
                    _model.kind = "input"
                    _model.deviceGuid = String(model[i].value)
                    _root.choicesRevision++
                }
            }
            ComboBox {
                id: _input
                objectName: "searchInput"
                visible: _device.visible
                Layout.fillWidth: true
                textRole: "label"
                model: visible && _model.deviceGuid.length ? _root.choices("input") : []
                currentIndex: _root.indexOfValue(model, function(v) {
                    return v.inputType === _model.inputType && _root.sameId(v.inputId, _model.inputId) })
                displayText: currentIndex < 0 ? "Choose an input" : currentText
                onActivated: (i) => _model.setFromInput(_model.deviceGuid, model[i].value.inputType,
                                                        model[i].value.inputId)
            }
            Button {
                objectName: "searchListenButton"
                visible: _device.visible
                text: "Listen"
                focusPolicy: Qt.NoFocus
                ToolTip.visible: hovered
                ToolTip.text: "Press an input to find its uses"
                onClicked: _listen.open()
            }

            // Output: vJoy device or Xbox pad, then its control.
            ComboBox {
                id: _output
                objectName: "searchOutput"
                visible: _model.kind === "output"
                Layout.fillWidth: true
                textRole: "label"
                model: visible ? _root.choices("output") : []
                currentIndex: _root.indexOfValue(model, function(v) {
                    return v.output === _model.output && v.outputId === _model.outputId })
                displayText: currentIndex < 0 ? "Choose an output" : currentText
                onActivated: (i) => {
                    _model.output = String(model[i].value.output)
                    _model.outputId = Number(model[i].value.outputId)
                    _root.choicesRevision++
                }
            }
            ComboBox {
                id: _outputInput
                objectName: "searchOutputInput"
                visible: _output.visible
                Layout.fillWidth: true
                textRole: "label"
                model: visible && _model.output.length ? _root.choices("outputInput") : []
                currentIndex: _root.indexOfValue(model, function(v) {
                    return v.inputType === _model.inputType && _root.sameId(v.inputId, _model.inputId) })
                displayText: currentIndex < 0 ? "Choose a control" : currentText
                onActivated: (i) => _model.setFromOutput(_model.output, _model.outputId,
                                                         model[i].value.inputType,
                                                         model[i].value.inputId)
            }

            // Mode.
            ComboBox {
                objectName: "searchMode"
                visible: _model.kind === "mode"
                Layout.fillWidth: true
                textRole: "label"
                model: visible ? _root.choices("mode") : []
                currentIndex: _root.indexOfValue(model, function(v) { return v === _model.mode })
                displayText: currentIndex < 0 ? "Choose a mode" : currentText
                onActivated: (i) => _model.setFromMode(String(model[i].value))
            }

            // Action type.
            ComboBox {
                objectName: "searchAction"
                visible: _model.kind === "action"
                Layout.fillWidth: true
                textRole: "label"
                model: visible ? _root.choices("action") : []
                currentIndex: _root.indexOfValue(model, function(v) { return v === _model.actionTag })
                displayText: currentIndex < 0 ? "Choose an action type" : currentText
                onActivated: (i) => _model.setFromAction(String(model[i].value))
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Style.dp(8)
            Label {
                objectName: "searchCount"
                Layout.fillWidth: true
                text: _root.countText(_model.count)
                color: Style.fgMuted
            }
            Button {
                objectName: "searchPrevious"
                text: "‹ Previous"
                focusPolicy: Qt.NoFocus
                enabled: _list.count > 0 && _root.current !== 0
                onClicked: _root.go(_root.current < 0 ? _list.count - 1 : _root.current - 1)
            }
            Button {
                objectName: "searchNext"
                text: "Next ›"
                focusPolicy: Qt.NoFocus
                enabled: _list.count > 0 && _root.current < _list.count - 1
                onClicked: _root.go(_root.current + 1)
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: Style.bgWell
            border.color: Style.line

            Label {
                objectName: "searchEmpty"
                anchors.centerIn: parent
                visible: _list.count === 0
                text: "No uses found."
                color: Style.fgMuted
            }

            JGListView {
                id: _list
                objectName: "searchResults"
                anchors.fill: parent
                anchors.margins: Style.dp(1)
                clip: true
                model: _model
                section.property: "group"
                section.criteria: ViewSection.FullString
                section.delegate: Label {
                    required property string section
                    objectName: "searchGroup:" + section
                    width: ListView.view.width
                    text: {
                        var groups = _model.groups || []
                        var title = section
                        for (var i = 0; i < groups.length; i++)
                            if (groups[i].role === section)
                                title = groups[i].title
                        return title + " (" + _root.countText(_root.groupCount(section)) + ")"
                    }
                    color: Style.fgStrong
                    font.bold: true
                    topPadding: Style.dp(8)
                    bottomPadding: Style.dp(2)
                    leftPadding: Style.dp(8)
                }
                delegate: Rectangle {
                    id: _row
                    required property int index
                    required property string deviceGuid
                    required property string deviceName
                    required property string mode
                    required property int inputType
                    required property var inputId
                    required property string inputLabel
                    required property int bindingIndex
                    required property string text
                    required property bool notFound
                    objectName: "searchRow:" + index
                    width: ListView.view.width
                    height: _rowBody.implicitHeight + Style.dp(10)
                    color: _root.current === index ? Style.bgSelected
                         : (_rowMouse.containsMouse ? Style.bgHover : Style.clear)

                    MouseArea {
                        id: _rowMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: _root.go(_row.index)
                    }

                    ColumnLayout {
                        id: _rowBody
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.leftMargin: Style.dp(20)
                        anchors.rightMargin: Style.dp(8)
                        spacing: Style.dp(3)

                        Label {
                            Layout.fillWidth: true
                            text: _row.deviceName + " · " + _row.mode + " · " + _row.inputLabel
                            color: Style.fg
                            elide: Text.ElideRight
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Style.dp(6)
                            // The action, in the Bindings number style.
                            Rectangle {
                                Layout.maximumWidth: _rowBody.width
                                implicitWidth: _actionText.implicitWidth + Style.dp(10)
                                implicitHeight: _actionText.implicitHeight + Style.dp(4)
                                radius: Style.dp(5)
                                color: Style.bindingBg
                                border.color: Style.bindingBorder
                                border.width: Style.dp(1)
                                Label {
                                    id: _actionText
                                    anchors.centerIn: parent
                                    width: Math.min(implicitWidth, parent.width - Style.dp(10))
                                    text: _row.text
                                    font.family: Style.monoFont
                                    color: Style.bindingText
                                    elide: Text.ElideRight
                                }
                            }
                            Label {
                                visible: _row.notFound
                                text: "[binding output not found]"
                                color: Style.warn
                            }
                            Item { Layout.fillWidth: true }
                        }
                    }
                }
            }
        }
    }
}
