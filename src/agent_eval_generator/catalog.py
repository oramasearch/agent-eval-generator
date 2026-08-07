"""Profiles across the solutions catalogue.

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
class Family:
    """One catalogue solution's data shape."""

    solution: str               # "S-1"
    slug: str                   # "churn"
    industry: str
    connections: list[dict[str, str]]
    build: Callable[[random.Random], list[Table]]


# --- schema families -------------------------------------------------------------------------
# Each carries real structure: something a model can only get right by reading the tables.

def churn_tables(rng: random.Random) -> list[Table]:
    """S-1. The label lives in the account dimension, not the events table — the join is the job."""
    accounts, events = [], []
    for index in range(12_000):
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
    for index in range(140_000):
        account = rng.randrange(12_000)
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


def maintenance_tables(rng: random.Random) -> list[Table]:
    """S-8. `closed_at` is null on open orders — using it as a label window drops failing assets."""
    assets, orders = [], []
    for index in range(8_400):
        assets.append({
            "asset_id": f"ast_{index:05d}",
            "model": rng.choice(["EX-210", "EX-330", "LD-90", "LD-140"]),
            "year": rng.randint(2012, 2024),
            "acquired_at": rng.randint(0, 1200),
            "depot_id": rng.choice(["D1", "D2", "D3", "D4"]),
        })
    for index in range(61_000):
        opened = rng.randint(0, 1200)
        closed = opened + rng.randint(1, 40) if rng.random() > 0.31 else None
        orders.append({
            "work_order_id": f"wo_{index:06d}",
            "asset_id": f"ast_{rng.randrange(8_400):05d}",
            "opened_at": opened,
            "closed_at": closed,
            "fault_code": rng.choice(["HYD", "ENG", "ELEC", "STR", None]),
            "is_breakdown": rng.random() < 0.19,
            "labour_hours": round(rng.uniform(0.5, 22.0), 1),
        })
    return [Table("fleet", "assets", assets), Table("fleet", "work_orders", orders)]


def claims_tables(rng: random.Random) -> list[Table]:
    """S-12. `total_paid` only exists after close — training on it leaks the outcome into triage."""
    claims, policies = [], []
    for index in range(190_00):
        policies.append({
            "policy_id": f"pol_{index:06d}",
            "inception": rng.randint(0, 1000),
            "expiry": rng.randint(1000, 1400),
            "state": rng.choice(["CA", "TX", "NY", "IL", "FL"]),
            "premium": round(rng.lognormvariate(8.4, 0.7), 2),
        })
    for index in range(110_000):
        reported = rng.randint(0, 1200)
        closed = reported + rng.randint(5, 400) if rng.random() < 0.78 else None
        claims.append({
            "claim_id": f"clm_{index:07d}",
            "policy_id": f"pol_{rng.randrange(19000):06d}",
            "reported_at": reported,
            "loss_date": reported - rng.randint(0, 30),
            "line_of_business": rng.choice(["gl", "property", "auto", "wc"]),
            "reserve_amount": round(rng.lognormvariate(8.0, 1.1), 2),
            "closed_at": closed,
            "total_paid": round(rng.lognormvariate(7.8, 1.2), 2) if closed else None,
            "siu_referred": rng.random() < 0.023,
        })
    return [Table("claims", "claims", claims), Table("claims", "policies", policies)]


def demand_tables(rng: random.Random) -> list[Table]:
    """S-5. Subscriptions largely DETERMINE orders — reading them beats forecasting the aggregate."""
    from agent_eval_generator.records import coffee_subscription
    return coffee_subscription(rng.randint(1, 10_000))


FAMILIES: list[Family] = [
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
            rng = random.Random(hash((family.slug, index)) & 0xFFFF)
            profile_id = f"{family.slug}-{persona.role.lower().replace(' ', '-').replace(',', '')}"
            out.append((profile_id, family, persona, family.build(rng)))
            if limit and len(out) >= limit:
                return out
    return out
