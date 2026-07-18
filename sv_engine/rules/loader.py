"""Load, validate and hash rule configuration as data."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sv_engine.services.hashing import canonical_hash

DEFAULT_RULE_PATH = Path(__file__).with_name("sv_rules_v1.json")


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
    }
    missing = sorted(required.difference(data))
    if missing:
        raise ValueError(f"Rule set missing keys: {', '.join(missing)}")
    category_ids = [item["id"] for item in data["categories"]]
    gate_ids = [item["id"] for item in data["gates"]]
    if len(category_ids) != 12 or len(set(category_ids)) != 12:
        raise ValueError("Rule set must define exactly 12 unique validation categories")
    if len(gate_ids) != 8 or len(set(gate_ids)) != 8:
        raise ValueError("Rule set must define exactly 8 unique mandatory gates")
    weight_total = sum(float(item["weight"]) for item in data["categories"])
    if abs(weight_total - 1.0) > 0.000001:
        raise ValueError("Category weights must total 1.0")
    return RuleSet(data=data, rule_hash=canonical_hash(data))

