"""Deterministic synthetic post generation."""
from __future__ import annotations

from typing import Any


def generate_records(count: int, scenario: str = "valid") -> list[dict[str, Any]]:
    if count < 1:
        raise ValueError("count must be positive")
    records: list[dict[str, Any]] = [
        {"id": 1_000_000 + i, "userId": (i % 100) + 1, "title": f"Synthetic post {i + 1}", "body": f"Deterministic body for record {i + 1}."}
        for i in range(count)
    ]
    if scenario == "mixed" and count >= 4:
        records[1].pop("title")
        records[2]["userId"] = "invalid"
        records[3] = dict(records[0])
    elif scenario != "valid":
        raise ValueError("scenario must be 'valid' or 'mixed'")
    return records
