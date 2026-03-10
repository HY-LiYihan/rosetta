#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../lib/common.sh"

require_tools git docker
ensure_dirs

cd "${ROSETTA_APP_DIR}"

log "creating backup before update"
"${SCRIPT_DIR}/../data/backup.sh"

if [[ -d .git ]]; then
  log "pulling latest code"
  git pull --ff-only origin main
fi

log "rebuilding and restarting service"
compose up -d --build
"${SCRIPT_DIR}/../ops/healthcheck.sh"
log "update finished"
