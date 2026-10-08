# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Release notes files (D-REL-NOTES-FILES) and the release text built from them."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from functools import cache
from pathlib import Path
from types import ModuleType

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_HELPER = _ROOT / "tools" / "release_body.py"
_WORKFLOW = _ROOT / ".github" / "workflows" / "release-exe.yml"
_NOTES = _ROOT / "release-notes"


@cache
def _helper() -> ModuleType:
    spec = importlib.util.spec_from_file_location("release_body", _HELPER)
    assert spec is not None and spec.loader is not None, f"missing {_HELPER}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_HELPER), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


def _expected_install(version: str) -> str:
    name = f"Gremlin-Platforms-R1-{version}"
    return (
        "## How to install\n"
        "\n"
        f"- Installer: run {name}-Setup.exe. It installs for your Windows user"
        " only (no administrator rights) and installed copies update themselves"
        " from Help -> Check for Updates.\n"
        f"- Portable: unzip {name}.zip anywhere (Documents, Desktop, etc), not"
        " in Program Files, and run gremlin_platforms.exe. A portable copy"
        " tells you about new versions but does not update itself.\n"
        "- Requires vJoy already installed.\n"
        "- Unsigned build: SmartScreen may warn on first run"
        " (More info -> Run anyway).\n"
    )


def test_body_for_1_0_27_is_notes_then_install() -> None:
    notes = (_NOTES / "1.0.27.md").read_text(encoding="utf-8")
    body = _helper().build_body("1.0.27", _NOTES)
    assert body.startswith("## What's new in 1.0.27\n")
    assert body == notes.rstrip() + "\n\n" + _expected_install("1.0.27")


def test_cli_writes_body_file(tmp_path: Path) -> None:
    out = tmp_path / "body.md"
    result = _run("1.0.27", "--out", str(out))
    assert result.returncode == 0, result.stderr
    assert out.read_text(encoding="utf-8") == _helper().build_body("1.0.27", _NOTES)


def test_missing_notes_file_fails_clearly(tmp_path: Path) -> None:
    result = _run("9.9.9", "--notes-dir", str(tmp_path))
    assert result.returncode != 0
    assert "release-notes" in result.stderr or "9.9.9.md" in result.stderr
    assert "9.9.9" in result.stderr
    with pytest.raises(_helper().ReleaseNotesError, match="9.9.9.md"):
        _helper().build_body("9.9.9", tmp_path)


@pytest.mark.parametrize(
    "text",
    [
        "",
        "Some notes\n",
        "## What's new in 1.0.0\n\n### New\n- x\n",  # wrong version
        "# What's new in 9.9.9\n",
    ],
)
def test_malformed_notes_file_fails_clearly(tmp_path: Path, text: str) -> None:
    (tmp_path / "9.9.9.md").write_text(text, encoding="utf-8")
    result = _run("9.9.9", "--notes-dir", str(tmp_path))
    assert result.returncode != 0
    assert "## What's new in 9.9.9" in result.stderr
    with pytest.raises(_helper().ReleaseNotesError):
        _helper().build_body("9.9.9", tmp_path)


def test_current_version_has_notes_file() -> None:
    """A version bump without its notes file fails here, before any release."""
    version = json.loads((_ROOT / "version.json").read_text(encoding="utf-8"))[
        "version"
    ]
    assert (_NOTES / f"{version}.md").is_file(), (
        f"version.json is {version} but release-notes/{version}.md is missing"
    )
    _helper().build_body(version, _NOTES)


def _workflow_steps() -> list[dict]:
    yaml = pytest.importorskip("yaml")
    doc = yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))
    return doc["jobs"]["build"]["steps"]


def test_workflow_checks_notes_before_building_and_uses_body_path() -> None:
    steps = _workflow_steps()
    names = [s.get("name", "") for s in steps]
    helper_steps = [
        i for i, s in enumerate(steps) if "tools/release_body.py" in s.get("run", "")
    ]
    assert helper_steps, "no step runs tools/release_body.py"
    first = helper_steps[0]
    assert first < names.index("Build executable"), "notes check must come first"
    assert "steps.version.outputs.version" in steps[first]["run"]

    release = next(s for s in steps if s.get("name") == "Create GitHub Release")
    with_ = release["with"]
    assert "body" not in with_
    assert with_["body_path"]
    assert any(with_["body_path"] in steps[i].get("run", "") for i in helper_steps), (
        "body_path is not the file the helper writes"
    )
    # Unchanged parts of the release step.
    tag = "Gremlin-Platforms-R1-${{ steps.version.outputs.version }}"
    assert with_["tag_name"] == tag
    assert with_["overwrite_files"] is True
    assert "-Setup.exe" in with_["files"] and ".zip" in with_["files"]
    assert release["if"] == "${{ inputs.publish }}"
