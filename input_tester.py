# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Gremlin Input Tester: entry point (decision D-02-INPUT-TESTER).

    "Gremlin Input Tester.exe" [--gremlin-dir "<user>\\Gremlin Platforms"]

Reads only. Never imports gremlin.config or anything that reads or writes
the user's settings; the one file it writes is <gremlin-dir>\\tester\\result.json.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def resource_root() -> Path:
    """The program folder: PyInstaller's _MEIPASS when frozen, else this
    file's folder."""
    if "_MEIPASS" in sys.__dict__:
        return Path(sys._MEIPASS).resolve()  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="Gremlin Input Tester")
    parser.add_argument("--gremlin-dir", default=None)
    args, _unknown = parser.parse_known_args(argv)
    return args


def build_engine(app: object, gremlin_dir: str | None, root: Path | None = None):  # noqa: ANN201
    """The QML engine with the tester window loaded; (engine, model)."""
    from PySide6 import QtCore, QtQml

    from gremlin.input_tester.model import InputTesterModel

    root = root or resource_root()
    engine = QtQml.QQmlApplicationEngine()
    engine.addImportPath(str(root / "theme"))
    QtQml.qmlRegisterSingletonType(
        QtCore.QUrl.fromLocalFile(str(root / "qml" / "Style.qml")),
        "Gremlin.Style",
        1,
        0,
        "Style",
    )
    model = InputTesterModel(gremlin_dir, parent=engine)
    context = engine.rootContext()
    # Style.qml reads `backend ? backend.uiScale : 100`.
    context.setContextProperty("backend", None)
    context.setContextProperty("tester", model)
    engine.load(
        QtCore.QUrl.fromLocalFile(str(root / "qml" / "tester" / "InputTester.qml"))
    )
    return engine, model


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "GremlinStyle")
    os.environ["QT_FILE_SELECTORS"] = ",".join(
        filter(None, [os.environ.get("QT_FILE_SELECTORS", ""), "Universal"])
    )
    root = resource_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from PySide6 import QtGui

    app = QtGui.QGuiApplication(sys.argv[:1])
    app.setApplicationName("Gremlin Input Tester")
    engine, _model = build_engine(app, args.gremlin_dir, root)
    if not engine.rootObjects():
        return 1
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
