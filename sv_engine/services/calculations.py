"""Deterministic workflow and economics checks shared by gates and reports."""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose
from typing import Any

from sv_engine.domain.models import (
    CustomerEconomicsModel,
    ProvenaUnitEconomicsModel,
    WorkflowModel,
)


LOWER_IS_BETTER_METRIC_TERMS = (
    "cost",
    "delay",
    "error",
    "handoff",
    "manual",
    "minute",
    "rework",
    "time",
    "wait",
)


@dataclass(frozen=True)
class WorkflowImprovementCheck:
    measurable: bool
    improvements: tuple[str, ...]
    regressions: tuple[str, ...]
    comparisons: dict[str, dict[str, float | int]]

    @property
    def supports_build(self) -> bool:
        return self.measurable and bool(self.improvements) and not self.regressions


@dataclass(frozen=True)
class EconomicsCheck:
    failures: tuple[str, ...]
    unresolved: tuple[str, ...]


def _workflow_totals(workflow: WorkflowModel) -> dict[str, int]:
    return {
        "steps": len(workflow.steps),
        "handoffs": sum(item.handoffs for item in workflow.steps),
        "manual_entries": sum(item.manual_entries for item in workflow.steps),
        "duplicated_work_steps": sum(1 for item in workflow.steps if item.duplicated_work),
        "documented_errors": sum(len(item.errors) for item in workflow.steps),
        "documented_rework": sum(len(item.rework) for item in workflow.steps),
    }


def compare_workflows(current: WorkflowModel, proposed: WorkflowModel) -> WorkflowImprovementCheck:
    """Compare only explicit lower-is-better measures; unknown direction earns no credit."""

    current_totals = _workflow_totals(current)
    proposed_totals = _workflow_totals(proposed)
    comparisons: dict[str, dict[str, float | int]] = {
        key: {"current": current_totals[key], "proposed": proposed_totals[key]}
        for key in current_totals
    }
    improvements: list[str] = []
    regressions: list[str] = []

    for key in (
        "handoffs",
        "manual_entries",
        "duplicated_work_steps",
        "documented_errors",
        "documented_rework",
    ):
        current_value = current_totals[key]
        proposed_value = proposed_totals[key]
        if proposed_value < current_value:
            improvements.append(f"{key}: {current_value} -> {proposed_value}")
        elif proposed_value > current_value:
            regressions.append(f"{key}: {current_value} -> {proposed_value}")

    current_metrics = {
        (item.name.strip().lower(), item.unit.strip().lower()): item
        for item in current.metrics
        if isinstance(item.value, (int, float)) and not isinstance(item.value, bool)
    }
    for proposed_metric in proposed.metrics:
        if not isinstance(proposed_metric.value, (int, float)) or isinstance(proposed_metric.value, bool):
            continue
        metric_name = proposed_metric.name.strip().lower()
        key = (metric_name, proposed_metric.unit.strip().lower())
        current_metric = current_metrics.get(key)
        if current_metric is None or not any(term in metric_name for term in LOWER_IS_BETTER_METRIC_TERMS):
            continue
        current_value = float(current_metric.value)  # type: ignore[arg-type]
        proposed_value = float(proposed_metric.value)
        comparison_key = f"metric:{metric_name}:{key[1]}"
        comparisons[comparison_key] = {"current": current_value, "proposed": proposed_value}
        if proposed_value < current_value:
            improvements.append(f"{proposed_metric.name}: {current_value:g} -> {proposed_value:g} {proposed_metric.unit}")
        elif proposed_value > current_value:
            regressions.append(f"{proposed_metric.name}: {current_value:g} -> {proposed_value:g} {proposed_metric.unit}")

    measurable = bool(current.steps and proposed.steps and comparisons)
    return WorkflowImprovementCheck(
        measurable=measurable,
        improvements=tuple(improvements),
        regressions=tuple(regressions),
        comparisons=comparisons,
    )


