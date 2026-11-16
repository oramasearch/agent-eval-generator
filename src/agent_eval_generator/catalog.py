# SPDX-License-Identifier: MIT

"""Profiles across the solutions catalogue — SEED MATERIAL, not the generator.

**This module is a cross-product, and a cross-product is not diversity.** Five families x five
personas x five scales produces 125 profiles that are combinations of fifteen things — one shape
wearing many names, which is precisely the defect that made a 14,889-case corpus teach two
pipeline shapes.

Keep it for what it is good for: a handful of known-good schema families with real structure, to
seed the agent and to regression-test the packaging path. **Quantity comes from the agent** (see
`prompts/v1.md`), which researches an industry, invents a situation nobody has seen, and is told
that if it produces a structure it has produced before it should pick something further away.


Volume and depth pull against each other here. The skill's own rule is that random noise shaped
like a schema teaches nothing — so variation comes from SITUATIONS over a small number of real
schemas, not from inventing a new table shape per profile.

Each catalogue entry contributes one schema family with genuine structure. Each persona varies the
things that change the correct answer: what the person can act on, what state their sources are in,
and the scale they operate at. Twelve families x several personas gives breadth without pretending
a made-up column teaches something.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable

from agent_eval_generator.records import Table


@dataclass(frozen=True)
class Persona:
    name: str
    role: str
    context: str
    measured_on: list[str]
    constraints: list[str]      # each must NARROW the space of correct answers


@dataclass(frozen=True)
class Scale:
    """Scale is real variation, not padding.

    The correct answer changes with it: at 12k rows you fit on everything, at 4M you sample or
    partition and the choice becomes part of the pipeline. A null rate that is a nuisance on a
    small table biases every aggregate on a large one. And a model that reads row counts before
    proposing an approach is doing something a model that pattern-matches the ask cannot.
    """

    name: str
    factor: float


SCALES: list[Scale] = [
    Scale("startup", 0.08),
    Scale("smb", 0.3),
    Scale("mid", 1.0),
    Scale("large", 4.0),
    Scale("enterprise", 16.0),
]


@dataclass(frozen=True)
class Family:
    """One catalogue solution's data shape."""

    solution: str               # "S-1"
    slug: str                   # "churn"
    industry: str
    connections: list[dict[str, str]]
    build: Callable[[random.Random, float], list[Table]]


# --- schema families -------------------------------------------------------------------------
# Each carries real structure: something a model can only get right by reading the tables.

def churn_tables(rng: random.Random, scale: float = 1.0) -> list[Table]:
    """S-1. The label lives in the account dimension, not the events table — the join is the job."""
    accounts, events = [], []
    for index in range(int(12_000 * scale)):
        signed = rng.randint(0, 900)
        churned = signed + rng.randint(60, 700) if rng.random() < 0.22 else None
        accounts.append({
            "account_id": f"acct_{index:06d}",
            "segment": rng.choice(["smb", "mid", "ent"]),
            "signed_at": signed,
            "mrr": round(rng.lognormvariate(6.2, 0.8), 2),
            "churn_date": churned,
            "last_churn_reason": rng.choice(["price", "support", "fit", None]) if churned else None,
        })
    for index in range(int(140_000 * scale)):
        account = rng.randrange(max(1, int(12_000 * scale)))
        events.append({
            "event_id": f"ev_{index:07d}",
            # Null on a fraction of rows, and the fraction differs by channel — the bias is real.
            "sfdc_account_id": None if rng.random() < 0.114 else f"acct_{account:06d}",
            "channel": rng.choice(["email", "chat", "phone", "ticket"]),
            "occurred_at": rng.randint(0, 900),
            "event_updated_datetime_pt": rng.randint(0, 900),  # load date, not source change date
            "sentiment": round(rng.uniform(-1, 1), 3),
        })
    return [Table("crm", "accounts", accounts), Table("crm", "comm_events", events)]


def maintenance_tables(rng: random.Random, scale: float = 1.0) -> list[Table]:
    """S-8. `closed_at` is null on open orders — using it as a label window drops failing assets."""
    assets, orders = [], []
    for index in range(int(8_400 * scale)):
        assets.append({
            "asset_id": f"ast_{index:05d}",
            "model": rng.choice(["EX-210", "EX-330", "LD-90", "LD-140"]),
            "year": rng.randint(2012, 2024),
            "acquired_at": rng.randint(0, 1200),
            "depot_id": rng.choice(["D1", "D2", "D3", "D4"]),
        })
    for index in range(int(61_000 * scale)):
        opened = rng.randint(0, 1200)
        closed = opened + rng.randint(1, 40) if rng.random() > 0.31 else None
        orders.append({
            "work_order_id": f"wo_{index:06d}",
            "asset_id": f"ast_{rng.randrange(max(1, int(8_400 * scale))):05d}",
            "opened_at": opened,
            "closed_at": closed,
            "fault_code": rng.choice(["HYD", "ENG", "ELEC", "STR", None]),
            "is_breakdown": rng.random() < 0.19,
            "labour_hours": round(rng.uniform(0.5, 22.0), 1),
        })
    return [Table("fleet", "assets", assets), Table("fleet", "work_orders", orders)]


