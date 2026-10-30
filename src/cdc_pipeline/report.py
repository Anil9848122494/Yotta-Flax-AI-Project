from __future__ import annotations

import json
import sqlite3
from typing import Any


def build_report(connection: sqlite3.Connection, run_id: str | None = None) -> dict[str, Any]:
    current = connection.execute(
        """SELECT COUNT(*) AS all_count,
                  SUM(CASE WHEN is_deleted = 0 THEN 1 ELSE 0 END) AS active_count,
                  SUM(CASE WHEN is_deleted = 1 THEN 1 ELSE 0 END) AS deleted_count,
                  COALESCE(SUM(CASE WHEN is_deleted = 0 THEN balance ELSE 0 END), 0) AS active_balance
           FROM current_accounts"""
    ).fetchone()
    totals = connection.execute(
        """SELECT COUNT(*) AS history_count,
                  SUM(CASE WHEN disposition = 'applied' THEN 1 ELSE 0 END) AS applied_history_count,
                  SUM(CASE WHEN disposition = 'stale' THEN 1 ELSE 0 END) AS stale_history_count
           FROM event_history"""
    ).fetchone()
    rejects = connection.execute("SELECT COUNT(*) AS reject_count FROM quarantine").fetchone()
    result: dict[str, Any] = {
        "current_accounts": {
            "total_including_tombstones": current["all_count"],
            "active": current["active_count"] or 0,
            "deleted_tombstones": current["deleted_count"] or 0,
            "active_balance_total": round(current["active_balance"], 2),
        },
        "event_history": {
            "total": totals["history_count"],
            "applied": totals["applied_history_count"] or 0,
            "stale": totals["stale_history_count"] or 0,
        },
        "quarantine_total": rejects["reject_count"],
    }
    if run_id is not None:
        row = connection.execute(
            "SELECT * FROM pipeline_runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        result["run"] = dict(row) if row else None
    return result


def format_report(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True)
