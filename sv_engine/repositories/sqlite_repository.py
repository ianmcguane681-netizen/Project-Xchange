"""Append-only SQLite persistence for SV Engine runs and artifacts."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from sv_engine.services.engine import EngineResult


class SQLiteSVRepository:
    def __init__(self, db_path: str | Path = "data/sv_engine.db") -> None:
        self.db_path = Path(db_path)

    def initialise(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS sv_runs (
                    execution_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    svr_id TEXT NOT NULL,
                    rule_version TEXT NOT NULL,
                    stable_business_hash TEXT NOT NULL,
                    input_hash TEXT NOT NULL,
                    output_hash TEXT NOT NULL,
                    verdict TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS solution_validation_records (
                    execution_id TEXT PRIMARY KEY,
                    svr_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    FOREIGN KEY(execution_id) REFERENCES sv_runs(execution_id)
                );
                CREATE TABLE IF NOT EXISTS sv_evidence (
                    execution_id TEXT NOT NULL,
                    evidence_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY(execution_id, evidence_id)
                );
                CREATE TABLE IF NOT EXISTS sv_workflows (
                    execution_id TEXT NOT NULL,
                    workflow_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY(execution_id, workflow_id)
                );
                CREATE TABLE IF NOT EXISTS sv_category_assessments (
                    execution_id TEXT NOT NULL,
                    category_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY(execution_id, category_id)
                );
                CREATE TABLE IF NOT EXISTS sv_gate_assessments (
                    execution_id TEXT NOT NULL,
                    gate_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY(execution_id, gate_id)
                );
                CREATE TABLE IF NOT EXISTS sv_scenarios (
                    execution_id TEXT NOT NULL,
                    scenario_name TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY(execution_id, scenario_name)
                );
                CREATE TABLE IF NOT EXISTS sv_validation_actions (
                    execution_id TEXT NOT NULL,
                    action_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY(execution_id, action_id)
                );
                CREATE TABLE IF NOT EXISTS sv_verdicts (
                    execution_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sv_run_manifests (
                    execution_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL
                );
                """
            )

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value, sort_keys=True, ensure_ascii=True)

    def save(self, result: EngineResult) -> None:
        self.initialise()
        record = result.record
        manifest = result.manifest
        execution_id = manifest.execution_id
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                "INSERT INTO sv_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    execution_id,
                    manifest.run_id,
                    record.svr_id,
                    manifest.scoring_rule_version,
                    record.stable_business_hash,
                    record.input_hash,
                    record.output_hash,
                    record.verdict.value.value,
                    manifest.created_at,
                ),
            )
            connection.execute(
                "INSERT INTO solution_validation_records VALUES (?, ?, ?)",
                (execution_id, record.svr_id, self._json(record.to_dict())),
            )
            for item in record.evidence_items:
                connection.execute(
                    "INSERT INTO sv_evidence VALUES (?, ?, ?)",
                    (execution_id, item.evidence_id, self._json(item.to_dict())),
                )
            for item in (record.current_workflow, record.proposed_workflow):
                connection.execute(
                    "INSERT INTO sv_workflows VALUES (?, ?, ?)",
                    (execution_id, item.workflow_id, self._json(item.to_dict())),
                )
            for item in record.category_assessments:
                connection.execute(
                    "INSERT INTO sv_category_assessments VALUES (?, ?, ?)",
                    (execution_id, item.category_id, self._json(item.to_dict())),
                )
            for item in record.gate_assessments:
                connection.execute(
                    "INSERT INTO sv_gate_assessments VALUES (?, ?, ?)",
                    (execution_id, item.gate_id, self._json(item.to_dict())),
                )
            for item in record.scenarios:
                connection.execute(
                    "INSERT INTO sv_scenarios VALUES (?, ?, ?)",
                    (execution_id, item.name.value, self._json(item.to_dict())),
                )
            for item in record.validation_actions:
                connection.execute(
                    "INSERT INTO sv_validation_actions VALUES (?, ?, ?)",
                    (execution_id, item.action_id, self._json(item.to_dict())),
                )
            connection.execute(
                "INSERT INTO sv_verdicts VALUES (?, ?)",
                (execution_id, self._json(record.verdict.to_dict())),
            )
            connection.execute(
                "INSERT INTO sv_run_manifests VALUES (?, ?)",
                (execution_id, self._json(manifest.to_dict())),
            )

    def list_runs(self) -> list[dict[str, Any]]:
        self.initialise()
        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT * FROM sv_runs ORDER BY created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def load_record(self, execution_id: str) -> dict[str, Any] | None:
        self.initialise()
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT payload_json FROM solution_validation_records WHERE execution_id = ?",
                (execution_id,),
            ).fetchone()
        return json.loads(row[0]) if row else None

