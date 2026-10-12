"""Analysis of the active scenario B sources: structure, editorial state, technical compatibility."""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from lafractale.engine.contracts import read_bounded
from lafractale.scenario_b import GATES, READER_VERSION, READY_FOR_KDP, REPORT_KIND, REPORT_SCHEMA, ReaderError
from lafractale.scenario_b.capabilities import (
    LAYOUT_TYPES, c4_connect_prompts, c4_pilot_pages, engine_facts, evaluate_page,
)
from lafractale.scenario_b.sources import (
    LoadedSource, SOURCE_SPECS, load_sources, parse_csv, parse_json, sha256_hex,
)
from lafractale.scenario_b.synthesis import COMPONENTS, component_for_mechanic, group_pages, implementation_order
from lafractale.security.text import UnsafeEditorialText, canonical_text

# Structure expected from the B3-A.3 / B3-A.4 documents (the mission's contract).
TOTAL_PAGES = 56
OPENING_PAGES = (1, 2)
ACTIVITY_PAGES = tuple(range(3, 49))
ANSWER_PAGES = (49, 50, 51, 52, 53, 54)
ANSWER_DISTRIBUTION = (6, 5, 5, 5, 5, 5)
LEXICON_PAGE, CLOSING_PAGE = 55, 56
LEXICON_PAIRS, CLOSING_UNITS, GRID_TOTAL = 18, 6, 103
CREATIVE_BREATHING = (42, 45, 47)
ARCHIVE_COUNT = 47
ACTIVE_SCOPE = "ACTIVE_B3A4_REVIEW_SCOPE"
REVIEW_FIELDS = (("fr_review_status", "FR"), ("en_review_status", "EN"),
                 ("bilingual_equivalence_status", "BILINGUAL_EQUIVALENCE"),
                 ("age_4_5_mediation_status", "MEDIATION_4_5"), ("human_review_status", "HUMAN_REVIEW"))
_CORR_ID = re.compile(r"-CORR-P(\d{2})\Z")
# Counts stated by docs/editorial/b3a/b3a4/05_feuille_route_technique_b3b.md (cross-checked, not trusted).
ROADMAP_CLAIMS = {"activities": 46, "mechanisms": 16, "c4_pilots": 3, "existing_type_non_pilot": 7,
                  "unimplemented_activities": 36, "unimplemented_mechanisms": 13}


class _Findings:
    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []
        self.checks: list[dict[str, Any]] = []

    def add(self, severity: str, code: str, message: str, pages: tuple[int, ...] = (), sources: tuple[str, ...] = ()) -> None:
        self.items.append({"severity": severity, "code": code, "message": message,
                           "pages": sorted(set(pages)), "sources": list(sources)})

    def check(self, check_id: str, label: str, expected: Any, observed: Any, ok: bool, *,
              severity: str = "STRUCTURE", message: str | None = None, pages: tuple[int, ...] = (),
              sources: tuple[str, ...] = ()) -> None:
        self.checks.append({"id": check_id, "label": label, "expected": expected, "observed": observed,
                            "status": "PASS" if ok else "FAIL"})
        if not ok:
            self.add(severity, check_id.upper(), message or f"{label} : attendu {expected!r}, observé {observed!r}",
                     pages, sources)


def _int(value: str) -> int | None:
    value = value.strip()
    return int(value) if value.isdigit() else None


def _page_list(pages: list[int]) -> str:
    return ", ".join(f"p.{p:02d}" for p in sorted(pages))


def _ranges(pages: list[int]) -> str:
    return _page_list(pages) if pages else "—"


