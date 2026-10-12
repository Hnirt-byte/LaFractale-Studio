"""B3-B.2 — read-only scenario B reader: structure, capabilities, determinism, read-only guarantees."""
from __future__ import annotations

import ast
import builtins
import copy
import csv
import hashlib
import io
import json
import os
import shutil
from pathlib import Path

import pytest

from lafractale.scenario_b import GATES, ReaderError
from lafractale.scenario_b import capabilities as caps
from lafractale.scenario_b.__main__ import main as cli_main
from lafractale.scenario_b.analyzer import analyze, dumps_report
from lafractale.scenario_b.render import render_report, render_synthesis
from lafractale.scenario_b.schema import validate_report
from lafractale.scenario_b.synthesis import COMPONENTS, implementation_order

ROOT = Path(__file__).resolve().parents[1]
B3A = "docs/editorial/b3a"
PLAN = f"{B3A}/b3a3/01_chemin_de_fer_scenario_B_56_pages.csv"
INSTR = f"{B3A}/b3a3/03_consignes_bilingues_finales_46_pages_scenario_B.csv"
ANSW = f"{B3A}/b3a3/02_controle_corriges_scenarios.csv"
GRID = f"{B3A}/b3a4/02_grille_relecture_humaine_complete.csv"
ARCH = f"{B3A}/b3a4/03_archive_historique_47_reference.csv"
EVID = f"{B3A}/b3a4/08_validation_evidence.json"
LEGACY = "books/halloween_2026/page_plan.csv"
SRC_DIRS = (f"{B3A}/b3a3", f"{B3A}/b3a4", "books/halloween_2026", "assets/illustrations")


@pytest.fixture(scope="module")
def report():
    return analyze(ROOT)


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
    writer.writerows([[r[h] for h in header] for r in body])
    path.write_text(buffer.getvalue(), encoding="utf-8", newline="")


def codes(rep) -> set[str]:
    return {f["code"] for f in rep["findings"]}


def page(rep, n):
    return rep["pages"][n - 1]


