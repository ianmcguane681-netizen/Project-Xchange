"""CLI adapter for the shared RBE-001 package builder and validator."""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from controlled_authority.rbe_package import (  # noqa: E402
    PackageValidationError,
    build,
    check,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        check() if args.check else build()
    except (KeyError, OSError, ValueError, PackageValidationError, zipfile.BadZipFile) as exc:
        print(f"RBE-001 package validation failed: {exc}", file=sys.stderr)
        return 1
    print("RBE-001 v1.1.0 package validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
