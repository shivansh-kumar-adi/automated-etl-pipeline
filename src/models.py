"""Shared domain models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Rejection:
    run_id: str
    source_id: int | None
    reason: str
    details: str
    rejected_at: datetime = field(default_factory=utcnow)
    raw_payload: dict[str, Any] | None = None


@dataclass
class RunCounts:
    extracted: int = 0
    staged: int = 0
    accepted: int = 0
    rejected: int = 0
    inserted: int = 0
    updated: int = 0
    duplicates: int = 0
    load_failures: int = 0
    destination_unique: int = 0
