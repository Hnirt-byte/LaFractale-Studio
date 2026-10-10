#!/usr/bin/env python3
"""Prove the B2-C2 V2 placed mode is byte-identical to an isolated Git reference.

Third non-regression oracle: the placed Halloween mode
(`--pip-placement halloween-pip-placement-v2`) must keep producing exactly the
merged B2-C2 output even as the engine evolves (B2-C3 read-only preflight,
B2-C4 opt-in editorial profile).  The guarantee is byte-identity of the
historical placed-V2 output, rebuilt independently from the reference tree.
Python source identity is recorded for traceability but no longer enforced:
the engine may change behind the opt-in editorial profile.

The candidate is captured as an immutable Git tree built through a private
index; the reference is a detached worktree of the B2-C2 merge commit.  Both
engines run in distinct Python processes with pinned fonts, dependencies, seed
and SOURCE_DATE_EPOCH.  A comparison between two candidate builds proves only
determinism, never non-regression.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_b2b_oracle import (  # noqa: E402  (proven B2-B helpers, unmodified)
    CommandResult,
    _candidate_snapshot,
    _closed_entries,
    _directory_flags,
    _font_hashes,
    _git,
    _open_anchored_directory,
    _python_source_blobs,
    _regular_hash,
    _required,
    _run,
    _runtime_environment,
    _sha_bytes,
    _verify_proof_candidate,
    _write_proof,
)

SOURCE_DATE_EPOCH = "1780000000"
SEED = "2026"
BOOK = "books/halloween_2026/book.yaml"
ROUTING_POLICY = "halloween-pip-demo-v1"
PLACEMENT_POLICY = "halloween-pip-placement-v2"
DEFAULT_REFERENCE_TREE = "07d8a5fabd9181d4f84e51fe6a472446b70df0a7"

PLACED_ROOT = frozenset({
    "interior.pdf", "answer_key.pdf", "activities.json", "quality_report.json",
    "quality_report.md", "manifest.json", "previews",
})
PLACED_PREVIEWS = frozenset({
    "interior_page_01.png", "interior_page_02.png", "interior_page_03.png",
    "answer_key_page_01.png", "answer_key_page_02.png", "answer_key_page_03.png",
})
PLACED_OUTPUTS = frozenset(
    {name for name in PLACED_ROOT if name != "previews"}
    | {f"previews/{name}" for name in PLACED_PREVIEWS}
)


def _placed_inventory(output: Path) -> dict[str, str]:
    """Hash the exact closed placed output tree through anchored descriptors."""
    root_fd = _open_anchored_directory(output)
    try:
        root_entries = _closed_entries(root_fd, expected=PLACED_ROOT, location="racine")
        for name, mode in root_entries.items():
            if name == "previews":
                if not stat.S_ISDIR(mode):
                    raise RuntimeError("Sortie non régulière dans oracle : previews")
            elif not stat.S_ISREG(mode):
                raise RuntimeError(f"Sortie non régulière dans oracle : {name}")
        previews_fd = os.open("previews", _directory_flags(), dir_fd=root_fd)
        try:
            preview_entries = _closed_entries(
                previews_fd, expected=PLACED_PREVIEWS, location="previews/",
            )
            if any(not stat.S_ISREG(mode) for mode in preview_entries.values()):
                raise RuntimeError("Sortie non régulière dans oracle : previews/")
            entries = {
                name: _regular_hash(root_fd, name, location="")
                for name in PLACED_ROOT - {"previews"}
            }
            entries.update({
                f"previews/{name}": _regular_hash(previews_fd, name, location="previews/")
                for name in PLACED_PREVIEWS
            })
        finally:
            os.close(previews_fd)
    finally:
        os.close(root_fd)
    if frozenset(entries) != PLACED_OUTPUTS:
        raise RuntimeError("Inventaire placé interne incohérent")
    return dict(sorted(entries.items()))


def _placed_case(*, source: Path, output: Path, python: str, env: dict[str, str],
                 pin: str) -> dict[str, object]:
    """Build and QA the placed V2 mode."""
    output.parent.mkdir(parents=True, exist_ok=True)
    options = [
        "--illustration-routing", ROUTING_POLICY,
        "--pip-placement", PLACEMENT_POLICY,
        "--approvals-sha256", pin,
    ]
    build = [python, "-m", "lafractale", "build-demo", BOOK, "--out", str(output),
             "--seed", SEED, *options]
    qa = [python, "-m", "lafractale", "qa", str(output), "--book", BOOK, *options]
    build_result = _run(build, cwd=source, env=env)
    _required(build_result, "Build placé V2")
    qa_result = _run(qa, cwd=source, env=env)
    _required(qa_result, "QA placé V2")
    return {
        "build": asdict(build_result),
        "qa": asdict(qa_result),
        "build_returncode": build_result.returncode,
        "qa_returncode": qa_result.returncode,
        "inventory": _placed_inventory(output),
    }


@contextmanager
def _reference_worktree(candidate: Path, commit: str):
    with tempfile.TemporaryDirectory(prefix="lafractale-b2c2-oracle-") as temporary:
        worktree = Path(temporary) / "reference"
        try:
            _git(candidate, "worktree", "add", "--detach", str(worktree), commit)
            yield worktree.resolve()
        finally:
            if worktree.exists():
                subprocess.run(
                    ["git", "-C", str(candidate), "worktree", "remove", "--force", str(worktree)],
                    text=True, capture_output=True, check=False,
                )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-repo", type=Path, required=True)
    parser.add_argument("--reference-commit")
    parser.add_argument("--expected-reference-tree", default=DEFAULT_REFERENCE_TREE)
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
        if any(value is not None for value in (args.reference_commit, args.approvals_sha256, args.proof)):
            raise RuntimeError("--verify-proof est exclusif des options de génération")
        _verify_proof_candidate(candidate, args.verify_proof.resolve())
        print(f"B2C2_ORACLE_PROOF_APPLICABLE {args.verify_proof.resolve()}")
        return 0
    if not args.reference_commit or not args.approvals_sha256 or args.proof is None:
        raise RuntimeError("--reference-commit, --approvals-sha256 et --proof sont obligatoires")
    _git(candidate, "cat-file", "-e", f"{args.reference_commit}^{{commit}}")
    reference_tree = _git(candidate, "rev-parse", f"{args.reference_commit}^{{tree}}")
    if reference_tree != args.expected_reference_tree:
        raise RuntimeError(
            "Arbre de référence inattendu : "
            f"{reference_tree} != {args.expected_reference_tree}"
        )
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
        candidate_python_files = _python_source_blobs(candidate, snapshot.tree)
        reference_python_files = _python_source_blobs(candidate, args.reference_commit)
        # B2-C4: the engine may evolve behind the opt-in editorial profile, so
        # Python source identity is recorded for traceability only, not enforced.
        # The real non-regression guarantee is the byte-identity of the
        # historical placed-V2 output below, rebuilt from the reference tree.
        with tempfile.TemporaryDirectory(prefix="lafractale-b2c2-run-") as temporary:
            with _reference_worktree(candidate, args.reference_commit) as reference:
                candidate_env = base_env.copy()
                candidate_env["PYTHONPATH"] = str((snapshot.root / "src").resolve())
                reference_env = base_env.copy()
                reference_env["PYTHONPATH"] = str((reference / "src").resolve())
                candidate_runtime = _runtime_environment(python, source=snapshot.root, env=candidate_env)
                reference_runtime = _runtime_environment(python, source=reference, env=reference_env)
                if candidate_runtime["lafractale"] == reference_runtime["lafractale"]:
                    raise RuntimeError("Les deux processus importent le même checkout")

                reference_case = _placed_case(
                    source=reference, output=Path(temporary) / "reference-out" / "placed",
                    python=python, env=reference_env, pin=external_pin,
                )
                candidate_case = _placed_case(
                    source=snapshot.root, output=Path(temporary) / "candidate-out" / "placed",
                    python=python, env=candidate_env, pin=external_pin,
                )
                identical = reference_case["inventory"] == candidate_case["inventory"]
                proof: dict[str, object] = {
                    "oracle": "b2c2-placed-v2",
                    "reference_commit": args.reference_commit,
                    "reference_tree": reference_tree,
                    "routing_policy": ROUTING_POLICY,
                    "placement_policy": PLACEMENT_POLICY,
                    "candidate_head": snapshot.head,
                    "candidate_head_tree": snapshot.head_tree,
                    "candidate_tree": snapshot.tree,
                    "candidate_tree_matches_head": snapshot.tree == snapshot.head_tree,
                    "candidate_initial_status": snapshot.status,
                    "candidate_initial_status_sha256": snapshot.status_sha256,
                    "candidate_snapshot_inventory": snapshot.inventory,
                    "candidate_python_source_files": candidate_python_files,
                    "candidate_python_source_sha256": _sha_bytes(json.dumps(
                        candidate_python_files, sort_keys=True, separators=(",", ":")).encode("utf-8")),
                    "reference_python_source_files": reference_python_files,
                    "reference_source": reference_runtime["lafractale"],
                    "candidate_source": candidate_runtime["lafractale"],
                    "python": python,
                    "source_date_epoch": SOURCE_DATE_EPOCH,
                    "seed": int(SEED),
                    "fonts": fonts,
                    "reference_runtime": reference_runtime,
                    "candidate_runtime": candidate_runtime,
                    "cases": [{
                        "mode": "placed-v2",
                        "reference_qa": reference_case["qa_returncode"],
                        "candidate_qa": candidate_case["qa_returncode"],
                        "reference_build": reference_case["build_returncode"],
                        "candidate_build": candidate_case["build_returncode"],
                        "reference_inventory": reference_case["inventory"],
                        "candidate_inventory": candidate_case["inventory"],
                        "identical": identical,
                    }],
                }
                _write_proof(args.proof.resolve(), proof)
                if not identical:
                    raise RuntimeError(
                        "Régression B2-C2 : la sortie placée V2 diffère de l'oracle isolé"
                    )
    print(f"B2C2_ORACLE_OK {args.proof.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
