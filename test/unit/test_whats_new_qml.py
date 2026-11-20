# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""01 S183: the What's New banner (under the toolbar), its window and the
Help > What's New… item.

The real WhatsNewBanner.qml and WindowWhatsNew.qml run off-screen in their
own process against a stand-in `whatsNew` model that records calls.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

_ROOT = pathlib.Path(__file__).resolve().parents[2]

_SCRIPT = r'''
import json, sys, tempfile, unittest.mock
from pathlib import Path

ROOT = Path(sys.argv[1])
sys.path.insert(0, str(ROOT))
import gremlin.util
gremlin.util.userprofile_path = unittest.mock.Mock(return_value=tempfile.mkdtemp())

from PySide6 import QtCore, QtGui, QtQml, QtQuick

app = QtGui.QGuiApplication(sys.argv[:1])
QtQml.qmlRegisterSingletonType(
    QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "Style.qml")),
    "Gremlin.Style", 1, 0, "Style",
)
import joystick_gremlin
joystick_gremlin.register_config_options()


class Model(QtCore.QObject):
    changed = QtCore.Signal()

    def __init__(self):
        super().__init__()
        self.calls, self._visible = [], True

    bannerVisible = QtCore.Property(
        bool, fget=lambda self: self._visible, notify=changed)
    bannerTitle = QtCore.Property(
        str, fget=lambda self: "Updated to 1.0.40", notify=changed)
    bannerMessage = QtCore.Property(
        str, fget=lambda self: "See what changed in this version.",
        notify=changed)
    notesHtml = QtCore.Property(
        str,
        fget=lambda self: (
            '<p class="ver">What\'s new in 1.0.40</p><p>Point one</p>'
        ),
        notify=changed)

    @QtCore.Slot()
    def dismissBanner(self):
        self.calls.append("dismiss")
        self._visible = False
        self.changed.emit()

    @QtCore.Slot()
    def showBannerNotes(self):
        self.calls.append("banner")

    @QtCore.Slot()
    def showCurrentNotes(self):
        self.calls.append("current")


def pump(ms=200):
    from gremlin import clock
    end = clock.monotonic() + ms / 1000.0
    while clock.monotonic() < end:
        app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 20)


def load(name, model):
    engine = QtQml.QQmlApplicationEngine()
    engine.addImportPath(str(ROOT / "theme"))
    warnings = []
    engine.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))
    engine.rootContext().setContextProperty("whatsNew", model)
    engine.load(QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / name)))
    return engine, warnings


out = {}
model = Model()
# The banner lives in a window of its own here.
import shutil
work = Path(tempfile.mkdtemp())
holder = work / "holder.qml"
holder.write_text(
    "import QtQuick\nimport QtQuick.Controls\nimport QtQuick.Layouts\n"
    "import Gremlin.Style\n"
    "ApplicationWindow { width: 600; height: 100; visible: true\n"
    "  readonly property color infoColor: Style.gold\n"
    "  readonly property color infoFillColor: Style.goldFill\n"
    "  readonly property color pageColor: Style.bgPage\n"
    "  property int opened: 0\n"
    "  ColumnLayout { anchors.fill: parent\n"
    "    WhatsNewBanner { onOpenNotes: opened++ } } }\n",
    encoding="utf-8")
try:
    engine = QtQml.QQmlApplicationEngine()
    engine.addImportPath(str(ROOT / "theme"))
    warnings = []
    engine.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))
    engine.rootContext().setContextProperty("whatsNew", model)
    shutil.copy(ROOT / "qml" / "WhatsNewBanner.qml", work / "WhatsNewBanner.qml")
    engine.load(QtCore.QUrl.fromLocalFile(str(holder)))
    win = engine.rootObjects()[0]
    pump()
    text = win.findChild(QtCore.QObject, "whatsNewBannerTitle")
    message = win.findChild(QtCore.QObject, "whatsNewBannerMessage")
    card = win.findChild(QtCore.QObject, "whatsNewBannerCard")
    stripe = win.findChild(QtCore.QObject, "whatsNewBannerStripe")
    link = win.findChild(QtCore.QObject, "whatsNewBannerLink")
    close = win.findChild(QtCore.QObject, "whatsNewBannerClose")
    banner = win.findChild(QtCore.QObject, "whatsNewBanner")
    out["text"] = text.property("text")
    out["message"] = message.property("text")
    out["bold"] = bool(text.property("font").bold)
    out["link_text"] = link.property("text")
    out["visible"] = bool(banner.property("visible"))
    QtQml.QQmlExpression(QtQml.qmlContext(link), link, "activate()").evaluate()
    pump(50)
    out["opened"] = win.property("opened")
    out["calls_after_link"] = list(model.calls)
    QtCore.QMetaObject.invokeMethod(close, "click")
    pump(100)
    out["calls_after_close"] = list(model.calls)
    out["visible_after_close"] = bool(banner.property("visible"))
    out["fill"] = card.property("color").name().upper()
    out["stripe"] = stripe.property("color").name().upper()
    out["button_fill"] = link.property("color").name().upper()
    out["button_border"] = QtQml.QQmlExpression(
        QtQml.qmlContext(link), link, "border.color").evaluate()[0].name().upper()
    out["style_fill"] = win.property("infoFillColor").name()
    out["style_info"] = win.property("infoColor").name()
    out["page"] = win.property("pageColor").name()
    out["text_color"] = text.property("color").name().upper()
    # The see-through gold needs an opaque base under it (name() above
    # drops the alpha, so the alphas are read here).
    base = win.findChild(QtCore.QObject, "whatsNewBannerBase")
    out["base_alpha"] = base.property("color").alphaF() if base else None
    out["fill_alpha"] = card.property("color").alphaF()
    out["banner_warnings"] = [w for w in warnings if "WhatsNewBanner" in w]
finally:
    shutil.rmtree(work, ignore_errors=True)

engine2, warnings2 = load("WindowWhatsNew.qml", model)
w2 = engine2.rootObjects()[0]
w2.setProperty("visible", True)
pump(300)
area = w2.findChild(QtCore.QObject, "whatsNewNotes")
expr = QtQml.QQmlExpression(QtQml.qmlContext(area), area, "getText(0, length)")
out["window_title"] = w2.property("title")
out["window_notes"] = expr.evaluate()[0]
out["window_rich"] = bool(QtQml.QQmlExpression(
    QtQml.qmlContext(area), area, "textFormat === TextEdit.RichText").evaluate()[0])
out["window_warnings"] = [w for w in warnings2 if "WindowWhatsNew" in w]
print("RESULT " + json.dumps(out), flush=True)
'''


