# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import array
import logging
import threading
from collections.abc import Callable, Generator

import miniaudio

from gremlin import clock, threads
from gremlin.common import SingletonMetaclass
from gremlin.config import Configuration
from gremlin.log_once import log_once
from gremlin.types import PropertyType
from gremlin.util import clamp


class AudioSample:
    """Represents a single audiot sample to be played.

    Generates the audio samples from the given audio file while also exposing
    controls over the playback.

    TODO: An instance cannot be reused after playback has completed. This is
        fine for the play audio action, but may be limiting for other uses.
    """

    Generator_T = Generator[bytes | array.array[int], int, None]

    def __init__(self, sound_file: str, play_volume: int) -> None:
        """Creates an AudioSample instance.

        Args:
            sound_file: The path to the audio file to be played.
            play_volume: The volume of the playback, the value is in the range
                [0, 100] with 0 being mute and 100 maximum.
        """
        decoded = miniaudio.decode_file(sound_file)
        volume_factor = clamp(play_volume / 100.0, 0.0, 1.0)
        samples = array.array(
            "h", [int(sample * volume_factor) for sample in decoded.samples]
        )

        self.stream = miniaudio.stream_raw_pcm_memory(
            samples, decoded.nchannels, decoded.sample_width
        )
        # A short buffer: a cancelled sound stops within ~50 ms.
        self.device = miniaudio.PlaybackDevice(
            sample_rate=decoded.sample_rate,
            nchannels=decoded.nchannels,
            output_format=decoded.sample_format,
            buffersize_msec=50,
        )
        # The generator runs on miniaudio's audio thread: other threads only
        # set _cancel (closing a running generator from another thread raises
        # "generator already executing"), and the device is closed on the
        # player's playback thread, never inside the audio callback.
        self._cancel = threading.Event()
        self._stream_done = threading.Event()
        self._closed = threading.Event()
        self._close_lock = threading.Lock()

    @property
    def done(self) -> bool:
        """Playback has finished or was cancelled, and the device is closed."""
        return self._closed.is_set()

    def block(self, still_wanted: Callable[[], bool]) -> None:
        """Blocks the calling thread until the sound has played out, or until
        still_wanted() is False (the player stopped)."""
        while not self._stream_done.wait(0.5):
            if not still_wanted():
                return

    def cancel(self) -> None:
        """Stops the playback; safe from any thread. The audio thread ends
        the sound at its next callback."""
        self._cancel.set()

    def close_if_done(self) -> bool:
        """Closes the device once the sound has ended; True when closed."""
        if self._stream_done.is_set():
            self._close()
        return self._closed.is_set()

    def close(self, timeout: float = 0.5) -> None:
        """Cancels the sound and closes the device, waiting at most timeout
        seconds for the audio thread to leave the generator."""
        self._cancel.set()
        self._stream_done.wait(max(timeout, 0.0))
        self._close()

    def _close(self) -> None:
        with self._close_lock:
            if self._closed.is_set():
                return
            try:
                self.device.close()
            finally:
                self._closed.set()

    def play(self) -> None:
        """Starts playing the audio file on miniaudio's audio thread."""

        def sample_generator() -> AudioSample.Generator_T:
            try:
                frames = yield b""
                while not self._cancel.is_set():
                    try:
                        chunk = self.stream.send(frames)
                    except StopIteration:
                        return
                    frames = yield chunk
            finally:
                self._stream_done.set()

        generator = sample_generator()
        next(generator)  # primed, so the device's send() works
        self.device.start(generator)


