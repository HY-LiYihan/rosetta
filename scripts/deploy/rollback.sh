#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../lib/common.sh"

cd "${ROSETTA_APP_DIR}"

warn "rollback script is scaffolded. For now it performs a service restart only."
warn "To support image rollback, configure immutable image tags in docker-compose.yml."
compose restart "${ROSETTA_SERVICE}"
"${SCRIPT_DIR}/../ops/healthcheck.sh"
log "rollback fallback finished"
