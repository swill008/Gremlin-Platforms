// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Controls.Universal as U
import Gremlin.Style

// Print & Export (Button Map, File > Print & Export): the page as it will
// come out (a preview of the print area on the paper, inside its margins,
// drawn by the same hidden copy of the map as every print and export), the
// paper, orientation, margins, scale and background (kept with the map),
// and every print and export in one place. A window of its own, so the
// print area can be moved and resized on the map while it is open.
Window {
    id: _win
    // The Button Map window (DialogJoystickButtonMap): its settings and
    // exports.
    property var host: null

    title: "Print & Export"
    flags: Qt.Tool | Qt.WindowTitleHint | Qt.WindowCloseButtonHint
    // Kept inside the screen at any UI scale (as the other tool windows).
    // No width/height binding: ToolWindowMemory sets the size once when
    // the window opens (saved size, or its default fitted to the screen);
    // a binding on Screen would re-run on another screen and undo it.
    minimumWidth: Style.fitWidth(Style.dp(560), Screen)
    minimumHeight: Style.fitHeight(Style.dp(400), Screen)
    color: Style.background
    U.Universal.theme: Style.theme

    ToolWindowMemory {
        host: _win
        name: "print-export"
        defaultWidth: Style.fitWidth(Style.dp(760), Screen)
        defaultHeight: Style.fitHeight(Style.dp(720), Screen)
    }

    readonly property var setup: host ? host.printSetup : ({})
    // An export is being drawn or written.
    readonly property bool exportBusy: !!host && host.exportBusy === true
    readonly property bool onPaper: !!setup.paper && setup.paper !== "fit"
    readonly property bool metric: /^a[345]$/.test(String(setup.paper || ""))
    // The paper Freeform (As Drawn) goes back to when it is unticked.
    property string lastPaper: "letter"
    onSetupChanged: {
        var paper = String(setup.paper || "")
        if (paper.length && paper !== "fit")
            lastPaper = paper
    }
    // The preview: a picture of the whole page, cut to the print area as it
    // moves (nothing is drawn while the area is dragged, so it keeps up),
    // and once the area rests, the area drawn as the export draws it. Grab
    // results are kept: their urls are only good while they live.
    property var pageResult: null
    property string pageKey: ""
    property var shotResult: null
    property string shotKey: ""
    // The print area now ({fx, fy, fw, fh} of the page; null: all of it).
    property var area: null
    readonly property var areaNow: (area && area.fw > 0 && area.fh > 0)
                                   ? area : { fx: 0, fy: 0, fw: 1, fh: 1 }
    readonly property string lightKey: setup.light ? "light" : "dark"
    readonly property string areaKey: JSON.stringify(areaNow) + lightKey
    // The sharp picture is of the area as it is now.
    readonly property bool sharp: !!shotResult && shotKey === areaKey
    // Bumped when anything the result depends on changes.
    property int rev: 0
    // The export's size in pixels.
    readonly property var pixels: { rev; return host ? host.exportPixels() : { w: 0, h: 0 } }

    readonly property var papers: [
        { value: "letter", text: "Letter (8.5 × 11 in)" },
        { value: "legal", text: "Legal (8.5 × 14 in)" },
        { value: "tabloid", text: "Tabloid (11 × 17 in)" },
        { value: "a3", text: "A3 (297 × 420 mm)" },
        { value: "a4", text: "A4 (210 × 297 mm)" },
        { value: "a5", text: "A5 (148 × 210 mm)" }
    ]
    readonly property var margins: [
        { value: "none", inch: "None", mm: "None" },
        { value: "quarter", inch: "¼ in", mm: "6 mm" },
        { value: "half", inch: "½ in", mm: "13 mm" }
    ]

    function indexOfValue(list, value) {
        for (var i = 0; i < list.length; i++) {
            if (list[i].value === value)
                return i
        }
        return 0
    }

    // The page's size in inches: the paper, or for "fit" the print area at
    // 96 pixels an inch (the PDF's page).
    function pageInches() {
        if (!host)
            return { w: 8.5, h: 11 }
        var p = host.paperInches[setup.paper]
        if (!p)
            return { w: Math.max(1, pixels.w) / 96, h: Math.max(1, pixels.h) / 96 }
        return setup.landscape ? { w: p[1], h: p[0] } : { w: p[0], h: p[1] }
    }

    // How finely the area prints on the paper: it fills the space inside
    // the margins.
    function dpi() {
        var page = pageInches()
        var m = 2 * marginInches()
        var w = Math.max(0.1, page.w - m)
        var h = Math.max(0.1, page.h - m)
        return Math.round(Math.min(w > 0 ? pixels.w / w : 0, h > 0 ? pixels.h / h : 0))
    }

    function marginInches() {
        return onPaper && host ? (host.marginInches[setup.margin] || 0) : 0
    }

    function _dpr() { return Screen.devicePixelRatio > 0 ? Screen.devicePixelRatio : 1 }

    // The map changed: a new page picture, then the sharp one.
    function refreshSoon() {
        rev++
        if (visible) {
            _pageTimer.restart()
            _sharpTimer.restart()
        }
    }

    // The print area moved: the crop follows at once; a sharp picture
    // waiting to be drawn is dropped, and asked for again once it rests.
    function areaMoved() {
        var e = host ? host._ed() : null
        area = e ? e.printArea : (host ? host.printArea : null)
        rev++
        if (!visible)
            return
        if (host)
            host.dropPreview("area")
        _sharpTimer.restart()
    }

    function renderPage() {
        if (!host || !visible)
            return
        var key = lightKey
        // Twice the preview's size: a small area shown large stays clear.
        var side = Style.dp(1040) * _dpr()
        host.renderPreview("page", side, side, function(result) {
            if (!result)
                return
            _win.pageResult = result
            _win.pageKey = key
        })
    }

    function renderSharp() {
        if (!host || !visible)
            return
        var key = areaKey
        var side = Style.dp(520) * _dpr()
        host.renderPreview("area", side, side, function(result) {
            if (!result)
                return
            _win.shotResult = result
            _win.shotKey = key
        })
    }

    onVisibleChanged: {
        if (!visible)
            return
        areaMoved()
        refreshSoon()
    }

    // The print area as moved or zoomed in the preview, kept with the map.
    function keepArea() {
        var e = host ? host._ed() : null
        if (e)
            e.printAreaEdited(false)
    }

    Timer {
        id: _wheelRest
        interval: 400
        onTriggered: _win.keepArea()
    }

    Timer {
        id: _pageTimer
        interval: 150
        onTriggered: _win.renderPage()
    }
    Timer {
        id: _sharpTimer
        interval: 300
        onTriggered: _win.renderSharp()
    }

    Connections {
        target: _win.host
        function onPrintAreaChanged() { _win.areaMoved() }
        function onPrintSetupChanged() { _win.refreshSoon() }
        function onPhotoOverrideChanged() { _win.refreshSoon() }
    }
    Connections {
        target: _win.host ? _win.host._ed() : null
        function onPrintAreaChanged() { _win.areaMoved() }
        function onHistoryChanged() { _win.refreshSoon() }
        function onActionLabelsChanged() { _win.refreshSoon() }
        function onChipTextModeChanged() { _win.refreshSoon() }
        function onUnboundTextChanged() { _win.refreshSoon() }
        function onPhotoLookUrlChanged() { _win.refreshSoon() }
        function onSavedStylesChanged() { _win.refreshSoon() }
    }

    Shortcut {
        sequence: "Esc"
        onActivated: _win.close()
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: Style.dp(12)
        spacing: Style.dp(14)

        // The page as it will come out.
        Rectangle {
            id: _pane
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumWidth: Style.dp(240)
            color: Style.bgCard
            radius: Style.dp(4)

            readonly property var inches: { _win.rev; return _win.pageInches() }
            readonly property real fit: Math.min((width - Style.dp(24)) / inches.w, (height - Style.dp(24)) / inches.h)

            Rectangle {
                id: _paper
                objectName: "printPreviewPage"
                width: _pane.inches.w * _pane.fit
                height: _pane.inches.h * _pane.fit
                anchors.centerIn: parent
                color: Style.paper
                border.color: Style.lineStrong

                // Inside the margins: the print area, as large as fits.
                Item {
                    id: _printable
                    readonly property real m: _win.marginInches() * _pane.fit
                    x: m
                    y: m
                    width: parent.width - 2 * m
                    height: parent.height - 2 * m

                    Rectangle {
                        anchors.fill: parent
                        visible: _printable.m > 0
                        color: Style.clear
                        border.color: Style.fgDisabled
                        border.width: 1
                    }

                    // The print area in its shape (as it is now), as large as
                    // fits inside the margins: the page picture cut to it,
                    // or once it rests the area drawn as the export draws it.
                    Item {
                        id: _content
                        objectName: "printPreviewArea"
                        readonly property var a: _win.areaNow
                        readonly property real pageAspect: 32000 / 18000
                        readonly property real aspect: pageAspect * a.fw / Math.max(1e-6, a.fh)
                        width: Math.min(parent.width, parent.height * aspect)
                        height: width / aspect
                        anchors.centerIn: parent
                        clip: true

                        Rectangle {
                            anchors.fill: parent
                            color: _win.setup.light ? Style.paper : Style.background
                        }
                        Image {
                            id: _crop
                            objectName: "printPreviewCrop"
                            visible: !_win.sharp && _win.pageKey === _win.lightKey
                            width: _content.width / Math.max(1e-6, _content.a.fw)
                            height: _content.height / Math.max(1e-6, _content.a.fh)
                            x: -_content.a.fx * width
                            y: -_content.a.fy * height
                            source: _win.pageResult ? _win.pageResult.url : ""
                            cache: false
                            smooth: true
                            mipmap: true
                        }
                        Image {
                            id: _preview
                            objectName: "printPreviewImage"
                            visible: _win.sharp
                            anchors.fill: parent
                            source: _win.shotResult ? _win.shotResult.url : ""
                            cache: false
                            smooth: true
                            mipmap: true
                        }

                        // Drag the picture (it follows the hand: the print
                        // area moves the other way) and the wheel zooms about
                        // the pointer (in: a smaller area). The map's print
                        // area follows at once; saved with the map when the
                        // drag ends or the wheel rests. Not while it is locked.
                        MouseArea {
                            id: _pan
                            objectName: "printPreviewPan"
                            readonly property var ed: _win.host ? _win.host._ed() : null
                            readonly property bool canMove: !!ed && !ed.printAreaLocked
                            property point last: Qt.point(0, 0)
                            anchors.fill: parent
                            enabled: canMove
                            hoverEnabled: true
                            cursorShape: !canMove ? Qt.ArrowCursor
                                         : (pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor)
                            onPressed: (m) => { last = Qt.point(m.x, m.y) }
                            onPositionChanged: (m) => {
                                if (!pressed)
                                    return
                                var a = _content.a
                                ed.shiftPrintArea((m.x - last.x) / Math.max(1, width) * a.fw,
                                                  (m.y - last.y) / Math.max(1, height) * a.fh,
                                                  1, 0.5, 0.5)
                                last = Qt.point(m.x, m.y)
                            }
                            onReleased: _win.keepArea()
                            onWheel: (w) => {
                                var steps = w.angleDelta.y / 120
                                if (!steps)
                                    return
                                ed.shiftPrintArea(0, 0, Math.pow(0.85, steps),
                                                  Math.max(0, Math.min(1, w.x / Math.max(1, width))),
                                                  Math.max(0, Math.min(1, w.y / Math.max(1, height))))
                                _wheelRest.restart()
                            }
                        }
                    }
                }
            }
        }

        // The settings and the exports; they scroll when the window is too
        // short for them.
        Flickable {
            id: _side
            // A set width: with controls that fill it, it would take the
            // whole row from the preview.
            Layout.fillWidth: false
            Layout.preferredWidth: Style.dp(250)
            Layout.maximumWidth: Style.dp(250)
            Layout.fillHeight: true
            clip: true
            contentWidth: width
            contentHeight: _sideCol.height
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {
                policy: _side.contentHeight > _side.height ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
            }

            ColumnLayout {
                id: _sideCol
                width: _side.width
                height: Math.max(implicitHeight, _side.height)
                spacing: Style.dp(8)

                Label { text: "Paper"; color: Style.fgMuted }
                ComboBox {
                    id: _paperBox
                    objectName: "printPaper"
                    Layout.fillWidth: true
                    model: _win.papers
                    textRole: "text"
                    // Freeform (As Drawn) has no paper: the one it goes back
                    // to shows, greyed out.
                    enabled: _win.onPaper
                    currentIndex: _win.indexOfValue(_win.papers, _win.onPaper ? _win.setup.paper : _win.lastPaper)
                    onActivated: (i) => _win.host.setPrint("paper", _win.papers[i].value)
                }

                Label { text: "Orientation"; color: Style.fgMuted }
                RowLayout {
                    enabled: _win.onPaper
                    RadioButton {
                        text: "Portrait"
                        checked: !_win.setup.landscape
                        onClicked: _win.host.setPrint("landscape", false)
                    }
                    RadioButton {
                        text: "Landscape"
                        checked: !!_win.setup.landscape
                        onClicked: _win.host.setPrint("landscape", true)
                    }
                }

                Label { text: "Margins"; color: Style.fgMuted }
                ComboBox {
                    id: _marginBox
                    Layout.fillWidth: true
                    enabled: _win.onPaper
                    model: _win.margins.map(function(m) { return _win.metric ? m.mm : m.inch })
                    currentIndex: _win.indexOfValue(_win.margins, _win.setup.margin)
                    onActivated: (i) => _win.host.setPrint("margin", _win.margins[i].value)
                }

                Label { text: "Background"; color: Style.fgMuted }
                RowLayout {
                    RadioButton {
                        objectName: "printDark"
                        text: "Dark"
                        checked: !_win.setup.light
                        onClicked: _win.host.setPrint("light", false)
                    }
                    RadioButton {
                        objectName: "printLight"
                        text: "Light"
                        checked: !!_win.setup.light
                        onClicked: _win.host.setPrint("light", true)
                    }
                }

                // Custom: the scale, and Freeform (As Drawn): no paper, the
                // page takes the print area's own shape (stored as paper
                // "fit").
                Rectangle {
                    Layout.fillWidth: true
                    Layout.topMargin: Style.dp(4)
                    implicitHeight: _custom.implicitHeight + 2 * Style.dp(10)
                    color: Style.clear
                    radius: Style.dp(4)
                    border.color: Style.lineStrong
                    border.width: 1

                    ColumnLayout {
                        id: _custom
                        anchors.fill: parent
                        anchors.margins: Style.dp(10)
                        spacing: Style.dp(8)

                        Label { text: "Custom"; font.bold: true }
                        Label {
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            text: "Scale (100% = the photo's own size)"
                            color: Style.fgMuted
                        }
                        SpinBox {
                            id: _scaleBox
                            objectName: "printScale"
                            Layout.fillWidth: true
                            from: 10
                            to: 800
                            stepSize: 5
                            editable: true
                            value: Number(_win.setup.scale) || 100
                            textFromValue: (v) => v + "%"
                            valueFromText: (t) => parseInt(String(t).replace("%", "")) || 100
                            onValueModified: _win.host.setPrint("scale", value)
                        }
                        CheckBox {
                            objectName: "printFreeform"
                            text: "Freeform (As Drawn)"
                            checked: !_win.onPaper
                            onToggled: {
                                _win.host.setPrint("paper", checked ? "fit" : _win.lastPaper)
                                // A click replaces the binding: follow the setting again.
                                checked = Qt.binding(function() { return !_win.onPaper })
                            }
                        }
                    }
                }
                Label {
                    objectName: "printPixels"
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    color: Style.fg
                    text: {
                        var line = "Export: " + _win.pixels.w + " × " + _win.pixels.h + " pixels"
                        if (_win.onPaper)
                            return line + "\nOn the paper: " + _win.dpi() + " dpi"
                        return line + "\nPDF page: " + _win.pageInches().w.toFixed(1) + " × "
                               + _win.pageInches().h.toFixed(1) + " in (96 dpi)"
                    }
                }

                Item { Layout.fillHeight: true }

                Button {
                    Layout.fillWidth: true
                    text: "Print…"
                    onClicked: _win.host.printNow()
                }
                // One export at a time (07 S101): written in the
                // background, the window stays usable meanwhile.
                Button {
                    objectName: "printExportPdf"
                    Layout.fillWidth: true
                    text: "Export PDF…"
                    enabled: !_win.exportBusy
                    onClicked: _win.host.openExportFile("pdf")
                }
                RowLayout {
                    Layout.fillWidth: true
                    Button {
                        objectName: "printExportPng"
                        Layout.fillWidth: true
                        text: "Export PNG…"
                        enabled: !_win.exportBusy
                        onClicked: _win.host.openExportFile("png")
                    }
                    Button {
                        objectName: "printExportJpg"
                        Layout.fillWidth: true
                        text: "Export JPG…"
                        enabled: !_win.exportBusy
                        onClicked: _win.host.openExportFile("jpg")
                    }
                }
                Label {
                    objectName: "printExportBusy"
                    Layout.fillWidth: true
                    visible: _win.exportBusy
                    wrapMode: Text.WordWrap
                    color: Style.fgMuted
                    text: "Exporting…"
                }
                Button {
                    Layout.fillWidth: true
                    text: "Close"
                    onClicked: _win.close()
                }
            }
        }
    }
}