def _run(tmp_path: pathlib.Path) -> dict:
    script = tmp_path / "whats_new_qml.py"
    script.write_text(_SCRIPT, encoding="utf-8")
    env = dict(os.environ, USERPROFILE=str(tmp_path), QT_QPA_PLATFORM="offscreen",
               GREMLIN_OFFLINE="1")
    env.setdefault(
        "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts"))
    result = proc_tree.run([sys.executable, str(script), str(_ROOT)],
                           cwd=_ROOT, env=env, text=True, timeout=120)
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, smoke_report.explain(result)
    return json.loads(lines[-1][len("RESULT "):])


def test_banner_and_window_follow_the_model(tmp_path: pathlib.Path) -> None:
    out = _run(tmp_path)
    assert out["visible"] and out["text"] == "Updated to 1.0.40"
    assert out["message"] == "See what changed in this version."
    assert out["link_text"] == "What's New"
    # What's New: the model is asked, the window is opened, the bar stays.
    assert out["calls_after_link"] == ["banner"] and out["opened"] == 1
    # The close button dismisses; the bar goes.
    assert out["calls_after_close"] == ["banner", "dismiss"]
    assert out["visible_after_close"] is False
    assert out["banner_warnings"] == []


def test_banner_is_an_infobar_card_with_a_stripe_and_gold_button(
        tmp_path: pathlib.Path) -> None:
    out = _run(tmp_path)
    # Card fill, stripe and button fill come from Style; the title is bold.
    assert out["fill"] == out["style_fill"].upper()
    assert out["stripe"] == out["style_info"].upper()
    assert out["button_border"] == out["style_info"].upper()
    assert out["fill"] != out["page"].upper()
    # The card is a faint gold tint over an opaque base, not solid gold:
    # the full-size stripe behind it once showed through the see-through
    # fill.
    assert out["base_alpha"] == 1.0 and out["fill_alpha"] < 0.5, out
    assert out["bold"] is True
    # The window shows the model's notes as rich text under its title.
    assert out["window_title"] == "What's New"
    assert "Point one" in out["window_notes"] and out["window_rich"]
    assert out["window_warnings"] == []


def test_main_has_the_banner_and_the_help_item() -> None:
    main = (_ROOT / "qml" / "Main.qml").read_text(encoding="utf-8")
    commands = (_ROOT / "qml" / "main_commands.js").read_text(encoding="utf-8")
    assert "WhatsNewBanner {" in main and 'openTool("WindowWhatsNew.qml")' in main
    assert main.index("WhatsNewBanner {") < main.index('objectName: "modeBar"')
    assert main.index('command: "help.updates"') < main.index(
        'command: "help.whatsNew"') < main.index('command: "help.diagnostics"')
    assert '{ id: "help.whatsNew", text: "What\'s New…", group: "Help"' in commands
    assert "whatsNew.showCurrentNotes()" in commands
