from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any

from backend.app.contracts import EventModel, FeedbackRequest, ToolRecord
from backend.app.store.db import Database


def utc_now() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class PlatformRepository:
    def __init__(self, database: Database):
        self.database = database

    def insert_events(self, user_id: str, events: list[EventModel]) -> int:
        with self.database.connect() as connection:
            connection.executemany(
                """
                INSERT INTO events (
                    session_id, user_id, timestamp, url, event_type, target_json, value, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        event.session_id,
                        user_id,
                        event.timestamp,
                        event.url,
                        event.event_type,
                        json.dumps(event.target.model_dump(mode="json")),
                        event.value,
                        json.dumps(event.metadata),
                    )
                    for event in events
                ],
            )
            if events:
                latest_timestamp = max(event.timestamp for event in events)
                self.upsert_scheduler_state(connection, user_id=user_id, last_activity_at=latest_timestamp)
            connection.commit()
        return len(events)

    def count_pending_events(self, user_id: str) -> int:
        state = self.get_scheduler_state(user_id)
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM events WHERE user_id = ? AND id > ?",
                (user_id, state["last_processed_event_id"]),
            ).fetchone()
        return int(row["total"])

    def get_pending_events(self, user_id: str) -> list[dict[str, Any]]:
        state = self.get_scheduler_state(user_id)
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, session_id, user_id, timestamp, url, event_type, target_json, value, metadata_json
                FROM events
                WHERE user_id = ? AND id > ?
                ORDER BY id ASC
                """,
                (user_id, state["last_processed_event_id"]),
            ).fetchall()
        return [self._decode_event_row(row) for row in rows]

    def list_tool_signatures(self, user_id: str) -> list[str]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT signature FROM tools WHERE user_id = ? AND signature IS NOT NULL",
                (user_id,),
            ).fetchall()
        return [row["signature"] for row in rows]

    def save_tool(self, tool: ToolRecord) -> None:
        payload = tool.model_dump(mode="json")
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO tools (
                    id, user_id, name, description, created_at, source_event_window_json,
                    trigger_json, transformation_summary_json, artifact_json, ui_prefs_json,
                    stats_json, status, signature, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    user_id = excluded.user_id,
                    name = excluded.name,
                    description = excluded.description,
                    source_event_window_json = excluded.source_event_window_json,
                    trigger_json = excluded.trigger_json,
                    transformation_summary_json = excluded.transformation_summary_json,
                    artifact_json = excluded.artifact_json,
                    ui_prefs_json = excluded.ui_prefs_json,
                    stats_json = excluded.stats_json,
                    status = excluded.status,
                    signature = excluded.signature,
                    updated_at = excluded.updated_at
                """,
                (
                    payload["id"],
                    payload["user_id"],
                    payload["name"],
                    payload["description"],
                    payload["created_at"],
                    json.dumps(payload["source_event_window"]),
                    json.dumps(payload["trigger"]),
                    json.dumps(payload["transformation_summary"]),
                    json.dumps(payload["artifact"]),
                    json.dumps(payload["ui_prefs"]),
                    json.dumps(payload["stats"]),
                    payload["status"],
                    payload.get("signature"),
                    utc_now(),
                ),
            )
            connection.commit()

    def get_tool(self, tool_id: str) -> ToolRecord | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM tools WHERE id = ?", (tool_id,)).fetchone()
        if row is None:
            return None
        return self._decode_tool_row(row)

    def list_ready_tools_for_url(self, user_id: str) -> list[ToolRecord]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM tools WHERE user_id = ? AND status = 'ready' ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
        return [self._decode_tool_row(row) for row in rows]

    def store_artifact_record(self, artifact_id: str, user_id: str, html_path: str) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO artifacts (artifact_id, user_id, html_path, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(artifact_id) DO UPDATE SET
                    user_id = excluded.user_id,
                    html_path = excluded.html_path
                """,
                (artifact_id, user_id, html_path, utc_now()),
            )
            connection.commit()

    def get_artifact_record(self, artifact_id: str) -> dict[str, str] | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM artifacts WHERE artifact_id = ?", (artifact_id,)).fetchone()
        if row is None:
            return None
        return {
            "artifact_id": row["artifact_id"],
            "user_id": row["user_id"],
            "html_path": row["html_path"],
            "created_at": row["created_at"],
        }

    def log_tool_usage(self, tool_id: str, user_id: str, succeeded: bool, duration_ms: int) -> bool:
        tool = self.get_tool(tool_id)
        if tool is None or tool.user_id != user_id:
            return False

        stats = tool.stats.model_dump(mode="json")
        previous_count = int(stats["times_used"])
        previous_average = stats["avg_duration_ms"]
        updated_count = previous_count + 1
        updated_average = duration_ms if previous_average is None else ((previous_average * previous_count) + duration_ms) / updated_count
        stats.update(
            {
                "times_used": updated_count,
                "last_used": utc_now(),
                "avg_duration_ms": updated_average,
                "last_success": succeeded,
            }
        )
        tool.stats = tool.stats.model_validate(stats)
        self.save_tool(tool)
        return True

    def store_feedback(self, payload: FeedbackRequest) -> str:
        memory_id = f"mem_{payload.tool_id}_{int(datetime.now(tz=UTC).timestamp())}"
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO feedback (memory_id, user_id, tool_id, feedback, context, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (memory_id, payload.user_id, payload.tool_id, payload.feedback, payload.context, utc_now()),
            )
            connection.commit()
        return memory_id

    def recent_feedback(self, user_id: str, limit: int = 10) -> list[str]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT feedback, context
                FROM feedback
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [f"[{row['context']}] {row['feedback']}" for row in rows]

    def get_scheduler_state(self, user_id: str) -> dict[str, Any]:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM scheduler_state WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        if row is None:
            return {
                "user_id": user_id,
                "last_processed_event_id": 0,
                "last_detection_at": None,
                "last_activity_at": None,
            }
        return dict(row)

    def mark_events_processed(self, user_id: str, last_event_id: int, detected_at: str | None) -> None:
        with self.database.connect() as connection:
            self.upsert_scheduler_state(
                connection,
                user_id=user_id,
                last_processed_event_id=last_event_id,
                last_detection_at=detected_at,
            )
            connection.commit()

    def upsert_scheduler_state(
        self,
        connection: sqlite3.Connection,
        user_id: str,
        last_processed_event_id: int | None = None,
        last_detection_at: str | None = None,
        last_activity_at: str | None = None,
    ) -> None:
        existing = connection.execute(
            "SELECT * FROM scheduler_state WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        payload = {
            "user_id": user_id,
            "last_processed_event_id": last_processed_event_id if last_processed_event_id is not None else 0,
            "last_detection_at": last_detection_at,
            "last_activity_at": last_activity_at,
        }
        if existing is not None:
            payload["last_processed_event_id"] = (
                last_processed_event_id if last_processed_event_id is not None else existing["last_processed_event_id"]
            )
            payload["last_detection_at"] = last_detection_at if last_detection_at is not None else existing["last_detection_at"]
            payload["last_activity_at"] = last_activity_at if last_activity_at is not None else existing["last_activity_at"]

        connection.execute(
            """
            INSERT INTO scheduler_state (user_id, last_processed_event_id, last_detection_at, last_activity_at)
            VALUES (:user_id, :last_processed_event_id, :last_detection_at, :last_activity_at)
            ON CONFLICT(user_id) DO UPDATE SET
                last_processed_event_id = excluded.last_processed_event_id,
                last_detection_at = excluded.last_detection_at,
                last_activity_at = excluded.last_activity_at
            """,
            payload,
        )

    def _decode_event_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "session_id": row["session_id"],
            "user_id": row["user_id"],
            "timestamp": row["timestamp"],
            "url": row["url"],
            "event_type": row["event_type"],
            "target": json.loads(row["target_json"]),
            "value": row["value"],
            "metadata": json.loads(row["metadata_json"]),
        }

    def _decode_tool_row(self, row: sqlite3.Row) -> ToolRecord:
        return ToolRecord.model_validate(
            {
                "id": row["id"],
                "user_id": row["user_id"],
                "name": row["name"],
                "description": row["description"],
                "created_at": row["created_at"],
                "source_event_window": json.loads(row["source_event_window_json"]),
                "trigger": json.loads(row["trigger_json"]),
                "transformation_summary": json.loads(row["transformation_summary_json"]),
                "artifact": json.loads(row["artifact_json"]),
                "ui_prefs": json.loads(row["ui_prefs_json"]),
                "stats": json.loads(row["stats_json"]),
                "status": row["status"],
                "signature": row["signature"],
            }
        )
