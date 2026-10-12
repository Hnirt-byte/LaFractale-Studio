"""Bounded, read-only loading of the editorial sources.

Every file is opened once through the repository's ``read_bounded`` (no symlink,
regular file, size cap, validated on the opened descriptor) and hashed. Nothing
is ever opened for writing here.
"""
from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lafractale.engine.contracts import read_bounded
from lafractale.scenario_b import ReaderError
from lafractale.security.strict_json import loads_strict

MAX_SOURCE_BYTES = 4_000_000

B3A = "docs/editorial/b3a"
ROLE_CANONICAL = "ACTIVE_CANONICAL"
ROLE_SUPPORT = "ACTIVE_SUPPORTING"
ROLE_ARCHIVE = "HISTORICAL_ARCHIVE_EXCLUDED_FROM_ACTIVE_PLAN"
ROLE_LEGACY = "LEGACY_NON_AUTHORITATIVE"
ROLE_INTEGRITY = "INTEGRITY_REFERENCE"
ROLE_CONFIG = "ENGINE_CONFIGURATION"


@dataclass(frozen=True)
class SourceSpec:
    key: str
    path: str
    role: str
    required: bool
    columns: tuple[str, ...] = ()


SOURCE_SPECS: tuple[SourceSpec, ...] = (
    SourceSpec("plan", f"{B3A}/b3a3/01_chemin_de_fer_scenario_B_56_pages.csv", ROLE_CANONICAL, True,
               ("final_page", "source_old_pages", "final_title", "final_type", "correction_status",
                "demand_level", "status")),
    SourceSpec("instructions", f"{B3A}/b3a3/03_consignes_bilingues_finales_46_pages_scenario_B.csv", ROLE_CANONICAL, True,
               ("final_page", "final_title", "final_type", "final_fr", "final_en", "previous_classification",
                "autonomous_reading_risk", "answer_page")),
    SourceSpec("answers", f"{B3A}/b3a3/02_controle_corriges_scenarios.csv", ROLE_CANONICAL, True,
               ("scenario", "answer_page", "final_activity_page", "title", "correction_type")),
    SourceSpec("grid", f"{B3A}/b3a4/02_grille_relecture_humaine_complete.csv", ROLE_CANONICAL, True,
               ("unit_id", "active_or_archive", "final_page", "unit_type", "title_active", "activity_type",
                "source_completeness", "c4_lock", "answer_page", "fr_exact", "en_exact",
                "fr_review_status", "en_review_status", "bilingual_equivalence_status",
                "age_4_5_mediation_status", "human_review_status", "validator_identity",
                "evidence_reference", "final_status")),
    SourceSpec("evidence_b3a4", f"{B3A}/b3a4/08_validation_evidence.json", ROLE_SUPPORT, False),
    SourceSpec("archive_b3a3", f"{B3A}/b3a3/03_consignes_bilingues_historiques_47_propositions.csv", ROLE_ARCHIVE, False,
               ("source_historical_page", "active_scenario_b_final_page")),
    SourceSpec("archive_b3a4", f"{B3A}/b3a4/03_archive_historique_47_reference.csv", ROLE_ARCHIVE, False,
               ("historical_page", "active_final_page", "archive_status")),
    SourceSpec("manifest_b3a3", f"{B3A}/b3a3/09_integrity_manifest.json", ROLE_INTEGRITY, False),
    SourceSpec("manifest_b3a4", f"{B3A}/b3a4/09_integrity_manifest.json", ROLE_INTEGRITY, False),
    SourceSpec("book_config", "books/halloween_2026/book.yaml", ROLE_CONFIG, False),
    SourceSpec("legacy_plan", "books/halloween_2026/page_plan.csv", ROLE_LEGACY, False,
               ("page", "activity_type")),
    SourceSpec("approvals", "assets/illustrations/approvals.json", ROLE_CONFIG, False),
)


@dataclass(frozen=True)
class LoadedSource:
    spec: SourceSpec
    data: bytes
    sha256: str

    def provenance(self) -> dict[str, Any]:
        return {"key": self.spec.key, "path": self.spec.path, "role": self.spec.role,
                "required": self.spec.required, "bytes": len(self.data), "sha256": self.sha256}


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _decode(data: bytes, label: str) -> str:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ReaderError(f"{label} : UTF-8 invalide ({exc.reason})") from exc
    if "\x00" in text:
        raise ReaderError(f"{label} : octet nul interdit")
    return text


def parse_csv(data: bytes, label: str, columns: tuple[str, ...]) -> list[dict[str, str]]:
    """Parse a CSV strictly: header required, expected columns present, no ragged row."""
    text = _decode(data, label)
    reader = csv.reader(io.StringIO(text, newline=""))
    try:
        header = next(reader)
    except StopIteration:
        raise ReaderError(f"{label} : fichier vide") from None
    if len(set(header)) != len(header):
        raise ReaderError(f"{label} : en-tête avec colonnes dupliquées")
    missing = [c for c in columns if c not in header]
    if missing:
        raise ReaderError(f"{label} : colonne(s) obligatoire(s) absente(s) : {', '.join(missing)}")
    rows: list[dict[str, str]] = []
    try:
        for number, record in enumerate(reader, start=2):
            if not record:
                continue
            if len(record) != len(header):
                raise ReaderError(f"{label} : ligne {number} avec {len(record)} champs (attendu {len(header)})")
            rows.append(dict(zip(header, record)))
    except csv.Error as exc:
        raise ReaderError(f"{label} : CSV invalide ({exc})") from exc
    return rows


def parse_json(data: bytes, label: str) -> Any:
    try:
        return loads_strict(data)
    except ValueError as exc:
        raise ReaderError(f"{label} : JSON strict refusé ({exc})") from exc


def load_sources(root: str | Path) -> tuple[dict[str, LoadedSource], list[dict[str, str]]]:
    """Read every known source under ``root``.

    Returns the loaded sources and a list of absence records for optional sources.
    A missing REQUIRED source raises ReaderError (the analysis cannot proceed).
    """
    base = Path(root)
    loaded: dict[str, LoadedSource] = {}
    absent: list[dict[str, str]] = []
    fatal: list[str] = []
    for spec in SOURCE_SPECS:
        path = base / spec.path
        if not path.exists() and not path.is_symlink():
            if spec.required:
                fatal.append(f"source obligatoire absente : {spec.path}")
            else:
                absent.append({"key": spec.key, "path": spec.path, "role": spec.role})
            continue
        try:
            data = read_bounded(path, MAX_SOURCE_BYTES, label=spec.path, error=ReaderError)
        except ReaderError as exc:
            if spec.required:
                fatal.append(str(exc))
                continue
            raise
        loaded[spec.key] = LoadedSource(spec, data, sha256_hex(data))
    if fatal:
        raise ReaderError(fatal)
    return loaded, absent