def analyze(root: str | Path) -> dict[str, Any]:
    """Return the full report (a plain dict) for the sources under ``root``. Read-only."""
    loaded, absent = load_sources(root)
    f = _Findings()
    facts = engine_facts()
    src = {k: v.spec.path for k, v in loaded.items()}

    plan_rows = parse_csv(loaded["plan"].data, src["plan"], loaded["plan"].spec.columns)
    instr_rows = parse_csv(loaded["instructions"].data, src["instructions"], loaded["instructions"].spec.columns)
    answer_rows_all = parse_csv(loaded["answers"].data, src["answers"], loaded["answers"].spec.columns)
    grid_rows = parse_csv(loaded["grid"].data, src["grid"], loaded["grid"].spec.columns)
    archives = {key: parse_csv(loaded[key].data, src[key], loaded[key].spec.columns)
                for key in ("archive_b3a3", "archive_b3a4") if key in loaded}
    legacy_rows = (parse_csv(loaded["legacy_plan"].data, src["legacy_plan"], loaded["legacy_plan"].spec.columns)
                   if "legacy_plan" in loaded else None)
    evidence = parse_json(loaded["evidence_b3a4"].data, src["evidence_b3a4"]) if "evidence_b3a4" in loaded else None
    approvals = parse_json(loaded["approvals"].data, src["approvals"]) if "approvals" in loaded else None
    book = None
    if "book_config" in loaded:
        try:
            book = yaml.safe_load(loaded["book_config"].data.decode("utf-8"))
        except (yaml.YAMLError, UnicodeDecodeError) as exc:
            raise ReaderError(f"{src['book_config']} : YAML illisible ({exc})") from exc
    for item in absent:
        f.add("STRUCTURE", "OPTIONAL_SOURCE_ABSENT", f"Source optionnelle absente : {item['path']} ({item['role']}).",
              sources=(item["path"],))

    # ---- plan (canonical pagination) -------------------------------------------------
    plan: dict[int, dict[str, str]] = {}
    duplicated: list[int] = []
    out_of_range: list[int] = []
    for row in plan_rows:
        number = _int(row["final_page"])
        if number is None:
            f.add("STRUCTURE", "PLAN_PAGE_NOT_INTEGER", f"Numéro de page non entier dans le plan : {row['final_page']!r}.",
                  sources=(src["plan"],))
        elif not 1 <= number <= TOTAL_PAGES:
            out_of_range.append(number)
        elif number in plan:
            duplicated.append(number)
        else:
            plan[number] = row
    missing_pages = [p for p in range(1, TOTAL_PAGES + 1) if p not in plan]
    f.check("plan_page_count", "Plan actif : 56 pages distinctes", TOTAL_PAGES, len(plan), len(plan) == TOTAL_PAGES,
            pages=tuple(missing_pages), sources=(src["plan"],),
            message=f"Plan actif : {len(plan)} pages distinctes sur {TOTAL_PAGES}" + (f" ; absentes : {_ranges(missing_pages)}" if missing_pages else ""))
    f.check("plan_duplicate_pages", "Plan actif : aucune page dupliquée", [], sorted(set(duplicated)), not duplicated,
            pages=tuple(duplicated), sources=(src["plan"],), message=f"Pages dupliquées dans le plan : {_ranges(sorted(set(duplicated)))}")
    f.check("plan_out_of_range", "Plan actif : aucune page hors 1..56", [], sorted(set(out_of_range)), not out_of_range,
            sources=(src["plan"],), message=f"Pages hors plage dans le plan : {sorted(set(out_of_range))}")
    scenarios = {r.get("scenario", "B") for r in plan_rows}
    f.check("plan_scenario", "Plan actif : scénario B uniquement", ["B"], sorted(scenarios), scenarios == {"B"},
            sources=(src["plan"],))

    def ptype(p: int) -> str:
        return plan[p]["final_type"].strip() if p in plan else ""

    f.check("opening_pages", "p.01-02 : titres d'ouverture (front_matter)", ["front_matter"] * 2,
            [ptype(p) for p in OPENING_PAGES], all(ptype(p) == "front_matter" for p in OPENING_PAGES), pages=OPENING_PAGES,
            sources=(src["plan"],))
    activity_types = {p: ptype(p) for p in ACTIVITY_PAGES}
    bad_activity = [p for p, t in activity_types.items() if not t or t in LAYOUT_TYPES]
    f.check("activity_pages", "p.03-48 : 46 pages d'activité", 46, len(ACTIVITY_PAGES) - len(bad_activity), not bad_activity,
            pages=tuple(bad_activity), sources=(src["plan"],),
            message=f"Pages p.03-48 sans type d'activité exploitable : {_ranges(bad_activity)}")
    f.check("answer_pages", "p.49-54 : six pages de corrigés", ["answers"] * 6, [ptype(p) for p in ANSWER_PAGES],
            all(ptype(p) == "answers" for p in ANSWER_PAGES), pages=ANSWER_PAGES, sources=(src["plan"],))
    f.check("lexicon_page", "p.55 : lexique", "glossary typographique", ptype(LEXICON_PAGE),
            ptype(LEXICON_PAGE) == "glossary typographique", pages=(LEXICON_PAGE,), sources=(src["plan"],))
    f.check("closing_page", "p.56 : diplôme et clôture", "diploma + back_matter", ptype(CLOSING_PAGE),
            ptype(CLOSING_PAGE) == "diploma + back_matter", pages=(CLOSING_PAGE,), sources=(src["plan"],))
    f.check("creative_breathing", "Respirations créatives p.42, p.45, p.47", ["creative_color"] * 3,
            [ptype(p) for p in CREATIVE_BREATHING], all(ptype(p) == "creative_color" for p in CREATIVE_BREATHING),
            pages=CREATIVE_BREATHING, sources=(src["plan"],))
    free_with_answer = [p for p in CREATIVE_BREATHING if p in plan and plan[p]["correction_status"].strip() not in ("libre", "")]
    f.check("creative_breathing_free", "Respirations créatives : correction « libre »", [], free_with_answer, not free_with_answer,
            pages=tuple(free_with_answer), sources=(src["plan"],))

    # ---- active instructions (46) vs plan ------------------------------------------------
    instr: dict[int, dict[str, str]] = {}
    instr_dup: list[int] = []
    for row in instr_rows:
        number = _int(row["final_page"])
        if number is None:
            f.add("STRUCTURE", "INSTRUCTION_PAGE_NOT_INTEGER", f"Numéro de page non entier dans les consignes : {row['final_page']!r}.",
                  sources=(src["instructions"],))
        elif number in instr:
            instr_dup.append(number)
        else:
            instr[number] = row
    missing_instr = [p for p in ACTIVITY_PAGES if p not in instr]
    extra_instr = sorted(p for p in instr if p not in ACTIVITY_PAGES)
    f.check("instructions_count", "Consignes actives : 46 pages p.03-48", 46, len(instr) - len(extra_instr),
            not missing_instr and not extra_instr and not instr_dup, pages=tuple(missing_instr + extra_instr + instr_dup),
            sources=(src["instructions"],),
            message=f"Consignes actives : absentes {_ranges(missing_instr)} ; hors p.03-48 {extra_instr} ; dupliquées {sorted(set(instr_dup))}")
    historical_in_active = bool(extra_instr) or len(instr_rows) == ARCHIVE_COUNT
    f.check("historical_not_active", "Sources historiques non confondues avec les sources actives (47 ≠ 46)", False,
            historical_in_active, not historical_in_active, severity="CONTRADICTION", pages=tuple(extra_instr),
            sources=(src["instructions"],),
            message="Le fichier de consignes actives contient des lignes de l'archive historique (47 propositions, p.49).")
    title_mm = [p for p in ACTIVITY_PAGES if p in plan and p in instr and plan[p]["final_title"] != instr[p]["final_title"]]
    type_mm = [p for p in ACTIVITY_PAGES if p in plan and p in instr and plan[p]["final_type"] != instr[p]["final_type"]]
    f.check("titles_plan_vs_instructions", "Titres identiques plan ↔ consignes", [], title_mm, not title_mm,
            severity="CONTRADICTION", pages=tuple(title_mm), sources=(src["plan"], src["instructions"]),
            message=f"Titres divergents plan/consignes : {_ranges(title_mm)}")
    f.check("types_plan_vs_instructions", "Types identiques plan ↔ consignes", [], type_mm, not type_mm,
            severity="CONTRADICTION", pages=tuple(type_mm), sources=(src["plan"], src["instructions"]),
            message=f"Types divergents plan/consignes : {_ranges(type_mm)}")
    empty_lang = [p for p in ACTIVITY_PAGES if p in instr and not (instr[p]["final_fr"].strip() and instr[p]["final_en"].strip())]
    f.check("instructions_fr_en", "Consignes FR et EN renseignées", [], empty_lang, not empty_lang, severity="CONTRADICTION",
            pages=tuple(empty_lang), sources=(src["instructions"],),
            message=f"Consigne FR ou EN manquante : {_ranges(empty_lang)}")
    unicode_bad: list[int] = []
    for p, row in sorted(instr.items()):
        for column in ("final_title", "final_fr", "final_en"):
            try:
                canonical_text(row[column], location=f"p.{p} {column}")
            except UnsafeEditorialText as exc:
                unicode_bad.append(p)
                f.add("STRUCTURE", "UNICODE_POLICY", str(exc), (p,), (src["instructions"],))
    f.check("unicode_policy", "Texte éditorial conforme à la politique Unicode du dépôt", [], sorted(set(unicode_bad)),
            not unicode_bad, pages=tuple(unicode_bad), sources=(src["instructions"],), message="Texte non conforme (voir détails).")
    # C4 canonical text must not drift from the engine's profile.
    prompt_fr, prompt_en = c4_connect_prompts()
    if 6 in instr:
        ok = (instr[6]["final_fr"], instr[6]["final_en"]) == (prompt_fr, prompt_en)
        f.check("c4_p06_text", "p.06 : consigne identique au profil C4 du moteur", [prompt_fr, prompt_en],
                [instr[6]["final_fr"], instr[6]["final_en"]], ok, severity="CONTRADICTION", pages=(6,),
                sources=(src["instructions"],))

    # ---- corrigés ---------------------------------------------------------------------
    answers_b = [r for r in answer_rows_all if r["scenario"].strip() == "B"]
    corr: dict[int, dict[str, str]] = {}
    corr_dup: list[int] = []
    for row in answers_b:
        number = _int(row["final_activity_page"])
        if number is None:
            f.add("STRUCTURE", "ANSWER_PAGE_NOT_INTEGER", f"Page d'activité non entière dans les corrigés : {row['final_activity_page']!r}.",
                  sources=(src["answers"],))
        elif number in corr:
            corr_dup.append(number)
        else:
            corr[number] = row
    per_answer_page = Counter(_int(r["answer_page"]) for r in corr.values())
    distribution = tuple(per_answer_page.get(p, 0) for p in ANSWER_PAGES)
    f.check("answers_count", "Corrigés : 31 unités", 31, len(corr), len(corr) == 31 and not corr_dup,
            pages=tuple(corr_dup), sources=(src["answers"],), message=f"Corrigés scénario B : {len(corr)} unités (doublons {sorted(set(corr_dup))}).")
    f.check("answers_distribution", "Corrigés : répartition 6/5/5/5/5/5 sur p.49-54", list(ANSWER_DISTRIBUTION),
            list(distribution), distribution == ANSWER_DISTRIBUTION and set(per_answer_page) <= set(ANSWER_PAGES),
            pages=ANSWER_PAGES, sources=(src["answers"],),
            message=f"Répartition des corrigés {list(distribution)} (pages {sorted(k for k in per_answer_page if k is not None)}) au lieu de {list(ANSWER_DISTRIBUTION)}.")
    free_pages = [p for p in plan if plan[p]["correction_status"].strip() == "libre" or plan[p]["final_type"] in ("coloring", "creative_color")]
    free_in_answers = sorted(p for p in corr if p in free_pages)
    f.check("answers_no_free_activity", "Aucune activité libre dans les corrigés", [], free_in_answers, not free_in_answers,
            severity="CONTRADICTION", pages=tuple(free_in_answers), sources=(src["answers"],))
    unknown_activity = sorted(p for p in corr if p not in ACTIVITY_PAGES)
    f.check("answers_target_pages", "Corrigés rattachés à des activités p.03-48", [], unknown_activity, not unknown_activity,
            severity="CONTRADICTION", pages=tuple(unknown_activity), sources=(src["answers"],))
    ans_title_mm = [p for p in corr if p in plan and corr[p]["title"] != plan[p]["final_title"]]
    f.check("answers_titles", "Titres des corrigés = titres du plan", [], ans_title_mm, not ans_title_mm,
            severity="CONTRADICTION", pages=tuple(ans_title_mm), sources=(src["answers"], src["plan"]))
    instr_answer = {p: _int(instr[p]["answer_page"]) for p in instr if instr[p]["answer_page"].strip()}
    ans_vs_instr = sorted(p for p in set(corr) | set(instr_answer)
                          if (_int(corr[p]["answer_page"]) if p in corr else None) != instr_answer.get(p))
    f.check("answer_pages_consistent", "Page de corrigé identique consignes ↔ contrôle des corrigés", [], ans_vs_instr,
            not ans_vs_instr, severity="CONTRADICTION", pages=tuple(ans_vs_instr),
            sources=(src["instructions"], src["answers"]))
    plan_kind_filled = [p for p in ACTIVITY_PAGES if p in plan and plan[p]["correction_status"].strip()]
    needs_without_plan_kind = sorted(p for p in corr if p in plan and not plan[p]["correction_status"].strip())
    if needs_without_plan_kind:
        f.add("CONTRADICTION", "PLAN_CORRECTION_STATUS_EMPTY",
              f"Le plan actif ne renseigne correction_status que pour {len(plan_kind_filled)} pages ; "
              f"{len(needs_without_plan_kind)} pages ont pourtant un corrigé dans le contrôle des corrigés. "
              "Le contrôle des corrigés fait foi pour le besoin de corrigé.",
              tuple(needs_without_plan_kind), (src["plan"], src["answers"]))

    # ---- B3-A.4 grid (103 units) --------------------------------------------------------
    unit_ids = [r["unit_id"] for r in grid_rows]
    dup_units = sorted(u for u, n in Counter(unit_ids).items() if n > 1)
    types = Counter(r["unit_type"] for r in grid_rows)
    expected_types = {"activity_instruction": 46, "answer_entry": 31, "lexicon_pair": LEXICON_PAIRS, "opening_text": 2}
    closing_types = ("congratulations", "diploma_label", "name_label", "drawing_instruction", "closing", "thanks")
    closing_count = sum(types.get(t, 0) for t in closing_types)
    f.check("grid_total", "Grille B3-A.4 : 103 unités actives", GRID_TOTAL, len(grid_rows),
            len(grid_rows) == GRID_TOTAL and not dup_units, sources=(src["grid"],),
            message=f"Grille B3-A.4 : {len(grid_rows)} unités (doublons {dup_units}) au lieu de {GRID_TOTAL}.")
    breakdown_ok = all(types.get(t, 0) == n for t, n in expected_types.items()) and closing_count == CLOSING_UNITS
    f.check("grid_breakdown", "Grille : 46 consignes + 31 corrigés + 18 paires + 2 ouvertures + 6 unités p.56",
            {**expected_types, "closing_units": CLOSING_UNITS},
            {**{t: types.get(t, 0) for t in expected_types}, "closing_units": closing_count}, breakdown_ok,
            sources=(src["grid"],))
    non_active = sorted(r["unit_id"] for r in grid_rows if r["active_or_archive"] != ACTIVE_SCOPE)
    f.check("grid_active_only", "Grille : aucune unité d'archive dans le périmètre actif", [], non_active, not non_active,
            severity="CONTRADICTION", sources=(src["grid"],),
            message=f"Unités non actives dans la grille active : {non_active[:5]}")
    units_by_page: dict[int, list[dict[str, str]]] = {}
    solution_unit: dict[int, dict[str, str]] = {}
    for row in grid_rows:
        number = _int(row["final_page"])
        if number is None:
            f.add("STRUCTURE", "GRID_PAGE_NOT_INTEGER", f"Page non entière dans la grille : {row['unit_id']}", sources=(src["grid"],))
            continue
        units_by_page.setdefault(number, []).append(row)
        match = _CORR_ID.search(row["unit_id"])
        if row["unit_type"] == "answer_entry" and match:
            solution_unit[int(match.group(1))] = row
    grid_vs_corr = sorted(set(solution_unit) ^ set(corr))
    f.check("grid_answers_vs_controle", "Entrées de corrigé de la grille = contrôle des corrigés", [], grid_vs_corr,
            not grid_vs_corr, severity="CONTRADICTION", pages=tuple(grid_vs_corr), sources=(src["grid"], src["answers"]))
    grid_answer_pages = {p: _int(u["final_page"]) for p, u in solution_unit.items()}
    grid_answer_mm = sorted(p for p in grid_answer_pages if p in corr and grid_answer_pages[p] != _int(corr[p]["answer_page"]))
    f.check("grid_answer_pages", "Pages de corrigé de la grille = contrôle des corrigés", [], grid_answer_mm,
            not grid_answer_mm, severity="CONTRADICTION", pages=tuple(grid_answer_mm), sources=(src["grid"], src["answers"]))
    grid_instr = {int(r["final_page"]): r for r in grid_rows if r["unit_type"] == "activity_instruction" and r["final_page"].isdigit()}
    g_mm = sorted(p for p in grid_instr if p in instr and (grid_instr[p]["fr_exact"], grid_instr[p]["en_exact"],
                  grid_instr[p]["title_active"], grid_instr[p]["activity_type"]) != (instr[p]["final_fr"], instr[p]["final_en"],
                  instr[p]["final_title"], instr[p]["final_type"]))
    f.check("grid_vs_instructions", "Grille ↔ consignes actives (titre, type, FR, EN)", [], g_mm, not g_mm,
            severity="CONTRADICTION", pages=tuple(g_mm), sources=(src["grid"], src["instructions"]))
    lex_rows = [r for r in grid_rows if r["unit_type"] == "lexicon_pair"]
    f.check("lexicon_pairs", "p.55 : 18 paires de lexique", LEXICON_PAIRS, len(lex_rows),
            len(lex_rows) == LEXICON_PAIRS and all(r["final_page"] == str(LEXICON_PAGE) for r in lex_rows),
            pages=(LEXICON_PAGE,), sources=(src["grid"],))
    if isinstance(book, dict) and isinstance(book.get("vocabulary"), dict):
        grid_fr = {r["fr_exact"].strip().casefold() for r in lex_rows}
        yaml_fr = {str(k).strip().casefold() for k in book["vocabulary"]}
        f.check("lexicon_vs_book", "p.55 : paires de la grille = vocabulaire de books/halloween_2026/book.yaml",
                sorted(yaml_fr), sorted(grid_fr), grid_fr == yaml_fr, severity="CONTRADICTION", pages=(LEXICON_PAGE,),
                sources=(src["grid"], src["book_config"]))
    if isinstance(book, dict):
        pages_cfg = (book.get("interior") or {}).get("pages")
        f.check("book_yaml_pages", "book.yaml : 56 pages intérieures", TOTAL_PAGES, pages_cfg, pages_cfg == TOTAL_PAGES,
                severity="CONTRADICTION", sources=(src["book_config"],))
    closing_units = [r for r in grid_rows if r["unit_type"] in closing_types]
    f.check("closing_units", "p.56 : 6 unités", CLOSING_UNITS, len(closing_units),
            len(closing_units) == CLOSING_UNITS and all(r["final_page"] == str(CLOSING_PAGE) for r in closing_units),
            pages=(CLOSING_PAGE,), sources=(src["grid"],))
    opening_units = [r for r in grid_rows if r["unit_type"] == "opening_text"]
    f.check("opening_units", "p.01-02 : 2 titres d'ouverture", 2, len(opening_units),
            sorted(r["final_page"] for r in opening_units) == ["1", "2"], pages=OPENING_PAGES, sources=(src["grid"],))
    c4_flags = sorted(int(r["final_page"]) for r in grid_rows if r["c4_lock"] == "YES" and r["final_page"].isdigit())
    pilots = c4_pilot_pages()
    f.check("c4_lock_vs_engine", "Pages C4_LOCKED de la grille = pages couvertes par le profil du moteur", sorted(pilots),
            c4_flags, c4_flags == sorted(pilots), severity="CONTRADICTION", pages=tuple(set(c4_flags) ^ set(pilots)),
            sources=(src["grid"],))
    c4_type_mm = sorted(p for p, kind in pilots.items() if ptype(p) != kind)
    f.check("c4_types", "Types des pilotes C4 = types du moteur", [], c4_type_mm, not c4_type_mm, severity="CONTRADICTION",
            pages=tuple(c4_type_mm), sources=(src["plan"],))

    # ---- archives ------------------------------------------------------------------------
    for key, rows in sorted(archives.items()):
        label = "b3a3" if key == "archive_b3a3" else "b3a4"
        f.check(f"archive_{label}_count", f"Archive historique {label} : 47 propositions (exclues du plan actif)",
                ARCHIVE_COUNT, len(rows), len(rows) == ARCHIVE_COUNT, severity="CONTRADICTION", sources=(src[key],))
    if "archive_b3a4" in archives:
        not_historical = [r["historical_page"] for r in archives["archive_b3a4"] if "HISTORICAL_ONLY" not in r["archive_status"]]
        f.check("archive_flag", "Archive b3a4 : statut HISTORICAL_ONLY sur chaque ligne", [], not_historical,
                not not_historical, severity="CONTRADICTION", sources=(src["archive_b3a4"],))
        if plan.get(48) is not None:
            hist49 = [r for r in archives["archive_b3a4"] if r["historical_page"] == "49"]
            ok = bool(hist49) and hist49[0]["active_final_page"] == "48" and plan[48]["source_old_pages"].strip() == "49"
            f.check("archive_p49_to_p48", "Ancienne p.49 → p.48 finale (ancienne p.48 supprimée)", "49→48",
                    f"{hist49[0]['historical_page']}→{hist49[0]['active_final_page']}" if hist49 else "absente", ok,
                    severity="CONTRADICTION", pages=(48,), sources=(src["archive_b3a4"], src["plan"]))

    # ---- gates, human validation counters, integrity ---------------------------------------
    if isinstance(evidence, dict):
        ev_status = evidence.get("statuses") or {}
        gate_drift = sorted(k for k, v in GATES.items() if ev_status.get(k) != v)
        f.check("gates_consistent", "Statuts permanents des sources = constantes du lecteur", dict(GATES),
                {k: ev_status.get(k) for k in GATES}, not gate_drift, severity="CONTRADICTION",
                sources=(src["evidence_b3a4"],), message=f"Statuts permanents divergents dans la preuve B3-A.4 : {gate_drift}")
        recorded = evidence.get("human_validations_recorded")
        validated_rows = sum(1 for r in grid_rows if r["human_review_status"].strip().upper() == "VALIDATED")
        f.check("human_validations_evidence", "Validations humaines enregistrées (preuve) = lignes validées de la grille",
                recorded, validated_rows, recorded == validated_rows, severity="CONTRADICTION", sources=(src["evidence_b3a4"], src["grid"]))
    for key in ("manifest_b3a3", "manifest_b3a4"):
        if key not in loaded:
            continue
        manifest = parse_json(loaded[key].data, src[key])
        entries = manifest.get("files") or manifest.get("records") or []
        directory = Path(src[key]).parent
        bad: list[str] = []
        for entry in entries:
            rel = entry.get("path", "")
            digest = None
            # A manifest entry may only name a file inside its own directory (no traversal, no absolute path).
            if isinstance(rel, str) and rel and not rel.startswith("/") and ".." not in Path(rel).parts:
                target = Path(root) / directory / rel
                if target.is_file() and not target.is_symlink():
                    digest = sha256_hex(_read_for_hash(target))
            if digest != entry.get("sha256"):
                bad.append(rel)
        f.check(f"integrity_{key[-4:]}", f"Manifeste d'intégrité {key[-4:]} : empreintes des fichiers", [], sorted(bad),
                not bad, severity="CONTRADICTION", sources=(src[key],),
                message=f"Fichiers dont l'empreinte diffère du manifeste {key[-4:]} : {sorted(bad)[:6]}")
    unvalidated_claims = [r["unit_id"] for r in grid_rows if r["human_review_status"].strip().upper() == "VALIDATED"
                          and not (r["validator_identity"].strip() and r["evidence_reference"].strip())]
    if unvalidated_claims:
        f.add("CONTRADICTION", "VALIDATION_WITHOUT_EVIDENCE",
              f"{len(unvalidated_claims)} unité(s) déclarée(s) VALIDATED sans identité de validateur ni preuve : "
              f"{unvalidated_claims[:5]}. Le lecteur ne les considère pas comme approuvées.", sources=(src["grid"],))
    if legacy_rows is not None:
        legacy = {r["page"].strip(): r["activity_type"].strip() for r in legacy_rows}
        diverging = sorted(p for p in range(1, TOTAL_PAGES + 1) if p in plan and legacy.get(str(p)) is not None
                           and legacy[str(p)] != ptype(p) and not (ptype(p) in LAYOUT_TYPES and legacy[str(p)] in ("front_matter",)))
        f.add("INFO", "LEGACY_PLAN_NOT_AUTHORITATIVE",
              f"books/halloween_2026/page_plan.csv n'est pas utilisé comme référence (migration B3-A.3 non validée) ; "
              f"{len(diverging)} pages y portent un type différent du plan B actif.", tuple(diverging), (src["legacy_plan"],))

    # ---- per-page diagnostics ---------------------------------------------------------------
    approved_ids = {a["id"] for a in (approvals or {}).get("illustrations", []) if a.get("human_approved") is True} if isinstance(approvals, dict) else set()
    companion_bindings = _companion_bindings()
    pages: list[dict[str, Any]] = []
    for number in range(1, TOTAL_PAGES + 1):
        pages.append(_page_report(number, plan.get(number), instr.get(number), corr.get(number),
                                  units_by_page.get(number, []), solution_unit.get(number), facts,
                                  companion_bindings, approved_ids, src))

    unlisted = [p["page"] for p in pages if p["sources"]["solution"]["status"] == "NOT_LISTED_IN_ANSWER_CONTROL"]
    if unlisted:
        f.add("INFO", "ACTIVITY_WITHOUT_ANSWER_ENTRY",
              f"{len(unlisted)} activité(s) fermée(s) absente(s) du contrôle des corrigés (aucune solution requise ou oubli à confirmer) : "
              f"{_page_list(unlisted)}.", tuple(unlisted), (src["answers"],))
    summary = _summary(pages, grid_rows, plan, f, facts)
    synthesis = _synthesis(pages, f.items, summary)
    structure_ok = not any(i["severity"] == "STRUCTURE" for i in f.items)
    report = {
        "schema": REPORT_SCHEMA,
        "kind": REPORT_KIND,
        "reader_version": READER_VERSION,
        "gates": dict(GATES),
        "ready_for_kdp": READY_FOR_KDP,
        "authority": {
            "pagination": src["plan"],
            "instructions": src["instructions"],
            "review_grid": src["grid"],
            "corrections": src["answers"],
            "excluded_from_active_plan": [src[k] for k in ("archive_b3a3", "archive_b3a4") if k in src] +
                                         ([src["legacy_plan"]] if "legacy_plan" in src else []),
            "note": "Le plan B3-A.3 fait autorité pour la pagination ; l'archive des 47 propositions et page_plan.csv sont exclus du plan actif.",
        },
        "provenance": {
            "sources": [loaded[k].provenance() for k in sorted(loaded)],
            "absent_optional_sources": absent,
            "sources_aggregate_sha256": sha256_hex("".join(f"{k}:{loaded[k].sha256}\n" for k in sorted(loaded)).encode()),
        },
        "engine_capabilities": facts,
        "illustration_registry": {
            "path": src.get("approvals"),
            "approved_asset_ids": sorted(approved_ids),
            "roles": sorted({a.get("role") for a in (approvals or {}).get("illustrations", [])}) if isinstance(approvals, dict) else [],
            "note": "Le registre ne contient que des visuels de compagnon ; aucune illustration de scène n'est liée à une page.",
        },
        "analysis": {"structure_ok": structure_ok, "checks": f.checks},
        "findings": sorted(f.items, key=lambda i: (i["severity"], i["code"], i["pages"], i["message"])),
        "pages": pages,
        "summary": summary,
        "synthesis": synthesis,
    }
    return report


