# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import contextlib
import logging
import threading
from collections.abc import Iterator

_quiet = threading.local()


@contextlib.contextmanager
def quiet() -> Iterator[None]:
    """GremlinErrors made on this thread inside the block aren't logged:
    for callers that catch them and say why themselves (D-09-OSC-TRACE)."""
    depth = getattr(_quiet, "depth", 0)
    _quiet.depth = depth + 1
    try:
        yield
    finally:
        _quiet.depth = depth


class GremlinError(Exception):
    """Generic exception raised for gremlin related errors.

    This class also functions as the base class for all other
    exceptions.
    """

    def __init__(self, value: str) -> None:
        if not getattr(_quiet, "depth", 0):
            logging.getLogger("system").exception(value)
        self.value = value

    def __str__(self) -> str:
        return repr(self.value)


class ProfileError(GremlinError):
    """Exception raised when an error occurs with a profile related
    operation.
    """

    def __init__(self, value: str) -> None:
        super().__init__(value)


class KeyboardError(GremlinError):
    """Exception raised when an error occurs related to keyboard inputs."""

    def __init__(self, value: str) -> None:
        super().__init__(value)


class MouseError(GremlinError):
    """Exception raised when an error occurs related to mouse inputs."""

    def __init__(self, value: str) -> None:
        super().__init__(value)


class MissingImplementationError(GremlinError):
    """Exception raised when a method is not implemented."""

    def __init__(self, value: str) -> None:
        super().__init__(value)


class VJoyError(GremlinError):
    """Exception raised when an error occurs within the vJoy module."""

    def __init__(self, value: str) -> None:
        super().__init__(value)


class VJoyBusyError(VJoyError):
    """Exception raised when another program holds the vJoy device.

    Expected while that program runs and retried every few seconds, so it is
    not logged here: the output module logs it once and tells the user.
    """

    def __init__(self, value: str) -> None:
        Exception.__init__(self, value)
        self.value = value


class VJoyConcurrencyError(VJoyError):
    """Exception raised when vJoy is accessed from multiple threads."""

    def __init__(self, value: str) -> None:
        super().__init__(value)


class PluginError(GremlinError):
    """Exception raised when an error occurs withing a user plugin."""

    def __init__(self, value: str) -> None:
        super().__init__(value)
