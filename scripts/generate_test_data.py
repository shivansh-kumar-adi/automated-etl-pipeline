"""Generate deterministic synthetic JSON records."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.synthetic import generate_records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=int, default=1000)
    parser.add_argument("--scenario", choices=("valid", "mixed"), default="valid")
    parser.add_argument("--output", type=Path, default=Path("data/synthetic_posts.json"))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(generate_records(args.records, args.scenario), indent=2), encoding="utf-8")
    print(f"Wrote {args.records} deterministic {args.scenario} records to {args.output}")


if __name__ == "__main__":
    main()
