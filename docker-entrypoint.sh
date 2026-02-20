#!/bin/sh
set -e

echo "Waiting for PostgreSQL to be ready..."
sleep 10

if [ "${SKIP_CHECKPOINT_SETUP}" != "1" ]; then
  echo "Initializing checkpoint tables..."
  python -c "from backend.db.setup_checkpoints import main; main()"
else
  echo "Skipping checkpoint table initialization"
fi

echo "Starting application..."
exec "$@"
