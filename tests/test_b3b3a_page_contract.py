"""B3-B.3a — canonical page contract: nominal load, adversarial sources, immutability, isolation."""
from __future__ import annotations

import ast
import csv
import dataclasses
import hashlib
import inspect
import io
import json
import shutil
import unicodedata
from collections import Counter
from pathlib import Path

import pytest

from lafractale.scenario_b import GATES, ReaderError
from lafractale.scenario_b import pages as pages_module
from lafractale.scenario_b.pages import (
    AnswerLink, Issue, PageRecord, Provenance, ScenarioBPages, UnitRecord, load_pages,
)

ROOT = Path(__file__).resolve().parents[1]
B3A = "docs/editorial/b3a"
PLAN = f"{B3A}/b3a3/01_chemin_de_fer_scenario_B_56_pages.csv"
INSTR = f"{B3A}/b3a3/03_consignes_bilingues_finales_46_pages_scenario_B.csv"
ANSW = f"{B3A}/b3a3/02_controle_corriges_scenarios.csv"
GRID = f"{B3A}/b3a4/02_grille_relecture_humaine_complete.csv"
LEGACY = "books/halloween_2026/page_plan.csv"
SRC_DIRS = (f"{B3A}/b3a3", f"{B3A}/b3a4", "books/halloween_2026", "assets/illustrations")


@pytest.fixture(scope="module")
def contract() -> ScenarioBPages:
    return load_pages(ROOT)


@pytest.fixture()
def tree(tmp_path):
    """A private copy of the sources, free to be corrupted by a test."""
    for rel in (f"{B3A}/b3a3", f"{B3A}/b3a4", "books/halloween_2026"):
        shutil.copytree(ROOT / rel, tmp_path / rel)
    (tmp_path / "assets/illustrations").mkdir(parents=True)
    shutil.copy(ROOT / "assets/illustrations/approvals.json", tmp_path / "assets/illustrations/approvals.json")
    return tmp_path


def edit_csv(root: Path, rel: str, fn) -> None:
    path = root / rel
    with open(path, encoding="utf-8", newline="") as stream:
        rows = list(csv.reader(stream))
    header, body = rows[0], [dict(zip(rows[0], r)) for r in rows[1:]]
    body = fn(body) or body
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows([[r.get(h, "") for h in header] for r in body])
    path.write_text(buffer.getvalue(), encoding="utf-8", newline="")


def grid_row(rows, unit_id):
    return next(r for r in rows if r["unit_id"] == unit_id)


def blocking(contract, number):
    return {i.code for i in contract.page(number).issues if i.blocking}


def all_codes(contract):
    return {i.code for p in contract.pages for i in p.issues} | {i.code for i in contract.issues}


