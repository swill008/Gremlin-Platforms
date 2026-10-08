# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""01 S133 (D-01-UPDATE-NOTES, D-01-UPDATE-WHATSNEW, D-01-UPDATE-NOTES-CACHE):
the Update window's
release notes: only each release's What's new, with small headings.

Nothing goes out: a stand-in network hands the model GitHub's replies.
"""

from __future__ import annotations

import sys

sys.path.append(".")

import json
import pathlib
import re
from unittest import mock

import pytest
from PySide6 import (
    QtCore,
    QtNetwork,
)

from gremlin import updater
from gremlin.config import Configuration
from gremlin.ui import update_model

_app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])

_NoError = QtNetwork.QNetworkReply.NetworkError.NoError
_Timeout = QtNetwork.QNetworkReply.NetworkError.OperationCanceledError
_HostNotFound = QtNetwork.QNetworkReply.NetworkError.HostNotFoundError


class _Reply(QtCore.QObject):
    """A network reply the test finishes when it chooses."""

    finished = QtCore.Signal()

    def __init__(self) -> None:
        super().__init__()
        self._data = b""
        self._error = _NoError

    def finish(self, doc: object = None, error=_NoError) -> None:  # noqa: ANN001
        self._data = json.dumps(doc).encode("utf-8") if doc is not None else b""
        self._error = error
        self.finished.emit()

    def error(self) -> QtNetwork.QNetworkReply.NetworkError:
        return self._error

    def errorString(self) -> str:  # noqa: N802
        return "Host not found" if self._error != _NoError else ""

    def readAll(self) -> QtCore.QByteArray:  # noqa: N802
        return QtCore.QByteArray(self._data)

    def deleteLater(self) -> None:  # noqa: N802
        pass  # the test keeps it

    aborted = False

    def abort(self) -> None:
        self.aborted = True


class _Network:
    def __init__(self) -> None:
        self.requests: list[QtNetwork.QNetworkRequest] = []
        self.replies: list[_Reply] = []

    def get(self, request: QtNetwork.QNetworkRequest) -> _Reply:
        self.requests.append(QtNetwork.QNetworkRequest(request))
        reply = _Reply()
        self.replies.append(reply)
        return reply

    def urls(self) -> list[str]:
        return [r.url().toString() for r in self.requests]


def _doc(version: str, body: str | None = "", **extra: object) -> dict:
    doc = {
        "tag_name": f"Gremlin-Platforms-R1-{version}",
        "html_url": f"https://github.com/x/y/releases/tag/{version}",
        "assets": [],
        "body": body,
    }
    doc.update(extra)
    return doc


@pytest.fixture
def model(monkeypatch: pytest.MonkeyPatch):  # noqa: ANN201
    monkeypatch.delenv("GREMLIN_OFFLINE", raising=False)
    monkeypatch.setattr(update_model.util, "get_code_version", lambda: "1.0.0")
    cfg = Configuration()
    cfg.set("global", "internal", "update-feed-url", "")
    cfg.set("global", "internal", "skipped-update-version", "")
    m = update_model.UpdateModel()
    m._network = _Network()  # type: ignore[assignment]
    offers: list[int] = []
    m.offerUpdate.connect(lambda: offers.append(1))
    m.offers = offers  # type: ignore[attr-defined]
    return m


def _check(m, latest: dict, manual: bool = True) -> None:  # noqa: ANN001
    m.check(manual)
    m._network.replies[0].finish(latest)


_ROOT = pathlib.Path(__file__).resolve().parents[2]
# A release text as the release workflow builds it: install steps first,
# then the version's release-notes file (D-REL-NOTES-FILES).
_INSTALL = (
    "## How to install\n\n"
    "Installer: run `Gremlin-Platforms-R1-{v}-Setup.exe`.\n\n"
    "Portable: unzip anywhere.\n\n"
)


def _release_text(version: str) -> str:
    notes = (_ROOT / "release-notes" / f"{version}.md").read_text(encoding="utf-8")
    return _INSTALL.format(v=version) + notes + "\n## Checksums\n\nsha256 abc\n"


def _new(version: str, *points: str) -> str:
    return f"## What's new in {version}\n\n" + "".join(f"- {p}\n" for p in points)


def _plain(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html)


def test_one_newer_release_shows_only_its_whats_new(model) -> None:  # noqa: ANN001
    body = _release_text("1.0.27")
    _check(model, _doc("1.0.27", body))
    # The window waits for the list (D-01-UPDATE-NOTES-CACHE).
    assert model.state == "checking" and model.releaseNotes == ""
    model._network.replies[1].finish([_doc("1.0.27", body)])
    assert model.state == "available"
    html = model.releaseNotes
    text = _plain(html)
    assert "Search layers" in text and "Esc clears" in text
    for gone in ("Installer", "How to install", "Portable", "Checksums",
                 "What's new", "#"):
        assert gone not in text, gone
    # Small headings: New / Fixed are bold lines, never HTML headings.
    assert not re.search(r"<h[1-6]", html)
    assert '<p class="kind"><b>New</b></p>' in html
    assert '<p class="kind"><b>Fixed</b></p>' in html
    assert "<b>Search layers</b>" in html
    # One version: no version line.
    assert 'class="ver"' not in html and "1.0.27" not in text
    # Sub-points sit in a list inside the bullet.
    assert html.count("<ul") >= 3


def test_skipped_versions_show_newest_first_in_one_request(model) -> None:  # noqa: ANN001
    _check(model, _doc("1.0.3", _new("1.0.3", "Three")))
    assert model._network.urls()[1] == updater.RELEASES_LIST_URL
    model._network.replies[1].finish([
        _doc("1.1.0", _new("1.1.0", "Beta"), prerelease=True),
        _doc("1.0.9", _new("1.0.9", "Draft"), draft=True),
        _doc("1.0.3", _new("1.0.3", "Three")),
        _doc("1.0.1", _new("1.0.1", "One")),
        _doc("1.0.2", _new("1.0.2", "Two")),
        _doc("1.0.0", _new("1.0.0", "Running")),
        _doc("0.9.0", _new("0.9.0", "Old")),
    ])
    html = model.releaseNotes
    assert re.findall(r'<p class="ver">([^<]*)</p>', html) == [
        "What's new in 1.0.3", "What's new in 1.0.2", "What's new in 1.0.1",
    ]  # D-01-UPDATE-VERSION-LINE
    assert html.count("<hr") == 2  # a thin line between versions
    for gone in ("Beta", "Draft", "Running", "Old"):
        assert gone not in html
    assert len(model._network.requests) == 2  # the check and one list


def test_an_old_release_without_whats_new_says_unavailable(model) -> None:  # noqa: ANN001
    old = "Download the installer below and run it.\n\nPortable zip too."
    _check(model, _doc("1.0.25", old))
    model._network.replies[1].finish([_doc("1.0.25", old)])
    assert model.releaseNotes == ""  # the window says "Release notes unavailable."
    # Next to a version that has one: its own line says so.
    model._state = "upToDate"
    model.check(True)
    model._network.replies[2].finish(_doc("1.0.26", _release_text("1.0.26")))
    model._network.replies[3].finish(
        [_doc("1.0.26", _release_text("1.0.26")), _doc("1.0.25", old)]
    )
    html = model.releaseNotes
    assert "Download the installer" not in html
    assert html.index("<p class=\"ver\">What's new in 1.0.26</p>") < html.index(
        "<p class=\"ver\">What's new in 1.0.25</p>"
    )
    assert html.rstrip().endswith('<p class="none">Release notes unavailable.</p>')


def test_the_full_notes_link_goes_to_the_newest_release(model) -> None:  # noqa: ANN001
    _check(model, _doc("1.0.27", _release_text("1.0.27")))
    model._network.replies[1].finish([_doc("1.0.27", "x"), _doc("1.0.26", "y")])
    assert model.releasePageUrl == "https://github.com/x/y/releases/tag/1.0.27"
    opened: list[str] = []
    with mock.patch.object(
        update_model.QtGui.QDesktopServices, "openUrl",
        side_effect=lambda url: opened.append(url.toString()),
    ):
        model.openReleasePage()
    assert opened == ["https://github.com/x/y/releases/tag/1.0.27"]


def test_a_release_page_that_isnt_https_is_never_opened(model) -> None:  # noqa: ANN001
    _check(model, _doc("1.0.1", "", html_url="javascript:alert(1)"))
    assert model.releasePageUrl == updater.RELEASES_PAGE_URL


def test_no_notes_or_no_network_leaves_updating_working(model) -> None:  # noqa: ANN001
    model._kind = updater.INSTALLED
    latest = _doc("1.0.1", None)
    latest["assets"] = [{
        "name": updater.setup_name("1.0.1"),
        "browser_download_url": "https://github.com/x/y/releases/download/t/s.exe",
        "size": 10,
        "digest": "sha256:" + "a" * 64,
    }]
    _check(model, latest)
    model._network.replies[1].finish(None, _HostNotFound)
    assert model.releaseNotes == ""  # the window says "Release notes unavailable."
    assert model.state == "available" and model.canInstall


def test_unsafe_markup_is_dropped(model) -> None:  # noqa: ANN001
    body = (
        "## What's new in 1.0.1\n\n"
        "- Fixed <b>it</b>.<script>alert(1)</script>\n"
        "- <!-- hidden -->![screenshot](https://evil.example/x.png)\n"
        '- <img src="https://evil.example/y.png"><iframe src="x"></iframe>\n'
        "- See [the page](javascript:alert(2)) and [help](https://example.org/h)\n"
        "- Your name becomes `<user>`\n"
    )
    _check(model, _doc("1.0.1", body))
    model._network.replies[1].finish([_doc("1.0.1", body)])
    html = model.releaseNotes
    for gone in ("<script", "alert", "hidden", "evil.example", "iframe", "<img",
                 "javascript"):
        assert gone not in html, gone
    text = _plain(html)
    assert "Fixed it." in text and "screenshot" in text and "the page" in text
    assert '<a href="https://example.org/h">help</a>' in html
    assert "<code>&lt;user&gt;</code>" in html


def test_a_list_that_fails_shows_the_own_notes(model) -> None:  # noqa: ANN001
    _check(model, _doc("1.0.1", _new("1.0.1", "One")))
    assert model.state == "checking" and model.offers == []
    # Bounded: the request gives up like the check does (and the model
    # stops waiting after _NOTES_WAIT_MS).
    timeout = model._network.requests[1].transferTimeout()
    assert timeout == update_model._CHECK_TIMEOUT_MS
    model._network.replies[1].finish(None, _Timeout)
    assert model.state == "available" and model.offers == [1]
    assert "One" in model.releaseNotes  # the latest release's own notes


def test_a_late_list_from_an_earlier_check_is_ignored(model) -> None:  # noqa: ANN001
    _check(model, _doc("1.0.1", _new("1.0.1", "One")))
    stale = model._network.replies[1]
    model._state = "upToDate"
    model.check(True)
    model._network.replies[2].finish(_doc("1.0.2", _new("1.0.2", "Two")))
    stale.finish([_doc("1.0.1", _new("1.0.1", "One"))])
    assert model.state == "checking"
    model._network.replies[3].finish(None, _HostNotFound)
    assert "Two" in model.releaseNotes
    assert "One" not in model.releaseNotes


def test_startup_check_stays_silent_and_asks_for_no_notes(model) -> None:  # noqa: ANN001
    _check(model, _doc("1.0.0", "Same"), manual=False)
    assert model.state == "upToDate" and model.offers == []
    assert len(model._network.requests) == 1
    model._state = "idle"
    model.check(False)
    model._network.replies[1].finish(None, _HostNotFound)
    assert model.state == "error" and model.offers == []
    assert len(model._network.requests) == 2


def test_startup_check_of_a_skipped_version_asks_for_no_notes(model) -> None:  # noqa: ANN001
    Configuration().set("global", "internal", "skipped-update-version", "1.0.1")
    _check(model, _doc("1.0.1", _new("1.0.1", "One")), manual=False)
    assert model.offers == [] and len(model._network.requests) == 1


def test_notes_url_follows_the_feed() -> None:
    assert updater.notes_url(updater.LATEST_RELEASE_URL) == updater.RELEASES_LIST_URL
    assert (
        updater.notes_url("http://localhost:8000/repos/a/b/releases/latest")
        == "http://localhost:8000/repos/a/b/releases?per_page=30"
    )
    assert updater.notes_url("http://localhost:8000/feed.json") == ""


# --- the notes request never outlives its model or leaks out of a test -----


def test_an_offline_run_sends_no_notes_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Driving the check's reply directly (as older tests do) must not reach
    GitHub for the notes when GREMLIN_OFFLINE is set."""
    monkeypatch.setenv("GREMLIN_OFFLINE", "1")
    monkeypatch.setattr(update_model.util, "get_code_version", lambda: "1.0.0")
    m = update_model.UpdateModel()
    network = _Network()
    m._network = network  # type: ignore[assignment]
    reply = _Reply()
    reply._data = json.dumps(
        _doc("1.0.1", _new("1.0.1", "One"))
    ).encode("utf-8")
    m._manual = True
    m._on_checked(reply)  # type: ignore[arg-type]
    assert m.state == "available"
    assert network.requests == []
    assert "One" in m.releaseNotes


