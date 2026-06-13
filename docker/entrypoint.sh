#!/usr/bin/env bash
set -euo pipefail

ROLE="${ROLE:-web}"

case "$ROLE" in
  web)
    echo "[entrypoint] starting web (FastAPI)"
    exec gunicorn app.main:app \
      --worker-class uvicorn.workers.UvicornWorker \
      --bind "0.0.0.0:${PORT:-8000}" \
      --workers "${WEB_CONCURRENCY:-2}"
    ;;
  worker)
    echo "[entrypoint] starting worker (async run consumer)"
    exec python -m app.workers
    ;;
  *)
    echo "[entrypoint] unknown ROLE='$ROLE' (expected: web | worker)" >&2
    exit 1
    ;;
esac
