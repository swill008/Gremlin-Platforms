# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The real Home page (qml/StatusPage.qml with its StatusCards) off-screen
over a stand-in card model, driven with real mouse events. Prints
"RESULT name json" per value, "ERROR ..." for a failing step, "WARN ..." per
QML warning, then "done". test_home_card_drag.py, test_home_card_size.py and
test_home_image_menu.py, test_home_compact_thumb.py and test_home_band.py run
it in its own process:

    python test/unit/home_cards_smoke.py <out_dir> <drag|size|image|compact|band>

HOME_QML_DIR points it at another qml folder (a copy with the old files,
to show a test fails on the old code).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parents[1]

# The stand-in model: four input cards a, b, c, d in one pane, no stacks.
# Card "b" has a Device Image (hasImage). It records what the page asks.
# piles: a stack's members by any of its slugs (band mode stacks b and c).
_WRAPPER = """
import QtQuick
import QtQuick.Controls

import "{qml}"

ApplicationWindow {{
    id: _win
    width: {width}
    height: 900
    visible: true

    QtObject {{
        id: _fake
        property string splitMode: "none"
        property bool compactView: false
        property bool canUndo: false
        property bool canRedo: false
        property string focusedSlug: ""
        property var order: ["a", "b", "c", "d"]
        property var widths: ({{}})
        property var piles: ({{}})
        property var calls: []
        signal panesChanged()
        signal claimsChanged()
        signal cantSendChanged()
        signal targetsChanged()
        signal namesChanged()
        signal lastChanged()
        signal focusChanged()
        signal modelReset()
        signal rowsInserted()
        signal rowsRemoved()
        function note(text) {{ var c = calls.slice(); c.push(text); calls = c }}
        function visibleCount() {{ return order.length }}
        function pileLeaders(dir) {{ return order }}
        function pileMembers(slug) {{ return piles[slug] || [slug] }}
        function cardMap(slug) {{
            return {{ slug: slug, name: "Card " + slug, rawName: "Card " + slug,
                     guid: "", direction: slug === "x" ? "dest" : "source",
                     status: "Connected", bus: "HID", tab: "physical",
                     isModule: true, isStub: false, hasImage: slug === "b",
                     photo: "" }}
        }}
        function cardWidth(slug) {{ return widths[slug] || 0 }}
        function cardHeight(slug) {{ return 0 }}
        function setPileSize(slug, w, h) {{
            note("size " + slug + " " + w + " " + h)
        }}
        function dropSlugBefore(slug, before) {{
            note("drop " + slug + " before " + before)
        }}
        function setCardImage(slug, url) {{
            note("set " + slug + " " + url)
            return true
        }}
        function removeCardImage(slug) {{ note("remove " + slug); return true }}
        function hideSelected(csv) {{ note("hide " + csv) }}
        function resetSelectedSizes(csv) {{ note("reset " + csv) }}
        function undo() {{ note("undo") }}
        function redo() {{ note("redo") }}
        function setFocus(slug) {{}}
        function raiseSlug(slug) {{}}
        function hiddenList() {{ return [] }}
        function hiddenCards() {{ return [] }}
    }}

    StatusPage {{
        id: _page
        objectName: "homePage"
        anchors.fill: parent
        model: _fake
    }}

    function cardOf(slug) {{
        var list = _page._liveCards
        for (var i = 0; i < list.length; ++i)
            if (list[i] && list[i].slug === slug)
                return list[i]
        return null
    }}
    function at(slug) {{
        var c = cardOf(slug)
        var p = c.mapToItem(null, 0, 0)
        return [Math.round(p.x), Math.round(p.y),
                Math.round(c.width), Math.round(c.height)]
    }}
    // The card's own right-click menu (its ContextMenu).
    function menuOf(slug) {{
        var c = cardOf(slug)
        for (var i = 0; c && i < c.data.length; ++i) {{
            var d = c.data[i]
            if (d && typeof d.describe === "function"
                    && typeof d.activate === "function")
                return d
        }}
        return null
    }}
    // The first item named so inside the card (depth first).
    function inCard(slug, name) {{
        var found = null
        function walk(it) {{
            if (found || !it) return
            if (it.objectName === name) {{ found = it; return }}
            for (var i = 0; i < it.children.length; ++i) walk(it.children[i])
        }}
        walk(cardOf(slug))
        return found
    }}
    // Compact thumb, glyph and big picture of a card (D-03-COMPACT-THUMB).
    function looks(slug) {{
        var t = inCard(slug, "cardThumb")
        var g = inCard(slug, "deviceThumbGlyph")
        var p = inCard(slug, "cardPhoto")
        return {{ thumb: t ? t.visible : null,
                 thumbSize: t ? [Math.round(t.width), Math.round(t.height)] : null,
                 thumbPicture: t ? t.showsPicture : null,
                 glyph: g && g.visible ? g.text : "",
                 photoSource: p ? String(p.source) : null,
                 photoReady: p ? p.status === Image.Ready : null,
                 height: Math.round(cardOf(slug).height) }}
    }}
    // The first item named so on the page (depth first).
    function onPage(name) {{
        var found = null
        function walk(it) {{
            if (found || !it) return
            if (it.objectName === name) {{ found = it; return }}
            for (var i = 0; i < it.children.length; ++i) walk(it.children[i])
        }}
        walk(_page)
        return found
    }}
    function sel() {{ return _page.selectedSlugs.slice().sort().join(",") }}
    function child(name) {{
        for (var i = 0; i < _page.children.length; ++i)
            if (_page.children[i].objectName === name)
                return _page.children[i]
        return null
    }}
}}
"""