def test_a_notes_reply_after_the_model_is_gone_does_nothing(
    model, monkeypatch: pytest.MonkeyPatch  # noqa: ANN001
) -> None:
    import shiboken6

    errors: list[BaseException] = []
    monkeypatch.setattr(sys, "excepthook", lambda *exc: errors.append(exc[1]))
    _check(model, _doc("1.0.1", _new("1.0.1", "One")))
    pending = model._network.replies[1]
    shiboken6.delete(model)
    pending.finish([_doc("1.0.1", _new("1.0.1", "One"))])
    _app.processEvents()
    assert errors == []


def test_a_new_check_abandons_the_pending_notes_request(model) -> None:  # noqa: ANN001
    _check(model, _doc("1.0.1", _new("1.0.1", "One")))
    pending = model._network.replies[1]
    model._state = "upToDate"
    model.check(True)
    assert pending.aborted


# --- D-01-UPDATE-NOTES-CACHE: fetched before the window shows them, filled
# once, kept for the session ------------------------------------------------


def _fills(m) -> list[str]:  # noqa: ANN001
    """Every non-empty notes text the window is handed."""
    fills: list[str] = []
    m.notesChanged.connect(
        lambda: fills.append(m.releaseNotes) if m.releaseNotes else None
    )
    return fills


