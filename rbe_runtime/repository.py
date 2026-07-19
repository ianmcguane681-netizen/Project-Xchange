"""SQLite persistence with atomic commands and a hash-chained audit trail."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, TypeVar

from rbe_runtime.canonical import (
    canonical_hash,
    canonical_json,
    deterministic_id,
    sha256_digest,
    utc_now,
)
from rbe_runtime.constants import RUNTIME_SCHEMA_VERSION
from rbe_runtime.errors import RBEError
from rbe_runtime.models import (
    AuditEntry,
    EvidenceReference,
    Finding,
    ReviewAssignment,
    ReviewerReport,
    ReviewSession,
)
from rbe_runtime.state_machine import CanonicalStateMachine


T = TypeVar("T")


MIGRATIONS: tuple[tuple[int, str], ...] = (
    (
        1,
        """
        CREATE TABLE review_sessions (
            session_id TEXT PRIMARY KEY,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            target_version TEXT NOT NULL,
            methodology_id TEXT NOT NULL,
            methodology_version TEXT NOT NULL,
            methodology_checksum TEXT NOT NULL,
            engine_version TEXT NOT NULL,
            schema_version TEXT NOT NULL,
            status TEXT NOT NULL,
            aggregate_version INTEGER NOT NULL,
            execution_mode TEXT NOT NULL,
            binding INTEGER NOT NULL CHECK (binding IN (0, 1)),
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            completed_at TEXT,
            parent_session_id TEXT REFERENCES review_sessions(session_id)
        );

        CREATE TABLE review_packages (
            package_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL UNIQUE REFERENCES review_sessions(session_id),
            schema_name TEXT NOT NULL,
            raw_json TEXT NOT NULL,
            raw_sha256 TEXT NOT NULL,
            package_root_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE review_assignments (
            assignment_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES review_sessions(session_id),
            reviewer_role TEXT NOT NULL,
            reviewer_actor TEXT NOT NULL,
            reviewer_spec_id TEXT NOT NULL,
            status TEXT NOT NULL,
            sequence INTEGER NOT NULL CHECK (sequence > 0),
            required INTEGER NOT NULL CHECK (required IN (0, 1)),
            conflict_declared INTEGER NOT NULL CHECK (conflict_declared IN (0, 1)),
            has_material_conflict INTEGER NOT NULL CHECK (has_material_conflict IN (0, 1)),
            assigned_at TEXT NOT NULL,
            accepted_at TEXT,
            completed_at TEXT,
            UNIQUE (session_id, reviewer_role),
            UNIQUE (session_id, sequence)
        );

        CREATE TABLE evidence_references (
            reference_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES review_sessions(session_id),
            reference_type TEXT NOT NULL,
            locator TEXT NOT NULL,
            content_sha256 TEXT NOT NULL,
            content_blob BLOB NOT NULL,
            description TEXT NOT NULL,
            source_tier TEXT,
            provenance_json TEXT NOT NULL,
            registered_at TEXT NOT NULL,
            UNIQUE (session_id, locator, content_sha256)
        );

        CREATE TABLE conflict_declarations (
            declaration_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES review_sessions(session_id),
            assignment_id TEXT NOT NULL UNIQUE REFERENCES review_assignments(assignment_id),
            actor TEXT NOT NULL,
            has_material_conflict INTEGER NOT NULL CHECK (has_material_conflict IN (0, 1)),
            basis TEXT,
            declared_at TEXT NOT NULL
        );

        CREATE TABLE review_reports (
            report_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES review_sessions(session_id),
            assignment_id TEXT NOT NULL REFERENCES review_assignments(assignment_id),
            report_version INTEGER NOT NULL CHECK (report_version > 0),
            raw_record_json TEXT NOT NULL,
            raw_record_sha256 TEXT NOT NULL,
            summary TEXT NOT NULL,
            recommendation TEXT NOT NULL,
            finding_ids_json TEXT NOT NULL,
            evidence_reference_ids_json TEXT NOT NULL,
            ai_assisted INTEGER NOT NULL CHECK (ai_assisted IN (0, 1)),
            human_verified INTEGER NOT NULL CHECK (human_verified IN (0, 1)),
            human_signature_ref TEXT NOT NULL,
            submitted_at TEXT NOT NULL,
            supersedes_report_id TEXT REFERENCES review_reports(report_id),
            UNIQUE (assignment_id, report_version)
        );

        CREATE TABLE report_evidence_links (
            report_id TEXT NOT NULL REFERENCES review_reports(report_id),
            reference_id TEXT NOT NULL REFERENCES evidence_references(reference_id),
            PRIMARY KEY (report_id, reference_id)
        );

        CREATE TABLE findings (
            finding_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES review_sessions(session_id),
            source_report_id TEXT NOT NULL REFERENCES review_reports(report_id),
            severity TEXT NOT NULL,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            evidence_reference_ids_json TEXT NOT NULL,
            status TEXT NOT NULL,
            remediation_required INTEGER NOT NULL CHECK (remediation_required IN (0, 1)),
            remediation_plan_accepted INTEGER NOT NULL CHECK (remediation_plan_accepted IN (0, 1)),
            raw_record_json TEXT NOT NULL,
            raw_record_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL,
            supersedes_finding_id TEXT REFERENCES findings(finding_id)
        );

        CREATE TABLE finding_evidence_links (
            finding_id TEXT NOT NULL REFERENCES findings(finding_id),
            reference_id TEXT NOT NULL REFERENCES evidence_references(reference_id),
            PRIMARY KEY (finding_id, reference_id)
        );

        CREATE TABLE board_decisions (
            decision_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES review_sessions(session_id),
            status TEXT NOT NULL,
            binding INTEGER NOT NULL CHECK (binding IN (0, 1)),
            merge_permitted INTEGER NOT NULL CHECK (merge_permitted IN (0, 1)),
            execution_mode TEXT NOT NULL,
            evaluation_json TEXT NOT NULL,
            finding_snapshot_hash TEXT NOT NULL,
            artifact_manifest_hash TEXT NOT NULL,
            artifact_manifest_json TEXT NOT NULL,
            computed_at TEXT NOT NULL,
            signed_at TEXT,
            published_at TEXT,
            published_by TEXT,
            superseded INTEGER NOT NULL DEFAULT 0 CHECK (superseded IN (0, 1))
        );
        CREATE UNIQUE INDEX one_current_decision_per_session
            ON board_decisions(session_id) WHERE superseded = 0;

        CREATE TABLE audit_log (
            audit_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES review_sessions(session_id),
            sequence INTEGER NOT NULL CHECK (sequence > 0),
            event_type TEXT NOT NULL,
            actor TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            previous_hash TEXT,
            entry_hash TEXT NOT NULL,
            schema_id TEXT NOT NULL,
            schema_version TEXT NOT NULL,
            UNIQUE (session_id, sequence)
        );

        CREATE TABLE idempotency_keys (
            session_id TEXT NOT NULL REFERENCES review_sessions(session_id),
            command_name TEXT NOT NULL,
            idempotency_key TEXT NOT NULL,
            payload_hash TEXT NOT NULL,
            result_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (session_id, command_name, idempotency_key)
        );

        CREATE TRIGGER review_packages_no_update
        BEFORE UPDATE ON review_packages BEGIN SELECT RAISE(ABORT, 'review_packages are immutable'); END;
        CREATE TRIGGER review_packages_no_delete
        BEFORE DELETE ON review_packages BEGIN SELECT RAISE(ABORT, 'review_packages are append-only'); END;
        CREATE TRIGGER evidence_references_no_update
        BEFORE UPDATE ON evidence_references BEGIN SELECT RAISE(ABORT, 'evidence_references are immutable'); END;
        CREATE TRIGGER evidence_references_no_delete
        BEFORE DELETE ON evidence_references BEGIN SELECT RAISE(ABORT, 'evidence_references are append-only'); END;
        CREATE TRIGGER conflict_declarations_no_update
        BEFORE UPDATE ON conflict_declarations BEGIN SELECT RAISE(ABORT, 'conflict_declarations are immutable'); END;
        CREATE TRIGGER conflict_declarations_no_delete
        BEFORE DELETE ON conflict_declarations BEGIN SELECT RAISE(ABORT, 'conflict_declarations are append-only'); END;
        CREATE TRIGGER review_reports_no_update
        BEFORE UPDATE ON review_reports BEGIN SELECT RAISE(ABORT, 'review_reports are immutable'); END;
        CREATE TRIGGER review_reports_no_delete
        BEFORE DELETE ON review_reports BEGIN SELECT RAISE(ABORT, 'review_reports are append-only'); END;
        CREATE TRIGGER findings_no_update
        BEFORE UPDATE ON findings BEGIN SELECT RAISE(ABORT, 'findings are immutable'); END;
        CREATE TRIGGER findings_no_delete
        BEFORE DELETE ON findings BEGIN SELECT RAISE(ABORT, 'findings are append-only'); END;
        CREATE TRIGGER board_decisions_no_update
        BEFORE UPDATE ON board_decisions BEGIN SELECT RAISE(ABORT, 'board_decisions are immutable'); END;
        CREATE TRIGGER board_decisions_no_delete
        BEFORE DELETE ON board_decisions BEGIN SELECT RAISE(ABORT, 'board_decisions are append-only'); END;
        CREATE TRIGGER audit_log_no_update
        BEFORE UPDATE ON audit_log BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;
        CREATE TRIGGER audit_log_no_delete
        BEFORE DELETE ON audit_log BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;

        CREATE INDEX assignments_by_session ON review_assignments(session_id, sequence);
        CREATE INDEX evidence_by_session ON evidence_references(session_id, reference_id);
        CREATE INDEX reports_by_session ON review_reports(session_id, report_id);
        CREATE INDEX findings_by_session ON findings(session_id, severity, finding_id);
        CREATE INDEX audit_by_session ON audit_log(session_id, sequence);
        """,
    ),
)


class SQLiteRepository:
    """Durable repository for a single-node, non-production RBE runtime."""

    def __init__(
        self,
        path: str | Path,
        state_machine: CanonicalStateMachine,
        *,
        clock: Callable[[], str] = utc_now,
    ) -> None:
        self.path = Path(path)
        self.state_machine = state_machine
        self.clock = clock
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate()
        self.verify_all_audits()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
            connection.close()
            raise RBEError(
                "RBE_SQLITE_FOREIGN_KEYS_DISABLED",
                "SQLite foreign-key enforcement could not be enabled",
                "RBE-ES-PER-001",
            )
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    def _migrate(self) -> None:
        connection = self._connect()
        try:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    checksum TEXT NOT NULL,
                    applied_at TEXT NOT NULL
                )
                """
            )
            connection.commit()
            rows = connection.execute(
                "SELECT version, checksum FROM schema_migrations ORDER BY version"
            ).fetchall()
            supported = {version: sha256_digest(sql.encode("utf-8")) for version, sql in MIGRATIONS}
            if rows and rows[-1]["version"] > max(supported):
                raise RBEError(
                    "RBE_DATABASE_SCHEMA_TOO_NEW",
                    "The database schema is newer than this runtime supports",
                    "RBE-ES-PER-005",
                    {
                        "database_version": rows[-1]["version"],
                        "runtime_schema_version": RUNTIME_SCHEMA_VERSION,
                    },
                )
            for row in rows:
                if supported.get(row["version"]) != row["checksum"]:
                    raise RBEError(
                        "RBE_MIGRATION_CHECKSUM_MISMATCH",
                        "An applied database migration checksum has changed",
                        "RBE-ES-PER-004",
                        {"version": row["version"]},
                    )
            applied = {row["version"] for row in rows}
            for version, sql in MIGRATIONS:
                if version in applied:
                    continue
                connection.executescript(sql)
                connection.execute(
                    "INSERT INTO schema_migrations(version, checksum, applied_at) VALUES (?, ?, ?)",
                    (version, supported[version], self.clock()),
                )
                connection.commit()
        finally:
            connection.close()

    def _append_audit(
        self,
        connection: sqlite3.Connection,
        *,
        session_id: str,
        event_type: str,
        actor: str,
        occurred_at: str,
        payload: dict[str, Any],
    ) -> AuditEntry:
        previous = connection.execute(
            """
            SELECT sequence, entry_hash FROM audit_log
            WHERE session_id = ? ORDER BY sequence DESC LIMIT 1
            """,
            (session_id,),
        ).fetchone()
        sequence = 1 if previous is None else previous["sequence"] + 1
        previous_hash = None if previous is None else previous["entry_hash"]
        hash_payload = {
            "session_id": session_id,
            "sequence": sequence,
            "event_type": event_type,
            "actor": actor,
            "occurred_at": occurred_at,
            "payload": payload,
            "previous_hash": previous_hash,
        }
        entry_hash = canonical_hash(hash_payload)
        entry = AuditEntry(
            audit_id=deterministic_id(
                "AUD", session_id, str(sequence), entry_hash
            ),
            session_id=session_id,
            sequence=sequence,
            event_type=event_type,
            actor=actor,
            occurred_at=occurred_at,
            payload=payload,
            previous_hash=previous_hash,
            entry_hash=entry_hash,
        )
        connection.execute(
            """
            INSERT INTO audit_log(
                audit_id, session_id, sequence, event_type, actor, occurred_at,
                payload_json, previous_hash, entry_hash, schema_id, schema_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.audit_id,
                entry.session_id,
                entry.sequence,
                entry.event_type,
                entry.actor,
                entry.occurred_at,
                canonical_json(entry.payload),
                entry.previous_hash,
                entry.entry_hash,
                entry.schema_id,
                entry.schema_version,
            ),
        )
        return entry

    def _session_exists(self, connection: sqlite3.Connection, session_id: str) -> bool:
        return (
            connection.execute(
                "SELECT 1 FROM review_sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            is not None
        )

    def _run_idempotent(
        self,
        *,
        session_id: str,
        command_name: str,
        idempotency_key: str,
        actor: str,
        payload: dict[str, Any],
        operation: Callable[[sqlite3.Connection, str], dict[str, Any]],
    ) -> dict[str, Any]:
        if not idempotency_key.strip():
            raise RBEError(
                "RBE_IDEMPOTENCY_KEY_REQUIRED",
                "A non-empty idempotency key is required",
                "RBE-ES-LIF-005",
            )
        payload_hash = canonical_hash(payload)
        connection = self._connect()
        pending_error: RBEError | None = None
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT payload_hash, result_json FROM idempotency_keys
                WHERE session_id = ? AND command_name = ? AND idempotency_key = ?
                """,
                (session_id, command_name, idempotency_key),
            ).fetchone()
            if existing is not None:
                if existing["payload_hash"] == payload_hash:
                    connection.rollback()
                    return json.loads(existing["result_json"])
                now = self.clock()
                self._append_audit(
                    connection,
                    session_id=session_id,
                    event_type="IDEMPOTENCY_CONFLICT",
                    actor=actor,
                    occurred_at=now,
                    payload={
                        "command": command_name,
                        "idempotency_key": idempotency_key,
                        "original_payload_hash": existing["payload_hash"],
                        "received_payload_hash": payload_hash,
                    },
                )
                connection.commit()
                raise RBEError(
                    "RBE_IDEMPOTENCY_CONFLICT",
                    "The idempotency key was already used with a different payload",
                    "RBE-ES-LIF-005",
                )

            now = self.clock()
            connection.execute("SAVEPOINT command_operation")
            try:
                result = operation(connection, now)
            except RBEError as exc:
                connection.execute("ROLLBACK TO command_operation")
                connection.execute("RELEASE command_operation")
                if self._session_exists(connection, session_id):
                    self._append_audit(
                        connection,
                        session_id=session_id,
                        event_type="COMMAND_REJECTED",
                        actor=actor,
                        occurred_at=now,
                        payload={
                            "command": command_name,
                            "error_code": exc.code,
                            "payload_hash": payload_hash,
                        },
                    )
                connection.commit()
                pending_error = exc
                result = {}
            except sqlite3.IntegrityError as exc:
                connection.execute("ROLLBACK TO command_operation")
                connection.execute("RELEASE command_operation")
                pending_error = RBEError(
                    "RBE_PERSISTENCE_CONSTRAINT",
                    "The command violates a durable record constraint",
                    "RBE-ES-PER-001",
                    {"constraint": str(exc)},
                )
                if self._session_exists(connection, session_id):
                    self._append_audit(
                        connection,
                        session_id=session_id,
                        event_type="COMMAND_REJECTED",
                        actor=actor,
                        occurred_at=now,
                        payload={
                            "command": command_name,
                            "error_code": pending_error.code,
                            "payload_hash": payload_hash,
                        },
                    )
                connection.commit()
                result = {}
            else:
                connection.execute("RELEASE command_operation")
                connection.execute(
                    """
                    INSERT INTO idempotency_keys(
                        session_id, command_name, idempotency_key,
                        payload_hash, result_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        command_name,
                        idempotency_key,
                        payload_hash,
                        canonical_json(result),
                        now,
                    ),
                )
                connection.commit()
            if pending_error is not None:
                raise pending_error
            return result
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def create_review(
        self,
        session: ReviewSession,
        initiation: dict[str, Any],
        assignments: Iterable[ReviewAssignment],
        *,
        actor: str,
        idempotency_key: str,
        package_root_hash: str,
    ) -> dict[str, Any]:
        assignment_list = tuple(assignments)
        payload = {
            "session": session.to_dict(),
            "initiation": initiation,
            "assignments": [item.to_dict() for item in assignment_list],
            "package_root_hash": package_root_hash,
        }

        def operation(connection: sqlite3.Connection, now: str) -> dict[str, Any]:
            connection.execute(
                """
                INSERT INTO review_sessions VALUES (
                    :session_id, :target_type, :target_id, :target_version,
                    :methodology_id, :methodology_version, :methodology_checksum,
                    :engine_version, :schema_version, :status, :aggregate_version,
                    :execution_mode, :binding, :created_at, :created_by,
                    :completed_at, :parent_session_id
                )
                """,
                {**session.to_dict(), "binding": int(session.binding)},
            )
            raw_sha256 = canonical_hash(initiation)
            package_id = deterministic_id("PKG", session.session_id, raw_sha256)
            connection.execute(
                """
                INSERT INTO review_packages VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    package_id,
                    session.session_id,
                    "tpl-rir",
                    canonical_json(initiation),
                    raw_sha256,
                    package_root_hash,
                    now,
                ),
            )
            for assignment in assignment_list:
                connection.execute(
                    """
                    INSERT INTO review_assignments VALUES (
                        :assignment_id, :session_id, :reviewer_role,
                        :reviewer_actor, :reviewer_spec_id, :status, :sequence,
                        :required, :conflict_declared, :has_material_conflict,
                        :assigned_at, :accepted_at, :completed_at
                    )
                    """,
                    {
                        **assignment.to_dict(),
                        "required": int(assignment.required),
                        "conflict_declared": int(assignment.conflict_declared),
                        "has_material_conflict": int(
                            assignment.has_material_conflict
                        ),
                    },
                )
            self._append_audit(
                connection,
                session_id=session.session_id,
                event_type="SESSION_CREATED",
                actor=actor,
                occurred_at=now,
                payload={
                    "initial_state": session.status,
                    "package_id": package_id,
                    "package_sha256": raw_sha256,
                    "assignment_ids": sorted(
                        item.assignment_id for item in assignment_list
                    ),
                    "binding": session.binding,
                    "execution_mode": session.execution_mode,
                },
            )
            return {
                "session_id": session.session_id,
                "status": session.status,
                "aggregate_version": session.aggregate_version,
                "package_id": package_id,
                "assignment_ids": sorted(
                    item.assignment_id for item in assignment_list
                ),
            }

        return self._run_idempotent(
            session_id=session.session_id,
            command_name="create_review",
            idempotency_key=idempotency_key,
            actor=actor,
            payload=payload,
            operation=operation,
        )

    def transition(
        self,
        session_id: str,
        target_state: str,
        *,
        actor: str,
        idempotency_key: str,
        expected_version: int,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "target_state": target_state,
            "expected_version": expected_version,
            "metadata": metadata or {},
        }

        def operation(connection: sqlite3.Connection, now: str) -> dict[str, Any]:
            row = connection.execute(
                "SELECT * FROM review_sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            if row is None:
                raise RBEError(
                    "RBE_SESSION_NOT_FOUND",
                    "Review session was not found",
                    "RBE-ES-LIF-002",
                    {"session_id": session_id},
                )
            source_state = row["status"]
            self.state_machine.require_transition(source_state, target_state)
            if row["aggregate_version"] != expected_version:
                raise RBEError(
                    "RBE_CONCURRENCY_CONFLICT",
                    "The review session changed after it was read",
                    "RBE-ES-LIF-002",
                    {
                        "expected_version": expected_version,
                        "actual_version": row["aggregate_version"],
                    },
                )
            new_version = expected_version + 1
            completed_at = now if target_state in self.state_machine.terminal_states else None
            updated = connection.execute(
                """
                UPDATE review_sessions
                SET status = ?, aggregate_version = ?, completed_at = ?
                WHERE session_id = ? AND status = ? AND aggregate_version = ?
                """,
                (
                    target_state,
                    new_version,
                    completed_at,
                    session_id,
                    source_state,
                    expected_version,
                ),
            )
            if updated.rowcount != 1:
                raise RBEError(
                    "RBE_CONCURRENCY_CONFLICT",
                    "The transition lost an optimistic concurrency race",
                    "RBE-ES-LIF-002",
                )
            self._append_audit(
                connection,
                session_id=session_id,
                event_type="STATE_TRANSITIONED",
                actor=actor,
                occurred_at=now,
                payload={
                    "source_state": source_state,
                    "target_state": target_state,
                    "aggregate_version": new_version,
                    "metadata": metadata or {},
                },
            )
            return {
                "session_id": session_id,
                "source_state": source_state,
                "status": target_state,
                "aggregate_version": new_version,
            }

        return self._run_idempotent(
            session_id=session_id,
            command_name="transition",
            idempotency_key=idempotency_key,
            actor=actor,
            payload=payload,
            operation=operation,
        )

    def register_evidence(
        self,
        reference: EvidenceReference,
        content: bytes,
        *,
        actor: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        computed_hash = sha256_digest(content)
        payload = {
            "reference": reference.to_dict(),
            "computed_content_sha256": computed_hash,
        }

        def operation(connection: sqlite3.Connection, now: str) -> dict[str, Any]:
            if computed_hash != reference.content_sha256:
                raise RBEError(
                    "RBE_EVIDENCE_HASH_MISMATCH",
                    "Evidence content does not match its declared SHA-256",
                    "RBE-ES-SEC-004",
                    {
                        "declared": reference.content_sha256,
                        "computed": computed_hash,
                    },
                )
            connection.execute(
                """
                INSERT INTO evidence_references(
                    reference_id, session_id, reference_type, locator,
                    content_sha256, content_blob, description, source_tier,
                    provenance_json, registered_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    reference.reference_id,
                    reference.session_id,
                    reference.reference_type,
                    reference.locator,
                    reference.content_sha256,
                    content,
                    reference.description,
                    reference.source_tier,
                    canonical_json(reference.provenance),
                    reference.registered_at,
                ),
            )
            self._append_audit(
                connection,
                session_id=reference.session_id,
                event_type="EVIDENCE_REGISTERED",
                actor=actor,
                occurred_at=now,
                payload={
                    "reference_id": reference.reference_id,
                    "content_sha256": computed_hash,
                    "locator": reference.locator,
                    "provenance_sha256": canonical_hash(reference.provenance),
                },
            )
            return reference.to_dict()

        return self._run_idempotent(
            session_id=reference.session_id,
            command_name="register_evidence",
            idempotency_key=idempotency_key,
            actor=actor,
            payload=payload,
            operation=operation,
        )

    def record_assignment_response(
        self,
        session_id: str,
        assignment_id: str,
        *,
        actor: str,
        has_material_conflict: bool,
        conflict_basis: str | None,
        idempotency_key: str,
    ) -> dict[str, Any]:
        payload = {
            "assignment_id": assignment_id,
            "has_material_conflict": has_material_conflict,
            "conflict_basis": conflict_basis,
        }

        def operation(connection: sqlite3.Connection, now: str) -> dict[str, Any]:
            row = connection.execute(
                """
                SELECT * FROM review_assignments
                WHERE assignment_id = ? AND session_id = ?
                """,
                (assignment_id, session_id),
            ).fetchone()
            if row is None:
                raise RBEError(
                    "RBE_ASSIGNMENT_NOT_FOUND",
                    "Review assignment was not found in the session",
                    "RBE-ES-ORC-006",
                )
            if row["reviewer_actor"] != actor:
                raise RBEError(
                    "RBE_ASSIGNMENT_ACTOR_MISMATCH",
                    "Only the assigned human reviewer may accept the assignment",
                    "RBE-ES-ORC-006",
                )
            if row["status"] != "PLANNED":
                raise RBEError(
                    "RBE_ASSIGNMENT_ALREADY_RESPONDED",
                    "The assignment already has a recorded response",
                    "RBE-ES-ORC-008",
                    {"assignment_status": row["status"]},
                )
            if has_material_conflict and not (conflict_basis or "").strip():
                raise RBEError(
                    "RBE_CONFLICT_BASIS_REQUIRED",
                    "A material conflict declaration requires a recorded basis",
                    "RBE-ES-ORC-003",
                )
            status = "DECLINED" if has_material_conflict else "ACCEPTED"
            declaration_id = deterministic_id(
                "CFD", session_id, assignment_id, actor, now
            )
            connection.execute(
                """
                INSERT INTO conflict_declarations(
                    declaration_id, session_id, assignment_id, actor,
                    has_material_conflict, basis, declared_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    declaration_id,
                    session_id,
                    assignment_id,
                    actor,
                    int(has_material_conflict),
                    conflict_basis,
                    now,
                ),
            )
            connection.execute(
                """
                UPDATE review_assignments
                SET status = ?, conflict_declared = 1,
                    has_material_conflict = ?, accepted_at = ?
                WHERE assignment_id = ?
                """,
                (
                    status,
                    int(has_material_conflict),
                    None if has_material_conflict else now,
                    assignment_id,
                ),
            )
            self._append_audit(
                connection,
                session_id=session_id,
                event_type=(
                    "ASSIGNMENT_CONFLICT_DECLARED"
                    if has_material_conflict
                    else "ASSIGNMENT_ACCEPTED"
                ),
                actor=actor,
                occurred_at=now,
                payload={
                    "assignment_id": assignment_id,
                    "declaration_id": declaration_id,
                    "status": status,
                    "has_material_conflict": has_material_conflict,
                    "conflict_basis_hash": (
                        canonical_hash(conflict_basis) if conflict_basis else None
                    ),
                },
            )
            return {
                "assignment_id": assignment_id,
                "status": status,
                "has_material_conflict": has_material_conflict,
            }

        return self._run_idempotent(
            session_id=session_id,
            command_name="record_assignment_response",
            idempotency_key=idempotency_key,
            actor=actor,
            payload=payload,
            operation=operation,
        )

    def submit_review(
        self,
        report: ReviewerReport,
        findings: Iterable[Finding],
        *,
        actor: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        finding_list = tuple(findings)
        payload = {
            "report": report.to_dict(),
            "findings": [finding.to_dict() for finding in finding_list],
        }

        def operation(connection: sqlite3.Connection, now: str) -> dict[str, Any]:
            assignment = connection.execute(
                "SELECT * FROM review_assignments WHERE assignment_id = ?",
                (report.assignment_id,),
            ).fetchone()
            if assignment is None or assignment["session_id"] != report.session_id:
                raise RBEError(
                    "RBE_ASSIGNMENT_SESSION_MISMATCH",
                    "Report assignment does not belong to the report session",
                    "RBE-ES-DOM-001",
                )
            if assignment["status"] != "ACCEPTED":
                raise RBEError(
                    "RBE_ASSIGNMENT_NOT_ACCEPTED",
                    "Only accepted assignments may submit a report",
                    "RBE-ES-ORC-006",
                )
            received_findings = {finding.finding_id for finding in finding_list}
            if received_findings != set(report.finding_ids):
                raise RBEError(
                    "RBE_REPORT_FINDING_SET_MISMATCH",
                    "Submitted findings do not match the report declaration",
                    "RBE-ES-DOM-002",
                    {
                        "declared": sorted(report.finding_ids),
                        "received": sorted(received_findings),
                    },
                )
            connection.execute(
                """
                INSERT INTO review_reports VALUES (
                    :report_id, :session_id, :assignment_id, :report_version,
                    :raw_record_json, :raw_record_sha256, :summary,
                    :recommendation, :finding_ids_json,
                    :evidence_reference_ids_json, :ai_assisted,
                    :human_verified, :human_signature_ref, :submitted_at,
                    :supersedes_report_id
                )
                """,
                {
                    **report.to_dict(),
                    "raw_record_json": canonical_json(report.raw_record),
                    "finding_ids_json": canonical_json(list(report.finding_ids)),
                    "evidence_reference_ids_json": canonical_json(
                        list(report.evidence_reference_ids)
                    ),
                    "ai_assisted": int(report.ai_assisted),
                    "human_verified": int(report.human_verified),
                },
            )
            for reference_id in report.evidence_reference_ids:
                connection.execute(
                    "INSERT INTO report_evidence_links VALUES (?, ?)",
                    (report.report_id, reference_id),
                )
            for finding in finding_list:
                if (
                    finding.session_id != report.session_id
                    or finding.source_report_id != report.report_id
                ):
                    raise RBEError(
                        "RBE_FINDING_CROSS_RECORD_MISMATCH",
                        "A finding does not belong to its submitted report",
                        "RBE-ES-DOM-002",
                    )
                connection.execute(
                    """
                    INSERT INTO findings VALUES (
                        :finding_id, :session_id, :source_report_id, :severity,
                        :category, :title, :description,
                        :evidence_reference_ids_json, :status,
                        :remediation_required, :remediation_plan_accepted,
                        :raw_record_json, :raw_record_sha256, :created_at,
                        :supersedes_finding_id
                    )
                    """,
                    {
                        **finding.to_dict(),
                        "evidence_reference_ids_json": canonical_json(
                            list(finding.evidence_reference_ids)
                        ),
                        "remediation_required": int(finding.remediation_required),
                        "remediation_plan_accepted": int(
                            finding.remediation_plan_accepted
                        ),
                        "raw_record_json": canonical_json(finding.raw_record),
                    },
                )
                for reference_id in finding.evidence_reference_ids:
                    connection.execute(
                        "INSERT INTO finding_evidence_links VALUES (?, ?)",
                        (finding.finding_id, reference_id),
                    )
            connection.execute(
                """
                UPDATE review_assignments
                SET status = 'COMPLETED', completed_at = ?
                WHERE assignment_id = ?
                """,
                (now, report.assignment_id),
            )
            self._append_audit(
                connection,
                session_id=report.session_id,
                event_type="REVIEW_REPORT_SUBMITTED",
                actor=actor,
                occurred_at=now,
                payload={
                    "assignment_id": report.assignment_id,
                    "report_id": report.report_id,
                    "report_sha256": report.raw_record_sha256,
                    "finding_ids": sorted(received_findings),
                },
            )
            return {
                "report_id": report.report_id,
                "finding_ids": sorted(received_findings),
                "assignment_status": "COMPLETED",
            }

        return self._run_idempotent(
            session_id=report.session_id,
            command_name="submit_review",
            idempotency_key=idempotency_key,
            actor=actor,
            payload=payload,
            operation=operation,
        )

    def get_session(self, session_id: str) -> ReviewSession:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM review_sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            raise RBEError(
                "RBE_SESSION_NOT_FOUND",
                "Review session was not found",
                "RBE-ES-LIF-002",
                {"session_id": session_id},
            )
        return self._session_from_row(row)

    def list_assignments(self, session_id: str) -> tuple[ReviewAssignment, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT * FROM review_assignments
                WHERE session_id = ? ORDER BY sequence, assignment_id
                """,
                (session_id,),
            ).fetchall()
        finally:
            connection.close()
        return tuple(self._assignment_from_row(row) for row in rows)

    def list_evidence(self, session_id: str) -> dict[str, EvidenceReference]:
        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT * FROM evidence_references
                WHERE session_id = ? ORDER BY reference_id
                """,
                (session_id,),
            ).fetchall()
        finally:
            connection.close()
        return {
            row["reference_id"]: EvidenceReference(
                reference_id=row["reference_id"],
                session_id=row["session_id"],
                reference_type=row["reference_type"],
                locator=row["locator"],
                content_sha256=row["content_sha256"],
                description=row["description"],
                source_tier=row["source_tier"],
                provenance=json.loads(row["provenance_json"]),
                registered_at=row["registered_at"],
            )
            for row in rows
        }

    def get_evidence_content(self, reference_id: str) -> bytes:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT content_blob FROM evidence_references WHERE reference_id = ?",
                (reference_id,),
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            raise RBEError(
                "RBE_EVIDENCE_NOT_FOUND",
                "Evidence reference was not found",
                "RBE-ES-ORC-007",
                {"reference_id": reference_id},
            )
        return bytes(row["content_blob"])

    def list_reports(self, session_id: str) -> tuple[ReviewerReport, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT * FROM review_reports
                WHERE session_id = ? ORDER BY report_id
                """,
                (session_id,),
            ).fetchall()
        finally:
            connection.close()
        return tuple(self._report_from_row(row) for row in rows)

    def list_findings(self, session_id: str) -> tuple[Finding, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT * FROM findings
                WHERE session_id = ? ORDER BY severity, category, finding_id
                """,
                (session_id,),
            ).fetchall()
        finally:
            connection.close()
        return tuple(self._finding_from_row(row) for row in rows)

    def list_audit(self, session_id: str) -> tuple[AuditEntry, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT * FROM audit_log
                WHERE session_id = ? ORDER BY sequence
                """,
                (session_id,),
            ).fetchall()
        finally:
            connection.close()
        return tuple(
            AuditEntry(
                audit_id=row["audit_id"],
                session_id=row["session_id"],
                sequence=row["sequence"],
                event_type=row["event_type"],
                actor=row["actor"],
                occurred_at=row["occurred_at"],
                payload=json.loads(row["payload_json"]),
                previous_hash=row["previous_hash"],
                entry_hash=row["entry_hash"],
                schema_id=row["schema_id"],
                schema_version=row["schema_version"],
            )
            for row in rows
        )

    def verify_audit(self, session_id: str) -> dict[str, Any]:
        entries = self.list_audit(session_id)
        previous_hash: str | None = None
        for expected_sequence, entry in enumerate(entries, start=1):
            payload = {
                "session_id": entry.session_id,
                "sequence": entry.sequence,
                "event_type": entry.event_type,
                "actor": entry.actor,
                "occurred_at": entry.occurred_at,
                "payload": entry.payload,
                "previous_hash": entry.previous_hash,
            }
            if (
                entry.sequence != expected_sequence
                or entry.previous_hash != previous_hash
                or entry.entry_hash != canonical_hash(payload)
            ):
                raise RBEError(
                    "RBE_AUDIT_CHAIN_INVALID",
                    "The session audit chain failed verification",
                    "RBE-ES-AUD-002",
                    {
                        "session_id": session_id,
                        "sequence": entry.sequence,
                    },
                )
            previous_hash = entry.entry_hash
        return {
            "session_id": session_id,
            "entries_verified": len(entries),
            "root_hash": previous_hash,
            "valid": True,
        }

    def verify_all_audits(self) -> None:
        connection = self._connect()
        try:
            session_ids = [
                row["session_id"]
                for row in connection.execute(
                    "SELECT session_id FROM review_sessions ORDER BY session_id"
                ).fetchall()
            ]
        finally:
            connection.close()
        for session_id in session_ids:
            self.verify_audit(session_id)

    @staticmethod
    def _session_from_row(row: sqlite3.Row) -> ReviewSession:
        return ReviewSession(
            session_id=row["session_id"],
            target_type=row["target_type"],
            target_id=row["target_id"],
            target_version=row["target_version"],
            methodology_id=row["methodology_id"],
            methodology_version=row["methodology_version"],
            methodology_checksum=row["methodology_checksum"],
            engine_version=row["engine_version"],
            schema_version=row["schema_version"],
            status=row["status"],
            aggregate_version=row["aggregate_version"],
            execution_mode=row["execution_mode"],
            binding=bool(row["binding"]),
            created_at=row["created_at"],
            created_by=row["created_by"],
            completed_at=row["completed_at"],
            parent_session_id=row["parent_session_id"],
        )

    @staticmethod
    def _assignment_from_row(row: sqlite3.Row) -> ReviewAssignment:
        return ReviewAssignment(
            assignment_id=row["assignment_id"],
            session_id=row["session_id"],
            reviewer_role=row["reviewer_role"],
            reviewer_actor=row["reviewer_actor"],
            reviewer_spec_id=row["reviewer_spec_id"],
            status=row["status"],
            sequence=row["sequence"],
            required=bool(row["required"]),
            conflict_declared=bool(row["conflict_declared"]),
            has_material_conflict=bool(row["has_material_conflict"]),
            assigned_at=row["assigned_at"],
            accepted_at=row["accepted_at"],
            completed_at=row["completed_at"],
        )

    @staticmethod
    def _report_from_row(row: sqlite3.Row) -> ReviewerReport:
        return ReviewerReport(
            report_id=row["report_id"],
            session_id=row["session_id"],
            assignment_id=row["assignment_id"],
            report_version=row["report_version"],
            raw_record=json.loads(row["raw_record_json"]),
            raw_record_sha256=row["raw_record_sha256"],
            summary=row["summary"],
            recommendation=row["recommendation"],
            finding_ids=tuple(json.loads(row["finding_ids_json"])),
            evidence_reference_ids=tuple(
                json.loads(row["evidence_reference_ids_json"])
            ),
            ai_assisted=bool(row["ai_assisted"]),
            human_verified=bool(row["human_verified"]),
            human_signature_ref=row["human_signature_ref"],
            submitted_at=row["submitted_at"],
            supersedes_report_id=row["supersedes_report_id"],
        )

    @staticmethod
    def _finding_from_row(row: sqlite3.Row) -> Finding:
        return Finding(
            finding_id=row["finding_id"],
            session_id=row["session_id"],
            source_report_id=row["source_report_id"],
            severity=row["severity"],
            category=row["category"],
            title=row["title"],
            description=row["description"],
            evidence_reference_ids=tuple(
                json.loads(row["evidence_reference_ids_json"])
            ),
            status=row["status"],
            remediation_required=bool(row["remediation_required"]),
            remediation_plan_accepted=bool(row["remediation_plan_accepted"]),
            raw_record=json.loads(row["raw_record_json"]),
            raw_record_sha256=row["raw_record_sha256"],
            created_at=row["created_at"],
            supersedes_finding_id=row["supersedes_finding_id"],
        )
