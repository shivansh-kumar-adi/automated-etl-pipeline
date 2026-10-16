"""SQLAlchemy engine and schema initialization."""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def make_engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True, future=True)


def initialize_database(engine: Engine, schema_path: Path) -> None:
    sql = schema_path.read_text(encoding="utf-8")
    with engine.begin() as connection:
        # Psycopg's extended protocol accepts one statement at a time.
        # This schema intentionally contains no procedural blocks with embedded semicolons.
        for statement in (part.strip() for part in sql.split(";")):
            if statement:
                connection.execute(text(statement))
