from __future__ import annotations

from dataclasses import dataclass
try:
    from enum import StrEnum
except ImportError:  # Python 3.10 Streamlit Cloud compatibility.
    from enum import Enum

    class StrEnum(str, Enum):
        pass
from pathlib import Path
import time

from project_exchange.database import add_changelog, connect, count_rows, utc_now
from project_exchange.eos import add_event, add_notification
from project_exchange.ids import next_sequence_id


class PromptStatus(StrEnum):
    DRAFT = "Draft"
    APPROVED = "Approved"
    RETIRED = "Retired"


@dataclass(frozen=True)
class Prompt:
    id: str
    worker_id: str
    prompt_type: str
    version: str
    status: str
    prompt_text: str
    created_at: str
    updated_at: str


def create_prompt(
    db_path: str | Path,
    worker_id: str,
    prompt_type: str,
    prompt_text: str,
    version: str = "v1.0.0",
    status: PromptStatus = PromptStatus.DRAFT,
) -> dict[str, str]:
    if not worker_id or not prompt_type or not prompt_text:
        raise ValueError("worker_id, prompt_type, and prompt_text are required")

    with connect(db_path) as connection:
        prompt_id = next_sequence_id("PRM", count_rows(connection, "prompts"))
        now = utc_now()
        connection.execute(
            """
            INSERT INTO prompts
            (id, worker_id, prompt_type, version, status, prompt_text, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (prompt_id, worker_id, prompt_type, version, str(status), prompt_text, now, now),
        )
        connection.execute(
            """
            INSERT INTO prompt_versions
            (id, prompt_id, version, prompt_text, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (next_sequence_id("PV", count_rows(connection, "prompt_versions")), prompt_id, version, prompt_text, str(status), now),
        )
        add_changelog(connection, prompt_id, "prompt", f"Created {prompt_type} prompt for {worker_id}.")
    add_event(db_path, "PromptCreated", worker_id, "Prompt created", str(status), prompt_id)
    return get_prompt(db_path, prompt_id)


def approve_prompt(db_path: str | Path, prompt_id: str) -> dict[str, str]:
    with connect(db_path) as connection:
        connection.execute(
            "UPDATE prompts SET status = ?, updated_at = ? WHERE id = ?",
            (PromptStatus.APPROVED.value, utc_now(), prompt_id),
        )
        add_changelog(connection, prompt_id, "prompt", "Prompt approved.")
    add_notification(db_path, "prompt_approved", f"Prompt approved: {prompt_id}", prompt_id)
    add_event(db_path, "PromptApproved", None, "Prompt approved", PromptStatus.APPROVED.value, prompt_id)
    return get_prompt(db_path, prompt_id)


def retire_prompt(db_path: str | Path, prompt_id: str) -> dict[str, str]:
    with connect(db_path) as connection:
        connection.execute(
            "UPDATE prompts SET status = ?, updated_at = ? WHERE id = ?",
            (PromptStatus.RETIRED.value, utc_now(), prompt_id),
        )
        add_changelog(connection, prompt_id, "prompt", "Prompt retired.")
    return get_prompt(db_path, prompt_id)


def create_prompt_version(
    db_path: str | Path,
    prompt_id: str,
    prompt_text: str,
    version: str,
    status: PromptStatus = PromptStatus.DRAFT,
) -> dict[str, str]:
    if not prompt_text or not version:
        raise ValueError("prompt_text and version are required")
    with connect(db_path) as connection:
        prompt = connection.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,)).fetchone()
        if prompt is None:
            raise ValueError(f"Prompt not found: {prompt_id}")
        now = utc_now()
        version_id = next_sequence_id("PV", count_rows(connection, "prompt_versions"))
        connection.execute(
            """
            INSERT INTO prompt_versions
            (id, prompt_id, version, prompt_text, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (version_id, prompt_id, version, prompt_text, str(status), now),
        )
        connection.execute(
            """
            UPDATE prompts
            SET version = ?, status = ?, prompt_text = ?, updated_at = ?
            WHERE id = ?
            """,
            (version, str(status), prompt_text, now, prompt_id),
        )
        add_changelog(connection, prompt_id, "prompt", f"Created prompt version {version}.")
    return get_prompt(db_path, prompt_id)


def rollback_prompt(db_path: str | Path, prompt_id: str, version: str) -> dict[str, str]:
    with connect(db_path) as connection:
        row = connection.execute(
            "SELECT * FROM prompt_versions WHERE prompt_id = ? AND version = ? ORDER BY created_at DESC LIMIT 1",
            (prompt_id, version),
        ).fetchone()
        if row is None:
            raise ValueError(f"Prompt version not found: {prompt_id} {version}")
        now = utc_now()
        connection.execute(
            """
            UPDATE prompts
            SET version = ?, status = ?, prompt_text = ?, updated_at = ?
            WHERE id = ?
            """,
            (row["version"], row["status"], row["prompt_text"], now, prompt_id),
        )
        add_changelog(connection, prompt_id, "prompt", f"Rolled back prompt to {version}.")
    return get_prompt(db_path, prompt_id)


def run_prompt_test(
    db_path: str | Path,
    prompt_id: str,
    test_input: str,
    expected_output: str | None = None,
) -> dict[str, str | None]:
    if not test_input:
        raise ValueError("test_input is required")

    prompt = get_prompt(db_path, prompt_id)
    actual_output = f"{prompt['worker_id']} response for: {test_input[:120]}"
    result = "pass" if not expected_output or expected_output.lower() in actual_output.lower() else "fail"

    with connect(db_path) as connection:
        test_id = next_sequence_id("PTS", count_rows(connection, "prompt_tests"))
        tested_at = utc_now()
        connection.execute(
            """
            INSERT INTO prompt_tests
            (id, prompt_id, test_input, expected_output, actual_output, result, tested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (test_id, prompt_id, test_input, expected_output, actual_output, result, tested_at),
        )
        add_changelog(connection, prompt_id, "prompt", f"Prompt test {test_id} recorded as {result}.")
    if result == "fail":
        add_notification(db_path, "prompt_failed_test", f"Prompt failed test: {prompt_id}", prompt_id, "warning")
    add_event(db_path, "PromptTested", prompt["worker_id"], "Prompt tested", result, prompt_id, success=result == "pass")

    return {
        "id": test_id,
        "prompt_id": prompt_id,
        "test_input": test_input,
        "expected_output": expected_output,
        "actual_output": actual_output,
        "result": result,
        "tested_at": tested_at,
    }


def benchmark_prompt(
    db_path: str | Path,
    prompt_id: str,
    test_input: str,
    expected_output: str | None = None,
    variant_label: str = "A",
) -> dict[str, object]:
    started = time.perf_counter()
    result = run_prompt_test(db_path, prompt_id, test_input, expected_output)
    duration_ms = int((time.perf_counter() - started) * 1000)
    score = 100 if result["result"] == "pass" else 30
    with connect(db_path) as connection:
        benchmark_id = next_sequence_id("PB", count_rows(connection, "prompt_benchmarks"))
        connection.execute(
            """
            INSERT INTO prompt_benchmarks
            (id, prompt_id, variant_label, test_input, expected_output, actual_output, result, score, duration_ms,
             token_usage, response_quality, success_rate, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                benchmark_id,
                prompt_id,
                variant_label,
                test_input,
                expected_output,
                result["actual_output"],
                result["result"],
                score,
                duration_ms,
                estimate_tokens(test_input, str(result["actual_output"] or "")),
                score,
                100.0 if result["result"] == "pass" else 0.0,
                utc_now(),
            ),
        )
        connection.execute(
            """
            INSERT INTO prompt_usage (prompt_id, worker_id, token_usage, response_quality, success, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                prompt_id,
                get_prompt(db_path, prompt_id)["worker_id"],
                estimate_tokens(test_input, str(result["actual_output"] or "")),
                score,
                1 if result["result"] == "pass" else 0,
                f"Benchmark {variant_label}",
                utc_now(),
            ),
        )
    add_event(db_path, "PromptBenchmarked", None, "Prompt benchmarked", str(score), benchmark_id)
    return {"id": benchmark_id, "prompt_id": prompt_id, "variant_label": variant_label, "score": score, "duration_ms": duration_ms}


def list_prompt_benchmarks(db_path: str | Path, prompt_id: str = "") -> list[dict[str, object]]:
    values = []
    where = ""
    if prompt_id:
        where = "WHERE prompt_id = ?"
        values.append(prompt_id)
    with connect(db_path) as connection:
        rows = connection.execute(
            f"SELECT * FROM prompt_benchmarks {where} ORDER BY created_at DESC",
            values,
        ).fetchall()
    return [dict(row) for row in rows]


def get_prompt(db_path: str | Path, prompt_id: str) -> dict[str, str]:
    with connect(db_path) as connection:
        row = connection.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,)).fetchone()
    if row is None:
        raise ValueError(f"Prompt not found: {prompt_id}")
    return dict(row)


