# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""No new pyright or ruff errors: the errors there are today are a baseline.

    python tools/pyright_baseline.py            check (fails on a new error)
    python tools/pyright_baseline.py --update   write today's errors as the baseline
    python tools/pyright_baseline.py --pins     the tool versions, for pip install

pyright runs with the [tool.pyright] settings in pyproject.toml and ruff as
`ruff check .`, the same as the lint commands in AGENTS.md. Errors are
grouped by file, rule and message (line numbers and other numbers left out,
so moving code is not a new error) and counted: a group with more errors
than the baseline is new, one with fewer was fixed. Both tools' groups are
kept in tools/pyright_baseline.json, with the versions they were made with
(another version finds other errors: CI installs these).
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
from collections import Counter

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_BASELINE = pathlib.Path(__file__).resolve().with_suffix(".json")
_TOOLS = ("pyright", "ruff")

Key = tuple[str, str, str]  # file, rule, message


def _relative(path: str, root: pathlib.Path) -> str:
    """The file's path from root, with forward slashes (pyright writes the
    drive letter in lower case, ruff doesn't)."""
    try:
        return pathlib.Path(path).resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return pathlib.Path(path).as_posix()


def _message(text: str) -> str:
    """The first line of a message, numbers left out (a line length or an
    argument count changes when the code around it does)."""
    first = text.replace(chr(0xA0), " ").splitlines()[0] if text else ""
    return re.sub(r"\d+", "N", " ".join(first.split()))


def _json_out(command: list[str], root: pathlib.Path) -> object:
    result = subprocess.run(
        command, cwd=root, capture_output=True, timeout=900, check=False
    )
    out = result.stdout.decode("utf-8", errors="replace")
    start = min((i for i in (out.find("{"), out.find("[")) if i >= 0), default=-1)
    if start < 0:
        err = result.stderr.decode("utf-8", errors="replace")
        raise SystemExit(
            f"{' '.join(command[2:4])}: no JSON output (exit {result.returncode})\n"
            f"{out[-2000:]}\n{err[-2000:]}"
        )
    return json.loads(out[start:])


def _version(tool: str) -> str:
    result = subprocess.run(
        [sys.executable, "-m", tool, "--version"],
        cwd=_ROOT, capture_output=True, text=True, timeout=600, check=False,
    )
    words = result.stdout.split()
    return words[-1] if words else "?"


def pyright_errors(root: pathlib.Path) -> Counter[Key]:
    data = _json_out([sys.executable, "-m", "pyright", "--outputjson"], root)
    assert isinstance(data, dict)
    found: Counter[Key] = Counter()
    for item in data.get("generalDiagnostics", []):
        if item.get("severity") != "error":
            continue
        key = (
            _relative(item.get("file", ""), root),
            item.get("rule") or "-",
            _message(item.get("message", "")),
        )
        found[key] += 1
    return found


def ruff_errors(root: pathlib.Path) -> Counter[Key]:
    data = _json_out(
        [sys.executable, "-m", "ruff", "check", ".", "--output-format=json",
         "--exit-zero", "--no-cache"],
        root,
    )
    assert isinstance(data, list)
    found: Counter[Key] = Counter()
    for item in data:
        key = (
            _relative(item.get("filename", ""), root),
            item.get("code") or "-",
            _message(item.get("message", "")),
        )
        found[key] += 1
    return found


def _load_baseline() -> dict:
    try:
        return json.loads(_BASELINE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _as_counter(rows: list[dict]) -> Counter[Key]:
    return Counter(
        {(r["file"], r["rule"], r["message"]): int(r["count"]) for r in rows}
    )


def _as_rows(found: Counter[Key]) -> list[dict]:
    return [
        {"file": f, "rule": rule, "message": msg, "count": n}
        for (f, rule, msg), n in sorted(found.items())
    ]


def _compare(tool: str, now: Counter[Key], before: Counter[Key]) -> int:
    """Prints what is new and what was fixed; returns how many are new."""
    new = {k: now[k] - before.get(k, 0) for k in now if now[k] > before.get(k, 0)}
    fixed = {
        k: before[k] - now.get(k, 0) for k in before if before[k] > now.get(k, 0)
    }
    total_new = sum(new.values())
    print(
        f"{tool}: {sum(now.values())} errors, baseline {sum(before.values())}: "
        f"{total_new} new, {sum(fixed.values())} fixed"
    )
    for (f, rule, msg), n in sorted(new.items()):
        print(f"  NEW   {f}: [{rule}] {msg}" + (f" (x{n})" if n > 1 else ""))
    for (f, rule, msg), n in sorted(fixed.items()):
        print(f"  fixed {f}: [{rule}] {msg}" + (f" (x{n})" if n > 1 else ""))
    return total_new


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--update", action="store_true",
                        help="write today's errors as the baseline")
    parser.add_argument("--only", choices=_TOOLS,
                        help="check (or update) one tool only")
    parser.add_argument("--pins", action="store_true",
                        help="print the baseline's tool versions for pip install")
    parser.add_argument("--root", type=pathlib.Path, default=_ROOT,
                        help="the tree to check (default: this checkout)")
    args = parser.parse_args()

    baseline = _load_baseline()
    if args.pins:
        versions = baseline.get("versions", {})
        print(" ".join(f"{t}=={versions[t]}" for t in _TOOLS if t in versions))
        return 0

    tools = [args.only] if args.only else list(_TOOLS)
    runners = {"pyright": pyright_errors, "ruff": ruff_errors}
    versions = {t: _version(t) for t in tools}
    for tool in tools:
        made_with = baseline.get("versions", {}).get(tool)
        if made_with and made_with != versions[tool] and not args.update:
            print(f"Note: {tool} is {versions[tool]}, the baseline was made "
                  f"with {made_with}: errors may differ for that reason.")

    found = {tool: runners[tool](args.root) for tool in tools}
    if args.update:
        out = dict(baseline)
        out.setdefault("versions", {}).update(versions)
        for tool in tools:
            out[tool] = _as_rows(found[tool])
            print(f"{tool}: {sum(found[tool].values())} errors in "
                  f"{len(found[tool])} groups written")
        text = json.dumps(out, indent=1, ensure_ascii=False) + "\n"
        _BASELINE.write_bytes(text.encode("utf-8"))
        return 0

    new = 0
    for tool in tools:
        new += _compare(tool, found[tool], _as_counter(baseline.get(tool, [])))
    if new:
        print(f"\n{new} new errors: fix them (or, if they are wanted, run "
              "tools/pyright_baseline.py --update and say why in the commit).")
        return 1
    print("No new errors.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
