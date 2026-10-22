#!/usr/bin/env bash
# start.sh — production startup script for KalaKatte backend
# Run as: bash start.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Generate a random secret key if one isn't set
if [ -z "$KK_SECRET_KEY" ]; then
  export KK_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  echo "[KalaKatte] Warning: KK_SECRET_KEY not set. Generated a random one for this session."
  echo "[KalaKatte] Set it permanently in /etc/environment or ~/.bashrc to avoid logging out all users on restart:"
  echo "  export KK_SECRET_KEY=$KK_SECRET_KEY"
fi

echo "[KalaKatte] Starting gunicorn on 0.0.0.0:8000 ..."
exec gunicorn main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 2 \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile - \
  --log-level info