def _read_for_hash(path: Path) -> bytes:
    return read_bounded(path, 8_000_000, label=str(path.name), error=ReaderError)


def _companion_bindings() -> dict[int, str]:
    try:
        from lafractale.illustrations.routing import _CANONICAL_HALLOWEEN_PIP_DEMO_V1 as routing
    except ImportError:  # pragma: no cover - defensive
        return {}
    return {page: asset for _, _, page, _, asset in routing}


def _review_missing(rows: list[dict[str, str]]) -> list[str]:
    missing: list[str] = []
    for column, code in REVIEW_FIELDS:
        if any(r[column].strip().upper() != "VALIDATED" for r in rows):
            missing.append(code)
    return missing


def _editorial_state(rows: list[dict[str, str]], classification: str) -> str:
    if not rows:
        return "NO_SOURCE"
    if any(r["final_status"].strip() == "BLOCKED_BY_SOURCE" for r in rows):
        return "BLOCKED_BY_SOURCE"
    if classification == "HUMAN_REVIEW":
        return "HUMAN_REVIEW"
    if any(r["final_status"].strip().upper() != "VALIDATED" for r in rows):
        return "NOT_VALIDATED"
    if any(not (r["validator_identity"].strip() and r["evidence_reference"].strip()) for r in rows):
        return "NOT_VALIDATED"
    return "VALIDATED"


