#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../lib/common.sh"

require_tools docker
ensure_dirs

cd "${ROSETTA_APP_DIR}"
log "starting deployment in ${ROSETTA_APP_DIR}"
compose up -d --build
"${SCRIPT_DIR}/../ops/healthcheck.sh"
log "deployment finished"
