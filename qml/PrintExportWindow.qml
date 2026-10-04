// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Controls.Universal as U
import Gremlin.Style

// Print & Export (Button Map, File > Print & Export): the page as it will
// come out (a live preview of the print area on the paper, inside its
// margins), the paper, orientation, margins and scale (kept with the map),
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
    width: Style.fitWidth(Style.dp(760), Screen)
    height: Style.fitHeight(Style.dp(520), Screen)
    minimumWidth: Style.fitWidth(Style.dp(560), Screen)
    minimumHeight: Style.fitHeight(Style.dp(400), Screen)
    color: Style.background
    U.Universal.theme: Style.theme

    ToolWindowMemory {
        host: _win
        name: "print-export"
        defaultWidth: Style.dp(760)
        defaultHeight: Style.dp(520)
    }

    readonly property var setup: host ? host.printSetup : ({})
    readonly property bool onPaper: !!setup.paper && setup.paper !== "fit"
    readonly property bool metric: /^a[345]$/.test(String(setup.paper || ""))
    // The preview picture (the print area, as exported) and its size.
    property url shot: ""
    property size shotSize: Qt.size(0, 0)
    // Bumped when anything the result depends on changes.
    property int rev: 0

    readonly property var papers: [
        { value: "fit", text: "Fit to area" },
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

    // The page's size in inches (paper, or the area's own shape for "fit").
    function pageInches() {
        if (!host)
            return { w: 8.5, h: 11 }
        var p = host.paperInches[setup.paper]
        if (!p) {
            var e = host._ed()
            var r = e ? e.printAreaRect() : { w: 4, h: 3 }
            return { w: 8 * r.w / Math.max(1, Math.max(r.w, r.h)), h: 8 * r.h / Math.max(1, Math.max(r.w, r.h)) }
        }
        return setup.landscape ? { w: p[1], h: p[0] } : { w: p[0], h: p[1] }
    }

    function marginInches() {
        return onPaper && host ? (host.marginInches[setup.margin] || 0) : 0
    }

    // A new preview, a moment after the last change (the map is drawn once
    // without its editing marks for it).
    function refreshSoon() {
        rev++
        if (visible)
            _refresh.restart()
    }

    function refresh() {
        var e = host ? host._ed() : null
        if (!e || !visible)
            return
        var r = e.printAreaRect()
        var q = Math.min(2, Style.dp(420) / Math.max(1, r.w, r.h))
        e.printLight = _opts().values["light-page"] === true
        e.exporting = true
        e.repaint()
        Qt.callLater(function() {
            var ok = e.grabToImage(function(result) {
                e.exporting = false
                e.printLight = false
                e.repaint()
                if (!result)
                    return
                _win.shot = result.url
                _win.shotSize = Qt.size(e.width * q, e.height * q)
                _win.shotRect = Qt.rect(r.x * q, r.y * q, r.w * q, r.h * q)
            }, Qt.size(Math.round(e.width * q), Math.round(e.height * q)))
            if (!ok) {
                e.exporting = false
                e.printLight = false
                e.repaint()
            }
        })
    }
    property rect shotRect: Qt.rect(0, 0, 0, 0)

    function _opts() { return host ? host.buttonMapOptions() : { values: {} } }

    onVisibleChanged: if (visible) refreshSoon()

    Timer {
        id: _refresh
        interval: 400
        onTriggered: _win.refresh()
    }

    Connections {
        target: _win.host
        function onPrintAreaChanged() { _win.refreshSoon() }
        function onPrintSetupChanged() { _win.refreshSoon() }
    }
    Connections {
        target: _win.host ? _win.host._ed() : null
        function onHistoryChanged() { _win.refreshSoon() }
        function onWidthChanged() { _win.refreshSoon() }
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

                    // The print area in its shape, as large as fits inside
                    // the margins: the picture of the map, cut to the area
                    // (the export's background behind it: dark, or white
                    // with Light Page for Exports, as the file will have).
                    Item {
                        id: _content
                        readonly property real aspect: _win.shotRect.width > 0
                            ? _win.shotRect.width / _win.shotRect.height : 1
                        width: Math.min(parent.width, parent.height * aspect)
                        height: width / aspect
                        anchors.centerIn: parent
                        clip: true

                        Rectangle {
                            anchors.fill: parent
                            color: _win._opts().values["light-page"] === true ? Style.paper : Style.background
                        }

                        Image {
                            id: _preview
                            objectName: "printPreviewImage"
                            readonly property real k: _content.width / Math.max(1, _win.shotRect.width)
                            x: -_win.shotRect.x * k
                            y: -_win.shotRect.y * k
                            width: _win.shotSize.width * k
                            height: _win.shotSize.height * k
                            source: _win.shot
                            cache: false
                            smooth: true
                        }
                    }
                }
            }
        }

        // The settings and the exports.
        ColumnLayout {
            // A set width: with controls that fill it, it would take the
            // whole row from the preview.
            Layout.fillWidth: false
            Layout.preferredWidth: Style.dp(250)
            Layout.maximumWidth: Style.dp(250)
            Layout.fillHeight: true
            spacing: Style.dp(8)

            Label { text: "Paper"; color: Style.fgMuted }
            ComboBox {
                id: _paperBox
                objectName: "printPaper"
                Layout.fillWidth: true
                model: _win.papers
                textRole: "text"
                currentIndex: _win.indexOfValue(_win.papers, _win.setup.paper)
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

            Label { text: "Scale (100% = the photo's own size)"; color: Style.fgMuted }
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
            Label {
                objectName: "printPixels"
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: Style.fg
                text: {
                    _win.rev
                    if (!_win.host)
                        return ""
                    var px = _win.host.exportPixels()
                    return "Export: " + px.w + " × " + px.h + " pixels"
                }
            }

            Item { Layout.fillHeight: true }

            Button {
                Layout.fillWidth: true
                text: "Print…"
                onClicked: _win.host.printView()
            }
            Button {
                Layout.fillWidth: true
                text: "Export PDF…"
                onClicked: _win.host.openExportFile("pdf")
            }
            RowLayout {
                Layout.fillWidth: true
                Button {
                    Layout.fillWidth: true
                    text: "Export PNG…"
                    onClicked: _win.host.openExportFile("png")
                }
                Button {
                    Layout.fillWidth: true
                    text: "Export JPG…"
                    onClicked: _win.host.openExportFile("jpg")
                }
            }
            Button {
                Layout.fillWidth: true
                text: "Export Modes…"
                enabled: !!_win.host && _win.host.profileModes.length > 0 && _win.host.targetGuid.length > 0
                onClicked: _win.host.openExportModes()
            }
            Button {
                Layout.fillWidth: true
                text: "Close"
                onClicked: _win.close()
            }
        }
    }
}
