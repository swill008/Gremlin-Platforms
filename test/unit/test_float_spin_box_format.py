# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A FloatSpinBox shows its number with its decimals from the start (04 S98).

At value 0 the box showed "0" instead of "0.00": the custom text format was
set after the limits, and setting the value 0 again changed nothing, so the
shown text was never redrawn with it. Non-zero values were right.

Loads FloatSpinBox (theme/Gremlin/Base) in the running program off-screen,
in its own process with a temporary USERPROFILE and fake hardware.

Spec: 04-profile-modes S98.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

_ROOT = pathlib.Path(__file__).parents[2]

# (value, decimals) -> the text the box should show.
_CASES = {
    "0|2": "0.00",
    "0|3": "0.000",
    "0.5|2": "0.50",
    "-1|2": "-1.00",
}

_CODE = """
import json, os, sys
sys.path.insert(0, '.')
sys.path.insert(0, 'test')
import importlib.util
spec = importlib.util.spec_from_file_location('fake_hardware', 'test/fake_hardware.py')
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()
import gremlin.ui.update_model as um
um.UpdateModel.startup = lambda self, *a, **k: None
import joystick_gremlin
from PySide6 import QtCore, QtQml, QtQuick, QtTest
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
engine = app.engine

out = {}
for case in sys.argv[1].split(','):
    value, decimals = case.split('|')
    comp = QtQml.QQmlComponent(engine)
    comp.setData(
        ('import QtQuick; import Gremlin.Base; FloatSpinBox { '
         'minValue: -1.0; maxValue: 1.0; value: %s; decimals: %s }'
         % (value, decimals)).encode(),
        QtCore.QUrl.fromLocalFile(os.path.abspath('qml/_float_spin_box_test.qml')))
    obj = comp.create()
    if obj is None:
        out[case] = 'ERROR ' + comp.errorString()
        continue
    QtTest.QTest.qWait(50)
    boxes = [i for i in obj.findChildren(QtQuick.QQuickItem)
             if i.inherits('QQuickSpinBox')]
    out[case] = boxes[0].property('displayText') if boxes else 'NO SPINBOX'
    obj.deleteLater()
print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive
"""


@pytest.fixture(scope="module")
def shown(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    script = home / "float_spin.py"
    script.write_text(_CODE, encoding="utf-8")
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen")
    result = proc_tree.run(
        [sys.executable, str(script), ",".join(_CASES)], cwd=_ROOT, env=env,
        text=True, timeout=120,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, smoke_report.explain(result)
    return json.loads(lines[0][len("RESULT "):])


@pytest.mark.parametrize("case", list(_CASES))
def test_the_box_shows_its_decimals_from_the_start(
    shown: dict[str, str], case: str
) -> None:
    assert shown.get(case) == _CASES[case], shown
