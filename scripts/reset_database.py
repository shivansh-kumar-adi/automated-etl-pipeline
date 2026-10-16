"""Safely clear only the configured ETL database tables."""
import argparse

from sqlalchemy import text

from src.config import Settings
from src.database import make_engine


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true", help="Required destructive-action confirmation")
    args = parser.parse_args()
    if not args.confirm:
        raise SystemExit("Refusing to reset. Re-run with --confirm after checking .env.")
    answer = input("Type RESET ETL to truncate only ETL project tables: ")
    if answer != "RESET ETL":
        raise SystemExit("Cancelled.")
    with make_engine(Settings.from_env().database_url).begin() as connection:
        connection.execute(text("TRUNCATE rejected_records, staging_posts, posts, pipeline_runs RESTART IDENTITY CASCADE"))
    print("ETL project tables reset.")


if __name__ == "__main__":
    main()
