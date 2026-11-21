"""01 S187-S192, 06 S186: setup's Drivers page and driver jobs.

ISCC is not run in tests, so these read installer/gremlin_platforms.iss: the
names and keys must match gremlin/drivers.py, the job file the script writes
must be one the helper reads, and the Pascal must at least be well formed.
"""

from __future__ import annotations

import json
import pathlib
import re

import pytest

from gremlin import drivers

_ROOT = pathlib.Path(__file__).parents[2]
_ISS = _ROOT / "installer" / "gremlin_platforms.iss"


def _iss() -> str:
    return _ISS.read_text(encoding="utf-8")


def _code() -> str:
    return _iss().split("[Code]", 1)[1]


def _section(name: str) -> str:
    return _iss().split(f"[{name}]", 1)[1].split("\n[", 1)[0]


def _routine(iss: str, header: str) -> str:
    body = iss[iss.index(header):]
    return body[: body.index("\nend;") + 5]


def _pascal_string(text: str) -> str:
    """Joins 'a' + 'b' Pascal string pieces into one Python string."""
    return "".join(re.findall(r"'((?:[^']|'')*)'", text)).replace("''", "'")


def _define(name: str) -> str:
    found = re.search(rf'^#define {name} "([^"]*)"$', _iss(), re.M)
    assert found, f"#define {name} missing"
    return found.group(1)


def _strip(code: str) -> str:
    """The Pascal code with strings, comments and // lines blanked out.

    Fails on a { comment that holds another '{': Pascal comments don't nest,
    so its first '}' would end it early (an easy slip with '{app}' or JSON).
    """
    out: list[str] = []
    i = 0
    while i < len(code):
        c = code[i]
        if c == "'":
            j = i + 1
            while True:
                j = code.index("'", j)
                if code[j + 1: j + 2] == "'":
                    j += 2
                    continue
                break
            out.append("''")
            i = j + 1
        elif c == "{":
            j = code.index("}", i)
            inner = code[i + 1: j]
            assert "{" not in inner, f"brace inside a {{ }} comment: {inner[:60]!r}"
            out.append(" ")
            i = j + 1
        elif code.startswith("(*", i):
            j = code.index("*)", i)
            out.append(" ")
            i = j + 2
        elif code.startswith("//", i):
            j = code.find("\n", i)
            i = len(code) if j < 0 else j
        else:
            out.append(c)
            i += 1
    return "".join(out)


# -- a small evaluator for the script's string expressions ---------------------


def _eval(expr: str, env: dict[str, str]) -> str:
    """Evaluates a Pascal '+' chain of string literals, #$xxxx characters and
    names looked up in env (JsonEscape(x) escapes env[x] like the script)."""
    result = []
    for part in _split_plus(expr):
        part = part.strip()
        if part.startswith("'"):
            result.append(part[1:-1].replace("''", "'"))
        elif part.startswith("#$"):
            result.append(chr(int(part[2:], 16)))
        elif part.startswith("JsonEscape(") and part.endswith(")"):
            value = env[part[len("JsonEscape("):-1].strip()]
            result.append(value.replace("\\", "\\\\").replace('"', '\\"'))
        else:
            result.append(env[part])
    return "".join(result)


def _split_plus(expr: str) -> list[str]:
    parts, depth, current, in_string = [], 0, "", False
    for c in expr:
        if c == "'":
            in_string = not in_string
        if not in_string:
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            elif c == "+" and depth == 0:
                parts.append(current)
                current = ""
                continue
        current += c
    parts.append(current)
    return parts


def _assignments(routine: str, target: str) -> list[str]:
    """The right-hand sides of `target := ...;` in a routine, in order."""
    found = re.findall(
        rf"{re.escape(target)} := ((?:'(?:[^']|'')*'|[^;'])*);", routine
    )
    return [" ".join(line.split()) for line in found]


# -- 01 S187: the Drivers page ---------------------------------------------------


def test_the_drivers_page_comes_after_the_folder_page() -> None:
    create = _routine(_code(), "procedure CreateDriverPages;")
    assert "CreateCustomPage(wpSelectDir, 'Drivers'," in create
    assert "TNewCheckListBox.Create(DriversPage)" in create
    assert "DisableDirPage=no" in _iss()


def test_missing_is_ticked_older_unticked_same_or_newer_has_no_box() -> None:
    fill = _routine(_code(), "procedure FillDriverList;")
    assert "(Drivers[I].State = 'missing') or (Drivers[I].State = 'older')" in fill
    # AddCheckBox(caption, sub item, level, checked, ...): ticked only when missing.
    assert re.search(
        r"AddCheckBox\(Drivers\[I\]\.Name, DriverLabel\(I\),\s*0, "
        r"Drivers\[I\]\.State = 'missing', True,",
        fill,
    )
    assert "AddGroup(Drivers[I].Name, DriverLabel(I)" in fill  # no box
    words = _routine(_code(), "function DriverLabel(")
    assert "'not installed'" in words
    assert "'update available: ' + Drivers[I].Installed + ' ' + #$2192 + ' ' +" in words


def test_states_follow_drivers_compare() -> None:
    detect = _routine(_code(), "procedure DetectDrivers;")
    for line in (
        "-1: Drivers[I].State := 'older';",
        "0: Drivers[I].State := 'same';",
        "Drivers[I].State := 'newer';",
        "Drivers[I].State := 'missing'",
    ):
        assert line in detect
    compare = _routine(_code(), "function CompareVersions(")
    assert "NextVersionPart(A)" in compare and "NextVersionPart(B)" in compare