def _page_report(number: int, plan_row: dict[str, str] | None, instr_row: dict[str, str] | None,
                 corr_row: dict[str, str] | None, units: list[dict[str, str]], sol_unit: dict[str, str] | None,
                 facts: dict[str, Any], companion: dict[int, str], approved_ids: set[str], src: dict[str, str]) -> dict[str, Any]:
    plan_type = plan_row["final_type"].strip() if plan_row else None
    if plan_type in LAYOUT_TYPES:
        kind = LAYOUT_TYPES[plan_type]
    elif plan_type in ("coloring", "creative_color"):
        kind = "free_creative"
    elif plan_type:
        kind = "activity"
    else:
        kind = "absent"
    blockers: list[dict[str, str]] = []
    actions: list[dict[str, str]] = []
    deps: list[str] = []
    if plan_row is None:
        technical = {"status": "UNKNOWN", "family": None, "reasons": ["Page absente du plan actif : exigences inconnues."],
                     "missing_capabilities": [], "open_questions": ["Restaurer la page dans le plan B3-A.3."]}
        blockers.append({"code": "PAGE_ABSENT_FROM_PLAN", "category": "DOC_CONSISTENCY",
                         "detail": "La page n'existe pas dans le chemin de fer actif."})
    else:
        technical = evaluate_page(number, plan_type or "", plan_row["demand_level"], facts)
    instruction_units = [u for u in units if u["unit_type"] != "answer_entry"]
    own_units = units if kind == "answers" else instruction_units
    classification = (instr_row or {}).get("previous_classification", "").strip()
    state = _editorial_state(own_units, classification)
    # instruction source
    if kind in ("activity", "free_creative"):
        fr = (instr_row or {}).get("final_fr", "")
        en = (instr_row or {}).get("final_en", "")
        instruction = {"status": "PRESENT" if instr_row and fr.strip() and en.strip() else "ABSENT",
                       "fr": fr, "en": en, "classification": classification or None,
                       "c4_locked": bool(units and any(u["c4_lock"] == "YES" for u in units))}
        if instruction["status"] == "ABSENT":
            blockers.append({"code": "INSTRUCTION_FR_EN_MISSING", "category": "EDITORIAL_CONTENT",
                             "detail": "Consigne FR/EN absente ou incomplète."})
            actions.append({"category": "EDITORIAL_CONTENT", "short": "consigne FR/EN", "text": "Fournir la consigne bilingue FR/EN active."})
    else:
        instruction = {"status": "NOT_APPLICABLE", "fr": None, "en": None, "classification": None, "c4_locked": False}
    # solution
    required = corr_row is not None
    answer_page = _int(corr_row["answer_page"]) if corr_row else None
    if required:
        sol_state = (sol_unit["final_status"].strip() if sol_unit else "MISSING_MAPPING")
        if sol_unit and sol_state.upper() == "VALIDATED" and not (sol_unit["validator_identity"].strip() and sol_unit["evidence_reference"].strip()):
            sol_state = "CLAIMED_VALIDATED_WITHOUT_EVIDENCE"
        solution = {"required": True, "kind": corr_row["correction_type"].strip(), "answer_page": answer_page,
                    "unit_id": sol_unit["unit_id"] if sol_unit else None,
                    "source_completeness": sol_unit["source_completeness"] if sol_unit else None, "status": sol_state,
                    "engine_can_derive": technical["status"] in ("SUPPORTED",)}
        if sol_state == "BLOCKED_BY_SOURCE":
            blockers.append({"code": "SOLUTION_BLOCKED_BY_SOURCE", "category": "EDITORIAL_CONTENT",
                             "detail": f"Solution et libellé de corrigé absents (p.{answer_page})."})
            actions.append({"category": "EDITORIAL_CONTENT", "short": f"solution → p.{answer_page}", "text": f"Fournir la solution et le libellé du corrigé (p.{answer_page})."})
        deps.append(f"p.{answer_page} (mise en page du corrigé)")
    else:
        solution = {"required": False, "kind": (plan_row or {}).get("correction_status", "").strip() or None,
                    "answer_page": None, "unit_id": None, "source_completeness": None,
                    "status": "NOT_REQUIRED" if kind in ("free_creative", "front_matter", "glossary", "closing", "answers") else "UNDETERMINED",
                    "engine_can_derive": False}
        if kind == "activity" and plan_row is not None:
            # Not a blocker: the answer control simply does not list this activity.
            solution["status"] = "NOT_LISTED_IN_ANSWER_CONTROL"
    # unit-level blockers kept as-is (real state, grouped per code and completeness)
    grouped: dict[tuple[str, str], list[str]] = {}
    for u in own_units:
        completeness = u["source_completeness"].strip()
        if any(token in completeness for token in ("PARTIAL", "MOCK", "CANDIDATE", "NON_PRODUCTION")) and u["unit_type"] != "answer_entry":
            code = {"opening_text": "OPENING_COPY_ABSENT", "lexicon_pair": "LEXICON_PRODUCTION_COPY_ABSENT"}.get(u["unit_type"], "PRODUCTION_COPY_NOT_FINAL")
            grouped.setdefault((code, completeness), []).append(u["unit_id"])
        if u["final_status"].strip() == "BLOCKED_BY_SOURCE" and u["unit_type"] != "answer_entry":
            grouped.setdefault(("BLOCKED_BY_SOURCE", "BLOCKED_BY_SOURCE"), []).append(u["unit_id"])
    for (code, token), ids in sorted(grouped.items()):
        blockers.append({"code": code, "category": "EDITORIAL_CONTENT",
                         "detail": f"{len(ids)} unité(s) ({ids[0]}{'…' + ids[-1] if len(ids) > 1 else ''}) : {token}."})
    for code, short, text in (("OPENING_COPY_ABSENT", "copie d'ouverture", "Fournir la copie bilingue d'ouverture."),
                              ("LEXICON_PRODUCTION_COPY_ABSENT", "copie de production p.55", "Figer la copie de production du lexique (ordre, repères)."),
                              ("PRODUCTION_COPY_NOT_FINAL", "copie de production p.56", "Séparer la copie candidate des annotations techniques et la figer.")):
        if any(b["code"] == code for b in blockers):
            actions.append({"category": "EDITORIAL_CONTENT", "short": short, "text": text})
    if kind == "answers":
        pages_listed = sorted(int(m.group(1)) for u in units if (m := _CORR_ID.search(u["unit_id"])))
        deps.append("activités sources : " + _page_list(pages_listed))
    if classification == "HUMAN_REVIEW":
        blockers.append({"code": "HUMAN_REVIEW_DATA_INSUFFICIENT", "category": "HUMAN_VALIDATION",
                         "detail": (instr_row or {}).get("autonomous_reading_risk", "").strip()})
        actions.append({"category": "EDITORIAL_CONTENT", "short": "fixer les données de la page",
                        "text": "Fixer les données déterministes de la page (règle, objets, quantités, solution) puis la soumettre à revue humaine."})
    if instruction["c4_locked"]:
        deps.append("profil éditorial C4 (texte canonique non modifiable)")
    if plan_type == "match_vocabulary":
        deps.append("p.55 (lexique 18 paires) et pictogrammes approuvés")
    missing_validations = _review_missing(own_units) if own_units else []
    if required and sol_unit and sol_unit["human_review_status"].strip().upper() != "VALIDATED":
        missing_validations.append("SOLUTION_REVIEW")
    if missing_validations:
        actions.append({"category": "HUMAN_VALIDATION", "short": "revue humaine",
                        "text": "Revue humaine requise : " + ", ".join(missing_validations) + "."})
    if technical["status"] != "SUPPORTED" and plan_row is not None:
        needs = technical["missing_capabilities"]
        actions.append({"category": "DEV", "short": f"dév. {technical['family'] or 'à cadrer'}",
                        "text": ("Développer : " + " ; ".join(needs)) if needs else "Clarifier les exigences techniques."})
    # illustrations
    if kind in ("activity", "free_creative"):
        bound = companion.get(number)
        illustration = {"scene_art": "NOT_VERIFIABLE_NO_PAGE_BINDING",
                        "companion_art": (f"BOUND_APPROVED:{bound}" if bound in approved_ids else
                                          f"BOUND_NOT_APPROVED:{bound}" if bound else "NONE_BOUND")}
        actions.append({"category": "EDITORIAL_CONTENT", "short": "illustration de scène",
                        "text": "Lier et faire approuver l'illustration de scène de la page."})
    else:
        illustration = {"scene_art": "NOT_APPLICABLE", "companion_art": "NOT_APPLICABLE"}
    return {
        "page": number,
        "title": plan_row["final_title"] if plan_row else None,
        "plan_present": plan_row is not None,
        "plan_type": plan_type,
        "content_kind": kind,
        "mechanic": plan_type if kind in ("activity", "free_creative") else None,
        "plan": {"source_old_pages": plan_row["source_old_pages"] if plan_row else None,
                 "demand_level": (plan_row["demand_level"].strip() or None) if plan_row else None,
                 "correction_status": (plan_row["correction_status"].strip() or None) if plan_row else None,
                 "status": plan_row["status"] if plan_row else None},
        "technical": technical,
        "sources": {"instruction": instruction, "solution": solution, "illustration": illustration,
                    "units": [{"unit_id": u["unit_id"], "unit_type": u["unit_type"], "source_completeness": u["source_completeness"],
                               "final_status": u["final_status"], "human_review_status": u["human_review_status"]} for u in own_units]},
        "editorial": {"state": state, "missing_validations": missing_validations},
        "blockers": blockers,
        "dependencies": deps,
        "actions": actions,
    }


