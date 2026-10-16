"""Deterministic transformations."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from .validate import PostInput


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def transform_post(post: PostInput, ingested_at: datetime) -> dict[str, Any]:
    return {
        "id": post.id,
        "user_id": post.userId,
        "title": normalize_text(post.title),
        "body": normalize_text(post.body),
        "ingested_at": ingested_at,
        "last_seen_at": ingested_at,
    }
