"""CLI adapter for the shared RBM-001 package builder and validator."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from controlled_authority.rbm_package import (
    PROFILE_VERSION,
    validate_package,
    write_control_files,
)  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write:
        write_control_files()
    validate_package()
    print(f"RBM-001 {PROFILE_VERSION} package validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
