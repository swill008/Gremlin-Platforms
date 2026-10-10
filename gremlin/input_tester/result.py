# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""result.json: the tester's one written file (contract item 6)."""

from __future__ import annotations

import datetime
import json
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gremlin.input_tester.compare import Verdict

RESULT_NAME = "result.json"


def result_data(verdict: Verdict) -> dict:
    """The result.json content, without the time it was written."""
    return {
        "version": 1,
        "verdict": verdict.verdict,
        "summary": verdict.summary,
        "rows": [
            {
                "kind": row.kind,
                "name": row.name,
                "expect": row.expect,
                "seen": row.seen,
                "verdict": row.verdict,
            }
            for row in verdict.rows
        ],
        "steam": dict(verdict.steam),
    }


def write_result(tester_dir: str | os.PathLike, verdict: Verdict) -> Path:
    """Writes <tester_dir>/result.json atomically (temp file + replace)."""
    folder = Path(tester_dir)
    folder.mkdir(parents=True, exist_ok=True)
    data = result_data(verdict)
    data["written"] = datetime.datetime.now().isoformat(timespec="seconds")
    target = folder / RESULT_NAME
    fd, tmp = tempfile.mkstemp(prefix=".result-", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, target)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return target
