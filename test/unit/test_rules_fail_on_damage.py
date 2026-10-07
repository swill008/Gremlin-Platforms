# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The rule checks after each test fail it on damage (D-TEST-RULES-FAIL).

A sample test file runs through pytest with the tests' own conftest: a test
that leaves a damaged open profile fails, one that leaves only a warning
(PROFILE-UNUSED-ACTION) passes, validate_off leaves a test out, a test's
own failure stays its own, and a Run that leaves something behind is an
error at teardown. Every problem, warnings too, is still in the report.
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

import pytest

_ROOT = pathlib.Path(__file__).parents[2]

_SAMPLE = '''
import uuid

import pytest

from gremlin import plugin_manager, run_scope, shared_state, validate
from gremlin.profile import Profile
from gremlin.types import InputType

_STICK = uuid.UUID("5a1d0000-1111-2222-3333-444444444444")


@pytest.fixture(scope="module", autouse=True)
def _options():
    import joystick_gremlin

    joystick_gremlin.register_config_options()


def _bound() -> Profile:
    """A profile with one input and one action, made the open one."""
    profile = Profile()
    shared_state.current_profile = profile
    action = plugin_manager.PluginManager().create_instance(
        "Description", InputType.JoystickButton
    )
    item = profile.get_input_item(
        _STICK, InputType.JoystickButton, 1, "Default", create_if_missing=True
    )
    binding = item.add_item_binding()
    binding.root_action.insert_action(action, "children")
    return profile


def test_a_clean_profile_passes():
    _bound()


def test_damage_fails():
    profile = _bound()
    profile.modes.add_mode("Twin")
    profile.modes.add_mode("Twin2")
    modes = profile.modes._hierarchy.children
    next(m for m in modes if m.value == "Twin2").value = "Twin"


def test_a_warning_passes():
    profile = _bound()
    item = profile.get_input_item(
        _STICK, InputType.JoystickButton, 1, "Default", create_if_missing=False
    )
    item.remove_item_binding(item.action_sequences[0])  # kept for Undo


@pytest.mark.validate_off
def test_validate_off_passes():
    profile = _bound()
    profile.modes._hierarchy.value = "not the root"


def test_its_own_failure_stays_its_own():
    profile = _bound()
    profile.modes._hierarchy.value = "not the root"
    assert False, "the test's own failure"


def test_a_run_left_behind_errors_at_teardown():
    shared_state.current_profile = None
    run_scope.number = lambda: 10_000
    validate.after_stop = lambda: ["RUN-HELD-KEYS: key 42 is still held"]
'''


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> tuple[int, str, str]:
    folder = tmp_path_factory.mktemp("rules")
    sample = folder / "test_sample.py"
    sample.write_text(_SAMPLE, encoding="utf-8")
    report = folder / "report.txt"
    env = dict(
        os.environ,
        PYTHONPATH=os.pathsep.join([str(_ROOT / "test"), str(_ROOT)]),
        GREMLIN_VALIDATE_REPORT=str(report),
        GREMLIN_TEST_HANG_LIMIT="",
        USERPROFILE=str(folder),
    )
    # To a file, not a pipe (a full pipe would block the run).
    log = folder / "out.txt"
    with log.open("w", encoding="utf-8") as out:
        process = subprocess.run(
            [sys.executable, "-m", "pytest", "-p", "conftest", "-v", "-rA",
             "-p", "no:cacheprovider", "-p", "no:randomly", str(sample)],
            cwd=_ROOT, env=env, stdout=out, stderr=subprocess.STDOUT,
            timeout=120, check=False,
        )
    text = log.read_text(encoding="utf-8", errors="replace")
    return process.returncode, text, report.read_text(encoding="utf-8")


def _line(out: str, name: str) -> str:
    """The -v result line of one sample test."""
    lines = [line for line in out.splitlines() if f"::{name} " in line]
    assert lines, out[-3000:]
    return lines[0]


def test_a_clean_profile_passes(run: tuple[int, str, str]) -> None:
    _, out, _ = run
    assert "PASSED" in _line(out, "test_a_clean_profile_passes"), out[-3000:]


def test_a_damaged_profile_fails_the_test(run: tuple[int, str, str]) -> None:
    _, out, _ = run
    assert "FAILED" in _line(out, "test_damage_fails"), out[-3000:]
    assert "found damage in the open profile" in out
    assert "PROFILE-MODE-DUPLICATE: 2 modes are named 'Twin'" in out


def test_a_warning_only_passes_and_is_reported(run: tuple[int, str, str]) -> None:
    _, out, report = run
    assert "PASSED" in _line(out, "test_a_warning_passes"), out[-3000:]
    assert "test_a_warning_passes" in report
    assert "PROFILE-UNUSED-ACTION" in report


def test_validate_off_leaves_the_test_out(run: tuple[int, str, str]) -> None:
    _, out, report = run
    assert "PASSED" in _line(out, "test_validate_off_passes"), out[-3000:]
    assert "test_validate_off_passes" not in report


def test_a_tests_own_failure_is_kept(run: tuple[int, str, str]) -> None:
    _, out, report = run
    assert "FAILED" in _line(out, "test_its_own_failure_stays_its_own")
    assert "the test's own failure" in out
    # Still in the report, though the failure shown is the test's own.
    assert "test_its_own_failure_stays_its_own" in report
    assert "PROFILE-MODE-ROOT" in report


def test_a_run_left_behind_is_an_error_at_teardown(run: tuple[int, str, str]) -> None:
    code, out, _ = run
    assert "ERROR at teardown of test_a_run_left_behind_errors_at_teardown" in out, (
        out[-3000:]
    )
    assert "found damage after the Run" in out
    assert "RUN-HELD-KEYS: key 42 is still held" in out
    assert "2 failed, 4 passed, 1 error" in out, out[-3000:]
    assert code == 1


def test_the_run_ends_with_the_summary(run: tuple[int, str, str]) -> None:
    _, out, _ = run
    assert "validate: " in out and "PROFILE-MODE-DUPLICATE x1" in out, out[-3000:]
