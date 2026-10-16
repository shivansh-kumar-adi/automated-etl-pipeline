"""Transactional PostgreSQL UPSERT loading."""
from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection


def load_posts(connection: Connection, posts: list[dict[str, Any]]) -> tuple[int, int]:
    """Upsert posts and return (inserted, updated), counting unchanged as updates/seen."""
    statement = text("""
        INSERT INTO posts (id, user_id, title, body, created_at, updated_at)
        VALUES (:id, :user_id, :title, :body, :ingested_at, :last_seen_at)
        ON CONFLICT (id) DO UPDATE SET
          user_id = EXCLUDED.user_id,
          title = EXCLUDED.title,
          body = EXCLUDED.body,
          updated_at = EXCLUDED.updated_at
        RETURNING (xmax = 0) AS inserted
    """)
    inserted = updated = 0
    for post in posts:
        was_inserted = bool(connection.execute(statement, post).scalar_one())
        inserted += int(was_inserted)
        updated += int(not was_inserted)
    return inserted, updated


def destination_count(connection: Connection, source_ids: list[int]) -> int:
    if not source_ids:
        return 0
    return int(connection.execute(text("SELECT COUNT(*) FROM posts WHERE id = ANY(:ids)"), {"ids": source_ids}).scalar_one())
