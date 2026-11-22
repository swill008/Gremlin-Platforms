# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""gremlin.drivers: facts, detection, release check, file checks, job files."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from gremlin import drivers
from gremlin.drivers import (
    DRIVERS,
    HIDHIDE_KEY,
    UNINSTALL,
    VJOY_UNINSTALL,
    Job,
    JobResult,
    MemoryRegistry,
    RealRunnerBlocked,
    VJoyDevice,
)

REPO = Path(__file__).resolve().parents[2]


def test_module_has_no_qt_and_no_program_imports() -> None:
    for name in ("drivers.py", "driver_jobs.py"):
        tree = ast.parse((REPO / "gremlin" / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                mods = [node.module or ""]
            else:
                continue
            for mod in mods:
                assert "PySide" not in mod and "Qt" not in mod, (name, mod)
                if mod.startswith("gremlin"):
                    assert mod in ("gremlin", "gremlin.drivers"), (name, mod)


def test_driver_facts() -> None:
    assert list(DRIVERS) == ["vjoy", "vigembus", "hidhide"]
    assert DRIVERS["vjoy"].bundled_file == "vJoySetup_v2.2.2.0_Win10_Win11.exe"
    assert DRIVERS["vjoy"].restart_codes == (8,)
    assert DRIVERS["vigembus"].repo is None
    assert DRIVERS["hidhide"].restart_codes == (3010, 1641)
    for info in DRIVERS.values():
        assert len(info.sha256) == 64


@pytest.mark.parametrize(
    "a, b, expected",
    [
        ("2.1.9.1", "2.2.2.0", -1),
        ("2.2.2", "2.2.2.0", 0),
        ("v1.22.0", "1.21.442.0", 1),
        ("1.5.230.0", "1.5.230", 0),
        ("", "1.0", -1),
    ],
)
def test_compare(a: str, b: str, expected: int) -> None:
    assert drivers.compare(a, b) == expected


def test_version_tuple() -> None:
    assert drivers.version_tuple("v2.2.2.0") == (2, 2, 2, 0)


def _reg(
    vjoy: str | None = None,
    sys_version: str | None = None,
    vigem_entry: str | None = None,
    hidhide: str | None = None,
) -> MemoryRegistry:
    values: dict[str, dict[str, str]] = {}
    if vjoy:
        values[VJOY_UNINSTALL] = {"DisplayVersion": vjoy}
    if vigem_entry:
        values[UNINSTALL + r"\{966606F3-2745-49E9-BF15-5C3EAA4E9077}"] = {
            "DisplayName": "ViGEm Bus Driver",
            "DisplayVersion": vigem_entry,
        }
    if hidhide:
        values[HIDHIDE_KEY] = {"Version": hidhide}
    files = {drivers.vigembus_sys_path(): sys_version} if sys_version else {}
    return MemoryRegistry(values, files)


def test_status_states() -> None:
    reg = _reg(vjoy="2.1.9.1", sys_version="1.22.0.0", hidhide="1.6.0")
    states = {s.key: s.state for s in drivers.all_status(reg)}
    assert states == {"vjoy": "older", "vigembus": "same", "hidhide": "newer"}
    assert drivers.status("vjoy", _reg()).state == "missing"
    assert drivers.status("vjoy", _reg()).installed == ""


def test_vigembus_version_comes_from_the_uninstall_entry() -> None:
    # Found in the test machine: the 1.22.0 installer leaves a .sys file that
    # reports 1.21.442.0, while the Uninstall entry says 1.22.0.
    reg = _reg(sys_version="1.21.442.0", vigem_entry="1.22.0")
    assert drivers.installed_version("vigembus", reg) == "1.22.0"
    assert drivers.status("vigembus", reg).state == "same"


def test_vigembus_accepts_the_nefarius_docs_name() -> None:
    reg = MemoryRegistry(
        {
            UNINSTALL + r"\{X}": {
                "DisplayName": "Nefarius Virtual Gamepad Emulation Bus Driver",
                "DisplayVersion": "1.22.0",
            }
        },
        {drivers.vigembus_sys_path(): "1.21.442.0"},
    )
    assert drivers.installed_version("vigembus", reg) == "1.22.0"


def test_vigembus_uses_the_sys_version_when_there_is_no_entry() -> None:
    reg = _reg(sys_version="1.21.442.0")
    assert drivers.installed_version("vigembus", reg) == "1.21.442.0"
    assert drivers.installed_version("vigembus", _reg()) == ""


def _release_json(tag: str, names: list[str]) -> bytes:
    return json.dumps(
        {
            "tag_name": tag,
            "assets": [
                {"name": n, "browser_download_url": f"https://github.com/x/{n}"}
                for n in names
            ],
        }
    ).encode()


def test_latest_release_picks_matching_asset() -> None:
    asked = []

    def fetch(url: str, timeout: float) -> bytes:
        asked.append((url, timeout))
        return _release_json(
            "v2.2.3.0",
            ["vJoySetup_v2.2.3.0_Win7.exe", "vJoySetup_v2.2.3.0_Win10_Win11.exe"],
        )

    release = drivers.latest_release("vjoy", fetch=fetch, timeout=3.0)
    assert release == drivers.Release(
        "2.2.3.0",
        "https://github.com/x/vJoySetup_v2.2.3.0_Win10_Win11.exe",
        "vJoySetup_v2.2.3.0_Win10_Win11.exe",
    )
    assert asked == [
        ("https://api.github.com/repos/BrunnerInnovation/vJoy/releases/latest", 3.0)
    ]


def test_latest_release_none_cases() -> None:
    def offline(url: str, timeout: float) -> bytes:
        raise OSError("no network")

    assert drivers.latest_release("hidhide", fetch=offline) is None
    assert drivers.latest_release("hidhide", fetch=lambda u, t: b"not json") is None
    assert (
        drivers.latest_release(
            "hidhide", fetch=lambda u, t: _release_json("v1.6", ["other.zip"])
        )
        is None
    )
    called = []
    assert (
        drivers.latest_release("vigembus", fetch=lambda u, t: called.append(u)) is None
    )
    assert called == []


def test_real_fetch_signer_blocked_under_test(tmp_path: Path) -> None:
    with pytest.raises(RealRunnerBlocked):
        drivers.latest_release("vjoy")
    exe = tmp_path / "a.exe"
    exe.write_bytes(b"x")
    with pytest.raises(RealRunnerBlocked):
        drivers.check_download(exe, DRIVERS["vjoy"])


def test_check_bundled(tmp_path: Path) -> None:
    good = tmp_path / "good.exe"
    good.write_bytes(b"driver")
    info = drivers.DriverInfo(
        **{**DRIVERS["vjoy"].__dict__, "sha256": hashlib.sha256(b"driver").hexdigest()}
    )
    assert drivers.check_bundled(good, info) == ""
    assert drivers.sha256_of(good) == info.sha256
    bad = tmp_path / "bad.exe"
    bad.write_bytes(b"tampered")
    assert "does not match" in drivers.check_bundled(bad, info)
    assert "not found" in drivers.check_bundled(tmp_path / "none.exe", info)
    unknown = drivers.DriverInfo(**{**info.__dict__, "sha256": ""})
    assert "no SHA-256" in drivers.check_bundled(good, unknown)


def test_check_download_signer(tmp_path: Path) -> None:
    exe = tmp_path / "HidHide_1.6.0_x64.exe"
    exe.write_bytes(b"x")
    info = DRIVERS["hidhide"]
    good = "CN=Nefarius Software Solutions e.U., O=Nefarius, C=AT"
    assert drivers.check_download(exe, info, signer=lambda p: (True, good)) == ""
    quoted = 'CN="Nefarius Software Solutions, e.U.", C=AT'
    assert drivers.check_download(exe, info, signer=lambda p: (True, quoted)) == ""
    assert "no valid" in drivers.check_download(
        exe, info, signer=lambda p: (False, good)
    )
    other = "CN=Someone Else, O=Nefarius Software Solutions"
    assert "Someone Else" in drivers.check_download(
        exe, info, signer=lambda p: (True, other)
    )

    def broken(path: str) -> tuple[int, str]:
        raise OSError("boom")

    assert "could not be checked" in drivers.check_download(exe, info, signer=broken)
    assert "not found" in drivers.check_download(
        tmp_path / "none.exe", info, signer=lambda p: (True, good)
    )


def test_uninstall_entry() -> None:
    reg = MemoryRegistry(
        {
            UNINSTALL + r"\{ABC}": {"DisplayName": "Other"},
            UNINSTALL + r"\{0E2E3D4D-1111-2222-3333-444455556666}": {
                "DisplayName": "HidHide",
                "DisplayVersion": "1.5.230",
                "UninstallString": (
                    "MsiExec.exe /X{0E2E3D4D-1111-2222-3333-444455556666}"
                ),
            },
        }
    )
    key, fields = drivers.uninstall_entry("HidHide", reg)
    assert key == "{0E2E3D4D-1111-2222-3333-444455556666}"
    assert fields["DisplayVersion"] == "1.5.230"
    assert drivers.uninstall_entry("Nothing", reg) is None


def test_presets() -> None:
    assert [d.__dict__ for d in drivers.PRESETS["1 device, full"]] == [
        {"id": 1, "axes": drivers.VJOY_AXES, "buttons": 128, "hats": 4}
    ]
    two = drivers.PRESETS["2 devices, full"]
    assert [(d.id, d.buttons) for d in two] == [(1, 128), (2, 127)]
    assert drivers.alike_devices(two) == []


def test_default_buttons_countdown() -> None:
    assert drivers.default_buttons(1) == 128
    assert drivers.default_buttons(2) == 127
    assert drivers.default_buttons(16) == 113
    assert drivers.default_buttons(0) == 128  # clamped
    assert drivers.default_buttons(200) == 0  # clamped
    dev = drivers.new_device(2)
    assert (dev.id, dev.axes, dev.buttons, dev.hats) == (2, drivers.VJOY_AXES, 127, 4)
    assert dev.problem() == ""
    assert drivers.VJoyDevice(5).buttons == 128  # field default unchanged


def _dev(
    i: int, axes: tuple[str, ...] = drivers.VJOY_AXES, b: int = 10, h: int = 4
) -> drivers.VJoyDevice:
    return drivers.VJoyDevice(i, axes, b, h)


def test_alike_devices_groups() -> None:
    assert drivers.layout_key(_dev(1, ("x", "y"), 7, 2)) == (2, 7, 2)
    devs = [
        _dev(4),
        _dev(1),
        _dev(2, b=11),
        _dev(3, b=11),
        _dev(5, b=12),
        _dev(6, b=11),
    ]
    assert drivers.alike_devices(devs) == [[1, 4], [2, 3, 6]]
    assert drivers.alike_devices([_dev(1), _dev(2, b=9)]) == []
    assert drivers.alike_devices([]) == []


def test_alike_means_same_axis_count_not_same_axes() -> None:
    a = _dev(1, ("x", "y"))
    b = _dev(2, ("z", "rx"))
    assert drivers.alike_devices([a, b]) == [[1, 2]]
    assert drivers.alike_devices([a, _dev(2, ("x", "y", "z"))]) == []


def test_alike_warning_wording() -> None:
    tail = (
        " have the same number of axes, buttons and hats, so "
        "Gremlin-Platforms can't tell them apart and won't use them."
    )
    assert drivers.alike_warning([]) == ""
    assert drivers.alike_warning([[1, 3]]) == "vJoy 1 and vJoy 3" + tail
    assert drivers.alike_warning([[1, 2, 4]]) == "vJoy 1, vJoy 2 and vJoy 4" + tail
    assert drivers.alike_warning([[1, 3], [2, 5]]) == (
        "vJoy 1 and vJoy 3" + tail + " vJoy 2 and vJoy 5" + tail
    )


def test_jobs_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "jobs.json"
    jobs = [
        Job(
            "install",
            "vjoy",
            [
                {"path": "C:/d.exe", "kind": "download"},
                {"path": "C:/b.exe", "kind": "bundled"},
            ],
        ),
        Job("remove", "hidhide", []),
        Job(
            "vjoy_setup",
            "vjoy",
            [],
            [VJoyDevice(1), VJoyDevice(2, ("x", "y", "sl0"), 32, 0)],
        ),
    ]
    drivers.write_jobs(path, jobs)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["version"] == 1
    assert data["jobs"][2]["devices"][1] == {
        "id": 2,
        "axes": ["x", "y", "sl0"],
        "buttons": 32,
        "hats": 0,
    }
    assert drivers.read_jobs(path) == jobs


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        json.dumps({"jobs": []}),
        json.dumps({"version": 1, "jobs": [{"op": "format", "driver": "vjoy"}]}),
        json.dumps(
            {
                "version": 1,
                "jobs": [
                    {
                        "op": "install",
                        "driver": "x",
                        "files": [{"path": "a", "kind": "bundled"}],
                    }
                ],
            }
        ),
        json.dumps(
            {"version": 1, "jobs": [{"op": "install", "driver": "vjoy", "files": []}]}
        ),
        json.dumps(
            {
                "version": 1,
                "jobs": [
                    {
                        "op": "install",
                        "driver": "vjoy",
                        "files": [{"path": "a", "kind": "web"}],
                    }
                ],
            }
        ),
        json.dumps(
            {
                "version": 1,
                "jobs": [
                    {
                        "op": "vjoy_setup",
                        "driver": "vjoy",
                        "devices": [{"id": 1, "buttons": 129}],
                    }
                ],
            }
        ),
        json.dumps(
            {
                "version": 1,
                "jobs": [
                    {"op": "vjoy_setup", "driver": "vjoy", "devices": [{"id": 17}]}
                ],
            }
        ),
        json.dumps({"version": 1, "jobs": [{"op": "remove", "driver": "vjoy"}]}),
        json.dumps(
            {
                "version": 1,
                "jobs": [
                    {
                        "op": "vjoy_setup",
                        "driver": "vjoy",
                        "devices": [{"id": 1, "axes": 3}],
                    }
                ],
            }
        ),
        json.dumps(
            {
                "version": 1,
                "jobs": [
                    {
                        "op": "vjoy_setup",
                        "driver": "vjoy",
                        "devices": [{"id": 1, "axes": ["x", "wheel"]}],
                    }
                ],
            }
        ),
    ],
)
def test_read_jobs_rejects_bad_files(tmp_path: Path, content: str) -> None:
    path = tmp_path / "jobs.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        drivers.read_jobs(path)


