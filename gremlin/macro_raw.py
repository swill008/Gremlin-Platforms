# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A macro step the program can't read, kept as it was (05 S117).

A step of an unknown type, or one whose data can't be read, doesn't stop the
profile opening: it is held as its saved XML element, written back unchanged
on Save, does nothing at Run, and says why in `problem` (macro editor, rule
checks).
"""

from __future__ import annotations

import copy
from xml.etree import ElementTree

from gremlin.macro import AbstractAction


class RawMacroStep(AbstractAction):
    """A macro step kept as its saved element."""

    tag = "unreadable"

    def __init__(self, element: ElementTree.Element, problem: str = "") -> None:
        self._element = copy.deepcopy(element)
        self._element.tail = None
        self.problem = problem

    @property
    def step_type(self) -> str:
        """The type the saved step names ("" when it names none)."""
        return self._element.get("type") or ""

    @classmethod
    def create(cls) -> RawMacroStep:
        return RawMacroStep(ElementTree.Element("macro-action"))

    @staticmethod
    def unknown_type(element: ElementTree.Element) -> RawMacroStep:
        step_type = element.get("type") or ""
        return RawMacroStep(
            element,
            f"Unknown step type '{step_type}': kept as it was, does nothing.",
        )

    @staticmethod
    def unreadable(element: ElementTree.Element, err: Exception) -> RawMacroStep:
        step_type = element.get("type") or ""
        return RawMacroStep(
            element,
            f"This {step_type} step can't be read ({err}): kept as it was, "
            "does nothing.",
        )

    def __call__(self) -> None:
        pass

    def to_xml(self) -> ElementTree.Element:
        return copy.deepcopy(self._element)

    def from_xml(self, node: ElementTree.Element) -> None:
        self._element = copy.deepcopy(node)
        self._element.tail = None

    def is_valid(self) -> bool:
        return True
