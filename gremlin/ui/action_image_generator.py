# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import collections
import logging
import math
import threading
import urllib.parse

from PySide6 import (
    QtCore,
    QtGui,
    QtQuick,
)

from gremlin.ui import ui_scale_option
from gremlin.ui.util import ColorInformation

_XBOX_FACE = {
    "a": ("A", QtGui.QColor("#22C55E")),
    "b": ("B", QtGui.QColor("#EF4444")),
    "x": ("X", QtGui.QColor("#3B82F6")),
    "y": ("Y", QtGui.QColor("#EAB308")),
}
_XBOX_LABELS = {
    "left_stick_x": "LSX",
    "left_stick_y": "LSY",
    "right_stick_x": "RSX",
    "right_stick_y": "RSY",
    "left_trigger": "LT",
    "right_trigger": "RT",
    "left_shoulder": "LB",
    "right_shoulder": "RB",
    "left_thumb": "LS",
    "right_thumb": "RS",
    "start": "STR",
    "back": "BAK",
    "guide": "G",
    "dpad": "DP",
    "dpad_up": "DU",
    "dpad_down": "DD",
    "dpad_left": "DL",
    "dpad_right": "DR",
}


def _scale(query: str) -> float:
    """The UI scale an image id asks for ("r=3&s=175": 1.75); the active UI
    scale when it names none (09 Q16)."""
    values = urllib.parse.parse_qs(query).get("s", [])
    if values:
        return ui_scale_option.clamp_scale(values[0]) / 100
    return ui_scale_option.active_scale() / 100


