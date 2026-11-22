# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Gremlin Device Helper: entry point (S25).

    "Gremlin Device Helper.exe" --pipe NAME --journal PATH --key PATH --parent PID
    "Gremlin Device Helper.exe" --jobs PATH --results PATH [--parent PID]

The only part of Gremlin with administrator rights. Gremlin starts it with
Windows' confirmation; exactly one mode runs.

Pipe mode: it connects back to Gremlin's private pipe with the authkey from
the key file (read, then deleted) and disables or enables the game-input
devices the journal lists, one `pnputil` run each (it also enables a
physical USB device an older journal still lists, never disables one). It
ends on "quit", when the connection closes or when Gremlin's process is
gone.

Jobs mode (driver setup): it reads the job file, writes the results file
with every job "waiting", runs the jobs in order and rewrites the results
at each state change, with `finished` true at the end. Exit 0 when the
results were written, 2 for a bad job file.

Imports from the program only gremlin.device_helper_protocol, plus
gremlin.drivers and gremlin.driver_jobs (loaded only in jobs mode).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable
from multiprocessing.connection import Client
from pathlib import Path
from typing import Any, Protocol

from gremlin import device_helper_protocol as protocol

PNPUTIL_TIMEOUT_S = 30
POLL_S = 1.0
_PNPUTIL_SWITCH = {"disable": "/disable-device", "enable": "/enable-device"}

# (op, device id) -> "done" | "error: ..."
Runner = Callable[[str, str], str]

log = logging.getLogger("gremlin.device_helper")


class Connection(Protocol):
    """What the serve loop needs of a multiprocessing Connection."""

    def poll(self, timeout: float) -> bool: ...
    def recv(self) -> object: ...
    def send(self, obj: object) -> None: ...
    def close(self) -> None: ...


class RealRunnerBlocked(RuntimeError):
    """The real pnputil runner was called from a test."""


