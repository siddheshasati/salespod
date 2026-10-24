from __future__ import annotations

import argparse

from salespod.config import Settings
from salespod.infrastructure.db.session import migrate_database


def main() -> None:
    settings = Settings.from_env()
    parser = argparse.ArgumentParser(
        description="Upgrade the Sales Pod database to the latest schema"
    )
    parser.add_argument("--database-url", default=settings.database_url)
    args = parser.parse_args()
    Settings(database_url=args.database_url).ensure_database_parent()
    migrate_database(args.database_url)
    print(f"Migrated {args.database_url} to head")


if __name__ == "__main__":
    main()
