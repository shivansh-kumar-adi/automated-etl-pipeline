"""Pydantic validation and duplicate detection."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from .models import Rejection


class PostInput(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)
    id: int = Field(gt=0)
    userId: int = Field(gt=0)
    title: str
    body: str

    @field_validator("title", "body")
    @classmethod
    def non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value


def validate_records(
    records: list[dict[str, Any]], run_id: str
) -> tuple[list[PostInput], list[Rejection], int]:
    valid: list[PostInput] = []
    rejected: list[Rejection] = []
    seen: set[int] = set()
    duplicates = 0
    for raw in records:
        source_id = raw.get("id") if isinstance(raw.get("id"), int) else None
        try:
            item = PostInput.model_validate(raw)
            if item.id in seen:
                duplicates += 1
                rejected.append(Rejection(run_id, item.id, "duplicate_source_id", "Duplicate ID within input", raw_payload=raw))
                continue
            seen.add(item.id)
            valid.append(item)
        except ValidationError as exc:
            rejected.append(Rejection(run_id, source_id, "schema_validation", str(exc), raw_payload=raw))
    return valid, rejected, duplicates
