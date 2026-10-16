"""Opt-in PostgreSQL integration tests; skipped unless TEST_DATABASE_URL is set."""
import os
from pathlib import Path

import pytest
from sqlalchemy import text

from src.database import initialize_database, make_engine
from src.pipeline import run_pipeline
from src.synthetic import generate_records


@pytest.mark.integration
def test_end_to_end_idempotency_and_update(tmp_path):
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to a dedicated disposable PostgreSQL database")
    if "test" not in url.lower():
        pytest.fail("TEST_DATABASE_URL must visibly name a test database")
    engine = make_engine(url)
    initialize_database(engine, Path(__file__).parents[1] / "sql" / "schema.sql")
    records = generate_records(10)
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE rejected_records, staging_posts, posts, pipeline_runs RESTART IDENTITY CASCADE"))
    _, first, result, _ = run_pipeline(engine, "synthetic", tmp_path, records=records)
    assert result.status == "PASS" and first.inserted == 10
    _, second, result, _ = run_pipeline(engine, "synthetic", tmp_path, records=records)
    assert result.status == "PASS" and second.inserted == 0 and second.updated == 10
    records[0]["title"] = "Changed title"
    run_pipeline(engine, "synthetic", tmp_path, records=records)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT title FROM posts WHERE id=:id"), {"id": records[0]["id"]}).scalar_one() == "Changed title"