def snapshot(root: Path) -> dict[str, str]:
    out = {}
    for rel in SRC_DIRS:
        for path in sorted((root / rel).rglob("*")):
            if path.is_file():
                out[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest() + str(path.stat().st_mtime_ns)
    return out


# ---- nominal ------------------------------------------------------------------------------------
def test_nominal_loads_56_readable_pages(contract):
    assert [p.page for p in contract.pages] == list(range(1, 57))
    assert contract.all_readable and contract.readable_pages == tuple(range(1, 57))
    assert [i.code for i in contract.issues] == ["PLAN_CORRECTION_STATUS_EMPTY"]
    assert not any(i.blocking for i in contract.issues)
    assert contract.page(4).title == "Aide Pip à trouver la sortie"


def test_nominal_structure_counts(contract):
    assert sum(p.nature == "activity" or p.nature == "creative" for p in contract.pages) == 46
    assert [p.page for p in contract.pages if p.nature == "activity" or p.nature == "creative"] == list(range(3, 49))
    assert [p.page for p in contract.pages if p.content_type == "creative_color"] == [8, 28, 42, 45, 47]
    assert {42, 45, 47} <= {p.page for p in contract.pages if p.nature == "creative"}
    assert [p.nature for p in contract.pages if p.page in (1, 2)] == ["opening", "opening"]
    assert [len(p.units) for p in contract.pages if p.page in (1, 2)] == [1, 1]
    assert len(contract.page(55).units) == 18 and len(contract.page(56).units) == 6
    assert sum(len(p.units) for p in contract.pages) == 103
    assert len({u.unit_id for p in contract.pages for u in p.units}) == 103
    assert all(len(p.units) == 1 for p in contract.pages if 3 <= p.page <= 48)


def test_nominal_answers_are_linked_to_31_source_pages(contract):
    linked = [p for p in contract.pages if p.answer is not None]
    assert len(linked) == 31 and all(p.answer_requirement == "REQUIRED" for p in linked)
    assert [len(contract.page(n).answer_entries) for n in range(49, 55)] == [6, 5, 5, 5, 5, 5]
    for p in linked:
        assert p.answer.source_page == p.page and 49 <= p.answer.answer_page <= 54
        entry = [e for e in contract.page(p.answer.answer_page).answer_entries if e.source_page == p.page]
        assert len(entry) == 1 and entry[0].unit_id == f"P{p.answer.answer_page}-CORR-P{p.page:02d}"
    assert contract.page(9).answer_requirement == "NOT_LISTED_IN_ANSWER_CONTROL" and contract.page(9).answer is None
    for n in (42, 45, 47):
        assert contract.page(n).answer is None and contract.page(n).mechanic == "creative_color"
    assert contract.page(3).mechanic == "coloring"
    assert contract.page(55).mechanic is None and contract.page(1).mechanic is None


def test_nominal_instructions_and_c4(contract):
    assert contract.page(3).instruction_fr == "Colorie Pip et son invitation."
    assert contract.page(3).instruction_en == "Color Pip and his invitation."
    assert contract.page(1).instruction_fr is None
    assert [p.page for p in contract.pages if p.c4_locked] == [4, 6, 20]


def test_statuses_are_copied_literally_from_the_grid(contract):
    with open(ROOT / GRID, encoding="utf-8", newline="") as stream:
        grid = {r["unit_id"]: r for r in csv.DictReader(stream)}
    units = [u for p in contract.pages for u in p.units]
    assert len(units) == len(grid) == 103
    for u in units:
        r = grid[u.unit_id]
        assert (u.final_status, u.human_review_status, u.fr_review_status, u.en_review_status,
                u.bilingual_equivalence_status, u.age_4_5_mediation_status, u.validator_identity, u.evidence_reference,
                u.source_completeness, u.c4_lock) == (
            r["final_status"], r["human_review_status"], r["fr_review_status"], r["en_review_status"],
            r["bilingual_equivalence_status"], r["age_4_5_mediation_status"], r["validator_identity"],
            r["evidence_reference"], r["source_completeness"], r["c4_lock"])
        assert u.evidence_complete is False
    assert Counter(u.final_status for u in units) == {"NOT_VALIDATED": 64, "BLOCKED_BY_SOURCE": 39}
    assert {u.human_review_status for u in units} == {"NOT_REVIEWED"}


def test_provenance_points_to_the_real_lines_and_hashes(contract):
    by_path = {s.path: s for s in contract.sources}
    assert set(by_path) == {PLAN, INSTR, ANSW, GRID}
    for s in contract.sources:
        assert s.sha256 == hashlib.sha256((ROOT / s.path).read_bytes()).hexdigest()
    lines = (ROOT / GRID).read_text(encoding="utf-8").split("\n")
    for p in contract.pages:
        for u in p.units:
            assert u.provenance.line is not None and lines[u.provenance.line - 1].startswith(u.unit_id + ",")
            assert u.provenance.sha256 == by_path[GRID].sha256
    plan_lines = (ROOT / PLAN).read_text(encoding="utf-8").split("\n")
    prov = next(x for x in contract.page(7).provenance if x.source == "plan")
    assert plan_lines[prov.line - 1].split(",")[1] == "7"
    assert {s.source for s in contract.page(7).provenance} == {"plan", "instructions", "grid"}
    assert {s.source for s in contract.page(7).answer.provenance} == {"answers", "grid"}


def test_line_reference_is_dropped_when_it_cannot_be_trusted(tree):
    def embed_newline(rows):
        rows[6]["final_title"] = "L’ombre\nde la citrouille"
        return rows
    edit_csv(tree, PLAN, embed_newline)
    c = load_pages(tree)
    assert all(x.line is None for p in c.pages for x in p.provenance if x.source == "plan")
    assert all(x.line is not None for p in c.pages for x in p.provenance if x.source == "grid")


# ---- consistency defects --------------------------------------------------------------------------
def test_duplicated_and_missing_plan_pages(tree):
    edit_csv(tree, PLAN, lambda rows: [r for r in rows if r["final_page"] != "30"] + [dict(rows[11])])
    c = load_pages(tree)
    assert not c.all_readable
    assert "PLAN_PAGE_MISSING" in blocking(c, 30) and c.page(30).title is None and c.page(30).nature == "unknown"
    assert "PLAN_PAGE_DUPLICATED" in blocking(c, 12) and c.page(12).title is None
    assert c.page(13).readable and c.readable_pages == tuple(p for p in range(1, 57) if p not in (12, 30))


def test_plan_row_of_another_scenario_is_refused(tree):
    edit_csv(tree, PLAN, lambda rows: next(r for r in rows if r["final_page"] == "20").update(scenario="A"))
    c = load_pages(tree)
    assert "PLAN_SCENARIO" in blocking(c, 20) and c.page(21).readable


def test_out_of_range_plan_page_is_a_global_issue(tree):
    edit_csv(tree, PLAN, lambda rows: rows + [{**rows[0], "final_page": "57"}])
    c = load_pages(tree)
    assert any(i.code == "PLAN_PAGE_INVALID" and i.blocking for i in c.issues) and not c.all_readable
    assert c.readable_pages == tuple(range(1, 57))


def test_duplicated_unit_and_orphan_unit(tree):
    edit_csv(tree, GRID, lambda rows: rows + [dict(grid_row(rows, "P05-ACTIVITY"))])
    c = load_pages(tree)
    assert {"UNIT_DUPLICATED", "UNIT_ATTACHMENT"} <= blocking(c, 5)
    assert not c.page(5).readable and c.page(6).readable and "GRID_TOTAL" in all_codes(c)


def test_orphan_unit_with_unknown_page(tree):
    def orphan(rows):
        grid_row(rows, "P09-ACTIVITY")["final_page"] = "99"
    edit_csv(tree, GRID, orphan)
    c = load_pages(tree)
    assert any(i.code == "UNIT_ORPHAN" for i in c.issues)
    assert "UNIT_ATTACHMENT" in blocking(c, 9) and not c.page(9).readable


def test_unit_attached_to_the_wrong_kind_of_page(tree):
    def move(rows):
        grid_row(rows, "P55-LEX-01")["final_page"] = "3"
    edit_csv(tree, GRID, move)
    c = load_pages(tree)
    assert "UNIT_WRONG_PAGE" in blocking(c, 3) and not c.page(3).readable
    assert not c.page(55).readable and "UNIT_ATTACHMENT" in blocking(c, 55)


def test_answer_page_mismatch_between_instructions_and_control(tree):
    def change(rows):
        next(r for r in rows if r["scenario"] == "B" and r["final_activity_page"] == "5")["answer_page"] = "50"
    edit_csv(tree, ANSW, change)
    c = load_pages(tree)
    assert "ANSWER_PAGE_MISMATCH" in blocking(c, 5) and not c.page(5).readable
    assert "ANSWER_ENTRY_MISPLACED" in blocking(c, 5)
    assert {"ANSWER_DISTRIBUTION"} <= blocking(c, 49) and not c.page(49).readable and not c.page(50).readable
    assert c.page(4).readable


def test_answer_page_outside_the_answer_range(tree):
    def change(rows):
        next(r for r in rows if r["scenario"] == "B" and r["final_activity_page"] == "5")["answer_page"] = "12"
    edit_csv(tree, ANSW, change)
    c = load_pages(tree)
    assert "ANSWER_PAGE_INVALID" in blocking(c, 5) and c.page(5).answer is None


def test_duplicated_or_free_page_answer(tree):
    def change(rows):
        b = [r for r in rows if r["scenario"] == "B"]
        rows.append(dict(b[0]))
        rows.append({**b[0], "final_activity_page": "42", "title": "Les invités arrivent"})
    edit_csv(tree, ANSW, change)
    c = load_pages(tree)
    assert "ANSWER_DUPLICATED" in blocking(c, 4) and c.page(4).answer is None
    assert "ANSWER_ON_FREE_PAGE" in blocking(c, 42)


def test_missing_answer_entry_in_the_grid_and_orphan_entry(tree):
    edit_csv(tree, GRID, lambda rows: [r for r in rows if r["unit_id"] != "P49-CORR-P07"])
    c = load_pages(tree)
    assert "ANSWER_ENTRY_MISSING" in blocking(c, 7) and not c.page(7).readable and not c.page(49).readable
    assert "GRID_TOTAL" in all_codes(c)
    edit_csv(tree, ANSW, lambda rows: [r for r in rows if not (r["scenario"] == "B" and r["final_activity_page"] == "10")])
    c = load_pages(tree)
    assert "ANSWER_ENTRY_ORPHAN" in blocking(c, 10)


def test_plan_promises_an_answer_that_the_control_does_not_list(tree):
    def change(rows):
        next(r for r in rows if r["final_page"] == "9")["correction_status"] = "graphique"
    edit_csv(tree, PLAN, change)
    assert "PLAN_ANSWER_NOT_LISTED" in blocking(load_pages(tree), 9)


def test_incorrect_answer_link_title(tree):
    def change(rows):
        next(r for r in rows if r["scenario"] == "B" and r["final_activity_page"] == "11")["title"] = "Autre titre"
    edit_csv(tree, ANSW, change)
    assert "ANSWER_TITLE_MISMATCH" in blocking(load_pages(tree), 11)


def test_identity_mismatch_plan_vs_instructions_and_grid(tree):
    edit_csv(tree, INSTR, lambda rows: next(r for r in rows if r["final_page"] == "8").update(final_title="Décore autre chose"))
    c = load_pages(tree)
    assert {"IDENTITY_MISMATCH", "GRID_VS_INSTRUCTIONS"} <= blocking(c, 8) and c.page(9).readable


def test_missing_or_empty_instruction(tree):
    edit_csv(tree, INSTR, lambda rows: [r for r in rows if r["final_page"] != "13"])
    c = load_pages(tree)
    assert "INSTRUCTION_MISSING" in blocking(c, 13) and c.page(13).instruction_fr is None
    edit_csv(tree, INSTR, lambda rows: next(r for r in rows if r["final_page"] == "14").update(final_en="  "))
    assert "INSTRUCTION_EMPTY" in blocking(load_pages(tree), 14)


def test_non_canonical_unicode_blocks_only_the_affected_page(tree):
    decomposed = unicodedata.normalize("NFD", "Aide Pip à trouver la sortie")
    assert decomposed != "Aide Pip à trouver la sortie"
    edit_csv(tree, PLAN, lambda rows: next(r for r in rows if r["final_page"] == "4").update(final_title=decomposed))
    edit_csv(tree, INSTR, lambda rows: next(r for r in rows if r["final_page"] == "5").update(final_fr="Qui se cache​ ?"))
    c = load_pages(tree)
    assert "UNICODE_POLICY" in blocking(c, 4) and "UNICODE_POLICY" in blocking(c, 5) and c.page(6).readable


def test_global_structure_expectations(tree):
    edit_csv(tree, GRID, lambda rows: [r for r in rows if not r["unit_id"].startswith("P55-LEX-1")])
    c = load_pages(tree)
    assert "GRID_BREAKDOWN" in all_codes(c) and "GRID_TOTAL" in all_codes(c) and not c.all_readable
    assert "UNIT_ATTACHMENT" in blocking(c, 55)


# ---- sources: structural failures -------------------------------------------------------------------
@pytest.mark.parametrize("rel", [PLAN, INSTR, ANSW, GRID])
def test_missing_required_source_is_refused(tree, rel):
    (tree / rel).unlink()
    with pytest.raises(ReaderError, match="source obligatoire absente"):
        load_pages(tree)


@pytest.mark.parametrize("rel", [PLAN, GRID])
def test_symlinked_source_is_refused(tree, rel, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside") / "copy.csv"
    shutil.copy(tree / rel, outside)
    (tree / rel).unlink()
    (tree / rel).symlink_to(outside)
    with pytest.raises(ReaderError, match="lien symbolique"):
        load_pages(tree)


def test_malformed_csv_is_refused(tree):
    path = tree / INSTR
    lines = path.read_text(encoding="utf-8").split("\n")
    lines[3] = lines[3] + ",extra"
    path.write_text("\n".join(lines), encoding="utf-8")
    with pytest.raises(ReaderError, match="champs"):
        load_pages(tree)


def test_missing_column_and_bad_encoding_are_refused(tree):
    path = tree / PLAN
    text = path.read_text(encoding="utf-8").replace("final_title", "titre", 1)
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ReaderError, match="colonne"):
        load_pages(tree)
    shutil.copy(ROOT / PLAN, path)
    path.write_bytes(path.read_bytes() + b"\xff\xfe")
    with pytest.raises(ReaderError, match="UTF-8"):
        load_pages(tree)


def test_legacy_page_plan_is_never_used(tree):
    reference = load_pages(tree).to_canonical_json()
    (tree / LEGACY).write_text("page,activity_type\n1,garbage\n3,maze\n", encoding="utf-8")
    assert load_pages(tree).to_canonical_json() == reference
    assert "page_plan" not in reference and "legacy" not in reference


# ---- status falsification --------------------------------------------------------------------------
def _validated(rows, uid="P05-ACTIVITY", **extra):
    row = grid_row(rows, uid)
    row["final_status"] = "VALIDATED"
    for column in pages_module.REVIEW_FIELDS:
        row[column] = "VALIDATED"
    row.update(extra)


def test_claimed_validation_without_human_evidence_is_not_recognised(tree):
    edit_csv(tree, GRID, lambda rows: _validated(rows))
    c = load_pages(tree)
    unit = c.page(5).units[0]
    assert unit.final_status == "VALIDATED" and unit.evidence_complete is False
    assert "VALIDATION_WITHOUT_EVIDENCE" in blocking(c, 5) and not c.page(5).readable
    assert c.page(5).production_authorized is False


def test_partial_claim_on_a_single_review_field_is_refused(tree):
    edit_csv(tree, GRID, lambda rows: grid_row(rows, "P06-ACTIVITY").update(human_review_status="VALIDATED"))
    assert "VALIDATION_WITHOUT_EVIDENCE" in blocking(load_pages(tree), 6)


def test_validated_final_status_requires_the_five_reviews(tree):
    def change(rows):
        grid_row(rows, "P07-ACTIVITY").update(final_status="VALIDATED", validator_identity="X", evidence_reference="Y")
    edit_csv(tree, GRID, change)
    assert "VALIDATION_INCONSISTENT" in blocking(load_pages(tree), 7)


@pytest.mark.parametrize("value", ["validated", "APPROVED", " VALIDATED", ""])
def test_unknown_or_altered_status_vocabulary_is_refused(tree, value):
    edit_csv(tree, GRID, lambda rows: grid_row(rows, "P08-ACTIVITY").update(final_status=value))
    c = load_pages(tree)
    assert "UNIT_STATUS_UNKNOWN" in blocking(c, 8) and not c.page(8).readable
    assert c.page(8).units[0].final_status == value


def test_even_a_fully_documented_validation_never_authorises_production(tree):
    edit_csv(tree, GRID, lambda rows: _validated(rows, validator_identity="Relecteur", evidence_reference="PV-1"))
    c = load_pages(tree)
    unit = c.page(5).units[0]
    assert unit.evidence_complete is True and unit.final_status == "VALIDATED"
    assert c.page(5).readable and c.page(5).production_authorized is False
    assert c.production_authorized is False and c.to_dict()["production_authorized"] is False
    assert all(p["production_authorized"] is False for p in c.to_dict()["pages"])


# ---- production authorisation -----------------------------------------------------------------------
def test_production_authorized_cannot_be_enabled(monkeypatch, tree, contract):
    assert pages_module.PRODUCTION_AUTHORIZED is False and pages_module.READY_FOR_KDP is False
    for name in ("PRODUCTION_AUTHORIZED", "LAFRACTALE_PRODUCTION_AUTHORIZED", "READY_FOR_KDP", "PRODUCTION_GENERATION"):
        monkeypatch.setenv(name, "1")

    path = tree / GRID
    with open(path, encoding="utf-8", newline="") as stream:
        table = list(csv.reader(stream))
    table[0].append("production_authorized")
    for row in table[1:]:
        row.append("true")
    with open(path, "w", encoding="utf-8", newline="") as stream:
        csv.writer(stream, lineterminator="\n").writerows(table)
    (tree / "books/halloween_2026/book.yaml").write_text("production_authorized: true\nready_for_kdp: true\n", encoding="utf-8")
    c = load_pages(tree)
    assert c.production_authorized is False and all(p.production_authorized is False for p in c.pages)
    assert "AUTHORIZATION_COLUMN_IGNORED" in {i.code for i in c.issues}
    assert not any(i.blocking for i in c.issues)
    data = c.to_dict()
    assert data["gates"] == dict(GATES) and data["ready_for_kdp"] is False and data["kind"].endswith("NON_PRODUCTION")
    assert list(inspect.signature(load_pages).parameters) == ["root"]


def test_production_authorized_is_not_a_field_nor_a_constructor_argument(contract):
    for cls in (PageRecord, ScenarioBPages, UnitRecord, AnswerLink):
        assert "production_authorized" not in {f.name for f in dataclasses.fields(cls)}
    page = contract.page(3)
    kwargs = {f.name: getattr(page, f.name) for f in dataclasses.fields(page)}
    with pytest.raises(TypeError):
        PageRecord(**kwargs, production_authorized=True)
    with pytest.raises(TypeError):
        PageRecord(**kwargs, readability="READABLE")
    for attr in ("production_authorized", "readability", "readable"):
        with pytest.raises(dataclasses.FrozenInstanceError if attr not in ("readable", "production_authorized") else AttributeError):
            setattr(page, attr, True)


def test_readability_cannot_be_forged_over_a_blocking_issue(contract):
    page = contract.page(3)
    kwargs = {f.name: getattr(page, f.name) for f in dataclasses.fields(page)}
    kwargs["issues"] = (Issue("X", "BLOCKING", "bloquant"),)
    assert PageRecord(**kwargs).readability == "NOT_READABLE"


# ---- immutability -----------------------------------------------------------------------------------
def _walk(value, seen=None):
    seen = seen if seen is not None else set()
    if value is None or isinstance(value, (str, int, bool)):
        return
    assert isinstance(value, tuple) or (dataclasses.is_dataclass(value) and value.__dataclass_params__.frozen), type(value)
    assert not isinstance(value, (list, dict, set, bytearray))
    if id(value) in seen:
        return
    seen.add(id(value))
    items = value if isinstance(value, tuple) else [getattr(value, f.name) for f in dataclasses.fields(value)]
    for item in items:
        _walk(item, seen)


def test_object_graph_contains_only_immutable_values(contract):
    _walk(contract)
    assert all(hasattr(cls, "__slots__") for cls in (PageRecord, UnitRecord, AnswerLink, Provenance, Issue, ScenarioBPages))


def test_records_reject_mutation_and_new_attributes(contract):
    page = contract.page(4)
    for obj, attr, value in ((page, "title", "x"), (page, "units", ()), (page.units[0], "final_status", "VALIDATED"),
                             (page.units[0].provenance, "sha256", "0"), (page.answer, "answer_page", 50),
                             (contract, "pages", ()), (page, "nouveau", 1)):
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError, TypeError)):
            setattr(obj, attr, value)
    with pytest.raises((AttributeError, TypeError)):
        page.units.append(None)  # type: ignore[attr-defined]
    with pytest.raises(TypeError):
        page.units[0] = None  # type: ignore[index]