def customer_economics_check(model: CustomerEconomicsModel) -> EconomicsCheck:
    failures: list[str] = []
    unresolved: list[str] = []
    if model.annual_value is None or model.price_assumption is None:
        unresolved.append("Customer annual value and price assumptions are required.")
    else:
        if model.annual_value <= 0:
            failures.append("Calculated customer annual value must be positive.")
        if model.price_assumption <= 0:
            failures.append("Customer price assumption must be positive.")
        if model.annual_value > 0 and model.price_assumption > model.annual_value:
            failures.append("Customer price exceeds the stated annual value.")
        if model.payback_months is None:
            unresolved.append("Customer payback period is required.")
        elif model.payback_months <= 0:
            failures.append("Customer payback period must be positive.")
        elif model.annual_value > 0 and model.price_assumption > 0:
            calculated_payback = model.price_assumption / model.annual_value * 12
            if not isclose(model.payback_months, calculated_payback, rel_tol=0.05, abs_tol=0.1):
                failures.append(
                    f"Customer payback {model.payback_months:g} months does not reconcile to "
                    f"the calculated {calculated_payback:.2f} months."
                )
    if not model.formulae:
        unresolved.append("Customer economics formulae are required.")
    if not model.assumptions:
        unresolved.append("Customer economics assumptions are required.")
    if not model.evidence_ids:
        unresolved.append("Customer economics evidence references are required.")
    return EconomicsCheck(tuple(failures), tuple(unresolved))


def provena_economics_check(model: ProvenaUnitEconomicsModel) -> EconomicsCheck:
    failures: list[str] = []
    unresolved: list[str] = []
    required: dict[str, float | None] = {
        "development cost": model.development_cost,
        "implementation cost per customer": model.implementation_cost_per_customer,
        "annual cost to serve per customer": model.annual_cost_to_serve_per_customer,
        "annual price": model.annual_price,
        "gross margin percent": model.gross_margin_percent,
        "break-even customer count": model.break_even_customer_count,
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        unresolved.append(f"Provena unit economics missing: {', '.join(missing)}.")
    for name, value in required.items():
        if value is not None and value < 0:
            failures.append(f"Provena {name} cannot be negative.")

    price = model.annual_price
    annual_cost = model.annual_cost_to_serve_per_customer
    implementation_cost = model.implementation_cost_per_customer
    development_cost = model.development_cost
    if price is not None and annual_cost is not None:
        if price <= 0:
            failures.append("Provena annual price must be positive.")
        elif price <= annual_cost:
            failures.append("Provena annual contribution margin is non-positive.")
        elif model.gross_margin_percent is not None:
            calculated_margin = (price - annual_cost) / price * 100
            if not isclose(model.gross_margin_percent, calculated_margin, rel_tol=0.01, abs_tol=0.1):
                failures.append(
                    f"Gross margin {model.gross_margin_percent:g}% does not reconcile to "
                    f"the calculated {calculated_margin:.2f}%."
                )

    if price is not None and annual_cost is not None and implementation_cost is not None:
        contribution = price - annual_cost - implementation_cost
        if contribution <= 0:
            failures.append("First-year contribution after implementation cost is non-positive.")
        elif development_cost is not None and model.break_even_customer_count is not None:
            calculated_break_even = development_cost / contribution
            if not isclose(model.break_even_customer_count, calculated_break_even, rel_tol=0.02, abs_tol=0.02):
                failures.append(
                    f"Break-even count {model.break_even_customer_count:g} does not reconcile to "
                    f"the calculated {calculated_break_even:.2f}."
                )
    if not model.formulae:
        unresolved.append("Provena unit economics formulae are required.")
    if not model.assumptions:
        unresolved.append("Provena unit economics assumptions are required.")
    if not model.evidence_ids:
        unresolved.append("Provena unit economics evidence references are required.")
    return EconomicsCheck(tuple(dict.fromkeys(failures)), tuple(unresolved))


def workflow_comparison_payload(current: WorkflowModel, proposed: WorkflowModel) -> dict[str, Any]:
    check = compare_workflows(current, proposed)
    return {
        "current_state": current.to_dict(),
        "proposed_state": proposed.to_dict(),
        "calculated_comparison": check.comparisons,
        "measurable": check.measurable,
        "supports_build": check.supports_build,
        "improvements": list(check.improvements),
        "regressions": list(check.regressions),
        "warning": "Only explicit lower-is-better measures are treated as improvements.",
    }
