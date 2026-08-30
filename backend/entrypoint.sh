#!/bin/sh
set -e

echo "Waiting for database..."
until pg_isready -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "${DB_USER:-chumber}" >/dev/null 2>&1; do
  sleep 1
done

alembic upgrade head

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
