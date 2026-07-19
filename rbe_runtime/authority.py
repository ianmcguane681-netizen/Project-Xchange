"""Load and verify authoritative RBE and RBM packages."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rbe_runtime.constants import RBE_RELEASE, RBM_PROFILE_ID, RBM_PROFILE_VERSION
from rbe_runtime.errors import RBEError
from rbe_runtime.models import ExecutionMode
from scripts import build_rbe001_v1_1_package, validate_rbm001_package


def _semver(value: str) -> tuple[int, int, int]:
    try:
        major, minor, patch = value.split(".")
        return int(major), int(minor), int(patch)
    except (AttributeError, TypeError, ValueError) as exc:
        raise RBEError(
            "RBE_INVALID_VERSION",
            f"Invalid semantic version: {value!r}",
            "RBE-ES-VER-003",
        ) from exc


@dataclass(frozen=True, slots=True)
class AuthorityBundle:
    repo_root: Path
    state_machine: dict[str, Any]
    verdict_taxonomy: dict[str, Any]
    profile: dict[str, Any]
    profile_manifest: dict[str, Any]
    reviewer_specs: dict[str, Path]
    schemas: dict[str, Path]

    @classmethod
    def load(cls, repo_root: str | Path | None = None) -> "AuthorityBundle":
        root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[1]
        try:
            build_rbe001_v1_1_package.check()
            validate_rbm001_package.validate_package()
        except Exception as exc:
            raise RBEError(
                "RBE_AUTHORITY_PACKAGE_INVALID",
                "The controlled RBE or RBM package failed validation",
                "RBE-ES-DEC-002",
                {"error_type": type(exc).__name__},
            ) from exc

        rbe_root = root / "docs" / "rbe-001" / "v1.1.0"
        rbm_root = root / "docs" / "review-board"
        state_machine = json.loads(
            (rbe_root / "registers" / "state_machine.json").read_text(
                encoding="utf-8"
            )
        )
        verdict_taxonomy = json.loads(
            (rbe_root / "registers" / "verdict_taxonomy.json").read_text(
                encoding="utf-8"
            )
        )
        profile = json.loads((rbm_root / "PROFILE.json").read_text(encoding="utf-8"))
        profile_manifest = json.loads(
            (rbm_root / "MANIFEST.json").read_text(encoding="utf-8")
        )
        reviewer_specs = {
            "-".join(path.name.split("-")[:2]): path
            for path in sorted((rbm_root / "specs").glob("RBS-*.md"))
        }
        schemas = {
            path.name.removesuffix(".schema.json"): path
            for path in sorted((rbm_root / "schemas").glob("*.schema.json"))
        }

        bundle = cls(
            repo_root=root,
            state_machine=state_machine,
            verdict_taxonomy=verdict_taxonomy,
            profile=profile,
            profile_manifest=profile_manifest,
            reviewer_specs=reviewer_specs,
            schemas=schemas,
        )
        bundle.validate_identity()
        return bundle

    def validate_identity(self) -> None:
        if self.state_machine.get("architecture_release") != RBE_RELEASE:
            raise RBEError(
                "RBE_ARCHITECTURE_VERSION_MISMATCH",
                "State-machine release does not match the runtime authority",
                "RBE-ES-LIF-001",
            )
        if self.profile.get("profile_id") != RBM_PROFILE_ID or self.profile.get(
            "version"
        ) != RBM_PROFILE_VERSION:
            raise RBEError(
                "RBE_PROFILE_IDENTITY_MISMATCH",
                "The loaded methodology is not RBM-001 v2.0.0",
                "RBE-ES-DEC-002",
            )
        minimum = self.profile.get("architecture_authority", {}).get(
            "minimum_compatible_version"
        )
        if _semver(RBE_RELEASE) < _semver(minimum):
            raise RBEError(
                "RBE_PROFILE_ARCHITECTURE_INCOMPATIBLE",
                "The methodology requires a newer RBE architecture",
                "RBE-ES-DEC-002",
                {"minimum": minimum, "loaded": RBE_RELEASE},
            )
        if len(self.reviewer_specs) != 8 or len(self.schemas) != 7:
            raise RBEError(
                "RBE_PROFILE_INCOMPLETE",
                "RBM reviewer specifications or schemas are incomplete",
                "RBE-ES-DEC-002",
            )

    def require_execution_mode(self, mode: ExecutionMode) -> None:
        status = self.profile["status"]
        binding = self.profile["binding"]
        if mode == ExecutionMode.ADVISORY_DRY_RUN:
            if status not in {"RELEASE_CANDIDATE", "ACTIVE"}:
                raise RBEError(
                    "RBE_PROFILE_INACTIVE",
                    "The profile cannot be used for an advisory dry run",
                    "RBE-ES-DEC-002",
                    {"profile_status": status},
                )
            return
        if status != "ACTIVE" or binding is not True or not self.profile.get(
            "human_approval_record"
        ):
            raise RBEError(
                "RBE_PROFILE_NOT_ACTIVE",
                "Binding execution requires an ACTIVE, human-approved profile",
                "RBE-ES-DEC-002",
                {"profile_status": status, "binding": binding},
            )
