#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SKILL_SOURCE="${REPO_ROOT}/skills/rosetta-research"
CODEX_ROOT="${CODEX_HOME:-${HOME}/.codex}"
TARGET_DIR="${CODEX_ROOT}/skills"
TARGET_PATH="${TARGET_DIR}/rosetta-research"

if [ ! -d "${SKILL_SOURCE}" ]; then
  echo "Missing skill source: ${SKILL_SOURCE}" >&2
  exit 1
fi

mkdir -p "${TARGET_DIR}"

if [ -L "${TARGET_PATH}" ]; then
  CURRENT_TARGET="$(readlink "${TARGET_PATH}")"
  if [ "${CURRENT_TARGET}" = "${SKILL_SOURCE}" ]; then
    echo "Rosetta research skill is already installed at ${TARGET_PATH}"
    exit 0
  fi
  echo "Target already exists as a symlink to ${CURRENT_TARGET}. Remove it first." >&2
  exit 1
fi

if [ -e "${TARGET_PATH}" ]; then
  echo "Target path already exists and is not a symlink: ${TARGET_PATH}" >&2
  exit 1
fi

ln -s "${SKILL_SOURCE}" "${TARGET_PATH}"
echo "Installed rosetta-research skill at ${TARGET_PATH}"