def _summary(pages: list[dict[str, Any]], grid_rows: list[dict[str, str]], plan: dict[int, dict[str, str]],
             f: _Findings, facts: dict[str, Any]) -> dict[str, Any]:
    activity_pages = [p for p in pages if p["content_kind"] in ("activity", "free_creative")]
    tech_all = Counter(p["technical"]["status"] for p in pages)
    tech_act = Counter(p["technical"]["status"] for p in activity_pages)
    mechs = Counter(p["mechanic"] for p in activity_pages)
    pilot_pages = [p["page"] for p in activity_pages if p["technical"]["status"] == "SUPPORTED"]
    existing_non_pilot = [p["page"] for p in activity_pages if p["technical"]["status"] == "PARTIAL"]
    absent = [p for p in activity_pages if p["technical"]["status"] == "UNSUPPORTED"]
    computed = {"activities": len(activity_pages), "mechanisms": len(mechs), "c4_pilots": len(pilot_pages),
                "existing_type_non_pilot": len(existing_non_pilot), "unimplemented_activities": len(absent),
                "unimplemented_mechanisms": len({p["mechanic"] for p in absent})}
    claims_ok = computed == ROADMAP_CLAIMS
    f.checks.append({"id": "roadmap_claims", "label": "Chiffres de la feuille de route B3-B (b3a4/05) recalculés",
                     "expected": ROADMAP_CLAIMS, "observed": computed, "status": "PASS" if claims_ok else "FAIL"})
    if not claims_ok:
        f.add("CONTRADICTION", "ROADMAP_CLAIMS_DIFFER",
              f"Chiffres recalculés {computed} ≠ feuille de route B3-A.4 {ROADMAP_CLAIMS}.")
    states = Counter(p["editorial"]["state"] for p in pages)
    sols = Counter(p["sources"]["solution"]["status"] for p in pages if p["sources"]["solution"]["required"])
    reviewed = sum(1 for r in grid_rows if r["human_review_status"].strip().upper() == "VALIDATED")
    return {
        "pages_total": len(pages),
        "activity_pages": len(activity_pages),
        "technical_status_all_pages": {s: tech_all.get(s, 0) for s in ("SUPPORTED", "PARTIAL", "UNSUPPORTED", "UNKNOWN")},
        "technical_status_activity_pages": {s: tech_act.get(s, 0) for s in ("SUPPORTED", "PARTIAL", "UNSUPPORTED", "UNKNOWN")},
        "mechanics": dict(sorted(mechs.items())),
        "editorial_state": dict(sorted(states.items())),
        "solutions_required": sum(sols.values()),
        "solution_status": dict(sorted(sols.items())),
        "human_review_pages": sorted(p["page"] for p in pages if p["editorial"]["state"] == "HUMAN_REVIEW"),
        "grid_units": len(grid_rows),
        "human_validations_recorded": reviewed,
        "recomputed_roadmap_counts": computed,
        "findings_by_severity": dict(sorted(Counter(i["severity"] for i in f.items).items())),
        "checks_failed": sum(1 for c in f.checks if c["status"] == "FAIL"),
        "checks_total": len(f.checks),
        "engine_supported_mechanics": facts["generators"],
    }


