"""Independent B2-B byte-regression oracle required before C1 routing."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


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
    assert isinstance(payload["candidate_commit"], str) and len(payload["candidate_commit"]) == 40
    assert payload["reference_source"] != payload["candidate_source"]
    assert [case["mode"] for case in payload["cases"]] == ["placeholder", "legacy_illustration"]
    assert all(case["identical"] is True for case in payload["cases"])
    assert all(case["reference_qa"] == 0 and case["candidate_qa"] == 0 for case in payload["cases"])
