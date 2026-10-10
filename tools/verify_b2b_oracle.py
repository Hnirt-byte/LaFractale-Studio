#!/usr/bin/env python3
"""Prove B2-B historical modes are byte-identical to an isolated Git reference.

The candidate is first captured as an immutable Git tree built through a private
index.  Both engines then run from distinct, isolated source roots.  This is a
release gate for B2-C1, not an approval authority: the external approval-registry
SHA is still supplied by the operator and passed unchanged to both engines.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import tarfile
import tempfile
from typing import Iterable, Iterator, cast


SOURCE_DATE_EPOCH = "1780000000"
SEED = "2026"
BOOK = "books/halloween_2026/book.yaml"
HISTORICAL_ROOT = frozenset({
    "interior.pdf", "answer_key.pdf", "activities.json", "quality_report.json",
    "quality_report.md", "manifest.json", "previews",
})
HISTORICAL_PREVIEWS = frozenset({"page_01.png", "page_02.png", "page_03.png"})
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


@dataclass(frozen=True)
class CandidateSnapshot:
    head: str
    head_tree: str
    tree: str
    status: str
    status_sha256: str
    inventory: dict[str, str]
    root: Path


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


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(["git", "-C", str(repo), *args], text=True,
                               capture_output=True, check=False, env=env)
    if completed.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {completed.stderr.strip()}")
    return completed.stdout.strip()


def _git_bytes(repo: Path, *args: str, env: dict[str, str] | None = None) -> bytes:
    completed = subprocess.run(["git", "-C", str(repo), *args], stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, check=False, env=env)
    if completed.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {completed.stderr.decode(errors='replace').strip()}")
    return completed.stdout


def _sha(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


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


def _directory_flags() -> int:
    if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
        raise RuntimeError("O_DIRECTORY/O_NOFOLLOW obligatoires pour l'oracle")
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)


def _open_anchored_directory(path: Path) -> int:
    """Open every path component from / through descriptor-relative nofollow opens."""
    raw = os.fspath(path)
    if not raw or "\x00" in raw or ".." in Path(raw).parts:
        raise RuntimeError("Inventaire historique : chemin de sortie invalide")
    absolute = Path(os.path.abspath(raw))
    flags = _directory_flags()
    fd = os.open("/", flags)
    try:
        for component in absolute.parts[1:]:
            next_fd = os.open(component, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except Exception:
        os.close(fd)
        raise


def _directory_entries(fd: int, *, location: str) -> dict[str, int]:
    with os.scandir(fd) as scan:
        entries = {entry.name: entry.stat(follow_symlinks=False).st_mode for entry in scan}
    if any("/" in name or name in {"", ".", ".."} for name in entries):
        raise RuntimeError(f"Inventaire historique invalide dans {location}")
    return entries


def _closed_entries(fd: int, *, expected: frozenset[str], location: str) -> dict[str, int]:
    entries = _directory_entries(fd, location=location)
    names = frozenset(entries)
    if names != expected:
        missing = sorted(expected - names)
        extra = sorted(names - expected)
        raise RuntimeError(
            f"Inventaire historique inattendu dans {location} : "
            f"manquants={missing} supplémentaires={extra}"
        )
    return entries


def _regular_hash(directory_fd: int, name: str, *, location: str) -> str:
    flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(name, flags, dir_fd=directory_fd)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise RuntimeError(f"Sortie non régulière dans oracle : {location}{name}")
        digest = sha256()
        with os.fdopen(descriptor, "rb") as source:
            descriptor = -1
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _inventory(output: Path) -> dict[str, str]:
    """Hash only the exact closed B2-B output tree through anchored descriptors."""
    root_fd = _open_anchored_directory(output)
    try:
        root_entries = _closed_entries(root_fd, expected=HISTORICAL_ROOT, location="racine")
        for name, mode in root_entries.items():
            if name == "previews":
                if not stat.S_ISDIR(mode):
                    raise RuntimeError("Sortie non régulière dans oracle : previews")
            elif not stat.S_ISREG(mode):
                raise RuntimeError(f"Sortie non régulière dans oracle : {name}")
        previews_fd = os.open("previews", _directory_flags(), dir_fd=root_fd)
        try:
            preview_entries = _closed_entries(
                previews_fd, expected=HISTORICAL_PREVIEWS, location="previews/",
            )
            if any(not stat.S_ISREG(mode) for mode in preview_entries.values()):
                raise RuntimeError("Sortie non régulière dans oracle : previews/")
            entries = {
                name: _regular_hash(root_fd, name, location="")
                for name in HISTORICAL_ROOT - {"previews"}
            }
            entries.update({
                f"previews/{name}": _regular_hash(previews_fd, name, location="previews/")
                for name in HISTORICAL_PREVIEWS
            })
        finally:
            os.close(previews_fd)
    finally:
        os.close(root_fd)
    if frozenset(entries) != HISTORICAL_OUTPUTS:
        raise RuntimeError("Inventaire historique interne incohérent")
    return dict(sorted(entries.items()))


def _safe_archive_member(root: Path, name: str) -> Path:
    member = PurePosixPath(name)
    if (not name or "\x00" in name or member.is_absolute() or ".." in member.parts
            or any(part in {"", "."} for part in member.parts)):
        raise RuntimeError(f"Archive Git candidate non sûre : {name!r}")
    target = root.joinpath(*member.parts)
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise RuntimeError(f"Archive Git candidate hors snapshot : {name!r}") from exc
    return target


def _extract_tree(repo: Path, tree: str, root: Path) -> None:
    archive = _git_bytes(repo, "archive", "--format=tar", tree)
    root.mkdir(mode=0o700)
    seen: set[str] = set()
    with tarfile.open(fileobj=BytesIO(archive), mode="r:") as stream:
        for member in stream:
            target = _safe_archive_member(root, member.name.rstrip("/"))
            if member.name in seen:
                raise RuntimeError(f"Archive Git candidate duplique une entrée : {member.name}")
            seen.add(member.name)
            if member.isdir():
                target.mkdir(mode=0o700, parents=True, exist_ok=False)
                continue
            if not member.isreg():
                raise RuntimeError(f"Archive Git candidate contient une entrée non régulière : {member.name}")
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            payload = stream.extractfile(member)
            if payload is None:
                raise RuntimeError(f"Archive Git candidate illisible : {member.name}")
            with target.open("xb") as destination:
                while chunk := payload.read(1024 * 1024):
                    destination.write(chunk)
            os.chmod(target, member.mode & 0o777)


def _snapshot_inventory(root: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink() or not path.is_file():
            if path.is_dir() and not path.is_symlink():
                continue
            raise RuntimeError(f"Snapshot candidat non régulier : {relative}")
        entries[relative] = _sha(path)
    return dict(sorted(entries.items()))


@contextmanager
def _candidate_snapshot(candidate: Path) -> Iterator[CandidateSnapshot]:
    """Capture HEAD + tracked/untracked nonignored changes through a private index."""
    head = _git(candidate, "rev-parse", "HEAD")
    head_tree = _git(candidate, "rev-parse", "HEAD^{tree}")
    status = _git(candidate, "status", "--porcelain=v1", "--untracked-files=all")
    with tempfile.TemporaryDirectory(prefix="lafractale-b2b-candidate-") as temporary:
        temporary_root = Path(temporary)
        index = temporary_root / "candidate.index"
        index_env = os.environ.copy()
        index_env["GIT_INDEX_FILE"] = str(index)
        _git(candidate, "read-tree", "HEAD", env=index_env)
        _git(candidate, "add", "--all", env=index_env)
        tree = _git(candidate, "write-tree", env=index_env)
        root = temporary_root / "source"
        _extract_tree(candidate, tree, root)
        inventory = _snapshot_inventory(root)
        yield CandidateSnapshot(
            head=head,
            head_tree=head_tree,
            tree=tree,
            status=status,
            status_sha256=_sha_bytes(status.encode("utf-8")),
            inventory=inventory,
            root=root,
        )


def _python_source_blobs(repo: Path, tree: str) -> dict[str, str]:
    """Return the exact Python blob map used to distinguish executable engines."""
    listing = _git_bytes(repo, "ls-tree", "-r", "-z", "--full-tree", tree, "--", "src/lafractale")
    files: dict[str, str] = {}
    for record in listing.split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            _mode, object_type, object_id = metadata.decode("ascii").split(" ", 2)
            path = raw_path.decode("utf-8")
        except (UnicodeDecodeError, ValueError) as exc:
            raise RuntimeError("Inventaire Python Git invalide") from exc
        if object_type != "blob" or not path.endswith(".py"):
            continue
        if path in files:
            raise RuntimeError(f"Inventaire Python Git duplique : {path}")
        files[path] = object_id
    if not files:
        raise RuntimeError("Inventaire Python Git vide : src/lafractale absent")
    return dict(sorted(files.items()))


def _python_source_fingerprint(files: dict[str, str]) -> str:
    return _sha_bytes(json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def _require_distinct_python_source(repo: Path, candidate_tree: str,
                                    reference_commit: str) -> tuple[dict[str, str], dict[str, str]]:
    candidate_files = _python_source_blobs(repo, candidate_tree)
    reference_files = _python_source_blobs(repo, reference_commit)
    if candidate_files == reference_files:
        raise RuntimeError("Oracle invalide : candidat et baseline contiennent le même code Python")
    return candidate_files, reference_files


def _verify_proof_candidate(candidate: Path, proof_path: Path) -> None:
    try:
        proof = json.loads(proof_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"Preuve oracle illisible : {exc}") from exc
    if not isinstance(proof, dict):
        raise RuntimeError("Preuve oracle invalide : objet JSON attendu")
    expected_tree = proof.get("candidate_tree")
    expected_inventory = proof.get("candidate_snapshot_inventory")
    if not isinstance(expected_tree, str) or len(expected_tree) != 40 or not isinstance(expected_inventory, dict):
        raise RuntimeError("Preuve oracle invalide : identité candidate absente")
    with _candidate_snapshot(candidate) as snapshot:
        if snapshot.tree != expected_tree or snapshot.inventory != expected_inventory:
            raise RuntimeError("Preuve oracle plus applicable : le tree candidat a changé")


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
    parser.add_argument("--reference-commit")
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
        print(f"B2B_ORACLE_PROOF_APPLICABLE {args.verify_proof.resolve()}")
        return 0
    if not args.reference_commit or not args.approvals_sha256 or args.proof is None:
        raise RuntimeError("--reference-commit, --approvals-sha256 et --proof sont obligatoires")
    _git(candidate, "cat-file", "-e", f"{args.reference_commit}^{{commit}}")
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
        candidate_python_files, reference_python_files = _require_distinct_python_source(
            candidate, snapshot.tree, args.reference_commit,
        )
        with tempfile.TemporaryDirectory(prefix="lafractale-b2b-oracle-") as temporary:
            worktree = Path(temporary) / "reference"
            try:
                _git(candidate, "worktree", "add", "--detach", str(worktree), args.reference_commit)
                reference = worktree.resolve()
                candidate_env = base_env.copy()
                candidate_env["PYTHONPATH"] = str((snapshot.root / "src").resolve())
                reference_env = base_env.copy()
                reference_env["PYTHONPATH"] = str((reference / "src").resolve())
                candidate_runtime = _runtime_environment(python, source=snapshot.root, env=candidate_env)
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
                        name=mode, source=snapshot.root, output=Path(temporary) / "candidate-out" / mode,
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
                    "candidate_head": snapshot.head,
                    "candidate_head_tree": snapshot.head_tree,
                    "candidate_tree": snapshot.tree,
                    "candidate_tree_matches_head": snapshot.tree == snapshot.head_tree,
                    "candidate_initial_status": snapshot.status,
                    "candidate_initial_status_sha256": snapshot.status_sha256,
                    "candidate_snapshot_inventory": snapshot.inventory,
                    "candidate_python_source_files": candidate_python_files,
                    "candidate_python_source_sha256": _python_source_fingerprint(candidate_python_files),
                    "reference_python_source_files": reference_python_files,
                    "reference_python_source_sha256": _python_source_fingerprint(reference_python_files),
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
