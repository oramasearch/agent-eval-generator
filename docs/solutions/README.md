# Solution-aware eval profiles

Eval profiles select a Zetta catalogue solution and capability level. The portable artifact keeps
the selected solution's exact policy and correctness expectations, so later evaluation checks the
composed product module rather than treating one methodology as the whole answer.

## Registry reads

The generator refreshes the registry for every profile:

1. `list_solutions` supplies the choices placed in model context.
2. After the model returns `solution` and `level`, `get_solution {solution}` supplies the detail
   copied into the artifact.

The list is never defined in this repository. A workspace that returns `unknown_capability` for
`list_solutions` is treated as having no solutions. Generation stops before a model call and says
the solution registry is not deployed yet. Other registry errors fail the turn.

Direct embeddings provide a source whose `read` method invokes those capabilities. Through lake,
the reads go through `workspace_query` for the turn's customer and credential. The model never
receives workspace tools; it receives the fresh read results as context.

## Profile contract

A generated profile includes the selection and the registry-owned evaluation facts:

```json
{
  "solution": "S-1",
  "level": 1,
  "methodology": "M-1",
  "runnable": false,
  "issue": "",
  "decision_policy": "Risk and treatment tiers with eligibility, contact caps, approvals, and a kill switch.",
  "solution_checks": {
    "capability_level": {"level": 1, "name": "CL-1", "description": "..."},
    "composition": [
      {"methodology": "M-1", "role": "primary", "minimum_level": 1}
    ],
    "pipeline_order": ["M-2", "M-1", "M-3"],
    "required_data_roles": [
      {"role": "entity", "required": true, "description": "customer or account"}
    ],
    "measurement_design": "...",
    "guardrails": ["..."]
  }
}
```

`composition` contains entries whose `minimum_level` is at or below the selected level.
`pipeline_order` contains those methodologies in the engine's execution order. The selected
methodology must be a member of that level's composition.

The remaining checks come directly from `get_solution`: required data roles, measurement design,
and guardrails. `decision_policy` is the solution's `decision_policy_template`. These fields are
copied rather than rewritten so an offline evaluator can compare the agent's proposed pipeline,
measurement, and action policy against the engine contract that existed when the profile was
generated.

## Run state and scoring

The profile is scoreable only when both its selected methodology and its solution report
`runnable: true`. A false solution state takes precedence and copies the solution's issue. The
artifact is retained as future coverage but returns `scoreable: false`; an unavailable product
module is not counted as an agent failure.

Packaging validation requires the level, decision policy, and every `solution_checks` member. It
also verifies that the level agrees with the selected capability-level record and that the named
methodology participates in the stored composition.
