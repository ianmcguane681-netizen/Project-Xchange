"""Command-line entry point for local, file-first solution validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sv_engine.repositories import SQLiteSVRepository
from sv_engine.reporting import write_outputs
from sv_engine.services.engine import SolutionValidationEngine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Provena Foundry SV Engine v1")
    parser.add_argument("--input", required=True, help="Path to a structured SV JSON input")
    parser.add_argument("--output-dir", required=True, help="Directory for JSON and Markdown artifacts")
    parser.add_argument("--db", default="data/sv_engine.db", help="SQLite audit database path")
    parser.add_argument("--rules", default=None, help="Optional historical rule-set JSON path")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    input_path = Path(args.input)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if args.rules:
        from sv_engine.rules import load_rule_set

        engine = SolutionValidationEngine(load_rule_set(args.rules))
    else:
        engine = SolutionValidationEngine()
    result = engine.evaluate_dict(payload)
    final_result, paths = write_outputs(result, args.output_dir)
    SQLiteSVRepository(args.db).save(final_result)
    print(f"Verdict: {final_result.record.verdict.value.value}")
    print(f"Run ID: {final_result.manifest.run_id}")
    print(f"Decision brief: {paths['decision_brief']}")
    print(f"JSON result: {paths['sv_result']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
