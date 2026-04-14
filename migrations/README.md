# Migrations

This folder contains Alembic database migrations.

## Usage

- Using SQLite (dev):

```bash
./venv/bin/alembic upgrade head
```

- Using Postgres (prod):

```bash
export DATABASE_URL='postgresql+psycopg2://user:pass@host:5432/nofal_panel'
./venv/bin/alembic upgrade head
```

