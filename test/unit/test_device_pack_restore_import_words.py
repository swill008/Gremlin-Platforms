# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Export / Import Device window words (D-TESTLIST-1 items 7 and 8).

Undo Import is Restore Import (button, message-line link, confirm), with
the decision's two sentences in the warnings, and the window says "file",
never "pack". The warning and the link are read from the window off-screen
(device_pack_window_smoke.py); the title, button and new-device text from
the page's own text.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

_ROOT = pathlib.Path(__file__).parents[2]
_QML = _ROOT / "qml" / "DialogDevicePack.qml"

_EXISTING = (
    "You can restore the device as it was with Restore Import until you "
    "import the file again or close this window."
)
_NEW = (
    "You can remove the new device with Restore Import until you import "
    "the file again or close this window."
)


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    env = dict(
        os.environ,
        USERPROFILE=str(home),
        QT_QPA_PLATFORM="offscreen",
        HTTPS_PROXY="http://127.0.0.1:9",
        GREMLIN_PACK_PART="",
    )
    result = proc_tree.run(
        [sys.executable, "test/unit/device_pack_window_smoke.py"],
        cwd=_ROOT,
        env=env,
        text=True,
        timeout=120,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, smoke_report.explain(result)
    return json.loads(lines[0][len("RESULT ") :])


def test_the_warning_uses_restore_import_and_file(run: dict) -> None:
    warning = run["warning"]
    assert _EXISTING in warning
    assert "2 from the file." in warning
    assert "Undo Import" not in warning
    assert "pack" not in warning.lower()


def test_the_message_line_link_is_restore_import(run: dict) -> None:
    assert run["message-after"]["undo"] == "Restore Import"


def _shown_strings() -> list[str]:
    # Quoted strings, minus objectNames and the dialog's settings name.
    text = _QML.read_text(encoding="utf-8")
    text = re.sub(r"(objectName|name):\s*\"[^\"]*\"", "", text)
    text = "\n".join(ln.split("//")[0] for ln in text.splitlines())
    return re.findall(r"\"([^\"]*)\"", text)


def test_the_page_says_restore_import_and_file() -> None:
    text = _QML.read_text(encoding="utf-8")
    assert '"Replace with This File?"' in text
    assert 'text: "Restore Import"' in text
    assert '"Restore Import?", info.error || "", "Restore Import"' in text
    assert _NEW in text
    assert _EXISTING in text
    shown = _shown_strings()
    assert not [s for s in shown if "pack" in s.lower()], shown
    assert not [s for s in shown if "undo" in s.lower()], shown
