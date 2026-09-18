"""Lightroom Classic .lrsmcol writer.

Format is the Lua table Lightroom writes for "Export Smart Collection Settings",
not an invented schema. Checked against published files:

- https://gist.github.com/dergachev/6541450
  ``type = "LibrarySmartCollection"``, ``criteria = "filename"``,
  ``value2 = ""``, ``version = 0``. That sample uses ``operation = "any"``
  with a full filename including extension, and the author says a JPEG name
  must be rewritten to the RAW name before import.
- http://worldofthev1.blogspot.com/2017/11/importing-collection-in-lightroom-using.html
  uses ``operation = "beginsWith"`` and ``combine = "union"`` for a list of files.

A JPEG stem is therefore emitted as ``beginsWith`` ``"<stem>."`` so one rule
can match ``DSC_1832.CR3`` without naming a camera extension. Rules are OR'd
(``combine = "union"``). The outer gist prose uses ``intersect``, which would
require one photo to match every filename; the working list generator and the
2017 catalog query both use ``union``.
"""

from __future__ import annotations

import uuid
from pathlib import Path

# Stable namespace taken from the published gist id, so the same list contents
# always render the same ``id`` field.
_ID_NAMESPACE = uuid.UUID("d7b14054-ae5e-4fc8-8e16-fc0eaa9b9581")
_JPEG_SUFFIXES = frozenset({".jpg", ".jpeg"})

DUPLICATE_STEM_WARNING = (
    "Lightroom RAW 收藏夹按文件主名匹配。\n\n"
    "如果 Lightroom Catalog 中存在不同目录下的同名 RAW，\n"
    "这些文件可能同时进入智能收藏夹。"
)


def jpeg_stem(file_name: str) -> str | None:
    suffix = Path(file_name).suffix.lower()
    if suffix not in _JPEG_SUFFIXES:
        return None
    stem = Path(file_name).stem
    if not stem:
        return None
    return stem


def unique_jpeg_stems(file_names: list[str]) -> list[str]:
    seen: set[str] = set()
    stems: list[str] = []
    for name in file_names:
        stem = jpeg_stem(name)
        if stem is None or stem in seen:
            continue
        seen.add(stem)
        stems.append(stem)
    return sorted(stems)


def render_lrsmcol(title: str, stems: list[str]) -> str:
    """Render a deterministic .lrsmcol document. ``stems`` are filename stems."""
    ordered = sorted(dict.fromkeys(stems))
    collection_id = str(
        uuid.uuid5(_ID_NAMESPACE, title + "\n" + "\n".join(ordered))
    ).upper()
    rules = "".join(_rule(stem) for stem in ordered)
    return (
        "s = {\n"
        f"  id = {_lua_string(collection_id)},\n"
        f"  internalName = {_lua_string(title)},\n"
        f"  title = {_lua_string(title)},\n"
        '  type = "LibrarySmartCollection",\n'
        "  value = {\n"
        f"{rules}"
        '    combine = "union",\n'
        "  },\n"
        "  version = 0,\n"
        "}\n"
    )


def _rule(stem: str) -> str:
    return (
        "    {\n"
        '      criteria = "filename",\n'
        '      operation = "beginsWith",\n'
        f"      value = {_lua_string(stem + '.')},\n"
        '      value2 = "",\n'
        "    },\n"
    )


def _lua_string(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\r", "\\r")
        .replace("\n", "\\n")
    )
    return f'"{escaped}"'
