"""Generate the RECORDS a profile comes with, and land them in Zetta.

A profile is not a description of data that exists elsewhere — it comes with its data. Downstream
agents have to query real tables, and a profile whose tables cannot be queried cannot grade
anything. Generating them also exercises the capture path, which is part of what this bootstrap
exists to prove.

Two rules the generators here follow, and both were learned the hard way:

* **Awkwardness is generated, never annotated.** If a profile says `closed_at` is null on 31% of
  rows, this actually produces nulls at that rate. Whether an agent notices is what the later
  layers test — so the data must really be awkward rather than described as awkward.
* **The structure has to be real enough to reward reading it.** A subscription table that makes
  demand largely deterministic only teaches something if the subscriptions actually determine the
  orders. Random noise shaped like a schema teaches nothing.
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from agent_eval_generator.tools import ZettaClient


@dataclass
class Table:
    """One table of a profile: where it lands in Zetta, and the rows themselves."""

    database: str
    name: str
    rows: list[dict[str, Any]]

    def write_jsonl(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{self.database}.{self.name}.jsonl"
        with path.open("w") as handle:
            for row in self.rows:
                handle.write(json.dumps(row) + "\n")
        return path


def coffee_subscription(seed: int = 7) -> list[Table]:
    """Profile C — Dana, DTC coffee subscription.

    The structure that matters: subscriptions largely DETERMINE daily orders. An agent that reads
    `subscriptions` can predict most of `orders_daily` from cadence alone; one that forecasts the
    aggregate in isolation will produce a backtest a spreadsheet beats. That is a property of the
    generated data, not a hint in the profile.
    """
    rng = random.Random(seed)
    skus = ["ETH-YIRG", "COL-HUILA", "BRZ-CERR", "KEN-AA", "GUA-ANTI"]

    subscriptions: list[dict[str, Any]] = []
    for index in range(47_000):
        started = rng.randint(0, 1_000)
        cadence = rng.choice([7, 14, 28])
        # ~18% churn, and a few paused rather than cancelled — a null cancelled_at does not mean
        # active, which is exactly the sort of thing only visible by reading the table.
        cancelled = started + rng.randint(30, 600) if rng.random() < 0.18 else None
        subscriptions.append({
            "sub_id": f"sub_{index:06d}",
            "sku": rng.choice(skus),
            "started_at": started,
            "cancelled_at": cancelled,
            "cadence_days": cadence,
            "pause_until": started + rng.randint(10, 200) if rng.random() < 0.06 else None,
        })

    # Daily orders: the deterministic subscription base, plus a modest one-off tail and promos.
    orders: list[dict[str, Any]] = []
    for day in range(1_090):
        for sku in skus:
            due = sum(
                1
                for s in subscriptions
                if s["sku"] == sku
                and s["started_at"] <= day
                and (s["cancelled_at"] is None or s["cancelled_at"] > day)
                and (s["pause_until"] is None or s["pause_until"] <= day)
                and (day - s["started_at"]) % s["cadence_days"] == 0
            )
            promo = 1 if rng.random() < 0.04 else 0
            one_off = max(0, int(rng.gauss(12, 5))) * (3 if promo else 1)
            units = due + one_off
            orders.append({
                "date": day,
                "sku": sku,
                "units": units,
                "revenue": round(units * rng.uniform(17.5, 24.0), 2),
                "promo_flag": promo,
            })

    inventory = []
    for day in range(1_090):
        for sku in skus:
            inventory.append({
                "date": day,
                "sku": sku,
                "on_hand": max(0, int(rng.gauss(400, 120))),
                "on_order": rng.choice([0, 0, 250, 500]),
            })

    return [
        Table("coffee", "subscriptions", subscriptions),
        Table("coffee", "orders_daily", orders),
        Table("coffee", "inventory_snapshots", inventory),
    ]


PROFILES: dict[str, Callable[[], list[Table]]] = {
    "coffee": coffee_subscription,
}


def land(client: ZettaClient, tables: list[Table], staging: Path) -> list[dict[str, Any]]:
    """Write each table and load it into Zetta as a partitioned dataset."""
    landed = []
    for table in tables:
        path = table.write_jsonl(staging)
        result = client.act(
            "add_dataset",
            path=str(path.resolve()),
            database=table.database,
            table_name=table.name,
        )
        landed.append({"table": f"{table.database}.{table.name}",
                       "rows": len(table.rows),
                       "ok": result.get("ok", False)})
    return landed
