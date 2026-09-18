from __future__ import annotations

import os
from pathlib import Path

from local_media_curator.db.repositories import MediaRepository, SourceFolderRepository
from local_media_curator.domain.models import Project
from local_media_curator.domain.paths import normalize_path
from local_media_curator.domain.portable_list import PortableItem, PortableList, to_json
from local_media_curator.services.list_service import ListService


def source_labels(folder_paths: list[str]) -> dict[str, str]:
    """Map each folder path to a unique label, disambiguating shared leaf names."""
    if not folder_paths:
        return {}
    paths = [Path(path) for path in folder_paths]
    max_depth = max(len(path.parts) for path in paths)
    depth = 1
    while depth <= max_depth:
        labels: dict[str, str] = {}
        for original, path in zip(folder_paths, paths, strict=True):
            take = min(depth, len(path.parts))
            labels[original] = "/".join(path.parts[-take:])
        if len(set(labels.values())) == len(labels):
            return labels
        depth += 1
    # Distinct inputs that still collide after exhausting parts (e.g. same path twice).
    counts: dict[str, int] = {}
    result: dict[str, str] = {}
    for original, path in zip(folder_paths, paths, strict=True):
        base = "/".join(path.parts)
        n = counts.get(base, 0)
        counts[base] = n + 1
        result[original] = base if n == 0 else f"{base}#{n}"
    return result


def relative_to_source(absolute: str, source_root: str) -> str:
    return (
        Path(absolute)
        .resolve()
        .relative_to(Path(source_root).resolve())
        .as_posix()
    )


def owning_source(absolute: str, folder_paths: list[str]) -> str | None:
    abs_norm = normalize_path(Path(absolute))
    best: str | None = None
    best_len = -1
    for folder in folder_paths:
        folder_norm = normalize_path(Path(folder))
        if abs_norm == folder_norm or abs_norm.startswith(folder_norm + os.sep):
            if len(folder_norm) > best_len:
                best = folder
                best_len = len(folder_norm)
    return best


class ExportService:
    def __init__(self, project: Project) -> None:
        self._project = project
        self._lists = ListService(project)
        self._media = MediaRepository(project.connection)
        self._sources = SourceFolderRepository(project.connection)

    def export_list(self, list_id: int, destination: Path) -> PortableList:
        list_meta = next(
            (row for row in self._lists.all_lists() if int(row["id"]) == list_id),
            None,
        )
        if list_meta is None:
            raise ValueError("名单不存在。")

        ordered_ids = self._lists.ordered_media_ids(list_id)
        rows = self._media.get_by_ids(ordered_ids)
        folder_paths = [str(row["path"]) for row in self._sources.list_enabled()]
        labels = source_labels(folder_paths)

        items: list[PortableItem] = []
        for order, row in enumerate(rows):
            absolute = str(row["absolute_path"])
            owner = owning_source(absolute, folder_paths)
            if owner is None:
                source_label = ""
                rel = Path(absolute).name
            else:
                source_label = labels[owner]
                rel = relative_to_source(absolute, owner)
            items.append(
                PortableItem(
                    order=order,
                    source=source_label,
                    relative_path=rel,
                    file_name=str(row["file_name"]),
                    file_size=row["file_size"],
                    modified_at=row["modified_at"],
                )
            )

        document = PortableList(name=str(list_meta["name"]), items=items)
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(to_json(document), encoding="utf-8")
        return document