def claims_tables(rng: random.Random, scale: float = 1.0) -> list[Table]:
    """S-12. `total_paid` only exists after close — training on it leaks the outcome into triage."""
    claims, policies = [], []
    for index in range(int(190_00 * scale)):
        policies.append({
            "policy_id": f"pol_{index:06d}",
            "inception": rng.randint(0, 1000),
            "expiry": rng.randint(1000, 1400),
            "state": rng.choice(["CA", "TX", "NY", "IL", "FL"]),
            "premium": round(rng.lognormvariate(8.4, 0.7), 2),
        })
    for index in range(int(110_000 * scale)):
        reported = rng.randint(0, 1200)
        closed = reported + rng.randint(5, 400) if rng.random() < 0.78 else None
        claims.append({
            "claim_id": f"clm_{index:07d}",
            "policy_id": f"pol_{rng.randrange(max(1, int(19000 * scale))):06d}",
            "reported_at": reported,
            "loss_date": reported - rng.randint(0, 30),
            "line_of_business": rng.choice(["gl", "property", "auto", "wc"]),
            "reserve_amount": round(rng.lognormvariate(8.0, 1.1), 2),
            "closed_at": closed,
            "total_paid": round(rng.lognormvariate(7.8, 1.2), 2) if closed else None,
            "siu_referred": rng.random() < 0.023,
        })
    return [Table("claims", "claims", claims), Table("claims", "policies", policies)]


def demand_tables(rng: random.Random, scale: float = 1.0) -> list[Table]:
    """S-5. Subscriptions largely DETERMINE orders — reading them beats forecasting the aggregate."""
    from agent_eval_generator.records import coffee_subscription
    return coffee_subscription(rng.randint(1, 10_000), scale)


def multi_source_tables(rng: random.Random, scale: float = 1.0) -> list[Table]:
    """A business with MANY sources, where several solutions are simultaneously supportable.

    The single-source profiles ask "is this task supportable?". This one asks a harder question:
    **which set of tasks, and in what order?** Auto-Suggest has to propose several, and the good
    answer has DEPENDENCIES in it:

      * `crm.accounts` and `billing.invoices` describe the same customers under different ids, so
        **entity resolution comes before anything account-level** — a churn model built on the
        unresolved join silently trains on two populations.
      * A churn score is an input to next-best-action, not a competitor to it. Proposing both as
        independent projects misses that one feeds the other.
      * `support.tickets` and `web.sessions` are captured; `product.telemetry` is not. A task that
        needs telemetry is "capture it first", and that ordering is part of the answer.

    None of this is stated anywhere. Whether Auto-Suggest sees the links is the measurement.
    """
    accounts, invoices, tickets, sessions, telemetry = [], [], [], [], []
    count = max(1, int(9_000 * scale))

    for index in range(count):
        signed = rng.randint(0, 900)
        accounts.append({
            "account_id": f"acct_{index:06d}",
            "company_name": f"Company {index}",
            "segment": rng.choice(["smb", "mid", "ent"]),
            "signed_at": signed,
            "mrr": round(rng.lognormvariate(6.2, 0.8), 2),
            "churn_date": signed + rng.randint(60, 700) if rng.random() < 0.21 else None,
        })

    # Billing knows the same customers by a DIFFERENT key, and the names do not match exactly.
    for index in range(count):
        invoices.append({
            "invoice_id": f"inv_{index:07d}",
            "billing_customer_id": f"bc_{index:06d}",
            "customer_name": f"Company {index}" + rng.choice(["", " Inc", " Ltd", ", Inc."]),
            "issued_at": rng.randint(0, 900),
            "amount": round(rng.lognormvariate(6.4, 0.9), 2),
            "days_late": max(0, int(rng.gauss(4, 14))),
            "written_off": rng.random() < 0.03,
        })

    for index in range(max(1, int(48_000 * scale))):
        tickets.append({
            "ticket_id": f"tkt_{index:07d}",
            "account_id": f"acct_{rng.randrange(count):06d}",
            "opened_at": rng.randint(0, 900),
            "priority": rng.choice(["p1", "p2", "p3", "p4"]),
            "resolved_hours": round(rng.expovariate(1 / 18.0), 1),
            "csat": rng.choice([1, 2, 3, 4, 5, None]),
        })

    for index in range(max(1, int(120_000 * scale))):
        sessions.append({
            "session_id": f"ses_{index:08d}",
            "account_id": None if rng.random() < 0.23 else f"acct_{rng.randrange(count):06d}",
            "started_at": rng.randint(0, 900),
            "duration_s": max(1, int(rng.expovariate(1 / 340.0))),
            "pages": rng.randint(1, 40),
        })

    # Discovered, not captured — anything needing it is "capture it first".
    for index in range(max(1, int(20_000 * scale))):
        telemetry.append({
            "event_id": f"tel_{index:08d}",
            "account_id": f"acct_{rng.randrange(count):06d}",
            "feature": rng.choice(["export", "api", "dashboard", "alerting"]),
            "used_at": rng.randint(0, 900),
        })

    return [
        Table("crm", "accounts", accounts),
        Table("billing", "invoices", invoices),
        Table("support", "tickets", tickets),
        Table("web", "sessions", sessions),
        Table("product", "telemetry", telemetry),
    ]


