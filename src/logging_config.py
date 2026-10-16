"""Console and rotating-file logging."""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


class RunContext(logging.Filter):
    def __init__(self, run_id: str) -> None:
        super().__init__()
        self.run_id = run_id

    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = getattr(record, "run_id", self.run_id)
        return True


def configure_logging(log_dir: Path, level: str, run_id: str) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / "pipeline.log"
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s run_id=%(run_id)s logger=%(name)s %(message)s"
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    for handler in (
        logging.StreamHandler(),
        RotatingFileHandler(path, maxBytes=2_000_000, backupCount=5, encoding="utf-8"),
    ):
        handler.setFormatter(formatter)
        handler.addFilter(RunContext(run_id))
        root.addHandler(handler)
    return path
