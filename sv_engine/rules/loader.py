"""Load, validate and hash rule configuration as data."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sv_engine.services.hashing import canonical_hash

DEFAULT_RULE_PATH = Path(__file__).with_name("sv_rules_v1_1.json")

EXPECTED_CATEGORY_IDS = {
    "C1_PROBLEM_INHERITANCE",
    "C2_CURRENT_WORKFLOW_BASELINE",
    "C3_WORKFLOW_IMPROVEMENT",
    "C4_TECHNICAL_FEASIBILITY",
    "C5_INTERNAL_OPERATIONAL_COMPLEXITY",
    "C6_BUYER_DEFINITION",
    "C7_CUSTOMER_ECONOMICS",
    "C8_MARKET_COMPETITION",
    "C9_PROVENA_UNIT_ECONOMICS",
    "C10_ADOPTION_RISK",
    "C11_COMPONENT_REUSABILITY",
    "C12_STRATEGIC_FIT",
}
EXPECTED_GATE_IDS = {
    "G1_VERIFIED_PROBLEM_LINKAGE",
    "G2_BASELINE_SUFFICIENCY",
    "G3_TECHNICAL_PLAUSIBILITY",
    "G4_BUYER_CREDIBILITY",
    "G5_VALUE_PLAUSIBILITY",
    "G6_INTERNAL_OPERABILITY",
    "G7_COMPETITIVE_VIABILITY",
    "G8_ETHICAL_LEGAL_REGULATORY_ACCEPTABILITY",
}
TRUSTED_RULE_HASHES = {
    "d1d520b44c3953390959605cfd1923871ab8a82ba83b9ca0446da4ab883ef5ff",
    "72c59163686e91a08b944feff76af3123ee720c836e4e015b45897379236bc3a",
}


@dataclass(frozen=True)
class RuleSet:
    data: dict[str, Any]
    rule_hash: str

    @property
    def version(self) -> str:
        return str(self.data["rule_version"])

    @property
    def methodology_version(self) -> str:
        return str(self.data["methodology_version"])

    @property
    def engine_version(self) -> str:
        return str(self.data["engine_version"])


def load_rule_set(path: str | Path | None = None) -> RuleSet:
    rule_path = Path(path) if path else DEFAULT_RULE_PATH
    data = json.loads(rule_path.read_text(encoding="utf-8"))
    required = {
        "rule_version",
        "methodology_version",
        "engine_version",
        "categories",
        "gates",
        "verdict_thresholds",
        "evidence_sufficiency",
        "operability_limits",
        "global_build_claims",
    }
    missing = sorted(required.difference(data))
    if missing:
        raise ValueError(f"Rule set missing keys: {', '.join(missing)}")
    category_ids = [item["id"] for item in data["categories"]]
    gate_ids = [item["id"] for item in data["gates"]]
    if set(category_ids) != EXPECTED_CATEGORY_IDS or len(category_ids) != len(EXPECTED_CATEGORY_IDS):
        raise ValueError("Rule set category identities do not match the approved methodology contract")
    if set(gate_ids) != EXPECTED_GATE_IDS or len(gate_ids) != len(EXPECTED_GATE_IDS):
        raise ValueError("Rule set gate identities do not match the approved methodology contract")
    weight_total = sum(float(item["weight"]) for item in data["categories"])
    if abs(weight_total - 1.0) > 0.000001:
        raise ValueError("Category weights must total 1.0")
    for item in data["categories"]:
        weight = float(item["weight"])
        minimum_score = int(item["minimum_build_score"])
        minimum_confidence = float(item.get("minimum_build_confidence", 0.5))
        if weight <= 0 or not 0 <= minimum_score <= 5 or not 0 <= minimum_confidence <= 1:
            raise ValueError(f"Invalid category thresholds for {item['id']}")
        if not item.get("required_claims"):
            raise ValueError(f"Category {item['id']} must define required claims")
    for item in data["gates"]:
        if not item.get("required_true_claims"):
            raise ValueError(f"Gate {item['id']} must define required claims")
    thresholds = data["verdict_thresholds"]
    if not 0 <= float(thresholds["build_weighted_adjusted_score"]) <= 5:
        raise ValueError("Build weighted threshold must be between 0 and 5")
    if not 0 <= float(thresholds["minimum_overall_confidence"]) <= 1:
        raise ValueError("Minimum overall confidence must be between 0 and 1")
    if not 0 <= float(thresholds["borderline_tolerance"]) <= 5:
        raise ValueError("Borderline tolerance must be between 0 and 5")
    if not 0 <= float(thresholds["maximum_scenario_adjustment"]) <= 5:
        raise ValueError("Maximum scenario adjustment must be between 0 and 5")
    if set(data["global_build_claims"]) != {"prototype_cost_proportionate"}:
        raise ValueError("Rule set must retain the approved prototype-cost build claim")
    rule_hash = canonical_hash(data)
    if rule_hash not in TRUSTED_RULE_HASHES:
        raise ValueError(
            f"Rule set hash {rule_hash} is not approved. Register reviewed rule versions in code before use."
        )
    return RuleSet(data=data, rule_hash=rule_hash)
