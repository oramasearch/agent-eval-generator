"""What a model-written profile may contain before anything is written or synthesized.

The profile comes from the model, and the person's request and the registry text steer the model.
Its `profile_id` and its tables' `database` and `name` become file names, and its table and column
counts decide how much memory and disk a turn uses in a pod that every workspace shares. So both
are checked here, right after parsing (agent-eval-generator#21, agent-eval-generator#22):

* **Names are single, safe path components.** `profile_id`, `database` and `name` must match
  `SAFE_NAME`: a letter or digit, then letters, digits, `_` or `-`, at most 64 characters. No `/`,
  no `.`, no `..`, no absolute path. `within()` then resolves every path and refuses one that is not
  inside the directory it was meant for.
* **Size is bounded.** At most `MAX_TABLES` tables, `MAX_COLUMNS` columns per table and
  `CELL_BUDGET` generated cells (rows times columns, after the `MAX_ROWS` sample cap) in one
  profile.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
MAX_TABLES = 12
MAX_COLUMNS = 64
MAX_ROWS = 50_000
CELL_BUDGET = 5_000_000
MAX_COLUMN_NAME = 128
DEFAULT_DATABASE = "main"
DEFAULT_ROWS = 5_000


class ProfileRejected(ValueError):
    """A profile that may not be written or synthesized; the message says why."""


def safe_name(value: Any, what: str) -> str:
    """`value` if it is one safe path component, else ProfileRejected."""
    if not isinstance(value, str) or not SAFE_NAME.fullmatch(value):
        raise ProfileRejected(
            f"{what} {value!r} is not a safe name: use 1-64 letters, digits, '_' or '-', "
            "starting with a letter or digit"
        )
    return value


def within(base: Path, *parts: str) -> Path:
    """`base / parts`, resolved, and refused unless it stays inside `base`."""
    root = base.resolve()
    path = root.joinpath(*parts).resolve()
    if path == root or not path.is_relative_to(root):
        raise ProfileRejected(f"{'/'.join(parts)!r} resolves outside {root}")
    return path


def table_database(spec: dict[str, Any]) -> str:
    value = spec.get("database")
    return DEFAULT_DATABASE if value is None else value


def table_rows(spec: dict[str, Any]) -> tuple[int, int]:
    """The declared row count and the count that will be generated."""
    try:
        declared = int(spec.get("rows") or DEFAULT_ROWS)
    except (TypeError, ValueError) as error:
        raise ProfileRejected(f"table {spec.get('name')!r} rows is not a number") from error
    return declared, max(0, min(declared, MAX_ROWS))


def check_profile(profile: dict[str, Any]) -> None:
    """Raise ProfileRejected when the profile's names or size are outside the limits."""
    safe_name(profile.get("profile_id"), "profile_id")
    tables = profile.get("tables", [])
    if not isinstance(tables, list):
        raise ProfileRejected("tables must be a list")
    if len(tables) > MAX_TABLES:
        raise ProfileRejected(f"{len(tables)} tables is more than the limit of {MAX_TABLES}")
    cells = 0
    seen: set[tuple[str, str]] = set()
    for spec in tables:
        if not isinstance(spec, dict):
            raise ProfileRejected("every table must be an object")
        database = safe_name(table_database(spec), "table database")
        name = safe_name(spec.get("name"), "table name")
        if (database, name) in seen:
            raise ProfileRejected(f"table {database}.{name} is declared twice")
        seen.add((database, name))
        columns = spec.get("columns") or []
        if not isinstance(columns, list):
            raise ProfileRejected(f"table {database}.{name} columns must be a list")
        if len(columns) > MAX_COLUMNS:
            raise ProfileRejected(
                f"table {database}.{name} has {len(columns)} columns, more than the limit of "
                f"{MAX_COLUMNS}"
            )
        for column in columns:
            column_name = column if isinstance(column, str) else (
                column.get("name") if isinstance(column, dict) else None)
            if not isinstance(column_name, str) or not column_name:
                raise ProfileRejected(f"table {database}.{name} has a column without a name")
            if len(column_name) > MAX_COLUMN_NAME:
                raise ProfileRejected(
                    f"table {database}.{name} has a column name longer than {MAX_COLUMN_NAME}"
                )
        _, count = table_rows(spec)
        cells += count * len(columns)
    if cells > CELL_BUDGET:
        raise ProfileRejected(
            f"the profile would generate {cells:,} cells, more than the budget of {CELL_BUDGET:,}"
        )
