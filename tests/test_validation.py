from src.validate import validate_records


def test_valid_records_are_accepted(valid_records):
    valid, rejected, duplicates = validate_records(valid_records, "run")
    assert len(valid) == 2
    assert rejected == []
    assert duplicates == 0


def test_missing_and_invalid_fields_are_rejected():
    records = [{"id": 1, "userId": 1, "body": "x"}, {"id": 2, "userId": "1", "title": "x", "body": "y"}]
    valid, rejected, _ = validate_records(records, "run")
    assert not valid
    assert len(rejected) == 2
    assert all(item.reason == "schema_validation" for item in rejected)
    assert "title" in rejected[0].details


def test_empty_text_and_bad_identifier_are_rejected():
    records = [{"id": 0, "userId": 1, "title": " ", "body": "x"}]
    _, rejected, _ = validate_records(records, "run")
    assert rejected[0].source_id == 0


def test_duplicate_identifier_is_rejected(valid_records):
    valid, rejected, duplicates = validate_records(valid_records + [dict(valid_records[0])], "run")
    assert len(valid) == 2
    assert duplicates == 1
    assert rejected[0].reason == "duplicate_source_id"