def _wait_until(condition, ms: int = 3000) -> None:  # noqa: ANN001
    from gremlin import clock

    end = clock.monotonic() + ms / 1000.0
    while not condition() and clock.monotonic() < end:
        _app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 20)
    assert condition()


@pytest.mark.parametrize("manual", [True, False])
def test_the_window_opens_once_with_every_version(model, manual: bool) -> None:  # noqa: ANN001
    """Help > Check for Updates and the start-up check alike: the list is
    fetched while "Checking…"; the window opens with both versions in one go."""
    fills = _fills(model)
    _check(model, _doc("1.0.2", _new("1.0.2", "Two")), manual=manual)
    assert model.state == "checking" and model.offers == []
    assert fills == [] and model.releaseNotes == ""
    model._network.replies[1].finish([
        _doc("1.0.2", _new("1.0.2", "Two")), _doc("1.0.1", _new("1.0.1", "One")),
    ])
    assert model.state == "available" and model.offers == [1]
    assert len(fills) == 1
    assert "Two" in fills[0] and "One" in fills[0]


def test_a_list_that_takes_too_long_uses_the_own_notes_and_never_refills(
    model, monkeypatch: pytest.MonkeyPatch  # noqa: ANN001
) -> None:
    monkeypatch.setattr(update_model, "_NOTES_WAIT_MS", 30)
    fills = _fills(model)
    _check(model, _doc("1.0.2", _new("1.0.2", "Two")), manual=False)
    assert model.state == "checking"
    _wait_until(lambda: model.state == "available")
    assert model.offers == [1]
    assert len(fills) == 1 and "Two" in fills[0]
    late = model._network.replies[1]
    assert late.aborted
    late.finish([
        _doc("1.0.2", _new("1.0.2", "Two")), _doc("1.0.1", _new("1.0.1", "One")),
    ])
    _app.processEvents()
    assert len(fills) == 1 and "One" not in model.releaseNotes


