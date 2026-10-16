from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture
def valid_records() -> list[dict[str, Any]]:
    return [
        {"id": 1, "userId": 1, "title": " First  title ", "body": "Body\ntext"},
        {"id": 2, "userId": 1, "title": "Second", "body": "Another body"},
    ]
