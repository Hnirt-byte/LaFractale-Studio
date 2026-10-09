"""Build short technical demo and a transparent, reproducible audit trail."""
from __future__ import annotations
import hashlib
import json
import re
import copy
import secrets
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import fitz

from lafractale import __version__
from lafractale.config.schema import Book, ConfigError, validate_plan_vocabulary, verify_book_snapshot
from lafractale.story.plan import demo_specs, full_build_blockers
from lafractale.activities.engine import generate, stable_seed
from lafractale.assets.registry import registry, sha256
from lafractale.config.companions import verify_companion_text
from lafractale.security.text import (verify_text_policy, blocked_name_fingerprints,
                                     parse_fingerprints, UnsafeEditorialText)
from lafractale.quality.checks import validate_collection
from lafractale.layout.pdf import write_pdf
from lafractale.export.securefs import parent_dirfd, validate_leaf_dir, audit_root_dirfd, UnsafeOutputPath


class PublicationError(RuntimeError):
    """Failed to publish a generated demo (not an unsafe output path)."""


class PublicationRecoveryError(PublicationError):
    """Both publishing and restoring failed; old valid output is in backup_path."""

    def __init__(self, backup_path: Path, publish_error: OSError, restore_error: OSError):
        self.backup_path = backup_path
        self.publish_error = publish_error
        self.restore_error = restore_error
        super().__init__(
            f"Échec de publication ({publish_error}) ET de restauration ({restore_error}). "
            f"Sauvegarde conservée pour récupération manuelle : {backup_path}"
        )


def dump_json(path: Path, data: dict | list) -> None:
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False,sort_keys=True) + "\n",encoding="utf-8")


def _timestamp() -> str:
    # SOURCE_DATE_EPOCH allows byte-for-byte reproducible manifests in CI.
    value=os.getenv("SOURCE_DATE_EPOCH")
    return datetime.fromtimestamp(int(value), timezone.utc).isoformat() if value else datetime.now(timezone.utc).isoformat()


