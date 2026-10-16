from unittest.mock import Mock

import pytest
import requests

from src.extract import extract_posts


def response(status=200, payload=None, json_error=None):
    item = Mock(status_code=status)
    item.raise_for_status.side_effect = requests.HTTPError(str(status)) if status >= 400 else None
    item.json.side_effect = json_error
    if json_error is None:
        item.json.return_value = payload
    return item


def test_successful_and_empty_extraction(valid_records):
    session = Mock()
    session.get.return_value = response(payload=valid_records)
    assert extract_posts("http://test", session=session) == valid_records
    session.get.return_value = response(payload=[])
    assert extract_posts("http://test", session=session) == []


def test_connection_failure_retries_then_succeeds(valid_records):
    session = Mock()
    session.get.side_effect = [requests.ConnectionError("down"), response(payload=valid_records)]
    assert len(extract_posts("http://test", attempts=2, session=session)) == 2
    assert session.get.call_count == 2


def test_transient_http_retries():
    session = Mock()
    session.get.side_effect = [response(503), response(payload=[])]
    assert extract_posts("http://test", attempts=2, session=session) == []


def test_permanent_http_error_is_not_retried():
    session = Mock()
    session.get.return_value = response(404)
    with pytest.raises(requests.HTTPError):
        extract_posts("http://test", attempts=3, session=session)
    assert session.get.call_count == 1


def test_malformed_or_unexpected_payload():
    session = Mock()
    session.get.return_value = response(json_error=ValueError("bad"))
    with pytest.raises(ValueError, match="malformed"):
        extract_posts("http://test", session=session)
    session.get.return_value = response(payload={"not": "a list"})
    with pytest.raises(ValueError, match="array"):
        extract_posts("http://test", session=session)
