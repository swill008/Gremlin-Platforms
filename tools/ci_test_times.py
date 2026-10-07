# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Writes test/test_times.json: how long each test file took in a CI run.

    python tools/ci_test_times.py RUN_ID

test/run_tests.py splits test/unit into parts by these times when it has
none of its own (CI's first run, a new checkout). Each file's time is the
time between its test results in the run's log, as run_tests.py measures it.
"""

from __future__ import annotations

import datetime
import json
import pathlib
import re
import subprocess
import sys

_ROOT = pathlib.Path(__file__).parents[1]
_OUT = _ROOT / "test" / "test_times.json"
_STAMP = r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?)Z \[\d\d:\d\d\] (\S+)\s+\d+/\S+\s+"
_STARTED = re.compile(_STAMP + r"started:")
_COLLECTED = re.compile(_STAMP + r"(?:collecting \.\.\. )?collected \d+ item")
_RESULT = re.compile(
    _STAMP + r"(\S+::\S+) (PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)"
)


def _when(stamp: str) -> datetime.datetime:
    # GitHub writes 7 decimals, fromisoformat wants at most 6.
    return datetime.datetime.fromisoformat(stamp[:26])


def file_times(log_lines: list[str]) -> dict[str, float]:
    last: dict[str, datetime.datetime] = {}
    times: dict[str, float] = {}
    for line in log_lines:
        if m := _STARTED.search(line) or _COLLECTED.search(line):
            last[m.group(2)] = _when(m.group(1))
        elif (m := _RESULT.search(line)) and m.group(2) in last:
            now, part = _when(m.group(1)), m.group(2)
            test_file = m.group(3).split("::")[0]
            took = (now - last[part]).total_seconds()
            times[test_file] = times.get(test_file, 0.0) + took
            last[part] = now
    return {f: round(t, 1) for f, t in sorted(times.items())}


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    log = subprocess.run(
        ["gh", "run", "view", sys.argv[1], "--repo", "swill008/Gremlin-Platforms",
         "--log"],
        cwd=_ROOT, capture_output=True, text=True, encoding="utf-8",
        errors="replace", check=True,
    ).stdout
    times = file_times(log.splitlines())
    if not times:
        print("No test results in that run's log.")
        return 1
    _OUT.write_text(json.dumps(times, indent=1) + "\n", encoding="utf-8")
    print(f"{len(times)} files, {sum(times.values()):.0f} s: {_OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
