# Methodology-aware eval profiles

Eval profiles record the catalogue solution and engine methodology required by their selected
task. This keeps an agent score tied to a pipeline shape the engine could run when the profile was
generated.

## Registry input

The lake library agent has no workspace tools. Lake reads `list_methodologies` at the start of the
turn and passes that response in the turn body under `methodologies`:

```json
{
  "request": "forecast demand for a parts distributor",
  "methodologies": {
    "methodologies": [
      {
        "id": "M-4",
        "name": "Time-series forecasting",
        "solutions": ["S-5", "S-6"],
        "runnable": false,
        "partial": false,
        "issue": "https://github.com/oramasearch/zetta/issues/1043"
      }
    ]
  }
}
```

The direct Python embedding may inject a client whose `read("list_methodologies")` returns the
same payload. The batch CLI uses that path and refreshes the snapshot for every generated case.
The model receives the snapshot as context, not as a callable tool.

If an older workspace returns `unknown_capability`, the generator uses the compatibility rule
from the engine rollout: only M-1 tabular supervised learning is treated as runnable. A missing
snapshot also selects this fallback for older lake callers. Other registry errors fail the turn;
they do not silently claim M-1 support.

## Profile contract

Every newly generated `profile.json` contains:

```json
{
  "solution": "S-5",
  "methodology": "M-4",
  "runnable": false,
  "issue": "https://github.com/oramasearch/zetta/issues/1043"
}
```

The model selects `solution`, `level`, and `methodology`. The generator verifies that the selected
methodology exists and owns the solution in that turn's methodology registry. It then reads the
selected solution detail and verifies that the methodology participates at that level. This
prevents generated prose from claiming a composition the engine did not report.

Runnable profiles omit `issue`. Unrunnable profiles require it and remain valid dataset artifacts
for later releases. The service returns `result.scoreable: false` for them. A false solution state
takes precedence over the methodology state and uses the solution's issue. They are not counted as
agent failures.

## Validation

Packaging validation requires `solution`, `level`, `methodology`, the solution checks and policy,
and a boolean `runnable`. An unrunnable profile without `issue` is rejected. These checks concern
artifact completeness; run state always comes from the per-turn registry snapshots.