FAMILIES: list[Family] = [
    Family("S-1/S-4/S-11", "multi-source", "B2B SaaS with several systems",
           [{"name": "sfdc_pg", "kind": "postgres", "state": "captured"},
            {"name": "netsuite_billing", "kind": "rest", "state": "captured"},
            {"name": "zendesk_pg", "kind": "postgres", "state": "captured"},
            {"name": "ga4_bq", "kind": "bigquery", "state": "captured"},
            {"name": "product_kafka", "kind": "kafka", "state": "discovered"},
            {"name": "hubspot_api", "kind": "rest", "state": "discovered"}],
           multi_source_tables),
    Family("S-1", "churn", "B2B SaaS",
           [{"name": "sfdc_pg", "kind": "postgres", "state": "captured"},
            {"name": "zendesk_api", "kind": "rest", "state": "discovered"}],
           churn_tables),
    Family("S-8", "predictive-maintenance", "equipment rental",
           [{"name": "fleet_pg", "kind": "postgres", "state": "captured"},
            {"name": "telemetry_s3", "kind": "s3", "state": "discovered"}],
           maintenance_tables),
    Family("S-12", "claims-triage", "specialty insurance",
           [{"name": "guidewire_replica", "kind": "postgres", "state": "captured"},
            {"name": "nicb_api", "kind": "rest", "state": "discovered"}],
           claims_tables),
    Family("S-5", "demand-forecasting", "DTC subscription",
           [{"name": "shopify_bq", "kind": "bigquery", "state": "captured"},
            {"name": "ga4_bq", "kind": "bigquery", "state": "discovered"}],
           demand_tables),
]

# Personas vary what changes the ANSWER: authority, capacity, obligation, cadence.
PERSONAS: list[Persona] = [
    Persona("the operator", "Director of Operations", "Eight years in the business; not technical.",
            ["utilization", "unplanned downtime"],
            ["Can action roughly 40 items a month and no more."]),
    Persona("the analyst", "Senior Analyst", "Reports to Finance; writes SQL daily.",
            ["forecast accuracy", "month-end close time"],
            ["Anything shipped must be reproducible by a colleague from the query alone."]),
    Persona("the regulated owner", "VP, regulated line", "Answers to a regulator and a reinsurer.",
            ["cycle time", "leakage"],
            ["Must be able to explain any individual decision on request.",
             "No decision may be taken without a named human approving that instance."]),
    Persona("the executive", "Chief Operating Officer", "Reads one number a week; delegates the rest.",
            ["margin", "on-time delivery"],
            ["Will only act on something that names the single account or asset to touch."]),
    Persona("the small team", "Head of Function", "Third hire; two people including them.",
            ["stockouts", "waste"],
            ["Orders are placed weekly on a fixed day and cannot be changed once placed."]),
]


def generate(limit: int | None = None) -> list[tuple[str, Family, Persona, list[Table]]]:
    """Every (family x persona) pairing. The same tables under a different situation is a
    DIFFERENT eval — that is the point, not a shortcut."""
    out = []
    for family in FAMILIES:
        for index, persona in enumerate(PERSONAS):
            for scale in SCALES:
                rng = random.Random(hash((family.slug, index, scale.name)) & 0xFFFF)
                role = persona.role.lower().replace(" ", "-").replace(",", "")
                profile_id = f"{family.slug}-{role}-{scale.name}"
                out.append((profile_id, family, persona, family.build(rng, scale.factor)))
                if limit and len(out) >= limit:
                    return out
    return out
