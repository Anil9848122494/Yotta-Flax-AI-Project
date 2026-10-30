from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .db import connect

BASE_FIELDS = {"event_id", "account_id", "operation", "event_ts"}
PAYLOAD_FIELDS = {"account_name", "region_id", "balance"}
ALLOWED_FIELDS = BASE_FIELDS | PAYLOAD_FIELDS


class PipelineExecutionError(RuntimeError):
    """Unexpected pipeline failure after recording a failed run."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def normalize_event_time(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("event_ts must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("event_ts must be a valid ISO-8601 timestamp") from error
    if parsed.tzinfo is None:
        raise ValueError("event_ts must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _quarantine(
    connection: sqlite3.Connection,
    run_id: str,
    source_file: str,
    line_number: int,
    raw_record: str,
    reason: str,
    event_id: str | None = None,
) -> None:
    connection.execute(
        """INSERT INTO quarantine
           (run_id, source_file, line_number, event_id, raw_record, reason, rejected_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (run_id, source_file, line_number, event_id, raw_record, reason, utc_now()),
    )


def _extract_source_event_id(raw_record: str) -> str | None:
    try:
        source_record = json.loads(raw_record)
    except json.JSONDecodeError:
        return None
    if not isinstance(source_record, dict):
        return None
    event_id = source_record.get("event_id")
    return event_id if isinstance(event_id, str) and event_id.strip() else None


def _validate(
    connection: sqlite3.Connection, raw_record: str
) -> tuple[dict[str, Any] | None, str | None]:
    try:
        event = json.loads(raw_record)
    except json.JSONDecodeError:
        return None, "malformed_json"
    if not isinstance(event, dict):
        return None, "record_must_be_json_object"

    event_id = event.get("event_id")
    if set(event) - ALLOWED_FIELDS:
        unknown = ",".join(sorted(set(event) - ALLOWED_FIELDS))
        return None, f"unexpected_fields:{unknown}"
    missing_base = BASE_FIELDS - set(event)
    if missing_base:
        return None, f"missing_required_fields:{','.join(sorted(missing_base))}"
    if not isinstance(event_id, str) or not event_id.strip():
        return None, "event_id_must_be_non_empty_string"
    account_id = event.get("account_id")
    if not isinstance(account_id, str) or not account_id.strip():
        return None, "account_id_must_be_non_empty_string"
    operation = event.get("operation")
    if operation not in ("insert", "update", "delete"):
        return None, "operation_must_be_insert_update_or_delete"

    try:
        event["event_ts"] = normalize_event_time(event.get("event_ts"))
    except ValueError as error:
        return None, str(error)

    if operation != "delete":
        missing_payload = PAYLOAD_FIELDS - set(event)
        if missing_payload:
            return None, f"missing_required_fields:{','.join(sorted(missing_payload))}"
        name = event.get("account_name")
        if not isinstance(name, str) or not name.strip():
            return None, "account_name_must_be_non_empty_string"
        region_id = event.get("region_id")
        if not isinstance(region_id, str) or not region_id:
            return None, "region_id_must_be_non_empty_string"
        if connection.execute(
            "SELECT 1 FROM regions WHERE region_id = ?", (region_id,)
        ).fetchone() is None:
            return None, f"invalid_reference:region_id:{region_id}"
        balance = event.get("balance")
        if isinstance(balance, bool) or not isinstance(balance, (int, float)):
            return None, "balance_must_be_numeric"
        if not math.isfinite(balance) or balance < 0:
            return None, "balance_must_be_finite_and_non_negative"
        event["balance"] = float(balance)

    return event, None


