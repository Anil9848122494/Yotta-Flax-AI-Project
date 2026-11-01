# AI Prompt History

This file records the user-authored prompts visible in the Copilot conversation used for this project, plus the project-generation prompt sent to the workspace setup tool. No other AI tools were used for this work. AI responses are omitted because the submission guidance makes them optional.

Exact per-prompt timestamps were not retained in the available conversation history. The prompts below are kept in chronological order; this is not a substitute for the email's recorded project-send timestamp used to calculate the deadline. The applicant should review this log and add any prompts from AI sessions or tools outside this conversation before submitting.

## 1. Initial Challenge Prompt

```text
ottaFlex.ai Careers
My Applications
/
Associate AI Forward Deployed Engineers
/
Code Challenge
Round 2
72 Hours Code Challenge
Associate AI Forward Deployed Engineers · AI Data Forward Deployed Engineer

Problem statement
Read it carefully. Your build should cover every point below.

Business Context / Problem
Process change events for inserts, updates, and deletes into a current-state table while preserving an auditable history. Handle duplicate and out-of-order events.

Objective and Scope
Deliver a working Data Engineering solution within 72 hours for: Process change events for inserts, updates, and deletes into a current-state table while preserving an auditable history. Handle duplicate and out-of-order events. The solution should be runnable locally or in a clearly documented cloud environment, expose failures and data-quality issues, and produce measurable outputs. Target level: 0–3 years of experience. Prioritize correctness, clear design, maintainability, and evidence of testing over unnecessary complexity.

Primary Actors / Systems
Data engineer, source system or file/API producer, storage/processing layer, target analytical consumer, and pipeline operator.

Business Workflow and Rules
1. Define source and target schemas, data types, keys, and assumptions.
2. Generate or provide a small reproducible sample dataset and a larger scalable dataset generator.
3. Implement ingestion, validation, transformation, and target publishing.
4. Make reruns safe; record run status, row counts, rejects, and errors.
5. Include automated tests and demonstrate expected results with sample queries or reports.

Entities and Relationships
Identify the source entities and their keys, relationships, grain, and important business rules. Document nullability, uniqueness, referential integrity, and any derived fields. Keep rejected or anomalous records traceable to their source. Where history matters, preserve change or event history instead of silently overwriting it.

ID / Nomenclature Conventions
Use stable, deterministic IDs; consistent snake_case table and column names; ISO-8601 timestamps; and explicit run_id / source_file fields where applicable. Document naming choices in the README.

Implementation Instructions (Granular)
Step 1 — Write a concise README, data dictionary, architecture diagram or flow description, and setup instructions.
Step 2 — Implement the core pipeline with clear modules/functions and configurable paths or parameters.
Step 3 — Add schema validation, business-rule checks, duplicate handling, and an explicit reject/quarantine path.
Step 4 — Add logging and operational metrics: run ID, start/end time, input/output counts, rejected count, and failure reason.
Step 5 — Add automated tests for the happy path, empty input, malformed records, duplicates, nulls, and at least two domain-specific edge cases.
Step 6 — Make the load idempotent and document retry, restart, and backfill behavior where applicable.
Step 7 — Provide reproducible sample data; use synthetic data unless public data has clear reuse rights. Keep any expected-answer labels separate from input data.
Step 8 — Demonstrate output correctness with reconciliation queries, assertions, or a validation report.
Step 9 — Include a simple performance measurement and identify one reasonable optimization.
Step 10 — Submit source code, tests, sample input/output, README, schema/data dictionary, and a short design/trade-off note.

Suggested Volume and Coverage
Support a small starter sample for quick review and a configurable larger run (for example, 100,000+ records where practical). Include normal data, boundary values, duplicate records, missing values, late or out-of-order data where relevant, and deliberately labelled invalid records. Use a fixed random seed for reproducibility.

Required Edge Cases / Negative Scenarios
Malformed input; missing required field; duplicate key/event; unexpected schema change; empty batch; partial failure and retry; late-arriving or out-of-order data where relevant; invalid reference key; and rerun of the same input.

Validation Rules / Acceptance Criteria
Primary keys and referential integrity are checked; transformation rules are deterministic; source-to-target counts and key aggregates reconcile or explain differences; invalid records are traceable; reruns do not create unintended duplicates; tests pass; setup and run instructions work from a clean environment.

Evaluation Focus
Correctness and data quality (30%); pipeline design and code clarity (20%); testing and edge-case handling (20%); idempotency, recovery, and observability (15%); performance reasoning (10%); documentation and reproducibility (5%). Candidates should explain design choices and limitations.

72-Hour Deliverables
1. Working source code and dependency/setup files.
2. Reproducible sample data or generator.
3. Automated tests and execution evidence.
4. Output dataset/report plus reconciliation results.
5. README covering architecture, assumptions, run instructions, known limitations, and possible next steps.

Scope Guidance
A complete, tested vertical slice is preferred over an unfinished enterprise-scale implementation. External services are optional; provide a local mock or clear setup instructions if credentials are required. Do not commit secrets or use data that you are not authorized to access.
```

