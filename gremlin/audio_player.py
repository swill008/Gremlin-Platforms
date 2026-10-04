# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import array
import logging
import threading
import time
from collections.abc import Callable, Generator

import miniaudio

from gremlin import threads
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
        self.device = miniaudio.PlaybackDevice(
            sample_rate=decoded.sample_rate,
            nchannels=decoded.nchannels,
            output_format=decoded.sample_format,
        )
        self._playback_done_event = threading.Event()
        self._generator: AudioSample.Generator_T | None = None

    @property
    def done(self) -> bool:
        """Playback has finished or was cancelled."""
        return self._playback_done_event.is_set()

    def block(self, still_wanted: Callable[[], bool]) -> None:
        """Blocks the calling thread until playback is complete, or until
        still_wanted() is False (the player stopped)."""
        while not self._playback_done_event.wait(0.5):
            if not still_wanted():
                return

    def cancel(self) -> None:
        """Stops the playback immediately."""
        if not self._playback_done_event.is_set() and self._generator:
            try:
                self._generator.close()
            except ValueError:
                logging.getLogger("system").debug(
                    "Audio playback generator already running error raised."
                )

    def play(self) -> None:
        """Starts playing the audio file.

        Sets up the generator and notification events to control and manage
        playback.
        """
        self._playback_done_event.clear()

        def sample_generator() -> AudioSample.Generator_T:
            try:
                yield from self.stream
            finally:
                self._playback_done_event.set()
                self.device.close()

        # Create generator and initialize it such that the .send() method works.
        self._generator = sample_generator()
        next(self._generator)
        self.device.start(self._generator)


class AudioPlayer(metaclass=SingletonMetaclass):
    """Manages the playing of audio files."""

    def __init__(self) -> None:
        # (file, volume) waiting to play: decoded on the playback thread, not
        # on the thread that queued them (the event thread).
        self._play_list: list[tuple[str, int]] = []
        self._currently_playing: list[AudioSample] = []
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
        self._play_list = []
        for sample in list(self._currently_playing):
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
        self._play_list.append((file_name, volume))

    def _next_sample(self) -> AudioSample | None:
        """The next queued sound, decoded and started; None if there is none
        or it can't be played (logged)."""
        if not self._play_list:
            return None
        file_name, volume = self._play_list.pop(0)
        try:
            sample = AudioSample(file_name, volume)
            if self._playback_mode == "Interrupt":
                while self._currently_playing:
                    self._currently_playing.pop(0).cancel()
            self._currently_playing.append(sample)
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
            # Finished sounds go, with their decoded audio.
            self._currently_playing = [
                s for s in self._currently_playing if not s.done
            ]
            time.sleep(0.01)


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
