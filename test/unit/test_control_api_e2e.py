# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The control API end to end (claude/plans/control-api-contract.md): the
real program, built off-screen in its own process with a temporary
USERPROFILE (the journey harness, test/journeys/_harness.py), starts the
API as joystick_gremlin's main() does (attach_ui, start); the Options
switch is turned on as its row does; then

- gremlin_ctl.client connects through endpoint.json and calls state,
  run.start / run.stop (the Run really starts and stops), commands and
  window.list;
- the CLI (python -m gremlin_ctl --json state), started through
  test/proc_tree.py, reports the same state;
- with the switch off again the CLI exits 2 with its message.

The pipe has a fresh random name: never the user's running program's.
In the program's process control_api's test guard (_under_test: this
file imports pytest) is turned off so it opens a real pipe, as the
installed program does.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import threading
from typing import Any

import pytest

_JOURNEYS = pathlib.Path(__file__).resolve().parents[1] / "journeys"
sys.path.insert(0, str(_JOURNEYS))
from _harness import ROOT, Journey, run_journey, step  # noqa: E402

_SWITCH = ("global", "control", "allow-other-programs")


# +-------------------------------------------------------------------------
# | The program's side (a child process)


def _in_worker(j: Journey, fn: Any, what: str, timeout: float = 60.0) -> Any:  # noqa: ANN401
    """fn on a worker thread (another program's view) while the program's
    main thread runs its events."""
    box: dict[str, Any] = {}

    def work() -> None:
        try:
            box["value"] = fn()
        except BaseException as e:  # noqa: BLE001
            box["error"] = f"{type(e).__name__}: {e}"

    thread = threading.Thread(target=work, name="e2e-client", daemon=True)
    thread.start()
    j.wait_until(lambda: not thread.is_alive(), what, timeout=timeout)
    if "error" in box:
        return {"error": box["error"]}
    return box.get("value")


def _cli(*argv: str, endpoint: pathlib.Path) -> dict:
    import _harness  # the program's process: test/ is loaded by path

    proc_tree = _harness._load("proc_tree")  # noqa: SLF001
    env = dict(os.environ, GREMLIN_CTL_ENDPOINT=str(endpoint), PYTHONIOENCODING="utf-8")
    done = proc_tree.run(
        [sys.executable, "-m", "gremlin_ctl", *argv],
        cwd=ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=45,
    )
    return {"code": done.returncode, "stdout": done.stdout, "stderr": done.stderr}


def story(j: Journey) -> None:
    from gremlin import control_api
    from gremlin.ui import option
    from gremlin_ctl import client as ctl

    out = j.out
    # A real pipe (random name), as in the installed program.
    control_api._under_test = lambda: False  # noqa: SLF001
    control_api.attach_ui()
    control_api.start()
    endpoint = control_api.endpoint_path()
    out["endpoint-while-off"] = endpoint.exists()
    out["switch-set"] = option.change_setting(_SWITCH, True)
    out["endpoint-while-on"] = endpoint.exists()
    out["endpoint-under-home"] = str(endpoint).startswith(os.environ["USERPROFILE"])

    def wait_run(client: Any, want: str) -> str:  # noqa: ANN401
        import time

        deadline = time.monotonic() + 20
        run = ""
        while time.monotonic() < deadline:
            run = client.call("state")["run"]
            if run == want:
                break
            time.sleep(0.1)
        return run

    def client_calls() -> dict:
        found: dict[str, Any] = {}
        with ctl.connect(endpoint=endpoint) as client:
            found["state"] = client.call("state")
            found["run.start"] = client.call("run.start")
            found["running"] = wait_run(client, "running")
            found["run.stop"] = client.call("run.stop")
            found["stopped"] = wait_run(client, "stopped")
            found["commands"] = client.call("commands")
            found["windows"] = client.call("window.list")
        return found

    out["client"] = _in_worker(j, client_calls, "the client's calls")
    out["cli-state"] = _in_worker(
        j,
        lambda: _cli("--json", "state", endpoint=endpoint),
        "gremlin-ctl --json state",
    )
    out["cli-state-json-after"] = _in_worker(
        j,
        lambda: _cli("state", "--json", endpoint=endpoint),
        "gremlin-ctl state --json",
    )
    out["switch-off"] = option.change_setting(_SWITCH, False)
    out["endpoint-after-off"] = endpoint.exists()
    out["cli-off"] = _in_worker(
        j, lambda: _cli("state", endpoint=endpoint), "gremlin-ctl state (off)"
    )
    control_api.stop()


def main() -> None:
    Journey(None).run(story)


# +-------------------------------------------------------------------------
# | The pytest side


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("control-api-e2e"))


def test_the_switch_opens_the_endpoint_in_the_user_folder(run: dict) -> None:
    assert step(run, "endpoint-while-off") is False
    assert step(run, "switch-set") is True
    assert step(run, "endpoint-while-on") is True
    assert step(run, "endpoint-under-home") is True


def test_the_client_reads_state(run: dict) -> None:
    state = step(run, "client")["state"]
    assert state["api_version"] == 1
    assert state["run"] == "stopped"
    assert state["tracing"] is False
    assert isinstance(state["version"], str) and state["version"]
    assert "screen_saver_mode" in state and "health" in state


def test_run_start_and_stop_through_the_api_start_and_stop_the_run(run: dict) -> None:
    found = step(run, "client")
    assert found["running"] == "running", found
    assert found["stopped"] == "stopped", found


def test_commands_and_windows_through_the_api(run: dict) -> None:
    found = step(run, "client")
    ids = {c["id"] for c in found["commands"]}
    assert ids, "the main window's menu commands"
    assert all(c["text"] for c in found["commands"])
    assert any(w["visible"] for w in found["windows"])


def test_the_cli_reports_the_state(run: dict) -> None:
    cli = step(run, "cli-state")
    assert cli["code"] == 0, cli
    state = json.loads(cli["stdout"])
    assert state["api_version"] == 1
    assert state["run"] == "stopped"


def test_json_may_follow_the_command(run: dict) -> None:
    """gremlin-ctl state --json, as the plan writes it."""
    cli = step(run, "cli-state-json-after")
    assert cli["code"] == 0, cli
    assert json.loads(cli["stdout"])["api_version"] == 1


def test_with_the_switch_off_the_cli_exits_2_with_the_message(run: dict) -> None:
    assert step(run, "switch-off") is True
    assert step(run, "endpoint-after-off") is False
    cli = step(run, "cli-off")
    assert cli["code"] == 2, cli
    assert "isn't running" in cli["stderr"]
    assert "Options › General" in cli["stderr"]


def test_the_cli_exits_2_when_the_program_is_not_running(
    tmp_path: pathlib.Path,
) -> None:
    """No program, no endpoint.json: exit 2 with the message."""
    import proc_tree  # pyright: ignore[reportMissingImports]  (test/)

    env = dict(
        os.environ,
        USERPROFILE=str(tmp_path),
        GREMLIN_CTL_ENDPOINT=str(
            tmp_path / "Gremlin Platforms" / "api" / "endpoint.json"
        ),
        PYTHONIOENCODING="utf-8",
    )
    done = proc_tree.run(
        [sys.executable, "-m", "gremlin_ctl", "state"],
        cwd=ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=45,
    )
    assert done.returncode == 2, (done.stdout, done.stderr)
    assert "Gremlin-Platforms isn't running" in done.stderr
    assert done.stdout == ""


if __name__ == "__main__":
    main()
