# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""When the program can't start, it says so.

It used to close without a word: an error while starting only went to
system.log, and a main window that failed to load ended the process with
sys.exit(-1). Now main() shows a Windows message box with the reason and
where the logs are. No test here shows a real message box.
"""

from __future__ import annotations

import sys

sys.path.append(".")

import os
import pathlib
import subprocess
from unittest import mock

import pytest

import joystick_gremlin

_ROOT = pathlib.Path(__file__).parents[2]


def test_message_names_the_reason_the_error_and_the_logs(
    _no_message_boxes: list[tuple],
) -> None:
    joystick_gremlin.tell_could_not_start(
        "The main window could not be loaded.",
        "\n".join(f"line {i}" for i in range(30)),
    )
    assert len(_no_message_boxes) == 1  # recorded, not shown (test/conftest.py)
    text, title, flags = _no_message_boxes[0]
    assert text.startswith("Gremlin-Platforms could not start.")
    assert "The main window could not be loaded." in text
    assert "line 29" in text and "line 17" not in text  # the last lines only
    assert str(joystick_gremlin.gremlin.util.logs_dir()) in text
    assert title == "Gremlin-Platforms R1"
    assert flags == 0x10


def test_main_tells_the_user_and_ends_when_starting_fails() -> None:
    class _Ended(Exception):
        pass

    with (
        mock.patch.object(joystick_gremlin, "acquire_instance_lock", return_value=None),
        mock.patch.object(joystick_gremlin, "_gremlin_window_titles", return_value=[]),
        mock.patch.object(joystick_gremlin, "_other_gremlin_pids", return_value=[]),
        mock.patch.object(
            joystick_gremlin, "_confirm_second_instance", return_value="continue"
        ),
        mock.patch.object(
            joystick_gremlin,
            "JoystickGremlinApp",
            side_effect=joystick_gremlin.StartupError("Broken", "qml: line 1"),
        ),
        mock.patch.object(joystick_gremlin, "tell_could_not_start") as tell,
        mock.patch.object(joystick_gremlin.os, "_exit", side_effect=_Ended) as end,
        pytest.raises(_Ended),
    ):
        joystick_gremlin.main()
    tell.assert_called_once_with("Broken", "qml: line 1")
    end.assert_called_once_with(1)


def test_broken_main_window_raises_with_the_qml_errors(tmp_path: pathlib.Path) -> None:
    broken = tmp_path / "Main.qml"
    broken.write_text("import QtQuick\nItem { this is not qml }\n", encoding="utf-8")
    code = (
        "import sys\n"
        "sys.path.insert(0, '.')\n"
        "import importlib.util\n"
        "spec = importlib.util.spec_from_file_location(\n"
        "    'fake_hardware', 'test/fake_hardware.py')\n"
        "fake_hardware = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(fake_hardware)\n"
        "fake_hardware.install()\n"
        "import gremlin.ui.update_model as um\n"
        "um.UpdateModel.startup = lambda self, *a, **k: None\n"
        "import joystick_gremlin, gremlin.util\n"
        "real = gremlin.util.resource_path\n"
        f"broken = {str(broken)!r}\n"
        "gremlin.util.resource_path = (\n"
        "    lambda p: broken if p == 'qml/Main.qml' else real(p))\n"
        "try:\n"
        "    joystick_gremlin.JoystickGremlinApp([sys.argv[0]])\n"
        "    print('NO ERROR', flush=True)\n"
        "except joystick_gremlin.StartupError as e:\n"
        "    details = e.details.replace(chr(10), ' ')\n"
        "    print('STARTUP ERROR:', e, '|', details, flush=True)\n"
        "import os\n"
        "os._exit(0)  # threads started by the app would keep it alive\n"
    )
    # Run as a script: with -c the program takes "-c" as its own path.
    script = tmp_path / "start_broken.py"
    script.write_text(code, encoding="utf-8")
    env = dict(os.environ, USERPROFILE=str(tmp_path), QT_QPA_PLATFORM="offscreen")
    result = subprocess.run(
        [sys.executable, str(script)], cwd=_ROOT, env=env,
        capture_output=True, text=True, timeout=120,
    )
    assert "STARTUP ERROR: The main window could not be loaded." in result.stdout, (
        result.stdout + result.stderr[-1500:]
    )
    assert "Main.qml" in result.stdout  # the QML error is passed on