def test_serialised_copies_do_not_alias_the_record(contract):
    before = contract.to_canonical_json()
    data = contract.to_dict()
    data["pages"][3]["title"] = "modifié"
    data["pages"][3]["units"][0]["final_status"] = "VALIDATED"
    data["pages"].clear()
    page_dict = contract.page(4).to_dict()
    page_dict["answer"]["answer_page"] = 54
    assert contract.to_canonical_json() == before and contract.page(4).answer.answer_page == 49


def test_page_lookup_is_strict(contract):
    for bad in (0, 57, -1, True, "4", None):
        with pytest.raises(KeyError):
            contract.page(bad)


# ---- determinism and read-only guarantees -----------------------------------------------------------
def test_serialisation_is_deterministic_and_location_independent(tree, contract):
    first = contract.to_canonical_json()
    assert load_pages(ROOT).to_canonical_json() == first
    assert load_pages(tree).to_canonical_json() == first
    assert hashlib.sha256(first.encode()).hexdigest() == hashlib.sha256(load_pages(tree).to_canonical_json().encode()).hexdigest()
    parsed = json.loads(first)
    assert json.dumps(parsed, ensure_ascii=False, sort_keys=True, separators=(",", ":")) == first
    assert [p["page"] for p in parsed["pages"]] == list(range(1, 57)) and str(tree) not in first and str(ROOT) not in first
    assert parsed["sources_aggregate_sha256"] == contract.sources_aggregate_sha256 and parsed["all_readable"] is True