def test_read_jobs_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        drivers.read_jobs(tmp_path / "none.json")


def test_results_round_trip_and_atomic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "results.json"
    results = [JobResult("done", "ok", True, "bundled"), JobResult("waiting")]
    replaced = []
    real_replace = drivers.os.replace

    def spy(src: str, dst: str) -> None:
        replaced.append((Path(src).name, Path(dst).name))
        real_replace(src, dst)

    monkeypatch.setattr(drivers.os, "replace", spy)
    drivers.write_results(path, results, finished=False)
    assert replaced == [("results.json.tmp", "results.json")]
    assert not (tmp_path / "results.json.tmp").exists()
    assert drivers.read_results(path) == (results, False)
    drivers.write_results(path, results, finished=True)
    assert drivers.read_results(path)[1] is True


def test_read_results_missing_or_partial(tmp_path: Path) -> None:
    path = tmp_path / "results.json"
    assert drivers.read_results(path) == ([], False)
    path.write_text('{"version": 1, "finished": true, "jobs": [{"sta', encoding="utf-8")
    assert drivers.read_results(path) == ([], False)
    path.write_text(
        json.dumps({"version": 1, "finished": True, "jobs": [{"state": "odd"}]}),
        encoding="utf-8",
    )
    assert drivers.read_results(path) == ([], False)


