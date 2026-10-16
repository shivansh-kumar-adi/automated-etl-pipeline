"""Count-based reconciliation rules."""
from __future__ import annotations

from dataclasses import dataclass

from .models import RunCounts


@dataclass(frozen=True)
class ReconciliationResult:
    status: str
    details: str


def reconcile(counts: RunCounts) -> ReconciliationResult:
    failures: list[str] = []
    if counts.extracted != counts.accepted + counts.rejected:
        failures.append("extracted must equal accepted + rejected")
    if counts.staged + counts.duplicates != counts.extracted:
        failures.append("staged + duplicate source IDs must equal extracted")
    if counts.inserted + counts.updated + counts.load_failures != counts.accepted:
        failures.append("inserted + updated + load_failures must equal accepted")
    if counts.destination_unique != counts.accepted - counts.load_failures:
        failures.append("destination unique count does not match successfully loaded unique input")
    if counts.duplicates > counts.rejected:
        failures.append("duplicates cannot exceed rejected records")
    return ReconciliationResult("FAIL", "; ".join(failures)) if failures else ReconciliationResult("PASS", "All reconciliation invariants satisfied")