def _synthesis(pages: list[dict[str, Any]], findings: list[dict[str, Any]], summary: dict[str, Any]) -> dict[str, Any]:
    needing = [p for p in pages if p["technical"]["status"] != "SUPPORTED" and p["plan_present"]]
    by_component: dict[str, list[dict[str, Any]]] = {}
    for p in needing:
        cid = component_for_mechanic(p["plan_type"] or "")
        if cid is not None:
            by_component.setdefault(cid, []).append(p)
    catalogue = {c["id"]: c for c in COMPONENTS}
    technical: list[dict[str, Any]] = []
    for cid in sorted(catalogue, key=lambda i: catalogue[i]["priority"]):
        group = by_component.get(cid, [])
        if not group and cid not in ("C1", "C3", "C10"):
            continue
        mechanics: dict[str, list[int]] = {}
        for p in group:
            mechanics.setdefault(p["plan_type"], []).append(p["page"])
        technical.append({
            "component": cid, "label": catalogue[cid]["label"], "depends_on": list(catalogue[cid]["depends_on"]),
            "reuses": list(catalogue[cid]["reuses"]), "work": list(catalogue[cid]["work"]),
            "pages": sorted(p["page"] for p in group),
            "mechanics": {m: {"pages": sorted(v), "status": sorted({q["technical"]["status"] for q in group if q["plan_type"] == m}),
                              "missing_capabilities": sorted({c for q in group if q["plan_type"] == m for c in q["technical"]["missing_capabilities"]})}
                          for m, v in sorted(mechanics.items())},
        })
    editorial_gaps: dict[str, list[int]] = {}
    for p in pages:
        for b in p["blockers"]:
            if b["category"] == "EDITORIAL_CONTENT":
                editorial_gaps.setdefault(b["code"], []).append(p["page"])
    validation = {
        "units_not_validated": summary["grid_units"] - summary["human_validations_recorded"],
        "units_validated": summary["human_validations_recorded"],
        "human_review_pages": summary["human_review_pages"],
        "roles_required": ["réviseur FR", "réviseur EN", "relecteur bilingue", "pédagogie 4-5 ans", "impression 100 %", "arbitre éditorial"],
    }
    docs = [i for i in findings if i["severity"] in ("CONTRADICTION", "STRUCTURE")]
    page_counts = {cid: len(v) for cid, v in by_component.items()}
    return {
        "technical_development": technical,
        "editorial_content_to_complete": {code: {"pages": sorted(set(v)), "count": len(set(v))} for code, v in sorted(editorial_gaps.items())},
        "human_validation_required": validation,
        "documentary_inconsistencies": docs,
        "implementation_order": implementation_order(page_counts),
        "grouped_pages_by_component": {k: v for k, v in group_pages(pages).items()},
    }


def dumps_report(report: dict[str, Any]) -> bytes:
    """Canonical, deterministic JSON encoding (sorted keys, UTF-8, trailing newline)."""
    return (json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
