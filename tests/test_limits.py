# SPDX-License-Identifier: MIT

"""Model-written names stay inside the turn's directory, and profile size is bounded.

agent-eval-generator#21 (profile_id and table names used as paths) and agent-eval-generator#22
(no bound on tables or columns).
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from agent_eval_generator import limits, service
from agent_eval_generator.limits import ProfileRejected
from agent_eval_generator.records import Table, package
from agent_eval_generator.synth import synthesize
from test_service import PROFILE, FakeZetta, Scripted


def good_profile() -> dict:
    profile = deepcopy(PROFILE)
    profile["solution"] = "S-1"
    profile["level"] = 1
    profile["methodology"] = "M-1"
    return profile


def turn(profile: dict, trace_dir: Path) -> dict:
    return service.run_turn(
        {"request": "a test case"}, Scripted(json.dumps(profile)), FakeZetta(), "m", trace_dir
    )


@pytest.mark.parametrize("profile_id", ["/tmp/agent-eval-generator-traces", "../x", "a/b", ".",
                                        "..", "", "x.y", None, "a" * 65])
def test_an_unsafe_profile_id_is_refused(profile_id, tmp_path):
    with pytest.raises(ProfileRejected):
        limits.check_profile({"profile_id": profile_id, "tables": []})


@pytest.mark.parametrize("field,value", [("name", "/../eval-generator-2026-11-14"),
                                         ("name", "a/b"), ("name", "../x"), ("name", "x.y"),
                                         ("database", ""), ("database", "/abs"),
                                         ("database", "..")])
def test_an_unsafe_table_name_is_refused(field, value):
    spec = {"database": "crm", "name": "accounts", "rows": 10, "columns": ["id"], field: value}
    with pytest.raises(ProfileRejected):
        limits.check_profile({"profile_id": "ok", "tables": [spec]})


def test_a_turn_with_an_absolute_profile_id_writes_nothing_outside(tmp_path):
    target = tmp_path / "outside"
    target.mkdir()
    (target / "records").mkdir()
    (target / "records" / "keep.txt").write_text("other tenant's file")
    profile = good_profile()
    profile["profile_id"] = str(target)

    answer = turn(profile, tmp_path / "traces")

    assert not answer["ok"] and "profile_id" in answer["error"]
    assert (target / "records" / "keep.txt").read_text() == "other tenant's file"
    assert sorted(path.name for path in target.iterdir()) == ["records"]


def test_a_turn_with_a_traversing_table_name_writes_nothing_outside(tmp_path):
    trace_dir = tmp_path / "traces"
    trace_dir.mkdir()
    victim = trace_dir / "eval-generator-2026-11-14.jsonl"
    victim.write_text("a real trace\n")
    profile = good_profile()
    profile["profile_id"] = "../x"
    profile["tables"][0]["database"] = ""
    profile["tables"][0]["name"] = "/../" + str(victim.with_suffix(""))

    answer = turn(profile, trace_dir)

    assert not answer["ok"]
    assert victim.read_text() == "a real trace\n"
    assert not (tmp_path / "x").exists()


def test_package_refuses_a_path_outside_out(tmp_path):
    out = tmp_path / "out"
    with pytest.raises(ProfileRejected):
        package("../escaped", "", [], out)
    with pytest.raises(ProfileRejected):
        package("ok", "", [Table("", "/../../escaped", [])], out)
    assert not (tmp_path / "escaped").exists()
    assert not (tmp_path / "escaped.jsonl").exists()


def test_within_refuses_a_symbolic_link_out(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "link").symlink_to(tmp_path)
    with pytest.raises(ProfileRejected):
        limits.within(out, "link", "file")


def test_package_does_not_follow_a_records_link(tmp_path):
    out = tmp_path / "out"
    (out / "ok").mkdir(parents=True)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "keep.txt").write_text("kept")
    (out / "ok" / "records").symlink_to(elsewhere)

    package("ok", "", [Table("crm", "accounts", [{"id": 1}])], out)

    assert (elsewhere / "keep.txt").read_text() == "kept"
    assert (out / "ok" / "records" / "crm.accounts.jsonl").is_file()


def test_a_safe_profile_still_packages(tmp_path):
    directory = package("water-utility", "s", [Table("crm", "accounts", [{"id": 1}])], tmp_path)
    assert directory == (tmp_path / "water-utility").resolve()
    assert (directory / "records" / "crm.accounts.jsonl").is_file()


def test_200_tables_of_500_columns_are_refused_without_synthesizing(tmp_path, monkeypatch):
    called = []
    monkeypatch.setattr(service, "synthesize", lambda *a, **k: called.append(1) or [])
    profile = good_profile()
    profile["tables"] = [
        {"database": "crm", "name": f"t{index}", "rows": 50_000,
         "columns": [{"name": f"c{column}", "type": "int"} for column in range(500)]}
        for index in range(200)
    ]

    answer = turn(profile, tmp_path)

    assert not answer["ok"] and "tables" in answer["error"]
    assert called == [], "synthesize() is never called for a profile over the limits"


@pytest.mark.parametrize("tables,expected", [
    ([{"name": f"t{index}", "columns": ["a"], "rows": 1} for index in range(13)], "tables"),
    ([{"name": "t", "columns": [f"c{index}" for index in range(65)], "rows": 1}], "columns"),
    ([{"name": f"t{index}", "columns": [f"c{column}" for column in range(64)], "rows": 50_000}
      for index in range(2)], "cells"),
    ([{"name": "t", "columns": ["a"]}, {"name": "t", "columns": ["a"]}], "twice"),
    ([{"name": "t", "columns": ["x" * 129], "rows": 1}], "column name"),
])
def test_size_limits(tables, expected):
    with pytest.raises(ProfileRejected, match=expected):
        limits.check_profile({"profile_id": "ok", "tables": tables})


def test_synthesize_enforces_the_limits_itself():
    profile = {"profile_id": "ok",
               "tables": [{"name": "t", "columns": [f"c{index}" for index in range(65)]}]}
    with pytest.raises(ProfileRejected):
        synthesize(profile)


def test_the_committed_profile_is_within_the_limits():
    limits.check_profile(PROFILE)
