from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text


def main() -> int:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not set; nothing to migrate.")
        return 0
    engine = create_engine(db_url)
    sql_path = Path(__file__).with_name("migrations") / "0001_init.sql"
    sql = sql_path.read_text()
    with engine.begin() as conn:
        for stmt in filter(None, (s.strip() for s in sql.split(";"))):
            conn.execute(text(stmt))
    print("Migrations applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