def _build_demo_unpublished(book: Book, out: Path, *, seed: int = 2026) -> dict:
    verify_companion_text(book.root, book.companion, book.data, book.plan)
    verify_book_snapshot(book)
    errors = validate_plan_vocabulary(book)
    if errors:
        raise ConfigError("\n".join(errors))
    specs=demo_specs(book)
    activities=[generate(spec,stable_seed(book.book_id,spec.id,seed)) for spec in specs]
    errors=validate_collection(activities)
    if errors:
        raise ConfigError("Exercices invalides :\n" + "\n".join(errors))
    assets=registry(book)
    companion=book.companion
    prohibited = tuple(name for name in companion.reserved_names
                       if not companion.selected or name.casefold() != companion.render_name.casefold())
    # Capture the same detached, validated data for both PDF and JSON exports.
    activity_snapshot = copy.deepcopy([a.as_dict() for a in activities])
    verify_text_policy(activity_snapshot, forbidden_names=prohibited, location="activités générées")
    # Build in destination only after all structural blockers have passed.
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    interior=out/"interior.pdf";answers=out/"answer_key.pdf"
    write_pdf(interior,activities,book.data,answer_key=False)
    write_pdf(answers,activities,book.data,answer_key=True)
    previews=out/"previews";previews.mkdir(exist_ok=True)
    with fitz.open(interior) as pdf:
        if len(pdf)!=len(activities):
            raise RuntimeError("Pagination PDF incorrecte")
        for i,page in enumerate(pdf,1):
            pix=page.get_pixmap(matrix=fitz.Matrix(1.4,1.4),alpha=False)
            pix.save(str(previews/f"page_{i:02d}.png"))
    with fitz.open(answers) as pdf:
        if len(pdf)!=len(activities):
            raise RuntimeError("Pagination du corrigé incorrecte")
    # Reject any unexpected mutation by a renderer/hook before publication.
    if [a.as_dict() for a in activities] != activity_snapshot:
        raise ConfigError("Activités modifiées après validation pendant le rendu")
    dump_json(out/"activities.json",activity_snapshot)
    report={
        "book_id":book.book_id,"engine_version":__version__,"kind":"TECHNICAL_DEMO_ONLY",
        "companion":{"status":companion.status,"id":companion.id,"name":companion.render_name},
        "auto_checks":{"pass":True,"errors":[],"activity_count":len(activities),
                       "expected_demo_pages":len(activities),"checked_types":sorted({a.type for a in activities})},
        "page_results":[{"id":a.id,"source_page":a.page,"mechanic":a.type,
                         "automatic":"auto_pass", "graphic":"needs_visual_review",
                         "human_approval":"pending"} for a in activities],
        "blocking_for_publication":[
            "Fiches non revues visuellement et pédagogiquement",
            (f"Variantes graphiques de {companion.render_name} non approuvées (référence non dessinée)"
             if companion.selected else "Compagnon non sélectionné : illustrations en attente"),
            "Droits de la référence graphique non documentés" if assets else "Assets graphiques non validés",
            "Plan de pages intégral non implémenté",
            "Contrôles KDP Print Previewer et épreuve physique non réalisés"],
        "full_build_blockers":full_build_blockers(book),"ready_for_kdp":False,
    }
    dump_json(out/"quality_report.json",report)
    lines=[f"# Rapport qualité - {book.book_id}","","**Démo technique uniquement, non publiable.**","",
           f"- Mécaniques valides : {', '.join(report['auto_checks']['checked_types'])}",
           f"- {len(activities)} fiches et {len(activities)} corrigés PDF", "- Revue humaine : EN ATTENTE","",
           "## Bloquants avant publication",""]
    lines += [f"- {s}" for s in report["blocking_for_publication"]]
    lines += ["","## Assemblage intégral","",*[f"- {s}" for s in report["full_build_blockers"]],""]
    (out/"quality_report.md").write_text("\n".join(lines),encoding="utf-8")
    plan_file=book.path.with_name("page_plan.csv")
    manifest={"engine_version":__version__,"generated_at_utc":_timestamp(),"book_id":book.book_id,
              "companion":{"status":companion.status,"id":companion.id,"name":companion.render_name},
              "target_pages":book.pages,"demo_pages":len(activities),"seed":seed,
              "source":{"book_config":str(book.path.relative_to(book.root)),"book_config_sha256":sha256(book.path),
                        "page_plan_sha256":sha256(plan_file) if plan_file.exists() else None},
              "assets":assets,"activities":[{"id":a.id,"page":a.page,"seed":a.seed} for a in activities],
              "outputs":{p:sha256(out/p) for p in ("interior.pdf","answer_key.pdf","activities.json","quality_report.json")},
              "security":{"unicode_policy":"NFKC-Latin-no-ignorable-v1",
                          "blocked_name_fingerprints":[list(item) for item in blocked_name_fingerprints(prohibited)]},
              "publication_approved":False}
    # Re-read the approved source at the last publication-adjacent step: a
    # post-load or mid-build mutation must never yield a trusted manifest.
    verify_companion_text(book.root, book.companion, book.data, book.plan)
    verify_book_snapshot(book)
    if registry(book) != assets:
        raise ConfigError("Compagnon modifié pendant la génération")
    # Rendered PDFs must not smuggle reserved names which were absent from
    # validated editorial source (including a renderer-level text injection).
    for filename in ("interior.pdf", "answer_key.pdf"):
        with fitz.open(out / filename) as pdf:
            content = "\n".join(page.get_text() for page in pdf)
        verify_text_policy(content, forbidden_names=prohibited, location=f"PDF {filename}")
    # Re-check the generated data against companion restrictions as well.
    enriched = copy.deepcopy(book.data)
    enriched["generated_activities"] = activity_snapshot
    verify_companion_text(book.root, book.companion, enriched, book.plan)
    verify_text_policy(report, forbidden_names=prohibited, location="rapport JSON")
    verify_text_policy(manifest, forbidden_names=prohibited, location="manifeste JSON")
    dump_json(out/"manifest.json",manifest)
    return report


