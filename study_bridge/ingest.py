"""Register a verified study bundle as evidence inside a review session."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from rbe_runtime.canonical import deterministic_id

from study_bridge.bundle import ARTIFACT_CLASS, StudyBundle

if TYPE_CHECKING:  # pragma: no cover - import cycle only matters for type checkers
    from rbe_runtime.service import RBERuntime

SOURCE_TIER = ARTIFACT_CLASS


@dataclass(frozen=True, slots=True)
class IngestResult:
    session_id: str
    study_id: str
    run_id: str
    bundle_root_hash: str
    reference_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "study_id": self.study_id,
            "run_id": self.run_id,
            "bundle_root_hash": self.bundle_root_hash,
            "reference_ids": list(self.reference_ids),
        }


def ingest_study_bundle(
    runtime: "RBERuntime",
    session_id: str,
    bundle: StudyBundle,
    *,
    actor: str,
) -> IngestResult:
    """Attach every file of a verified bundle to a session as evidence.

    Each file is registered with its own content hash and carries the study's
    identity - study, run, code commit, rule versions and the bundle root hash -
    as provenance. Registration is written through the runtime's ordinary evidence
    path, so the board's hash-chained audit log commits to the study contents and
    the exact code that produced them.

    Idempotency keys are derived from the bundle root hash, so re-ingesting the
    same bundle is a no-op rather than a duplicate, while a bundle whose contents
    differ by even one byte produces different keys and is refused as a conflict.
    """

    identity = bundle.identity()
    reference_ids: list[str] = []
    for item in bundle.files:
        provenance = {**identity, "bundle_file": item.name, "file_sha256": item.sha256}
        result = runtime.register_evidence(
            session_id,
            locator=f"{bundle.study_id}/{bundle.run_id}/{item.name}",
            content=bundle.file_content(item.name),
            description=f"{bundle.study_id} proof bundle file {item.name}",
            source_tier=SOURCE_TIER,
            provenance=provenance,
            actor=actor,
            idempotency_key=deterministic_id(
                "SBI", session_id, bundle.bundle_root_hash, item.name
            ),
            reference_type="STUDY_PROOF_BUNDLE_FILE",
        )
        reference_ids.append(str(result["reference_id"]))

    return IngestResult(
        session_id=session_id,
        study_id=bundle.study_id,
        run_id=bundle.run_id,
        bundle_root_hash=bundle.bundle_root_hash,
        reference_ids=tuple(reference_ids),
    )
