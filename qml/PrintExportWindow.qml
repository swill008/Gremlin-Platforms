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
    width: Style.fitWidth(Style.dp(760), Screen)
    height: Style.fitHeight(Style.dp(640), Screen)
    minimumWidth: Style.fitWidth(Style.dp(560), Screen)
    minimumHeight: Style.fitHeight(Style.dp(400), Screen)
    color: Style.background
    U.Universal.theme: Style.theme

    ToolWindowMemory {
        host: _win
        name: "print-export"
        defaultWidth: Style.dp(760)
        defaultHeight: Style.dp(640)
    }

    readonly property var setup: host ? host.printSetup : ({})
    readonly property bool onPaper: !!setup.paper && setup.paper !== "fit"
    readonly property bool metric: /^a[345]$/.test(String(setup.paper || ""))
    // The preview picture (the print area as exported, on its background):
    // the grab result is kept, its url is only good while it lives.
    property var shotResult: null
    readonly property url shot: shotResult ? shotResult.url : ""
    // Bumped when anything the result depends on changes.
    property int rev: 0
    // The export's size in pixels.
    readonly property var pixels: { rev; return host ? host.exportPixels() : { w: 0, h: 0 } }

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

    // A new preview, a moment after the last change.
    function refreshSoon() {
        rev++
        if (visible)
            _refresh.restart()
    }

    function refresh() {
        if (!host || !visible)
            return
        var dpr = Screen.devicePixelRatio > 0 ? Screen.devicePixelRatio : 1
        host.renderPreview(Style.dp(520) * dpr, Style.dp(520) * dpr, function(result) {
            if (result)
                _win.shotResult = result
        })
    }

    onVisibleChanged: if (visible) refreshSoon()

    Timer {
        id: _refresh
        interval: 250
        onTriggered: _win.refresh()
    }

    Connections {
        target: _win.host
        function onPrintAreaChanged() { _win.refreshSoon() }
        function onPrintSetupChanged() { _win.refreshSoon() }
    }
    Connections {
        target: _win.host
        function onPhotoOverrideChanged() { _win.refreshSoon() }
    }
    Connections {
        target: _win.host ? _win.host._ed() : null
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

                    // The print area in its shape, as large as fits inside
                    // the margins: drawn as the export draws it.
                    Image {
                        id: _preview
                        objectName: "printPreviewImage"
                        readonly property real aspect: _win.pixels.h > 0 ? _win.pixels.w / _win.pixels.h : 1
                        width: Math.min(parent.width, parent.height * aspect)
                        height: width / aspect
                        anchors.centerIn: parent
                        source: _win.shot
                        cache: false
                        smooth: true
                        mipmap: true
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
                    text: "Close"
                    onClicked: _win.close()
                }
            }
        }
    }
}