def list_prompts(db_path: str | Path) -> list[dict[str, str]]:
    with connect(db_path) as connection:
        rows = connection.execute("SELECT * FROM prompts ORDER BY created_at DESC").fetchall()
    return [dict(row) for row in rows]


def list_prompt_versions(db_path: str | Path, prompt_id: str) -> list[dict[str, str]]:
    with connect(db_path) as connection:
        rows = connection.execute(
            "SELECT * FROM prompt_versions WHERE prompt_id = ? ORDER BY created_at DESC",
            (prompt_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def search_prompts(
    db_path: str | Path,
    query: str = "",
    worker_id: str = "",
    status: str = "",
) -> list[dict[str, str]]:
    query_lower = query.lower().strip()
    worker_lower = worker_id.lower().strip()
    status_lower = status.lower().strip()
    records = list_prompts(db_path)
    filtered = []
    for record in records:
        haystack = " ".join(str(record.get(field) or "") for field in record).lower()
        if query_lower and query_lower not in haystack:
            continue
        if worker_lower and worker_lower != str(record.get("worker_id") or "").lower():
            continue
        if status_lower and status_lower != str(record.get("status") or "").lower():
            continue
        filtered.append(record)
    return filtered


def estimate_tokens(*parts: str) -> int:
    return max(1, sum(len(part.split()) for part in parts))


def list_prompt_usage(db_path: str | Path, worker_id: str = "") -> list[dict[str, object]]:
    values = []
    where = ""
    if worker_id:
        where = "WHERE worker_id = ?"
        values.append(worker_id)
    with connect(db_path) as connection:
        rows = connection.execute(
            f"SELECT * FROM prompt_usage {where} ORDER BY created_at DESC",
            values,
        ).fetchall()
    return [dict(row) for row in rows]


def best_prompt_for_worker(db_path: str | Path, worker_id: str) -> dict[str, object] | None:
    with connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT prompts.*, ROUND(AVG(prompt_usage.response_quality), 1) AS quality,
                   ROUND(100.0 * SUM(prompt_usage.success) / NULLIF(COUNT(prompt_usage.id), 0), 1) AS success_rate
            FROM prompts
            LEFT JOIN prompt_usage ON prompt_usage.prompt_id = prompts.id
            WHERE prompts.worker_id = ? AND prompts.status = ?
            GROUP BY prompts.id
            ORDER BY COALESCE(quality, 0) DESC, COALESCE(success_rate, 0) DESC, prompts.updated_at DESC
            LIMIT 1
            """,
            (worker_id, PromptStatus.APPROVED.value),
        ).fetchone()
    return dict(row) if row else None