def build_demo(book: Book, out: Path, *, seed: int = 2026) -> dict:
    """Build in a private directory and publish using anchored directory FDs.

    Each parent component is opened with O_NOFOLLOW; replacements and cleanup
    operate on names relative to the verified parent, not resolved user paths.
    """
    if ".." in Path(out).parts:
        raise UnsafeOutputPath("Traversée de chemin de sortie interdite")
    out = Path(os.path.abspath(out))
    with parent_dirfd(out, create=True) as (parent_fd, leaf):
        validate_leaf_dir(parent_fd, leaf)
        nonce = secrets.token_hex(16)
        stage_name = f".{leaf}.build-{nonce}"
        backup_name = f".{leaf}.previous-{nonce}"
        os.mkdir(stage_name, mode=0o700, dir_fd=parent_fd)
        # The parent FD anchors the actual directory even if an ancestor path
        # is concurrently renamed. Staging is private to the generating user.
        parent_real = Path(os.readlink(f"/proc/self/fd/{parent_fd}"))
        stage = parent_real / stage_name
        backup = parent_real / backup_name
        has_backup = False
        published = False
        try:
            report = _build_demo_unpublished(book, stage, seed=seed)
            errors = audit_output(stage, book=book)
            if errors:
                raise ConfigError("QA de génération incomplète : " + "; ".join(errors))
            if validate_leaf_dir(parent_fd, leaf):
                os.replace(leaf, backup_name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
                has_backup = True
            try:
                os.replace(stage_name, leaf, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
            except OSError as publish_exc:
                if has_backup:
                    try:
                        os.replace(backup_name, leaf, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
                    except OSError as restore_exc:
                        # Recovery is not confirmed: NEVER remove the backup.
                        # The old, audited manifest and PDFs remain there.
                        raise PublicationRecoveryError(backup, publish_exc, restore_exc) from restore_exc
                    else:
                        has_backup = False  # restoration succeeded; backup moved back
                raise PublicationError(f"Échec de publication du dossier : {publish_exc}") from publish_exc
            published = True
            return report
        finally:
            if stage.is_dir() and not stage.is_symlink():
                shutil.rmtree(stage)
            # Only a CONFIRMED successful publication permits deleting the old
            # valid demo. A failed rollback must retain the backup intact.
            if published and has_backup and backup.is_dir() and not backup.is_symlink():
                shutil.rmtree(backup)


def audit_output(out: Path, *, book: Book | None = None) -> list[str]:
    """Audit only through a symlink-free, FD-anchored directory root."""
    if book is None:
        return ["Audit impossible : --book / contexte source de confiance obligatoire"]
    try:
        with audit_root_dirfd(out) as anchored_root:
            return _audit_output_verified(anchored_root, book=book)
    except (UnsafeOutputPath, OSError) as exc:
        return [f"Répertoire d'audit non autorisé : {exc}"]


def _audit_output_verified(out: Path, *, book: Book) -> list[str]:
    """Source policy comes from Book; the output FD cannot be a user symlink.

    The root FD stays open while files are inspected through /proc/self/fd.
    """
    try:
        verify_book_snapshot(book)
        verify_companion_text(book.root, book.companion, book.data, book.plan)
        # The audit policy comes exclusively from the pinned source catalogue.
        companion = book.companion
        prohibited = tuple(name for name in companion.reserved_names
                           if not companion.selected or
                           name.casefold() != companion.render_name.casefold())
        trusted_fingerprints = blocked_name_fingerprints(prohibited)
        expected_companion = {"status": companion.status, "id": companion.id,
                              "name": companion.render_name}
        trusted_source = {
            "book_config": str(book.path.relative_to(book.root)),
            "book_config_sha256": book.source_sha256,
            "page_plan_sha256": book.source_plan_sha256,
        }
    except (ConfigError, ValueError, OSError, RuntimeError) as exc:
        return [f"Audit impossible : source de confiance invalide : {exc}"]
    # Resolve only the already-open trusted FD for within-root comparisons;
    # NEVER resolve an untrusted user-provided audit path.
    root_real = out.resolve(strict=True)
    expected_outputs = {"interior.pdf", "answer_key.pdf", "activities.json", "quality_report.json"}
    errors: list[str] = []
    manifest_path = out / "manifest.json"
    report_path = out / "quality_report.json"
    for path in (manifest_path, report_path):
        if path.is_symlink() or not path.is_file():
            return [f"Manifest/rapport non autorisé : {path.name}"]
        try:
            path.resolve().relative_to(root_real)
        except ValueError:
            return [f"Manifest/rapport non autorisé : {path.name}"]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        return [f"Manifest/rapport manquant ou invalide : {exc}"]
    if not isinstance(manifest, dict):
        return ["Manifest invalide : objet JSON attendu"]
    if not isinstance(report, dict):
        return ["Rapport qualité invalide : objet JSON attendu"]
    try:
        security = manifest.get("security")
        if not isinstance(security, dict) or security.get("unicode_policy") != "NFKC-Latin-no-ignorable-v1":
            raise UnsafeEditorialText("Manifeste : politique Unicode absente ou non conforme")
        # Strict comparison with source-backed policy; the manifest CANNOT select
        # or disable forbidden identities, even with recomputed file checksums.
        manifest_fingerprints = parse_fingerprints(security.get("blocked_name_fingerprints"))
        if (set(security) != {"unicode_policy", "blocked_name_fingerprints"}
                or manifest_fingerprints != trusted_fingerprints):
            raise UnsafeEditorialText("Manifeste : empreintes des noms réservés non conformes à la source")
        if (manifest.get("book_id") != book.book_id
                or manifest.get("target_pages") != book.pages
                or manifest.get("companion") != expected_companion
                or manifest.get("source") != trusted_source
                or report.get("book_id") != book.book_id
                or report.get("companion") != expected_companion):
            raise UnsafeEditorialText("Manifeste/rapport : identité ou provenance non conformes à la source")
        fingerprints = trusted_fingerprints
        verify_text_policy(manifest, fingerprints=fingerprints, location="manifeste")
        verify_text_policy(report, fingerprints=fingerprints, location="rapport")
        # QA must not follow attacker-provided symlinks while reading JSON/MD.
        # This guard precedes parsing; checksum validation follows below.
        activities_path = out / "activities.json"
        markdown_path = out / "quality_report.md"
        for artifact in (activities_path, markdown_path):
            if (artifact.is_symlink() or not artifact.is_file()
                    or artifact.stat().st_size > 4_000_000):
                raise UnsafeEditorialText(f"Sortie texte non autorisée : {artifact.name}")
        activities_json = json.loads(activities_path.read_text(encoding="utf-8"))
        verify_text_policy(activities_json, fingerprints=fingerprints, location="activités JSON")
        verify_text_policy(markdown_path.read_text(encoding="utf-8"),
                           fingerprints=fingerprints, location="rapport Markdown")
    except (UnsafeEditorialText, ValueError, OSError) as exc:
        return [f"Sécurité texte/Unicode activities.json / manifeste / rapport : {exc}"]
    demo_pages = manifest.get("demo_pages")
    if not isinstance(demo_pages, int) or isinstance(demo_pages, bool) or not 1 <= demo_pages <= 50:
        return ["Manifest demo_pages invalide"]
    if manifest.get("publication_approved") is not False:
        return ["Manifest publication_approved doit être false"]
    outputs = manifest.get("outputs")
    if not isinstance(outputs, dict):
        return ["Manifest outputs invalide : objet JSON attendu"]
    names = set(outputs)
    if names != expected_outputs:
        extra = sorted(names - expected_outputs)
        missing = sorted(expected_outputs - names)
        if extra:
            errors.append("Manifest outputs non autorisé : " + ", ".join(extra))
        if missing:
            errors.append("Manifest outputs manquant : " + ", ".join(missing))
    for name in sorted(expected_outputs):
        checksum = outputs.get(name)
        path = out / name
        if not isinstance(checksum, str) or len(checksum) != 64:
            errors.append(f"Checksum invalide : {name}")
            continue
        if path.is_symlink() or not path.is_file():
            errors.append(f"Fichier modifié/absent : {name}")
            continue
        try:
            path.resolve().relative_to(root_real)
        except ValueError:
            errors.append(f"Fichier hors sortie autorisée : {name}")
            continue
        if sha256(path) != checksum:
            errors.append(f"Fichier modifié/absent : {name}")
    for name in ("interior.pdf", "answer_key.pdf"):
        path = out / name
        if path.is_symlink() or not path.is_file():
            continue
        try:
            with fitz.open(path) as pdf:
                if len(pdf) != manifest.get("demo_pages"):
                    errors.append(f"PDF : mauvais nombre de pages {name}")
                for index, page in enumerate(pdf):
                    extracted = page.get_text()
                    if not extracted.strip():
                        errors.append(f"PDF : texte absent {name} p{index + 1}")
                    try:
                        verify_text_policy(extracted, fingerprints=fingerprints,
                                           location=f"PDF {name} p{index+1}")
                    except UnsafeEditorialText as exc:
                        errors.append(str(exc))
                    if not page.get_fonts():
                        errors.append(f"PDF : police absente {name} p{index + 1}")
        except Exception as exc:
            errors.append(f"PDF non lisible {name}: {exc}")
    previews = out / "previews"
    if previews.is_symlink() or not previews.is_dir():
        errors.append("Dossier d'aperçus absent ou invalide")
    else:
        preview_files = [path for path in previews.glob("page_*.png") if path.is_file() and not path.is_symlink()]
        if len(preview_files) != manifest.get("demo_pages"):
            errors.append("Nombre d'aperçus incorrect")
    auto_checks = report.get("auto_checks")
    if not isinstance(auto_checks, dict):
        errors.append("Rapport qualité auto_checks invalide")
    elif auto_checks.get("pass") is not True:
        errors.append("Contrôles logiques non validés")
    if report.get("ready_for_kdp") is not False:
        errors.append("Démo incorrectement déclarée publiable")
    return errors