def test_pending(tmp_path: Path) -> None:
    assert drivers.pending_path(tmp_path) == tmp_path / "drivers" / "pending.json"
    assert drivers.read_pending(tmp_path) is None
    data = {"hidhide": {"version": "1.5.230", "file": "C:/h.exe", "kind": "bundled"}}
    drivers.write_pending(tmp_path, data)
    assert drivers.read_pending(tmp_path) == data
    drivers.clear_pending(tmp_path)
    assert drivers.read_pending(tmp_path) is None
    drivers.clear_pending(tmp_path)  # already gone: no error


def test_app_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delattr(drivers.sys, "frozen", raising=False)
    assert drivers.app_dir() is None
    monkeypatch.setattr(drivers.sys, "frozen", True, raising=False)
    monkeypatch.setattr(drivers.sys, "executable", str(tmp_path / "Gremlin.exe"))
    assert drivers.app_dir() == tmp_path.resolve()


def test_windows_registry_reads_only(monkeypatch: pytest.MonkeyPatch) -> None:
    # The real reader answers for a key that cannot exist, without raising.
    reg = drivers.WindowsRegistry()
    if drivers.os.name != "nt":
        pytest.skip("Windows only")
    assert reg.value(r"SOFTWARE\Gremlin-Platforms-test-no-such-key", "X") is None
    assert reg.subkeys(r"SOFTWARE\Gremlin-Platforms-test-no-such-key") == []
    assert reg.file_version(r"C:\no\such\file.sys") == ""