def main() -> None:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["QT_QUICK_CONTROLS_STYLE"] = "GremlinStyle"
    os.environ["QT_FILE_SELECTORS"] = "Universal"
    os.environ.setdefault(
        "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    )
    sys.path.insert(0, str(_ROOT))
    sys.stdout.reconfigure(encoding="utf-8")  # pyright: ignore[reportAttributeAccessIssue]
    out = Path(sys.argv[1])
    mode = sys.argv[2]
    out.mkdir(parents=True, exist_ok=True)
    qml_dir = Path(os.environ.get("HOME_QML_DIR") or (_ROOT / "qml"))

    import shiboken6
    from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest

    import gremlin.ui.device  # noqa: F401  (Gremlin.Device)
    import gremlin.ui.folder_memory  # noqa: F401  (FilePicker)

    def result(name: str, value: object) -> None:
        print(f"RESULT {name} {json.dumps(value)}", flush=True)

    class FakeBackend(QtCore.QObject):
        changed = QtCore.Signal()
        uiScale = QtCore.Property(int, fget=lambda self: 100, notify=changed)
        gremlinActive = QtCore.Property(bool, fget=lambda self: False, notify=changed)

    app = QtGui.QGuiApplication(sys.argv[:1])
    QtQml.qmlRegisterSingletonType(
        QtCore.QUrl.fromLocalFile(str(qml_dir / "Style.qml")),
        "Gremlin.Style",
        1,
        0,
        "Style",
    )
    engine = QtQml.QQmlApplicationEngine()
    engine.addImportPath(str(_ROOT / "theme"))
    backend = FakeBackend()
    engine.rootContext().setContextProperty("backend", backend)
    warnings: list[str] = []
    engine.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))
    wrapper = out / "HomeCardsHarness.qml"
    width = 800 if mode == "size" else 1400
    wrapper.write_text(
        _WRAPPER.format(qml=qml_dir.as_uri(), width=width), encoding="utf-8"
    )
    engine.load(QtCore.QUrl.fromLocalFile(str(wrapper)))
    roots = engine.rootObjects()
    if not roots:
        print("ERROR window did not load", flush=True)
        for w in warnings:
            print(f"WARN {w}", flush=True)
        print("done", flush=True)
        return
    win = roots[0]
    quick = shiboken6.wrapInstance(
        shiboken6.getCppPointer(win)[0], QtQuick.QQuickWindow
    )
    QtTest.QTest.qWait(500)

    def on(obj: QtCore.QObject, code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(obj), obj, code)
        value = expr.evaluate()
        if expr.hasError():
            print(f"ERROR {code}: {expr.error().toString()}", flush=True)
            return None
        value = value[0] if isinstance(value, tuple) else value
        if isinstance(value, QtQml.QJSValue):
            value = value.toQObject() if value.isQObject() else value.toVariant()
        return value

    def ev(code: str) -> object:
        return on(win, code)

    def pos_of(slug: str, dx: int = 40, dy: int = 40) -> QtCore.QPoint:
        x, y, _w, _h = ev(f"at({json.dumps(slug)})")  # type: ignore[misc]
        return QtCore.QPoint(int(x) + dx, int(y) + dy)

    left = QtCore.Qt.MouseButton.LeftButton
    none = QtCore.Qt.KeyboardModifier.NoModifier

    def move(p: QtCore.QPoint) -> None:
        QtTest.QTest.mouseMove(quick, p)
        QtTest.QTest.qWait(60)

    if mode == "drag":
        result("before", {s: ev(f"at('{s}')") for s in "abcd"})
        start = pos_of("a")
        QtTest.QTest.mousePress(quick, left, none, start)
        QtTest.QTest.qWait(50)
        # 3 px: not a drag yet (it starts at 4 dp).
        move(start + QtCore.QPoint(3, 0))
        result("drag-at-3px", ev("_page.dragSlug"))
        move(start + QtCore.QPoint(5, 0))
        result("drag-at-5px", ev("_page.dragSlug"))
        QtTest.QTest.qWait(300)
        # Over card c, right of its middle: the drop spot is before d.
        cx, cy, cw, _ch = ev("at('c')")  # type: ignore[misc]
        target = QtCore.QPoint(int(cx + cw * 0.75), int(cy) + 40)
        for step in range(1, 9):
            move(start + (target - start) * step / 8)
        QtTest.QTest.qWait(300)
        result("during", {s: ev(f"at('{s}')") for s in "abcd"})
        result("insert-before", ev("_page.insertBefore"))
        result(
            "picture",
            ev(
                "var f = child('homeDragPicture'); f ? [f.visible, f.opacity,"
                " String(f.source).length > 0, f.status === Image.Ready,"
                " Math.round(f.width), Math.round(f.height),"
                " Math.round(f.x), Math.round(f.y)] : null"
            ),
        )
        result("pointer", [target.x(), target.y()])
        result(
            "line",
            ev(
                "var l = child('homeDropLine'); l ? [l.visible, Math.round(l.width),"
                " Qt.colorEqual(l.color, Style.info), Math.round(l.x), Math.round(l.y),"
                " Math.round(l.height)] : null"
            ),
        )
        result("dragged-opacity", ev("cardOf('a').opacity"))
        result("dp2", ev("Style.dp(2)"))
        quick.grabWindow().save(str(out / "drag.png"))
        QtTest.QTest.mouseRelease(quick, left, none, target)
        QtTest.QTest.qWait(300)
        result("calls", ev("_fake.calls"))
        result("after-drop", [ev("_page.dragSlug"), ev("cardOf('a').opacity")])
    elif mode == "size":
        # Limits (03 S83): 220-1080 wide, 140-780 tall; the picture decoded for
        # the largest card.
        ev("_fake.widths = { a: 1080 }; _page.pileRev++")
        QtTest.QTest.qWait(300)
        result("flow-width", ev("cardOf('a').parent.parent.width"))
        result("wide-card", ev("at('a')"))
        result(
            "decode",
            ev(
                "var c = cardOf('b'); var found = null;"
                " function walk(it) { if (found) return;"
                "   if (it.sourceSize !== undefined"
                "       && it.fillMode === Image.PreserveAspectFit)"
                "     { found = it; return }"
                "   for (var i = 0; i < it.children.length; ++i) walk(it.children[i]) }"
                " walk(c);"
                " found ? [found.sourceSize.width, found.sourceSize.height] : null"
            ),
        )
        result("dpr", ev("Screen.devicePixelRatio"))
        # A resize with the corner handle is held to the window's width.
        bx, by, bw, bh = ev("at('b')")  # type: ignore[misc]
        corner = QtCore.QPoint(int(bx + bw - 6), int(by + bh - 6))
        QtTest.QTest.mousePress(quick, left, none, corner)
        QtTest.QTest.qWait(50)
        for step in range(1, 6):
            move(corner + QtCore.QPoint(300 * step, 0))
        QtTest.QTest.mouseRelease(quick, left, none, corner + QtCore.QPoint(1500, 0))
        QtTest.QTest.qWait(200)
        result("calls", ev("_fake.calls"))
        # The limits themselves (fitWidth 0: no window limit).
        result(
            "clamp",
            ev(
                "var c = cardOf('b'); c.fitWidth = 0;"
                " [c._clampW(99999), c._clampH(99999), c._clampW(1), c._clampH(1)]"
            ),
        )
        result(
            "clamp-fit", ev("var c = cardOf('c'); c.fitWidth = 500; c._clampW(99999)")
        )
    elif mode == "image":
        page = win.findChild(QtCore.QObject, "homePage")

        def device_rows(slug: str) -> list[str]:
            if not ev(f"menuOf('{slug}') !== null"):
                print(f"ERROR no menu on {slug}", flush=True)
                return []
            p = pos_of(slug, 30, 30)
            QtTest.QTest.mouseClick(quick, QtCore.Qt.MouseButton.RightButton, none, p)
            QtTest.QTest.qWait(250)
            rows = str(ev(f"menuOf('{slug}').describe().join('|')") or "").split("|")
            if "> Device" in rows:
                ev(f"menuOf('{slug}').activate('Device')")
                rows = str(ev(f"menuOf('{slug}').describe().join('|')") or "").split(
                    "|"
                )
            return rows

        def picker() -> QtCore.QObject | None:
            for dialog in page.findChildren(QtCore.QObject, "filePickerFileDialog"):
                owner = dialog.parent()
                if owner is not None and owner.property("title") == "Choose Image":
                    return owner
            return None

        result("a-has-image", ev("cardOf('a').hasImage"))
        result("b-has-image", ev("cardOf('b').hasImage"))
        result("a-rows", device_rows("a"))
        result("a-add-ran", ev("menuOf('a').activate('Add Image…')"))
        QtTest.QTest.qWait(200)
        pk = picker()
        if pk is None:
            print("ERROR no Choose Image FilePicker on the page", flush=True)
        else:
            dialog = pk.findChild(QtCore.QObject, "filePickerFileDialog")
            if dialog is not None:
                on(dialog, "close()")
            QtTest.QTest.qWait(100)
            on(pk, "_accept('file:///C:/pick/stick.png')")
            QtTest.QTest.qWait(200)
        ev("menuOf('a').close()")
        QtTest.QTest.qWait(100)
        result("b-rows", device_rows("b"))
        result("b-remove-ran", ev("menuOf('b').activate('Remove Image')"))
        QtTest.QTest.qWait(200)
        result("calls", ev("_fake.calls"))
    elif mode == "compact":
        # Card b gets a real picture; a has none (D-03-COMPACT-THUMB).
        png = out / "stick.png"
        img = QtGui.QImage(64, 48, QtGui.QImage.Format.Format_RGB32)
        img.fill(QtGui.QColor(40, 120, 200))
        img.save(str(png))
        url = QtCore.QUrl.fromLocalFile(str(png)).toString()
        result("url", url)
        ev(f"cardOf('b').photo = {json.dumps(url)}")
        QtTest.QTest.qWait(400)
        result("full", {s: ev(f"looks('{s}')") for s in "ab"})
        ev("_fake.compactView = true")
        QtTest.QTest.qWait(400)
        result("compact", {s: ev(f"looks('{s}')") for s in "ab"})
        result("dp40", ev("Style.dp(40)"))
        ev("_fake.compactView = false")
        QtTest.QTest.qWait(400)
        result("full-again", {s: ev(f"looks('{s}')") for s in "ab"})
    elif mode == "band":
        _band(ev, quick, result, move, out)
    for w in warnings:
        print(f"WARN {w}", flush=True)
    print("done", flush=True)
    app.processEvents()
    os._exit(0)