def snapshot(root: Path) -> dict[str, str]:
    out = {}
    for rel in SRC_DIRS:
        for path in sorted((root / rel).rglob("*")):
            if path.is_file():
                out[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest() + str(path.stat().st_mtime_ns)
    return out


# ---- nominal sources ------------------------------------------------------------------------
def test_nominal_structure_all_checks_pass(report):
    failed = [c for c in report["analysis"]["checks"] if c["status"] == "FAIL"]
    assert failed == []
    assert report["analysis"]["structure_ok"] is True
    assert [p["page"] for p in report["pages"]] == list(range(1, 57))
    ids = {c["id"] for c in report["analysis"]["checks"]}
    for needed in ("plan_page_count", "activity_pages", "answers_count", "answers_distribution", "lexicon_pairs",
                   "closing_units", "grid_total", "creative_breathing", "historical_not_active", "roadmap_claims"):
        assert needed in ids
    assert report["summary"]["grid_units"] == 103
    assert next(c for c in report["analysis"]["checks"] if c["id"] == "answers_distribution")["observed"] == [6, 5, 5, 5, 5, 5]


def test_nominal_known_gap_is_a_finding_not_a_failure(report):
    assert "PLAN_CORRECTION_STATUS_EMPTY" in codes(report)
    info = next(f for f in report["findings"] if f["code"] == "ACTIVITY_WITHOUT_ANSWER_ENTRY")
    assert info["severity"] == "INFO" and info["pages"] == [9, 19, 29, 38]
    assert page(report, 9)["sources"]["solution"]["status"] == "NOT_LISTED_IN_ANSWER_CONTROL"
    assert page(report, 9)["blockers"] == []
    assert report["analysis"]["structure_ok"] is True


def test_schema_validates_nominal_report(report):
    assert validate_report(report) == []
    assert validate_report(json.loads(dumps_report(report).decode())) == []


def test_technical_statuses_match_engine_reality(report):
    status = {p["page"]: p["technical"]["status"] for p in report["pages"]}
    assert [n for n in (4, 6, 20) if status[n] != "SUPPORTED"] == []
    assert sorted(n for n, s in status.items() if s == "PARTIAL") == [14, 17, 25, 27, 34, 43, 46]
    activity = [p for p in report["pages"] if p["content_kind"] in ("activity", "free_creative")]
    assert sum(p["technical"]["status"] == "UNSUPPORTED" for p in activity) == 36
    assert all(status[n] == "UNSUPPORTED" for n in (1, 2, 49, 50, 54, 55, 56))
    assert report["summary"]["recomputed_roadmap_counts"] == {
        "activities": 46, "mechanisms": 16, "c4_pilots": 3, "existing_type_non_pilot": 7,
        "unimplemented_activities": 36, "unimplemented_mechanisms": 13}


def test_name_match_is_not_compatibility(report):
    p14, p43, p46, p17 = page(report, 14), page(report, 43), page(report, 46), page(report, 17)
    assert p14["mechanic"] == "maze" and p14["technical"]["status"] == "PARTIAL"
    assert "5x5" in " ".join(p43["technical"]["reasons"])
    assert any("colonnes identiques" in c for c in p46["technical"]["missing_capabilities"])
    assert p17["technical"]["open_questions"]
    assert "C4" in " ".join(page(report, 20)["technical"]["reasons"])


def test_human_states_are_preserved_never_approved(report):
    assert report["gates"] == dict(GATES) and report["ready_for_kdp"] is False
    assert report["summary"]["human_validations_recorded"] == 0
    assert report["summary"]["human_review_pages"] == [17, 22, 37, 43, 44, 45, 46, 48]
    assert all(p["editorial"]["state"] != "VALIDATED" for p in report["pages"])
    assert report["summary"]["solution_status"] == {"BLOCKED_BY_SOURCE": 31}
    assert page(report, 1)["editorial"]["state"] == "BLOCKED_BY_SOURCE"
    assert page(report, 56)["editorial"]["state"] == "BLOCKED_BY_SOURCE"
    assert {b["code"] for b in page(report, 55)["blockers"]} == {"LEXICON_PRODUCTION_COPY_ABSENT"}
    assert page(report, 4)["sources"]["instruction"]["c4_locked"] is True
    for n in (42, 45, 47):
        assert page(report, n)["sources"]["solution"]["status"] == "NOT_REQUIRED"


def test_illustration_state_is_not_invented(report):
    assert report["illustration_registry"]["roles"] == ["companion"]
    assert page(report, 4)["sources"]["illustration"]["companion_art"].startswith("BOUND_APPROVED:")
    assert page(report, 14)["sources"]["illustration"]["companion_art"] == "NONE_BOUND"
    assert page(report, 14)["sources"]["illustration"]["scene_art"] == "NOT_VERIFIABLE_NO_PAGE_BINDING"


def test_archive_and_legacy_plan_are_not_authoritative(report):
    assert any("archive_historique_47" in p for p in report["authority"]["excluded_from_active_plan"])
    assert any("page_plan.csv" in p for p in report["authority"]["excluded_from_active_plan"])
    blob = json.dumps([p["sources"] for p in report["pages"]])
    assert "archive_historique" not in blob and "page_plan" not in blob


def test_markdown_lists_56_pages_and_required_columns(report):
    md = render_report(report)
    table = md[md.index("## Les 56 pages"):md.index("## Blocages")]
    rows = [l for l in table.splitlines() if l.startswith("| ") and l[2:4].isdigit()]
    assert len(rows) == 56
    for column in ("Page", "Titre", "Type de contenu", "Mécanique", "Compat. technique", "Validations manquantes", "Actions nécessaires"):
        assert column in table
    assert "READ_ONLY_ANALYSIS_NON_PRODUCTION" in md and "KDP                   = FORBIDDEN" in md


def test_synthesis_groups_and_orders_by_dependencies(report):
    syn = report["synthesis"]
    order = [s["component"] for s in syn["implementation_order"]]
    assert order[0] == "C1" and order[-1] == "C10"
    position = {c: i for i, c in enumerate(order)}
    for comp in COMPONENTS:
        assert all(position[d] < position[comp["id"]] for d in comp["depends_on"])
    dev = {item["component"]: item for item in syn["technical_development"]}
    assert dev["C2"]["pages"] == [14, 17, 25, 27, 34, 43, 46]
    assert len(dev["C8"]["pages"]) == 11 and len(dev["C6"]["pages"]) == 8
    assert syn["editorial_content_to_complete"]["SOLUTION_BLOCKED_BY_SOURCE"]["count"] == 31
    assert "PLAN_CORRECTION_STATUS_EMPTY" in {i["code"] for i in syn["documentary_inconsistencies"]}
    assert implementation_order({}) == implementation_order({})
    assert "Ordre d'implémentation" in render_synthesis(report)


# ---- structure defects --------------------------------------------------------------------------
def test_missing_page_is_reported_and_analysis_continues(tree):
    edit_csv(tree, PLAN, lambda rows: [r for r in rows if r["final_page"] != "30"])
    rep = analyze(tree)
    assert "PLAN_PAGE_COUNT" in codes(rep) and rep["analysis"]["structure_ok"] is False
    assert page(rep, 30)["plan_present"] is False and page(rep, 30)["technical"]["status"] == "UNKNOWN"
    assert "PAGE_ABSENT_FROM_PLAN" in {b["code"] for b in page(rep, 30)["blockers"]}
    assert validate_report(rep) == []
    assert page(rep, 31)["technical"]["status"] == "UNSUPPORTED"


def test_duplicated_page_is_reported(tree):
    def dup(rows):
        return rows + [dict(rows[11])]
    edit_csv(tree, PLAN, dup)
    rep = analyze(tree)
    assert "PLAN_DUPLICATE_PAGES" in codes(rep) and rep["analysis"]["structure_ok"] is False


def test_out_of_range_and_title_and_type_inconsistencies(tree):
    def mutate(rows):
        rows.append({**rows[0], "final_page": "57"})
        return rows
    edit_csv(tree, PLAN, mutate)
    assert "PLAN_OUT_OF_RANGE" in codes(analyze(tree))

    def retitle(rows):
        for r in rows:
            if r["final_page"] == "10":
                r["final_title"] = "Autre titre"
            if r["final_page"] == "16":
                r["final_type"] = "count"
        return rows
    edit_csv(tree, INSTR, retitle)
    rep = analyze(tree)
    assert {"TITLES_PLAN_VS_INSTRUCTIONS", "TYPES_PLAN_VS_INSTRUCTIONS"} <= codes(rep)
    finding = next(f for f in rep["findings"] if f["code"] == "TITLES_PLAN_VS_INSTRUCTIONS")
    assert finding["pages"] == [10]


def test_bad_answer_distribution(tree):
    def move(rows):
        for r in rows:
            if r["scenario"] == "B" and r["final_activity_page"] == "4":
                r["answer_page"] = "50"
        return rows
    edit_csv(tree, ANSW, move)
    rep = analyze(tree)
    assert {"ANSWERS_DISTRIBUTION", "ANSWER_PAGES_CONSISTENT"} <= codes(rep)
    assert next(c for c in rep["analysis"]["checks"] if c["id"] == "answers_distribution")["observed"] == [5, 6, 5, 5, 5, 5]


def test_free_activity_in_answers_and_missing_mapping(tree):
    def add(rows):
        rows.append({"scenario": "B", "answer_page": "54", "final_activity_page": "42", "old_activity_page": "42",
                     "title": "Décore le sac de Pip", "correction_type": "graphique", "kept": "yes"})
        return rows
    edit_csv(tree, ANSW, add)
    rep = analyze(tree)
    assert "ANSWERS_NO_FREE_ACTIVITY" in codes(rep) and "ANSWERS_COUNT" in codes(rep)


def test_missing_fr_en_instruction(tree):
    def blank(rows):
        for r in rows:
            if r["final_page"] == "15":
                r["final_en"] = ""
        return rows
    edit_csv(tree, INSTR, blank)
    rep = analyze(tree)
    assert "INSTRUCTIONS_FR_EN" in codes(rep)
    assert page(rep, 15)["sources"]["instruction"]["status"] == "ABSENT"
    assert "INSTRUCTION_FR_EN_MISSING" in {b["code"] for b in page(rep, 15)["blockers"]}


def test_historical_sources_confused_with_active(tree):
    def historical(rows):
        return rows + [{**rows[-1], "final_page": "49"}]
    edit_csv(tree, INSTR, historical)
    rep = analyze(tree)
    assert "HISTORICAL_NOT_ACTIVE" in codes(rep)

    def archive_row(rows):
        rows[0]["active_or_archive"] = "HISTORICAL_ARCHIVE"
        return rows
    edit_csv(tree, GRID, archive_row)
    assert "GRID_ACTIVE_ONLY" in codes(analyze(tree))


def test_archive_of_47_is_checked_but_never_planned(tree):
    edit_csv(tree, ARCH, lambda rows: rows[:-1])
    rep = analyze(tree)
    assert "ARCHIVE_B3A4_COUNT" in codes(rep)
    assert [p["page"] for p in rep["pages"]] == list(range(1, 57))


def test_c4_text_drift_and_lexicon_mismatch(tree):
    def drift(rows):
        for r in rows:
            if r["final_page"] == "6":
                r["final_fr"] = "Relie les points."
        return rows
    edit_csv(tree, INSTR, drift)
    assert "C4_P06_TEXT" in codes(analyze(tree))

    def lex(rows):
        for r in rows:
            if r["unit_id"] == "P55-LEX-01":
                r["fr_exact"] = "licorne"
        return rows
    edit_csv(tree, GRID, lex)
    assert "LEXICON_VS_BOOK" in codes(analyze(tree))


def test_legacy_plan_cannot_override_pagination(tree):
    base = analyze(tree)
    edit_csv(tree, LEGACY, lambda rows: [{**r, "activity_type": "maze"} for r in rows])
    other = analyze(tree)
    assert other["pages"] == base["pages"]


def test_unknown_plan_type_is_unknown_not_guessed(tree):
    def alien(rows):
        for r in rows:
            if r["final_page"] == "16":
                r["final_type"] = "hologram"
        return rows
    edit_csv(tree, PLAN, alien)
    rep = analyze(tree)
    assert page(rep, 16)["technical"]["status"] == "UNKNOWN" and page(rep, 16)["technical"]["open_questions"]


# ---- technical vs editorial independence ------------------------------------------------------------------
def test_technical_status_independent_of_editorial_state(tree, report):
    def approve(rows):
        for r in rows:
            for col in ("fr_review_status", "en_review_status", "bilingual_equivalence_status",
                        "age_4_5_mediation_status", "human_review_status"):
                r[col] = "VALIDATED"
            r["validator_identity"], r["evidence_reference"], r["final_status"] = "reviewer-1", "evidence-1", "VALIDATED"
        return rows
    edit_csv(tree, GRID, approve)
    rep = analyze(tree)
    assert [p["technical"] for p in rep["pages"]] == [p["technical"] for p in report["pages"]]
    assert page(rep, 4)["editorial"]["state"] == "VALIDATED"          # real human state is reflected, not invented
    assert "HUMAN_VALIDATIONS_EVIDENCE" in codes(rep)                  # but contradicts the recorded evidence (0)
    assert page(rep, 14)["technical"]["status"] == "PARTIAL"           # validated copy does not make the engine capable


def test_validated_without_evidence_is_not_trusted(tree):
    def claim(rows):
        for r in rows:
            if r["unit_id"] == "P03-ACTIVITY":
                r["human_review_status"], r["final_status"] = "VALIDATED", "VALIDATED"
        return rows
    edit_csv(tree, GRID, claim)
    rep = analyze(tree)
    assert "VALIDATION_WITHOUT_EVIDENCE" in codes(rep)
    assert page(rep, 3)["editorial"]["state"] == "NOT_VALIDATED"


def test_capability_rules_are_derived_from_engine_facts():
    facts = caps.engine_facts()
    assert caps.evaluate_page(4, "maze", "", facts)["status"] == "SUPPORTED"
    assert caps.evaluate_page(14, "maze", "", facts)["status"] == "PARTIAL"
    assert caps.evaluate_page(43, "maze", "HIGH", facts)["status"] == "PARTIAL"
    assert caps.evaluate_page(5, "find_count", "", facts)["status"] == "UNSUPPORTED"
    no_maze = {**facts, "generators": ["connect_dots", "match"]}
    assert caps.evaluate_page(4, "maze", "", no_maze)["status"] == "UNSUPPORTED"
    assert caps.evaluate_page(9, "wizardry", "", facts)["status"] == "UNKNOWN"
    assert facts["maze"]["size_fixed"] == 5 and facts["match"]["registry_families"] == ["shapes"]


# ---- determinism and read-only guarantees -------------------------------------------------------------------
def test_report_is_deterministic_across_runs_and_locations(tree, report):
    first, second = dumps_report(analyze(ROOT)), dumps_report(analyze(ROOT))
    assert first == second == dumps_report(report)
    assert dumps_report(analyze(tree)) == first        # path/mtime independent
    assert render_report(report) == render_report(analyze(ROOT))
    assert b"generated_at" not in first and str(ROOT).encode() not in first


def test_analysis_never_opens_a_file_for_writing(monkeypatch):
    real_open, real_os_open = builtins.open, os.open

    def guarded_open(file, mode="r", *a, **k):
        if any(c in str(mode) for c in "wax+"):
            raise AssertionError(f"écriture interdite : {file}")
        return real_open(file, mode, *a, **k)

    def guarded_os_open(path, flags, *a, **k):
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            raise AssertionError(f"écriture interdite : {path}")
        return real_os_open(path, flags, *a, **k)

    monkeypatch.setattr(builtins, "open", guarded_open)
    monkeypatch.setattr(os, "open", guarded_os_open)
    assert analyze(ROOT)["summary"]["pages_total"] == 56


def test_sources_untouched_by_cli_run(tree, tmp_path):
    before = snapshot(tree)
    out = tmp_path / "out"
    out.mkdir()
    assert cli_main(["analyze", "--root", str(tree), "--out-dir", str(out)]) == 0
    assert snapshot(tree) == before
    assert sorted(p.name for p in out.iterdir()) == ["scenario_b_report.json", "scenario_b_report.md", "scenario_b_synthesis.md"]
    first = (out / "scenario_b_report.json").read_bytes()
    assert cli_main(["analyze", "--root", str(tree), "--out-dir", str(out)]) == 2     # no silent overwrite
    assert cli_main(["analyze", "--root", str(tree), "--out-dir", str(out), "--overwrite"]) == 0
    assert (out / "scenario_b_report.json").read_bytes() == first
    assert cli_main(["validate-report", str(out / "scenario_b_report.json")]) == 0
    assert snapshot(tree) == before


@pytest.mark.parametrize("sub", ["docs/editorial/b3a/b3a3", "assets", "books/halloween_2026", "docs/editorial"])
def test_cli_refuses_to_write_into_sources(tree, sub):
    target = tree / sub
    before = sorted(p.name for p in target.iterdir())
    assert cli_main(["analyze", "--root", str(tree), "--out-dir", str(target)]) == 2
    assert sorted(p.name for p in target.iterdir()) == before


def test_cli_refuses_symlink_output_and_missing_dir(tree, tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    assert cli_main(["analyze", "--root", str(tree), "--out-dir", str(link)]) == 2
    assert cli_main(["analyze", "--root", str(tree), "--out-dir", str(tmp_path / "absent")]) == 2
    assert list(real.iterdir()) == []


def test_cli_strict_mode_exit_code(tree, tmp_path):
    out = tmp_path / "o"
    out.mkdir()
    assert cli_main(["analyze", "--root", str(tree), "--out-dir", str(out), "--strict"]) == 1   # known documentary contradiction
    assert cli_main(["analyze", "--root", str(tree), "--out-dir", str(out), "--overwrite"]) == 0


# ---- fatal structure errors -------------------------------------------------------------------------------------
def test_missing_required_source_is_fatal(tree):
    (tree / PLAN).unlink()
    with pytest.raises(ReaderError) as exc:
        analyze(tree)
    assert "source obligatoire absente" in str(exc.value)


def test_missing_column_ragged_row_and_bad_utf8_are_fatal(tree):
    path = tree / INSTR
    original = path.read_bytes()
    path.write_bytes(original.replace(b"final_fr", b"fr_final", 1))
    with pytest.raises(ReaderError, match="colonne"):
        analyze(tree)
    path.write_bytes(original + b"1,2,3\n")
    with pytest.raises(ReaderError, match="champs"):
        analyze(tree)
    path.write_bytes(original + b"\xff\xfe\n")
    with pytest.raises(ReaderError, match="UTF-8"):
        analyze(tree)


def test_symlinked_source_is_refused(tree, tmp_path):
    real = tmp_path / "elsewhere.csv"
    real.write_bytes((tree / PLAN).read_bytes())
    (tree / PLAN).unlink()
    (tree / PLAN).symlink_to(real)
    with pytest.raises(ReaderError):
        analyze(tree)


def test_cli_reports_fatal_error_without_traceback(tree, tmp_path, capsys):
    (tree / GRID).unlink()
    out = tmp_path / "o"
    out.mkdir()
    assert cli_main(["analyze", "--root", str(tree), "--out-dir", str(out)]) == 2
    assert "ANALYSE IMPOSSIBLE" in capsys.readouterr().err
    assert list(out.iterdir()) == []


def test_permanent_gates_come_from_code_not_sources(tree):
    path = tree / EVID
    data = json.loads(path.read_text(encoding="utf-8"))
    data["statuses"]["KDP"] = "ALLOWED"
    path.write_text(json.dumps(data), encoding="utf-8")
    rep = analyze(tree)
    assert rep["gates"]["KDP"] == "FORBIDDEN" and rep["ready_for_kdp"] is False
    assert "GATES_CONSISTENT" in codes(rep)


# ---- schema, isolation, no network ---------------------------------------------------------------------------------
def test_schema_rejects_tampered_reports(report):
    def broken(mutate):
        clone = copy.deepcopy(report)
        mutate(clone)
        return validate_report(clone)
    assert broken(lambda r: r["gates"].__setitem__("KDP", "ALLOWED"))
    assert broken(lambda r: r.__setitem__("ready_for_kdp", True))
    assert broken(lambda r: r["pages"].pop())
    assert broken(lambda r: r["pages"][3]["technical"].__setitem__("status", "OK"))
    assert broken(lambda r: r["pages"][3].__setitem__("extra", 1))
    assert broken(lambda r: r["provenance"]["sources"][0].__setitem__("sha256", "xyz"))
    assert broken(lambda r: r.__setitem__("kind", "PRODUCTION"))
    assert broken(lambda r: r["findings"].append({"severity": "BOGUS"}))


def test_reader_is_isolated_and_offline():
    pkg = ROOT / "src/lafractale/scenario_b"
    forbidden = {"socket", "requests", "urllib", "http", "httpx", "anthropic", "openai", "subprocess", "reportlab", "fitz"}
    for path in pkg.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module] if isinstance(node, ast.ImportFrom) and node.module else []
            assert not {n.split(".")[0] for n in names} & forbidden, (path.name, names)
    for path in (ROOT / "src/lafractale").rglob("*.py"):
        if "scenario_b" in path.parts:
            continue
        assert "scenario_b" not in path.read_text(encoding="utf-8"), path


def test_report_does_not_leak_absolute_paths(report):
    assert "/home/" not in json.dumps(report) and "/tmp/" not in json.dumps(report)


def test_cli_refuses_symlinked_path_into_sources(tree, tmp_path):
    link_parent = tmp_path / "via"
    link_parent.symlink_to(tree / "docs/editorial")
    before = sorted(p.name for p in (tree / "docs/editorial/b3a").iterdir())
    assert cli_main(["analyze", "--root", str(tree), "--out-dir", str(link_parent / "b3a")]) == 2
    assert sorted(p.name for p in (tree / "docs/editorial/b3a").iterdir()) == before


def test_manifest_cannot_point_outside_its_directory(tree):
    path = tree / f"{B3A}/b3a4/09_integrity_manifest.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["records"][0]["path"] = "../b3a3/00_README.md"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert "INTEGRITY_B3A4" in codes(analyze(tree))


def test_committed_demo_report_is_current(report):
    demo = ROOT / "docs/b3b2/demo"
    assert (demo / "scenario_b_report.json").read_bytes() == dumps_report(report), \
        "régénérer : python -m lafractale.scenario_b analyze --root . --out-dir docs/b3b2/demo --overwrite"
    assert (demo / "scenario_b_report.md").read_text(encoding="utf-8") == render_report(report)
    assert (demo / "scenario_b_synthesis.md").read_text(encoding="utf-8") == render_synthesis(report)
