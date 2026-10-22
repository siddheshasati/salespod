from __future__ import annotations

import argparse
from pathlib import Path

from salespod.config import Settings
from salespod.infrastructure.seed.generator import seed_database


def main() -> None:
    settings = Settings.from_env()
    parser = argparse.ArgumentParser(description="Generate the deterministic Sales Pod CRM fixture")
    parser.add_argument("--database-url", default=settings.database_url)
    parser.add_argument("--seed", type=int, default=settings.seed)
    parser.add_argument("--as-of", default=settings.dataset_as_of.isoformat())
    parser.add_argument("--truth-output", default="data/ground_truth.json")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    from datetime import datetime

    as_of = datetime.fromisoformat(args.as_of.replace("Z", "+00:00"))
    result = seed_database(
        args.database_url,
        seed=args.seed,
        as_of=as_of,
        reset=args.reset,
        truth_output=Path(args.truth_output),
    )
    print(f"Seeded {args.database_url}")
    print(f"Counts: {result.counts}")
    print(f"Manifest hash: {result.truth_manifest['content_hash']}")


if __name__ == "__main__":
    main()
