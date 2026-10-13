"""B3-B.3a — canonical, immutable, traceable contract of the 56 pages of scenario B.

``load_pages(root)`` builds one :class:`PageRecord` per page from the ACTIVE editorial sources
(B3-A.3 plan / instructions / answer control, B3-A.4 review grid), through the bounded loader of
``scenario_b.sources`` (B3-B.2). Nothing is written, rendered or generated.

Two levels are kept strictly apart and can never be merged:

* ``readable``              : derived ONLY from the absence of blocking issues (the data can be read
                              and its structure is unambiguous). It says nothing about validation.
* ``production_authorized`` : a constant ``False`` of the code. It is not a field, not a constructor
                              argument, and nothing read from a source, CLI argument or environment
                              variable can change it.

The editorial statuses of the grid are copied literally; an unproven or inconsistent claim makes the
page NOT readable, it never upgrades anything. No adapter to the synthetic B3-B.1 ``SpecSet`` exists
here, and ``legacy_plan`` (``books/halloween_2026/page_plan.csv``) is never parsed or used.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, fields, is_dataclass
from pathlib import Path
from typing import Any, Final

from lafractale.scenario_b import GATES, ReaderError
from lafractale.scenario_b.analyzer import (
    _CORR_ID, ACTIVE_SCOPE, ACTIVITY_PAGES, ANSWER_DISTRIBUTION, ANSWER_PAGES, CLOSING_PAGE, CLOSING_UNITS,
    CREATIVE_BREATHING, GRID_TOTAL, LEXICON_PAGE, LEXICON_PAIRS, OPENING_PAGES, TOTAL_PAGES,
)
from lafractale.scenario_b.capabilities import FREE_TYPES, LAYOUT_TYPES
from lafractale.scenario_b.sources import LoadedSource, load_sources, parse_csv, sha256_hex
from lafractale.security.text import UnsafeEditorialText, canonical_text

PAGES_SCHEMA: Final = "lafractale-scenario-b-pages-v1"
PAGES_KIND: Final = "READ_ONLY_PAGE_CONTRACT_NON_PRODUCTION"
PAGES_VERSION: Final = "b3b3a-pages-1.0"
#: Constant of the code (never read from a source, argument or environment).
PRODUCTION_AUTHORIZED: Final = False
READY_FOR_KDP: Final = False

BLOCKING, NON_BLOCKING = "BLOCKING", "NON_BLOCKING"
READABLE, NOT_READABLE = "READABLE", "NOT_READABLE"

#: Used sources (the legacy page plan, archives, evidence and approvals are NOT used).
USED_SOURCES: Final = ("plan", "instructions", "answers", "grid")
FINAL_STATUSES: Final = frozenset({"NOT_VALIDATED", "BLOCKED_BY_SOURCE", "VALIDATED"})
REVIEW_STATUSES: Final = frozenset({"NOT_REVIEWED", "VALIDATED"})
REVIEW_FIELDS: Final = ("fr_review_status", "en_review_status", "bilingual_equivalence_status",
                        "age_4_5_mediation_status", "human_review_status")
CLOSING_TYPES: Final = ("congratulations", "diploma_label", "name_label", "drawing_instruction", "closing", "thanks")
UNIT_TYPES_BY_NATURE: Final = {
    "opening": ("opening_text",),
    "activity": ("activity_instruction",),
    "creative": ("activity_instruction",),
    "answers": ("answer_entry",),
    "lexicon": ("lexicon_pair",),
    "closing": CLOSING_TYPES,
}
_AUTH_COLUMN = re.compile(r"authori[sz]|production", re.IGNORECASE)


# --------------------------------------------------------------------------------------------
# immutable model
# --------------------------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class Provenance:
    """Where a value comes from. ``line`` is the physical line, or None when it cannot be trusted."""
    source: str
    path: str
    sha256: str
    line: int | None
    columns: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Issue:
    code: str
    severity: str
    message: str
    pages: tuple[int, ...] = ()
    sources: tuple[str, ...] = ()

    @property
    def blocking(self) -> bool:
        return self.severity == BLOCKING


@dataclass(frozen=True, slots=True)
class UnitRecord:
    """One B3-A.4 grid unit; every status is the literal text of the grid."""
    unit_id: str
    unit_type: str
    final_page: int
    title_active: str
    activity_type: str
    source_completeness: str
    c4_lock: str
    answer_page: int | None
    fr_exact: str
    en_exact: str
    fr_review_status: str
    en_review_status: str
    bilingual_equivalence_status: str
    age_4_5_mediation_status: str
    human_review_status: str
    validator_identity: str
    evidence_reference: str
    final_status: str
    evidence_complete: bool
    provenance: Provenance


@dataclass(frozen=True, slots=True)
class AnswerLink:
    """Answer requirement of an activity page, or one entry of an answer page."""
    source_page: int
    answer_page: int
    kind: str
    unit_id: str | None
    status: str
    provenance: tuple[Provenance, ...]


@dataclass(frozen=True, slots=True)
class PageRecord:
    page: int
    title: str | None
    nature: str
    content_type: str | None
    mechanic: str | None
    plan_status: str | None
    demand_level: str | None
    plan_correction_status: str | None
    c4_locked: bool
    instruction_fr: str | None
    instruction_en: str | None
    answer_requirement: str
    answer: AnswerLink | None
    answer_entries: tuple[AnswerLink, ...]
    units: tuple[UnitRecord, ...]
    provenance: tuple[Provenance, ...]
    issues: tuple[Issue, ...]

    @property
    def readability(self) -> str:
        return NOT_READABLE if any(i.blocking for i in self.issues) else READABLE

    @property
    def readable(self) -> bool:
        return self.readability == READABLE

    @property
    def production_authorized(self) -> bool:
        return PRODUCTION_AUTHORIZED

    def to_dict(self) -> dict[str, Any]:
        data = _plain(self)
        data["readability"] = self.readability
        data["production_authorized"] = False
        return data


@dataclass(frozen=True, slots=True)
class ScenarioBPages:
    pages: tuple[PageRecord, ...]
    sources: tuple[Provenance, ...]
    sources_aggregate_sha256: str
    issues: tuple[Issue, ...]

    def page(self, number: int) -> PageRecord:
        if isinstance(number, bool) or not isinstance(number, int) or not 1 <= number <= len(self.pages):
            raise KeyError(f"page inconnue : {number!r}")
        return self.pages[number - 1]

    @property
    def readable_pages(self) -> tuple[int, ...]:
        return tuple(p.page for p in self.pages if p.readable)

    @property
    def all_readable(self) -> bool:
        return len(self.readable_pages) == len(self.pages) and not any(i.blocking for i in self.issues)

    @property
    def production_authorized(self) -> bool:
        return PRODUCTION_AUTHORIZED

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": PAGES_SCHEMA, "kind": PAGES_KIND, "version": PAGES_VERSION,
            "gates": dict(GATES), "ready_for_kdp": READY_FOR_KDP, "production_authorized": False,
            "all_readable": self.all_readable, "readable_pages": list(self.readable_pages),
            "sources": [_plain(s) for s in self.sources],
            "sources_aggregate_sha256": self.sources_aggregate_sha256,
            "issues": [_plain(i) for i in self.issues],
            "pages": [p.to_dict() for p in self.pages],
        }

    def to_canonical_json(self) -> str:
        """Deterministic serialisation (sorted keys, no locale/time dependence)."""
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _plain(value: Any) -> Any:
    """Fresh plain copy (dict/list/scalars) of a frozen structure: mutating it cannot reach the record."""
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: _plain(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, tuple):
        return [_plain(v) for v in value]
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"type non immuable ou inattendu dans le contrat : {type(value).__name__}")


# --------------------------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------------------------
def _int(value: str) -> int | None:
    value = value.strip()
    return int(value) if value.isdigit() and value.isascii() else None


def _prov(src: LoadedSource, row_index: int | None, lines: list[int | None], *names: str) -> Provenance:
    line = lines[row_index] if row_index is not None else None
    return Provenance(src.spec.key, src.spec.path, src.sha256, line, tuple(names))


def _row_lines(src: LoadedSource, rows: list[dict[str, str]]) -> list[int | None]:
    """Physical line of each parsed row, only when the file is one-record-per-line (else None).

    No second parser: the rows come from ``parse_csv``; here we only check that the physical line
    count is consistent with the record count, otherwise a line number would be misleading.
    """
    text = src.data.decode("utf-8-sig")
    physical = text.split("\n")
    if physical and physical[-1] == "":
        physical.pop()
    if len(physical) != len(rows) + 1:
        return [None] * len(rows)
    return [index + 2 for index in range(len(rows))]


class _Collector:
    def __init__(self) -> None:
        self.global_issues: list[Issue] = []
        self.by_page: dict[int, list[Issue]] = {p: [] for p in range(1, TOTAL_PAGES + 1)}

    def add(self, code: str, severity: str, message: str, pages: tuple[int, ...] = (), sources: tuple[str, ...] = ()) -> None:
        issue = Issue(code, severity, message, tuple(sorted(set(pages))), tuple(sources))
        targets = [p for p in set(pages) if p in self.by_page]
        if not targets or len(targets) != len(set(pages)):
            self.global_issues.append(issue)
        for page in targets:
            self.by_page[page].append(issue)


def _nature(page: int, content_type: str | None) -> str:
    if content_type is None:
        return "unknown"
    if content_type in LAYOUT_TYPES:
        return {"front_matter": "opening", "answers": "answers", "glossary": "lexicon", "closing": "closing"}[LAYOUT_TYPES[content_type]]
    if content_type in FREE_TYPES:
        return "creative" if content_type == "creative_color" else "activity"
    return "activity"


def _expected_nature(page: int) -> str:
    if page in OPENING_PAGES:
        return "opening"
    if page in ACTIVITY_PAGES:
        return "activity"
    if page in ANSWER_PAGES:
        return "answers"
    return "lexicon" if page == LEXICON_PAGE else "closing"


def load_pages(root: str | Path) -> ScenarioBPages:
    """Load the 56-page contract from the active sources under ``root`` (read-only, deterministic).

    Structurally unreadable sources (missing, symlink, malformed CSV, invalid UTF-8) raise
    ``ReaderError``: no partial contract is returned. Contradictions are issues: BLOCKING ones remove
    the READABLE state of the pages they make ambiguous, NON_BLOCKING ones are only documented.
    """
    loaded, _absent = load_sources(root)
    src = {key: loaded[key] for key in USED_SOURCES}
    tables = {key: parse_csv(s.data, s.spec.path, s.spec.columns) for key, s in src.items()}
    lines = {key: _row_lines(s, tables[key]) for key, s in src.items()}
    paths = {key: s.spec.path for key, s in src.items()}
    issues = _Collector()

    for key, s in src.items():
        extra = [c for c in tables[key][0] if _AUTH_COLUMN.search(c)] if tables[key] else []
        if extra:
            issues.add("AUTHORIZATION_COLUMN_IGNORED", NON_BLOCKING,
                       f"Colonne(s) {extra} ignorée(s) dans {paths[key]} : aucune source ne peut autoriser la production.",
                       sources=(paths[key],))

    # ---- plan : one row per page ---------------------------------------------------------
    plan: dict[int, int] = {}
    plan_dup: set[int] = set()
    for index, row in enumerate(tables["plan"]):
        number = _int(row["final_page"])
        if number is None or not 1 <= number <= TOTAL_PAGES:
            issues.add("PLAN_PAGE_INVALID", BLOCKING, f"Numéro de page invalide dans le plan : {row['final_page']!r}.", sources=(paths["plan"],))
        elif number in plan:
            plan_dup.add(number)
        else:
            plan[number] = index
    for number in sorted(plan_dup):
        issues.add("PLAN_PAGE_DUPLICATED", BLOCKING, f"Page p.{number:02d} dupliquée dans le plan : identité ambiguë.", (number,), (paths["plan"],))
    for number in range(1, TOTAL_PAGES + 1):
        if number not in plan:
            issues.add("PLAN_PAGE_MISSING", BLOCKING, f"Page p.{number:02d} absente du plan actif.", (number,), (paths["plan"],))
    plan_row = {p: tables["plan"][i] for p, i in plan.items() if p not in plan_dup}

    # ---- instructions --------------------------------------------------------------------
    instr: dict[int, int] = {}
    instr_dup: set[int] = set()
    for index, row in enumerate(tables["instructions"]):
        number = _int(row["final_page"])
        if number is None or number not in ACTIVITY_PAGES:
            issues.add("INSTRUCTION_PAGE_INVALID", BLOCKING,
                       f"Consigne hors p.03-48 ou page non entière : {row['final_page']!r}.",
                       (number,) if number else (), (paths["instructions"],))
        elif number in instr:
            instr_dup.add(number)
        else:
            instr[number] = index
    for number in sorted(instr_dup):
        issues.add("INSTRUCTION_PAGE_DUPLICATED", BLOCKING, f"Consigne dupliquée pour p.{number:02d}.", (number,), (paths["instructions"],))
    instr_row = {p: tables["instructions"][i] for p, i in instr.items() if p not in instr_dup}

    # ---- answer control (scenario B) -----------------------------------------------------
    corr: dict[int, int] = {}
    corr_dup: set[int] = set()
    for index, row in enumerate(tables["answers"]):
        if row["scenario"].strip() != "B":
            continue
        number = _int(row["final_activity_page"])
        if number is None or number not in ACTIVITY_PAGES:
            issues.add("ANSWER_SOURCE_PAGE_INVALID", BLOCKING,
                       f"Page source de corrigé hors p.03-48 : {row['final_activity_page']!r}.",
                       (number,) if number else (), (paths["answers"],))
        elif number in corr:
            corr_dup.add(number)
        else:
            corr[number] = index
    for number in sorted(corr_dup):
        issues.add("ANSWER_DUPLICATED", BLOCKING, f"Plusieurs corrigés pour p.{number:02d} : corrigé ambigu.", (number,), (paths["answers"],))
    corr_row = {p: tables["answers"][i] for p, i in corr.items() if p not in corr_dup}

    # ---- grid units ----------------------------------------------------------------------
    id_count = Counter(r["unit_id"] for r in tables["grid"])
    unit_rows: dict[int, list[int]] = {p: [] for p in range(1, TOTAL_PAGES + 1)}
    for index, row in enumerate(tables["grid"]):
        number = _int(row["final_page"])
        if id_count[row["unit_id"]] > 1:
            issues.add("UNIT_DUPLICATED", BLOCKING, f"Unité {row['unit_id']!r} dupliquée.",
                       (number,) if number and 1 <= number <= TOTAL_PAGES else (), (paths["grid"],))
            if number and 1 <= number <= TOTAL_PAGES:
                unit_rows[number].append(index)
            continue
        if number is None or not 1 <= number <= TOTAL_PAGES:
            issues.add("UNIT_ORPHAN", BLOCKING, f"Unité {row['unit_id']!r} rattachée à une page invalide : {row['final_page']!r}.",
                       sources=(paths["grid"],))
            continue
        unit_rows[number].append(index)
        if row["active_or_archive"] != ACTIVE_SCOPE:
            issues.add("UNIT_NOT_ACTIVE", BLOCKING, f"Unité {row['unit_id']!r} hors du périmètre actif.", (number,), (paths["grid"],))
    types = Counter(r["unit_type"] for r in tables["grid"])
    closing_count = sum(types.get(t, 0) for t in CLOSING_TYPES)
    if len(tables["grid"]) != GRID_TOTAL:
        issues.add("GRID_TOTAL", BLOCKING, f"Grille : {len(tables['grid'])} unités au lieu de {GRID_TOTAL}.", sources=(paths["grid"],))
    for unit_type, expected in (("activity_instruction", 46), ("answer_entry", 31), ("lexicon_pair", LEXICON_PAIRS), ("opening_text", 2)):
        if types.get(unit_type, 0) != expected:
            issues.add("GRID_BREAKDOWN", BLOCKING, f"Grille : {types.get(unit_type, 0)} unité(s) {unit_type} au lieu de {expected}.",
                       sources=(paths["grid"],))
    if closing_count != CLOSING_UNITS:
        issues.add("GRID_BREAKDOWN", BLOCKING, f"Grille : {closing_count} unité(s) de p.56 au lieu de {CLOSING_UNITS}.", sources=(paths["grid"],))

    units: dict[int, tuple[UnitRecord, ...]] = {}
    grid_answer_entry: dict[int, tuple[UnitRecord, int]] = {}
    for number, indexes in unit_rows.items():
        built: list[UnitRecord] = []
        for index in indexes:
            row = tables["grid"][index]
            unit = _unit(row, number, _prov(src["grid"], index, lines["grid"], "unit_id", "final_status"), issues, paths["grid"])
            built.append(unit)
            match = _CORR_ID.search(unit.unit_id)
            if unit.unit_type == "answer_entry" and match:
                source_page = int(match.group(1))
                if source_page in grid_answer_entry:
                    issues.add("ANSWER_ENTRY_DUPLICATED", BLOCKING, f"Entrée de corrigé dupliquée pour p.{source_page:02d}.",
                               (source_page, number), (paths["grid"],))
                grid_answer_entry[source_page] = (unit, index)
        units[number] = tuple(built)

    # ---- cross-checks by activity page -----------------------------------------------------
    per_answer_page: Counter[int] = Counter()
    links: dict[int, AnswerLink] = {}
    for number in sorted(corr_row):
        row = corr_row[number]
        answer_page = _int(row["answer_page"])
        if answer_page is None or answer_page not in ANSWER_PAGES:
            issues.add("ANSWER_PAGE_INVALID", BLOCKING, f"Page de corrigé invalide pour p.{number:02d} : {row['answer_page']!r}.",
                       (number,), (paths["answers"],))
            continue
        plan_type = plan_row[number]["final_type"].strip() if number in plan_row else None
        if plan_type in FREE_TYPES or number in CREATIVE_BREATHING:
            issues.add("ANSWER_ON_FREE_PAGE", BLOCKING, f"p.{number:02d} (création libre) ne peut pas avoir de corrigé.",
                       (number, answer_page), (paths["answers"],))
            continue
        if number in plan_row and row["title"] != plan_row[number]["final_title"]:
            issues.add("ANSWER_TITLE_MISMATCH", BLOCKING, f"Titre du corrigé ≠ titre du plan pour p.{number:02d}.",
                       (number, answer_page), (paths["answers"], paths["plan"]))
        if number in instr_row and _int(instr_row[number]["answer_page"]) != answer_page:
            issues.add("ANSWER_PAGE_MISMATCH", BLOCKING,
                       f"Page de corrigé p.{number:02d} : contrôle={answer_page}, consignes={instr_row[number]['answer_page']!r}.",
                       (number, answer_page), (paths["answers"], paths["instructions"]))
        entry = grid_answer_entry.get(number)
        unit_id: str | None = None
        if entry is None:
            issues.add("ANSWER_ENTRY_MISSING", BLOCKING, f"Aucune entrée de grille pour le corrigé de p.{number:02d}.",
                       (number, answer_page), (paths["grid"],))
        else:
            unit, _ = entry
            unit_id = unit.unit_id
            if unit.final_page != answer_page:
                issues.add("ANSWER_ENTRY_MISPLACED", BLOCKING,
                           f"Entrée {unit.unit_id} sur p.{unit.final_page} au lieu de p.{answer_page}.",
                           (number, answer_page, unit.final_page), (paths["grid"], paths["answers"]))
        plan_correction = plan_row[number]["correction_status"].strip() if number in plan_row else ""
        if plan_correction == "libre":
            issues.add("ANSWER_VS_PLAN_FREE", BLOCKING, f"Le plan déclare p.{number:02d} « libre » mais un corrigé existe.",
                       (number, answer_page), (paths["plan"], paths["answers"]))
        status = next((u.final_status for u in units[answer_page] if u.unit_id == unit_id), "MISSING_MAPPING")
        per_answer_page[answer_page] += 1
        links[number] = AnswerLink(number, answer_page, row["correction_type"].strip(), unit_id, status,
                                   (_prov(src["answers"], corr[number], lines["answers"], "answer_page", "correction_type"),)
                                   + ((_prov(src["grid"], entry[1], lines["grid"], "unit_id", "answer_page"),) if entry else ()))
    for number in sorted(set(grid_answer_entry) - set(corr_row)):
        issues.add("ANSWER_ENTRY_ORPHAN", BLOCKING, f"Entrée de corrigé de la grille sans contrôle des corrigés pour p.{number:02d}.",
                   (number, grid_answer_entry[number][0].final_page), (paths["grid"], paths["answers"]))
    for number in sorted(plan_row):
        if plan_row[number]["correction_status"].strip() in ("graphique", "chiffre") and number not in corr_row and number not in corr_dup:
            issues.add("PLAN_ANSWER_NOT_LISTED", BLOCKING, f"Le plan annonce un corrigé pour p.{number:02d} absent du contrôle des corrigés.",
                       (number,), (paths["plan"], paths["answers"]))
    distribution = tuple(per_answer_page.get(p, 0) for p in ANSWER_PAGES)
    if len(corr_row) != 31 or distribution != ANSWER_DISTRIBUTION:
        bad = tuple(p for p, got, want in zip(ANSWER_PAGES, distribution, ANSWER_DISTRIBUTION) if got != want)
        issues.add("ANSWER_DISTRIBUTION", BLOCKING,
                   f"Corrigés : {len(corr_row)} unités, répartition {list(distribution)} au lieu de 31 / {list(ANSWER_DISTRIBUTION)}.",
                   bad, (paths["answers"],))
    unfilled = sorted(p for p in links if p in plan_row and not plan_row[p]["correction_status"].strip())
    if unfilled:
        issues.add("PLAN_CORRECTION_STATUS_EMPTY", NON_BLOCKING,
                   f"Le plan ne renseigne pas correction_status pour {len(unfilled)} page(s) qui ont un corrigé ; "
                   "le contrôle des corrigés fait foi.", sources=(paths["plan"], paths["answers"]))

    # ---- build records ---------------------------------------------------------------------
    # Phase 1 collects every issue (some are cross-page); phase 2 freezes the records.
    drafts = {n: _draft(n, plan, plan_row, instr, instr_row, links, units, lines, src, issues, paths, instr_dup)
              for n in range(1, TOTAL_PAGES + 1)}
    records = [PageRecord(issues=tuple(issues.by_page[n]), **drafts[n]) for n in range(1, TOTAL_PAGES + 1)]
    sources = tuple(Provenance(k, loaded[k].spec.path, loaded[k].sha256, None) for k in USED_SOURCES)
    aggregate = sha256_hex("".join(f"{k}:{loaded[k].sha256}\n" for k in sorted(USED_SOURCES)).encode())
    result = ScenarioBPages(tuple(records), sources, aggregate, tuple(issues.global_issues))
    _ = result.to_canonical_json()  # fails now, not later, on any non-immutable/unexpected value
    return result


def _unit(row: dict[str, str], page: int, provenance: Provenance, issues: _Collector, path: str) -> UnitRecord:
    evidence = bool(row["validator_identity"].strip() and row["evidence_reference"].strip())
    statuses = {"final_status": row["final_status"], **{name: row[name] for name in REVIEW_FIELDS}}
    uid = row["unit_id"]
    for name, value in statuses.items():
        known = FINAL_STATUSES if name == "final_status" else REVIEW_STATUSES
        if value not in known:
            issues.add("UNIT_STATUS_UNKNOWN", BLOCKING, f"{uid} : {name}={value!r} hors du vocabulaire B3-A.4 (statut non reconnu).",
                       (page,), (path,))
    claimed = any(v == "VALIDATED" for v in statuses.values())
    if claimed and not evidence:
        issues.add("VALIDATION_WITHOUT_EVIDENCE", BLOCKING,
                   f"{uid} : statut VALIDATED sans identité de validateur ni référence de preuve (revendication non reconnue).",
                   (page,), (path,))
    if row["final_status"] == "VALIDATED" and any(row[name] != "VALIDATED" for name in REVIEW_FIELDS):
        issues.add("VALIDATION_INCONSISTENT", BLOCKING, f"{uid} : final_status=VALIDATED sans validation complète des cinq revues.",
                   (page,), (path,))
    return UnitRecord(
        unit_id=uid, unit_type=row["unit_type"], final_page=page, title_active=row["title_active"],
        activity_type=row["activity_type"], source_completeness=row["source_completeness"], c4_lock=row["c4_lock"],
        answer_page=_int(row["answer_page"]), fr_exact=row["fr_exact"], en_exact=row["en_exact"],
        fr_review_status=row["fr_review_status"], en_review_status=row["en_review_status"],
        bilingual_equivalence_status=row["bilingual_equivalence_status"],
        age_4_5_mediation_status=row["age_4_5_mediation_status"], human_review_status=row["human_review_status"],
        validator_identity=row["validator_identity"], evidence_reference=row["evidence_reference"],
        final_status=row["final_status"], evidence_complete=evidence, provenance=provenance)


def _draft(number, plan, plan_row, instr, instr_row, links, units, lines, src, issues, paths, instr_dup) -> dict[str, Any]:
    row = plan_row.get(number)
    provenance: list[Provenance] = []
    title = content_type = plan_status = demand = plan_correction = None
    if row is not None:
        title, content_type = row["final_title"], row["final_type"].strip()
        plan_status, demand, plan_correction = row["status"], row["demand_level"], row["correction_status"]
        provenance.append(_prov(src["plan"], plan[number], lines["plan"], "final_page", "final_title", "final_type",
                                "correction_status", "demand_level", "status"))
        for column, value in (("final_title", title),):
            try:
                canonical_text(value, location=f"p.{number} {column}")
            except UnsafeEditorialText as exc:
                issues.add("UNICODE_POLICY", BLOCKING, str(exc), (number,), (paths["plan"],))
        if row.get("scenario", "B").strip() != "B":
            issues.add("PLAN_SCENARIO", BLOCKING, f"p.{number:02d} : ligne du plan hors scénario B.", (number,), (paths["plan"],))
        if not title.strip() or not content_type:
            issues.add("PLAN_ROW_INCOMPLETE", BLOCKING, f"p.{number:02d} : titre ou type vide.", (number,), (paths["plan"],))
    nature = _nature(number, content_type)
    expected = _expected_nature(number)
    if row is not None and nature != expected and not (expected == "activity" and nature == "creative"):
        issues.add("PAGE_NATURE_MISMATCH", BLOCKING, f"p.{number:02d} : type {content_type!r} incompatible avec la structure attendue ({expected}).",
                   (number,), (paths["plan"],))
    if number in CREATIVE_BREATHING and content_type not in (None, "creative_color"):
        issues.add("CREATIVE_BREATHING_TYPE", BLOCKING, f"p.{number:02d} doit être une respiration créative.", (number,), (paths["plan"],))
    mechanic = content_type if nature in ("activity", "creative") else None

    fr = en = None
    irow = instr_row.get(number)
    if number in ACTIVITY_PAGES:
        if irow is None:
            if number not in instr_dup:
                issues.add("INSTRUCTION_MISSING", BLOCKING, f"Consigne FR/EN absente pour p.{number:02d}.", (number,), (paths["instructions"],))
        else:
            fr, en = irow["final_fr"], irow["final_en"]
            provenance.append(_prov(src["instructions"], instr[number], lines["instructions"], "final_page", "final_title", "final_type",
                                    "final_fr", "final_en", "answer_page"))
            if not fr.strip() or not en.strip():
                issues.add("INSTRUCTION_EMPTY", BLOCKING, f"Consigne FR ou EN vide pour p.{number:02d}.", (number,), (paths["instructions"],))
            for column, value in (("final_title", irow["final_title"]), ("final_fr", fr), ("final_en", en)):
                try:
                    canonical_text(value, location=f"p.{number} {column}")
                except UnsafeEditorialText as exc:
                    issues.add("UNICODE_POLICY", BLOCKING, str(exc), (number,), (paths["instructions"],))
            if row is not None and (irow["final_title"] != row["final_title"] or irow["final_type"].strip() != content_type):
                issues.add("IDENTITY_MISMATCH", BLOCKING, f"p.{number:02d} : titre/type du plan ≠ consignes (identité ambiguë).",
                           (number,), (paths["plan"], paths["instructions"]))
    page_units = units[number]
    allowed = UNIT_TYPES_BY_NATURE.get(expected, ())
    for unit in page_units:
        if unit.unit_type not in allowed:
            issues.add("UNIT_WRONG_PAGE", BLOCKING, f"Unité {unit.unit_id} ({unit.unit_type}) rattachée à p.{number:02d} : type incompatible.",
                       (number,), (paths["grid"],))
        provenance.append(unit.provenance)
    if number in ACTIVITY_PAGES and len([u for u in page_units if u.unit_type == "activity_instruction"]) != 1:
        issues.add("UNIT_ATTACHMENT", BLOCKING, f"p.{number:02d} : exactement une unité de consigne attendue.", (number,), (paths["grid"],))
    elif number in ACTIVITY_PAGES and irow is not None:
        unit = next(u for u in page_units if u.unit_type == "activity_instruction")
        if (unit.fr_exact, unit.en_exact, unit.title_active, unit.activity_type) != (fr, en, irow["final_title"], irow["final_type"]):
            issues.add("GRID_VS_INSTRUCTIONS", BLOCKING, f"p.{number:02d} : grille ≠ consignes actives.", (number,), (paths["grid"], paths["instructions"]))
    if not page_units:
        issues.add("UNIT_ATTACHMENT", BLOCKING, f"p.{number:02d} : aucune unité de grille rattachée.", (number,), (paths["grid"],))
    count_expected = {LEXICON_PAGE: LEXICON_PAIRS, CLOSING_PAGE: CLOSING_UNITS, 1: 1, 2: 1}.get(number)
    if count_expected is not None and len(page_units) != count_expected:
        issues.add("UNIT_ATTACHMENT", BLOCKING, f"p.{number:02d} : {len(page_units)} unité(s) au lieu de {count_expected}.", (number,), (paths["grid"],))

    link = links.get(number)
    entries = tuple(links[p] for p in sorted(links) if links[p].answer_page == number) if number in ANSWER_PAGES else ()
    if nature == "answers" and len(entries) != len([u for u in page_units if u.unit_type == "answer_entry"]):
        issues.add("ANSWER_PAGE_ENTRIES", BLOCKING, f"p.{number:02d} : entrées de corrigé du contrôle ≠ unités de la grille.",
                   (number,), (paths["answers"], paths["grid"]))
    if link is not None:
        requirement = "REQUIRED"
    elif nature in ("activity",) and number in ACTIVITY_PAGES:
        requirement = "NOT_LISTED_IN_ANSWER_CONTROL"
    else:
        requirement = "NOT_APPLICABLE"
    return dict(
        page=number, title=title, nature=nature, content_type=content_type, mechanic=mechanic, plan_status=plan_status,
        demand_level=demand, plan_correction_status=plan_correction,
        c4_locked=any(u.c4_lock == "YES" for u in page_units), instruction_fr=fr, instruction_en=en,
        answer_requirement=requirement, answer=link, answer_entries=entries, units=page_units,
        provenance=tuple(provenance))
