"""The batch command line uploads only to a dataset it is given (EVAL_PROFILES_DATASET)."""

from pathlib import Path

from agent_eval_generator import agent


def test_no_dataset_configured_means_no_upload(monkeypatch):
    monkeypatch.delenv(agent.UPLOAD_DATASET_ENV, raising=False)
    assert agent.upload_dataset() is None
    monkeypatch.setenv(agent.UPLOAD_DATASET_ENV, "   ")
    assert agent.upload_dataset() is None


def test_the_configured_dataset_is_the_upload_target(monkeypatch):
    monkeypatch.setenv(agent.UPLOAD_DATASET_ENV, "someone/eval-profiles")
    assert agent.upload_dataset() == "someone/eval-profiles"
    command = agent.upload_command("someone/eval-profiles", Path("evals/profiles/p1"), "p1", 12)
    assert command[:3] == ["hf", "upload", "someone/eval-profiles"]
    assert command[3:6] == ["evals/profiles/p1", "p1", "--repo-type=dataset"]
    assert command[6] == "--commit-message=p1: 12 records"
