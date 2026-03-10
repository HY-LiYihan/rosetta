#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../lib/common.sh"

cd "${ROSETTA_APP_DIR}"
log "restarting service: ${ROSETTA_SERVICE}"
compose restart "${ROSETTA_SERVICE}"
"${SCRIPT_DIR}/healthcheck.sh"
