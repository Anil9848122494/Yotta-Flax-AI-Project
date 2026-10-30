from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path


def generate_events(output_path: str | Path, count: int, seed: int = 20261030) -> int:
    if count < 0:
        raise ValueError("count must be non-negative")

    rng = random.Random(seed)
    events: list[dict[str, object]] = []
    base_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
    accounts = (count + 2) // 3

    for index in range(count):
        account_number, sequence = divmod(index, 3)
        operation = "insert" if sequence == 0 else "update"
        if sequence == 2 and account_number % 10 == 0:
            operation = "delete"

        event_time = base_time + timedelta(minutes=sequence)
        event: dict[str, object] = {
            "event_id": f"evt-{index:08d}",
            "account_id": f"account-{account_number:08d}",
            "operation": operation,
            "event_ts": event_time.isoformat().replace("+00:00", "Z"),
        }
        if operation != "delete":
            event.update(
                {
                    "account_name": f"Synthetic Account {account_number:08d}",
                    "region_id": rng.choice(("apac", "eu", "na")),
                    "balance": round(rng.uniform(0, 100000), 2),
                }
            )
        events.append(event)

    rng.shuffle(events)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as output:
        for event in events:
            output.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
    return len(events)
