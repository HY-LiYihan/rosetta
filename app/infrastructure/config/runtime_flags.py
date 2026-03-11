from __future__ import annotations

import argparse
import os
from dataclasses import dataclass


def _truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on", "debug"}


@dataclass(frozen=True)
class RuntimeFlags:
    debug_mode: bool


def parse_runtime_flags(argv: list[str] | None = None, env: dict[str, str] | None = None) -> RuntimeFlags:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--debug-mode", action="store_true")
    parser.add_argument("--rosetta-debug", action="store_true")
    args, _ = parser.parse_known_args(argv)

    source_env = env or os.environ
    env_enabled = _truthy(source_env.get("ROSETTA_DEBUG_MODE"))
    arg_enabled = args.debug or args.debug_mode or args.rosetta_debug
    return RuntimeFlags(debug_mode=bool(arg_enabled or env_enabled))
