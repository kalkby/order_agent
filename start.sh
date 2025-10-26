#!/usr/bin/env bash
# start.sh — used to start the app (reads PORT from environment)
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
