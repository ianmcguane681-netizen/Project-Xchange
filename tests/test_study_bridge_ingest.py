"""The board's audit chain must cryptographically commit to study contents.

Before this bridge existed, a Golden Study proved its own integrity and the Review
Board proved its own, with nothing linking them - so no single verifiable thread
ran from a raw source record to a board decision. These tests pin that join.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from rbe_runtime.errors import RBEError
from rbe_runtime.service import RBERuntime
from study_bridge import StudyBundle, ingest_study_bundle
from tests.test_rbe_runtime_service import NOW, initiation
from tests.test_study_bridge_bundle import write_bundle


def runtime_with_session(tmp_path: Path, review_id: str = "RBE-STUDY-0001"):
    runtime = RBERuntime(tmp_path / "bridge.sqlite3", clock=lambda: NOW)
    runtime.initiate_review(
        initiation(runtime.authority, review_id),
        actor="human-chair",
        idempotency_key=f"init-{review_id}",
    )
    return runtime, review_id


def test_bundle_files_become_evidence_carrying_study_identity(tmp_path: Path):
    runtime, review_id = runtime_with_session(tmp_path)
    bundle = StudyBundle.load(write_bundle(tmp_path / "bundle"))

    result = ingest_study_bundle(runtime, review_id, bundle, actor="human-chair")

    assert result.study_id == "GS-CF001-C"
    assert result.bundle_root_hash == bundle.bundle_root_hash
    assert len(result.reference_ids) == len(bundle.files)

    stored = runtime.repository.list_evidence(review_id)
    assert len(stored) == len(bundle.files)
    for reference in stored.values():
        assert reference.source_tier == "GOLDEN_STUDY_PROOF_BUNDLE"
        assert reference.provenance["study_id"] == "GS-CF001-C"
        assert reference.provenance["run_id"] == "RUN-TEST0001"
        assert reference.provenance["bundle_root_hash"] == bundle.bundle_root_hash
        # The commit that produced the evidence travels with the evidence.
        assert reference.provenance["code_commit_hash"] == bundle.code_commit_hash


def test_stored_content_hash_matches_the_bundle(tmp_path: Path):
    runtime, review_id = runtime_with_session(tmp_path)
    bundle = StudyBundle.load(write_bundle(tmp_path / "bundle"))

    ingest_study_bundle(runtime, review_id, bundle, actor="human-chair")

    by_file = {
        reference.provenance["bundle_file"]: reference
        for reference in runtime.repository.list_evidence(review_id).values()
    }
    for item in bundle.files:
        reference = by_file[item.name]
        assert reference.content_sha256 == f"sha256:{item.sha256}"
        assert runtime.repository.get_evidence_content(reference.reference_id) == bundle.file_content(item.name)


def test_ingestion_is_recorded_in_the_audit_chain(tmp_path: Path):
    runtime, review_id = runtime_with_session(tmp_path)
    bundle = StudyBundle.load(write_bundle(tmp_path / "bundle"))

    ingest_study_bundle(runtime, review_id, bundle, actor="human-chair")

    audit = runtime.repository.list_audit(review_id)
    registered = [entry for entry in audit if entry.event_type == "EVIDENCE_REGISTERED"]
    assert len(registered) == len(bundle.files)
    # The chain must still verify after ingestion.
    assert runtime.repository.verify_audit(review_id)["valid"] is True


def test_re_ingesting_the_same_bundle_is_idempotent(tmp_path: Path):
    runtime, review_id = runtime_with_session(tmp_path)
    bundle = StudyBundle.load(write_bundle(tmp_path / "bundle"))

    first = ingest_study_bundle(runtime, review_id, bundle, actor="human-chair")
    second = ingest_study_bundle(runtime, review_id, bundle, actor="human-chair")

    assert first.reference_ids == second.reference_ids
    assert len(runtime.repository.list_evidence(review_id)) == len(bundle.files)


def test_a_tampered_bundle_never_reaches_the_session(tmp_path: Path):
    runtime, review_id = runtime_with_session(tmp_path)
    root = write_bundle(tmp_path / "bundle")
    bundle = StudyBundle.load(root)
    (root / "report.md").write_text("# Edited after verification\n", encoding="utf-8")

    # Re-loading is what a caller does; verification refuses before any write.
    from study_bridge.bundle import StudyBundleError

    with pytest.raises(StudyBundleError):
        StudyBundle.load(root)
    assert runtime.repository.list_evidence(review_id) == {}
    assert bundle.bundle_root_hash  # original hash remains the committed identity


def test_a_later_bundle_cannot_be_added_after_the_evidence_lock(tmp_path: Path):
    """The bridge respects the lifecycle rather than bypassing it.

    Once evidence is locked, the set the board reasoned over is fixed. A study
    re-run after that point must not be able to slip into the same session.
    """
    runtime, review_id = runtime_with_session(tmp_path)
    ingest_study_bundle(
        runtime,
        review_id,
        StudyBundle.load(write_bundle(tmp_path / "bundle")),
        actor="human-chair",
    )
    for target in ["SUBMITTED", "INTAKE_VALIDATION", "ACCEPTED", "EVIDENCE_LOCKED"]:
        runtime.advance(
            review_id,
            target,
            actor="human-chair",
            idempotency_key=f"adv-{target}",
        )

    later_run = StudyBundle.load(
        write_bundle(tmp_path / "later", extra={"report.md": "# Second run\n"})
    )
    with pytest.raises(RBEError) as exc:
        ingest_study_bundle(runtime, review_id, later_run, actor="human-chair")

    assert exc.value.code == "RBE_EVIDENCE_LOCKED"
