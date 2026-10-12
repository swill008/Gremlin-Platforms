// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Device
import Gremlin.Style
import Gremlin.UI

// The Xbox output's Output View (03 S139, D-XBOX-PADS): one red line when
// the ViGEmBus driver is missing (the full check is in Xbox Setup), the
// Find bar once for every pad, then one section per pad that is on and has
// a Map to Xbox binding (any mode): its face, its chip rows and its control
// list. Each section folds and remembers it; all open the first time. One
// scroll for all of it; the list's own Appearance on the page bar.
Item {
    id: _root

    // The red line's "Open Xbox Setup" link; Main opens the window.
    signal xboxSetupRequested()

    // Pad number -> open; a pad not in it is open. Set from the saved state
    // when the page loads (no starting binding to overwrite).
    property var padOpenMap
    readonly property int padSectionCount: _sections.count
    // The Find bar's "Show only bound controls" tick: on the first time,
    // then as last left (saved with the fold state).
    property bool findSending: true

    // The page's Appearance part (PageAppearance.qml): Main shows its
    // Appearance… / Hide Appearance button on the page bar.
    property alias displayOpen: _appear.displayOpen
    readonly property Component pageBar: _sections.count > 0 ? _appear.pageBar : null
    function toggleAppearance() { _appear.toggleAppearance() }
    function requestCloseDisplay() { _appear.requestCloseDisplay() }
    readonly property alias appearance: _appear

    readonly property bool running:
        !!(typeof backend !== "undefined" && backend && backend.gremlinActive)

    XboxPadSectionsModel { id: _pads }

    XboxDriverStatus { id: _driver }

    WindowPlacement { id: _place }

    function isPadOpen(pad) {
        return !padOpenMap || padOpenMap[String(pad)] !== false
    }

    function setPadOpen(pad, open) {
        var next = {}
        for (var key in padOpenMap)
            next[key] = padOpenMap[key]
        next[String(pad)] = !!open
        padOpenMap = next
        _saveState()
    }

    // The fold state and the tick, kept per page in the tool-row state.
    function _saveState() {
        _place.saveToolRowState("xboxOutput", JSON.stringify({
            open: padOpenMap || {},
            boundOnly: findSending
        }))
    }

    // That pad's control list, or null when it has no section.
    function padList(pad) {
        for (var i = 0; i < _sections.count; ++i) {
            var section = _sections.itemAt(i)
            if (section && section.padId === pad)
                return section.list
        }
        return null
    }

    // The saved fold state and tick, read once when the page is made.
    function _readState() {
        try {
            var state = JSON.parse(_place.toolRowState("xboxOutput"))
            return (state && typeof state === "object") ? state : {}
        } catch (e) {
            return {}
        }
    }
    readonly property var _saved: _readState()
    // How the "sending" tick starts: as last left, on the first time.
    readonly property bool _boundStart: _saved.boundOnly !== false
    // The Find bar's ticks, the "sending" one starting as saved.
    readonly property var _filters: _pads.filters.map(function(tick) {
        var copy = { label: tick.label, name: tick.name }
        if (tick.name === "sending")
            copy.checked = _boundStart
        return copy
    })

    function _loadPadOpen() {
        var open = _saved.open
        padOpenMap = (open && typeof open === "object") ? open : {}
        findSending = _boundStart
    }

    Component.onCompleted: _loadPadOpen()
    onVisibleChanged: if (visible) _driver.reload()

    // What the shared Find bar reads from its list: the count across pads,
    // nothing to undo, no "Can't be sent" tick.
    QtObject {
        id: _findLayout
        readonly property int parentCount: {
            var n = 0
            for (var i = 0; i < _sections.count; ++i) {
                var section = _sections.itemAt(i)
                if (section)
                    n += section.list.parentCount
            }
            return n
        }
        readonly property bool canUndo: false
        readonly property bool canRedo: false
        readonly property string undoTip: ""
        readonly property string redoTip: ""
        readonly property string lastChange: ""
        readonly property string undone: ""
        function setCantSendOnly(on) {}
        function undo() {}
        function redo() {}
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        ScrollView {
            id: _scroll
            objectName: "xboxOutputScroll"
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumWidth: Style.dp(360)
            Layout.margins: Style.dp(10)
            contentWidth: availableWidth
            ScrollBar.vertical.policy: ScrollBar.AlwaysOn

            Component.onCompleted: {
                _scroll.contentItem.boundsMovement = Flickable.StopAtBounds
                _scroll.contentItem.boundsBehavior = Flickable.StopAtBounds
            }

            ColumnLayout {
                id: _column
                width: _scroll.availableWidth - Style.dp(16)
                spacing: Style.dp(8)

                // Only when the driver is missing: the pads can't be sent.
                RowLayout {
                    objectName: "xboxDriverMissingRow"
                    visible: !_driver.ready
                    Layout.fillWidth: true
                    spacing: Style.dp(10)

                    JGText {
                        objectName: "xboxDriverMissing"
                        text: "ViGEmBus driver not found: the Xbox pads can't be sent."
                        color: Style.danger
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                    AbstractButton {
                        id: _setupLink
                        objectName: "xboxOpenSetupLink"
                        text: "Open Xbox Setup"
                        hoverEnabled: true
                        implicitWidth: _linkText.implicitWidth
                        implicitHeight: _linkText.implicitHeight
                        Accessible.name: text
                        onClicked: _root.xboxSetupRequested()
                        contentItem: Label {
                            id: _linkText
                            text: _setupLink.text
                            color: Style.accent
                            font.underline: _setupLink.hovered
                        }
                        HoverHandler { cursorShape: Qt.PointingHandCursor }
                    }
                }

                JGText {
                    objectName: "xboxOutputEmpty"
                    visible: _sections.count === 0
                    text: "No Xbox controller has a binding yet. Add a Map to Xbox action on Device Bindings to see it here."
                    opacity: 0.65
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                // Once for every pad section (S139).
                ControlFindBar {
                    id: _find
                    objectName: "xboxOutputFindBar"
                    visible: _sections.count > 0
                    Layout.fillWidth: true
                    layout: _findLayout
                    namePrefix: "xboxOutput"
                    placeholder: "Control or source"
                    showUndo: false
                    showCantSend: false
                    typeChoices: _pads.typeChoices
                    filters: _root._filters
                    onChanged: {
                        var on = _find.isChecked("sending")
                        if (on !== _root.findSending) {
                            _root.findSending = on
                            _root._saveState()
                        }
                    }
                }

                // The pad sections, "Space between groups" apart (S139).
                ColumnLayout {
                    objectName: "xboxPadSections"
                    Layout.fillWidth: true
                    spacing: Style.dp(_appear.groupSpacing)

                    Repeater {
                        id: _sections
                        model: _pads
                        delegate: XboxPadCard {
                            Layout.fillWidth: true
                            open: _root.isPadOpen(padId)
                            running: _root.running
                            appear: _appear
                            findText: _find.text
                            findType: _find.typeValue
                            findSending: _root.findSending
                            filtering: _find.filtering
                            onToggleRequested: _root.setPadOpen(padId, !open)
                            onClearFilters: _find.clear()
                        }
                    }
                }
            }
        }

        // The list's own Appearance (05 S125, AP2), kept in program
        // settings under "xbox-output".
        PageAppearance {
            id: _appear
            objectName: "xboxOutputAppearance"
            visible: _sections.count > 0 && displayOpen
            pageKey: "xbox-output"
            buttonName: "xboxOutputAppearanceButton"
            title: "Xbox Output View — Appearance"
            liveOptions: true
        }
    }
}
