# AGENTS.md - JoystickGremlin Developer Guide

**Grok / project agents: read [`grok_rules.md`](grok_rules.md) first.** That file is the standing product contract (button-map editor, handoffs, pictures, parked work). This file is code style and architecture only.


This file provides guidance for AI agents working on the JoystickGremlin codebase.




## Mandatory: change control (user, 2026-10-06)

The program's intended behaviour is the approved spec in `claude/program-map/`
(section 8 statements plus the section 12 decisions on each page; the
decision wins where they disagree). The plan and working rules are in
`claude/system-maps.md`.

- Read the spec page(s) before changing behaviour.
- A change that would add, change, remove or contradict a spec statement or
  decision goes to the user first; the spec is updated with their answer
  before any code.
- Code that differs from the spec is a gap to fix (failing test first), not a
  spec change.
- Every commit touching `gremlin/`, `qml/`, `action_plugins/`, `dill/`,
  `vigem/` or `joystick_gremlin.py` carries `Spec: <page> <S/Q refs>` or
  `Spec: none (no behaviour change)`; `test/unit/test_spec_line.py` checks it.

## Mandatory: test before you push

This sandbox cannot launch the Qt app. That is not a reason to skip tests.
Before every Contents PUT on this repo:

1. `ast.parse` every Python file you changed (must succeed).
2. Brace-count every QML file you changed (`{` == `}`).
3. `@ta.QmlElement` / `@QmlElement` must decorate a **class**, never a `def`.
4. If the change is logic, add or extend a test under `test/unit/` and run it
   (`poetry run pytest test/unit/<file>.py`). Duplicate a tiny helper in the
   test if importing the module pulls Qt/DILL you cannot load here.
5. When the environment has PySide6: `poetry run python -c "import <module>"`
   for every Python module you touched. The crash `qmlRegisterType(function, ...)`
   means a decorator landed on a helper — fix before PUT.
6. Do not PUT until those checks pass. Report what you ran.

The user still has to pull and click the GUI. Your job is to catch import
breaks, decorator mistakes, and logic regressions before they do.

## Project Overview

JoystickGremlin is a Python application (PySide6/QML) for configuring joystick devices on Windows. It uses vJoy for virtual joystick emulation and supports macros, modes, and Python scripting.


## Build, Lint, and Test Commands

The project is using poetry for dependency management. Thus all calls to python HAVE TO USE poetry.

### Running Tests

Run the tests with `test/run_tests.py`. It runs `test/action_interaction`,
`test/integration` and `test/unit` (split into 6 parts, balanced by the last
run's times; a heavy file is split test by test) **at the same time**, so a
full run takes under a minute instead of 4.5. Chosen unit files and
`--failed` tests are spread over the parts the same way. The three folders can't share one pytest process (mixed runs
are refused), so a plain `poetry run pytest` with no folder does not work.

```powershell
# Every test, in parallel (before every commit; let it run to the end)
poetry run python test/run_tests.py

# Only what failed in the last run (seconds)
poetry run python test/run_tests.py --failed

# Only the tests that touch what changed since the last commit (while
# working; it prints which tests and why)
poetry run python test/run_tests.py --changed

# Only these files or folders, stopping at the first failure (while working)
poetry run python test/run_tests.py --quick test/unit/test_profile.py
```

Every line shows the time, the part and how many tests are done; a quiet test
is named after 15 s; a part is stopped after 10 min; the end lists each
part's result and the 10 slowest tests. Watch it live from another window:

```powershell
Get-Content "$env:TEMP\gremlin-test-run.log" -Wait -Tail 20
```

Rhythm: while changing code, `--changed` (or the affected files with
`--quick`); after a fix, `--failed`; before every commit, one full run, to
the end. `--changed` follows imports two steps out, QML and JavaScript files
through the QML that uses them, and the helper scripts tests run
(`test/changed_tests.py` says how); what it misses, the full run catches.

One test run at a time on this PC: a run that finds another going (another
checkout or session) waits for it and says so, since two at once slow each
other down several times over and fail timing tests. Each checkout keeps its
own `--failed` list.

