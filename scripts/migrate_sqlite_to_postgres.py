from __future__ import annotations

import os
import sys
from typing import Any

from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import Engine

from app import models  # noqa: F401
from app.database import Base


def _env(name: str, default: str | None = None) -> str:
    v = os.getenv(name, default)
    if v is None or not str(v).strip():
        raise SystemExit(f"Missing env var: {name}")
    return str(v).strip()


def _engine(url: str) -> Engine:
    # Keep it simple; rely on URL driver config.
    return create_engine(url, pool_pre_ping=True)


def _disable_fks_pg(dst: Engine) -> None:
    # Speeds up bulk inserts while keeping data consistent as we insert in dependency order.
    with dst.begin() as c:
        c.execute(text("SET session_replication_role = replica;"))


def _enable_fks_pg(dst: Engine) -> None:
    with dst.begin() as c:
        c.execute(text("SET session_replication_role = DEFAULT;"))


def _truncate_all_pg(dst: Engine) -> None:
    # Danger: wipes destination. Use only for fresh migrations.
    tables = [t.name for t in reversed(Base.metadata.sorted_tables)]
    if not tables:
        return
    with dst.begin() as c:
        joined = ", ".join(f'"{t}"' for t in tables)
        c.execute(text(f"TRUNCATE TABLE {joined} RESTART IDENTITY CASCADE;"))


def _copy_table(src: Engine, dst: Engine, table_name: str, batch_size: int = 2000) -> int:
    table = Base.metadata.tables[table_name]

    total = 0
    with src.connect() as sc, dst.begin() as dc:
        rows = sc.execute(select(table)).mappings().all()
        if not rows:
            return 0

        # Insert in batches.
        for i in range(0, len(rows), batch_size):
            chunk = rows[i : i + batch_size]
            dc.execute(table.insert(), list(chunk))
            total += len(chunk)
    return total


def main() -> int:
    """
    Migrate panel data from SQLite to Postgres.

    Usage:
      export SRC_DATABASE_URL='sqlite:////opt/nofal-panel/nofal_panel.db'
      export DST_DATABASE_URL='postgresql+psycopg2://user:pass@127.0.0.1:5432/nofal_panel'
      /opt/nofal-panel/venv/bin/python scripts/migrate_sqlite_to_postgres.py
    """

    src_url = _env("SRC_DATABASE_URL")
    dst_url = _env("DST_DATABASE_URL")

    if not src_url.startswith("sqlite:"):
        raise SystemExit("SRC_DATABASE_URL must be sqlite://…")
    if not dst_url.startswith("postgres"):
        raise SystemExit("DST_DATABASE_URL must be postgres://…")

    src = _engine(src_url)
    dst = _engine(dst_url)

    # Ensure destination schema exists.
    Base.metadata.create_all(bind=dst)

    # Safety: allow explicit wipe.
    wipe = os.getenv("WIPE_DST", "0").strip() in ("1", "true", "yes")
    if wipe:
        print("[!] WIPE_DST enabled: truncating destination tables...")
        _disable_fks_pg(dst)
        _truncate_all_pg(dst)
        _enable_fks_pg(dst)

    print("[*] Migrating tables...")
    _disable_fks_pg(dst)
    try:
        # Copy in metadata order (parents first).
        for t in Base.metadata.sorted_tables:
            n = _copy_table(src, dst, t.name)
            print(f"  - {t.name}: {n} rows")
    finally:
        _enable_fks_pg(dst)

    print("[OK] Migration complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