def test_signer_output_reads_non_ascii_subjects() -> None:
    """vJoy's signer subject has "S=Zürich"; a text-mode read of PowerShell's
    output failed on it (found on the user's PC, 2026-11-21)."""
    raw = ("Valid\r\nCN=Brunner Elektronik AG, L=Hittnau, S=Zürich, C=CH\r\n").encode(
        "utf-8"
    )
    valid, subject = drivers.signer_output(raw)
    assert valid
    assert drivers.subject_cn(subject) == "Brunner Elektronik AG"
    assert "Zürich" in subject
    # A byte that isn't UTF-8 (an OEM code page "ü") never raises.
    valid, subject = drivers.signer_output(b"Valid\r\nCN=Brunner, S=Z\x81rich\r\n")
    assert valid and subject.startswith("CN=Brunner")
    assert drivers.signer_output(b"") == (False, "")


# -- Visual C++ Runtime (spec 01 S193) ----------------------------------------

_RT_64 = drivers.RUNTIME_KEYS[0]
_RT_32 = drivers.RUNTIME_KEYS[1]


def test_runtime_is_not_a_driver_and_has_the_contract_values() -> None:
    rt = drivers.RUNTIME
    assert rt not in DRIVERS.values() and rt.key not in DRIVERS
    assert rt.key == "vcredist"
    assert rt.name == "Microsoft Visual C++ Runtime"
    assert rt.bundled_version == "14.44.35211"
    assert rt.bundled_file == "VC_redist.x64.exe"
    assert rt.sha256 == (
        "cc0ff0eb1dc3f5188ae6300faef32bf5beeba4bdd6e8e445a9184072096b713b"
    )
    assert rt.signer_prefix == "Microsoft Corporation"
    assert rt.repo is None and rt.asset_regex is None
    assert rt.install_args == ("/install", "/quiet", "/norestart")
    assert rt.restart_codes == (3010,)
    assert drivers.RUNTIME_DONE_CODES == (0, 1638, 3010)
    assert drivers.RUNTIME_RESTART_CODE == 3010


