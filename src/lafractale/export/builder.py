"""Build short technical demo and a transparent, reproducible audit trail."""
from __future__ import annotations
import hashlib
import json
import math
import re
import copy
import secrets
import os
import shutil
import tempfile
import stat
from datetime import datetime, timezone
from pathlib import Path
from io import BytesIO
import fitz
from PIL import Image

from lafractale import __version__
from lafractale.config.schema import Book, ConfigError, validate_plan_vocabulary, verify_book_snapshot
from lafractale.story.plan import demo_specs, full_build_blockers
from lafractale.activities.engine import generate, stable_seed
from lafractale.assets.registry import registry, sha256
from lafractale.config.companions import verify_companion_text
from lafractale.security.text import (verify_text_policy, blocked_name_fingerprints,
                                     parse_fingerprints, UnsafeEditorialText)
from lafractale.security.strict_json import loads_strict
from lafractale.quality.checks import validate_collection
from lafractale.layout.pdf import write_pdf, fonts, _measure
from lafractale.layout.composition import compose_page
from lafractale.editorial import editorial_spec, transform_editorial
from lafractale.illustrations.registry import (IllustrationError, load_approved_artwork,
                                               verify_approved_artwork)
from lafractale.illustrations.routing import (IllustrationRoute, build_illustration_route,
    resolve_illustration_mode, verify_illustration_route)
from lafractale.illustrations.placement import (PipPlacementPlan, build_pip_placement_plan,
    placed_composition, resolve_pip_placement_mode, verify_pip_placement_plan)
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
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False,sort_keys=True,allow_nan=False) + "\n",encoding="utf-8")


def _timestamp() -> str:
    # SOURCE_DATE_EPOCH allows byte-for-byte reproducible manifests in CI.
    value=os.getenv("SOURCE_DATE_EPOCH")
    return datetime.fromtimestamp(int(value), timezone.utc).isoformat() if value else datetime.now(timezone.utc).isoformat()


