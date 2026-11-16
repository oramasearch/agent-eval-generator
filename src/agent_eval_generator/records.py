# SPDX-License-Identifier: MIT

"""Generate the RECORDS a profile comes with, and package it as a portable eval dataset.

A profile is not a description of data that exists elsewhere — it comes with its data. And it is
an **eval artifact published to HuggingFace**, not a fixture for an engine: its job is to evaluate
Auto-Suggest (does it propose the right tasks for this situation?) and then project creation (is
the Pipeline it builds correct for this data?). Both must be scoreable **without a running Zetta
node**, so a profile has to be self-contained and portable.

`land()` remains for the case where someone wants the tables queryable in Zetta, but that is a
convenience, not what a profile is for.

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

from agent_eval_generator.limits import safe_name, within
from agent_eval_generator.tools import ZettaClient


@dataclass
class Table:
    """One table of a profile: where it lands in Zetta, and the rows themselves."""

    database: str
    name: str
    rows: list[dict[str, Any]]

    def write_jsonl(self, directory: Path) -> Path:
        # database and name come from the model: each must be one safe path component, and the
        # file must resolve inside `directory` (agent-eval-generator#21).
        database = safe_name(self.database, "table database")
        name = safe_name(self.name, "table name")
        directory.mkdir(parents=True, exist_ok=True)
        path = within(directory, f"{database}.{name}.jsonl")
        with path.open("w") as handle:
            for row in self.rows:
                handle.write(json.dumps(row) + "\n")
        return path


def coffee_subscription(seed: int = 7, scale: float = 1.0) -> list[Table]:
    """Profile C — Dana, DTC coffee subscription.

    The structure that matters: subscriptions largely DETERMINE daily orders. An agent that reads
    `subscriptions` can predict most of `orders_daily` from cadence alone; one that forecasts the
    aggregate in isolation will produce a backtest a spreadsheet beats. That is a property of the
    generated data, not a hint in the profile.
    """
    rng = random.Random(seed)
    skus = ["ETH-YIRG", "COL-HUILA", "BRZ-CERR", "KEN-AA", "GUA-ANTI"]

    subscriptions: list[dict[str, Any]] = []
    for index in range(max(1, int(47_000 * scale))):
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
    for day in range(max(30, int(1_090 * min(scale, 3.0)))):
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
    for day in range(max(30, int(1_090 * min(scale, 3.0)))):
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


def package(profile: str, situation: str, tables: list[Table], out: Path) -> Path:
    """Write a self-contained profile: the situation, the schemas, and the records.

    This is the artifact that goes to HuggingFace. It must be readable and scoreable with no Zetta
    node running — a model being evaluated on it should need nothing but the files.
    """
    # `profile` is the model's profile_id: one safe path component, resolved inside `out`, or the
    # profile is refused before anything is written or deleted (agent-eval-generator#21).
    out.mkdir(parents=True, exist_ok=True)
    directory = within(out, safe_name(profile, "profile_id"))
    # Clear records first. Without this a previous profile's files persist in a reused directory
    # and get uploaded under the new name — which put `coffee.inventory_snapshots.jsonl` inside an
    # agricultural-equipment-rental profile on the Hub. Only a real directory inside `out` is
    # removed, never a symbolic link: the per-turn temporary directory is empty anyway.
    import shutil
    records = directory / "records"
    if records.is_symlink():
        records.unlink()
    elif records.is_dir():
        within(out, directory.name, "records")
        shutil.rmtree(records)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "situation.md").write_text(situation)

    schema = {
        "profile": profile,
        "tables": [
            {
                "database": table.database,
                "name": table.name,
                "rows": len(table.rows),
                "columns": sorted({key for row in table.rows[:200] for key in row}),
            }
            for table in tables
        ],
    }
    (directory / "schema.json").write_text(json.dumps(schema, indent=2))
    for table in tables:
        table.write_jsonl(directory / "records")
    return directory


def land(client: ZettaClient, tables: list[Table], staging: Path) -> list[dict[str, Any]]:
    """Optionally load the tables into Zetta as partitioned datasets.

    A convenience for working against a live node. NOT what a profile is for — the profile is the
    portable artifact written by `package()`.
    """
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
