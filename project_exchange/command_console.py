from __future__ import annotations

from pathlib import Path

from project_exchange.head_of_functions import parse_research_topic, submit_command


def run_command(db_path: str | Path, command: str) -> dict[str, object]:
    return submit_command(db_path, command)
