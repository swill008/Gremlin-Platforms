# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""
This module provides text-to-speech support via the Qt WinRT TTS backend.
"""

from __future__ import annotations

import dataclasses
import enum
import logging
from collections import deque

from PySide6 import QtCore
from PySide6.QtTextToSpeech import (
    QTextToSpeech,
    QVoice,
)

from gremlin import threads
from gremlin.common import SingletonMetaclass
from gremlin.config import Configuration
from gremlin.types import PropertyType


class TTSQueueMode(enum.StrEnum):
    QueueBack = "queue-back"
    QueueFront = "queue-front"
    Interrupt = "interrupt"


@dataclasses.dataclass
class TTSRequest:
    text: str
    rate: float
    volume: float
    pitch: float


# The Qt speech backend used (Windows speech).
_ENGINE = "winrt"


class TTSManager(metaclass=SingletonMetaclass):
    """Singleton TTS manager with a self-managed playback queue."""

    def __init__(self) -> None:
        self._engine: QTextToSpeech | None = None
        self._queue: deque[TTSRequest] = deque()
        self._current_request: TTSRequest | None = None
        # True between start() and stop() (a Run): speech asked for with no
        # Run on (a late timer after Stop) is ignored (06 Q8). The engine
        # itself stays for the program's life (Options lists its voices).
        self._running = False
        # None until checked; then True when Windows speech can't be used.
        self._unavailable: bool | None = None

    def start(self) -> None:
        """A Run starts: speech is taken from now until stop(). Safe to
        call repeatedly; from any thread (Run starts on the input thread):
        the engine is made on the main thread, where it lives."""
        self._running = True
        threads.main_call(self.prepare_engine)

    def prepare_engine(self) -> None:
        """Initialise the engine and wire signals (no Run needed: Options
        lists the voices). Safe to call repeatedly."""
        if self._engine is not None:
            return
        self._engine = QTextToSpeech(_ENGINE)
        voice_name = Configuration().value("action", "text-to-speech", "voice")
        if voice_name:
            for voice in self._engine.availableVoices():
                if voice.name() == voice_name:
                    self._engine.setVoice(voice)
                    break
        self._engine.stateChanged.connect(self._on_state_changed)
        if self._engine.state() == getattr(QTextToSpeech.State, "Error", None):
            self._mark_unavailable()
        self.speech_available()

    def speech_available(self) -> bool:
        """False when Windows speech can't be used: nothing will be spoken
        (09 Q13). The first time it is found missing, one warning goes to
        the log."""
        if self._unavailable is None:
            try:
                missing = _ENGINE not in QTextToSpeech.availableEngines()
            except Exception:
                missing = True
            if missing:
                self._mark_unavailable()
            else:
                self._unavailable = False
        return not self._unavailable

    def _mark_unavailable(self) -> None:
        if self._unavailable:
            return
        self._unavailable = True
        logging.getLogger("system").warning(
            "Windows speech is not available: Text to Speech actions say nothing."
        )

    def stop(self) -> None:
        """Clear the queue and stop any ongoing speech. From any thread
        (Stop runs on the input thread): the engine is stopped on the main
        thread; speech asked for after this is ignored at once."""
        self._running = False
        threads.main_call(self._stop_now)

    def _stop_now(self) -> None:
        self._queue.clear()
        if self._engine is not None:
            self._engine.stop()

    def close(self) -> None:
        """Release the engine at program exit: a Windows speech engine left
        alive holds the process for about 5 s after it ends (to-do 81).
        Main thread only; safe to call twice or with no engine."""
        self.stop()
        engine, self._engine = self._engine, None
        if engine is None:
            return
        try:
            engine.stateChanged.disconnect(self._on_state_changed)
        except (RuntimeError, TypeError):
            pass
        engine.deleteLater()
        # Delete it now: after the event loop ends nothing else will. Only
        # the engine: flushing every pending deleteLater on the thread
        # deleted other objects mid-shutdown and aborted the process (111).
        QtCore.QCoreApplication.sendPostedEvents(
            engine, QtCore.QEvent.Type.DeferredDelete
        )

    def enqueue(self, request: TTSRequest, mode: TTSQueueMode) -> None:
        """Add *request* to the queue according to *mode* and start speaking
        if the engine is currently idle.

        Asked for on another thread (the input thread, a macro), the
        request is passed to the main thread first: the engine is a Qt
        object of the main thread (09 R10).
        """
        if not self._running:
            return
        threads.main_call(self._enqueue_now, request, mode)

    def _enqueue_now(self, request: TTSRequest, mode: TTSQueueMode) -> None:
        if not self._running:
            return  # stopped while it was on its way
        force_speak = False
        match mode:
            case TTSQueueMode.QueueBack:
                self._queue.append(request)
            case TTSQueueMode.QueueFront:
                self._queue.appendleft(request)
            case TTSQueueMode.Interrupt:
                if self._engine is not None:
                    self._engine.stop()
                self._queue.appendleft(request)
                force_speak = True
        self._speak_next(force_speak)

    def available_voices(self) -> list[QVoice]:
        if self._engine is None:
            return []
        return self._engine.availableVoices()

    def update_voice(self, voice_name: str) -> None:
        """Speak with *voice_name* from now on; "" (or a voice that is not
        installed) means the system's default voice (09 S58, S59)."""
        if self._engine is None:
            return
        for voice in self._engine.availableVoices():
            if voice.name() == voice_name:
                self._engine.setVoice(voice)
                return
        # Qt has no "back to default": a new engine starts with it (and
        # prepare_engine applies the saved voice, if installed).
        self._engine.stop()
        self._engine.stateChanged.disconnect(self._on_state_changed)
        self._engine = None
        self.prepare_engine()
        self._speak_next()

    def _on_state_changed(self, state: QTextToSpeech.State) -> None:
        if state == QTextToSpeech.State.Ready:
            self._speak_next()

    def _speak_next(self, force_speak: bool = False) -> None:
        """Pop and speak the next queued item."""
        if not self._queue or self._engine is None:
            return
        if self._engine.state() != QTextToSpeech.State.Ready and not force_speak:
            return

        self._current_request = self._queue.popleft()
        self._engine.setRate(self._current_request.rate)
        self._engine.setVolume(self._current_request.volume)
        self._engine.setPitch(self._current_request.pitch)
        self._engine.say(self._current_request.text)


Configuration().register(
    "action",
    "text-to-speech",
    "voice",
    PropertyType.String,
    "",
    "Name of the TTS voice to use for all Text to Speech actions.",
    {},
    False,
)
