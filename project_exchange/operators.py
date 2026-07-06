from __future__ import annotations

import importlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from project_exchange.eos import worker_registry


@dataclass(frozen=True)
class ProvenaOperator:
    operator_id: str
    operator_name: str
    system_function: str
    backend_module: str
    backend_function: str
    status_source: str
    input_contract: str
    output_contract: str
    activity_table: str = "worker_activity"


OPERATOR_DEFINITIONS: tuple[ProvenaOperator, ...] = (
    ProvenaOperator(
        "PX-H001",
        "Head of Functions Operator",
        "Plans commands, schedules jobs, routes operator messages, refreshes memory, and produces operating briefs.",
        "project_exchange.command_console",
        "run_command",
        "workers.status",
        "Natural-language command or operating schedule payload.",
        "Execution plan, jobs, operator messages, memory update, and recommendations.",
    ),
    ProvenaOperator(
        "PX-R001",
        "Research Acquisition Operator",
        "Turns real source material or configured provider output into structured research packages.",
        "project_exchange.research_engine",
        "run_internet_research",
        "workers.status",
        "Market/company/source payload with provider or manual evidence text.",
        "Research record, research package, extracted complaints, and pending audit job.",
    ),
    ProvenaOperator(
        "PX-A001",
        "Evidence Verification Operator",
        "Audits research evidence, checks traceability, scores confidence, and blocks weak records.",
        "workers.px_a001_audit.audit_engine",
        "run_audit",
        "workers.status",
        "Research record with source URL, source text, complaint summary, and evidence score.",
        "Audit decision, evidence checklist, reasoning summary, and approval/block status.",
    ),
    ProvenaOperator(
        "PX-L001",
        "Library Steward Operator",
        "Stores approved audit outputs as versioned canonical library records with lineage.",
        "workers.px_l001_library.library_manager",
        "store_approved_record",
        "workers.status",
        "Approved audit report and linked research record.",
        "Library record, changelog entry, lineage fields, and source tracking.",
    ),
)


def operator_definitions() -> list[dict[str, object]]:
    return [asdict(operator) for operator in OPERATOR_DEFINITIONS]


def operator_function(operator: ProvenaOperator) -> Callable[..., object]:
    module = importlib.import_module(operator.backend_module)
    function = getattr(module, operator.backend_function)
    if not callable(function):
        raise ValueError(f"{operator.operator_id} backend function is not callable")
    return function


def validate_operator_contracts() -> list[dict[str, object]]:
    checks: list[dict[str, object]] = []
    for operator in OPERATOR_DEFINITIONS:
        status = "pass"
        error = ""
        try:
            operator_function(operator)
        except Exception as exc:
            status = "fail"
            error = str(exc)
        missing = [
            field
            for field in [
                "backend_module",
                "backend_function",
                "status_source",
                "input_contract",
                "output_contract",
                "activity_table",
            ]
            if not getattr(operator, field)
        ]
        if missing:
            status = "fail"
            error = f"Missing fields: {', '.join(missing)}"
        checks.append(
            {
                "operator_id": operator.operator_id,
                "operator_name": operator.operator_name,
                "backend_module": operator.backend_module,
                "backend_function": operator.backend_function,
                "status": status,
                "error": error,
            }
        )
    return checks


def provena_operator_registry(db_path: str | Path) -> list[dict[str, object]]:
    runtime = {str(row["id"]): row for row in worker_registry(db_path)}
    checks = {row["operator_id"]: row for row in validate_operator_contracts()}
    records: list[dict[str, object]] = []
    for operator in OPERATOR_DEFINITIONS:
        runtime_row = runtime.get(operator.operator_id, {})
        check = checks.get(operator.operator_id, {})
        records.append(
            {
                **asdict(operator),
                "status": runtime_row.get("status") or "Unknown",
                "health": runtime_row.get("health") or runtime_row.get("health_percent") or "Unknown",
                "current_load": runtime_row.get("current_load", 0),
                "jobs_completed": runtime_row.get("jobs_completed", 0),
                "last_run": runtime_row.get("last_run") or "",
                "contract_status": check.get("status") or "fail",
                "contract_error": check.get("error") or "",
                "input": operator.input_contract,
                "output": operator.output_contract,
                "traceable_activity": operator.activity_table,
            }
        )
    return records
