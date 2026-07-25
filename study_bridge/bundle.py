"""Load and verify a Golden Study proof bundle."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rbe_runtime.canonical import canonical_hash, sha256_digest

CHECKSUM_FILE = "checksums.txt"
MANIFEST_FILE = "run_manifest.json"
ARTIFACT_CLASS = "GOLDEN_STUDY_PROOF_BUNDLE"

# Identity a bundle must carry to be auditable at all. Without these, a reader
# cannot say which study, which run, or which code produced the evidence.
REQUIRED_MANIFEST_FIELDS = (
    "run_id",
    "study_id",
    "code_commit_hash",
    "configuration_version",
    "methodology_version",
    "rule_versions",
)

# GS-CF001's manifest writer falls back to this when it cannot resolve git. A
# bundle that cannot name the code that produced it cannot support an audit
# claim, so it is refused rather than silently admitted.
UNRESOLVED_COMMIT = "unknown"

_CHECKSUM_LINE = re.compile(r"^([0-9a-f]{64})\s+(\S.*)$")


class StudyBundleError(RuntimeError):
    """A proof bundle is missing, malformed, or fails its own integrity claim."""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


@dataclass(frozen=True, slots=True)
class StudyBundleFile:
    name: str
    sha256: str
    size_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "sha256": self.sha256, "size_bytes": self.size_bytes}


@dataclass(frozen=True, slots=True)
class StudyBundle:
    """A verified proof bundle, reduced to one deterministic root hash."""

    root: Path
    study_id: str
    run_id: str
    code_commit_hash: str
    configuration_version: str
    methodology_version: str
    rule_versions: dict[str, str]
    files: tuple[StudyBundleFile, ...]
    bundle_root_hash: str
    manifest: dict[str, Any]

    @classmethod
    def load(cls, path: str | Path) -> "StudyBundle":
        root = Path(path)
        if not root.is_dir():
            raise StudyBundleError(
                "STUDY_BUNDLE_NOT_FOUND",
                f"Proof bundle directory does not exist: {root}",
                {"path": str(root)},
            )

        expected = cls._read_checksums(root)
        present = {
            item.relative_to(root).as_posix()
            for item in root.rglob("*")
            if item.is_file() and item.name != CHECKSUM_FILE
        }

        missing = sorted(set(expected) - present)
        if missing:
            raise StudyBundleError(
                "STUDY_BUNDLE_FILE_MISSING",
                "Proof bundle is missing files listed in its checksum file",
                {"missing": missing},
            )
        # An unlisted file is as much an integrity failure as a modified one:
        # it is content the bundle's own checksum file does not vouch for.
        unlisted = sorted(present - set(expected))
        if unlisted:
            raise StudyBundleError(
                "STUDY_BUNDLE_FILE_UNLISTED",
                "Proof bundle contains files absent from its checksum file",
                {"unlisted": unlisted},
            )

        files: list[StudyBundleFile] = []
        mismatched: list[str] = []
        for name in sorted(expected):
            content = (root / name).read_bytes()
            digest = sha256_digest(content).removeprefix("sha256:")
            if digest != expected[name]:
                mismatched.append(name)
                continue
            files.append(
                StudyBundleFile(name=name, sha256=digest, size_bytes=len(content))
            )
        if mismatched:
            raise StudyBundleError(
                "STUDY_BUNDLE_CHECKSUM_MISMATCH",
                "Proof bundle content does not match its recorded checksums",
                {"files": mismatched},
            )

        manifest = cls._read_manifest(root)
        return cls(
            root=root,
            study_id=str(manifest["study_id"]),
            run_id=str(manifest["run_id"]),
            code_commit_hash=str(manifest["code_commit_hash"]),
            configuration_version=str(manifest["configuration_version"]),
            methodology_version=str(manifest["methodology_version"]),
            rule_versions=dict(manifest["rule_versions"]),
            files=tuple(files),
            bundle_root_hash=canonical_hash([item.to_dict() for item in files]),
            manifest=manifest,
        )

    @staticmethod
    def _read_checksums(root: Path) -> dict[str, str]:
        checksum_path = root / CHECKSUM_FILE
        if not checksum_path.is_file():
            raise StudyBundleError(
                "STUDY_BUNDLE_CHECKSUMS_MISSING",
                f"Proof bundle has no {CHECKSUM_FILE}",
                {"path": str(checksum_path)},
            )
        expected: dict[str, str] = {}
        for number, line in enumerate(
            checksum_path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip():
                continue
            match = _CHECKSUM_LINE.match(line.strip())
            if match is None:
                raise StudyBundleError(
                    "STUDY_BUNDLE_CHECKSUMS_MALFORMED",
                    f"Unparseable checksum entry at line {number}",
                    {"line": line},
                )
            digest, name = match.group(1), match.group(2).strip()
            if name in expected:
                raise StudyBundleError(
                    "STUDY_BUNDLE_CHECKSUMS_DUPLICATE",
                    f"Checksum file lists {name} more than once",
                    {"name": name},
                )
            expected[name] = digest
        if not expected:
            raise StudyBundleError(
                "STUDY_BUNDLE_CHECKSUMS_EMPTY",
                "Checksum file lists no files",
            )
        return expected

    @staticmethod
    def _read_manifest(root: Path) -> dict[str, Any]:
        manifest_path = root / MANIFEST_FILE
        if not manifest_path.is_file():
            raise StudyBundleError(
                "STUDY_BUNDLE_MANIFEST_MISSING",
                f"Proof bundle has no {MANIFEST_FILE}",
            )
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise StudyBundleError(
                "STUDY_BUNDLE_MANIFEST_INVALID",
                "Run manifest is not valid JSON",
                {"error": str(exc)},
            ) from exc
        if not isinstance(manifest, dict):
            raise StudyBundleError(
                "STUDY_BUNDLE_MANIFEST_INVALID", "Run manifest must be a JSON object"
            )
        absent = [
            field
            for field in REQUIRED_MANIFEST_FIELDS
            if not manifest.get(field)
        ]
        if absent:
            raise StudyBundleError(
                "STUDY_BUNDLE_MANIFEST_INCOMPLETE",
                "Run manifest is missing required identity fields",
                {"fields": absent},
            )
        if str(manifest["code_commit_hash"]).strip().lower() == UNRESOLVED_COMMIT:
            raise StudyBundleError(
                "STUDY_BUNDLE_COMMIT_UNRESOLVED",
                "Run manifest does not identify the code that produced the bundle",
                {"code_commit_hash": manifest["code_commit_hash"]},
            )
        return manifest

    def identity(self) -> dict[str, Any]:
        """Study provenance recorded against every registered evidence reference."""

        return {
            "artifact_class": ARTIFACT_CLASS,
            "study_id": self.study_id,
            "run_id": self.run_id,
            "code_commit_hash": self.code_commit_hash,
            "configuration_version": self.configuration_version,
            "methodology_version": self.methodology_version,
            "rule_versions": dict(sorted(self.rule_versions.items())),
            "bundle_root_hash": self.bundle_root_hash,
        }

    def file_content(self, name: str) -> bytes:
        return (self.root / name).read_bytes()
