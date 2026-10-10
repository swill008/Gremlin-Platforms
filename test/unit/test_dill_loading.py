"""dill.dll comes only from the package's own folder (or the frozen
program's folder), never from the folder the program was started in.

`import dill` runs before joystick_gremlin.py changes to its install folder,
so a dill.dll planted in the start folder must not be loaded. Each check runs
in a fresh Python whose working folder holds a fake dill.dll.
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
PACKAGE_DLL = REPO / "dill" / "dill.dll"

pytestmark = pytest.mark.skipif(
    sys.platform != "win32" or not PACKAGE_DLL.is_file(),
    reason="needs Windows and dill/dill.dll",
)

# Records every ctypes load, imports dill, and reports what was loaded.
_PROBE = r"""
import ctypes, json, os, sys
loads = []
sys.addaudithook(
    lambda event, args: loads.append(str(args[0])) if event == "ctypes.dlopen" else None
)
meipass = os.environ.get("PROBE_MEIPASS")
if meipass:
    sys._MEIPASS = meipass
import dill
planted = os.path.join(os.getcwd(), "dill.dll")
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.GetModuleHandleW.restype = ctypes.c_void_p
k32.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
print(json.dumps({
    "module_path": dill._dll_path,
    "class_path": dill.DILL._dll_path,
    "same_handle": dill.DILL._dll is dill._di_listener_dll,
    "dill_loads": [p for p in loads if os.path.basename(p).lower() == "dill.dll"],
    "planted_loaded": bool(k32.GetModuleHandleW(planted)),
}))
"""


def _run(tmp_path: pathlib.Path, meipass: pathlib.Path | None = None) -> dict:
    start = tmp_path / "start"
    start.mkdir()
    # Not a real DLL: loading it at all fails the import.
    (start / "dill.dll").write_bytes(b"planted, not a DLL")
    home = tmp_path / "home"
    home.mkdir()
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO)
    env["USERPROFILE"] = str(home)
    env.pop("PROBE_MEIPASS", None)
    if meipass is not None:
        env["PROBE_MEIPASS"] = str(meipass)
    done = subprocess.run(
        [sys.executable, "-c", _PROBE],
        cwd=start,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout.strip().splitlines()[-1])


def _same(a: str, b: pathlib.Path) -> bool:
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(str(b))


def test_a_dill_dll_in_the_start_folder_is_not_loaded(tmp_path: pathlib.Path) -> None:
    seen = _run(tmp_path)
    assert _same(seen["module_path"], PACKAGE_DLL)
    assert _same(seen["class_path"], PACKAGE_DLL)
    assert os.path.isabs(seen["module_path"])
    assert not seen["planted_loaded"]
    # One load, from the package's own folder.
    assert len(seen["dill_loads"]) == 1, seen["dill_loads"]
    assert _same(seen["dill_loads"][0], PACKAGE_DLL)
    assert seen["same_handle"]


def test_the_frozen_program_loads_from_its_own_folder(tmp_path: pathlib.Path) -> None:
    frozen = tmp_path / "frozen"
    frozen.mkdir()
    shutil.copyfile(PACKAGE_DLL, frozen / "dill.dll")
    seen = _run(tmp_path, meipass=frozen)
    assert _same(seen["module_path"], frozen / "dill.dll")
    assert _same(seen["class_path"], frozen / "dill.dll")
    assert not seen["planted_loaded"]
    assert len(seen["dill_loads"]) == 1, seen["dill_loads"]
    assert _same(seen["dill_loads"][0], frozen / "dill.dll")


def test_dll_path_never_names_the_working_folder(tmp_path: pathlib.Path) -> None:
    import dill

    assert _same(dill.dll_path(meipass=str(tmp_path)), tmp_path / "dill.dll")
    assert _same(
        dill.dll_path(meipass=None, package_dir=str(tmp_path)), tmp_path / "dill.dll"
    )
    assert os.path.isabs(dill.dll_path())
