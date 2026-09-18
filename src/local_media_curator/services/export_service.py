from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from local_media_curator.db.repositories import MediaRepository, SourceFolderRepository
from local_media_curator.domain.models import Project
from local_media_curator.domain.paths import normalize_path
from local_media_curator.domain.portable_list import (
    PortableItem,
    PortableList,
    from_json,
    to_json,
)
from local_media_curator.services.list_service import ListService


@dataclass
class MatchResult:
    name: str
    matched_ids: list[int]
    missing: list[PortableItem]
    ambiguous: list[PortableItem]


@dataclass
class ImportResult:
    list_id: int
    matched: int
    missing: list[PortableItem]
    ambiguous: list[PortableItem]


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

    def match_list(
        self, path: Path, remaps: dict[str, Path] | None = None
    ) -> MatchResult:
        """Match manifest items to media ids without writing lists or list_items."""
        document = from_json(Path(path).read_text(encoding="utf-8"))
        remaps = remaps or {}

        folder_paths = [str(row["path"]) for row in self._sources.list_enabled()]
        labels = source_labels(folder_paths)
        label_to_folder = {label: folder for folder, label in labels.items()}

        matched_ids: list[int] = []
        missing: list[PortableItem] = []
        ambiguous: list[PortableItem] = []

        for item in sorted(document.items, key=lambda entry: entry.order):
            media_id = self._match_item(item, label_to_folder, remaps)
            if isinstance(media_id, int):
                matched_ids.append(media_id)
            elif media_id == "ambiguous":
                ambiguous.append(item)
            else:
                missing.append(item)

        return MatchResult(
            name=document.name,
            matched_ids=matched_ids,
            missing=missing,
            ambiguous=ambiguous,
        )

    def import_list(
        self, path: Path, remaps: dict[str, Path] | None = None
    ) -> ImportResult:
        match = self.match_list(path, remaps=remaps)
        list_id = self._lists.create(match.name)
        self._lists.replace_items(list_id, match.matched_ids)
        return ImportResult(
            list_id=list_id,
            matched=len(match.matched_ids),
            missing=match.missing,
            ambiguous=match.ambiguous,
        )

    def _match_item(
        self,
        item: PortableItem,
        label_to_folder: dict[str, str],
        remaps: dict[str, Path],
    ) -> int | str:
        # Level 1: current project source whose label equals item.source.
        folder = label_to_folder.get(item.source)
        if folder is not None:
            candidate = self._media.get_by_normalized_path(
                normalize_path(Path(folder) / Path(item.relative_path))
            )
            if candidate is not None:
                return int(candidate["id"])

        # Level 2: user-provided remapped root for this source label.
        remap_root = remaps.get(item.source)
        if remap_root is not None:
            candidate = self._media.get_by_normalized_path(
                normalize_path(Path(remap_root) / Path(item.relative_path))
            )
            if candidate is not None:
                return int(candidate["id"])

        # Level 3: filename + size + mtime fingerprint. None fields → missing.
        if item.file_size is None or item.modified_at is None:
            return "missing"
        rows = list(
            self._project.connection.execute(
                """
                SELECT id FROM media
                WHERE file_name = ? AND file_size = ? AND modified_at = ?
                """,
                (item.file_name, item.file_size, item.modified_at),
            )
        )
        if len(rows) == 1:
            return int(rows[0][0])
        if len(rows) >= 2:
            return "ambiguous"
        return "missing"