def _build_demo_unpublished(book: Book, out: Path, *, seed: int = 2026,
                            illustration_id: str | None = None,
                            illustration_routing: str | None = None,
                            pip_placement: str | None = None,
                            editorial_profile: str | None = None,
                            trusted_approvals_sha256: str | None = None) -> dict:
    verify_companion_text(book.root, book.companion, book.data, book.plan)
    verify_book_snapshot(book)
    mode = resolve_illustration_mode(
        illustration_id, illustration_routing, trusted_approvals_sha256,
    )
    placement_mode = resolve_pip_placement_mode(pip_placement)
    if placement_mode != "none" and mode != "routed":
        raise IllustrationError("Placement Pip autorisé uniquement avec la route C1 Halloween")
    editorial = editorial_spec(editorial_profile)
    if editorial is not None and (mode != "routed" or placement_mode == "none"):
        raise IllustrationError("Profil éditorial exige la route C1 et le placement C2 V2")
    artwork = None
    route = None
    placement: PipPlacementPlan | None = None
    if mode == "legacy_illustration":
        assert isinstance(illustration_id, str) and isinstance(trusted_approvals_sha256, str)
        artwork = load_approved_artwork(
            book, illustration_id, trusted_approvals_sha256=trusted_approvals_sha256,
        )
    elif mode == "routed":
        assert isinstance(illustration_routing, str) and isinstance(trusted_approvals_sha256, str)
        route = build_illustration_route(
            book, policy_id=illustration_routing, trusted_approvals_sha256=trusted_approvals_sha256,
        )
        if placement_mode != "none":
            assert isinstance(pip_placement, str)
            placement = build_pip_placement_plan(
                book, route, policy_id=pip_placement,
                trusted_approvals_sha256=trusted_approvals_sha256,
            )
    errors = validate_plan_vocabulary(book)
    if errors:
        raise ConfigError("\n".join(errors))
    specs=demo_specs(book)
    activities=[generate(spec,stable_seed(book.book_id,spec.id,seed)) for spec in specs]
    errors=validate_collection(activities)
    if errors:
        raise ConfigError("Exercices invalides :\n"+"\n".join(errors))
    if editorial is not None:
        activities=[transform_editorial(a, book, editorial.profile_id) for a in activities]
        errors=validate_collection(activities, moon_len=8)
        if errors:
            raise ConfigError("Exercices éditoriaux C4 invalides :\n"+"\n".join(errors))
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
    kwargs = ({"artwork": artwork, "approved_book": book,
               "trusted_approvals_sha256": trusted_approvals_sha256} if artwork else
              {"illustration_route": route, "approved_book": book,
               "trusted_approvals_sha256": trusted_approvals_sha256,
               **(dict(pip_placement=placement.policy_id) if placement is not None else {}),
               **(dict(editorial_profile=editorial_profile) if editorial is not None else {})}
              if route else {})
    write_pdf(interior,activities,book.data,answer_key=False, **kwargs)
    write_pdf(answers,activities,book.data,answer_key=True, **kwargs)
    previews=out/"previews";previews.mkdir(exist_ok=True)
    preview_sources = (("interior", interior), ("answer_key", answers)) if route else (("", interior),)
    for label, pdf_path in preview_sources:
        with fitz.open(pdf_path) as pdf:
            if len(pdf)!=len(activities):
                raise RuntimeError("Pagination PDF incorrecte")
            for i,page in enumerate(pdf,1):
                pix=page.get_pixmap(matrix=fitz.Matrix(1.4,1.4),alpha=False)
                name = f"{label}_page_{i:02d}.png" if route else f"page_{i:02d}.png"
                pix.save(str(previews/name))
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
            ("Visuel monochrome intégré uniquement à la démo ; revue des droits et du prépresse KDP en attente"
             if artwork is not None or route is not None else
             f"Variantes graphiques de {companion.render_name} non approuvées (référence non dessinée)"
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
    if artwork is not None:
        manifest["illustration"] = artwork.manifest_entry()
    elif route is not None:
        manifest["illustration_routing"] = route.manifest_entry()
    if placement is not None:
        # Opt-in C2 only: a dedicated key, never an implicit activation.
        manifest["pip_placement"] = placement.manifest_entry()
    if editorial is not None:
        # Opt-in C4 only: a dedicated key, never an implicit activation.
        manifest["editorial_profile"] = editorial.profile_id
    # Re-read the approved source at the last publication-adjacent step: a
    # post-load or mid-build mutation must never yield a trusted manifest.
    verify_companion_text(book.root, book.companion, book.data, book.plan)
    verify_book_snapshot(book)
    if registry(book) != assets:
        raise ConfigError("Compagnon modifié pendant la génération")
    if artwork is not None:
        verify_approved_artwork(book, artwork, trusted_approvals_sha256=trusted_approvals_sha256)
    elif route is not None:
        assert isinstance(trusted_approvals_sha256, str)
        verify_illustration_route(book, route, policy_id=route.policy_id,
                                  trusted_approvals_sha256=trusted_approvals_sha256)
        if placement is not None:
            verify_pip_placement_plan(book, route, placement, policy_id=placement.policy_id,
                                      trusted_approvals_sha256=trusted_approvals_sha256)
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


def build_demo(book: Book, out: Path, *, seed: int = 2026,
               illustration_id: str | None = None,
               illustration_routing: str | None = None,
               pip_placement: str | None = None,
               editorial_profile: str | None = None,
               trusted_approvals_sha256: str | None = None) -> dict:
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
            report = _build_demo_unpublished(book, stage, seed=seed,
                illustration_id=illustration_id, illustration_routing=illustration_routing,
                pip_placement=pip_placement,
                editorial_profile=editorial_profile,
                trusted_approvals_sha256=trusted_approvals_sha256)
            errors = audit_output(stage, book=book, illustration_id=illustration_id,
                                  illustration_routing=illustration_routing,
                                  pip_placement=pip_placement,
                                  editorial_profile=editorial_profile,
                                  trusted_approvals_sha256=trusted_approvals_sha256)
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



# The output directory is an exact package, not merely a collection of known
# files: unknown artefacts must not travel beside a successful QA attestation.
_AUDITED_ROOT_FILES = frozenset({
    "interior.pdf", "answer_key.pdf", "activities.json",
    "quality_report.json", "quality_report.md", "manifest.json",
})


def _exact_output_inventory(out: Path, *, page_count: int, routed: bool = False) -> list[str]:
    """Check all root and preview entries through directory FDs, without following links.

    `out` is already `/proc/self/fd/<fd>` from audit_root_dirfd. We duplicate
    that already-verified descriptor (no pathname lookup) and use openat with
    O_NOFOLLOW for `previews`. No manifest field can expand the allowlist.
    """
    errors: list[str] = []
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    expected_root = _AUDITED_ROOT_FILES | {"previews"}
    expected_previews = ({f"{kind}_page_{i:02d}.png" for kind in ("interior", "answer_key")
                         for i in range(1, page_count + 1)} if routed else
                         {f"page_{i:02d}.png" for i in range(1, page_count + 1)})

    def inspect(fd: int, expected: set[str] | frozenset[str], *, root: bool) -> set[str]:
        location = "racine" if root else "previews/"
        with os.scandir(fd) as scan:
            entries = {entry.name: entry.stat(follow_symlinks=False).st_mode for entry in scan}
        extra = sorted(entries.keys() - expected)
        missing = sorted(expected - entries.keys())
        for name in extra:
            errors.append(f"Inventaire {location} : entrée non autorisée : {name}")
        for name in missing:
            errors.append(f"Inventaire {location} : entrée manquante : {name}")
        for name in sorted(entries.keys() & expected):
            mode = entries[name]
            if root and name == "previews":
                if not stat.S_ISDIR(mode):
                    errors.append("Inventaire racine : previews n'est pas un répertoire réel")
            elif not stat.S_ISREG(mode):
                # Preserve the existing public QA error vocabulary for these
                # two security-critical JSON files (historical CLI clients).
                legacy = (" (Manifest/rapport non autorisé)"
                          if root and name in {"manifest.json", "quality_report.json"} else "")
                errors.append(f"Inventaire {location} : entrée non régulière : {name}{legacy}")
        return set(entries)

    # The only allowed input to this internal helper is the descriptor token
    # produced by audit_root_dirfd. Duplicate the live FD directly: unlike a
    # fresh path open, this does not follow even a procfs magic symlink.
    if out.parent != Path("/proc/self/fd") or not out.name.isascii() or not out.name.isdecimal():
        raise UnsafeOutputPath("Inventaire : descripteur racine non ancré")
    root_fd = os.dup(int(out.name))
    if not stat.S_ISDIR(os.fstat(root_fd).st_mode):
        os.close(root_fd)
        raise UnsafeOutputPath("Inventaire : descripteur racine non répertoire")
    try:
        seen_root = inspect(root_fd, expected_root, root=True)
        if "previews" in seen_root:
            try:
                previews_fd = os.open("previews", flags, dir_fd=root_fd)
            except OSError as exc:
                errors.append(f"Inventaire previews/ : répertoire non autorisé : {exc}")
            else:
                try:
                    inspect(previews_fd, expected_previews, root=False)
                finally:
                    os.close(previews_fd)
    finally:
        os.close(root_fd)
    return errors


def _page_collision_errors(page, region: tuple[float, float, float, float], *,
                           location: str, tolerance: float = 0.05) -> list[str]:
    """Refuse any text or vector drawing overlapping the placed image box.

    Slot containment and region overlap checks are necessary but not sufficient:
    content actually drawn on the page (footer rule, board frame, labels and
    mechanic strokes) must not intersect the placed artwork either.
    """
    x0, y0, x1, y1 = region

    def overlaps(box) -> bool:
        try:
            bx0, by0, bx1, by1 = (float(value) for value in tuple(box)[:4])
        except (TypeError, ValueError):
            return False
        return (min(x1, bx1) - max(x0, bx0) > tolerance
                and min(y1, by1) - max(y0, by0) > tolerance)

    errors: list[str] = []
    for word in page.get_text("words"):
        if overlaps(word):
            errors.append(f"PDF : texte en collision avec le visuel Pip {location}")
            break
    for drawing in page.get_drawings():
        box = drawing.get("rect")
        if box is not None and overlaps((box.x0, box.y0, box.x1, box.y1)):
            errors.append(f"PDF : tracé vectoriel en collision avec le visuel Pip {location}")
            break
    return errors


def audit_output(out: Path, *, book: Book | None = None,
                 illustration_id: str | None = None,
                 illustration_routing: str | None = None,
                 pip_placement: str | None = None,
                 editorial_profile: str | None = None,
                 trusted_approvals_sha256: str | None = None) -> list[str]:
    """Audit only through a symlink-free, FD-anchored directory root."""
    if book is None:
        return ["Audit impossible : --book / contexte source de confiance obligatoire"]
    try:
        mode = resolve_illustration_mode(illustration_id, illustration_routing, trusted_approvals_sha256)
        placement_mode = resolve_pip_placement_mode(pip_placement)
        if placement_mode != "none" and mode != "routed":
            raise IllustrationError("Placement Pip autorisé uniquement avec la route C1 Halloween")
        editorial = editorial_spec(editorial_profile)
        if editorial is not None and (mode != "routed" or placement_mode == "none"):
            raise IllustrationError("Profil éditorial exige la route C1 et le placement C2 V2")
    except IllustrationError as exc:
        return [f"Audit impossible : contexte d'illustration non autorisé : {exc}"]
    try:
        with audit_root_dirfd(out) as anchored_root:
            return _audit_output_verified(anchored_root, book=book,
                illustration_id=illustration_id, illustration_routing=illustration_routing,
                pip_placement=pip_placement,
                editorial_profile=editorial_profile,
                trusted_approvals_sha256=trusted_approvals_sha256)
    except (UnsafeOutputPath, OSError, IllustrationError) as exc:
        return [f"Répertoire d'audit ou approbation non autorisé : {exc}"]


def _audit_output_verified(out: Path, *, book: Book,
                           illustration_id: str | None = None,
                           illustration_routing: str | None = None,
                           pip_placement: str | None = None,
                           editorial_profile: str | None = None,
                           trusted_approvals_sha256: str | None = None) -> list[str]:
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
        mode = resolve_illustration_mode(
            illustration_id, illustration_routing, trusted_approvals_sha256,
        )
        placement_mode = resolve_pip_placement_mode(pip_placement)
        if placement_mode != "none" and mode != "routed":
            raise IllustrationError("Placement Pip autorisé uniquement avec la route C1 Halloween")
        editorial = editorial_spec(editorial_profile)
        if editorial is not None and (mode != "routed" or placement_mode == "none"):
            raise IllustrationError("Profil éditorial exige la route C1 et le placement C2 V2")
        expected_artwork = None
        expected_route = None
        expected_placement: PipPlacementPlan | None = None
        if mode == "legacy_illustration":
            assert isinstance(illustration_id, str) and isinstance(trusted_approvals_sha256, str)
            expected_artwork = load_approved_artwork(
                book, illustration_id, trusted_approvals_sha256=trusted_approvals_sha256,
            )
        elif mode == "routed":
            assert isinstance(illustration_routing, str) and isinstance(trusted_approvals_sha256, str)
            expected_route = build_illustration_route(
                book, policy_id=illustration_routing,
                trusted_approvals_sha256=trusted_approvals_sha256,
            )
            if placement_mode != "none":
                assert isinstance(pip_placement, str)
                expected_placement = build_pip_placement_plan(
                    book, expected_route, policy_id=pip_placement,
                    trusted_approvals_sha256=trusted_approvals_sha256,
                )
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
    # Fail closed BEFORE reading outputs or replaying PDFs. The manifest and
    # its checksums cannot authorize extra files, folders or symlinks.
    try:
        inventory_errors = _exact_output_inventory(
            out, page_count=len(demo_specs(book)), routed=expected_route is not None,
        )
    except (OSError, ValueError, RuntimeError, ConfigError) as exc:
        return [f"Inventaire de sortie impossible : {exc}"]
    if inventory_errors:
        return inventory_errors
    expected_outputs = {"interior.pdf", "answer_key.pdf", "activities.json", "quality_report.json"}
    errors: list[str] = []
    def artwork_pixel_digest(artwork) -> str:
        with Image.open(BytesIO(artwork.pixels)) as approved_pixels:
            approved_pixels.load()
            return hashlib.sha256(approved_pixels.tobytes()).hexdigest()

    expected_pixel_digest = (artwork_pixel_digest(expected_artwork)
                             if expected_artwork is not None else None)
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
        manifest = loads_strict(manifest_path.read_bytes())
        report = loads_strict(report_path.read_bytes())
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
        if expected_artwork is not None:
            if (manifest.get("illustration") != expected_artwork.manifest_entry()
                    or "illustration_routing" in manifest or "pip_placement" in manifest):
                raise UnsafeEditorialText("Illustration du manifeste non conforme à la source approuvée")
        elif expected_route is not None:
            if ("illustration" in manifest
                    or manifest.get("illustration_routing") != expected_route.manifest_entry()):
                raise UnsafeEditorialText("Routage d'illustrations du manifeste non conforme")
            if expected_placement is not None:
                # C2 is opt-in: the manifest carries the recomputed plan or nothing.
                if manifest.get("pip_placement") != expected_placement.manifest_entry():
                    raise UnsafeEditorialText("Placement Pip du manifeste non conforme")
            elif "pip_placement" in manifest:
                raise UnsafeEditorialText("Placement Pip inattendu sans opt-in explicite")
        elif ("illustration" in manifest or "illustration_routing" in manifest
                or "pip_placement" in manifest):
            raise UnsafeEditorialText("Illustration inattendue dans le manifeste placeholder")
        if editorial is not None:
            if manifest.get("editorial_profile") != editorial.profile_id:
                raise UnsafeEditorialText("Profil éditorial du manifeste non conforme")
        elif "editorial_profile" in manifest:
            raise UnsafeEditorialText("Profil éditorial inattendu sans opt-in explicite")
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
        activities_json = loads_strict(activities_path.read_bytes())
        verify_text_policy(activities_json, fingerprints=fingerprints, location="activités JSON")
        verify_text_policy(markdown_path.read_text(encoding="utf-8"),
                           fingerprints=fingerprints, location="rapport Markdown")
    except (UnsafeEditorialText, ValueError, OSError) as exc:
        return [f"Sécurité texte/Unicode activities.json / manifeste / rapport : {exc}"]
    demo_pages = manifest.get("demo_pages")
    if not isinstance(demo_pages, int) or isinstance(demo_pages, bool) or not 1 <= demo_pages <= 50:
        return ["Manifest demo_pages invalide"]
    assert isinstance(demo_pages, int)
    if manifest.get("publication_approved") is not False:
        return ["Manifest publication_approved doit être false"]
    audit_seed = manifest.get("seed")
    if type(audit_seed) is not int or not -(2**31) <= audit_seed < 2**31:
        return ["Seed de régénération invalide"]
    route_layouts = ()
    answer_layouts = ()
    if expected_route is not None:
        if demo_pages != len(expected_route.bindings):
            return ["Manifest demo_pages incompatible avec la route C1"]
        expected_activities = [generate(spec, stable_seed(book.book_id, spec.id, audit_seed))
                               for spec in demo_specs(book)]
        if editorial is not None:
            expected_activities = [transform_editorial(a, book, editorial.profile_id)
                                   for a in expected_activities]
        regular, bold = fonts()

        def _trusted_layouts(answer_key: bool):
            """Recompute the trusted composition of one PDF; C2 slot included."""
            layouts = []
            for index, activity in enumerate(expected_activities, 1):
                layout = compose_page(activity, book.data, index=index,
                                      count=len(expected_activities), answer_key=answer_key,
                                      regular=regular, bold=bold, text_width=_measure,
                                      editorial=editorial)
                if expected_placement is not None:
                    layout = placed_composition(
                        layout, expected_placement.anchor_for(activity, demo_index=index),
                        text_width=_measure,
                    )
                layouts.append(layout)
            return tuple(layouts)

        route_layouts = _trusted_layouts(False)
        answer_layouts = _trusted_layouts(True)
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
                    expected_page_artwork = (expected_route.bindings[index].artwork
                                              if expected_route is not None and index < len(expected_route.bindings)
                                              else expected_artwork)
                    images = page.get_image_info(xrefs=True)
                    if len(images) != (1 if expected_page_artwork else 0):
                        errors.append(f"PDF : illustrations manquantes ou inattendues {name} p{index+1}")
                    for image in images:
                        if expected_page_artwork is not None:
                            try:
                                xref = image.get("xref", 0)
                                if not xref:
                                    raise ValueError("Image PDF sans xref vérifiable")
                                pixels = fitz.Pixmap(pdf, xref)
                                expected_digest = (artwork_pixel_digest(expected_page_artwork)
                                                   if expected_route is not None else expected_pixel_digest)
                                if (pixels.width != expected_page_artwork.width or
                                    pixels.height != expected_page_artwork.height or pixels.n != 1 or
                                    pixels.alpha or hashlib.sha256(pixels.samples).hexdigest() != expected_digest):
                                    errors.append(f"PDF : pixels graphiques différents de la source approuvée {name} p{index+1}")
                                bbox = image.get("bbox", ())
                                if expected_route is not None:
                                    if len(bbox) != 4 or not all(isinstance(value, (int, float)) and math.isfinite(value)
                                                                 for value in bbox):
                                        raise ValueError("BBox routée invalide")
                                    x0, y0, x1, y1 = bbox
                                    if x1 <= x0 or y1 <= y0:
                                        raise ValueError("BBox routée vide")
                                    trusted_layouts = (answer_layouts if name == "answer_key"
                                                       else route_layouts)
                                    slot = trusted_layouts[index].companion_slot
                                    scale = min((slot.width - 8) / expected_page_artwork.width,
                                                (slot.height - 6) / expected_page_artwork.height)
                                    width = expected_page_artwork.width * scale
                                    height = expected_page_artwork.height * scale
                                    expected_x = slot.x + (slot.width - width) / 2
                                    expected_y = page.rect.height - (slot.y + (slot.height - height) / 2 + height)
                                    predicted = (expected_x, expected_y, expected_x + width, expected_y + height)
                                    expected_slot = (slot.x, page.rect.height - slot.top,
                                                     slot.right, page.rect.height - slot.y)
                                    if (x0 < expected_slot[0] - .05 or y0 < expected_slot[1] - .05
                                            or x1 > expected_slot[2] + .05 or y1 > expected_slot[3] + .05):
                                        errors.append(f"PDF : illustration hors slot C1 {name} p{index+1}")
                                    if any(abs(actual - predicted_value) > .25
                                           for actual, predicted_value in zip(bbox, predicted, strict=True)):
                                        errors.append(f"PDF : bbox C1 différent du rendu attendu {name} p{index+1}")
                                    dpi_x = 72 * pixels.width / (x1 - x0)
                                    dpi_y = 72 * pixels.height / (y1 - y0)
                                    if min(dpi_x, dpi_y) < 299.99:
                                        errors.append(f"PDF : résolution C1 insuffisante {name} p{index+1}")
                                    # The slot is correct AND empty of other drawn content.
                                    errors.extend(_page_collision_errors(
                                        page, expected_slot, location=f"{name} p{index+1}"))
                                elif (len(bbox) != 4 or bbox[0] < page.rect.width * .60
                                      or bbox[2] > page.rect.width - 25 or bbox[1] < 25
                                      or bbox[3] > page.rect.height * .32):
                                    errors.append(f"PDF : illustration hors zone autorisée {name} p{index+1}")
                            except Exception as exc:
                                errors.append(f"PDF : image non vérifiable {name} p{index+1}: {exc}")
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
    # Fail fast on structural violations; never replay an already-rejected output.
    if not errors:
        # A source-backed replay is mandatory for EVERY build, even placeholder
        # pages. Nothing in the output directory (including its manifest checksums)
        # is an authority about what should have been rendered or reported.
        try:
            replay_seed = manifest.get("seed")
            if type(replay_seed) is not int or not -(2**31) <= replay_seed < 2**31:
                raise ValueError("Seed de régénération invalide")
            with tempfile.TemporaryDirectory(prefix="lafractale-qa-") as trusted_work:
                canonical = Path(trusted_work) / "replay"
                _build_demo_unpublished(
                    book, canonical, seed=replay_seed, illustration_id=illustration_id,
                    illustration_routing=illustration_routing,
                    pip_placement=pip_placement,
                    editorial_profile=editorial_profile,
                    trusted_approvals_sha256=trusted_approvals_sha256,
                )
                expected_manifest = loads_strict((canonical / "manifest.json").read_bytes())
                # Only the wall-clock generation timestamp is non-replayable when
                # SOURCE_DATE_EPOCH is unset. Validate syntax and preserve the
                # original value while strictly comparing every OTHER field.
                submitted_timestamp = manifest.get("generated_at_utc")
                if type(submitted_timestamp) is not str or len(submitted_timestamp) > 48:
                    raise ValueError("Horodatage manifeste invalide")
                parsed = datetime.fromisoformat(submitted_timestamp)
                if (parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0
                        or parsed.isoformat() != submitted_timestamp):
                    raise ValueError("Horodatage manifeste non canonique UTC")
                expected_manifest["generated_at_utc"] = submitted_timestamp
                if manifest != expected_manifest:
                    errors.append("Manifest non conforme au schéma et aux sources régénérées")
                # Strict byte comparison also detects: JSON scene replacement,
                # human/graphic approval forgery, altered markdown, vector overlays,
                # tampered previews, and recomputed self-declared checksums.
                canonical_names = (
                    "interior.pdf", "answer_key.pdf", "activities.json",
                    "quality_report.json", "quality_report.md",
                )
                for filename in canonical_names:
                    actual_path = out / filename
                    if (actual_path.is_symlink() or not actual_path.is_file()
                            or sha256(actual_path) != sha256(canonical / filename)):
                        errors.append(f"PDF différent de la régénération approuvée : {filename}" if filename.endswith(".pdf") else f"Artefact différent de la source approuvée : {filename}")
                actual_previews = out / "previews"
                expected_previews = canonical / "previews"
                if actual_previews.is_symlink() or not actual_previews.is_dir():
                    errors.append("Aperçus absents ou répertoire non autorisé")
                else:
                    expected_names = {item.name for item in expected_previews.iterdir()}
                    actual_names = {item.name for item in actual_previews.iterdir()}
                    if expected_names != actual_names:
                        errors.append("Liste des aperçus différente de la source approuvée")
                    for filename in sorted(expected_names):
                        actual_path = actual_previews / filename
                        if (actual_path.is_symlink() or not actual_path.is_file()
                                or sha256(actual_path) != sha256(expected_previews / filename)):
                            errors.append(f"Aperçu différent de la source approuvée : {filename}")
        except (IllustrationError, ConfigError, ValueError, RuntimeError, OSError,
                TypeError, KeyError) as exc:
            errors.append(f"Régénération de confiance impossible : {exc}")
    previews = out / "previews"
    if previews.is_symlink() or not previews.is_dir():
        errors.append("Dossier d'aperçus absent ou invalide")
    else:
        preview_sources = (("interior", out / "interior.pdf"), ("answer_key", out / "answer_key.pdf")) if expected_route else (("", out / "interior.pdf"),)
        expected_preview_count = manifest.get("demo_pages") * len(preview_sources)
        preview_files = [path for path in previews.iterdir() if path.is_file() and not path.is_symlink()]
        if len(preview_files) != expected_preview_count:
            errors.append("Nombre d'aperçus incorrect")
        else:
            # Preview hashes in an unsigned manifest are NOT authoritative.
            # Compare decoded preview pixels to a fresh render of their own PDF.
            try:
                for label, pdf_path in preview_sources:
                    with fitz.open(pdf_path) as src:
                        for index, page in enumerate(src, 1):
                            name = f"{label}_page_{index:02d}.png" if expected_route else f"page_{index:02d}.png"
                            path = previews / name
                            if path.is_symlink() or not path.is_file() or path.stat().st_size > 12_000_000:
                                raise ValueError(f"Aperçu interdit : {path.name}")
                            expected_preview = page.get_pixmap(matrix=fitz.Matrix(1.4, 1.4), alpha=False)
                            with path.open("rb") as f:
                                header = f.read(24)
                            if (len(header) < 24 or not header.startswith(b"\x89PNG\r\n\x1a\n")
                                    or int.from_bytes(header[16:20], "big") != expected_preview.width
                                    or int.from_bytes(header[20:24], "big") != expected_preview.height):
                                raise ValueError(f"Dimensions/format d'aperçu invalides : {path.name}")
                            actual_preview = fitz.Pixmap(str(path))
                            if (actual_preview.width != expected_preview.width or
                                    actual_preview.height != expected_preview.height or
                                    actual_preview.samples != expected_preview.samples):
                                raise ValueError(f"Pixels d'aperçu différents du PDF : {path.name}")
            except (ValueError, OSError, RuntimeError) as exc:
                errors.append(f"Aperçus non conformes au PDF : {exc}")
    if expected_artwork is not None:
        try:
            verify_approved_artwork(book, expected_artwork,
                trusted_approvals_sha256=trusted_approvals_sha256)
        except (IllustrationError, ConfigError, ValueError) as exc:
            errors.append(f"Illustration modifiée pendant l'audit : {exc}")
    elif expected_route is not None:
        try:
            assert isinstance(trusted_approvals_sha256, str)
            verify_illustration_route(book, expected_route,
                policy_id=expected_route.policy_id,
                trusted_approvals_sha256=trusted_approvals_sha256)
            if expected_placement is not None:
                verify_pip_placement_plan(book, expected_route, expected_placement,
                    policy_id=expected_placement.policy_id,
                    trusted_approvals_sha256=trusted_approvals_sha256)
        except (IllustrationError, ConfigError, ValueError) as exc:
            errors.append(f"Route d'illustrations modifiée pendant l'audit : {exc}")
    auto_checks = report.get("auto_checks")
    if not isinstance(auto_checks, dict):
        errors.append("Rapport qualité auto_checks invalide")
    elif auto_checks.get("pass") is not True:
        errors.append("Contrôles logiques non validés")
    if report.get("ready_for_kdp") is not False:
        errors.append("Démo incorrectement déclarée publiable")
    return errors
