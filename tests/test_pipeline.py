from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from cdc_pipeline.db import connect
from cdc_pipeline.generator import generate_events
from cdc_pipeline.pipeline import PipelineExecutionError, process_file
from cdc_pipeline.report import build_report


def event(event_id: str, account_id: str = "acct-1", **overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "event_id": event_id,
        "account_id": account_id,
        "operation": "insert",
        "event_ts": "2025-01-01T00:00:00Z",
        "account_name": "Test Account",
        "region_id": "na",
        "balance": 10.0,
    }
    value.update(overrides)
    return value


def write_events(path: Path, records: list[dict[str, object] | str]) -> Path:
    with path.open("w", encoding="utf-8", newline="\n") as output:
        for record in records:
            output.write(record if isinstance(record, str) else json.dumps(record))
            output.write("\n")
    return path


def test_happy_path_is_idempotent_and_preserves_history(tmp_path: Path) -> None:
    input_path = write_events(
        tmp_path / "events.jsonl",
        [
            event("e-1"),
            event("e-2", operation="update", event_ts="2025-01-01T00:01:00Z", balance=25),
        ],
    )
    database = tmp_path / "pipeline.db"

    first = process_file(input_path, database, run_id="run-1")
    second = process_file(input_path, database, run_id="run-2")

    assert first["status"] == "succeeded"
    assert first["input_count"] == first["accepted_count"] == first["applied_count"] == 2
    assert first["ended_at"] == _run_end(database, "run-1")
    assert second["duplicate_count"] == 2
    assert second["accepted_count"] == 0
    connection = connect(database)
    try:
        state = connection.execute(
            "SELECT balance, event_id, is_deleted FROM current_accounts WHERE account_id = 'acct-1'"
        ).fetchone()
        assert tuple(state) == (25.0, "e-2", 0)
        assert connection.execute("SELECT COUNT(*) FROM event_history").fetchone()[0] == 2
    finally:
        connection.close()


def test_empty_input_succeeds_with_zero_counts(tmp_path: Path) -> None:
    input_path = tmp_path / "empty.jsonl"
    input_path.write_text("\n", encoding="utf-8")

    result = process_file(input_path, tmp_path / "pipeline.db")

    assert result["status"] == "succeeded"
    assert result["input_count"] == result["processed_count"] == 0
    assert result["accepted_count"] == result["rejected_count"] == 0


def test_generator_is_reproducible_for_fixed_seed(tmp_path: Path) -> None:
    first_path = tmp_path / "first.jsonl"
    second_path = tmp_path / "second.jsonl"

    assert generate_events(first_path, count=25, seed=7) == 25
    assert generate_events(second_path, count=25, seed=7) == 25
    assert first_path.read_bytes() == second_path.read_bytes()


def test_malformed_missing_null_schema_and_bad_reference_are_quarantined(tmp_path: Path) -> None:
    input_path = write_events(
        tmp_path / "invalid.jsonl",
        [
            "{not-json",
            {"event_id": "missing-account"},
            event("null-name", account_name=None),
            event("new-field", new_column="unexpected"),
            event("bad-region", region_id="mars"),
            event("negative-balance", balance=-1),
        ],
    )

    result = process_file(input_path, tmp_path / "pipeline.db")

    assert result["rejected_count"] == 6
    assert result["accepted_count"] == 0
    connection = connect(tmp_path / "pipeline.db")
    try:
        reasons = {
            row[0]
            for row in connection.execute("SELECT reason FROM quarantine")
        }
        assert "malformed_json" in reasons
        assert any(reason.startswith("missing_required_fields:") for reason in reasons)
        assert "account_name_must_be_non_empty_string" in reasons
        assert "unexpected_fields:new_column" in reasons
        assert "invalid_reference:region_id:mars" in reasons
        assert "balance_must_be_finite_and_non_negative" in reasons
        assert connection.execute("SELECT COUNT(*) FROM current_accounts").fetchone()[0] == 0
    finally:
        connection.close()


def test_exact_duplicate_is_skipped_and_conflicting_event_id_rejected(tmp_path: Path) -> None:
    original = event("same-event")
    conflict = event("same-event", balance=99)
    input_path = write_events(tmp_path / "dupes.jsonl", [original, original.copy(), conflict])

    result = process_file(input_path, tmp_path / "pipeline.db")

    assert result["accepted_count"] == 1
    assert result["duplicate_count"] == 1
    assert result["rejected_count"] == 1
    connection = connect(tmp_path / "pipeline.db")
    try:
        assert connection.execute("SELECT COUNT(*) FROM event_history").fetchone()[0] == 1
        assert connection.execute("SELECT reason FROM quarantine").fetchone()[0] == "duplicate_event_id_conflict"
    finally:
        connection.close()


def test_late_events_delete_tombstones_and_reactivation(tmp_path: Path) -> None:
    input_path = write_events(
        tmp_path / "ordering.jsonl",
        [
            event("e-1"),
            event("e-3", operation="update", event_ts="2025-01-01T00:02:00Z", balance=30),
            event("e-2", operation="update", event_ts="2025-01-01T00:01:00Z", balance=20),
            event("e-4", operation="delete", event_ts="2025-01-01T00:03:00Z"),
            event("e-5", operation="update", event_ts="2025-01-01T00:02:30Z", balance=40),
            event("e-6", operation="update", event_ts="2025-01-01T00:04:00Z", balance=50),
        ],
    )

    result = process_file(input_path, tmp_path / "pipeline.db")

    assert result["applied_count"] == 4
    assert result["stale_count"] == 2
    connection = connect(tmp_path / "pipeline.db")
    try:
        state = connection.execute(
            "SELECT balance, event_id, is_deleted FROM current_accounts WHERE account_id = 'acct-1'"
        ).fetchone()
        assert tuple(state) == (50.0, "e-6", 0)
        assert connection.execute(
            "SELECT COUNT(*) FROM event_history WHERE disposition = 'stale'"
        ).fetchone()[0] == 2
    finally:
        connection.close()


