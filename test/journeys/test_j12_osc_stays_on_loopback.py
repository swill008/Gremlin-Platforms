# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Journey 12: a journey's OSC listener stays on this PC.

The program listens for OSC from start-up (D-09-OSC-ALWAYS-LISTEN) with
the settings in OSC's module file (D-09-OSC-FILE), whose defaults are every
address (0.0.0.0) on port 8001. A journey must never open that: another
Gremlin-Platforms may hold it ("Could not bind OSC"), and tests stay off
the network. The harness writes 127.0.0.1 and a port the OS picked into
the module file before the program starts; start-up and a Run listen
there and nowhere else.

Here every listener start is recorded; one that isn't on 127.0.0.1 is
recorded but not opened.

Spec: 09 (OSC server settings in the module file, always listening). No
known gap.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _harness import Journey, run_journey, step  # noqa: E402


def _record_binds(j: Journey) -> None:
    from gremlin import osc

    binds: list[list] = []
    j.out["binds"] = binds
    original = osc.OscListener.start

    def start(self: osc.OscListener) -> None:
        binds.append([self.host, self.port])
        if self.host == "127.0.0.1":
            original(self)

    osc.OscListener.start = start  # type: ignore[method-assign]


def story(j: Journey) -> None:
    from gremlin import osc, osc_device_file

    out = j.out
    out["file"] = {
        k: osc_device_file.read_server()[k] for k in ("enabled", "host", "port")
    }
    runtime = osc.OscRuntime()
    # What main() does at start-up (the harness builds the app itself).
    runtime.open_always()
    out["always-open"] = runtime.is_open()
    runtime.close_always()
    # The OSC Monitor's path (osc_monitor_model).
    out["monitor-held"] = runtime.hold_open("j12")
    runtime.release_open("j12")
    out["startup-binds"] = list(out["binds"])
    j.backend.activate_gremlin(True)
    j.app.processEvents()
    out["running"] = j.backend.runner.is_running()
    j.backend.activate_gremlin(False)
    out["all-binds"] = list(out["binds"])
    out["messages"] = [str(m) for m in j.messages]


def main() -> None:
    Journey(_record_binds).run(story)


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("j12"))


def test_the_module_file_points_osc_at_this_pc(run: dict) -> None:
    server = step(run, "file")
    assert server["enabled"] is True
    assert server["host"] == "127.0.0.1"
    assert server["port"] != 8001


def test_always_listening_and_the_monitor_stay_on_this_pc(run: dict) -> None:
    assert step(run, "always-open") is True
    assert step(run, "monitor-held") is True
    binds = step(run, "startup-binds")
    assert len(binds) == 2, binds
    assert all(host == "127.0.0.1" for host, _port in binds), binds


def test_a_run_never_opens_the_network_port(run: dict) -> None:
    assert step(run, "running") is True
    binds = step(run, "all-binds")
    assert all(host == "127.0.0.1" and port != 8001 for host, port in binds), binds
    assert not any("OSC" in m for m in step(run, "messages"))


if __name__ == "__main__":
    main()
