import json

import pytest

from local_media_curator.domain.portable_list import (
    FORMAT,
    VERSION,
    PortableItem,
    PortableList,
    from_json,
    to_json,
)


def test_round_trip_preserves_order_and_fields() -> None:
    document = PortableList(
        name="Website Final",
        items=[
            PortableItem(
                order=0,
                source="camera-a",
                relative_path="2026/IMG_0001.jpg",
                file_name="IMG_0001.jpg",
                file_size=8421943,
                modified_at="2026-08-31T20:31:12",
            ),
            PortableItem(
                order=1,
                source="camera-a",
                relative_path="2026/IMG_0002.jpg",
                file_name="IMG_0002.jpg",
                file_size=12,
                modified_at="2026-08-31T20:32:00",
            ),
        ],
    )
    loaded = from_json(to_json(document))
    assert loaded.name == "Website Final"
    assert [item.file_name for item in loaded.items] == ["IMG_0001.jpg", "IMG_0002.jpg"]
    assert [item.order for item in loaded.items] == [0, 1]
    payload = json.loads(to_json(document))
    assert payload["format"] == FORMAT == "light-local-photo-list"
    assert payload["version"] == VERSION == 1
    assert "absolute_path" not in payload["items"][0]


def test_from_json_rejects_wrong_format() -> None:
    with pytest.raises(ValueError):
        from_json('{"format": "other", "version": 1, "list": {"name": "A"}, "items": []}')


@pytest.mark.parametrize("missing_key", ["order", "source", "relative_path", "file_name"])
def test_from_json_missing_item_key_raises_value_error(missing_key: str) -> None:
    item = {
        "order": 0,
        "source": "src",
        "relative_path": "A.jpg",
        "file_name": "A.jpg",
        "file_size": 1,
        "modified_at": "2026-01-01T00:00:00",
    }
    del item[missing_key]
    text = json.dumps(
        {
            "format": "light-local-photo-list",
            "version": 1,
            "list": {"name": "A"},
            "items": [item],
        }
    )
    with pytest.raises(ValueError, match="名单文件缺少必要字段") as exc_info:
        from_json(text)
    assert not isinstance(exc_info.value, KeyError)
    assert exc_info.type is ValueError


def test_from_json_accepts_optional_absolute_path() -> None:
    text = json.dumps(
        {
            "format": "light-local-photo-list",
            "version": 1,
            "list": {"name": "A"},
            "items": [
                {
                    "order": 0,
                    "source": "src",
                    "relative_path": "A.jpg",
                    "file_name": "A.jpg",
                    "file_size": 1,
                    "modified_at": "2026-01-01T00:00:00",
                    "absolute_path": "D:/Photos/A.jpg",
                }
            ],
        }
    )
    loaded = from_json(text)
    assert loaded.items[0].absolute_path == "D:/Photos/A.jpg"