def _process_line(
    connection: sqlite3.Connection,
    run_id: str,
    source_file: str,
    line_number: int,
    raw_record: str,
) -> dict[str, int]:
    counts = {"processed": 1, "accepted": 0, "applied": 0, "duplicate": 0, "stale": 0, "rejected": 0}
    event, reason = _validate(connection, raw_record)
    if reason is not None or event is None:
        _quarantine(
            connection,
            run_id,
            source_file,
            line_number,
            raw_record,
            reason or "invalid_record",
            _extract_source_event_id(raw_record),
        )
        counts["rejected"] = 1
        return counts

    canonical = json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    event_id = event["event_id"]
    existing_event = connection.execute(
        "SELECT event_fingerprint FROM event_history WHERE event_id = ?", (event_id,)
    ).fetchone()
    if existing_event is not None:
        if existing_event["event_fingerprint"] == fingerprint:
            counts["duplicate"] = 1
            return counts
        _quarantine(
            connection,
            run_id,
            source_file,
            line_number,
            raw_record,
            "duplicate_event_id_conflict",
            event_id,
        )
        counts["rejected"] = 1
        return counts

    current = connection.execute(
        "SELECT event_ts, event_id, is_deleted FROM current_accounts WHERE account_id = ?",
        (event["account_id"],),
    ).fetchone()
    order_key = (event["event_ts"], event_id)
    if current is not None and order_key <= (current["event_ts"], current["event_id"]):
        disposition = "stale"
        counts["stale"] = 1
    else:
        disposition = "applied"
        if event["operation"] == "insert" and current is not None and not current["is_deleted"]:
            _quarantine(
                connection,
                run_id,
                source_file,
                line_number,
                raw_record,
                "insert_for_active_account",
                event_id,
            )
            counts["rejected"] = 1
            return counts

        deleted = event["operation"] == "delete"
        connection.execute(
            """INSERT INTO current_accounts
               (account_id, account_name, region_id, balance, event_ts, event_id,
                is_deleted, source_file, run_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(account_id) DO UPDATE SET
                 account_name = excluded.account_name,
                 region_id = excluded.region_id,
                 balance = excluded.balance,
                 event_ts = excluded.event_ts,
                 event_id = excluded.event_id,
                 is_deleted = excluded.is_deleted,
                 source_file = excluded.source_file,
                 run_id = excluded.run_id""",
            (
                event["account_id"],
                None if deleted else event["account_name"],
                None if deleted else event["region_id"],
                None if deleted else event["balance"],
                event["event_ts"],
                event_id,
                int(deleted),
                source_file,
                run_id,
            ),
        )
        counts["applied"] = 1

    connection.execute(
        """INSERT INTO event_history
           (event_id, account_id, operation, event_ts, event_fingerprint,
            payload_json, raw_json, disposition, source_file, run_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            event_id,
            event["account_id"],
            event["operation"],
            event["event_ts"],
            fingerprint,
            canonical,
            raw_record,
            disposition,
            source_file,
            run_id,
        ),
    )
    counts["accepted"] = 1
    return counts


def process_file(
    input_path: str | Path,
    database_path: str | Path,
    *,
    run_id: str | None = None,
    batch_size: int = 500,
    failure_hook: Callable[[int], None] | None = None,
) -> dict[str, Any]:
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    source = Path(input_path)
    source_file = source.as_posix()
    run_id = run_id or str(uuid.uuid4())
    started_at = utc_now()
    counters = {"processed": 0, "accepted": 0, "applied": 0, "duplicate": 0, "stale": 0, "rejected": 0}
    connection = connect(database_path)
    connection.execute(
        """INSERT INTO pipeline_runs(run_id, source_file, status, started_at)
           VALUES (?, ?, 'running', ?)""",
        (run_id, source_file, started_at),
    )
    connection.commit()

    try:
        with source.open("r", encoding="utf-8") as input_file:
            input_count = sum(1 for line in input_file if line.strip())
        connection.execute(
            "UPDATE pipeline_runs SET input_count = ? WHERE run_id = ?",
            (input_count, run_id),
        )
        connection.commit()

        line_number = 0
        with source.open("r", encoding="utf-8") as input_file:
            while True:
                batch: list[tuple[int, str]] = []
                while len(batch) < batch_size:
                    line = input_file.readline()
                    if not line:
                        break
                    line_number += 1
                    raw_record = line.rstrip("\r\n")
                    if raw_record.strip():
                        batch.append((line_number, raw_record))
                if not batch:
                    break

                batch_counts = {key: 0 for key in counters}
                with connection:
                    for record_line, raw_record in batch:
                        result = _process_line(
                            connection, run_id, source_file, record_line, raw_record
                        )
                        for key, value in result.items():
                            batch_counts[key] += value
                        if failure_hook is not None:
                            failure_hook(batch_counts["processed"] + counters["processed"])
                for key, value in batch_counts.items():
                    counters[key] += value

        ended_at = utc_now()
        connection.execute(
            """UPDATE pipeline_runs SET status = 'succeeded', ended_at = ?,
               processed_count = ?, accepted_count = ?, applied_count = ?,
               duplicate_count = ?, stale_count = ?, rejected_count = ?
               WHERE run_id = ?""",
            (
                ended_at,
                counters["processed"],
                counters["accepted"],
                counters["applied"],
                counters["duplicate"],
                counters["stale"],
                counters["rejected"],
                run_id,
            ),
        )
        connection.commit()
    except Exception as error:
        connection.execute(
            """UPDATE pipeline_runs SET status = 'failed', ended_at = ?,
               processed_count = ?, accepted_count = ?, applied_count = ?,
               duplicate_count = ?, stale_count = ?, rejected_count = ?,
               failure_reason = ? WHERE run_id = ?""",
            (
                utc_now(),
                counters["processed"],
                counters["accepted"],
                counters["applied"],
                counters["duplicate"],
                counters["stale"],
                counters["rejected"],
                f"{type(error).__name__}: {error}",
                run_id,
            ),
        )
        connection.commit()
        raise PipelineExecutionError(f"run {run_id} failed: {error}") from error
    finally:
        connection.close()

    return {
        "run_id": run_id,
        "source_file": source_file,
        "status": "succeeded",
        "started_at": started_at,
        "ended_at": ended_at,
        "input_count": input_count,
        "processed_count": counters["processed"],
        "accepted_count": counters["accepted"],
        "applied_count": counters["applied"],
        "duplicate_count": counters["duplicate"],
        "stale_count": counters["stale"],
        "rejected_count": counters["rejected"],
        "failure_reason": None,
    }
