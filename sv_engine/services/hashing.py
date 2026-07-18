"""Canonical hashing and business-change classification."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable

DEFAULT_METADATA_FIELDS = {
    "retrieval_timestamp",
    "retrieved_at",
    "created_at",
    "updated_at",
    "execution_id",
    "metadata",
    "input_hash",
    "output_hash",
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def stable_business_value(value: Any, metadata_fields: Iterable[str] = DEFAULT_METADATA_FIELDS) -> Any:
    ignored = DEFAULT_METADATA_FIELDS.union(metadata_fields)
    if isinstance(value, dict):
        return {
            str(key): stable_business_value(item, ignored)
            for key, item in sorted(value.items())
            if key not in ignored
        }
    if isinstance(value, list):
        return [stable_business_value(item, ignored) for item in value]
    return value


def stable_business_hash(value: Any, metadata_fields: Iterable[str] = DEFAULT_METADATA_FIELDS) -> str:
    return canonical_hash(stable_business_value(value, metadata_fields))


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            child = f"{prefix}.{key}" if prefix else str(key)
            result.update(_flatten(item, child))
        return result
    if isinstance(value, list):
        result = {}
        for index, item in enumerate(value):
            child = f"{prefix}[{index}]"
            result.update(_flatten(item, child))
        return result
    return {prefix: value}


@dataclass(frozen=True)
class ChangeClassification:
    classification: str
    changed_paths: tuple[str, ...]


def classify_input_change(
    previous: dict[str, Any],
    current: dict[str, Any],
    metadata_fields: Iterable[str] = DEFAULT_METADATA_FIELDS,
) -> ChangeClassification:
    if canonical_hash(previous) == canonical_hash(current):
        return ChangeClassification("NO_CHANGE", ())
    previous_business = stable_business_value(previous, metadata_fields)
    current_business = stable_business_value(current, metadata_fields)
    if canonical_hash(previous_business) == canonical_hash(current_business):
        return ChangeClassification("METADATA_ONLY", ())
    old_flat = _flatten(previous_business)
    new_flat = _flatten(current_business)
    changed = tuple(
        sorted(path for path in set(old_flat) | set(new_flat) if old_flat.get(path) != new_flat.get(path))
    )
    return ChangeClassification("MATERIAL_BUSINESS_CHANGE", changed)