def test_runtime_detection() -> None:
    missing = MemoryRegistry({})
    assert drivers.runtime_installed(missing) is False
    assert drivers.runtime_version(missing) == ""

    both = MemoryRegistry({_RT_64: {"Installed": "1", "Version": "v14.51.36247.00"}})
    assert drivers.runtime_installed(both) is True
    assert drivers.runtime_version(both) == "14.51.36247.00"

    wow_only = MemoryRegistry(
        {_RT_32: {"Installed": "1", "Version": "v14.44.35211.00"}}
    )
    assert drivers.runtime_installed(wow_only) is True
    assert drivers.runtime_version(wow_only) == "14.44.35211.00"

    zero = MemoryRegistry({_RT_64: {"Installed": "0", "Version": "v14.51.36247.00"}})
    assert drivers.runtime_installed(zero) is False
    assert drivers.runtime_version(zero) == ""


def test_runtime_files_are_checked_like_drivers(tmp_path: Path) -> None:
    exe = tmp_path / "VC_redist.x64.exe"
    exe.write_bytes(b"not the real file")
    assert "does not match" in drivers.check_bundled(exe, drivers.RUNTIME)
    assert "not found" in drivers.check_bundled(tmp_path / "x.exe", drivers.RUNTIME)
    ms = "CN=Microsoft Corporation, O=Microsoft Corporation, L=Redmond, C=US"
    assert (
        drivers.check_download(exe, drivers.RUNTIME, signer=lambda p: (True, ms)) == ""
    )
    nef = "CN=Nefarius Software Solutions e.U., O=Nefarius, C=AT"
    assert "Nefarius" in drivers.check_download(
        exe, drivers.RUNTIME, signer=lambda p: (True, nef)
    )


