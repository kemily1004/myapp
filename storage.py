"""쇼핑 리스트 데이터 로드/저장.

app.py는 load_items()와 save_items()만 호출한다.
추후 외부 DB로 교체할 때는 이 모듈만 바꾸면 된다.
"""

import json
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data.json"


def load_items() -> list[dict]:
    """data.json에서 아이템 목록을 읽는다. 파일이 없거나 손상되면 빈 리스트를 반환한다."""
    try:
        with DATA_FILE.open(encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    return [_normalize(item) for item in data if isinstance(item, dict) and item.get("id") and item.get("name")]


def _normalize(item: dict) -> dict:
    """누락되거나 형식이 잘못된 필드를 기본값으로 채운다."""
    try:
        quantity = int(item.get("quantity", 1))
    except (TypeError, ValueError):
        quantity = 1
    return {
        "id": str(item["id"]),
        "name": str(item["name"]),
        "quantity": quantity,
        "checked": bool(item.get("checked", False)),
        "created_at": str(item.get("created_at", "")),
    }


def save_items(items: list[dict]) -> None:
    """아이템 목록을 data.json에 저장한다."""
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
