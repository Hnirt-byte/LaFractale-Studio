"""Build short technical demo and a transparent, reproducible audit trail."""
from __future__ import annotations
import hashlib
import json
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
from lafractale.quality.checks import validate_collection
from lafractale.layout.pdf import write_pdf


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
    dump_json(out/"activities.json",[a.as_dict() for a in activities])
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
              "publication_approved":False}
    # Re-read the approved source at the last publication-adjacent step: a
    # post-load or mid-build mutation must never yield a trusted manifest.
    verify_companion_text(book.root, book.companion, book.data, book.plan)
    verify_book_snapshot(book)
    if registry(book) != assets:
        raise ConfigError("Compagnon modifié pendant la génération")
    dump_json(out/"manifest.json",manifest)
    return report


def build_demo(book: Book, out: Path, *, seed: int = 2026) -> dict:
    """Generate in a private staging directory, publish only after passing QA.

    Mid-render mutations must not leave a partially rendered book (or a fake
    success manifest) in the user-visible destination. An existing valid demo
    stays unchanged if validation fails.
    """
    out = Path(os.path.abspath(out))
    if out.is_symlink() or (out.exists() and not out.is_dir()):
        raise ConfigError("Répertoire de sortie invalide ou symlink interdit")
    out.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{out.name}.build-", dir=out.parent))
    backup: Path | None = None
    try:
        report = _build_demo_unpublished(book, stage, seed=seed)
        errors = audit_output(stage)
        if errors:
            raise ConfigError("QA de génération incomplète : " + "; ".join(errors))
        # After the last validation, the original output is not touched until
        # a complete and audited directory is ready to be swapped in.
        if out.is_symlink() or (out.exists() and not out.is_dir()):
            raise ConfigError("Répertoire de sortie modifié pendant la génération")
        if out.exists():
            backup = Path(tempfile.mkdtemp(prefix=f".{out.name}.previous-", dir=out.parent))
            backup.rmdir()
            os.replace(out, backup)
        try:
            os.replace(stage, out)
        except OSError:
            if backup is not None:
                os.replace(backup, out)
                backup = None
            raise
        return report
    finally:
        if stage.exists():
            shutil.rmtree(stage)
        if backup is not None and backup.exists():
            shutil.rmtree(backup)


def audit_output(out: Path) -> list[str]:
    """Audit only the fixed, local artifacts emitted by build_demo."""
    out = Path(out).resolve()
    expected_outputs = {"interior.pdf", "answer_key.pdf", "activities.json", "quality_report.json"}
    errors: list[str] = []
    manifest_path = out / "manifest.json"
    report_path = out / "quality_report.json"
    for path in (manifest_path, report_path):
        if path.is_symlink() or not path.is_file():
            return [f"Manifest/rapport non autorisé : {path.name}"]
        try:
            path.resolve().relative_to(out)
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
            path.resolve().relative_to(out)
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
                    if not page.get_text().strip():
                        errors.append(f"PDF : texte absent {name} p{index + 1}")
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