class AudioPlayer(metaclass=SingletonMetaclass):
    """Manages the playing of audio files."""

    def __init__(self) -> None:
        # (file, volume) waiting to play: decoded on the playback thread, not
        # on the thread that queued them (the event thread).
        self._play_list: list[tuple[str, int]] = []
        self._currently_playing: list[AudioSample] = []
        # Both lists are changed from the event thread, the playback thread
        # and Stop: every change holds this (09 R9).
        self._lock = threading.Lock()
        self._playback_mode = Configuration().value(
            "action", "play-sound", "playback-mode"
        )

        self._is_ready = False
        self._playback_thread: threading.Thread | None = None

    def refresh(self) -> None:
        """Refreshes the configuration by reading the playback-mode value."""
        self._playback_mode = Configuration().value(
            "action", "play-sound", "playback-mode"
        )

    def start(self) -> None:
        """Starts the audio playback thread if it is not already running."""
        if not self._is_ready:
            # Set here, not in the thread: a stop() right after start() must
            # not be undone when the thread starts.
            self._is_ready = True
            self._playback_thread = threads.start(
                "audio player", self._playback, stop=self._ask_to_stop
            )

    def _ask_to_stop(self) -> None:
        self._is_ready = False
        with self._lock:
            self._play_list = []
            playing = list(self._currently_playing)
        for sample in playing:
            sample.cancel()

    def stop(self) -> None:
        """Stops the audio playback thread."""
        self._ask_to_stop()
        if self._playback_thread is not None and self._playback_thread.is_alive():
            self._playback_thread.join(timeout=2.0)

    def enqueue(self, file_name: str, volume: int) -> None:
        """Queues the given sound with the specified volume to be played.

        The sound will be played according to the current playback mode.

        Args:
            sound_filename: The filename of the sound file to play.
            volume: The volume of the playback, the value is in the range
                [0, 100] with 0 being mute and 100 maximum
        """
        # No Run on (a late timer after Stop): nothing plays, now or at the
        # next Run (06 Q8).
        if not self._is_ready:
            return
        with self._lock:
            self._play_list.append((file_name, volume))

    def _next_sample(self) -> AudioSample | None:
        """The next queued sound, decoded and started; None if there is none
        or it can't be played (logged)."""
        with self._lock:
            if not self._play_list:
                return None
            file_name, volume = self._play_list.pop(0)
        try:
            sample = AudioSample(file_name, volume)
            with self._lock:
                # Interrupted sounds stay listed until the playback thread
                # has closed their device.
                interrupted = (
                    list(self._currently_playing)
                    if self._playback_mode == "Interrupt"
                    else []
                )
                self._currently_playing.append(sample)
            for old in interrupted:
                old.cancel()
            sample.play()
        except Exception as exc:
            # A file that can't be decoded (damaged, unsupported format).
            log_once(
                "user", ("play-sound-unreadable", file_name), logging.WARNING,
                f"Play Sound: could not play '{file_name}': {exc}",
            )
            return None
        return sample

    def _playback(self) -> None:
        """Background thread which ensures audio is played."""
        while self._is_ready:
            sample = self._next_sample()
            if sample is not None and self._playback_mode == "Sequential":
                sample.block(lambda: self._is_ready)
            self._close_finished()
            clock.sleep(0.01)
        self._close_all()

    def _close_finished(self) -> None:
        """Closes the devices of sounds that ended; they go, with their
        decoded audio. Closed here, off the lock and the audio thread."""
        with self._lock:
            playing = list(self._currently_playing)
        closed = [s for s in playing if s.close_if_done()]
        if closed:
            with self._lock:
                self._currently_playing = [
                    s for s in self._currently_playing if s not in closed
                ]

    def _close_all(self) -> None:
        """At the playback thread's end: cancels and closes every sound,
        waiting at most 0.5 s in all for the audio threads."""
        with self._lock:
            playing = list(self._currently_playing)
            self._currently_playing = []
        deadline = clock.monotonic() + 0.5
        for sample in playing:
            sample.close(deadline - clock.monotonic())


Configuration().register(
    "action",
    "play-sound",
    "playback-mode",
    PropertyType.Selection,
    "Sequential",
    "When playing sound files wait for the previous sound to finish "
    "(Sequential) or interrupt current playback (Interrupt), or play sounds "
    "in parallel (Overlap).",
    {"valid_options": ["Sequential", "Interrupt", "Overlap"]},
    True,
)
