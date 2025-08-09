#!/usr/bin/env bash
set -euo pipefail

# Не source .env: docker-compose сам прокидывает env, а Python читает .env через python-dotenv

DB_HOST=${DB_HOST:-db}
DB_PORT=${DB_PORT:-5432}

echo "[entrypoint] Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."
until pg_isready -h "$DB_HOST" -p "$DB_PORT" >/dev/null 2>&1; do
  sleep 1
done
echo "[entrypoint] PostgreSQL is ready. Starting bot..."

exec python -m src