def test_the_wait_is_about_five_seconds() -> None:
    assert 3000 <= update_model._NOTES_WAIT_MS <= 6000


def test_opening_again_uses_the_kept_notes(model) -> None:  # noqa: ANN001
    _check(model, _doc("1.0.2", _new("1.0.2", "Two")))
    model._network.replies[1].finish([
        _doc("1.0.2", _new("1.0.2", "Two")), _doc("1.0.1", _new("1.0.1", "One")),
    ])
    shown = model.releaseNotes
    fills = _fills(model)
    model.check(True)
    model._network.replies[2].finish(_doc("1.0.2", _new("1.0.2", "Two")))
    # At once, from the kept notes: no new list request.
    assert model.state == "available" and model.offers == [1, 1]
    assert len(model._network.requests) == 3
    assert fills == [shown]
    # A newer release found later replaces them.
    model.check(True)
    model._network.replies[3].finish(_doc("1.0.3", _new("1.0.3", "Three")))
    assert model.state == "checking"
    assert model._network.urls()[4] == updater.RELEASES_LIST_URL
    model._network.replies[4].finish([
        _doc("1.0.3", _new("1.0.3", "Three")), _doc("1.0.2", _new("1.0.2", "Two")),
    ])
    assert "Three" in model.releaseNotes and model.state == "available"
