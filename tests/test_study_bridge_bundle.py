"""A study bundle must prove its own integrity before it can become evidence.

These tests pin the verification contract: the bundle is refused unless every file
matches its recorded checksum, nothing is missing, nothing is present that the
checksum file does not vouch for, and the manifest names the code that produced it.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from study_bridge.bundle import StudyBundle, StudyBundleError

MANIFEST = {
    "run_id": "RUN-TEST0001",
    "study_id": "GS-CF001-C",
    "code_commit_hash": "9bb288cfad99e16425f98000a906f8ca1a35eeac",
    "configuration_version": "GS-CF001-CONFIG-001",
    "methodology_version": "PROVENA-EOS-METHOD-001",
    "rule_versions": {"proof_gates": "PG-001", "verification": "VER-CFPB-001"},
}


def write_bundle(root: Path, *, manifest: dict | None = None, extra: dict | None = None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    files = {
        "run_manifest.json": json.dumps(manifest if manifest is not None else MANIFEST, indent=2),
        "proof_gate_results.json": json.dumps([{"gate_id": "PG-01", "status": "PASS"}]),
        "report.md": "# Report\n",
    }
    files.update(extra or {})
    lines = []
    for name, text in sorted(files.items()):
        (root / name).write_text(text, encoding="utf-8")
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        lines.append(f"{digest}  {name}")
    (root / "checksums.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return root


def test_valid_bundle_loads_and_exposes_identity(tmp_path: Path):
    bundle = StudyBundle.load(write_bundle(tmp_path / "b"))

    assert bundle.study_id == "GS-CF001-C"
    assert bundle.run_id == "RUN-TEST0001"
    assert bundle.code_commit_hash == MANIFEST["code_commit_hash"]
    assert [item.name for item in bundle.files] == [
        "proof_gate_results.json",
        "report.md",
        "run_manifest.json",
    ]
    assert bundle.bundle_root_hash.startswith("sha256:")


def test_root_hash_is_deterministic_and_content_sensitive(tmp_path: Path):
    first = StudyBundle.load(write_bundle(tmp_path / "a"))
    same = StudyBundle.load(write_bundle(tmp_path / "b"))
    assert first.bundle_root_hash == same.bundle_root_hash

    altered = StudyBundle.load(
        write_bundle(tmp_path / "c", extra={"report.md": "# Report changed\n"})
    )
    assert altered.bundle_root_hash != first.bundle_root_hash


def test_tampered_file_is_refused(tmp_path: Path):
    root = write_bundle(tmp_path / "b")
    (root / "report.md").write_text("# Quietly edited\n", encoding="utf-8")

    with pytest.raises(StudyBundleError) as exc:
        StudyBundle.load(root)

    assert exc.value.code == "STUDY_BUNDLE_CHECKSUM_MISMATCH"
    assert exc.value.details["files"] == ["report.md"]


def test_missing_file_is_refused(tmp_path: Path):
    root = write_bundle(tmp_path / "b")
    (root / "report.md").unlink()

    with pytest.raises(StudyBundleError) as exc:
        StudyBundle.load(root)

    assert exc.value.code == "STUDY_BUNDLE_FILE_MISSING"


def test_unlisted_file_is_refused(tmp_path: Path):
    """Content the checksum file does not vouch for is an integrity failure."""
    root = write_bundle(tmp_path / "b")
    (root / "smuggled.json").write_text("{}", encoding="utf-8")

    with pytest.raises(StudyBundleError) as exc:
        StudyBundle.load(root)

    assert exc.value.code == "STUDY_BUNDLE_FILE_UNLISTED"
    assert exc.value.details["unlisted"] == ["smuggled.json"]


def test_unresolved_commit_hash_is_refused(tmp_path: Path):
    """A bundle that cannot name its own code cannot support an audit claim."""
    root = write_bundle(tmp_path / "b", manifest={**MANIFEST, "code_commit_hash": "unknown"})

    with pytest.raises(StudyBundleError) as exc:
        StudyBundle.load(root)

    assert exc.value.code == "STUDY_BUNDLE_COMMIT_UNRESOLVED"


def test_incomplete_manifest_is_refused(tmp_path: Path):
    manifest = {key: value for key, value in MANIFEST.items() if key != "methodology_version"}
    root = write_bundle(tmp_path / "b", manifest=manifest)

    with pytest.raises(StudyBundleError) as exc:
        StudyBundle.load(root)

    assert exc.value.code == "STUDY_BUNDLE_MANIFEST_INCOMPLETE"
    assert exc.value.details["fields"] == ["methodology_version"]


def test_missing_checksum_file_is_refused(tmp_path: Path):
    root = write_bundle(tmp_path / "b")
    (root / "checksums.txt").unlink()

    with pytest.raises(StudyBundleError) as exc:
        StudyBundle.load(root)

    assert exc.value.code == "STUDY_BUNDLE_CHECKSUMS_MISSING"


def test_malformed_checksum_line_is_refused(tmp_path: Path):
    root = write_bundle(tmp_path / "b")
    (root / "checksums.txt").write_text("not-a-checksum line\n", encoding="utf-8")

    with pytest.raises(StudyBundleError) as exc:
        StudyBundle.load(root)

    assert exc.value.code == "STUDY_BUNDLE_CHECKSUMS_MALFORMED"


def test_absent_directory_is_refused(tmp_path: Path):
    with pytest.raises(StudyBundleError) as exc:
        StudyBundle.load(tmp_path / "nope")

    assert exc.value.code == "STUDY_BUNDLE_NOT_FOUND"