def test_bundled_names_and_versions_match_drivers_py() -> None:
    defines = {
        "vjoy": ("VJoyBundled", "VJoyFile"),
        "vigembus": ("ViGEmBusBundled", "ViGEmBusFile"),
        "hidhide": ("HidHideBundled", "HidHideFile"),
    }
    assert list(drivers.DRIVERS) == list(defines)
    init = _routine(_code(), "procedure InitDrivers;")
    for index, (key, info) in enumerate(drivers.DRIVERS.items()):
        version_name, file_name = defines[key]
        assert _define(version_name) == info.bundled_version
        assert _define(file_name) == info.bundled_file
        call = re.search(
            rf"SetDriver\({index}, '{key}', '{re.escape(info.name)}', "
            rf"'\{{#{version_name}\}}', '\{{#{file_name}\}}',\s*"
            r"'([^']*)', '([^']*)', '([^']*)'\);",
            init,
        )
        assert call, f"SetDriver for {key}"
        repo, prefix, suffix = call.groups()
        assert repo == (info.repo or "")
        if info.asset_regex is None:
            assert (prefix, suffix) == ("", "")
        else:
            # Prefix + digits and dots + suffix is drivers.py's asset_regex.
            assert re.escape(prefix) + r"[\d.]+" + re.escape(suffix) == info.asset_regex


def test_detection_reads_the_same_keys_as_drivers_py() -> None:
    code = _code()
    assert f"UninstallRoot = '{drivers.UNINSTALL}';" in code
    assert f"VJoyUninstallKey = '{drivers.VJOY_UNINSTALL}';" in code
    assert f"HidHideKey = '{drivers.HIDHIDE_KEY}';" in code
    assert f"ViGEmBusDisplayName = '{drivers.VIGEMBUS_DISPLAY_NAME}';" in code
    found = _routine(code, "function InstalledDriverVersion(")
    assert "MachineValue(VJoyUninstallKey, 'DisplayVersion')" in found
    assert "MachineValue(HidHideKey, 'Version')" in found
    assert r"ExpandConstant('{sys}\drivers\ViGEmBus.sys')" in found
    assert pathlib.Path(drivers.vigembus_sys_path()).parts[-3:] == (
        "System32", "drivers", "ViGEmBus.sys"
    )
    assert "UninstallVersion(ViGEmBusDisplayName)" in found
    # Both registry views, like drivers.WindowsRegistry.
    machine = _routine(code, "function MachineValue(")
    assert "HKLM64" in machine and "HKLM32" in machine


# -- 01 S188: bundled copies and licences ---------------------------------------


def test_bundled_installers_and_licences_are_in_files() -> None:
    files = _section("Files")
    for info in drivers.DRIVERS.values():
        name = {
            "vjoy": "VJoyFile", "vigembus": "ViGEmBusFile", "hidhide": "HidHideFile",
        }[info.key]
        line = next(
            (x for x in files.splitlines() if f"{{#{name}}}" in x), None
        )
        assert line, f"{info.key} is not in [Files]"
        assert line.startswith(
            rf'Source: "drivers\{{#{name}}}"; DestDir: "{{app}}\drivers"'
        )
        # A missing bundled file fails the build, never a silent gap.
        assert "skipifsourcedoesntexist" not in line
    assert 'Source: "..\\licenses\\*"; DestDir: "{app}\\licenses"' in files
    for licence in ("vjoy.txt", "vigembus.txt", "hidhide.txt"):
        assert (_ROOT / "licenses" / licence).is_file(), licence


# -- 01 S189: newer versions -----------------------------------------------------


def test_vjoy_and_hidhide_ask_github_and_download_with_progress() -> None:
    code = _code()
    check = _routine(code, "procedure CheckLatest(")
    assert "if Drivers[I].LatestChecked or (Drivers[I].Repo = '') then" in check
    assert "'https://api.github.com/repos/' + Drivers[I].Repo +" in check
    assert "'/releases/latest'" in check
    assert "CompareVersions(Tag, Drivers[I].Bundled) <= 0" in check
    assert "(Copy(Url, 1, 19) = 'https://github.com/')" in check
    fetch = _routine(code, "function FetchText(")
    assert "Http.SetTimeouts(5000, 5000, 5000, 5000);" in fetch
    assert "except" in fetch
    create = _routine(code, "procedure CreateDriverPages;")
    assert "CreateDownloadPage('Drivers'," in create
    download = _routine(code, "procedure DownloadNewerDrivers;")
    assert "DriverDownloadPage.Download;" in download
    # A failed or stopped download leaves the bundled copy, never stops setup.
    after = download[download.index("except"):]
    assert "Drivers[I].Download := '';" in after
    assert "Result := False" not in download
    click = _routine(code, "function NextButtonClick(")
    assert "else if CurPageID = wpReady then" in click
    assert "DownloadNewerDrivers;" in click


# -- 12 S25: the job file -----------------------------------------------------------


def _job_json(op: str, key: str, download: str, bundled: str) -> str:
    routine = _routine(_code(), "function JobJson(")
    files_parts = _assignments(routine, "Files")
    assert len(files_parts) == 3, files_parts  # '', download, bundled
    env = {
        "Drivers[I].Download": download,
        "BundledPath(I)": bundled,
        "Drivers[I].Op": op,
        "Drivers[I].Key": key,
    }
    files = ""
    if op != "remove":
        if download:
            env["Files"] = files
            files = _eval(files_parts[1], env)
        env["Files"] = files
        files = _eval(files_parts[2], env)
    env["Files"] = files
    (result,) = _assignments(routine, "Result")
    return _eval(result, env)


