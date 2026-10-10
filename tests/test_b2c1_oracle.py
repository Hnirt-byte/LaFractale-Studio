"""Independent B2-B byte-regression oracle required before C1 routing."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
BASE = "d77e32327fecd0c4a983ef8298581525842c18fc"
PIN = "93c58e86a74e903af1be5cd4257d489c39bece8f5cd41d985586cbf775d45e61"


def test_b2b_oracle_compares_isolated_reference_and_candidate_byte_for_byte(tmp_path):
    """The C1 checkout must remain byte-identical for both historical modes."""
    proof = tmp_path / "b2b-oracle-proof.json"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "verify_b2b_oracle.py"),
            "--candidate-repo", str(ROOT),
            "--reference-commit", BASE,
            "--approvals-sha256", PIN,
            "--proof", str(proof),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "B2B_ORACLE_OK" in result.stdout
    payload = json.loads(proof.read_text(encoding="utf-8"))
    assert payload["reference_commit"] == BASE
    assert isinstance(payload["candidate_head"], str) and len(payload["candidate_head"]) == 40
    assert isinstance(payload["candidate_tree"], str) and len(payload["candidate_tree"]) == 40
    assert isinstance(payload["candidate_snapshot_inventory"], dict)
    assert isinstance(payload["candidate_python_source_files"], dict)
    assert isinstance(payload["candidate_python_source_sha256"], str)
    assert isinstance(payload["candidate_initial_status_sha256"], str)
    assert payload["reference_source"] != payload["candidate_source"]
    assert [case["mode"] for case in payload["cases"]] == ["placeholder", "legacy_illustration"]
    assert all(case["identical"] is True for case in payload["cases"])
    assert all(case["reference_qa"] == 0 and case["candidate_qa"] == 0 for case in payload["cases"])


def _oracle_module():
    path = ROOT / "tools" / "verify_b2b_oracle.py"
    spec = importlib.util.spec_from_file_location("b2b_oracle_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _historical_output(root: Path, oracle) -> None:
    for relative in oracle.HISTORICAL_OUTPUTS:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"historical-output")


@pytest.mark.parametrize("location", ["unexpected-empty-dir", "previews/unexpected-empty-subdir"])
def test_oracle_inventory_rejects_unexpected_empty_directories(tmp_path, location):
    oracle = _oracle_module()
    _historical_output(tmp_path, oracle)
    (tmp_path / location).mkdir()
    with pytest.raises(RuntimeError, match="Inventaire historique inattendu"):
        oracle._inventory(tmp_path)


@pytest.mark.parametrize("kind", ["hidden", "symlink", "fifo"])
def test_oracle_inventory_rejects_hidden_links_and_special_entries(tmp_path, kind):
    oracle = _oracle_module()
    _historical_output(tmp_path, oracle)
    if kind == "hidden":
        (tmp_path / ".unexpected").write_bytes(b"hidden")
    elif kind == "symlink":
        (tmp_path / "unexpected-link").symlink_to(tmp_path / "interior.pdf")
    else:
        if not hasattr(os, "mkfifo"):
            pytest.skip("mkfifo unavailable")
        os.mkfifo(tmp_path / "unexpected-pipe")
    with pytest.raises(RuntimeError):
        oracle._inventory(tmp_path)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], text=True,
                            capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _candidate_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "candidate"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "oracle@example.invalid")
    _git(repo, "config", "user.name", "Oracle Test")
    (repo / "pyproject.toml").write_text("[project]\nname='candidate'\nversion='0'\n", encoding="utf-8")
    package = repo / "src/lafractale"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("VALUE = 'baseline'\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "baseline")
    return repo


def test_candidate_snapshot_freezes_tracked_and_untracked_content(tmp_path):
    oracle = _oracle_module()
    repo = _candidate_repo(tmp_path)
    package = repo / "src/lafractale"
    (package / "__init__.py").write_text("VALUE = 'captured'\n", encoding="utf-8")
    (package / "new_module.py").write_text("VALUE = 'untracked'\n", encoding="utf-8")
    with oracle._candidate_snapshot(repo) as snapshot:
        assert snapshot.tree != _git(repo, "rev-parse", "HEAD^{tree}")
        assert snapshot.inventory["src/lafractale/new_module.py"]
        (package / "__init__.py").write_text("VALUE = 'after-capture'\n", encoding="utf-8")
        assert (snapshot.root / "src/lafractale/__init__.py").read_text(encoding="utf-8") == "VALUE = 'captured'\n"
        assert (snapshot.root / "src/lafractale/new_module.py").read_text(encoding="utf-8") == "VALUE = 'untracked'\n"


def test_oracle_refuses_candidate_with_same_python_source_tree_as_reference(tmp_path):
    oracle = _oracle_module()
    repo = _candidate_repo(tmp_path)
    baseline = _git(repo, "rev-parse", "HEAD")
    with pytest.raises(RuntimeError, match="même code Python"):
        oracle.main([
            "--candidate-repo", str(repo),
            "--reference-commit", baseline,
            "--approvals-sha256", PIN,
            "--proof", str(tmp_path / "same-code-proof.json"),
        ])


def test_oracle_refuses_marker_only_tree_change_when_python_source_is_identical(tmp_path):
    oracle = _oracle_module()
    repo = _candidate_repo(tmp_path)
    baseline = _git(repo, "rev-parse", "HEAD")
    (repo / "src/lafractale/NON_PYTHON_MARKER.txt").write_text("marker\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "marker only")
    with pytest.raises(RuntimeError, match="même code Python"):
        oracle.main([
            "--candidate-repo", str(repo),
            "--reference-commit", baseline,
            "--require-head-tree",
            "--approvals-sha256", PIN,
            "--proof", str(tmp_path / "marker-only-proof.json"),
        ])


def test_oracle_require_head_tree_rejects_uncommitted_candidate_snapshot(tmp_path):
    oracle = _oracle_module()
    repo = _candidate_repo(tmp_path)
    baseline = _git(repo, "rev-parse", "HEAD")
    (repo / "src/lafractale/__init__.py").write_text("VALUE = 'dirty'\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="diffère de HEAD"):
        oracle.main([
            "--candidate-repo", str(repo),
            "--reference-commit", baseline,
            "--require-head-tree",
            "--approvals-sha256", PIN,
            "--proof", str(tmp_path / "dirty-proof.json"),
        ])


def test_oracle_proof_becomes_inapplicable_after_candidate_tree_changes(tmp_path):
    oracle = _oracle_module()
    repo = _candidate_repo(tmp_path)
    proof = tmp_path / "proof.json"
    with oracle._candidate_snapshot(repo) as snapshot:
        proof.write_text(json.dumps({
            "candidate_tree": snapshot.tree,
            "candidate_snapshot_inventory": snapshot.inventory,
        }), encoding="utf-8")
    (repo / "src/lafractale/__init__.py").write_text("VALUE = 'changed'\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="plus applicable"):
        oracle._verify_proof_candidate(repo, proof)
