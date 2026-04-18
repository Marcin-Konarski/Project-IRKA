#!/bin/bash
set -e # (exit immediately if any command fails)
echo "Running migrations..."
python -m alembic upgrade head # Run migrations
exec "$@"