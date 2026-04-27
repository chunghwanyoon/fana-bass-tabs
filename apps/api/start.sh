#!/usr/bin/env bash
# 단일 컨테이너에서 arq 워커 (백그라운드) + uvicorn API (포그라운드) 동시 실행
set -e

arq api.worker.WorkerSettings &
WORKER_PID=$!

trap "kill $WORKER_PID 2>/dev/null || true" EXIT

exec uvicorn api.main:app --app-dir /app/src --host 0.0.0.0 --port 8000
