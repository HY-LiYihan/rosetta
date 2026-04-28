#!/usr/bin/env bash
set -euo pipefail

ROSETTA_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ -f "${ROSETTA_REPO_ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${ROSETTA_REPO_ROOT}/.env"
  set +a
fi

ROSETTA_APP_DIR="${ROSETTA_APP_DIR:-${ROSETTA_REPO_ROOT}}"
ROSETTA_RUNTIME_DIR="${ROSETTA_RUNTIME_DIR:-/opt/rosetta/runtime}"
ROSETTA_DATA_DIR="${ROSETTA_DATA_DIR:-${ROSETTA_RUNTIME_DIR}/data}"
ROSETTA_BACKUP_DIR="${ROSETTA_BACKUP_DIR:-${ROSETTA_RUNTIME_DIR}/backups}"
ROSETTA_LOG_DIR="${ROSETTA_LOG_DIR:-${ROSETTA_RUNTIME_DIR}/logs}"
ROSETTA_SERVICE="${ROSETTA_SERVICE:-rosetta}"
ROSETTA_PORT="${ROSETTA_PORT:-8501}"
ROSETTA_HEALTH_URL="${ROSETTA_HEALTH_URL:-http://localhost:${ROSETTA_PORT}/_stcore/health}"

log() {
  printf '[rosetta] %s\n' "$*"
}

warn() {
  printf '[rosetta][warn] %s\n' "$*" >&2
}

err() {
  printf '[rosetta][error] %s\n' "$*" >&2
}

require_tools() {
  local missing=()
  for tool in "$@"; do
    if ! command -v "${tool}" >/dev/null 2>&1; then
      missing+=("${tool}")
    fi
  done
  if (( ${#missing[@]} > 0 )); then
    printf 'Missing required tools: %s\n' "${missing[*]}" >&2
    exit 127
  fi
}

ensure_dirs() {
  mkdir -p "${ROSETTA_RUNTIME_DIR}" "${ROSETTA_DATA_DIR}" "${ROSETTA_BACKUP_DIR}" "${ROSETTA_LOG_DIR}"
}

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose "$@"
  else
    printf 'Missing docker compose or docker-compose\n' >&2
    exit 127
  fi
}
