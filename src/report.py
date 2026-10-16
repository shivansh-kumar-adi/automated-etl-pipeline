"""CSV reconciliation reporting."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from .models import RunCounts
from .reconcile import ReconciliationResult


def write_report(report_dir: Path, run_id: str, source: str, started_at: datetime, ended_at: datetime, counts: RunCounts, result: ReconciliationResult) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"reconciliation_{run_id}.csv"
    row = {
        "run_id": run_id, "run_start": started_at.isoformat(), "run_end": ended_at.isoformat(),
        "source_name": source, "extraction_count": counts.extracted, "staging_count": counts.staged,
        "accepted_count": counts.accepted, "rejected_count": counts.rejected, "inserted_count": counts.inserted,
        "updated_count": counts.updated, "duplicate_count": counts.duplicates, "load_failure_count": counts.load_failures,
        "destination_unique_count": counts.destination_unique, "reconciliation_status": result.status,
        "details": result.details,
    }
    pd.DataFrame([row]).to_csv(path, index=False)
    return path
