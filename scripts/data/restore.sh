#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <backup-file>" >&2
  exit 1
fi

BACKUP_FILE="$1"
if [[ ! -f "${BACKUP_FILE}" ]]; then
  echo "backup file not found: ${BACKUP_FILE}" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../lib/common.sh"

ensure_dirs

TARGET_FILE="${ROSETTA_DATA_DIR}/concepts.json"
if [[ ! -d "${ROSETTA_DATA_DIR}" ]]; then
  TARGET_FILE="${ROSETTA_APP_DIR}/assets/concepts.json"
fi

cp "${BACKUP_FILE}" "${TARGET_FILE}"
log "restored ${BACKUP_FILE} -> ${TARGET_FILE}"
"${SCRIPT_DIR}/../ops/restart.sh"
