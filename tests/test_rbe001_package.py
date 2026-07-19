from __future__ import annotations

import csv
import io
import json
import zipfile

from scripts import build_rbe001_v1_1_package as package


def test_package_is_current_and_valid() -> None:
    package.check()


def test_outcome_and_process_status_are_separate() -> None:
    taxonomy = json.loads(
        (package.PACKAGE_ROOT / "registers" / "verdict_taxonomy.json").read_text(
            encoding="utf-8"
        )
    )
    outcomes = taxonomy["substantive_outcomes"]
    statuses = {item["id"]: item for item in taxonomy["process_statuses"]}

    assert outcomes == package.CANONICAL_OUTCOMES
    assert statuses["READY"]["allows_outcome"] is True
    assert all(
        statuses[status]["allows_outcome"] is False
        for status in ("PROCEDURALLY_INCOMPLETE", "BLOCKED", "VOID")
    )


def test_state_machine_uses_only_canonical_states() -> None:
    package.validate_source_documents()
    state_machine = json.loads(
        (package.PACKAGE_ROOT / "registers" / "state_machine.json").read_text(
            encoding="utf-8"
        )
    )
    states = {item["id"] for item in state_machine["states"]}

    assert states.isdisjoint(package.LEGACY_ENGINEERING_STATES)
    assert {"DRAFT", "INDEPENDENT_REVIEW", "GOVERNANCE_VALIDATION", "PUBLISHED"} <= states


def test_requirement_namespaces_do_not_collide() -> None:
    requirements = package.collect_requirements()
    identifiers = [item["id"] for item in requirements]
    architecture = {item for item in identifiers if not item.startswith("RBE-ES-")}
    engineering = {item for item in identifiers if item.startswith("RBE-ES-")}

    assert len(identifiers) == len(set(identifiers))
    assert architecture
    assert engineering
    assert architecture.isdisjoint(engineering)


def test_every_engineering_requirement_has_migration_lineage() -> None:
    requirements = package.collect_requirements()
    engineering = {item["id"] for item in requirements if item["id"].startswith("RBE-ES-")}
    migration = package.migration_register_bytes(requirements).decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(migration)))

    engineering_rows = {
        row["new_id"]
        for row in rows
        if row["source_document"] == "RBE-001 Engineering Specification"
    }
    assert engineering_rows == engineering
    assert all(row["old_id"].startswith("RBE-") for row in rows)


def test_architecture_id_collisions_have_explicit_migrations() -> None:
    requirements = package.collect_requirements()
    rows = list(
        csv.DictReader(io.StringIO(package.migration_register_bytes(requirements).decode("utf-8")))
    )
    architecture_rows = [
        row for row in rows if row["disposition"] == "ARCHITECTURE_COLLISION_RESOLVED"
    ]

    assert len(architecture_rows) == 5
    assert {row["new_id"] for row in architecture_rows} == {
        "RBE-IBR-001",
        "RBE-AI-130",
        "RBE-AI-131",
        "RBE-OUT-010",
        "RBE-OUT-011",
    }


def test_archive_contains_manifest_and_all_searchable_sources() -> None:
    archive_path = package.PACKAGE_ROOT / package.ARCHIVE_NAME
    manifest = json.loads((package.PACKAGE_ROOT / package.MANIFEST_NAME).read_text())
    expected = {item["path"] for item in manifest["files"]}

    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == expected | {package.MANIFEST_NAME}
        assert len([name for name in archive.namelist() if "/chapters/" in name]) == 23


def test_release_does_not_claim_human_or_methodology_activation() -> None:
    readme = (package.PACKAGE_ROOT / "README.md").read_text(encoding="utf-8")
    authority = (
        package.PACKAGE_ROOT / "registers" / "AUTHORITY_AND_CONFORMANCE.md"
    ).read_text(encoding="utf-8")

    assert "Principal Architect approval: required" in readme
    assert "Only an `ACTIVE` profile may govern a binding live decision" in authority
