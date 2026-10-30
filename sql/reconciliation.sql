-- Every accepted event (including stale arrivals) is represented once in history.
SELECT
    (SELECT COUNT(*) FROM event_history) AS history_rows,
    (SELECT COALESCE(SUM(accepted_count), 0) FROM pipeline_runs WHERE status = 'succeeded') AS accepted_by_runs;

-- Current state is one row per account, including delete tombstones.
SELECT
    COUNT(*) AS current_rows,
    COUNT(DISTINCT account_id) AS distinct_accounts,
    SUM(CASE WHEN is_deleted = 1 THEN 1 ELSE 0 END) AS tombstones
FROM current_accounts;

-- Operator view: outcomes and errors per run.
SELECT run_id, status, input_count, processed_count, accepted_count,
       applied_count, duplicate_count, stale_count, rejected_count, failure_reason
FROM pipeline_runs
ORDER BY started_at;

-- Rejected records remain traceable to file and physical line number.
SELECT source_file, line_number, event_id, reason, raw_record
FROM quarantine
ORDER BY reject_id;
