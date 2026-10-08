"""Per-book companion policies with fail-closed catalogue and asset validation.

Only files beneath the project root can be referenced. On POSIX, every path
component is opened relative to the previous directory with O_NOFOLLOW,
preventing symlink parent traversal and symlink swap races during file reads.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path
from typing import Any
import os
import re
import stat
import yaml


class CompanionError(ValueError):
    """Forbidden character use, invalid reference, or modified approved asset."""


@dataclass(frozen=True)
class CompanionProfile:
    status: str
    id: str | None = None
    name: str | None = None
    reference: str | None = None
    sha256: str | None = None
    visual_constraints: tuple[str, ...] = ()
    # Frozen security snapshot captured at load_book, including pending books.
    # Never derive the reserved identities from an independently mutable catalogue.
    catalog_sha256: str = ""
    reserved_names: tuple[str, ...] = ()
    book_id: str = ""

    @property
    def selected(self) -> bool:
        return self.status == "approved_reference"

    @property
    def render_name(self) -> str | None:
        """Never expose a name as a renderer hint while selection is pending."""
        return self.name if self.selected else None


def _parts(raw_path: str) -> tuple[str, ...]:
    """Validate raw components BEFORE any path normalization can erase '..'."""
    if (not isinstance(raw_path, str) or not raw_path or "\\" in raw_path
            or "\x00" in raw_path or raw_path.startswith("/")):
        raise CompanionError("Chemin de référence compagnon invalide")
    parts = tuple(raw_path.split("/"))
    if any(part in ("", ".", "..") or ":" in part for part in parts):
        raise CompanionError("Traversée de namespace ou segment de chemin interdit")
    return parts


def _read_file(root: Path, reference: str, *, max_bytes: int = 40_000_000) -> bytes:
    """Read a regular project file without following symlinks at any depth.

    On platforms lacking openat-style operations, reject rather than silently
    downgrade the protection. The supported CI/production environment is Linux.
    """
    components = _parts(reference)
    if os.open not in os.supports_dir_fd or not hasattr(os, "O_NOFOLLOW"):
        raise CompanionError("Lecture sûre des compagnons nécessite openat/O_NOFOLLOW")
    try:
        root_path = root.resolve(strict=True)
        flags_dir = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        parent_fd = os.open(root_path, flags_dir)
        try:
            for component in components[:-1]:
                next_fd = os.open(component, flags_dir, dir_fd=parent_fd)
                os.close(parent_fd)
                parent_fd = next_fd
            flags_file = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0)
            file_fd = os.open(components[-1], flags_file, dir_fd=parent_fd)
            try:
                info = os.fstat(file_fd)
                if not stat.S_ISREG(info.st_mode) or info.st_size > max_bytes:
                    raise CompanionError("Fichier compagnon non régulier ou trop volumineux")
                with os.fdopen(file_fd, "rb", closefd=False) as stream:
                    data = stream.read(max_bytes + 1)
                if len(data) > max_bytes:
                    raise CompanionError("Fichier compagnon trop volumineux")
                return data
            finally:
                os.close(file_fd)
        finally:
            os.close(parent_fd)
    except OSError as exc:
        if isinstance(exc, FileNotFoundError) and reference.startswith("assets/characters/"):
            raise CompanionError(f"Asset officiel absent : {reference}") from exc
        raise CompanionError(f"Fichier compagnon absent, symlink ou chemin interdit : {reference} ({exc})") from exc


def _catalog_snapshot(root: Path) -> tuple[dict[str, Any], str, tuple[str, ...]]:
    """Securely read the exact catalogue bytes and pin every reserved identity.

    Hash *raw bytes*, not a mutable parsed YAML dictionary. A post-load edit,
    removal, addition or cosmetic rewrite invalidates a Book in every status.
    """
    try:
        content = _read_file(root, "assets/companions/catalog.yaml", max_bytes=1_000_000)
        data = yaml.safe_load(content.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise CompanionError(f"Catalogue de compagnons invalide : {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("characters"), dict):
        raise CompanionError("Catalogue de compagnons invalide : characters requis")
    characters = data["characters"]
    names = []
    for identity, entry in characters.items():
        if (not isinstance(identity, str) or not re.fullmatch(r"[a-z][a-z0-9_-]*", identity)
                or not isinstance(entry, dict) or not isinstance(entry.get("name"), str)
                or not entry["name"].strip()):
            raise CompanionError("Identité de personnage invalide dans le catalogue")
        names.append(entry["name"].strip())
    if len({name.casefold() for name in names}) != len(names):
        raise CompanionError("Noms de compagnons dupliqués dans le catalogue")
    return characters, sha256(content).hexdigest(), tuple(sorted(names, key=str.casefold))


def _validated_entry(root: Path, companion_id: str, entry: Any, book_id: str) -> CompanionProfile:
    if not isinstance(entry, dict):
        raise CompanionError(f"Compagnon non approuvé dans le catalogue : {companion_id}")
    allowed = entry.get("allowed_book_ids")
    if not isinstance(allowed, list) or not allowed or any(not isinstance(v, str) or not v for v in allowed):
        raise CompanionError("allowed_book_ids du compagnon invalide")
    if book_id not in allowed:
        raise CompanionError(f"Compagnon {companion_id} interdit pour le livre {book_id}")
    name = entry.get("name")
    if not isinstance(name, str) or not name.strip():
        raise CompanionError("Nom officiel du compagnon invalide")
    reference = entry.get("approved_reference")
    parts = _parts(reference)
    if len(parts) < 4 or parts[:3] != ("assets", "characters", companion_id):
        raise CompanionError("Référence compagnon dans un autre dossier de personnage")
    digest = entry.get("sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise CompanionError("SHA-256 de référence compagnon invalide")
    if sha256(_read_file(root, reference)).hexdigest() != digest:
        raise CompanionError(f"SHA-256 de la référence compagnon incorrect : {companion_id}")
    constraints = entry.get("visual_constraints", [])
    if not isinstance(constraints, list) or any(not isinstance(x, str) or not x.strip() for x in constraints):
        raise CompanionError("Contraintes graphiques du compagnon invalides")
    if entry.get("reference_only") is not True:
        raise CompanionError("La référence approuvée doit rester en usage REFERENCE_ONLY pour V0.2-A")
    return CompanionProfile("approved_reference", companion_id, name, reference, digest, tuple(constraints))


def resolve_companion(root: Path, book_id: str, raw: Any) -> CompanionProfile:
    if not isinstance(raw, dict):
        raise CompanionError("companion doit être une table")
    status = raw.get("status")
    if status == "pending_selection":
        if set(raw) != {"status"}:
            raise CompanionError("companion en attente : ne définir ni id ni asset non approuvé")
        characters, catalog_digest, reserved_names = _catalog_snapshot(root)
        # Pending books still bind to ALL currently reserved names and catalogue bytes.
        return CompanionProfile(status="pending_selection", catalog_sha256=catalog_digest,
                                reserved_names=reserved_names, book_id=book_id)
    if status != "approved_reference" or set(raw) != {"status", "id"}:
        raise CompanionError("companion exige status approved_reference + id, ou status pending_selection")
    companion_id = raw.get("id")
    if not isinstance(companion_id, str) or not re.fullmatch(r"[a-z][a-z0-9_-]*", companion_id):
        raise CompanionError("companion.id invalide")
    characters, catalog_digest, reserved_names = _catalog_snapshot(root)
    selected = _validated_entry(root, companion_id, characters.get(companion_id), book_id)
    return replace(selected, catalog_sha256=catalog_digest,
                   reserved_names=reserved_names, book_id=book_id)


def verify_companion_integrity(root: Path, book_id: str, profile: CompanionProfile) -> None:
    """Check frozen catalogue snapshot for ALL books, then selected asset bytes.

    If any bytes of the catalogue changed since load_book, reject before reading
    identities from the altered catalogue. Never allow post-load catalogue edits
    to erase previously reserved names for pending_selection.
    """
    # CompanionProfile is a transport object, not a security capability.
    # dataclasses.replace() can forge *any* field, even on a frozen instance.
    if type(profile) is not CompanionProfile or not profile.catalog_sha256 or profile.book_id != book_id:
        raise CompanionError("Contexte du catalogue compagnon invalide ou altéré")
    characters, catalog_digest, reserved_names = _catalog_snapshot(root)
    if catalog_digest != profile.catalog_sha256 or reserved_names != profile.reserved_names:
        raise CompanionError("catalogue de compagnons modifié depuis le chargement")
    if profile.status == "pending_selection":
        # Compare the ENTIRE canonical pending profile, not only its SHA.
        # Every optional identity/asset field must be None and constraints empty.
        expected = CompanionProfile(status="pending_selection", catalog_sha256=catalog_digest,
                                    reserved_names=reserved_names, book_id=book_id)
        if profile != expected:
            raise CompanionError("Profil pending_selection non canonique ou falsifié")
    elif profile.status == "approved_reference":
        current = _validated_entry(root, profile.id, characters.get(profile.id), book_id)
        expected = replace(current, catalog_sha256=catalog_digest,
                           reserved_names=reserved_names, book_id=book_id)
        if profile != expected:
            raise CompanionError("Compagnon approuvé modifié depuis le chargement")
    else:
        raise CompanionError("Statut compagnon invalide ou falsifié")


def _all_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from _all_strings(k)
            yield from _all_strings(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from _all_strings(v)


def verify_companion_text(root: Path, profile: CompanionProfile, book_data: Any, plan: Any) -> None:
    """Validate editorial text against frozen identities, not mutable catalogue.

    The integrity check is required *on each use*, including at manifest time.
    Any post-load change to a pending book's catalogue fails closed first.
    """
    if not isinstance(book_data, dict) or book_data.get("book_id") != profile.book_id:
        raise CompanionError("Identité du livre modifiée depuis le chargement")
    verify_companion_integrity(root, profile.book_id, profile)
    # A mutable in-memory YAML mapping must not silently disagree with the
    # validated profile. Enforce the exact schema at every trust boundary.
    expected_binding = ({"status": "approved_reference", "id": profile.id}
                        if profile.selected else {"status": "pending_selection"})
    if book_data.get("companion") != expected_binding:
        raise CompanionError("Déclaration compagnon du livre modifiée ou non canonique")
    # A pending profile may NEVER exempt any reserved name, even when forged.
    permitted_name = profile.name.casefold() if profile.selected else None
    prohibited = [name for name in profile.reserved_names
                  if permitted_name is None or name.casefold() != permitted_name]
    for value in (*_all_strings(book_data), *_all_strings(plan)):
        for name in prohibited:
            if re.search(rf"(?<!\w){re.escape(name)}(?!\w)", value, flags=re.IGNORECASE):
                raise CompanionError(f"Compagnon non autorisé dans le texte éditorial : {name}")
