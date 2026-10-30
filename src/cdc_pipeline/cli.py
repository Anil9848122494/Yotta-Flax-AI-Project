from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

from .db import connect
from .generator import generate_events
from .pipeline import PipelineExecutionError, process_file
from .report import build_report, format_report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cdc-pipeline")
    commands = parser.add_subparsers(dest="command", required=True)

    generate = commands.add_parser("generate", help="generate seeded synthetic JSONL events")
    generate.add_argument("--output", required=True)
    generate.add_argument("--count", type=int, default=100)
    generate.add_argument("--seed", type=int, default=20261030)

    process = commands.add_parser("process", help="process a JSONL event file")
    process.add_argument("--input", required=True)
    process.add_argument("--db", default="data/pipeline.db")
    process.add_argument("--batch-size", type=int, default=500)

    report = commands.add_parser("report", help="show reconciliation metrics")
    report.add_argument("--db", default="data/pipeline.db")
    report.add_argument("--run-id")

    benchmark = commands.add_parser("benchmark", help="generate and process a synthetic workload")
    benchmark.add_argument("--count", type=int, default=100000)
    benchmark.add_argument("--seed", type=int, default=20261030)
    benchmark.add_argument("--batch-size", type=int, default=500)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "generate":
            count = generate_events(args.output, args.count, args.seed)
            print(json.dumps({"output": str(Path(args.output)), "event_count": count, "seed": args.seed}))
            return 0
        if args.command == "process":
            result = process_file(args.input, args.db, batch_size=args.batch_size)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        if args.command == "report":
            connection = connect(args.db)
            try:
                print(format_report(build_report(connection, args.run_id)))
            finally:
                connection.close()
            return 0
        if args.command == "benchmark":
            with tempfile.TemporaryDirectory(prefix="ottaflex-cdc-") as temporary:
                root = Path(temporary)
                input_path = root / "events.jsonl"
                database_path = root / "pipeline.db"
                generate_events(input_path, args.count, args.seed)
                started = time.perf_counter()
                result = process_file(input_path, database_path, batch_size=args.batch_size)
                elapsed = time.perf_counter() - started
                print(
                    json.dumps(
                        {
                            "event_count": args.count,
                            "elapsed_seconds": round(elapsed, 3),
                            "events_per_second": round(args.count / elapsed, 1) if elapsed else 0,
                            "batch_size": args.batch_size,
                            "run": result,
                        },
                        indent=2,
                        sort_keys=True,
                    )
                )
                return 0
    except (OSError, ValueError, PipelineExecutionError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
