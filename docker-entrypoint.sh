#!/bin/bash
set -e

echo "Waiting for PostgreSQL to be ready..."
sleep 10

echo "Initializing checkpoint tables..."
python -c "from backend.db.setup_checkpoints import main; main()"

echo "Starting application..."
exec "$@"
