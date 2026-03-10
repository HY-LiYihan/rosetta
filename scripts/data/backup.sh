#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../lib/common.sh"

ensure_dirs

SOURCE_FILE="${ROSETTA_DATA_DIR}/concepts.json"
if [[ ! -f "${SOURCE_FILE}" ]]; then
  SOURCE_FILE="${ROSETTA_APP_DIR}/concepts.json"
fi

if [[ ! -f "${SOURCE_FILE}" ]]; then
  err "concepts.json not found in ${ROSETTA_DATA_DIR} or ${ROSETTA_APP_DIR}"
  exit 1
fi

timestamp="$(date '+%Y%m%d_%H%M%S')"
backup_file="${ROSETTA_BACKUP_DIR}/concepts_${timestamp}.json"
cp "${SOURCE_FILE}" "${backup_file}"
log "backup created: ${backup_file}"
