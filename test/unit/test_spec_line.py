# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Change control: every commit that touches program code names the spec it
follows (`Spec: <page> <refs>`) or says it changes no behaviour
(`Spec: none (no behaviour change)`). Checked for the commits made since
this test was added (older history is left as it is). See the change
control section of .claude/CLAUDE.md and claude/program-map/README.md."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_THIS = "test/unit/test_spec_line.py"
_PROGRAM = ("gremlin/", "qml/", "action_plugins/", "dill/", "vigem/")
_PROGRAM_FILES = ("joystick_gremlin.py",)
_SPEC = re.compile(r"^Spec:\s*\S", re.MULTILINE)


def _git(*args: str) -> str:
    done = subprocess.run(
        ["git", *args], cwd=_ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60,
    )
    if done.returncode != 0:
        pytest.skip(f"git {args[0]} failed: {done.stderr.strip()}")
    return done.stdout


def _touches_program(paths: list[str]) -> bool:
    return any(
        p.startswith(_PROGRAM) or p in _PROGRAM_FILES for p in paths if p
    )


def _commits_since_added() -> list[tuple[str, str, list[str]]]:
    """(sha, message, changed paths) for each commit after the one that
    added this test, oldest first."""
    added = _git("log", "--diff-filter=A", "--format=%H", "--", _THIS).split()
    if not added:
        return []  # not committed yet: nothing to check
    base = added[-1]
    out = _git(
        "log", "--reverse", "--format=%x1e%H%x1f%B%x1f", "--name-only",
        f"{base}..HEAD",
    )
    commits = []
    for record in out.split("\x1e"):
        if not record.strip():
            continue
        sha, message, files = (record.split("\x1f") + ["", ""])[:3]
        commits.append(
            (sha.strip(), message, [f.strip() for f in files.splitlines()])
        )
    return commits


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
def test_program_commits_name_their_spec() -> None:
    if not (_ROOT / ".git").exists():
        pytest.skip("not a git checkout")
    missing = [
        f"{sha[:8]} {message.strip().splitlines()[0] if message.strip() else ''}"
        for sha, message, paths in _commits_since_added()
        if _touches_program(paths) and not _SPEC.search(message)
    ]
    assert not missing, (
        "Commits that change program code need a 'Spec: <page> <refs>' line "
        "(or 'Spec: none (no behaviour change)'):\n" + "\n".join(missing)
    )


def test_the_rule_reads_spec_lines() -> None:
    assert _SPEC.search("Fix a thing\n\nSpec: 06 S28, Q8\n")
    assert _SPEC.search("Tidy\n\nSpec: none (no behaviour change)\n")
    assert not _SPEC.search("Fix a thing\n\nNo spec here\n")
    assert not _SPEC.search("Spec:\n")
    assert _touches_program(["gremlin/profile.py"])
    assert _touches_program(["joystick_gremlin.py"])
    assert not _touches_program(["claude/todo.md", "test/unit/x.py"])