def _job_file(jobs: list[str]) -> str:
    routine = _routine(_code(), "function WriteJobFile(")
    (line,) = _assignments(routine, "Lines[0]")
    assert "Jobs := Jobs + ', ';" in routine
    return _eval(line, {"Jobs": ", ".join(jobs)})


def test_the_job_file_is_one_the_helper_reads(tmp_path: pathlib.Path) -> None:
    # Paths with a quote-free space and backslashes, as {app} and {tmp} are.
    app = r"C:\Users\A B\AppData\Local\Programs\Gremlin-Platforms"
    tmp = r"C:\Users\A B\AppData\Local\Temp\is-ABC.tmp"
    text = _job_file([
        _job_json("install", "vjoy", tmp + r"\vJoySetup_v2.2.3.0_Win10_Win11.exe",
                  app + r"\drivers\vJoySetup_v2.2.2.0_Win10_Win11.exe"),
        _job_json("update", "vigembus", "",
                  app + r"\drivers\ViGEmBus_1.22.0_x64_x86_arm64.exe"),
        _job_json("remove", "hidhide", "", app + r"\drivers\HidHide_1.5.230_x64.exe"),
    ])
    data = json.loads(text)
    assert data["version"] == 1
    path = tmp_path / "jobs.json"
    path.write_text(text, encoding="utf-8")
    jobs = drivers.read_jobs(path)
    assert [(j.op, j.driver) for j in jobs] == [
        ("install", "vjoy"), ("update", "vigembus"), ("remove", "hidhide")
    ]
    # Download first, bundled second (01 S189, 12 S25); a remove lists no file.
    assert jobs[0].files == [
        {"path": tmp + r"\vJoySetup_v2.2.3.0_Win10_Win11.exe", "kind": "download"},
        {
            "path": app + r"\drivers\vJoySetup_v2.2.2.0_Win10_Win11.exe",
            "kind": "bundled",
        },
    ]
    assert [f["kind"] for f in jobs[1].files] == ["bundled"]
    assert jobs[2].files == []
    assert all(j.devices == [] for j in jobs)


def test_the_job_file_has_no_bom_and_lives_in_tmp() -> None:
    code = _code()
    write = _routine(code, "function WriteJobFile(")
    assert "SaveStringsToUTF8FileWithoutBOM(Path, Lines, False)" in write
    run = _routine(code, "procedure RunDriverJobs;")
    assert "JobFile := ExpandConstant('{tmp}\\' + JobFileName);" in run
    assert "ResultsFile := ExpandConstant('{tmp}\\' + ResultsFileName);" in run
    ops = _routine(code, "procedure DriversPageDone;")
    for op in re.findall(r"Drivers\[I\]\.Op := '(\w+)'", ops):
        assert op in drivers.JOB_OPS


# -- 01 S190: one admin prompt -----------------------------------------------------


def test_one_elevated_helper_start_with_jobs_and_results() -> None:
    iss = _iss()
    assert "PrivilegesRequired=lowest" in iss
    assert _define("HelperExeName") == "Gremlin Device Helper.exe"
    spec = (_ROOT / "joystick_gremlin.spec").read_text(encoding="utf-8")
    assert 'helper_name = "Gremlin Device Helper"' in spec
    run = _routine(_code(), "procedure RunDriverJobs;")
    assert run.count("ShellExec(") == 1
    start = "ShellExec('runas', ExpandConstant('{app}\\{#HelperExeName}'), Params,"
    assert start in run
    assert "Params := '--jobs ' + AddQuotes(JobFile) + ' --results ' +" in run
    assert "AddQuotes(ResultsFile);" in run
    assert "WaitForHelper(ResultsFile)" in run
    # The drivers' one prompt, and the runtime's own when it is missing (S193).
    assert _code().count("'runas'") == 2
    assert _runtime_install().count("'runas'") == 1


def test_progress_comes_from_the_results_file_until_finished() -> None:
    code = _code()
    read = _routine(code, "function ReadDriverResults(")
    for key in ("'jobs'", "'state'", "'message'", "'restart'", "'finished'"):
        assert key in read
    wait = _routine(code, "procedure WaitForHelper(")
    assert "if AllDone then" in wait
    assert "DriverProgressPage.SetProgress(DoneCount," in wait
    # Bounded: a helper that never starts or never finishes fails its jobs.
    assert "for Tick := 1 to Limit do" in wait
    assert "FailOpenJobs('Gremlin Device Helper did not start.');" in wait
    assert "FailOpenJobs('Gremlin Device Helper did not finish in time.');" in wait


