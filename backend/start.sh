#!/bin/sh
# Запуск backend: сначала миграции Alembic, затем сервер.
set -e
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 \
    --proxy-headers --forwarded-allow-ips='*' --no-access-log --no-server-header
