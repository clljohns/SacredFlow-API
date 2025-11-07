# SacredFlow Chat Backend

Lightweight FastAPI service that stores Sacred Guide conversations in PostgreSQL.

## Requirements

- Python 3.11+
- PostgreSQL 13+

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # update DATABASE_URL and BACKEND_CORS_ORIGINS
```

### Database

Run the SQL in `migrations/README.md` or initialize Alembic and run `alembic upgrade head`.

## Development

```bash
uvicorn backend.app:app --reload --port 8000
```

CORS is allowed for `http://localhost:5173` by default. Update `BACKEND_CORS_ORIGINS` with a comma-separated list for production.

## Environment variables

- `DATABASE_URL` – `postgresql+psycopg2://user:pass@host:5432/dbname`
- `BACKEND_CORS_ORIGINS` – e.g. `http://localhost:5173,https://malulani.co`
- `SECRET_KEY` – reserved for future auth extensions.
