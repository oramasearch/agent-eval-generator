"""Turn an agent-declared schema into real records.

The agent invents the situation and the schema; this makes the rows. Types are inferred from the
declared column type and name, and a declared `null_fraction` is HONOURED — if the profile says a
column is null on 31% of rows, the records really are.
"""

from __future__ import annotations

import random
from typing import Any

from agent_eval_generator.records import Table


def _value(column: dict[str, Any], rng: random.Random, row: int) -> Any:
    name = column.get("name", "").lower()
    kind = str(column.get("type", "string")).lower()
    if "id" in name and rng.random() < 0.9:
        return f"{name[:6]}_{row:07d}"
    if any(k in kind for k in ("time", "date")):
        return rng.randint(0, 1200)
    if any(k in kind for k in ("float", "double", "decimal", "number")):
        return round(rng.lognormvariate(5.0, 1.0), 3)
    if any(k in kind for k in ("int", "long")):
        return rng.randint(0, 5000)
    if "bool" in kind:
        return rng.random() < 0.2
    if "geo" in kind:
        return [round(rng.uniform(-90, 90), 4), round(rng.uniform(-180, 180), 4)]
    return rng.choice(["alpha", "beta", "gamma", "delta", "epsilon"])


def synthesize(profile: dict[str, Any], seed: int = 11) -> list[Table]:
    """Build one Table per declared table, honouring row counts and null fractions."""
    rng = random.Random(seed)
    tables: list[Table] = []
    for spec in profile.get("tables", []):
        columns = spec.get("columns") or []
        count = min(int(spec.get("rows") or 5_000), 50_000)
        rows = []
        for index in range(count):
            row: dict[str, Any] = {}
            for column in columns:
                if isinstance(column, str):
                    column = {"name": column, "type": "string"}
                null_fraction = float(column.get("null_fraction") or 0.0)
                row[column["name"]] = (
                    None if rng.random() < null_fraction else _value(column, rng, index)
                )
            rows.append(row)
        tables.append(Table(spec.get("database", "main"), spec["name"], rows))
    return tables
