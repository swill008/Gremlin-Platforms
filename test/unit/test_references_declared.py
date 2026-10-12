# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Guard: every action, macro step and condition declares what it uses with
its own references() (gremlin.references), so Search and the walkers built on
gremlin.usages find a new piece without anyone adding it to a list. A new
class without references() fails here."""

from __future__ import annotations

import importlib
import pathlib
import pkgutil
from collections.abc import Iterable

import pytest

from gremlin import references as refs
from gremlin.base_classes import AbstractActionData
from gremlin.types import InputType

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SHAPES = {"vjoy", "xbox", "input", "mode", "action", "osc-out", "mouse", "profile"}


def _import_everything() -> None:
    """Every plugin module, the macro steps and the unknown action."""
    import action_plugins

    for info in pkgutil.walk_packages(
        action_plugins.__path__, prefix="action_plugins."
    ):
        importlib.import_module(info.name)
    importlib.import_module("gremlin.macro")
    importlib.import_module("gremlin.unknown_action")


def _subclasses(base: type) -> list[type]:
    found: list[type] = []
    pending = list(base.__subclasses__())
    while pending:
        cls = pending.pop(0)
        if cls in found:
            continue
        found.append(cls)
        pending.extend(cls.__subclasses__())
    # Only the program's own classes, not test doubles made elsewhere.
    return sorted(
        (
            cls
            for cls in found
            if cls.__module__.startswith(("action_plugins.", "gremlin."))
        ),
        key=lambda cls: f"{cls.__module__}.{cls.__qualname__}",
    )


def _bases() -> dict[str, type]:
    _import_everything()
    from action_plugins.condition.condition import AbstractCondition
    from gremlin.macro import AbstractAction

    return {
        "action": AbstractActionData,
        "step": AbstractAction,
        "condition": AbstractCondition,
    }


def _abstract_beyond_references(cls: type) -> bool:
    """A base meant to be subclassed (abstract for more than references);
    one missing only references() is still checked."""
    return bool(set(getattr(cls, "__abstractmethods__", ())) - {"references"})


_BASES = _bases()
_CASES = [
    pytest.param(family, cls, id=f"{family}-{cls.__qualname__}")
    for family, base in _BASES.items()
    for cls in _subclasses(base)
    if not _abstract_beyond_references(cls)
]


def test_the_bases_require_references() -> None:
    for base in _BASES.values():
        assert "references" in vars(base), base.__qualname__
    assert "references" in AbstractActionData.__abstractmethods__


def test_every_family_has_classes() -> None:
    assert {family for family, *_ in (case.values for case in _CASES)} == set(
        _BASES
    )


@pytest.mark.parametrize("family, cls", _CASES)
def test_declares_its_own_references(family: str, cls: type) -> None:
    owner = next(k for k in cls.__mro__ if "references" in vars(k))
    assert owner is not _BASES[family], (
        f"{cls.__module__}.{cls.__qualname__} doesn't say what it uses: add "
        "references() (return () with a comment when it points at nothing)"
    )


def _made(family: str, cls: type) -> object:
    if family == "action":
        types = getattr(cls, "input_types", ()) or (InputType.JoystickButton,)
        return cls(types[0])
    if family == "step" and hasattr(cls, "create"):
        return cls.create()
    return cls()


def _check(declared: Iterable[refs.Reference]) -> None:
    for ref in declared:
        assert isinstance(ref, refs.Reference)
        assert ref.role in refs.ROLES
        assert ref.target and ref.target[0] in _SHAPES
        assert isinstance(ref.where, tuple)


@pytest.fixture
def profile(monkeypatch: pytest.MonkeyPatch) -> None:
    from gremlin import shared_state
    from gremlin.profile import Profile

    monkeypatch.setattr(shared_state, "current_profile", Profile())


@pytest.mark.usefixtures("profile")
@pytest.mark.parametrize("family, cls", _CASES)
def test_a_new_piece_answers_references(family: str, cls: type) -> None:
    """A freshly made piece answers with Reference objects of known shapes."""
    try:
        piece = _made(family, cls)
    except TypeError:
        pytest.skip(f"{cls.__qualname__} needs arguments to be made")
    _check(piece.references())  # type: ignore[attr-defined]