## 2. Workspace Setup Request

```text
Continue with #new workspace setup
```

## 3. Project-Generation Tool Prompt

This prompt was submitted by Copilot to the workspace setup tool to scaffold the project:

```text
Create a complete Python 3.11+ project in the new workspace for the ottaFlex.ai Associate AI Forward Deployed Engineer Round 2 challenge: a local CDC (insert/update/delete) pipeline that maintains current state and immutable auditable event history, safely handles duplicate and out-of-order events, and is idempotent on rerun. Use SQLite from the standard library for persistence and pytest for tests. Structure as a maintainable Python package (src layout), with CLI entry points to generate reproducible synthetic JSONL events, process a file into a configurable SQLite DB, and report/reconcile results. Use deterministic entity/event IDs, snake_case names, ISO-8601 UTC timestamps, explicit run_id/source_file. Include strict schema/domain validation, duplicate handling, late-event ordering policy, quarantine/reject table that preserves raw source records and reasons, run status/start/end/counts/error metrics, transaction behavior/retry safety, queryable history/current tables, and graceful empty batch. Tests should cover happy path, empty input, malformed records/schema changes, required nulls, duplicate event IDs, duplicate/out-of-order events, deletes/tombstones, invalid references, retry/partial failures, and deterministic edge cases. Include small reproducible sample inputs with expected-answer labels separate from input; a configurable seeded large data generator (target 100k+); reconciliation SQL/report output; a simple benchmark and one performance optimization discussion. Add README with architecture diagram/flow, setup/run/test instructions, assumptions and data dictionary/entity grain/keys/constraints, retry/restart/backfill policy, known limitations, performance notes, and design/trade-off note. Add pyproject.toml, .gitignore, tests, sample input/output artifacts if feasible, and concise clear documentation. Keep scope as a complete tested vertical slice; no cloud credentials/services.
```

## 4. Git Request

```text
I want to push My floder (Yotta flax AI) into Git
```

## 5. GitHub Account Request

```text
I have only Github Account do what ever required.
```

## 6. Repository URL

```text
I have Link https://github.com/Anil9848122494/Yotta-Flax-AI-Project.git
```

## 7. Compliance Review Prompt

```text
When does my 72-hour window start? When YottaFlex AI sends you the project. Your deadline is exactly 72 hours later, using the recorded send timestamp and its time zone. 7. Must I write all code myself? The project must be your individual work. AI and public learning resources are allowed; implementation help from other people is not. Understand the core logic, key design choices, dependencies, and limitations. 2. Can I submit early? Yes. You may submit as soon as you are ready. Keep your public repository available and editable until the 72-hour deadline; the latest version at the deadline is evaluated. 8. Can I choose my own technology stack? Yes. Choose suitable languages, frameworks, and storage. Use only free or locally runnable services, and avoid unusually large or slow dependencies where possible. 3. How do I submit my repository link? Create a new, dedicated public GitHub repository. Send the link from the same email address you used during recruitment and follow the submission instructions provided. 9. Must I provide a live demo or automated tests? No hosted demo or automated test suite is mandatory. Provide clear setup/run instructions and demonstrate how you verified the core functionality. Document environment needs and limitations. 4. What belongs in my repository? Include your code, prompt history, and relevant supporting artifacts in a clearly identifiable directory. There is no fixed list of documents or prescribed format. 10. Can I reuse existing code? Standard dependencies and small illustrative snippets are acceptable. Do not import a complete solution or existing code that performs the core project work. Follow licenses and provide attribution where required. 5. Which AI tools may I use? Any LLM or AI coding tool is allowed, including cloud-based and locally hosted tools. AI use is unrestricted; your judgment, understanding, ownership, and validation matter. 11. What if requirements are unclear or work is incomplete? Make reasonable assumptions and explain them. Partial solutions are acceptable if you state what works, what remains incomplete, known limitations, and next steps. Explain any requirement deviations. 6. What prompt history is required? Include all prompts submitted to every AI tool you used. AI responses are optional. If a tool cannot export prompts, keep a reasonable record and disclose the limitation. 12. What must I keep out of a public repository? Never include secrets, credentials, personal or sensitive information, or proprietary code you are not authorized to publish. Use safe sample data and local configuration; explain setup in the README. BE READY TO EXPLAIN YOUR DECISIONS, VERIFY YOUR WORK, AND OWN YOUR SUBMISSION
my project is obey every requirement or not
```

## 8. Prompt-History Addition Request

```text
could you please add my same project what ever missing required qualificationes like promt history
```