def test_active_insert_is_rejected_as_domain_violation(tmp_path: Path) -> None:
    input_path = write_events(
        tmp_path / "insert-conflict.jsonl",
        [
            event("e-1"),
            event("e-2", operation="insert", event_ts="2025-01-01T00:01:00Z"),
        ],
    )

    result = process_file(input_path, tmp_path / "pipeline.db")

    assert result["applied_count"] == 1
    assert result["rejected_count"] == 1
    connection = connect(tmp_path / "pipeline.db")
    try:
        assert connection.execute("SELECT reason FROM quarantine").fetchone()[0] == "insert_for_active_account"
    finally:
        connection.close()


def test_failed_batch_rolls_back_and_retry_is_safe(tmp_path: Path) -> None:
    input_path = write_events(
        tmp_path / "retry.jsonl",
        [event("e-1"), event("e-2", "acct-2"), event("e-3", "acct-3")],
    )
    database = tmp_path / "pipeline.db"

    def fail_inside_first_batch(processed: int) -> None:
        if processed == 2:
            raise RuntimeError("simulated batch failure")

    with pytest.raises(PipelineExecutionError, match="simulated batch failure"):
        process_file(input_path, database, run_id="failed-run", batch_size=1, failure_hook=fail_inside_first_batch)

    connection = connect(database)
    try:
        failed = connection.execute(
            "SELECT status, failure_reason, processed_count FROM pipeline_runs WHERE run_id = 'failed-run'"
        ).fetchone()
        assert failed[0] == "failed"
        assert "simulated batch failure" in failed[1]
        assert failed[2] == 1
        assert connection.execute("SELECT COUNT(*) FROM event_history").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM current_accounts").fetchone()[0] == 1
    finally:
        connection.close()

    recovered = process_file(input_path, database, run_id="retry-run", batch_size=1)
    repeated = process_file(input_path, database, run_id="repeat-run", batch_size=1)

    assert recovered["accepted_count"] == 2
    assert recovered["duplicate_count"] == 1
    assert repeated["duplicate_count"] == 3
    connection = connect(database)
    try:
        assert connection.execute("SELECT COUNT(*) FROM event_history").fetchone()[0] == 3
    finally:
        connection.close()


def test_report_reconciles_state_and_history(tmp_path: Path) -> None:
    input_path = write_events(
        tmp_path / "report.jsonl",
        [event("e-1"), event("e-2", operation="delete", event_ts="2025-01-01T00:01:00Z")],
    )
    database = tmp_path / "pipeline.db"
    process_file(input_path, database)
    connection = connect(database)
    try:
        summary = build_report(connection)
    finally:
        connection.close()

    assert summary["current_accounts"]["total_including_tombstones"] == 1
    assert summary["current_accounts"]["deleted_tombstones"] == 1
    assert summary["event_history"] == {"total": 2, "applied": 2, "stale": 0}
    assert summary["quarantine_total"] == 0


def test_checked_in_sample_matches_expected_summary(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    expected = json.loads(
        (project_root / "data" / "expected" / "sample_summary.json").read_text(encoding="utf-8")
    )
    with (project_root / "data" / "expected" / "sample_current_state.csv").open(
        encoding="utf-8", newline=""
    ) as expected_file:
        expected_state = list(csv.DictReader(expected_file))
    with (project_root / "data" / "expected" / "sample_rejects.csv").open(
        encoding="utf-8", newline=""
    ) as expected_file:
        expected_rejects = list(csv.DictReader(expected_file))
    result = process_file(
        project_root / "data" / "sample_events.jsonl", tmp_path / "sample.db"
    )

    assert {key: result[key] for key in expected["sample_run"]} == expected["sample_run"]
    connection = connect(tmp_path / "sample.db")
    try:
        report = build_report(connection)
        current_rows = connection.execute(
            """SELECT account_id, account_name, region_id, balance, event_ts, event_id, is_deleted
               FROM current_accounts ORDER BY account_id"""
        ).fetchall()
        reject_rows = connection.execute(
            """SELECT source_file, line_number, COALESCE(event_id, '') AS event_id, reason
               FROM quarantine ORDER BY line_number"""
        ).fetchall()
    finally:
        connection.close()
    assert {key: report[key] for key in expected if key != "sample_run"} == {
        key: expected[key] for key in expected if key != "sample_run"
    }
    actual_state = [
        {key: "" if row[key] is None else str(row[key]) for key in expected_state[0]}
        for row in current_rows
    ]
    actual_rejects = [
        {
            key: (
                Path(row[key]).relative_to(project_root).as_posix()
                if key == "source_file"
                else str(row[key])
            )
            for key in expected_rejects[0]
        }
        for row in reject_rows
    ]
    assert actual_state == expected_state
    assert actual_rejects == expected_rejects


def _run_end(database: Path, run_id: str) -> str:
    connection = connect(database)
    try:
        return connection.execute(
            "SELECT ended_at FROM pipeline_runs WHERE run_id = ?", (run_id,)
        ).fetchone()[0]
    finally:
        connection.close()
