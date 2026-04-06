"""SQLite database helpers for thread inspection records and settings."""

from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "inspections.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = _connect()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS inspections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            thread_type TEXT NOT NULL,
            pitch_mm REAL,
            diameter_mm REAL,
            ai_result TEXT,
            ai_confidence REAL,
            rule_result TEXT,
            final_decision TEXT,
            image_path TEXT,
            notes TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )

    defaults = {
        "calibration_factor_mm_per_px": 0.05,
        "default_tolerance_pct": 8.0,
        "thread_standards": {
            "M8": {"pitch_mm": 1.25, "diameter_mm": 8.0},
            "M10": {"pitch_mm": 1.50, "diameter_mm": 10.0},
            "M12": {"pitch_mm": 1.75, "diameter_mm": 12.0},
        },
        "camera_source": "0",
    }

    for key, value in defaults.items():
        cur.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, json.dumps(value)),
        )

    conn.commit()
    conn.close()


def set_setting(key: str, value: Any) -> None:
    conn = _connect()
    conn.execute(
        """
        INSERT INTO settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """,
        (key, json.dumps(value)),
    )
    conn.commit()
    conn.close()


def get_setting(key: str, default: Any = None) -> Any:
    conn = _connect()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    if row is None:
        return default
    try:
        return json.loads(row["value"])
    except json.JSONDecodeError:
        return row["value"]


def get_all_settings() -> Dict[str, Any]:
    conn = _connect()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()

    parsed: Dict[str, Any] = {}
    for row in rows:
        try:
            parsed[row["key"]] = json.loads(row["value"])
        except json.JSONDecodeError:
            parsed[row["key"]] = row["value"]
    return parsed


def insert_inspection(record: Dict[str, Any]) -> int:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO inspections (
            timestamp, thread_type, pitch_mm, diameter_mm,
            ai_result, ai_confidence, rule_result, final_decision,
            image_path, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record.get("timestamp"),
            record.get("thread_type", "UNKNOWN"),
            record.get("pitch_mm"),
            record.get("diameter_mm"),
            record.get("ai_result"),
            record.get("ai_confidence"),
            record.get("rule_result"),
            record.get("final_decision"),
            record.get("image_path"),
            record.get("notes"),
        ),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return int(row_id)


def get_latest_result() -> Optional[Dict[str, Any]]:
    conn = _connect()
    row = conn.execute(
        "SELECT * FROM inspections ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return dict(row)


def get_recent_logs(limit: int = 15) -> List[Dict[str, Any]]:
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM inspections ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats() -> Dict[str, Any]:
    conn = _connect()

    total = conn.execute("SELECT COUNT(*) AS c FROM inspections").fetchone()["c"]
    pass_count = conn.execute(
        "SELECT COUNT(*) AS c FROM inspections WHERE final_decision='PASS'"
    ).fetchone()["c"]
    fail_count = conn.execute(
        "SELECT COUNT(*) AS c FROM inspections WHERE final_decision='FAIL'"
    ).fetchone()["c"]

    trend_rows = conn.execute(
        """
        SELECT
            DATE(timestamp) AS day,
            SUM(CASE WHEN final_decision='PASS' THEN 1 ELSE 0 END) AS pass_count,
            SUM(CASE WHEN final_decision='FAIL' THEN 1 ELSE 0 END) AS fail_count
        FROM inspections
        GROUP BY DATE(timestamp)
        ORDER BY day DESC
        LIMIT 14
        """
    ).fetchall()

    conn.close()

    pass_pct = (pass_count / total * 100.0) if total else 0.0
    fail_pct = (fail_count / total * 100.0) if total else 0.0

    return {
        "total": total,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "pass_percentage": round(pass_pct, 2),
        "fail_percentage": round(fail_pct, 2),
        "inspection_trend": [dict(r) for r in reversed(trend_rows)],
    }


def export_inspections_csv(out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    conn = _connect()
    rows = conn.execute("SELECT * FROM inspections ORDER BY id DESC").fetchall()
    conn.close()

    if not rows:
        headers = [
            "id",
            "timestamp",
            "thread_type",
            "pitch_mm",
            "diameter_mm",
            "ai_result",
            "ai_confidence",
            "rule_result",
            "final_decision",
            "image_path",
            "notes",
        ]
        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
        return out_path

    headers = rows[0].keys()
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))

    return out_path