def test_vjoy_device_axes_are_normalised_and_checked() -> None:
    device = VJoyDevice(1, ["SL0", "x", "x", "Y"])
    assert device.axes == ("x", "y", "sl0")
    assert VJoyDevice(1).axes == drivers.VJOY_AXES
    assert VJoyDevice(1, ()).problem() == ""
    bad = VJoyDevice(1, ("x", "wheel"))
    assert "wheel" in bad.problem()
    assert drivers.axis_label("sl0") == "S1"
    assert drivers.axis_label("rx") == "Rx"
    assert drivers.axis_label("wheel") == "WHEEL"


def test_job_file_without_axes_means_all_eight(tmp_path: Path) -> None:
    path = tmp_path / "jobs.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "jobs": [
                    {"op": "vjoy_setup", "driver": "vjoy", "devices": [{"id": 1}]}
                ],
            }
        ),
        encoding="utf-8",
    )
    [job] = drivers.read_jobs(path)
    assert job.devices[0].axes == drivers.VJOY_AXES


# -- the runtime is setup's alone (spec 06 S185, 01 D-01-RUNTIME-ROW) ---------


@pytest.mark.parametrize("op", ["install", "update", "remove", "vjoy_setup"])
def test_read_jobs_refuses_a_vcredist_job(tmp_path: Path, op: str) -> None:
    raw = {
        "op": op,
        "driver": "vcredist",
        "files": [{"path": "a", "kind": "download"}],
        "devices": [{"id": 1}],
    }
    path = tmp_path / "jobs.json"
    path.write_text(json.dumps({"version": 1, "jobs": [raw]}), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown driver 'vcredist'"):
        drivers.read_jobs(path)


def test_the_runtime_update_path_is_gone() -> None:
    for name in (
        "fetch_runtime",
        "real_download",
        "runtime_update_job",
        "RUNTIME_URL",
        "RUNTIME_DOWNLOAD_TIMEOUT_S",
    ):
        assert not hasattr(drivers, name)


def test_axis_tables_come_from_axis_names() -> None:
    from gremlin import axis_names

    assert drivers.VJOY_AXES == ("x", "y", "z", "rx", "ry", "rz", "sl0", "sl1")
    assert drivers.VJOY_AXIS_LABELS == ("X", "Y", "Z", "Rx", "Ry", "Rz", "S1", "S2")
    assert drivers.VJOY_AXES == tuple(a.vjoy_config for a in axis_names.AXES)


def test_can_untick_axis() -> None:
    one = VJoyDevice(1, ("rz",), 8, 0)
    two = VJoyDevice(2, ("x", "y"), 8, 0)
    assert not drivers.can_untick_axis(one, "rz")
    assert drivers.can_untick_axis(one, "x")  # ticking-state irrelevant: not ticked
    assert drivers.can_untick_axis(two, "x")
    assert drivers.can_untick_axis(two, "y")


def test_in_use_warning_wording() -> None:
    assert drivers.in_use_warning([]) == ""
    assert drivers.in_use_warning([4]) == (
        "vJoy 4 is in use by another program. Changing it can stop that "
        "program's controls working until it restarts. Change it anyway?"
    )
    assert drivers.in_use_warning([4, 1]) == (
        "vJoy 1 and vJoy 4 are in use by another program. Changing them can "
        "stop that program's controls working until it restarts. Change them anyway?"
    )
    assert drivers.in_use_warning([1, 2, 4]).startswith(
        "vJoy 1, vJoy 2 and vJoy 4 are in use by another program."
    )
