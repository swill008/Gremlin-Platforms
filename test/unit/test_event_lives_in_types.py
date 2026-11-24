"""D-04-EVENT-TYPES: Event and NO_MODE live in gremlin.types, with no old name.

event_handler reaches them as ``types.Event`` / ``types.NO_MODE``, so neither
name exists on that module, and no code may reach them through it.
"""

import pathlib
import re
import uuid

from gremlin import event_handler, types

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_DIRS = ("gremlin", "action_plugins", "test", "user_scripts")
_OLD = re.compile(
    r"event_handler\.(Event|NO_MODE)\b"
    r"|from\s+gremlin\.event_handler\s+import\s+[^\n]*\b(Event|NO_MODE)\b"
)


def test_types_event_has_our_extra_fields() -> None:
    event = types.Event(types.InputType.JoystickButton, 1, uuid.UUID(int=0), "")
    for name in ("synthetic", "osc_address", "ld_chain", "t_rx"):
        assert hasattr(event, name), name
    assert event.synthetic is False
    assert event.osc_address is None
    assert event.ld_chain == ()
    assert event.t_rx is None


def test_no_mode_lives_in_types() -> None:
    assert types.NO_MODE == ""


def test_event_handler_has_no_class_of_its_own() -> None:
    source = (_ROOT / "gremlin" / "event_handler.py").read_text(encoding="utf-8")
    assert not re.search(r"^class Event\b", source, re.M)
    assert not re.search(r"^NO_MODE\s*=", source, re.M)
    assert not hasattr(event_handler, "Event")
    assert not hasattr(event_handler, "NO_MODE")


def test_display_name_is_a_function_in_event_handler() -> None:
    assert callable(event_handler.event_display_name)
    assert not hasattr(types.Event, "display_name")


def test_no_code_uses_the_old_name() -> None:
    hits = []
    this = pathlib.Path(__file__).resolve()
    for folder in _DIRS:
        for path in (_ROOT / folder).rglob("*.py"):
            if path.resolve() == this:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for n, line in enumerate(text.splitlines(), 1):
                if _OLD.search(line):
                    hits.append(f"{path.relative_to(_ROOT)}:{n}: {line.strip()}")
    assert hits == []
