"""Generate traceable JSON and Markdown decision artifacts."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from sv_engine.domain.models import RunManifest
from sv_engine.services.engine import EngineResult
from sv_engine.services.hashing import canonical_hash


def workflow_comparison(result: EngineResult) -> dict[str, Any]:
    current = result.record.current_workflow
    proposed = result.record.proposed_workflow
    return {
        "current_state": current.to_dict(),
        "proposed_state": proposed.to_dict(),
        "calculated_comparison": {
            "steps": {"current": len(current.steps), "proposed": len(proposed.steps)},
            "handoffs": {
                "current": sum(item.handoffs for item in current.steps),
                "proposed": sum(item.handoffs for item in proposed.steps),
            },
            "manual_entries": {
                "current": sum(item.manual_entries for item in current.steps),
                "proposed": sum(item.manual_entries for item in proposed.steps),
            },
        },
        "warning": "Unknown metrics remain unknown; the engine does not invent baseline values.",
    }


def render_markdown(result: EngineResult) -> str:
    record = result.record
    verdict = record.verdict
    lines = [
        f"# Solution Validation Decision Brief: {record.svr_id}",
        "",
        f"**Verdict:** {verdict.value.value}",
        f"**Borderline:** {'Yes' if verdict.borderline else 'No'}",
        f"**Weighted confidence-adjusted score:** {verdict.weighted_adjusted_score:.2f}",
        f"**Rule version:** {verdict.rule_version}",
        "",
        "## Decision Rationale",
        "",
        verdict.explanation,
        "",
        "This verdict concerns a bounded prototype only. It is not approval for a production product or market claim.",
        "",
        "## Verified Problem Handoff",
        "",
        f"- Verified problem: `{record.verified_problem.verified_problem_id}`",
        f"- Golden Study: `{record.verified_problem.golden_study_id}`",
        f"- Golden Study verdict: {record.verified_problem.golden_study_verdict}",
        f"- Mechanism: {record.verified_problem.problem_mechanism}",
        f"- Source families: {record.verified_problem.independent_source_family_count}",
        f"- Evidence lineage: {', '.join(record.verified_problem.evidence_lineage) or 'None recorded'}",
        "",
        "## Proposed Solution",
        "",
        f"- Solution: `{record.solution_hypothesis.solution_id}`",
        f"- Hypothesis: {record.solution_hypothesis.statement}",
        f"- Intended user: {record.solution_hypothesis.intended_user}",
        f"- Buyer hypothesis: {record.solution_hypothesis.intended_buyer_hypothesis}",
        f"- Prototype scope: {record.solution_hypothesis.prototype_scope}",
        "",
        "## Mandatory Gate Register",
        "",
        "| Gate | Status | Evidence | Explanation |",
        "|---|---|---|---|",
    ]
    for gate in record.gate_assessments:
        evidence = ", ".join(f"`{item}`" for item in gate.evidence_ids) or "None"
        detail = gate.failure_reason or gate.explanation
        lines.append(f"| {gate.gate_id} {gate.gate_name} | {gate.status.value} | {evidence} | {detail} |")
    lines.extend(
        [
            "",
            "## Category Scorecard",
            "",
            "| Category | Sufficiency | Raw | Confidence | Adjusted | Evidence |",
            "|---|---|---:|---:|---:|---|",
        ]
    )
    for category in record.category_assessments:
        evidence = ", ".join(f"`{item}`" for item in category.evidence_ids) or "None"
        lines.append(
            f"| {category.category_name} | {category.sufficiency.value} | {category.raw_score} | "
            f"{category.confidence:.2f} | {category.adjusted_score:.2f} | {evidence} |"
        )
    lines.extend(["", "## Evidence Register", ""])
    for item in record.evidence_items:
        lines.extend(
            [
                f"### {item.evidence_id}: {item.title}",
                "",
                f"- Class: {item.evidence_class.value}",
                f"- Source: {item.source_organisation} ({item.source_locator})",
                f"- Review state: {item.review_state.value}",
                f"- Relevant claim: {item.relevant_claim}",
                f"- Content hash: `{item.content_hash}`",
                f"- Limitations: {'; '.join(item.limitations) or 'None recorded'}",
                "",
            ]
        )
    lines.extend(["## Workflow Comparison", ""])
    comparison = workflow_comparison(result)["calculated_comparison"]
    for key, values in comparison.items():
        lines.append(f"- {key.replace('_', ' ').title()}: {values['current']} current -> {values['proposed']} proposed")
    lines.extend(
        [
            "",
            "## Internal Operational Complexity",
            "",
            f"- Rating: {record.internal_operational_complexity.operational_complexity_rating}",
            f"- Monthly operating effort: {record.internal_operational_complexity.monthly_operating_effort_hours}",
            f"- Support effort per customer: {record.internal_operational_complexity.support_effort_hours_per_customer}",
            f"- Update cadence: {record.internal_operational_complexity.expected_update_cadence}",
            f"- Confidence: {record.internal_operational_complexity.confidence:.2f}",
            f"- Maintenance risks: {'; '.join(record.internal_operational_complexity.principal_maintenance_risks) or 'None recorded'}",
            f"- Service risks: {'; '.join(record.internal_operational_complexity.principal_service_risks) or 'None recorded'}",
            "",
            "## Scenario and Sensitivity",
            "",
        ]
    )
    for item in record.sensitivity_results:
        lines.append(
            f"- {item.assumption}: downside `{item.downside_verdict.value}`, base `{item.base_verdict.value}`, "
            f"upside `{item.upside_verdict.value}`; material: {'yes' if item.material else 'no'}."
        )
    lines.extend(["", "## Contradictions", ""])
    if record.contradictions:
        for item in record.contradictions:
            lines.append(f"- `{item.contradiction_id}` {item.claim} ({', '.join(item.evidence_ids)})")
    else:
        lines.append("- None recorded.")
    lines.extend(["", "## Ranked Validation Plan", ""])
    if record.validation_actions:
        for item in record.validation_actions:
            lines.append(
                f"{item.rank}. {item.action} Target: {item.target}. Success: {item.success_threshold}"
            )
    else:
        lines.append("No further evidence action is required before the bounded prototype decision.")
    lines.extend(
        [
            "",
            "## Audit Hashes",
            "",
            f"- Stable business hash: `{record.stable_business_hash}`",
            f"- Input hash: `{record.input_hash}`",
            f"- Output hash: `{record.output_hash}`",
            f"- Rule-set hash: `{result.manifest.rule_set_hash}`",
            "",
            "Every material conclusion above references a structured artifact, explicit calculation, or versioned rule.",
        ]
    )
    return "\n".join(lines) + "\n"


def _write_json(path: Path, value: Any) -> str:
    content = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    path.write_text(content, encoding="utf-8")
    return canonical_hash(value)


def write_outputs(result: EngineResult, output_dir: str | Path) -> tuple[EngineResult, dict[str, Path]]:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    record = result.record
    payloads: dict[str, Any] = {
        "evidence_register": [item.to_dict() for item in record.evidence_items],
        "category_scorecard": [item.to_dict() for item in record.category_assessments],
        "gate_register": [item.to_dict() for item in record.gate_assessments],
        "missing_evidence_register": [item.to_dict() for item in record.missing_evidence],
        "contradiction_register": [item.to_dict() for item in record.contradictions],
        "workflow_comparison": workflow_comparison(result),
        "internal_operational_complexity": record.internal_operational_complexity.to_dict(),
        "customer_economics": record.customer_economics.to_dict(),
        "provena_unit_economics": record.provena_unit_economics.to_dict(),
        "scenario_sensitivity": {
            "scenarios": [item.to_dict() for item in record.scenarios],
            "sensitivity": [item.to_dict() for item in record.sensitivity_results],
        },
        "ranked_validation_plan": [item.to_dict() for item in record.validation_actions],
    }
    paths: dict[str, Path] = {}
    hashes: dict[str, str] = dict(result.manifest.artifact_hashes)
    for name, payload in payloads.items():
        path = directory / f"{name}.json"
        hashes[name] = _write_json(path, payload)
        paths[name] = path
    brief_path = directory / "decision_brief.md"
    brief = render_markdown(result)
    brief_path.write_text(brief, encoding="utf-8")
    hashes["decision_brief"] = canonical_hash(brief)
    paths["decision_brief"] = brief_path
    manifest: RunManifest = replace(result.manifest, artifact_hashes=hashes)
    final_result = EngineResult(record=result.record, manifest=manifest)
    manifest_path = directory / "run_manifest.json"
    _write_json(manifest_path, manifest.to_dict())
    paths["run_manifest"] = manifest_path
    result_path = directory / "sv_result.json"
    _write_json(result_path, final_result.to_dict())
    paths["sv_result"] = result_path
    return final_result, paths

