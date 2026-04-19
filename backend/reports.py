from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from .localization import format_datetime_mr
from .metadata import build_error_payload, localize_prediction_payload


class ReportStore:
    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.initialise()

    def connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialise(self):
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_path TEXT,
                    crop TEXT,
                    disease TEXT,
                    marathi_name TEXT,
                    category TEXT,
                    severity TEXT,
                    confidence REAL,
                    remedy TEXT,
                    prevention TEXT,
                    weather_note TEXT,
                    cause TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            existing_columns = {row["name"] for row in connection.execute("PRAGMA table_info(reports)")}
            if "payload_json" not in existing_columns:
                connection.execute("ALTER TABLE reports ADD COLUMN payload_json TEXT")

    def _normalise_timestamp(self, value):
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    def _row_to_report(self, row):
        if row is None:
            return None

        payload = build_error_payload("जतन केलेला अहवाल अपूर्ण आहे.")
        if row["payload_json"]:
            try:
                payload = json.loads(row["payload_json"])
            except json.JSONDecodeError:
                payload = build_error_payload("जतन केलेल्या अहवालातील माहिती वाचता आली नाही.")

        created_at = self._normalise_timestamp(row["created_at"])
        payload = localize_prediction_payload(payload)
        payload.setdefault("report_payload", {})
        payload["report_payload"]["id"] = row["id"]
        payload["report_payload"]["created_at"] = row["created_at"] or ""
        payload["report_payload"]["created_at_display"] = format_datetime_mr(created_at)

        return {
            "id": row["id"],
            "crop": payload.get("crop", row["crop"] or ""),
            "disease": payload.get("disease", row["disease"] or ""),
            "severity": row["severity"] or payload.get("severity", "medium"),
            "confidence": int(round(row["confidence"] or payload.get("confidence", 0))),
            "created_at": created_at,
            "created_at_display": format_datetime_mr(created_at),
            "payload": payload,
            "report_payload": payload["report_payload"],
        }

    def save_report(self, payload: dict):
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO reports (
                    image_path,
                    crop,
                    disease,
                    marathi_name,
                    category,
                    severity,
                    confidence,
                    remedy,
                    prevention,
                    weather_note,
                    cause,
                    payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.get("image_url", ""),
                    payload.get("crop", ""),
                    payload.get("disease", ""),
                    payload.get("marathi_name", ""),
                    payload.get("category", ""),
                    payload.get("severity", "medium"),
                    float(payload.get("confidence", 0)),
                    payload.get("remedy", ""),
                    payload.get("prevention", ""),
                    payload.get("weather_note", ""),
                    payload.get("cause", ""),
                    json.dumps(payload),
                ),
            )
            report_id = cursor.lastrowid

        return self.get_report(report_id)

    def list_reports(self):
        with self.connect() as connection:
            rows = connection.execute("SELECT * FROM reports ORDER BY datetime(created_at) DESC, id DESC").fetchall()
        return [self._row_to_report(row) for row in rows]

    def get_report(self, report_id: int):
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
        return self._row_to_report(row)

    def delete_report(self, report_id: int):
        with self.connect() as connection:
            connection.execute("DELETE FROM reports WHERE id = ?", (report_id,))
