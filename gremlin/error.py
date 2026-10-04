# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import logging


class GremlinError(Exception):
    """Generic exception raised for gremlin related errors.

    This class also functions as the base class for all other
    exceptions.
    """

    def __init__(self, value: str) -> None:
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
