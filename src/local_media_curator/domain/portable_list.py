from __future__ import annotations

import json
from dataclasses import dataclass

FORMAT = "light-local-photo-list"
VERSION = 1


@dataclass
class PortableItem:
    order: int
    source: str
    relative_path: str
    file_name: str
    file_size: int | None
    modified_at: str | None
    absolute_path: str | None = None


@dataclass
class PortableList:
    name: str
    items: list[PortableItem]


def to_json(document: PortableList) -> str:
    items: list[dict[str, object]] = []
    for item in document.items:
        payload: dict[str, object] = {
            "order": item.order,
            "source": item.source,
            "relative_path": item.relative_path,
            "file_name": item.file_name,
            "file_size": item.file_size,
            "modified_at": item.modified_at,
        }
        if item.absolute_path is not None:
            payload["absolute_path"] = item.absolute_path
        items.append(payload)
    return json.dumps(
        {
            "format": FORMAT,
            "version": VERSION,
            "list": {"name": document.name},
            "items": items,
        },
        ensure_ascii=False,
        indent=2,
    )


def from_json(text: str) -> PortableList:
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("名单文件格式无效。")
    if data.get("format") != FORMAT:
        raise ValueError(f"不支持的名单格式：{data.get('format')!r}")
    if data.get("version") != VERSION:
        raise ValueError(f"不支持的名单版本：{data.get('version')!r}")

    list_meta = data.get("list")
    if not isinstance(list_meta, dict) or "name" not in list_meta:
        raise ValueError("名单文件缺少必要字段。")
    name = list_meta["name"]
    if not isinstance(name, str):
        raise ValueError("名单文件缺少必要字段。")

    raw_items = data.get("items")
    if not isinstance(raw_items, list):
        raise ValueError("名单文件缺少必要字段。")

    items: list[PortableItem] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise ValueError("名单文件缺少必要字段。")
        try:
            items.append(
                PortableItem(
                    order=int(raw["order"]),
                    source=str(raw["source"]),
                    relative_path=str(raw["relative_path"]),
                    file_name=str(raw["file_name"]),
                    file_size=raw.get("file_size"),
                    modified_at=raw.get("modified_at"),
                    absolute_path=raw.get("absolute_path"),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("名单文件缺少必要字段。") from exc
    return PortableList(name=name, items=items)
