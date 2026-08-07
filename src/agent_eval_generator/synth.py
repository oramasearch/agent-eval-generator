"""Turn an agent-declared schema into real records.

The agent invents the situation and the schema; this makes the rows. Types are inferred from the
declared column type and name, and a declared `null_fraction` is HONOURED — if the profile says a
column is null on 31% of rows, the records really are.
"""

from __future__ import annotations

import random
from typing import Any

from agent_eval_generator.records import Table


# Plausible value pools by column name. Not exhaustive — the fallback derives a value from the
# column's own name, which is still meaningful where this table is not.
_DOMAINS: dict[str, list[str]] = {
    "sku": ["SKU-1042", "SKU-2277", "SKU-3391", "SKU-4820", "SKU-5163"],
    "status": ["active", "pending", "suspended", "closed"],
    "state": ["CA", "TX", "NY", "IL", "FL", "WA", "OH"],
    "segment": ["smb", "mid-market", "enterprise", "strategic"],
    "channel": ["email", "phone", "chat", "field", "partner"],
    "priority": ["p1", "p2", "p3", "p4"],
    "region": ["emea", "amer", "apac", "latam"],
    "currency": ["USD", "EUR", "GBP", "JPY"],
    "reason": ["price", "support", "product fit", "consolidation", "budget"],
    "type": ["standard", "expedited", "recurring", "one-off"],
    "model": ["EX-210", "EX-330", "LD-90", "CT-450"],
    "email": ["ops@example.com", "billing@example.com", "支持@example.com"],
    "name": ["Northwind Trading", "Acme Logistics", "Harbor Foods", "Vertex Mining"],
}


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

    # A string column gets a value that PLAUSIBLY belongs to it. The first version returned
    # alpha/beta/gamma for everything, which produced `"sku": "alpha"` — random noise shaped like a
    # schema, the exact thing the profile rules say teaches nothing. A model cannot learn to read
    # data that carries no meaning.
    for key, pool in _DOMAINS.items():
        if key in name:
            return rng.choice(pool)
    return f"{name.replace('_', '-')}-{rng.randrange(1000):03d}"


def synthesize(profile: dict[str, Any], seed: int = 11) -> list[Table]:
    """Build one Table per declared table, honouring row counts and null fractions."""
    rng = random.Random(seed)
    tables: list[Table] = []
    for spec in profile.get("tables", []):
        columns = spec.get("columns") or []
        declared = int(spec.get("rows") or 5_000)
        count = min(declared, 50_000)
        # Record the sampling ON the spec. A profile that declares 876,000 rows beside a
        # 50,000-line file misstates the artifact, and a model told a table is 876,000 rows may
        # reason differently about sampling and partitioning than one told it has 50,000. Both
        # numbers are true; the artifact has to carry both.
        if count < declared:
            spec["records_sampled"] = count
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
