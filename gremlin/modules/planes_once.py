# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""ONE-TIME (tracker OT-2): a device map saved before the background and
foreground planes kept the device's photo outside its layers, as a
top-level "image" with a "photo" pose and look. When such a map is opened,
the photo becomes the bottom background picture, in memory only; opening
never writes the file and the next Save writes today's layout (07 S125,
D-07-PLANES-ANSWERS P3a). Remove this module and its calls (store.
set_device_photo, store.device_photo_ref's fallback, HardwareProfile.load
and loadRecovery) once no map in the old layout is left.
"""

from __future__ import annotations

from pathlib import Path

from gremlin.modules import store

# ONE-TIME (tracker OT-2): the old layout's photo keys.
OLD_PHOTO_KEYS = ("image", "photo", "imageWidth", "imageHeight")


# ONE-TIME (tracker OT-2)
def _num(source: dict, key: str, default: float, low: float, high: float) -> float:
    try:
        value = float(source.get(key, default))
    except (TypeError, ValueError):
        value = default
    if value != value:  # NaN
        value = default
    return max(low, min(high, value))


# ONE-TIME (tracker OT-2)
def _old_size(doc: dict, folder: Path | None, ref: str) -> tuple[float, float]:
    """The old photo's size: its file's, else the size the old map noted."""
    width, height = store.picture_size(folder, ref)
    if width > 0 and height > 0:
        return width, height
    try:
        width = float(doc.get("imageWidth") or 0)
        height = float(doc.get("imageHeight") or 0)
    except (TypeError, ValueError):
        return 0, 0
    return (width, height) if width > 0 and height > 0 else (0, 0)


# ONE-TIME (tracker OT-2)
def old_photo_to_layer(doc: dict, folder: Path | None = None) -> bool:
    """A map in the old layout: its photo becomes the bottom background
    picture where it was shown (fitted in the photo frame, scaled about its
    centre, moved by offX/offY of the page, turned by rot), its fade an
    opacity, its brightness, contrast and greyscale the picture's look,
    hidden and locked kept; "image" and "photo" go. A map that already has a
    background picture only loses the old keys. folder: the device folder,
    where the picture's size is read. True when doc changed."""
    if not isinstance(doc, dict) or not any(k in doc for k in OLD_PHOTO_KEYS):
        return False
    ref = store.normal_ref(str(doc.get("image") or ""))
    raw = doc.get("photo")
    pose: dict = raw if isinstance(raw, dict) else {}
    nodes = doc.get("nodes")
    if not isinstance(nodes, list):
        nodes = []
        doc["nodes"] = nodes
    if ref and store._bottom_picture_index(nodes) < 0:
        width, height = _old_size(doc, folder, ref)
        _, _, base_w, base_h = store.fit_in_box(store.PHOTO_FRAME, width, height)
        # The old editor's clamp (rig_photo.clampPhotoScale).
        scale = _num(pose, "scale", 1.0, -1e9, 1e9)
        scale = max(0.25, min(4.0, scale)) if scale > 0 else 1.0
        fw, fh = base_w * scale, base_h * scale
        cx = 0.5 + _num(pose, "offX", 0.0, -1.0, 1.0)
        cy = 0.5 + _num(pose, "offY", 0.0, -1.0, 1.0)
        node = store.background_picture_node(ref, (cx - fw / 2, cy - fh / 2, fw, fh))
        node["rot"] = _num(pose, "rot", 0.0, -1e9, 1e9)
        fade = _num(pose, "fade", 0.0, 0.0, 0.9)
        node["opacity"] = round(1.0 - fade, 6)
        look: dict = {}
        for key in ("bright", "contrast"):
            value = _num(pose, key, 0.0, -1.0, 1.0)
            if value:
                look[key] = value
        grey = _num(pose, "grey", 0.0, 0.0, 1.0)
        if grey:
            look["grey"] = grey
        if look:
            node["look"] = look
        if pose.get("hidden") is True:
            node["hidden"] = True
        if pose.get("locked") is True:
            node["locked"] = True
        nodes.insert(0, node)
    for key in OLD_PHOTO_KEYS:
        doc.pop(key, None)
    return True