Each file's time is kept for balancing the parts; a run of only some of a
file's tests (`--failed`, `file::test`) doesn't change it. Unit tests get the
program's settings object back after each test (`test/unit/conftest.py`), so
a test may make a fresh `Configuration` without breaking later ones.

Plain pytest still works for one folder or file:

```powershell
# Run a single test file
poetry run pytest test/unit/test_profile.py

# Run a specific test
poetry run pytest test/unit/test_profile.py::test_simple_action

# Run tests with verbose output
poetry run pytest -v

# Run tests matching a pattern
poetry run pytest -k "test_simple"

# Run e2e tests only
poetry run pytest test/integration/

# Run action interaction tests only
poetry run pytest test/action_interaction/

# Run unit tests only
poetry run pytest test/unit/
```

### Linting

```powershell
# Run ruff linter (ANN = annotations required)
poetry run ruff check .
```

### Type Checking

```powershell
# Run pyright type checker
poetry run pyright
```

### Running the Application

```powershell
# Run in dev mode
poetry run python joystick_gremlin.py
```


## Architecture

### Code Structure

- Keep related functionality together
- Follow the existing module organization:
  - `gremlin/` - Core application logic
  - `gremlin/ui/` - UI-related code (PySide6/QML integration)
  - `action_plugins/` - Action plugins, one directory per action
  - `test/` - Test suites
  - `qml/` - QML UI files
  - `vjoy/` — vJoy virtual joystick ctypes wrapper
  - `dill/` — native device input library (DILL.dll) with Python wrapper
- `joystick_gremlin.py` — entry point; initializes devices, Qt engine, plugins

### Key Singletons

| Class | Module | Purpose |
|---|---|---|
| `Configuration` | `gremlin.config` | Persistent app config |
| `EventListener` | `gremlin.event_handler` | Raw input capture & routing |
| `ModeManager` | `gremlin.mode_manager` | Mode stack & switching when Gremlin is active |
| `Backend` | `gremlin.ui.backend` | Main QML↔Python bridge |

Use `metaclass=common.SingletonMetaclass` (not the legacy `@common.SingletonDecorator`).

### Profile Storage

Profiles are XML files. `gremlin.profile.Profile` owns load/save and dispatches this via various `to_xml` and `from_xml` call chains.

### Python/QML Bridge

- `Backend` (registered as `backend` context property) exposes signals and slots to QML
- QML-accessible classes use `@QtQml.QmlElement` or `engine.rootContext().setContextProperty()`
- Qt signals/slots use `@QtCore.Signal` / `@QtCore.Slot` decorators
- Never call Qt GUI APIs from non-main threads


## Code Style Guidelines

### File Headers

Every Python file must include:
```python
# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only
```

### Imports

- Use `from __future__ import annotations` for forward references
- Sort imports: stdlib, third-party, local (alphabetically within groups)
- Use absolute imports within the package (e.g., `from gremlin.types import InputType`)
- Use `TYPE_CHECKING` guard for imports only needed for type hints to avoid circular imports

Example:
```python
from __future__ import annotations

import logging
from typing import (
    cast,
    Any,
    TYPE_CHECKING
)

from PySide6 import (
    QtCore,
    QtQml
)

import gremlin.profile
from gremlin.types import InputType
from gremlin.error import GremlinError

if TYPE_CHECKING:
    from gremlin.base_classes import AbstractActionData
```

### Type Annotations

- **Required**: All function signatures must have type annotations (enforced by ruff ANN rule)
- Use Python 3.13+ syntax: `list[str]`, `dict[str, int]` (no need for `List`, `Dict` from typing)
- Acceptable exceptions:
  - `PySide6` import errors (project-wide Pylance issue)
  - `AbstractActionData` attribute unknowns (project-wide)
- Use `X | None` over `Optional[X]`

### Naming Conventions

- **Classes**: `PascalCase` (e.g., `JoystickGremlinApp`, `Profile`)
- **Functions/methods**: `snake_case` (e.g., `get_vjoy_device`, `from_xml`)
- **Constants**: `SCREAMING_SNAKE_CASE` (e.g., `MAX_CACHE_SIZE`)
- **Private members**: `_leading_underscore` (e.g., `_cache`)
- **Qt properties/slots**: Follow Qt conventions (e.g., `imageReady`, `requestImage`)
- **QML variables**: Follow Qt convention (e.g. `someVariable`)
- **QML element identifiers**: Always start with `_` (e.g. `_label`, `_actionModel`)