def _band(ev, quick, result, move, out: Path) -> None:  # noqa: ANN001
    """The selection box on empty space (D-03-HOME-BAND): piles a, b (a
    stack of b and c), d ... w, four a row (six rows), so the page scrolls."""
    from PySide6 import QtCore, QtGui, QtTest

    left = QtCore.Qt.MouseButton.LeftButton
    none = QtCore.Qt.KeyboardModifier.NoModifier
    shift = QtCore.Qt.KeyboardModifier.ShiftModifier
    ev(
        "_fake.piles = { b: ['b', 'c'], c: ['b', 'c'] };"
        " _fake.order = 'abdefghijklmnopqrstuvw'.split('');"
        " _page.pileRev++"
    )
    QtTest.QTest.qWait(500)
    scroll = "onPage('homeAllPaneScroll')"

    def flick_y() -> float:
        return float(ev(f"{scroll}.contentY") or 0)  # type: ignore[arg-type]

    def xy(slug: str) -> list[int]:
        return ev(f"at('{slug}')")  # type: ignore[return-value]

    _ax, ay, _aw, _ah = xy("a")
    ex, _ey, ew, _eh = xy("e")
    bx, _by, bw, _bh = xy("b")
    result("row", [xy(s)[1] for s in "abde"])
    result("scrollable", ev(f"{scroll}.contentHeight > {scroll}.height"))
    # Empty space right of the first row.
    start = QtCore.QPoint(ex + ew + 40, ay + 30)
    result("start-empty", ev(f"_page.cardUnder({start.x()}, {start.y()}) === null"))
    y0 = flick_y()
    QtTest.QTest.mousePress(quick, left, none, start)
    QtTest.QTest.qWait(50)
    target = QtCore.QPoint(bx + bw // 2, ay + 60)
    for step in range(1, 9):
        move(start + (target - start) * step / 8)
    result(
        "band",
        ev(
            "var b = onPage('homeAllPaneBand'); b ? [b.visible,"
            " Qt.colorEqual(b.border.color, Style.warn),"
            " Math.round(b.width), Math.round(b.height)] : null"
        ),
    )
    result("band-selected", ev("sel()"))
    result("band-scrolled", flick_y() - y0)
    quick.grabWindow().save(str(out / "band.png"))
    QtTest.QTest.mouseRelease(quick, left, none, target)
    QtTest.QTest.qWait(100)
    result("band-after", [ev("onPage('homeAllPaneBand').visible"), ev("sel()")])
    # The card menu acts on the selection.
    dx, dy, _dw, _dh = xy("d")
    QtTest.QTest.mouseClick(
        quick, QtCore.Qt.MouseButton.RightButton, none, QtCore.QPoint(dx + 30, dy + 30)
    )
    QtTest.QTest.qWait(250)
    rows = str(ev("menuOf('d').describe().join('|')") or "").split("|")
    if "> Cards" in rows:
        ev("menuOf('d').activate('Cards')")
    rows = str(ev("menuOf('d').describe().join('|')") or "").split("|")
    result("card-rows", [r.strip() for r in rows if "Selected" in r])
    ev("menuOf('d').activate('Reset Size of Selected Cards')")
    QtTest.QTest.qWait(100)
    result("after-reset", ev("sel()"))
    ev("menuOf('d').activate('Hide Selected Cards')")
    QtTest.QTest.qWait(100)
    result("menu-calls", ev("_fake.calls"))
    result("after-hide", ev("sel()"))

    # A box over e alone, then Shift + a box over the second row's first card.
    QtTest.QTest.mousePress(quick, left, none, start)
    on_e = QtCore.QPoint(ex + ew - 20, ay + 40)
    move(start + (on_e - start) / 2)
    move(on_e)
    QtTest.QTest.mouseRelease(quick, left, none, on_e)
    result("only-e", ev("sel()"))
    fx, fy, fw, _fh = xy("f")
    row2 = QtCore.QPoint(ex + ew + 40, fy + 30)
    on_f = QtCore.QPoint(fx + fw - 20, fy + 40)
    QtTest.QTest.mousePress(quick, left, shift, row2)
    move(row2 + (on_f - row2) / 2)
    move(on_f)
    QtTest.QTest.mouseRelease(quick, left, shift, on_f)
    result("shift-added", ev("sel()"))
    # A plain click on empty space clears.
    QtTest.QTest.mouseClick(quick, left, none, start)
    QtTest.QTest.qWait(100)
    result("click-cleared", ev("sel()"))

    # The wheel still scrolls.
    y0 = flick_y()
    wheel = QtGui.QWheelEvent(
        QtCore.QPointF(start), QtCore.QPointF(start), QtCore.QPoint(0, 0),
        QtCore.QPoint(0, -240), QtCore.Qt.MouseButton.NoButton, none,
        QtCore.Qt.ScrollPhase.NoScrollPhase, False,
    )
    QtGui.QGuiApplication.sendEvent(quick, wheel)
    QtTest.QTest.qWait(400)
    result("wheel-scrolled", flick_y() - y0)
    ev(f"{scroll}.contentY = 0")
    QtTest.QTest.qWait(100)

    # Held at the bottom edge, the page scrolls and the box takes more cards.
    y0 = flick_y()
    QtTest.QTest.mousePress(quick, left, none, start)
    bottom = QtCore.QPoint(start.x() - 300, quick.height() - 16)
    move(start + QtCore.QPoint(-20, 20))
    result("edge-before", ev("_page.selectedSlugs.length"))
    for step in range(1, 6):
        move(start + (bottom - start) * step / 5)
    held = ev("_page.selectedSlugs.length")
    QtTest.QTest.qWait(800)
    result("edge-scrolled", flick_y() - y0)
    result("edge-selected", [held, ev("_page.selectedSlugs.length")])
    # Esc clears, even with the box still held.
    QtTest.QTest.keyClick(quick, QtCore.Qt.Key.Key_Escape)
    QtTest.QTest.qWait(50)
    result("esc", [ev("sel()"), ev("onPage('homeAllPaneBand').visible")])
    QtTest.QTest.mouseRelease(quick, left, none, bottom)
    QtTest.QTest.qWait(50)

    # The empty-space menu: Undo / Redo beside its title.
    ev("_fake.canUndo = true")
    result(
        "empty-header",
        ev("JSON.stringify(_page.emptyMenuModel().header.map(function(h) {"
           " return [h.label, h.enabled] }))"),
    )
    ev("_page.emptyMenuModel().header[0].run()")
    QtTest.QTest.qWait(100)
    result("empty-undo", ev("_fake.calls[_fake.calls.length - 1]"))


def run(tmp_path: Path, mode: str, qml_dir: Path | None = None) -> dict[str, object]:
    """Runs this file in its own process; the RESULT values by name."""
    import proc_tree  # pyright: ignore[reportMissingImports]  (test/)

    profile = tmp_path / "profile"
    profile.mkdir(exist_ok=True)
    env = {
        **os.environ,
        "QT_QPA_PLATFORM": "offscreen",
        "PYTHONIOENCODING": "utf-8",
        "USERPROFILE": str(profile),
    }
    if qml_dir is not None:
        env["HOME_QML_DIR"] = str(qml_dir)
    proc = proc_tree.run(
        [sys.executable, str(Path(__file__).resolve()), str(tmp_path / "out"), mode],
        text=True,
        encoding="utf-8",
        timeout=120,
        env=env,
    )
    lines = proc.stdout.splitlines()
    assert "done" in lines, (proc.stdout[-2000:], proc.stderr[-3000:])
    errors = [line for line in lines if line.startswith("ERROR")]
    assert errors == [], (errors, proc.stderr[-2000:])
    found: dict[str, object] = {
        "warnings": [ln for ln in lines if ln.startswith("WARN")]
    }
    for line in lines:
        if line.startswith("RESULT "):
            _, name, value = line.split(" ", 2)
            found[name] = json.loads(value)
    return found


if __name__ == "__main__":
    main()
