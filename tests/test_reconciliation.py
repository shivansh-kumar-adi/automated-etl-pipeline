from src.models import RunCounts
from src.reconcile import reconcile


def test_reconciliation_pass():
    counts = RunCounts(extracted=3, staged=3, accepted=2, rejected=1, inserted=1, updated=1, duplicates=0, destination_unique=2)
    assert reconcile(counts).status == "PASS"


def test_reconciliation_fail_for_mismatch():
    result = reconcile(RunCounts(extracted=3, staged=2, accepted=3, destination_unique=0))
    assert result.status == "FAIL"
    assert "staged" in result.details


def test_reconciliation_accounts_for_duplicate_not_repeated_in_staging():
    counts = RunCounts(extracted=3, staged=2, accepted=1, rejected=2, inserted=1, duplicates=1, destination_unique=1)
    assert reconcile(counts).status == "PASS"
