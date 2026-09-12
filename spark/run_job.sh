#!/usr/bin/env bash
# Submit a PySpark job (from ./spark/jobs) to the local standalone cluster, with MinIO
# (s3a://) wired up. Usage: ./spark/run_job.sh bronze_to_silver.py [-- extra spark-submit args]
#
# Also callable from inside the Airflow worker container (Docker-outside-of-Docker): that
# container talks to the HOST's Docker daemon via the mounted socket, so `docker compose`
# must be pointed at the compose file's real HOST path -- a container-internal path like
# /opt/project means nothing to the daemon. Set COMPOSE_FILE to override the default.
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

COMPOSE_FILE="${COMPOSE_FILE:-$PROJECT_ROOT/docker-compose.yml}"

JOB_FILE="$1"
shift || true

# The worker can end up "alive" (container running, JVM up) but orphaned from the master's
# in-memory registry -- observed after the host sleeps mid-run: the worker's heartbeat thread
# freezes along with everything else, the master's wall-clock 60s timeout evicts it the moment
# things resume, and the worker's own reconnect logic occasionally never notices. Symptom: the
# master's REST API reports aliveworkers=0 while the worker container looks perfectly healthy,
# and any submitted job just sits in WAITING forever (no executors, no error, no timeout).
# Docker has no restart policy or healthcheck that would ever catch this, since the worker
# process never actually exits -- so we check for it explicitly before every submission and
# self-heal by restarting the worker, which forces a clean re-registration.
#
# Runs the query as a throwaway container on the same compose network as spark-submit itself
# (rather than the host-mapped port), since this script may be executing inside the Airflow
# worker container where "localhost:8080" doesn't reach it.
alive_workers() {
  docker compose -f "$COMPOSE_FILE" run --rm --entrypoint sh spark-master -c \
    'python3 -c "import json,urllib.request; print(json.load(urllib.request.urlopen(\"http://spark-master:8080/json/\", timeout=5)).get(\"aliveworkers\", 0))"' \
    2>/dev/null
}

is_number() { case "$1" in '' | *[!0-9]*) return 1 ;; *) return 0 ;; esac; }

ensure_worker_alive() {
  local workers
  workers="$(alive_workers)"
  if is_number "$workers" && [ "$workers" -ge 1 ]; then
    return 0
  fi

  echo "[run_job.sh] spark-master reports 0 alive workers -- worker likely got orphaned" >&2
  echo "[run_job.sh] (see README's Spark section). Restarting spark-worker to self-heal..." >&2
  docker compose -f "$COMPOSE_FILE" restart spark-worker >&2

  local attempt
  for attempt in 1 2 3 4 5 6; do
    sleep 5
    workers="$(alive_workers)"
    if is_number "$workers" && [ "$workers" -ge 1 ]; then
      echo "[run_job.sh] Worker re-registered after restart (${attempt}x5s). Continuing." >&2
      return 0
    fi
  done

  echo "[run_job.sh] ERROR: spark-worker still not registered 30s after restart." >&2
  echo "[run_job.sh] Failing this task cleanly so Airflow's retry policy can take over." >&2
  return 1
}

ensure_worker_alive

# Named volumes are created root-owned; the spark image runs as uid 185, so the
# ivy dependency cache needs its permissions fixed before spark-submit can write to it.
docker compose -f "$COMPOSE_FILE" run --rm --user root --entrypoint sh spark-master \
  -c "mkdir -p /opt/ivy-cache && chown -R 185:185 /opt/ivy-cache" >/dev/null

docker compose -f "$COMPOSE_FILE" run --rm -e PYTHONUNBUFFERED=1 spark-master /opt/spark/bin/spark-submit \
  --master spark://spark-master:7077 \
  --packages org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262,org.postgresql:postgresql:42.7.4 \
  --conf spark.jars.ivy=/opt/ivy-cache \
  --conf spark.hadoop.fs.s3a.endpoint="http://minio:9000" \
  --conf spark.hadoop.fs.s3a.access.key="$MINIO_ROOT_USER" \
  --conf spark.hadoop.fs.s3a.secret.key="$MINIO_ROOT_PASSWORD" \
  --conf spark.hadoop.fs.s3a.path.style.access=true \
  --conf spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem \
  --conf spark.hadoop.fs.s3a.connection.ssl.enabled=false \
  --conf spark.sql.shuffle.partitions=4 \
  "/opt/spark-jobs/$JOB_FILE" "$@"
