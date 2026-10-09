#!/usr/bin/env python3
"""Prove B2-B historical modes are byte-identical to an isolated Git reference.

This verifier intentionally runs the reference and candidate from distinct source
roots in independent Python processes.  It is a release gate for B2-C1, not an
approval authority: the external approval-registry SHA is still supplied by the
operator and passed unchanged to both engines.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Iterable, cast


SOURCE_DATE_EPOCH = "1780000000"
SEED = "2026"
BOOK = "books/halloween_2026/book.yaml"
HISTORICAL_OUTPUTS = frozenset({
    "interior.pdf", "answer_key.pdf", "activities.json", "quality_report.json",
    "quality_report.md", "manifest.json", "previews/page_01.png",
    "previews/page_02.png", "previews/page_03.png",
})


@dataclass(frozen=True)
class CommandResult:
    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


def _run(argv: Iterable[str], *, cwd: Path, env: dict[str, str]) -> CommandResult:
    completed = subprocess.run(
        list(argv), cwd=cwd, env=env, text=True, capture_output=True, check=False,
    )
    return CommandResult(tuple(str(item) for item in argv), completed.returncode,
                         completed.stdout, completed.stderr)


def _required(result: CommandResult, label: str) -> None:
    if result.returncode != 0:
        raise RuntimeError(
            f"{label} a échoué (rc={result.returncode})\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(["git", "-C", str(repo), *args], text=True,
                               capture_output=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {completed.stderr.strip()}")
    return completed.stdout.strip()


def _sha(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _font_hashes(env: dict[str, str]) -> dict[str, dict[str, str]]:
    defaults = {
        "regular": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "bold": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    }
    requested = {
        "regular": Path(env.get("LAFRACTALE_FONT_PATH", defaults["regular"])),
        "bold": Path(env.get("LAFRACTALE_FONT_BOLD_PATH", defaults["bold"])),
    }
    result: dict[str, dict[str, str]] = {}
    for name, path in requested.items():
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"Police requise absente ou non régulière : {path}")
        result[name] = {"path": str(path.resolve()), "sha256": _sha(path)}
    env["LAFRACTALE_FONT_PATH"] = result["regular"]["path"]
    env["LAFRACTALE_FONT_BOLD_PATH"] = result["bold"]["path"]
    return result


def _runtime_environment(python: str, *, source: Path, env: dict[str, str]) -> dict[str, str]:
    command = (
        "import json, lafractale, pymupdf, reportlab, PIL, yaml; "
        "print(json.dumps({'lafractale': lafractale.__file__, 'pymupdf': pymupdf.__version__, "
        "'reportlab': reportlab.Version, 'pillow': PIL.__version__, "
        "'pyyaml': yaml.__version__}, sort_keys=True))"
    )
    result = _run([python, "-c", command], cwd=source, env=env)
    _required(result, "Contrôle d'environnement Python")
    data = json.loads(result.stdout)
    module_path = Path(data["lafractale"]).resolve()
    source_root = (source / "src").resolve()
    try:
        module_path.relative_to(source_root)
    except ValueError as exc:
        raise RuntimeError(f"Import contaminé hors checkout attendu : {module_path}") from exc
    return {key: str(value) for key, value in data.items()}


def _inventory(output: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for path in output.rglob("*"):
        relative = path.relative_to(output).as_posix()
        if path.is_symlink():
            raise RuntimeError(f"Sortie non régulière dans oracle : {relative}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise RuntimeError(f"Sortie non régulière dans oracle : {relative}")
        entries[relative] = _sha(path)
    if frozenset(entries) != HISTORICAL_OUTPUTS:
        raise RuntimeError(
            "Inventaire historique inattendu : "
            f"attendu={sorted(HISTORICAL_OUTPUTS)} obtenu={sorted(entries)}"
        )
    return dict(sorted(entries.items()))


def _mode_case(*, name: str, source: Path, output: Path, python: str,
               env: dict[str, str], pin: str) -> dict[str, object]:
    output.parent.mkdir(parents=True, exist_ok=True)
    build = [python, "-m", "lafractale", "build-demo", BOOK, "--out", str(output), "--seed", SEED]
    qa = [python, "-m", "lafractale", "qa", str(output), "--book", BOOK]
    if name == "legacy_illustration":
        options = ["--illustration-id", "pip-reflexion-v2", "--approvals-sha256", pin]
        build.extend(options)
        qa.extend(options)
    elif name != "placeholder":
        raise ValueError(f"Mode historique inconnu : {name}")
    build_result = _run(build, cwd=source, env=env)
    _required(build_result, f"Build {name}")
    qa_result = _run(qa, cwd=source, env=env)
    _required(qa_result, f"QA {name}")
    return {
        "build": asdict(build_result),
        "qa": asdict(qa_result),
        "inventory": _inventory(output),
    }


def _write_proof(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-repo", type=Path, required=True)
    parser.add_argument("--reference-commit", required=True)
    parser.add_argument("--approvals-sha256", required=True)
    parser.add_argument("--proof", type=Path, required=True)
    args = parser.parse_args(argv)

    candidate = args.candidate_repo.resolve()
    if not (candidate / "pyproject.toml").is_file():
        raise RuntimeError("Checkout candidat invalide")
    candidate_commit = _git(candidate, "rev-parse", "HEAD")
    _git(candidate, "cat-file", "-e", f"{args.reference_commit}^{{commit}}")
    external_pin = args.approvals_sha256
    if len(external_pin) != 64 or any(char not in "0123456789abcdef" for char in external_pin):
        raise RuntimeError("Empreinte externe de registre invalide")

    base_env = os.environ.copy()
    base_env.pop("PYTHONHOME", None)
    base_env["SOURCE_DATE_EPOCH"] = SOURCE_DATE_EPOCH
    fonts = _font_hashes(base_env)
    python = sys.executable

    with tempfile.TemporaryDirectory(prefix="lafractale-b2b-oracle-") as temporary:
        worktree = Path(temporary) / "reference"
        try:
            _git(candidate, "worktree", "add", "--detach", str(worktree), args.reference_commit)
            reference = worktree.resolve()
            candidate_env = base_env.copy()
            candidate_env["PYTHONPATH"] = str((candidate / "src").resolve())
            reference_env = base_env.copy()
            reference_env["PYTHONPATH"] = str((reference / "src").resolve())
            candidate_runtime = _runtime_environment(python, source=candidate, env=candidate_env)
            reference_runtime = _runtime_environment(python, source=reference, env=reference_env)
            if candidate_runtime["lafractale"] == reference_runtime["lafractale"]:
                raise RuntimeError("Les deux processus importent le même checkout")

            cases: list[dict[str, object]] = []
            for mode in ("placeholder", "legacy_illustration"):
                reference_case = _mode_case(
                    name=mode, source=reference, output=Path(temporary) / "reference-out" / mode,
                    python=python, env=reference_env, pin=external_pin,
                )
                candidate_case = _mode_case(
                    name=mode, source=candidate, output=Path(temporary) / "candidate-out" / mode,
                    python=python, env=candidate_env, pin=external_pin,
                )
                identical = reference_case["inventory"] == candidate_case["inventory"]
                reference_qa = cast(dict[str, object], reference_case["qa"])
                candidate_qa = cast(dict[str, object], candidate_case["qa"])
                cases.append({
                    "mode": mode,
                    "reference_qa": reference_qa["returncode"],
                    "candidate_qa": candidate_qa["returncode"],
                    "reference_inventory": reference_case["inventory"],
                    "candidate_inventory": candidate_case["inventory"],
                    "identical": identical,
                })
            proof: dict[str, object] = {
                "reference_commit": args.reference_commit,
                "candidate_commit": candidate_commit,
                "reference_source": reference_runtime["lafractale"],
                "candidate_source": candidate_runtime["lafractale"],
                "python": python,
                "source_date_epoch": SOURCE_DATE_EPOCH,
                "seed": int(SEED),
                "fonts": fonts,
                "reference_runtime": reference_runtime,
                "candidate_runtime": candidate_runtime,
                "cases": cases,
            }
            _write_proof(args.proof.resolve(), proof)
            if not all(case["identical"] for case in cases):
                raise RuntimeError("Régression B2-B : sorties historiques différentes de l'oracle isolé")
        finally:
            if worktree.exists():
                subprocess.run(["git", "-C", str(candidate), "worktree", "remove", "--force", str(worktree)],
                               text=True, capture_output=True, check=False)
    print(f"B2B_ORACLE_OK {args.proof.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