### Qt Patterns

- Use `@QtCore.Signal` and `@QtCore.Slot` decorators for Qt signals/slots
- Signals are defined as class attributes: `imageReady = QtCore.Signal(str, str)`
- Subclass `QtCore.QObject` for QML-accessible classes if no more specialized class is applicable
- Use `@QtQml.QmlElement` decorator for classes to register with QML
- Register QML context properties with `engine.rootContext().setContextProperty()` to be used in exceptional circumstances only

```python
from PySide6 import QtCore

if TYPE_CHECKING:
    import gremlin.ui.type_aliases as ta

class DataProvider(QtCore.QObject):
    dataReady = QtCore.Signal(str)

    def __init__(self, parent: ta.OQO=None):
        self._value = ""

    def _get_value(self) -> str:
        return self._value

    def _set_value(self, val: str) -> None:
        self._value = val
        self.dataReady.emit(val)

    value = QtCore.Property(
        str,
        fget=_get_value,
        fset=_set_value,
        notify=dataReady
    )
```

### Error Handling

- Custom exceptions are defined in `gremlin.error` and inherit from `GremlinError`
- Use specific exception types (e.g., `ProfileError`, `VJoyError`, `MissingImplementationError`)
- Provide meaningful error messages
- Exceptions are caught on the highest level and logged there

Example:
```python
from gremlin.error import GremlinError

try:
    value = int(text)
except ValueError:
    raise GremlinError(f"Invalid device index: {index}")
```

### Logging

- Use `logging.getLogger("system")` for logging

### Qt Threading Rules

- **Never use Qt GUI classes from non-main threads** (Qt is not thread-safe)
- Background threads are acceptable for non-GUI work (device polling, file monitoring), started as below

### Threads, Waits and Timing (keep the program hang-proof)

- **Start every thread through `gremlin.threads`**: `threads.start(name, target, *args, stop=<request>)`
  and `threads.timer(name, seconds, fn)`, never `threading.Thread(...)` / `threading.Timer(...)`
  directly. The stop request only asks (set a flag, set an Event, cancel) and returns at once.
  `threads.shutdown()` stops them all on exit (`main()`) and at the end of a test run;
  `threads.running()` lists the ones still alive.
- Set a "running" flag **before** starting its thread, never inside the thread (an early
  `stop()` gets undone otherwise).
- No unbounded `join()`, `Event.wait()`, `Condition.wait_for()` or lock acquire on a path that
  can block: use a timeout, re-check the stop flag, and log once (`gremlin.log_once`) if it runs out.
- The main thread never waits on a worker that may not end.
- Timed loops read the time through `gremlin.clock.now()` / `clock.sleep()`, so tests can step it.
- Errors inside threads are logged with the thread's name (`gremlin/error_report.py`); a hard
  crash in native code writes every thread's stack to `crash.log` in the logs folder.
- **Log When Not Responding** (Options › Diagnostics, off by default, `gremlin/watchdog.py`):
  after 5 s without a main-loop tick it writes every thread's stack to system.log, once per freeze.
- Keys go out through `win32api.keybd_event`, mouse input through `sendinput._send_input`, and
  the keyboard/mouse hooks honour `windows_event_hook.enabled` (tests fake or turn off all three).

### Singleton Pattern

The project uses two singleton patterns:
- Only the newer `metaclass=common.SingletonMetaclass` should be used
- `@common.SingletonDecorator` is legacy and is not to be used anymore

### QML Integration

- Use `Connections` for QML-to-Python signal connections when data binding cannot be used
- Use `onSignalName` for Python-to-QML property changes
- QML model classes often inherit from `QtCore.QAbstractListModel` and implement `rowCount()`, `data()`, `roleNames()`

### Action Plugins

Each plugin under `action_plugins/<name>/` defines:
- `AbstractActionData` subclass — XML serialization, validity, metadata (`tag`, `name`, `icon`, `version`, `input_types`, `functor`)
- `AbstractFunctor` subclass — actual runtime behavior
- `ActionModel` — QML UI model, enabling modifying the data via the UI

