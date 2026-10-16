"""Run the ETL pipeline from the command line."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import text

from src.config import ROOT, Settings
from src.database import initialize_database, make_engine
from src.extract import extract_posts
from src.logging_config import configure_logging
from src.pipeline import run_pipeline
from src.synthetic import generate_records


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the automated ETL pipeline")
    parser.add_argument("--source", choices=("jsonplaceholder", "synthetic"), default="jsonplaceholder")
    parser.add_argument("--records", type=int, default=1000)
    parser.add_argument("--scenario", choices=("valid", "mixed"), default="valid")
    args = parser.parse_args()
    settings = Settings.from_env()
    engine = make_engine(settings.database_url)
    initialize_database(engine, ROOT / "sql" / "schema.sql")
    configure_logging(settings.log_dir, settings.log_level, "startup")
    if args.source == "synthetic":
        records = generate_records(args.records, args.scenario)
        extractor = None
    else:
        records = None
        extractor = lambda: extract_posts(settings.api_url, settings.request_timeout, settings.retry_count)
    run_id, counts, result, report = run_pipeline(engine, args.source, settings.report_dir, records, extractor)
    print(f"Run ID: {run_id}\nStatus: {result.status}\nCounts: {counts}\nReport: {report}")
    return 0 if result.status == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