def test_sources_are_not_modified(tree):
    before = snapshot(tree)
    load_pages(tree).to_canonical_json()
    assert snapshot(tree) == before
    real = snapshot(ROOT)
    load_pages(ROOT)
    assert snapshot(ROOT) == real


def test_loader_opens_nothing_for_writing(monkeypatch, tree):
    import builtins
    import os

    real_open, real_os_open = builtins.open, os.open
    writes = []

    def guard_open(file, mode="r", *a, **k):
        if any(m in mode for m in "wax+"):
            writes.append(file)
        return real_open(file, mode, *a, **k)

    def guard_os_open(path, flags, *a, **k):
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT):
            writes.append(path)
        return real_os_open(path, flags, *a, **k)

    monkeypatch.setattr(builtins, "open", guard_open)
    monkeypatch.setattr(os, "open", guard_os_open)
    load_pages(tree)
    assert writes == []


# ---- isolation from the historical / synthetic engine ------------------------------------------------
def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_pages_module_reuses_b3b2_and_does_not_touch_the_engine():
    imports = _imports(Path(pages_module.__file__))
    assert {"lafractale.scenario_b.sources", "lafractale.scenario_b.analyzer"} <= imports
    forbidden = ("lafractale.engine", "lafractale.activities", "lafractale.layout", "lafractale.editorial",
                 "lafractale.illustrations", "lafractale.render", "lafractale.cli", "yaml", "subprocess", "socket", "requests")
    assert [n for n in imports if n.startswith(forbidden)] == []
    module = ast.parse(Path(pages_module.__file__).read_text(encoding="utf-8"))
    module.body[0].value.value = ""  # the module docstring may mention the forbidden notions
    source = ast.unparse(module)
    for token in ("SpecSet", "SPEC_KIND", "b3b1", "generate(", "os.environ", "getenv", "argparse", "sys.argv", "open(", "write_"):
        assert token not in source, token


def test_nothing_else_imports_the_page_contract():
    package = ROOT / "src/lafractale"
    offenders = []
    for path in package.rglob("*.py"):
        if path.name == "pages.py" and path.parent.name == "scenario_b":
            continue
        text = path.read_text(encoding="utf-8")
        if "scenario_b.pages" in text or "scenario_b import pages" in text:
            offenders.append(str(path.relative_to(package)))
    assert offenders == []
    for rel in ("scenario_b/sources.py", "scenario_b/analyzer.py", "scenario_b/__init__.py"):
        assert "pages" not in " ".join(_imports(package / rel))


def test_no_adapter_towards_the_synthetic_specset():
    public = {n for n in dir(pages_module) if not n.startswith("_")}
    assert not {n for n in public if "specset" in n.lower() or "synthetic" in n.lower() or "adapter" in n.lower()}
    for cls in (PageRecord, ScenarioBPages):
        assert not [m for m in dir(cls) if "spec" in m.lower()]
