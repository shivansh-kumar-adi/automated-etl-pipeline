from src.synthetic import generate_records
from src.validate import validate_records


def test_1000_synthetic_records_are_deterministic_and_unique():
    first = generate_records(1000)
    second = generate_records(1000)
    assert first == second
    assert len({item["id"] for item in first}) == 1000


def test_mixed_scenario_produces_rejections_and_duplicate():
    records = generate_records(10, "mixed")
    valid, rejected, duplicates = validate_records(records, "run")
    assert len(valid) == 7
    assert len(rejected) == 3
    assert duplicates == 1
