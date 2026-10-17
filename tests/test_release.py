"""The version in the code has release notes, and the service reports it.

The version is read from `pyproject.toml` (and from the installed package), never repeated here, so
a version bump without a `docs/releases/v<version>.md` page fails this test.
"""

from __future__ import annotations

import tomllib
from importlib import metadata
from pathlib import Path

from agent_eval_generator import service

ROOT = Path(__file__).resolve().parent.parent
RELEASES = ROOT / "docs" / "releases"


def project_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)["project"]["version"]


def test_the_installed_package_has_the_projects_version():
    assert metadata.version("agent-eval-generator") == project_version()


def test_release_notes_exist_for_the_projects_version():
    version = project_version()
    notes = RELEASES / f"v{version}.md"
    assert notes.exists(), f"no release notes for v{version} at {notes}"
    heading = next(line for line in notes.read_text().splitlines() if line.startswith("# "))
    assert f"v{version}" in heading
    index = (RELEASES / "README.md").read_text()
    assert f"(v{version}.md)" in index


def test_healthz_reports_the_projects_version():
    body = service.health()
    assert body["ok"] is True
    assert body["agent"] == "agent-eval-generator"
    assert body["version"] == project_version()
    assert body["prompt_version"] == service.PROMPT_VERSION
