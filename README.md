# Yotta-Flax-AI-Project

## ottaFlex CDC Challenge

A small local change-data-capture pipeline that consumes newline-delimited JSON events, validates them, maintains current account state in SQLite, and preserves every accepted event in an auditable history. Rejected source rows are quarantined with the original content and source line.

## Architecture

```text
JSONL producer
    -> parse + strict schema/domain validation
        -> per-batch SQLite transaction
            -> event_history (applied or stale; event_id is unique)
            -> current_accounts (latest event by event_ts, then event_id)
            -> quarantine (raw row, file, line, reason)
            -> pipeline_runs (counts, status, timestamps, failure)
        -> report / reconciliation queries
```

This is a local vertical slice: Python 3.11+, SQLite, and pytest. Runtime processing uses only the Python standard library. SQLite is the durable target and can be inspected with any SQLite client.

## Setup

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
```

On macOS/Linux, activate with `source .venv/bin/activate` instead. For runtime-only use, install with `python -m pip install -e .`.

## Run

Process the checked-in sample and inspect the persisted run:

```powershell
cdc-pipeline process --input data/sample_events.jsonl --db data/sample_output.db
cdc-pipeline report --db data/sample_output.db
```

The sample includes valid inserts/updates/deletes, a zero-balance boundary, an exact duplicate, a late update, a duplicate-ID conflict, a missing field, an unknown field, malformed JSON, and an invalid region. Stable expected aggregates, current-state rows, and rejected rows are in `data/expected/`; no expected labels are mixed into source events.

Generate and process a larger seeded workload:

```powershell
cdc-pipeline generate --output data/generated_events.jsonl --count 100000 --seed 20261030
cdc-pipeline process --input data/generated_events.jsonl --db data/generated.db --batch-size 500
cdc-pipeline report --db data/generated.db
```

Run the built-in throughput measurement (temporary files are removed afterward):

```powershell
cdc-pipeline benchmark --count 100000 --seed 20261030 --batch-size 500
```

The generator emits deterministic event IDs and content for a fixed seed, groups three ordered changes per account where applicable, and shuffles the file to exercise out-of-order arrival. The curated sample supplies malformed and invalid cases. Generated database files are ignored by git.

## Validate

```powershell
python -m pytest -q
```

Tests cover the happy path, empty input, malformed JSON, missing/null fields, schema drift, invalid references, negative balances, duplicate events and conflicting IDs, late/out-of-order updates, delete tombstones, insert-domain violations, failed-batch rollback/retry, and reconciliation.

`sql/reconciliation.sql` contains useful queries. For a successful run, `processed_count = accepted_count + duplicate_count + rejected_count`; `accepted_count = applied_count + stale_count`. History contains accepted events only, while quarantine contains rejected rows. Current state has one row per account, including tombstones.

## Rules and Recovery

- Events are full after-image snapshots. Required fields and types are listed in [DATA_DICTIONARY.md](DATA_DICTIONARY.md).
- `event_id` is the globally unique idempotency key. A repeated ID with identical normalized content is counted as a duplicate and ignored. The same ID with different content is quarantined as a conflict.
- State ordering is `(event_ts, event_id)`, both compared in normalized UTC ISO-8601 form. Older events are still written to history with `disposition = 'stale'` but cannot overwrite current state. Event ID is the stable tie-breaker for equal timestamps.
- A delete writes a tombstone (`is_deleted = 1`) instead of physically removing state. A later event can reactivate the account if its ordering key is greater.
- Identical valid event IDs can be replayed safely, including after a prior partial run. Each batch commits state, history, and quarantine atomically. If a batch fails, it rolls back; earlier committed batches remain, the run is marked failed, and replaying the complete source file with a new run ID skips prior event IDs.
- Backfill uses the same process command against the same target database. Corrected source facts should use a new event ID and a later event timestamp; event history is append-only.

## Operations and Limitations

Every run records source path, run ID, UTC start/end, input/processed/accepted/applied/duplicate/stale/rejected counts, status, and failure reason. Quarantine retains the raw source line and physical line number. WAL mode and a busy timeout support a local operator workflow, but SQLite remains a single-writer database.

Transactions are batched (default 500 records), reducing commit/fsync overhead compared with a commit per row; tune `--batch-size` using the included benchmark for your machine and workload. A 100,000-event run on Windows with Python 3.13.3 completed at 5,702 events/second (17.536 seconds, batch size 500); rerun the benchmark locally because disk and SQLite versions affect results. Further scale can use bulk staging/`executemany` and a server database. Other limitations: the input is scanned once for counts and again for processing; the allowed region reference set is intentionally small and seeded in the database; no schema evolution registry, CDC transport, multi-writer coordination, or cloud deployment is included.

See [DESIGN.md](DESIGN.md) for design and trade-offs, and [DATA_DICTIONARY.md](DATA_DICTIONARY.md) for table and field definitions.
