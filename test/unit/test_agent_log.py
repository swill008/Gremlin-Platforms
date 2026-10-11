# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""tools/agent_log.py never stops a pipe on a line that isn't valid UTF-8."""

from __future__ import annotations

import importlib.util
import io
import sys
from pathlib import Path
from types import ModuleType

import pytest

_TOOL = Path(__file__).resolve().parents[2] / "tools" / "agent_log.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("agent_log_under_test", _TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bytes_that_are_not_utf8_are_replaced_not_fatal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tool = _load()
    monkeypatch.setattr(tool, "_FOLDER", tmp_path)
    data = (
        b"ok line\n" + b"bad \xff\xfe byte\r\n" + "arrow \u2192 end\n".encode("utf-8")
    )
    stdin = io.TextIOWrapper(io.BytesIO(data), encoding="utf-8")
    # A cp1252 console, as on Windows: strict encoding of the arrow would fail.
    out_bytes = io.BytesIO()
    stdout = io.TextIOWrapper(out_bytes, encoding="cp1252", errors="strict")
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(sys, "stdout", stdout)
    monkeypatch.setattr(sys, "argv", ["agent_log.py", "T"])

    assert tool.main() == 0
    stdout.flush()

    own = (tmp_path / "T.log").read_text(encoding="utf-8")
    shared = (tmp_path / "all.log").read_text(encoding="utf-8")
    assert "ok line" in own
    assert "bad \ufffd\ufffd byte" in own
    assert "arrow \u2192 end" in own
    assert "[T] bad \ufffd\ufffd byte" in shared
    assert b"ok line" in out_bytes.getvalue()
    assert "arrow \u2192 end".encode("utf-8") in out_bytes.getvalue()
