#!/usr/bin/env python3
"""Prove the B2-C4 editorial mode is deterministic and traceable.

Fourth oracle, per the B2-C4 contract §6: before any canonical reference can be
pinned (which requires human editorial validation), this oracle demonstrates
DETERMINISM, ISOLATION and TRACEABILITY of the opt-in `halloween-editorial-v1`
profile on the exact candidate tree.

- DETERMINISM: the editorial build is executed in two independent checkouts of
  the same immutable candidate tree and the closed inventories must be
  byte-identical.
- ISOLATION: the editorial mode requires the C1 route and C2 placement context;
  it never activates implicitly and does not touch the historical modes.
- TRACEABILITY: the proof records the candidate tree, editorial profile, the
  external registry PIN, pinned fonts, seed, SOURCE_DATE_EPOCH and the full
  closed inventory, so a canonical C4 reference can later be pinned.

A comparison between two builds of the same tree proves only determinism — it is
never presented as non-regression.  Historical non-regression stays the job of
the B2-B / B2-C1 / B2-C2 oracles.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_b2b_oracle import (  # noqa: E402  (proven B2-B helpers, unmodified)
    _candidate_snapshot,
    _font_hashes,
    _required,
    _run,
    _runtime_environment,
    _verify_proof_candidate,
    _write_proof,
)
from verify_b2c2_oracle import _placed_inventory  # noqa: E402  (proven closed-tree helper)

SOURCE_DATE_EPOCH = "1780000000"
SEED = "2026"
BOOK = "books/halloween_2026/book.yaml"
ROUTING_POLICY = "halloween-pip-demo-v1"
PLACEMENT_POLICY = "halloween-pip-placement-v2"
EDITORIAL_PROFILE = "halloween-editorial-v1"


def _editorial_case(*, source: Path, output: Path, python: str, env: dict[str, str],
                    pin: str) -> dict[str, object]:
    """Build and QA the editorial (C1 routed + C2 placed + C4) mode."""
    output.parent.mkdir(parents=True, exist_ok=True)
    options = [
        "--illustration-routing", ROUTING_POLICY,
        "--pip-placement", PLACEMENT_POLICY,
        "--editorial-profile", EDITORIAL_PROFILE,
        "--approvals-sha256", pin,
    ]
    build = [python, "-m", "lafractale", "build-demo", BOOK, "--out", str(output),
             "--seed", SEED, *options]
    qa = [python, "-m", "lafractale", "qa", str(output), "--book", BOOK, *options]
    build_result = _run(build, cwd=source, env=env)
    _required(build_result, "Build éditorial C4")
    qa_result = _run(qa, cwd=source, env=env)
    _required(qa_result, "QA éditorial C4")
    return {
        "build": asdict(build_result),
        "qa": asdict(qa_result),
        "build_returncode": build_result.returncode,
        "qa_returncode": qa_result.returncode,
        "inventory": _placed_inventory(output),
    }


@contextmanager
def _tree_checkout(candidate: Path, tree: str):
    """Materialize the immutable candidate tree into an independent directory."""
    with tempfile.TemporaryDirectory(prefix="lafractale-b2c4-oracle-") as temporary:
        checkout = Path(temporary) / "tree"
        checkout.mkdir()
        proc = subprocess.run(
            ["git", "-C", str(candidate), "archive", "--format=tar", tree],
            stdout=subprocess.PIPE, check=True,
        )
        with tarfile.open(fileobj=io.BytesIO(proc.stdout)) as archive:
            archive.extractall(checkout)
        yield checkout.resolve()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-repo", type=Path, required=True)
    parser.add_argument("--approvals-sha256")
    parser.add_argument("--proof", type=Path)
    parser.add_argument("--verify-proof", type=Path,
                        help="Refuser une preuve dont le tree candidat n'est plus actuel")
    parser.add_argument("--require-head-tree", action="store_true",
                        help="Refuser un candidat dont le snapshot diffère du tree de HEAD")
    args = parser.parse_args(argv)

    candidate = args.candidate_repo.resolve()
    if not (candidate / "pyproject.toml").is_file():
        raise RuntimeError("Checkout candidat invalide")
    if args.verify_proof is not None:
        if any(value is not None for value in (args.approvals_sha256, args.proof)):
            raise RuntimeError("--verify-proof est exclusif des options de génération")
        _verify_proof_candidate(candidate, args.verify_proof.resolve())
        print(f"B2C4_ORACLE_PROOF_APPLICABLE {args.verify_proof.resolve()}")
        return 0
    if not args.approvals_sha256 or args.proof is None:
        raise RuntimeError("--approvals-sha256 et --proof sont obligatoires")
    external_pin = args.approvals_sha256
    if len(external_pin) != 64 or any(char not in "0123456789abcdef" for char in external_pin):
        raise RuntimeError("Empreinte externe de registre invalide")

    base_env = os.environ.copy()
    base_env.pop("PYTHONHOME", None)
    base_env.pop("PYTHONPATH", None)
    base_env["PYTHONDONTWRITEBYTECODE"] = "1"
    base_env["SOURCE_DATE_EPOCH"] = SOURCE_DATE_EPOCH
    fonts = _font_hashes(base_env)
    python = sys.executable

    with _candidate_snapshot(candidate) as snapshot:
        if args.require_head_tree and snapshot.tree != snapshot.head_tree:
            raise RuntimeError(
                "Preuve oracle refusée : le tree candidat diffère de HEAD ; "
                "committer le snapshot ou régénérer la preuve sur le commit soumis"
            )
        with tempfile.TemporaryDirectory(prefix="lafractale-b2c4-run-") as temporary:
            with _tree_checkout(candidate, snapshot.tree) as detached:
                first_env = base_env.copy()
                first_env["PYTHONPATH"] = str((snapshot.root / "src").resolve())
                second_env = base_env.copy()
                second_env["PYTHONPATH"] = str((detached / "src").resolve())
                first_runtime = _runtime_environment(python, source=snapshot.root, env=first_env)
                second_runtime = _runtime_environment(python, source=detached, env=second_env)
                if first_runtime["lafractale"] == second_runtime["lafractale"]:
                    raise RuntimeError("Les deux processus importent le même checkout")

                first_case = _editorial_case(
                    source=snapshot.root, output=Path(temporary) / "first" / "editorial",
                    python=python, env=first_env, pin=external_pin,
                )
                second_case = _editorial_case(
                    source=detached, output=Path(temporary) / "second" / "editorial",
                    python=python, env=second_env, pin=external_pin,
                )
                identical = first_case["inventory"] == second_case["inventory"]
                proof: dict[str, object] = {
                    "oracle": "b2c4-editorial-v1-determinism",
                    "editorial_profile": EDITORIAL_PROFILE,
                    "routing_policy": ROUTING_POLICY,
                    "placement_policy": PLACEMENT_POLICY,
                    "candidate_head": snapshot.head,
                    "candidate_head_tree": snapshot.head_tree,
                    "candidate_tree": snapshot.tree,
                    "candidate_tree_matches_head": snapshot.tree == snapshot.head_tree,
                    "candidate_initial_status": snapshot.status,
                    "candidate_initial_status_sha256": snapshot.status_sha256,
                    "candidate_snapshot_inventory": snapshot.inventory,
                    "python": python,
                    "source_date_epoch": SOURCE_DATE_EPOCH,
                    "seed": int(SEED),
                    "fonts": fonts,
                    "first_runtime": first_runtime,
                    "second_runtime": second_runtime,
                    "cases": [{
                        "mode": "editorial-v1",
                        "first_qa": first_case["qa_returncode"],
                        "second_qa": second_case["qa_returncode"],
                        "first_build": first_case["build_returncode"],
                        "second_build": second_case["build_returncode"],
                        "first_inventory": first_case["inventory"],
                        "second_inventory": second_case["inventory"],
                        "identical": identical,
                    }],
                    "note": ("Déterminisme uniquement : aucune référence canonique C4 "
                             "n'est épinglée avant validation éditoriale humaine."),
                }
                _write_proof(args.proof.resolve(), proof)
                if not identical:
                    raise RuntimeError(
                        "Non-déterminisme B2-C4 : la sortie éditoriale diffère entre deux checkouts"
                    )
    print(f"B2C4_ORACLE_OK {args.proof.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
