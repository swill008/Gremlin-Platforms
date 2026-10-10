# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Records the results of Reset Devices (D-02-RESET-DEVICES): one system.log
line per device, a HIDHIDE trace line per device when the Trace tab's HidHide
row is ticked, and a fresh expected.json for a running Input Tester. Never
touches a device and never counts as a HidHide change."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

from gremlin import input_tester_link, trace

syslog = logging.getLogger("system")

OK = "ok"

_TEXTS = {
    "restart": "needs a Windows restart, or unplug it and plug it back in",
    "not_found": "not found",
    "declined": "permission declined",
}


def outcome_text(result: Any) -> str:  # noqa: ANN401
    """The result as the window shows it, e.g. "reset ✓ · back after 2.4 s"
    (ResetResult.text when it has one)."""
    text = getattr(result, "text", None)
    if isinstance(text, str) and text:
        return text
    outcome = str(getattr(result, "outcome", "") or "")
    if outcome == OK:
        back = getattr(result, "back_after", None)
        if back is None:
            return "reset ✓ · not back after 10 s"
        return f"reset ✓ · back after {float(back):.1f} s"
    if outcome in _TEXTS:
        return _TEXTS[outcome]
    if outcome == "failed" or not outcome:
        return f"failed: {getattr(result, 'code', None)}"
    return outcome


def _names(devices: Iterable[Any] | None) -> dict[str, str]:
    names: dict[str, str] = {}
    for dev in devices or ():
        usb_id = getattr(dev, "usb_id", None)
        name = getattr(dev, "name", None) or getattr(dev, "windows_name", None)
        if usb_id and name:
            names[str(usb_id)] = str(name)
    return names


def report(results: Iterable[Any], devices: Iterable[Any] | None = None) -> None:
    """Logs, traces and tells the tester about a finished reset. `devices`
    (the window's ResetDevice rows) only supplies names."""
    results = list(results or ())
    names = _names(devices)
    tracing = trace.enabled() and trace.hidhide_ticked()
    for result in results:
        usb_id = str(getattr(result, "usb_id", ""))
        name = getattr(result, "name", None) or names.get(usb_id) or usb_id
        text = f"Reset Devices: {name} ({usb_id}) → {outcome_text(result)}"
        syslog.info(text)
        if tracing:
            ok = str(getattr(result, "outcome", "")) == OK
            trace.hidhide(text, warning=not ok)
    if not results:
        return
    try:
        if input_tester_link.running() or input_tester_link.expected_file().exists():
            input_tester_link.write_expected()
    except Exception:
        syslog.warning("Reset Devices: expected.json not updated", exc_info=True)
