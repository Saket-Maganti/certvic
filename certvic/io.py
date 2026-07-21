"""Small JSON/JSONL helpers with Pydantic support."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, TypeVar

from pydantic import BaseModel

ModelT = TypeVar("ModelT", bound=BaseModel)


def ensure_parent(path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def read_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str | Path, data: Any) -> None:
    ensure_parent(path)
    with Path(path).open("w", encoding="utf-8") as handle:
        json.dump(_to_jsonable(data), handle, indent=2, sort_keys=True)
        handle.write("\n")


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    path = Path(path)
    if not path.exists():
        return records
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"JSONL record must be an object at {path}:{line_no}")
            records.append(record)
    return records


def write_jsonl(path: str | Path, records: Iterable[Any]) -> None:
    ensure_parent(path)
    with Path(path).open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(_to_jsonable(record), sort_keys=True) + "\n")
            handle.flush()


def append_jsonl(path: str | Path, record: Any) -> None:
    ensure_parent(path)
    with Path(path).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(_to_jsonable(record), sort_keys=True) + "\n")
        handle.flush()


def load_model_json(path: str | Path, model_cls: type[ModelT]) -> ModelT:
    return model_cls.model_validate(read_json(path))


def save_model_json(path: str | Path, model: BaseModel) -> None:
    write_json(path, model.model_dump(mode="json"))


def load_model_jsonl(path: str | Path, model_cls: type[ModelT]) -> list[ModelT]:
    return [model_cls.model_validate(row) for row in read_jsonl(path)]


def _to_jsonable(data: Any) -> Any:
    if isinstance(data, BaseModel):
        return data.model_dump(mode="json")
    if isinstance(data, list):
        return [_to_jsonable(item) for item in data]
    if isinstance(data, dict):
        return {key: _to_jsonable(value) for key, value in data.items()}
    return data