class ActionSummaryImageProvider(QtQuick.QQuickImageProvider):
    """Generates action sequence visualizations."""

    def __init__(self, max_cache_size: int = 500) -> None:
        super().__init__(QtQuick.QQuickImageProvider.ImageType.Image)

        self._cache = collections.OrderedDict()
        self._max_cache_size = max_cache_size
        self._lock = threading.Lock()

        self._spacing = 2
        self._glyph_height = 21

        self._bootstrap_font = QtGui.QFont("bootstrap-icons")
        self._bootstrap_font.setPixelSize(15)
        self._bootstrap_metrics = QtGui.QFontMetrics(self._bootstrap_font)

        self._segoe_font = QtGui.QFont("Segoe UI")
        self._segoe_font.setPixelSize(19)
        self._segoe_metrics = QtGui.QFontMetrics(self._segoe_font)

        self._vjoy_font = QtGui.QFont("Segoe UI")
        self._vjoy_font.setPixelSize(11)
        self._vjoy_metrics = QtGui.QFontMetrics(self._vjoy_font)

        self._badge_font = QtGui.QFont("Segoe UI")
        self._badge_font.setPixelSize(9)
        self._badge_font.setBold(True)
        self._badge_metrics = QtGui.QFontMetrics(self._badge_font)

    def _ink(self) -> QtGui.QColor:
        colors = ColorInformation()
        if colors.is_dark_theme:
            return QtGui.QColor("#F8FAFC")
        return colors.foreground

    def requestImage(
        self, image_id: str, size: QtCore.QSize, requested_size: QtCore.QSize
    ) -> QtGui.QImage:
        with self._lock:
            if image_id in self._cache:
                self._cache.move_to_end(image_id)
                return self._cache[image_id]

        action_string, _, query = image_id.partition("?")
        image = self._render(action_string, _scale(query))

        with self._lock:
            if len(self._cache) >= self._max_cache_size:
                self._cache.popitem(last=False)
            self._cache[image_id] = image
            return image

    def _render(self, action_string: str, scale: float = 1.0) -> QtGui.QImage:
        """The summary drawn at the given UI scale (1.0 = 100 %): laid out
        at 100 %, then drawn scaled, so text and shapes stay sharp."""
        tokens = action_string.split(":") if action_string else []

        picture = QtGui.QPicture()
        painter = QtGui.QPainter(picture)

        try:
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing)
            painter.setPen(self._ink())

            x_offset = 0
            for token in tokens:
                if token in ["(", ")"]:
                    painter.setPen(self._ink())
                    painter.setFont(self._segoe_font)
                    glyph_width = self._segoe_metrics.horizontalAdvance(token)
                    painter.drawText(
                        QtCore.QRect(x_offset, -3, glyph_width, self._glyph_height),
                        QtCore.Qt.AlignmentFlag.AlignCenter,
                        token,
                    )
                    x_offset += glyph_width + self._spacing
                elif token.startswith("\uf448"):
                    glyph_width = self._render_vjoy_glyph(
                        token.split(","), painter, x_offset
                    )
                    x_offset += glyph_width + self._spacing
                elif token.startswith("\uf11b") or token.startswith("\uf2d4"):
                    glyph_width = self._render_xbox_glyph(
                        token.split(","), painter, x_offset
                    )
                    x_offset += glyph_width + self._spacing
                elif len(token) == 1:
                    painter.setPen(self._ink())
                    painter.setFont(self._bootstrap_font)
                    glyph_width = self._bootstrap_metrics.horizontalAdvance(token)
                    painter.drawText(
                        QtCore.QRect(x_offset, 1, glyph_width, self._glyph_height),
                        QtCore.Qt.AlignmentFlag.AlignCenter,
                        token,
                    )
                    x_offset += glyph_width + self._spacing
                else:
                    logging.getLogger("system").warning(
                        f"Unrecognized token in action string: '{token}'"
                    )
        finally:
            painter.end()

        width = max(20, x_offset - self._spacing if x_offset > 0 else 0)
        image = QtGui.QImage(
            math.ceil(width * scale),
            math.ceil(self._glyph_height * scale),
            QtGui.QImage.Format.Format_ARGB32_Premultiplied,
        )
        image.fill(QtCore.Qt.GlobalColor.transparent)

        img_painter = QtGui.QPainter(image)
        img_painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        img_painter.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing)
        img_painter.scale(scale, scale)
        img_painter.drawPicture(0, 0, picture)
        img_painter.end()

        return image

    def _render_vjoy_glyph(
        self, token: list[str], painter: QtGui.QPainter, x_offset: int
    ) -> int:
        lookup = {"A": "AX", "B": "BTN", "H": "HAT"}
        if len(token) < 4 or token[2] not in lookup:
            return 0

        vjoy_icon = token[0]
        vjoy_id = int(token[1])
        input_type = lookup[token[2]]
        input_id = int(token[3])
        painter.setPen(self._ink())

        icon_width = self._bootstrap_metrics.horizontalAdvance(vjoy_icon)
        device_width = self._segoe_metrics.horizontalAdvance(str(vjoy_id))
        label_block_width = max(
            self._vjoy_metrics.horizontalAdvance(str(input_id)),
            self._vjoy_metrics.horizontalAdvance(input_type),
        )

        current_x = x_offset

        painter.setFont(self._bootstrap_font)
        painter.drawText(
            QtCore.QRect(current_x, 1, icon_width, self._glyph_height),
            QtCore.Qt.AlignmentFlag.AlignCenter,
            vjoy_icon,
        )
        current_x += icon_width + self._spacing

        painter.setFont(self._segoe_font)
        painter.drawText(
            QtCore.QRect(current_x, -2, device_width, self._glyph_height),
            QtCore.Qt.AlignmentFlag.AlignVCenter,
            str(vjoy_id),
        )
        current_x += device_width + self._spacing

        painter.setFont(self._vjoy_font)
        painter.drawText(
            QtCore.QRect(current_x, -1, label_block_width, 13),
            QtCore.Qt.AlignmentFlag.AlignCenter,
            str(input_id),
        )
        painter.drawText(
            QtCore.QRect(current_x, 8, label_block_width, 13),
            QtCore.Qt.AlignmentFlag.AlignCenter,
            input_type,
        )

        return icon_width + device_width + label_block_width + 2 * self._spacing

    def _render_xbox_glyph(
        self, token: list[str], painter: QtGui.QPainter, x_offset: int
    ) -> int:
        pad_id = token[1] if len(token) > 1 else "1"
        target = token[2].strip().lower() if len(token) > 2 else "a"

        pad_width = self._vjoy_metrics.horizontalAdvance(str(pad_id))
        current_x = x_offset
        ink = self._ink()

        painter.setPen(ink)
        painter.setFont(self._vjoy_font)
        painter.drawText(
            QtCore.QRect(current_x, 4, pad_width, self._glyph_height - 4),
            QtCore.Qt.AlignmentFlag.AlignVCenter,
            str(pad_id),
        )
        current_x += pad_width + 3

        if target in _XBOX_FACE:
            letter, fill = _XBOX_FACE[target]
            size = 16
            rect = QtCore.QRect(current_x, 3, size, size)
            painter.setBrush(QtGui.QBrush(fill))
            painter.setPen(QtGui.QPen(fill.darker(130), 1))
            painter.drawEllipse(rect)
            painter.setPen(QtGui.QColor("#FFFFFF"))
            painter.setFont(self._badge_font)
            painter.drawText(rect, QtCore.Qt.AlignmentFlag.AlignCenter, letter)
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            return (current_x + size) - x_offset

        if target == "guide":
            size = 16
            fill = QtGui.QColor("#16A34A")
            rect = QtCore.QRect(current_x, 3, size, size)
            painter.setBrush(QtGui.QBrush(fill))
            painter.setPen(QtGui.QPen(QtGui.QColor("#86EFAC"), 1))
            painter.drawEllipse(rect)
            painter.setPen(QtGui.QColor("#FFFFFF"))
            painter.setFont(self._badge_font)
            painter.drawText(rect, QtCore.Qt.AlignmentFlag.AlignCenter, "X")
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            return (current_x + size) - x_offset

        label = _XBOX_LABELS.get(target, target.upper()[:3])
        text_w = max(16, self._badge_metrics.horizontalAdvance(label) + 6)
        rect = QtCore.QRect(current_x, 4, text_w, 14)
        painter.setBrush(QtGui.QBrush(QtGui.QColor("#1F2937")))
        painter.setPen(QtGui.QPen(ink, 1))
        painter.drawRoundedRect(rect, 3, 3)
        painter.setPen(ink)
        painter.setFont(self._badge_font)
        painter.drawText(rect, QtCore.Qt.AlignmentFlag.AlignCenter, label)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        return (current_x + text_w) - x_offset

    def invalidate(self, action_string: str | None = None) -> None:
        with self._lock:
            if action_string is None:
                self._cache.clear()
            elif action_string in self._cache:
                del self._cache[action_string]
