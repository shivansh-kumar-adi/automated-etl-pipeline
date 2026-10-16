"""Environment-backed application configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    database_url: str
    api_url: str = "https://jsonplaceholder.typicode.com/posts"
    request_timeout: float = 10.0
    retry_count: int = 3
    log_level: str = "INFO"
    batch_size: int = 250
    report_dir: Path = ROOT / "reports"
    log_dir: Path = ROOT / "logs"

    @classmethod
    def from_env(cls, require_database: bool = True) -> "Settings":
        load_dotenv(ROOT / ".env")
        direct = os.getenv("DATABASE_URL", "").strip()
        if direct:
            url = direct
        else:
            required = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]
            missing = [key for key in required if not os.getenv(key)]
            if missing and require_database:
                raise ValueError(
                    "Missing database configuration: " + ", ".join(missing)
                    + ". Copy .env.example to .env and fill in the values."
                )
            url = "postgresql+psycopg://{user}:{password}@{host}:{port}/{name}".format(
                user=os.getenv("DB_USER", "etl_user"),
                password=os.getenv("DB_PASSWORD", ""),
                host=os.getenv("DB_HOST", "localhost"),
                port=os.getenv("DB_PORT", "5432"),
                name=os.getenv("DB_NAME", "etl_pipeline"),
            )
        return cls(
            database_url=url,
            api_url=os.getenv("API_URL", cls.api_url),
            request_timeout=float(os.getenv("REQUEST_TIMEOUT", "10")),
            retry_count=max(1, int(os.getenv("RETRY_COUNT", "3"))),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            batch_size=max(1, int(os.getenv("BATCH_SIZE", "250"))),
        )
