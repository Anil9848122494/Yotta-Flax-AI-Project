# Workspace Instructions

## Project

Python 3.11+ local CDC pipeline. Runtime dependencies are standard-library only; SQLite is the durable store and pytest is the test dependency. Read `README.md`, `DATA_DICTIONARY.md`, and `DESIGN.md` for requirements and behavior.

## Setup Checklist

- [x] Create `.github/copilot-instructions.md`.
- [x] Clarify requirements: Python package, SQLite, JSONL input, pytest.
- [x] Scaffold the package, CLI, schema, sample data, and configuration.
- [x] Implement validation, quarantine, event history, state ordering, idempotency, run metrics, and reporting.
- [x] Recommend Python extensions in `.vscode/extensions.json` (`ms-python.python`, `ms-python.vscode-python-envs`).
- [x] Compile and test: `python -m compileall -q src`; `python -m pytest -q` (10 passed).
- [x] Create/run task: skipped; direct CLI commands cover this non-interactive project.
- [x] Launch: CLI sample run and 100k benchmark verified; no persistent server or debug session is required.
- [x] Documentation and expected sample outputs are complete.

## Development Conventions

- Keep Python implementation under `src/cdc_pipeline/` and tests under `tests/`.
- Preserve event-history immutability and quarantine raw records with source path and physical line number.
- Use UTC ISO-8601 timestamps, deterministic IDs, snake_case names, and parameterized SQLite queries.
- Keep processing idempotent by `event_id`; retain stale events in history without overwriting newer state.
- Run `python -m pytest -q` after behavior changes. Use `cdc-pipeline benchmark` for throughput comparisons.
- Do not commit generated SQLite databases, secrets, or non-synthetic data.
