# Data Dictionary

All names use `snake_case`. Event timestamps are ISO-8601 with an explicit timezone and are normalized to UTC with microsecond precision. Source grain is one row per source change event; current-state grain is one row per `account_id`, including delete tombstones.

## Source: JSONL Change Event

| Field | Type | Nullable | Rule |
|---|---|---:|---|
| `event_id` | string | no | Stable globally unique event key; exact repeats are ignored, conflicting repeats rejected. |
| `account_id` | string | no | Stable account business key. |
| `operation` | string | no | `insert`, `update`, or `delete`. |
| `event_ts` | ISO-8601 string | no | Must include timezone; ordering timestamp. |
| `account_name` | string | for delete only | Required and non-empty for insert/update. |
| `region_id` | string | for delete only | Must reference seeded `regions`; accepted values are `apac`, `eu`, `na`. |
| `balance` | number | for delete only | Finite and non-negative; zero is valid. Booleans are not accepted as numbers. |

Unknown fields are treated as schema drift and quarantined, not silently ignored. Delete messages need only the four base fields; their current-state payload values are set to null.

## Tables

| Table | Grain / key | Important columns and constraints |
|---|---|---|
| `regions` | One row per reference region; PK `region_id` | Seeded reference data used for FK validation. |
| `pipeline_runs` | One row per invocation; PK `run_id` | `source_file`, `status`, UTC `started_at`/`ended_at`, input and outcome counts, optional `failure_reason`. |
| `event_history` | One row per accepted unique event; PK `event_id` | `account_id`, operation, normalized `event_ts`, SHA-256 canonical payload fingerprint, canonical payload, original raw JSON, `disposition` (`applied`/`stale`), source path and run ID. |
| `current_accounts` | One row per `account_id`; PK `account_id` | Latest ordering key (`event_ts`, `event_id`), current payload, `is_deleted`, source path and last-applied run ID. `region_id` references `regions`; deleted payload is null. |
| `quarantine` | One row per rejected source row; surrogate `reject_id` | `run_id`, `source_file`, physical `line_number`, optional event ID, original `raw_record`, machine-readable `reason`, UTC `rejected_at`. |

## Relationships and Derived Values

`current_accounts.region_id -> regions.region_id`; event and quarantine rows reference their processing run. `event_history.account_id` intentionally has no FK to current state so that history remains independently auditable. Current state is updated only when the incoming `(event_ts, event_id)` is greater than the stored key. `is_deleted` is derived from `operation = 'delete'`; the active-balance report excludes tombstones. An `event_fingerprint` is SHA-256 of the normalized, sorted JSON event and supports deterministic duplicate detection.

## Run Count Definitions

For a succeeded run, `input_count` and `processed_count` count nonblank source lines; `accepted_count` counts new history rows; `applied_count` and `stale_count` partition accepted rows; `duplicate_count` counts exact previously accepted IDs; `rejected_count` counts quarantined rows. Thus `processed_count = accepted_count + duplicate_count + rejected_count` and `accepted_count = applied_count + stale_count`. A rolled-back failed batch is not included in committed outcome counts; `input_count` still records the full nonblank file size.
