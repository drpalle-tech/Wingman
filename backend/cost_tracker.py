"""Token usage and cost tracking, persisted in SQLite so totals survive restarts."""

import logging
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

logger = logging.getLogger(__name__)

# USD per 1K tokens. Check current Azure pricing for your region and deployment type.
PRICING_PER_1K: dict[str, dict[str, float]] = {
    "gpt-5-mini": {"input": 0.00025, "output": 0.002},
    "llama-3.3-70b-instruct": {"input": 0.00315, "output": 0.0126},
}
USD_TO_INR = 83

SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    session_id TEXT NOT NULL,
    task TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    input_cost REAL NOT NULL,
    output_cost REAL NOT NULL,
    total_cost REAL NOT NULL
)
"""
RECORD_COLUMNS = "timestamp, task, model, input_tokens, output_tokens, input_cost, output_cost, total_cost"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CostTracker:
    def __init__(self, model: str, db_path: Path) -> None:
        self.model = model
        self.pricing: Optional[dict[str, float]] = PRICING_PER_1K.get(model.lower())
        if self.pricing is None:
            logger.warning("No pricing configured for model %s; costs will show as 0", model)
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.session_id = uuid.uuid4().hex
        self.start_time = _now()
        with self._db() as conn:
            conn.execute("PRAGMA journal_mode=WAL")  # lets several local backends share the file
            conn.execute(SCHEMA)

    @contextmanager
    def _db(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def track_request(self, input_tokens: int, output_tokens: int, task: str) -> dict:
        price = self.pricing or {"input": 0.0, "output": 0.0}
        input_cost = input_tokens / 1000 * price["input"]
        output_cost = output_tokens / 1000 * price["output"]
        record = {
            "timestamp": _now(),
            "task": task,
            "model": self.model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost": round(input_cost, 6),
            "output_cost": round(output_cost, 6),
            "total_cost": round(input_cost + output_cost, 6),
        }
        with self._db() as conn:
            conn.execute(
                f"INSERT INTO requests (session_id, {RECORD_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (self.session_id, *record.values()),
            )
        logger.info("Tracked %s request: %d in / %d out tokens, $%.6f", task, input_tokens, output_tokens, record["total_cost"])
        return record

    def get_current_usage(self) -> dict:
        with self._db() as conn:
            total = self._totals(conn)
            session = self._totals(conn, "WHERE session_id = ?", (self.session_id,))
            by_model = conn.execute(
                "SELECT model, COUNT(*) AS requests, SUM(input_tokens + output_tokens) AS tokens, SUM(total_cost) AS cost "
                "FROM requests GROUP BY model ORDER BY cost DESC"
            ).fetchall()

        requests = max(total["requests"], 1)
        total_tokens = total["input_tokens"] + total["output_tokens"]
        return {
            "model": self.model,
            "pricing_per_1k": self.pricing,
            "total_input_tokens": total["input_tokens"],
            "total_output_tokens": total["output_tokens"],
            "total_tokens": total_tokens,
            "total_requests": total["requests"],
            "total_cost_usd": round(total["cost"], 4),
            "total_cost_inr": round(total["cost"] * USD_TO_INR, 2),
            "average_cost_per_request": round(total["cost"] / requests, 6),
            "average_tokens_per_request": round(total_tokens / requests),
            "tracking_since": total["since"],
            "session": {
                "start_time": self.start_time,
                "requests": session["requests"],
                "total_tokens": session["input_tokens"] + session["output_tokens"],
                "total_cost_usd": round(session["cost"], 4),
            },
            "by_model": [
                {"model": r["model"], "requests": r["requests"], "total_tokens": r["tokens"], "total_cost_usd": round(r["cost"], 4)}
                for r in by_model
            ],
            "start_time": self.start_time,
            "current_time": _now(),
        }

    @staticmethod
    def _totals(conn: sqlite3.Connection, where: str = "", params: tuple = ()) -> sqlite3.Row:
        return conn.execute(
            "SELECT COUNT(*) AS requests, COALESCE(SUM(input_tokens), 0) AS input_tokens, "
            "COALESCE(SUM(output_tokens), 0) AS output_tokens, COALESCE(SUM(total_cost), 0) AS cost, "
            f"MIN(timestamp) AS since FROM requests {where}",
            params,
        ).fetchone()

    def get_request_history(self, limit: int = 10) -> list[dict]:
        if limit <= 0:
            return []
        with self._db() as conn:
            rows = conn.execute(f"SELECT {RECORD_COLUMNS} FROM requests ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in reversed(rows)]

    def reset_tracking(self) -> dict:
        logger.warning("Deleting all tracked usage")
        with self._db() as conn:
            conn.execute("DELETE FROM requests")
        return self.get_current_usage()

    def export_usage_report(self) -> dict:
        with self._db() as conn:
            recorded = conn.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
        return {
            "summary": self.get_current_usage(),
            "details": {
                "pricing_per_1k": self.pricing,
                "requests_recorded": recorded,
                "recent_requests": self.get_request_history(20),
            },
            "generated_at": _now(),
        }
