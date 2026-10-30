# Design and Trade-offs

## Chosen Shape

The solution is a Python package backed by SQLite rather than a distributed streaming stack. That keeps setup credential-free and makes the challenge's key properties inspectable in one file: event identity, append-only accepted history, deterministic current state, quarantine, and run-level observability. The CLI separates generation, processing, reporting, and benchmarking.

Each input event is validated before mutation. Within one batch transaction, the pipeline records newly accepted history and either updates current state or labels the event stale; rejected rows are written to quarantine. This makes current-state mutation and its audit record atomic. Unique constraints on run IDs, account IDs, and event IDs reinforce the invariants at the storage boundary.

## Ordering and Duplicate Policy

Events are after-image snapshots. An event is state-applicable only when its normalized UTC timestamp and then its event ID compare greater than the stored ordering key. This makes equal timestamps deterministic and protects current state from late arrivals while retaining the late event in history. Event IDs are assumed globally unique. An exact repeated canonical event is ignored; reuse of an ID for changed content is a data-quality conflict and is quarantined.

Deletes become tombstones, preserving the last applied ordering key and allowing a later event to reactivate an account. Inserts against an already active account are quarantined as a domain-rule violation; update events may establish state if they arrive without a prior insert, which is useful when feeds are incomplete or out of order.

## Restart and Backfill

A run is created before source processing, and each bounded batch commits atomically. A failed batch is rolled back and the run is marked failed with its reason; earlier successful batches remain durable. Reprocessing the full file is safe because accepted `event_id` values are unique. Each invocation gets its own run ID unless an explicit ID is provided. Backfills use the same path and retain their own source/run provenance.

## Performance and Next Steps

The implementation batches writes in configurable transactions (default 500 rows), avoiding a durability commit for every event. On the challenge environment (Windows, Python 3.13.3), a fixed-seed 100,000-event run took 17.536 seconds (5,702 events/second) at batch size 500. `cdc-pipeline benchmark` reports elapsed time and events per second; results depend on disk, Python, and SQLite versions, so treat this as local evidence, not a universal target. The generator is deterministic for fixed count and seed and supports workloads above 100,000 rows.

For larger sustained loads, a next optimization is to stage parsed rows and use bulk operations while preserving per-row reject reasons; indexing should then be benchmarked against the read/write mix. A cloud or multi-writer deployment would need an operational database, coordination/locking, schema evolution policy, durable object storage, and monitoring. Those are intentionally outside this tested local slice.
