#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../lib/common.sh"

require_tools curl

if curl -fsS "${ROSETTA_HEALTH_URL}" >/dev/null; then
  log "healthcheck passed: ${ROSETTA_HEALTH_URL}"
  exit 0
fi

err "healthcheck failed: ${ROSETTA_HEALTH_URL}"
exit 1
