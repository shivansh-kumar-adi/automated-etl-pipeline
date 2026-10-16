"""Display the latest database run summary."""
from sqlalchemy import text

from src.config import Settings
from src.database import make_engine


def main() -> None:
    with make_engine(Settings.from_env().database_url).connect() as connection:
        row = connection.execute(text("SELECT * FROM pipeline_runs ORDER BY started_at DESC LIMIT 1")).mappings().first()
    print(dict(row) if row else "No pipeline runs found.")


if __name__ == "__main__":
    main()