Required overrides on `AbstractActionData`: `_from_xml()`, `_to_xml()`, `is_valid()`, `_valid_selectors()`, `_get_container()`, `_handle_behavior_change()`.


Example:
```python
from gremlin.base_classes import AbstractActionData, AbstractFunctor
from typing import override

class SpecialActionData(AbstractActionData):

    tag = "special-action"
    name = "Special Action"
    icon = "f123"
    version = 1
    functor = SpecialActionFunctor

    # Implement functions mandated by the base class.
```

### Testing Conventions

- Tests go in `test/unit/`, `test/integration`, or `test/action_interaction/` depending on use  case
  - Self-contained unit tests are placed in `test/unit`
  - Simulated action interaction tests are placed in `test/action_interaction`
  - Full end to end system tests are placed in `test/integration`
- Function tests for action plugins are placed in `test/action_interaction`
- Tests in `test/action_interaction` have access to a `jgbot` fixture (`test/action_interaction/conftest.py:JoystickGremlinBot) which is similar to the Qt pytest fixture
- Use pytest fixtures from `test/conftest.py` and `test/unit/conftest.py`
- Use `pytest.raises()` for exception testing
- The test run guards itself (test tool only, under `test/`; the program does not use it):
  - A test whose main thread makes no progress for 10 s (30 s if its event loop idles) fails
    with the stuck line and every thread's stack, and the run goes on; one stuck inside C code
    ends the run with that report (`test/hang_trace/stall_watch.py`, `test/conftest.py`).
  - A test may not leave threads running. The unit package owns the shared event listener
    (started before the first test, stopped after the last).
  - Tests never hook, or send keys or mouse input to, the PC they run on: `test/conftest.py` turns
    `windows_event_hook.enabled` off and installs `test/fake_input.py`.
  - A program a test starts is watched the same way (`test/hang_trace/sitecustomize.py`) and ends
    at once when its main code ends. Such a program ends with `os._exit` (the program's own
    threads would keep it alive otherwise) and never shows a window on the user's screen
    (`QT_QPA_PLATFORM=offscreen`).
  - `test/` has no `__init__.py`: outside pytest's own import, `test` is Python's standard-library
    package, so load test helpers by file path in programs a test starts.
- UI at a large scale is checked off-screen in a program of its own (see
  `test/unit/test_main_window_fits.py`, `test_tool_windows_fit.py`, `test_pages_fit.py`):
  `gremlin.ui.ui_scale_option.active_scale = lambda: 175`; the screen size from
  `QT_QPA_PLATFORM=offscreen:configfile=<json>`, whose path must not contain a drive colon
  (the colon separates platform options; the process silently exits 127); `QT_QPA_FONTDIR` set to the
  Windows fonts folder, or no text is drawn. Size windows with `Style.fitWidth(w, Screen)` /
  `Style.fitHeight(h, Screen)` so they fit the screen at any scale.

Example:
```python
from test.unit.conftest import get_fake_device_guid

def test_something(xml_dir: pathlib.Path):
    p = Profile()
    p.from_xml(str(xml_dir / "profile_simple.xml"))
    assert len(p.inputs) == 1
```

### Type Aliases

Use type aliases from `gremlin.ui.type_aliases` for Qt-specific types:
```python
import gremlin.ui.type_aliases as ta
```

### Documentation

- Use docstrings for classes and complex functions
- Keep docstrings concise; describe purpose and parameters
- Do not add unnecessary inline comments

### Common Patterns

- Use `dataclasses` for simple data containers
- Use `ElementTree` for XML parsing/creation
- Use `pathlib.Path` for file paths

### Known Issues (Ignore)

- Pylance may show `Import "PySide6" could not be resolved` - this is a project-wide issue, not caused by your changes
- Some `AbstractActionData` attribute unknowns may appear - also project-wide

### Pre-commit Checks

Before considering a task complete, run what you can. **Do not skip the
Mandatory test-before-push list above.** When poetry is available:

```powershell
poetry run python -c "import gremlin.ui.live_input"
poetry run pytest test/unit/ -q
poetry run ruff check .
```

Do not block a small fix on a full pyright run if ruff/pytest/import already
passed. Never push unparsed Python or QML with unmatched braces.
