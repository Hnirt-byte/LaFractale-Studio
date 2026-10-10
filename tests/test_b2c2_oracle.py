"""Independent B2-C1 byte-regression oracle required before C2 placement ships.

The reference is the merged B2-C1 commit: the routed mode without the *new*
placement option must stay byte-identical, so the C2 opt-in cannot silently
change the C1 pipeline.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
BASE = "8a28fb824a2ef895f1cf22913bc231b3d1dd0826"
PIN = "93c58e86a74e903af1be5cd4257d489c39bece8f5cd41d985586cbf775d45e61"


def test_routed_mode_stays_byte_identical_to_the_merged_b2c1_commit(tmp_path):
    proof = tmp_path / "b2c1-oracle-proof.json"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "verify_b2c1_oracle.py"),
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
    assert "B2C1_ORACLE_OK" in result.stdout
    payload = json.loads(proof.read_text(encoding="utf-8"))
    assert payload["reference_commit"] == BASE
    assert isinstance(payload["candidate_head"], str) and len(payload["candidate_head"]) == 40
    assert isinstance(payload["candidate_tree"], str) and len(payload["candidate_tree"]) == 40
    assert isinstance(payload["candidate_snapshot_inventory"], dict)
    assert payload["reference_source"] != payload["candidate_source"]
    assert payload["reference_python_source_files"] != payload["candidate_python_source_files"]
    assert [case["mode"] for case in payload["cases"]] == ["routed"]
    assert all(case["identical"] is True for case in payload["cases"])
    assert all(case["reference_qa"] == 0 and case["candidate_qa"] == 0 for case in payload["cases"])
    assert all(case["reference_build"] == 0 and case["candidate_build"] == 0
               for case in payload["cases"])
    assert len(payload["candidate_python_source_files"]) > 5


def _oracle_module():
    path = ROOT / "tools" / "verify_b2c1_oracle.py"
    spec = importlib.util.spec_from_file_location("b2c1_oracle_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _routed_output(root: Path, oracle) -> None:
    for relative in oracle.ROUTED_OUTPUTS:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"routed-output")


@pytest.mark.parametrize("location", ["unexpected-empty-dir", "previews/unexpected-empty-subdir"])
def test_routed_inventory_rejects_unexpected_empty_directories(tmp_path, location):
    oracle = _oracle_module()
    _routed_output(tmp_path, oracle)
    (tmp_path / location).mkdir()
    with pytest.raises(RuntimeError, match="Inventaire historique inattendu"):
        oracle._routed_inventory(tmp_path)


@pytest.mark.parametrize("kind", ["hidden", "symlink", "fifo"])
def test_routed_inventory_rejects_hidden_links_and_special_entries(tmp_path, kind):
    oracle = _oracle_module()
    _routed_output(tmp_path, oracle)
    if kind == "hidden":
        (tmp_path / ".unexpected").write_bytes(b"hidden")
    elif kind == "symlink":
        (tmp_path / "unexpected-link").symlink_to(tmp_path / "interior.pdf")
    else:
        if not hasattr(os, "mkfifo"):
            pytest.skip("mkfifo unavailable")
        os.mkfifo(tmp_path / "unexpected-pipe")
    with pytest.raises(RuntimeError):
        oracle._routed_inventory(tmp_path)


def test_routed_inventory_rejects_a_missing_preview(tmp_path):
    oracle = _oracle_module()
    _routed_output(tmp_path, oracle)
    (tmp_path / "previews/interior_page_02.png").unlink()
    with pytest.raises(RuntimeError):
        oracle._routed_inventory(tmp_path)


def test_routed_inventory_rejects_an_extra_file(tmp_path):
    oracle = _oracle_module()
    _routed_output(tmp_path, oracle)
    (tmp_path / "previews/interior_page_04.png").write_bytes(b"extra")
    with pytest.raises(RuntimeError):
        oracle._routed_inventory(tmp_path)


def test_routed_case_requires_an_explicit_placement_free_call(tmp_path):
    """The oracle must never pass --pip-placement, or the proof is vacuous."""
    source = (ROOT / "tools" / "verify_b2c1_oracle.py").read_text(encoding="utf-8")
    code = source.split('"""', 2)[2]
    assert "--pip-placement" not in code
    assert "--illustration-routing" in code


def test_oracle_refuses_require_head_tree_on_a_dirty_candidate(tmp_path):
    oracle = _oracle_module()
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "verify_b2c1_oracle.py"),
            "--candidate-repo", str(ROOT),
            "--reference-commit", BASE,
            "--require-head-tree",
            "--approvals-sha256", PIN,
            "--proof", str(tmp_path / "dirty.json"),
            "--unreachable",
        ],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    assert result.returncode != 0
    assert oracle.DEFAULT_REFERENCE_TREE
