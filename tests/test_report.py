from datetime import datetime, timezone

import pandas as pd

from src.models import RunCounts
from src.reconcile import ReconciliationResult
from src.report import write_report


def test_csv_report_generation(tmp_path):
    now = datetime.now(timezone.utc)
    path = write_report(tmp_path, "abc", "synthetic", now, now, RunCounts(), ReconciliationResult("PASS", "ok"))
    frame = pd.read_csv(path)
    assert frame.loc[0, "run_id"] == "abc"
    assert frame.loc[0, "reconciliation_status"] == "PASS"
