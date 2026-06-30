from __future__ import annotations

import json
from pathlib import Path

from project_exchange.database import connect, row_to_dict, utc_now
from project_exchange.eos import add_event


def get_setting(db_path: str | Path, key: str, default: str = "") -> str:
    with connect(db_path) as connection:
        row = connection.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return str(row["value"]) if row else default


def set_setting(db_path: str | Path, key: str, value: str, category: str = "general") -> dict[str, object]:
    with connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO settings (key, value, category, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, category = excluded.category, updated_at = excluded.updated_at
            """,
            (key, value, category, utc_now()),
        )
    add_event(db_path, "SettingUpdated", None, "Setting updated", key, key)
    return {"key": key, "value": value, "category": category}


def list_settings(db_path: str | Path) -> list[dict[str, object]]:
    with connect(db_path) as connection:
        rows = connection.execute("SELECT * FROM settings ORDER BY category, key").fetchall()
    return [row_to_dict(row) for row in rows]


def send_worker_message(
    db_path: str | Path,
    sender_worker: str,
    receiver_worker: str,
    body: str,
    job_id: str = "",
    message_type: str = "handoff",
    priority: int = 3,
    payload: dict[str, object] | None = None,
    status: str = "sent",
) -> dict[str, object]:
    with connect(db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO worker_messages
            (sender_worker, receiver_worker, job_id, message_type, body, priority, payload, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sender_worker,
                receiver_worker,
                job_id,
                message_type,
                body,
                priority,
                json.dumps(payload or {}, ensure_ascii=False),
                status,
                utc_now(),
            ),
        )
    add_event(db_path, "WorkerMessageSent", sender_worker, "Worker message sent", receiver_worker, str(cursor.lastrowid))
    return {
        "id": cursor.lastrowid,
        "sender_worker": sender_worker,
        "receiver_worker": receiver_worker,
        "body": body,
        "priority": priority,
        "payload": payload or {},
        "status": status,
    }


def route_worker_message(
    db_path: str | Path,
    sender_worker: str,
    receiver_worker: str,
    body: str,
    job_id: str = "",
    priority: int = 3,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    inbound = send_worker_message(
        db_path,
        sender_worker,
        "PX-H001",
        body,
        job_id,
        "worker_to_head",
        priority,
        payload,
        "received",
    )
    outbound = send_worker_message(
        db_path,
        "PX-H001",
        receiver_worker,
        body,
        job_id,
        "head_to_worker",
        priority,
        payload,
        "sent",
    )
    return {"inbound": inbound, "outbound": outbound}


def list_worker_messages(db_path: str | Path) -> list[dict[str, object]]:
    with connect(db_path) as connection:
        rows = connection.execute("SELECT * FROM worker_messages ORDER BY created_at DESC, id DESC").fetchall()
    return [row_to_dict(row) for row in rows]


def add_knowledge_edge(
    db_path: str | Path,
    source_type: str,
    source_id: str,
    relationship: str,
    target_type: str,
    target_id: str,
    metadata: dict[str, object] | None = None,
) -> None:
    with connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO knowledge_edges
            (source_type, source_id, relationship, target_type, target_id, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (source_type, source_id, relationship, target_type, target_id, json.dumps(metadata or {}), utc_now()),
        )


def list_knowledge_edges(db_path: str | Path, entity_id: str = "") -> list[dict[str, object]]:
    values = []
    where = ""
    if entity_id:
        where = "WHERE source_id = ? OR target_id = ?"
        values = [entity_id, entity_id]
    with connect(db_path) as connection:
        rows = connection.execute(
            f"SELECT * FROM knowledge_edges {where} ORDER BY created_at DESC, id DESC",
            values,
        ).fetchall()
    return [row_to_dict(row) for row in rows]