def _under_test() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST")) or "pytest" in sys.modules


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Exactly one mode: pipe (--pipe --journal --key --parent) or jobs
    (--jobs --results, --parent optional). Anything else exits with 2."""
    parser = argparse.ArgumentParser(prog="Gremlin Device Helper")
    parser.add_argument("--pipe")
    parser.add_argument("--journal")
    parser.add_argument("--key")
    parser.add_argument("--parent", type=int)
    parser.add_argument("--jobs")
    parser.add_argument("--results")
    args = parser.parse_args(argv)
    pipe_given = any(v is not None for v in (args.pipe, args.journal, args.key))
    jobs_given = args.jobs is not None or args.results is not None
    if pipe_given and jobs_given:
        parser.error("pipe mode and jobs mode can't be mixed")
    if jobs_given:
        if args.jobs is None or args.results is None:
            parser.error("jobs mode needs --jobs and --results")
        args.mode = "jobs"
    elif pipe_given:
        for name in ("pipe", "journal", "key", "parent"):
            if getattr(args, name) is None:
                parser.error(f"pipe mode needs --{name}")
        args.mode = "pipe"
    else:
        parser.error("give --pipe/--journal/--key/--parent or --jobs/--results")
    return args


def log_path(journal: str | Path) -> Path:
    """<data folder>\\logs\\device_helper.log; the journal is
    <data folder>\\screen saver mode\\devices.json."""
    return Path(journal).resolve().parent.parent / "logs" / "device_helper.log"


def setup_log(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    for old in list(log.handlers):
        log.removeHandler(old)
        old.close()
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)


def read_key(path: str | Path) -> bytes:
    """The authkey (the file's bytes as written); the file is deleted
    whether or not it could be read."""
    key_path = Path(path)
    try:
        return key_path.read_bytes()
    finally:
        try:
            key_path.unlink()
        except FileNotFoundError:
            pass
        except OSError as error:
            log.warning("Could not delete the key file: %s", error)


def load_journal(path: str | Path) -> dict[str, Any]:
    """The journal's entries, {id: {"name", "state", ...}}; {} when the
    file is missing or unreadable (then nothing is allowed)."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        log.warning("Could not read the journal %s: %s", path, error)
        return {}
    if not isinstance(data, dict):
        return {}
    for key in ("devices", "entries"):
        if isinstance(data.get(key), dict):
            return data[key]
    return data


def _pnputil_path() -> str:
    root = os.environ.get("SystemRoot", r"C:\Windows")
    return os.path.join(root, "System32", "pnputil.exe")


def real_runner(op: str, device_id: str) -> str:
    """One `pnputil /disable-device|/enable-device <id>`, bounded."""
    if _under_test():
        raise RealRunnerBlocked("device helper real pnputil runner called from a test")
    if os.name != "nt":
        return "error: needs Windows"
    command = [_pnputil_path(), _PNPUTIL_SWITCH[op], device_id]
    try:
        done = subprocess.run(
            command,
            capture_output=True,
            timeout=PNPUTIL_TIMEOUT_S,
            check=False,
            shell=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired:
        return f"error: pnputil took over {PNPUTIL_TIMEOUT_S} s"
    except OSError as error:
        return f"error: {error}"
    if done.returncode == 0:
        return "done"
    output = (done.stdout or b"") + (done.stderr or b"")
    text = " ".join(output.decode("oem", errors="replace").split())
    return f"error: pnputil exit {done.returncode}: {text[:300]}"


def parent_watch(pid: int) -> Callable[[], bool]:
    """A check that Gremlin's process is still running. The process is
    opened once, so a new process reusing the id doesn't count."""
    if os.name != "nt":
        return lambda: True
    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    SYNCHRONIZE = 0x00100000
    WAIT_TIMEOUT = 0x102
    handle = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
    if not handle:
        return lambda: False

    def alive() -> bool:
        return kernel32.WaitForSingleObject(handle, 0) == WAIT_TIMEOUT

    return alive


def handle(req: object, journal_path: str | Path, runner: Runner) -> dict:
    """The response to one request. Never raises."""
    if not isinstance(req, dict) or not isinstance(req.get("ids", []), list):
        log.warning("Bad request: %r", req)
        return {"ok": False, "results": {}, "error": "bad request"}
    op = req.get("op")
    if op not in protocol.OPS:
        _allowed, results = protocol.check_request(req, {})
        log.warning("Unknown operation %r", op)
        return {"ok": False, "results": results, "error": "unknown operation"}
    if op in ("ping", "quit"):
        return {"ok": True, "results": {}}
    allowed, refused = protocol.check_request(req, load_journal(journal_path))
    results: dict[str, str] = dict(refused)
    for device_id, why in refused.items():
        log.warning("%s %s %s", op, device_id, why)
    for device_id in allowed:
        try:
            result = runner(op, device_id)
        except RealRunnerBlocked:
            raise
        except Exception as error:  # noqa: BLE001 - reported, never a crash
            result = f"error: {error}"
        if result != "done" and not result.startswith("error: "):
            result = f"error: {result}"
        results[device_id] = result
        log.info("%s %s: %s", op, device_id, result)
    ok = all(value == "done" for value in results.values())
    return {"ok": ok, "results": results}


def serve(
    conn: Connection,
    journal_path: str | Path,
    runner: Runner,
    parent_alive: Callable[[], bool],
    poll_s: float = POLL_S,
) -> str:
    """Answers requests until "quit", the connection closes or the parent
    is gone; returns which ("quit" | "closed" | "parent gone")."""
    while True:
        if not parent_alive():
            return "parent gone"
        try:
            if not conn.poll(poll_s):
                continue
            req = conn.recv()
        except (EOFError, OSError):
            return "closed"
        except Exception as error:  # noqa: BLE001 - a bad message, not a crash
            log.warning("Could not read a request: %s", error)
            req = None
        response = handle(req, journal_path, runner)
        try:
            conn.send(response)
        except (EOFError, OSError):
            return "closed"
        if isinstance(req, dict) and req.get("op") == "quit":
            return "quit"


def _connect(pipe: str, authkey: bytes) -> Connection:
    address = (
        pipe if pipe.startswith(protocol.PIPE_PREFIX) else protocol.PIPE_PREFIX + pipe
    )
    return Client(address, family="AF_PIPE", authkey=authkey)


def jobs_log_path() -> Path:
    """The log in the data folder (Gremlin Platforms in the user profile)
    when it exists, else in the temp folder."""
    data = Path(os.path.expanduser("~")) / "Gremlin Platforms"
    if data.is_dir():
        return data / "logs" / "device_helper.log"
    return Path(tempfile.gettempdir()) / "device_helper.log"


def run_jobs(
    jobs_path: str | Path,
    results_path: str | Path,
    run_job: Callable[..., Any] | None = None,
    runner: Callable[..., Any] | None = None,
) -> int:
    """Jobs mode. Writes the results at every state change; a job that
    raises becomes "failed" and the rest still run. Returns the exit code:
    0 results written, 2 bad job file."""
    # Imported here: the pipe mode needs only the protocol (S25).
    from gremlin import driver_jobs, drivers
    run = run_job or driver_jobs.run_job
    command_runner = runner or driver_jobs.real_runner
    try:
        jobs = drivers.read_jobs(jobs_path)
    except (OSError, ValueError) as error:
        log.error("Bad job file %s: %s", jobs_path, error)
        return 2
    results = [drivers.JobResult(state="waiting") for _ in jobs]
    # This run's vJoy device check (12 S25b), carried across its jobs; every
    # run_job (an injected one too) gets it.
    vjoy_run = driver_jobs.VJoyRun(jobs)

    def publish(finished: bool) -> None:
        try:
            drivers.write_results(results_path, list(results), finished)
        except OSError as error:
            log.error("Could not write the results: %s", error)

    publish(False)
    for index, job in enumerate(jobs):
        results[index] = drivers.JobResult(state="running")
        publish(False)
        log.info("Job %d: %s %s", index, job.op, job.driver)
        try:
            if run is driver_jobs.run_job:
                # vJoy's installer log goes beside the helper's own log.
                results[index] = run(
                    job,
                    command_runner,
                    log_dir=str(jobs_log_path().parent),
                    vjoy_run=vjoy_run,
                )
            else:
                results[index] = run(job, command_runner, vjoy_run=vjoy_run)
        except Exception as error:  # noqa: BLE001 - reported, never a crash
            log.exception("Job %d failed", index)
            results[index] = drivers.JobResult(state="failed", message=str(error))
        log.info("Job %d: %s %s", index, results[index].state, results[index].message)
        publish(False)
    publish(True)
    return 0


def main(
    argv: list[str] | None = None,
    *,
    connect: Callable[[str, bytes], Connection] | None = None,
    runner: Runner | None = None,
    parent_alive: Callable[[], bool] | None = None,
    run_job: Callable[..., Any] | None = None,
    job_runner: Callable[..., Any] | None = None,
) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.mode == "jobs":
        try:
            setup_log(jobs_log_path())
        except OSError:
            pass
        log.info("Jobs mode started (parent %s)", args.parent)
        try:
            return run_jobs(args.jobs, args.results, run_job, job_runner)
        except Exception as error:  # noqa: BLE001 - never raises
            log.exception("Jobs mode failed: %s", error)
            return 2
    try:
        setup_log(log_path(args.journal))
    except OSError:
        pass
    log.info("Started for process %d", args.parent)
    try:
        authkey = read_key(args.key)
    except OSError as error:
        log.error("Could not read the key file: %s", error)
        return 2
    if not authkey:
        log.error("The key file was empty")
        return 2
    try:
        conn = (connect or _connect)(args.pipe, authkey)
    except Exception as error:  # noqa: BLE001
        log.error("Could not connect to Gremlin: %s", error)
        return 3
    try:
        reason = serve(
            conn,
            args.journal,
            runner or real_runner,
            parent_alive or parent_watch(args.parent),
        )
    finally:
        try:
            conn.close()
        except OSError:
            pass
    log.info("Ended: %s", reason)
    return 0


if __name__ == "__main__":
    sys.exit(main())
