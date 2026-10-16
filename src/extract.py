"""HTTP and file/synthetic extraction."""
from __future__ import annotations

import logging
from typing import Any

import requests
from tenacity import Retrying, retry_if_exception, stop_after_attempt, wait_exponential

LOGGER = logging.getLogger(__name__)


class TransientExtractionError(RuntimeError):
    """An extraction failure that is safe to retry."""


def _retryable(exc: BaseException) -> bool:
    return isinstance(exc, (requests.ConnectionError, requests.Timeout, TransientExtractionError))


def extract_posts(
    url: str,
    timeout: float = 10.0,
    attempts: int = 3,
    session: requests.Session | None = None,
) -> list[dict[str, Any]]:
    """Fetch JSONPlaceholder posts, retrying only transient failures."""
    client = session or requests.Session()
    retrying = Retrying(
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(multiplier=0.25, min=0.25, max=4),
        retry=retry_if_exception(_retryable),
        reraise=True,
        before_sleep=lambda state: LOGGER.warning(
            "retrying API request attempt=%s error=%s",
            state.attempt_number + 1,
            state.outcome.exception() if state.outcome else "unknown",
        ),
    )
    for attempt in retrying:
        with attempt:
            LOGGER.info("requesting source attempt=%s url=%s", attempt.retry_state.attempt_number, url)
            response = client.get(url, timeout=timeout)
            if response.status_code == 429 or 500 <= response.status_code < 600:
                raise TransientExtractionError(f"transient HTTP {response.status_code}")
            response.raise_for_status()
            try:
                payload = response.json()
            except ValueError as exc:
                raise ValueError("API returned malformed JSON") from exc
            if not isinstance(payload, list):
                raise ValueError("API response must be a JSON array")
            if not all(isinstance(item, dict) for item in payload):
                raise ValueError("API response contains non-object records")
            LOGGER.info("fetched records=%s", len(payload))
            return payload
    raise AssertionError("retry loop exited unexpectedly")
