# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import threading
import weakref
from typing import (
    Any,
    Generic,
    TypeVar,
)

from gremlin import error
from gremlin.keyboard import key_from_code
from gremlin.types import (
    AxisNames,
    InputType,
    ScanCode,
)

T = TypeVar("T")


class SingletonDecorator(Generic[T]):
    """Decorator turning a class into a singleton."""

    def __init__(self, klass: type[T]) -> None:
        self.klass = klass
        self.instance: T | None = None
        # Reentrant so a constructor touching this singleton on the same
        # thread doesn't deadlock.
        self._lock = threading.RLock()

    def __call__(self, *args: Any, **kwargs: dict) -> T:  # noqa: ANN401
        instance = self.instance
        if instance is not None:
            return instance
        with self._lock:
            if self.instance is None:
                self.instance = self.klass(*args, **kwargs)
            return self.instance


class SingletonMetaclass(type):
    # https://stackoverflow.com/a/6798042

    _instances: dict[type, Any] = {}
    # One lock per class so a slow constructor only blocks its own class.
    _locks: weakref.WeakKeyDictionary[type, threading.RLock] = (
        weakref.WeakKeyDictionary()
    )
    _locks_guard = threading.Lock()

    def __call__(cls, *args: Any, **kwargs: dict) -> Any:  # noqa: ANN401
        instance = cls._instances.get(cls)
        if instance is not None:
            return instance
        with SingletonMetaclass._locks_guard:
            lock = SingletonMetaclass._locks.setdefault(cls, threading.RLock())
        with lock:
            if cls not in cls._instances:
                cls._instances[cls] = super(SingletonMetaclass, cls).__call__(
                    *args, **kwargs
                )
            return cls._instances[cls]


def input_to_ui_string(input_type: InputType, input_id: int | ScanCode) -> str:
    """Returns a string for UI usage of an input.

    Args:
        input_type: Type of the input
        input_id: Identifier of the input, usually a numerical index but for
            keyboard keys it is the key's scan code

    Returns:
        String for UI usage of the given data.
    """
    if input_type == InputType.JoystickAxis:
        try:
            return AxisNames.to_string(AxisNames(input_id))
        except error.GremlinError:
            return f"Axis {input_id:d}"
    elif input_type == InputType.Keyboard:
        assert isinstance(input_id, tuple) and len(input_id) == 2
        return key_from_code(*input_id).name
    else:
        return f"{InputType.to_string(input_type).capitalize()} {input_id}"
