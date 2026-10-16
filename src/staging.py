"""Persistence for raw staging records and rejections."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from .models import Rejection


def stage_records(connection: Connection, records: list[dict[str, Any]], run_id: str, extracted_at: datetime) -> int:
    statement = text("""
        INSERT INTO staging_posts
          (run_id, source_id, raw_payload, extracted_at, validation_status, processing_status)
        VALUES
          (:run_id, :source_id, CAST(:raw_payload AS jsonb), :extracted_at, 'pending', 'staged')
        ON CONFLICT (run_id, source_id) DO NOTHING
    """)
    import json
    count = 0
    for index, record in enumerate(records):
        # Negative surrogate keeps malformed/missing IDs auditable without collision.
        source_id = record.get("id") if isinstance(record.get("id"), int) else -(index + 1)
        result = connection.execute(statement, {"run_id": run_id, "source_id": source_id, "raw_payload": json.dumps(record), "extracted_at": extracted_at})
        count += result.rowcount
    return count


def update_validation_status(connection: Connection, run_id: str, valid_ids: set[int]) -> None:
    connection.execute(text("UPDATE staging_posts SET validation_status='rejected', processing_status='complete' WHERE run_id=:run_id"), {"run_id": run_id})
    if valid_ids:
        connection.execute(text("UPDATE staging_posts SET validation_status='valid' WHERE run_id=:run_id AND source_id = ANY(:ids)"), {"run_id": run_id, "ids": list(valid_ids)})


def save_rejections(connection: Connection, rejections: list[Rejection]) -> int:
    statement = text("""
        INSERT INTO rejected_records (run_id, source_id, reason, details, rejected_at)
        VALUES (:run_id, :source_id, :reason, :details, :rejected_at)
    """)
    for rejection in rejections:
        connection.execute(statement, {"run_id": rejection.run_id, "source_id": rejection.source_id, "reason": rejection.reason, "details": rejection.details[:4000], "rejected_at": rejection.rejected_at})
    return len(rejections)
