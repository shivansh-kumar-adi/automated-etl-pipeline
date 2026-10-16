"""End-to-end pipeline orchestration."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import text
from sqlalchemy.engine import Engine

from .extract import extract_posts
from .load import destination_count, load_posts
from .models import RunCounts
from .reconcile import ReconciliationResult, reconcile
from .report import write_report
from .staging import save_rejections, stage_records, update_validation_status
from .transform import transform_post
from .validate import validate_records

LOGGER = logging.getLogger(__name__)


def run_pipeline(engine: Engine, source: str, report_dir: Path, records: list[dict[str, Any]] | None = None, extractor: Callable[[], list[dict[str, Any]]] | None = None) -> tuple[str, RunCounts, ReconciliationResult, Path]:
    run_id = str(uuid.uuid4())
    started = datetime.now(timezone.utc)
    counts = RunCounts()
    LOGGER.info("pipeline started source=%s", source)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO pipeline_runs (run_id, source_name, started_at, status) VALUES (:id, :source, :started, 'RUNNING')"), {"id": run_id, "source": source, "started": started})
    try:
        raw = records if records is not None else (extractor or extract_posts)()
        counts.extracted = len(raw)
        valid, rejected, counts.duplicates = validate_records(raw, run_id)
        counts.accepted, counts.rejected = len(valid), len(rejected)
        transformed = [transform_post(item, started) for item in valid]
        with engine.begin() as connection:
            counts.staged = stage_records(connection, raw, run_id, started)
            update_validation_status(connection, run_id, {item.id for item in valid})
            save_rejections(connection, rejected)
            counts.inserted, counts.updated = load_posts(connection, transformed)
            counts.destination_unique = destination_count(connection, [item.id for item in valid])
            connection.execute(text("UPDATE staging_posts SET processing_status='loaded' WHERE run_id=:id AND validation_status='valid'"), {"id": run_id})
        result = reconcile(counts)
        ended = datetime.now(timezone.utc)
        report = write_report(report_dir, run_id, source, started, ended, counts, result)
        with engine.begin() as connection:
            connection.execute(text("""UPDATE pipeline_runs SET ended_at=:ended, status=:status, extraction_count=:extracted, staging_count=:staged, accepted_count=:accepted, rejected_count=:rejected, inserted_count=:inserted, updated_count=:updated, duplicate_count=:duplicates, load_failure_count=:failures, destination_unique_count=:destination, reconciliation_details=:details WHERE run_id=:id"""), {"ended": ended, "status": result.status, "extracted": counts.extracted, "staged": counts.staged, "accepted": counts.accepted, "rejected": counts.rejected, "inserted": counts.inserted, "updated": counts.updated, "duplicates": counts.duplicates, "failures": counts.load_failures, "destination": counts.destination_unique, "details": result.details, "id": run_id})
        LOGGER.info("pipeline finished status=%s counts=%s", result.status, counts)
        return run_id, counts, result, report
    except Exception as exc:
        LOGGER.exception("pipeline failed")
        ended = datetime.now(timezone.utc)
        try:
            with engine.begin() as connection:
                connection.execute(text("UPDATE pipeline_runs SET ended_at=:ended, status='FAIL', reconciliation_details=:details WHERE run_id=:id"), {"ended": ended, "details": f"Pipeline error: {type(exc).__name__}: {exc}"[:4000], "id": run_id})
        except Exception:
            LOGGER.exception("could not update failed run history")
        raise