def test_the_results_file_fields_match_drivers_py(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "results.json"
    drivers.write_results(
        path, [drivers.JobResult("done", "vJoy 2.2.2.0 installed", True, "bundled")],
        finished=True,
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    assert set(data) == {"version", "finished", "jobs"}
    assert set(data["jobs"][0]) == {"state", "message", "restart", "used"}
    # The script's reader keeps to ASCII \u escapes, which json writes by default.
    assert path.read_text(encoding="utf-8").isascii()


# -- 01 S191: Gremlin always installs ---------------------------------------------


def test_a_driver_failure_never_stops_the_install() -> None:
    code = _code()
    run = _routine(code, "procedure RunDriverJobs;")
    assert run.index("try") < run.index("ShellExec(")
    assert "except" in run and "GetExceptionMessage" in run
    assert "FailOpenJobs('Administrator permission was not given.')" in run
    step = _routine(code, "procedure CurStepChanged(")
    assert step.index("Finished := True;") < step.index("RunDriverJobs;")
    click = _routine(code, "function NextButtonClick(")
    # Only the folder check can keep setup on a page.
    assert click.count("Result := False;") == 1
    assert "Drivers" not in _routine(code, "function PrepareToInstall(")


def test_the_last_page_lists_results_and_offers_a_restart() -> None:
    code = _code()
    page = _routine(code, "procedure CurPageChanged(")
    assert "CurPageID <> wpFinished" in page
    assert "'Drivers:' + #13#10 + DriverSummary" in page
    assert "'Restart now'" in page and "'Restart later'" in page
    assert "Result := DriversNeedRestart or RuntimeNeedRestart;" in _routine(
        code, "function NeedRestart:"
    )
    summary = _routine(code, "procedure BuildDriverSummary;")
    assert "if Drivers[I].ResultRestart then" in summary


def test_the_ready_page_says_what_and_when() -> None:
    memo = _routine(_code(), "function UpdateReadyMemo(")
    assert "'Drivers, after the files are copied (Windows asks for '" in memo
    assert "MemoDirInfo" in memo and "MemoTasksInfo" in memo


def test_setup_closed_program_starts_after_the_drivers() -> None:
    code = _code()
    restart = _routine(code, "function RestartAfterClose:")
    assert "not DriverJobsPlanned" in restart
    run = _routine(code, "procedure RunDriverJobs;")
    tail = run[run.rindex("end;", 0, len(run) - 5):]
    assert "ClosedByInstaller and not LaunchAfterSilentUpdate" in tail
    assert "ExecAsOriginalUser(AppExe," in tail


# -- 06 S186: the HidHide update's first half ---------------------------------------


def test_hidhide_step_1_prompt_has_the_spec_words() -> None:
    ask = _routine(_code(), "function AskHidHideStep1(")
    assert "TaskDialogMsgBox('HidHide update, step 1 of 2'," in ask
    assert "['Continue', 'Skip HidHide update']" in ask
    body = ask[ask.index("'Setup will"): ask.index("mbConfirmation")]
    text = _pascal_string(body)
    assert text.startswith("Setup will remove HidHide ")
    assert "After a restart, Gremlin installs HidHide " in text
    assert "and asks for one more restart." in text
    assert text.endswith("Devices aren't hidden until then.")
    done = _routine(_code(), "procedure DriversPageDone;")
    # Nested, so the prompt shows only for a HidHide remove.
    nested = "if Drivers[I].Op = 'remove' then\n      if not AskHidHideStep1(I) then"
    assert nested in done
    assert "DriverList.Checked[Drivers[I].Row] := False;" in done


def test_removing_hidhide_shows_progress_and_asks_for_the_restart() -> None:
    code = _code()
    progress = _routine(code, "function JobProgressText(")
    assert "'Removing HidHide ' + Drivers[I].Installed + #$2026" in progress
    page = _routine(code, "procedure CurPageChanged(")
    assert "'Restart needed to continue the HidHide update'" in page
    summary = _routine(code, "procedure BuildDriverSummary;")
    assert "HidHideRemoved := True;" in summary


def test_pending_json_is_written_after_the_remove(tmp_path: pathlib.Path) -> None:
    code = _code()
    run = _routine(code, "procedure RunDriverJobs;")
    assert run.index("BuildDriverSummary;") < run.index(
        "if HidHideRemoved then\n        WriteHidHidePending(DriverIndex('hidhide'));"
    )
    pending = _routine(code, "procedure WriteHidHidePending(")
    assert "ExpandConstant('{app}\\drivers\\pending.json')" in pending
    parts = drivers.pending_path(pathlib.Path("A")).parts
    assert parts[-2:] == ("drivers", "pending.json")
    (line,) = _assignments(pending, "Lines[0]")
    text = _eval(line, {
        "Version": "1.5.230",
        "Path": r"C:\Users\A B\Gremlin-Platforms\drivers\HidHide_1.5.230_x64.exe",
        "Kind": "bundled",
    })
    app = tmp_path / "app"
    (app / "drivers").mkdir(parents=True)
    drivers.pending_path(app).write_text(text, encoding="utf-8")
    assert drivers.read_pending(app) == {
        "hidhide": {
            "version": "1.5.230",
            "file": r"C:\Users\A B\Gremlin-Platforms\drivers\HidHide_1.5.230_x64.exe",
            "kind": "bundled",
        }
    }
    assert "SaveStringsToUTF8FileWithoutBOM(" in pending


# -- 01 S192 and silent installs ---------------------------------------------------


def test_uninstall_leaves_the_drivers() -> None:
    iss = _iss()
    assert "[UninstallRun]" not in iss
    assert "msiexec" not in iss.lower()
    assert "UninstallString" not in iss
    deleted = _section("UninstallDelete")
    driver_lines = [x for x in deleted.splitlines() if "drivers" in x.lower()]
    assert driver_lines == ['Type: files; Name: "{app}\\drivers\\pending.json"']
    assert "UninstallNeedRestart" not in iss
    assert "CurUninstallStepChanged" not in iss


def test_a_silent_install_skips_the_drivers() -> None:
    code = _code()
    planned = _routine(code, "function DriverJobsPlanned:")
    assert planned.index("if WizardSilent then") < planned.index("for I := 0")
    head = planned[planned.index("if WizardSilent then"): planned.index("for I")]
    assert "Exit;" in head
    run = _routine(code, "procedure RunDriverJobs;")
    assert run.split("begin", 1)[1].lstrip().startswith(
        "if not DriverJobsPlanned then\n    Exit;"
    )
    click = _routine(code, "function NextButtonClick(")
    silent = click.index("if WizardSilent then\n    Exit;")
    assert silent < click.index("DriversPageDone") < click.index("DownloadNewerDrivers")
    skip = _routine(code, "function ShouldSkipPage(")
    assert "(PageID = DriversPage.ID) and WizardSilent" in skip
    # The in-app update path is unchanged.
    assert "Check: LaunchAfterSilentUpdate" in _section("Run")


# -- the Pascal is well formed (no compiler in this batch) ---------------------------


def test_the_code_section_is_well_formed() -> None:
    code = _strip(_code())
    words = re.findall(r"[A-Za-z_]\w*", code.lower())
    opens = sum(words.count(w) for w in ("begin", "case", "try", "record"))
    assert opens == words.count("end"), (opens, words.count("end"))
    assert code.count("(") == code.count(")")
    assert code.count("[") == code.count("]")


@pytest.mark.parametrize(
    "name",
    [
        "DriverJobsPlanned", "CompareVersions", "InstalledDriverVersion",
        "DetectDrivers", "CheckLatest", "DownloadNewerDrivers", "DriversPageDone",
        "WriteJobFile", "ReadDriverResults", "WaitForHelper", "WriteHidHidePending",
        "BuildDriverSummary", "RunDriverJobs", "CharAt", "JsonValue",
        "RuntimeInstalled", "RuntimeFileTrusted", "RuntimeCodeResult",
        "SetRuntimeText", "InstallRuntime",
    ],
)
def test_every_routine_is_declared_before_it_is_used(name: str) -> None:
    # Pascal Script has no forward use: the declaration must come first.
    code = _strip(_code())
    declared = re.search(rf"\b(?:function|procedure) {name}\b", code)
    assert declared, name
    first_use = re.search(rf"\b{name}\b", code)
    assert first_use and first_use.start() >= declared.start(), name


# -- 01 S187 (answer 1a): the vJoy device choice on the Drivers page (06 S185) ------


def _const(name: str) -> str:
    found = re.search(rf"^  {name} = '((?:[^']|'')*)';$", _code(), re.M)
    assert found, f"const {name} missing"
    return found.group(1).replace("''", "'")


def test_the_vjoy_choice_has_the_presets_and_custom() -> None:
    from gremlin.ui import drivers_model

    assert [_const("VJoyPresetOne"), _const("VJoyPresetTwo")] == list(drivers.PRESETS)
    assert _const("VJoyCustom") == drivers_model.CUSTOM
    create = _routine(_code(), "procedure CreateDriverPages;")
    assert "VJoyPresetBox := TNewComboBox.Create(DriversPage);" in create
    assert "VJoyPresetBox.Style := csDropDownList;" in create
    items = re.findall(r"VJoyPresetBox\.Items\.Add\((\w+)\);", create)
    assert items == ["VJoyPresetOne", "VJoyPresetTwo", "VJoyCustom"]
    # The Custom editor: one line per device, "axes, buttons, hats".
    assert "VJoyCustomMemo := TNewMemo.Create(DriversPage);" in create
    # Presets are full devices: 8 axes, 128 buttons, 4 hats (drivers.PRESETS).
    preset = _routine(_code(), "procedure PresetDevices(")
    assert "AddVJoyDevice(List, K, 8, 128, 4);" in preset
    assert "if Name = VJoyPresetTwo then\n    Count := 2;" in preset
    for name, devices in drivers.PRESETS.items():
        assert [(d.axes, d.buttons, d.hats) for d in devices] == [(8, 128, 4)] * (
            2 if name == _const("VJoyPresetTwo") else 1
        )
    # Custom: 1-16 devices, each number held to its range.
    memo = _routine(_code(), "procedure ReadCustomMemo;")
    assert "if GetArrayLength(VJoyChosen) >= VJoyMaxDevices then" in memo
    assert "ClampInt(StrToIntDef(NextToken(Line), 8), 0, 8)" in memo
    assert "ClampInt(StrToIntDef(NextToken(Line), 128), 0, 128)" in memo
    assert "ClampInt(StrToIntDef(NextToken(Line), 4), 0, 4)" in memo
    assert re.search(r"^  VJoyMaxDevices = 16;$", _code(), re.M)
    assert drivers.VJOY_MAX_DEVICES == 16


def test_vjoy_not_installed_gets_the_default_preset_and_no_current_layout() -> None:
    init = _routine(_code(), "procedure InitVJoyChoice;")
    read = init.index("ReadVJoyLayout;")
    assert init.index("if not WizardSilent then") < read
    assert init.index("State <> 'missing' then") < read
    assert "CopyVJoyDevices(VJoyCurrent, VJoyChosen)" in init
    assert "PresetDevices(VJoyPresetOne, VJoyChosen);" in init
    line = _routine(_code(), "function VJoyCurrentLine:")
    assert "State = 'missing' then\n    Result := ''" in line
    create = _routine(_code(), "procedure CreateDriverPages;")
    assert "Items.IndexOf(MatchingPreset(VJoyChosen))" in create
    order = _routine(_code(), "procedure InitializeWizard;")
    assert order.index("InitDrivers;") < order.index("InitVJoyChoice;") < order.index(
        "CreateDriverPages;"
    )


def test_the_current_layout_is_read_like_driver_jobs() -> None:
    code = _code()
    run = _routine(code, "function RunVJoyConfig(")
    # Never as administrator; output to a file in setup's temp folder.
    assert "ExecAsOriginalUser(ExpandConstant('{cmd}')" in run
    assert "ewWaitUntilTerminated" in run
    assert "ExpandConstant('{tmp}\\') + VJoyCaptureFile" in run
    assert "LoadStringsFromFile(OutFile, Lines)" in run
    assert "'runas'" not in run
    path = _routine(code, "function VJoyConfigPath:")
    assert r"ExpandConstant('{commonpf64}\vJoy\x64\vJoyConfig.exe')" in path
    layout = _routine(code, "procedure ReadVJoyLayout;")
    assert "RunVJoyConfig('-t', Lines)" in layout
    assert "RunVJoyConfig('-t ' + IntToStr(Ids[J]), Report)" in layout
    # The same rules as parse_status_list and parse_report.
    assert _const("VJoyAxisNames") == " ".join(drivers.VJOY_AXES)
    status = _routine(code, "procedure ParseVJoyStatus(")
    assert "(State = 'MISSING') or (State = 'UNKNOWN')" in status
    report = _routine(code, "procedure ParseVJoyReport(")
    for name in ("'device'", "'buttons'", "'continous povs'", "'continuous povs'",
                 "'axes'"):
        assert name in report


def test_existing_devices_change_only_when_edited_with_the_warning() -> None:
    from gremlin.ui import drivers_model

    assert _const("VJoyWarning") == drivers_model.VJOY_WARNING
    assert _const("VJoyWarning") == (
        "Running games will lose the vJoy devices until they restart."
    )
    code = _code()
    edited = _routine(code, "function VJoyEdited:")
    assert "if not VJoyUserEdited then\n    Exit;" in edited
    assert "Result := not SameLayout(VJoyCurrent, VJoyChosen);" in edited
    update = _routine(code, "procedure UpdateVJoyControls;")
    assert "if Active and VJoyEdited then" in update
    assert "VJoyWarningText.Caption := VJoyWarning;" in update
    memo = _routine(code, "function UpdateReadyMemo(")
    assert "Steps := Steps + Space + VJoyWarning + NewLine;" in memo
    assert "' will be deleted.'" in memo
    # Only the user's own changes count as edits (filling the lines is not one).
    change = _routine(code, "procedure VJoyMemoChange(")
    assert "if VJoyFilling or VJoyCustomMemo.ReadOnly then" in change


def test_vjoy_setup_comes_after_the_vjoy_install_job() -> None:
    code = _code()
    done = _routine(code, "procedure DriversPageDone;")
    tail = done[done.index("I := DriverIndex('vjoy');"):]
    assert "if Drivers[I].Op = 'install' then\n    VJoySetupPlanned := True" in tail
    assert (
        "else if Drivers[I].State <> 'missing' then\n"
        "    VJoySetupPlanned := VJoyEdited;"
    ) in tail
    write = _routine(code, "function WriteJobFile(")
    assert "for Pass := 0 to 1 do" in write
    assert write.index("Json := JobJson(I);") < write.index("Json := VJoySetupJobJson;")
    assert "Index := VJoySetupJob;" in write
    planned = _routine(code, "function DriverJobsPlanned:")
    assert "Result := VJoySetupPlanned;" in planned


def _vjoy_setup_json(devices: list[drivers.VJoyDevice]) -> str:
    routine = _routine(_code(), "function VJoySetupJobJson:")
    devices_parts = _assignments(routine, "Devices")
    assert len(devices_parts) == 3, devices_parts  # '', ', ', one device
    text = ""
    for k, device in enumerate(devices):
        env = {
            "Devices": text,
            "IntToStr(VJoyChosen[K].Id)": str(device.id),
            "IntToStr(VJoyChosen[K].Axes)": str(device.axes),
            "IntToStr(VJoyChosen[K].Buttons)": str(device.buttons),
            "IntToStr(VJoyChosen[K].Hats)": str(device.hats),
        }
        if k > 0:
            text = _eval(devices_parts[1], env)
            env["Devices"] = text
        text = _eval(devices_parts[2], env)
    (result,) = _assignments(routine, "Result")
    return _eval(result, {"Devices": text})


def test_the_vjoy_setup_job_is_one_the_helper_reads(tmp_path: pathlib.Path) -> None:
    app = r"C:\Users\A B\AppData\Local\Programs\Gremlin-Platforms"
    layout = [
        drivers.VJoyDevice(1),
        drivers.VJoyDevice(3, axes=0, buttons=0, hats=0),
        drivers.VJoyDevice(16, axes=2, buttons=12, hats=1),
    ]
    text = _job_file([
        _job_json("install", "vjoy", "",
                  app + r"\drivers\vJoySetup_v2.2.2.0_Win10_Win11.exe"),
        _vjoy_setup_json(layout),
    ])
    assert json.loads(text)["jobs"][1] == {
        "op": "vjoy_setup", "driver": "vjoy", "files": [],
        "devices": [
            {"id": 1, "axes": 8, "buttons": 128, "hats": 4},
            {"id": 3, "axes": 0, "buttons": 0, "hats": 0},
            {"id": 16, "axes": 2, "buttons": 12, "hats": 1},
        ],
    }
    path = tmp_path / "jobs.json"
    path.write_text(text, encoding="utf-8")
    jobs = drivers.read_jobs(path)
    assert [(j.op, j.driver) for j in jobs] == [
        ("install", "vjoy"), ("vjoy_setup", "vjoy")
    ]
    assert jobs[1].files == []
    assert [(d.id, d.axes, d.buttons, d.hats) for d in jobs[1].devices] == [
        (1, 8, 128, 4), (3, 0, 0, 0), (16, 2, 12, 1)
    ]


def test_the_vjoy_setup_job_has_its_progress_and_result_line() -> None:
    code = _code()
    progress = _routine(code, "function JobProgressText(")
    assert "if I = VJoySetupJob then" in progress
    assert "'Setting up the vJoy devices' + #$2026" in progress
    summary = _routine(code, "procedure BuildDriverSummary;")
    assert "DriverSummary := DriverSummary + VJoySetupResultLine;" in summary
    assert "if VJoySetupRestart then" in summary
    for name in ("ReadDriverResults", "FailOpenJobs"):
        body = _routine(code, ("function " if name == "ReadDriverResults" else
                               "procedure ") + name + "(")
        assert "SetJobResult(J," in body


def test_a_silent_install_never_reads_or_sets_up_vjoy() -> None:
    code = _code()
    planned = _routine(code, "function DriverJobsPlanned:")
    assert planned.index("if WizardSilent then") < planned.index(
        "Result := VJoySetupPlanned;"
    )
    init = _routine(code, "procedure InitVJoyChoice;")
    assert "VJoySetupPlanned := False;" in init
    assert init.index("if not WizardSilent then") < init.index("ReadVJoyLayout;")
    # Only DriversPageDone plans the job, and a silent install never calls it.
    assert re.findall(r"VJoySetupPlanned := True", code) == [
        "VJoySetupPlanned := True"
    ]
    assert "VJoySetupPlanned := True" in _routine(code, "procedure DriversPageDone;")


def test_no_code_line_starts_with_a_hash() -> None:
    # ISPP reads a line starting with '#' as a directive (#13#10 continuations).
    bad = [x for x in _code().splitlines() if x.lstrip().startswith("#")]
    assert bad == []


@pytest.mark.parametrize(
    "name",
    [
        "AddVJoyDevice", "CopyVJoyDevices", "PresetDevices", "SameLayout",
        "MatchingPreset", "VJoyEdited", "NextToken", "VJoyField", "AxesCount",
        "ParseVJoyReport", "ParseVJoyStatus", "RunVJoyConfig", "ReadVJoyLayout",
        "InitVJoyChoice", "VJoyLayoutText", "FillCustomMemo", "ReadCustomMemo",
        "UpdateVJoyControls", "VJoySetupJobJson", "JobState", "SetJobResult",
        "VJoySetupResultLine", "VJoyIdUsed", "ClampInt", "IsDigits",
    ],
)
def test_vjoy_routines_are_declared_before_use(name: str) -> None:
    code = _strip(_code())
    declared = re.search(rf"\b(?:function|procedure) {name}\b", code)
    assert declared, name
    first_use = re.search(rf"\b{name}\b", code)
    assert first_use and first_use.start() >= declared.start(), name


# -- 01 S193: the Microsoft Visual C++ Runtime ---------------------------------------


def _runtime_install() -> str:
    return _routine(_code(), "procedure InstallRuntime;")


def test_the_runtime_matches_drivers_py() -> None:
    info = drivers.RUNTIME
    assert info.key not in drivers.DRIVERS
    assert _define("RuntimeBundled") == info.bundled_version
    assert _define("RuntimeFile") == info.bundled_file
    assert _define("RuntimeSha256") == info.sha256
    assert _define("RuntimeSigner") == info.signer_prefix
    assert _const("RuntimeName") == info.name
    assert _const("RuntimeArgs") == " ".join(info.install_args)


def test_the_runtime_file_goes_to_tmp_only() -> None:
    files = _section("Files")
    lines = [x for x in files.splitlines() if "Runtime" in x and not x.startswith(";")]
    # dontcopy: never copied to {app}; extracted to {tmp} when it is missing.
    assert lines == ['Source: "drivers\\{#RuntimeFile}"; Flags: dontcopy']
    assert "skipifsourcedoesntexist" not in lines[0]
    assert "ExtractTemporaryFile('{#RuntimeFile}');" in _runtime_install()
    assert r"ExpandConstant('{tmp}\{#RuntimeFile}')" in _runtime_install()
    # The old [Files]/[Run] copy from dist\ is gone.
    assert r"dist\vc_redist" not in _iss().lower()
    assert r"{tmp}\vc_redist" not in _iss().lower()


def test_runtime_detection_reads_drivers_py_key_in_both_views() -> None:
    assert _const("RuntimeKey") == drivers.RUNTIME_KEYS[0]
    # The 32-bit view of RuntimeKey is drivers.py's WOW6432Node key.
    assert drivers.RUNTIME_KEYS[1] == drivers.RUNTIME_KEYS[0].replace(
        "SOFTWARE\\", "SOFTWARE\\WOW6432Node\\", 1
    )
    found = _routine(_code(), "function RuntimeInstalled:")
    assert found.index("HKLM64, RuntimeKey, 'Installed'") < found.index(
        "HKLM32, RuntimeKey, 'Installed'"
    )
    assert found.count("Result := Value = 1;") == 2


def test_the_drivers_page_shows_the_runtime_line_with_no_box() -> None:
    assert _const("RuntimeLine") == (
        "Microsoft Visual C++ Runtime: will be installed "
        "(Gremlin-Platforms needs it to run)"
    )
    fill = _routine(_code(), "procedure FillDriverList;")
    assert (
        "if RuntimeMissing then\n    DriverList.AddGroup(RuntimeLine, '', 0, nil);"
    ) in fill
    assert "AddCheckBox(RuntimeLine" not in _code()
    assert "RuntimeMissing := not RuntimeInstalled;" in _routine(
        _code(), "procedure InitDrivers;"
    )


def test_the_runtime_installs_first() -> None:
    code = _code()
    step = _routine(code, "procedure CurStepChanged(")
    # ssInstall comes before the files are copied, ssPostInstall's driver jobs
    # and every [Run] entry, so nothing can start the program before it.
    assert step.index("if CurStep = ssInstall then\n    InstallRuntime;") < step.index(
        "RunDriverJobs;"
    )
    run = [x for x in _section("Run").splitlines() if x and not x.startswith(";")]
    assert run
    assert all(x.startswith(r'Filename: "{app}\{#MyAppExeName}"') for x in run)
    assert code.index("procedure InstallRuntime;") < code.index(
        "procedure CurStepChanged("
    )


def test_the_runtime_runs_elevated_with_the_switches_and_bounded_wait() -> None:
    body = _runtime_install()
    assert "ShellExec('runas', ExpandConstant('{cmd}'), Params" in body
    assert "ewNoWait" in body and "ewWaitUntilTerminated" not in body
    params = body[body.index("Params := "): body.index(";", body.index("Params := "))]
    assert "RuntimeArgs" in params and "!errorlevel!" in params and "/v:on /c" in params
    assert _const("RuntimeArgs") == "/install /quiet /norestart"
    assert "for Tick := 1 to RuntimeWaitTicks do" in body
    assert "Sleep(RuntimeWaitStep);" in body
    ticks = int(_const_int("RuntimeWaitTicks"))
    assert ticks * int(_const_int("RuntimeWaitStep")) == 600_000
    assert "'not installed: it did not finish within 10 minutes'" in body
    # The bundled copy is checked before it runs (SHA-256 and signer).
    assert body.index("RuntimeFileTrusted(Path)") < body.index("ShellExec(")
    trusted = _routine(_code(), "function RuntimeFileTrusted(")
    assert "GetSHA256OfFile(Path)" in trusted and "'{#RuntimeSha256}'" in trusted
    assert "Get-AuthenticodeSignature" in trusted and "{#RuntimeSigner}" in trusted


def _const_int(name: str) -> str:
    found = re.search(rf"^  {name} = (\d+);$", _code(), re.M)
    assert found, name
    return found.group(1)


def test_runtime_exit_codes() -> None:
    assert int(_const_int("RuntimeDoneCode")) == drivers.RUNTIME_DONE_CODES[0]
    assert int(_const_int("RuntimeNewerCode")) == drivers.RUNTIME_DONE_CODES[1]
    assert int(_const_int("RuntimeRestartCode")) == drivers.RUNTIME_RESTART_CODE
    assert drivers.RUNTIME.restart_codes == (drivers.RUNTIME_RESTART_CODE,)
    codes = _routine(_code(), "function RuntimeCodeResult(")
    restart = codes[
        codes.index("Code = RuntimeRestartCode"):
        codes.index("  else\n    Result := 'not installed")
    ]
    assert "RuntimeNeedRestart := True;" in restart
    assert codes.count("RuntimeNeedRestart := True;") == 1
    assert "'not installed (error ' + IntToStr(Code)" in codes
    assert "Result := DriversNeedRestart or RuntimeNeedRestart;" in _routine(
        _code(), "function NeedRestart:"
    )
    page = _routine(_code(), "procedure CurPageChanged(")
    assert "RuntimeName + ': ' + RuntimeResult" in page
    assert "if DriversNeedRestart or RuntimeNeedRestart then" in page


def test_a_runtime_failure_never_stops_the_install() -> None:
    body = _runtime_install()
    assert body.index("try") < body.index("ExtractTemporaryFile(")
    assert "except" in body and "GetExceptionMessage" in body
    assert "'not installed: administrator permission was not given'" in body
    assert "Abort" not in body and "RaiseException" not in body
    assert "Runtime" not in _routine(_code(), "function PrepareToInstall(")


def test_a_silent_install_installs_the_runtime() -> None:
    body = _runtime_install()
    # Only "already installed" skips it; a silent install only skips the page.
    assert body.split("begin", 1)[1].lstrip().startswith(
        "if RuntimeInstalled then\n    Exit;"
    )
    assert "if WizardSilent then\n    Exit" not in body
    assert "InstallRuntime;" in _routine(_code(), "procedure CurStepChanged(")
    # Silent installs still run no driver jobs, and never restart on their own.
    planned = _routine(_code(), "function DriverJobsPlanned:")
    assert "if WizardSilent then\n    Exit;" in planned
    codes = _routine(_code(), "function RuntimeCodeResult(")
    assert "if not WizardSilent then\n      RuntimeNeedRestart := True;" in codes


def test_the_runtime_shows_its_progress_text() -> None:
    body = _runtime_install()
    assert "SetRuntimeText('Installing the ' + RuntimeName + #$2026);" in body
    assert _const("RuntimeName") + "…" == "Microsoft Visual C++ Runtime…"


def test_uninstall_never_touches_the_runtime() -> None:
    iss = _iss()
    assert "[UninstallRun]" not in iss
    assert "VisualStudio" not in _section("UninstallDelete")
    assert "Runtime" not in _section("UninstallDelete")
    for x in ("RegDeleteKey", "RegDeleteValue", "/uninstall"):
        assert x not in iss
