"""Validate a generated profile before it is published.

Two defects reached the Hub before this existed, and both were visible in ten seconds of looking:
a `coffee.inventory_snapshots.jsonl` inside an agricultural-equipment-rental profile (stale records
from a reused directory), and `"sku": "alpha"` (a fallback value that meant nothing).

Neither was caught by anything, because nothing looked. A generator that cannot check its own
output publishes its mistakes at the speed it makes them — and an eval nobody reviews is one whose
defects reach a model.

Every check answers a question a reviewer would ask, and each returns a reason a person can act on
rather than a boolean.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _rows(path: Path, limit: int = 500) -> list[dict[str, Any]]:
    rows = []
    with path.open() as handle:
        for index, line in enumerate(handle):
            if index >= limit:
                break
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                return []
    return rows


def validate(directory: Path) -> list[str]:
    """Return the problems found. Empty means publishable."""
    problems: list[str] = []

    profile_path = directory / "profile.json"
    if not profile_path.exists():
        return ["no profile.json"]
    try:
        profile = json.loads(profile_path.read_text())
    except json.JSONDecodeError as error:
        return [f"profile.json is not valid JSON: {error}"]

    for field in ("profile_id", "tables", "persona"):
        if not profile.get(field):
            problems.append(f"profile.json is missing `{field}`")

    declared = {f"{t.get('database')}.{t.get('name')}" for t in profile.get("tables", [])}
    records = directory / "records"
    present = {p.name.removesuffix(".jsonl") for p in records.glob("*.jsonl")} if records.exists() else set()

    # THE check that would have caught the coffee-in-agriculture defect: a record file nobody
    # declared is a leftover from another profile, and it is invisible unless you look.
    for stray in sorted(present - declared):
        problems.append(f"records/{stray}.jsonl is not declared in profile.json (stale file?)")
    for missing in sorted(declared - present):
        problems.append(f"table `{missing}` is declared but has no records file")

    for table in profile.get("tables", []):
        name = f"{table.get('database')}.{table.get('name')}"
        path = records / f"{name}.jsonl"
        if not path.exists():
            continue
        rows = _rows(path)
        if not rows:
            problems.append(f"`{name}` has no readable rows")
            continue

        columns = []
        for column in table.get("columns", []):
            columns.append({"name": column, "type": "string"} if isinstance(column, str) else column)
        declared_names = {c["name"] for c in columns}
        actual_names = set(rows[0])
        for extra in sorted(actual_names - declared_names):
            problems.append(f"`{name}` has undeclared column `{extra}`")
        for absent in sorted(declared_names - actual_names):
            problems.append(f"`{name}` declares `{absent}` but no row carries it")

        # A declared null_fraction that the records do not honour means the awkwardness was
        # described rather than generated — which is the whole property these profiles rest on.
        for column in columns:
            declared_null = float(column.get("null_fraction") or 0.0)
            if declared_null <= 0.0 or column["name"] not in actual_names:
                continue
            observed = sum(1 for row in rows if row.get(column["name"]) is None) / len(rows)
            if abs(observed - declared_null) > 0.15:
                problems.append(
                    f"`{name}.{column['name']}` declares null_fraction {declared_null:.2f} but "
                    f"{observed:.2f} of sampled rows are null — the awkwardness was described, "
                    f"not generated")

        # Placeholder values mean the generator fell back rather than producing something the
        # column could plausibly hold. `"sku": "alpha"` shipped to the Hub before this check.
        placeholders = {"alpha", "beta", "gamma", "delta", "epsilon", "string", "value", "foo"}
        for column_name in sorted(actual_names):
            sample = [row.get(column_name) for row in rows[:60]]
            hits = sum(1 for value in sample if isinstance(value, str) and value.lower() in placeholders)
            if hits > len(sample) * 0.5:
                problems.append(
                    f"`{name}.{column_name}` is mostly placeholder values — a column that carries "
                    f"no meaning cannot be read, so it teaches nothing")

        # `rows` is how big the SOURCE is; `records_sampled` is how many were packaged. They are
        # allowed to differ — a 500,000-row source with a 50,000-row sample is honest — but the
        # artifact has to SAY so. A declared 500,000 beside a 50,000-line file is a lie about the
        # thing being published, and a model told the table is 500,000 rows may reason differently.
        actual = sum(1 for _ in path.open())
        sampled = table.get("records_sampled")
        if sampled is None:
            if table.get("rows") and abs(table["rows"] - actual) > max(5, table["rows"] * 0.02):
                problems.append(
                    f"`{name}` declares {table['rows']} rows and the file has {actual} — set "
                    f"`records_sampled` to say the records are a sample of a larger source")
        elif abs(int(sampled) - actual) > max(5, int(sampled) * 0.02):
            problems.append(f"`{name}` claims {sampled} sampled records but the file has {actual}")

    situation = directory / "situation.md"
    if not situation.exists() or len(situation.read_text().strip()) < 120:
        problems.append("situation.md is missing or too thin to describe a situation")

    if not any(c.get("state") == "captured" for c in profile.get("connections", [])):
        problems.append("no connection is `captured` — nothing here could be trained on")

    return problems
