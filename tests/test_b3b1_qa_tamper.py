"""The QA must detect a package or a PDF that no longer matches its source."""
import json
import shutil

import pytest

from b3b1_support import FIXTURE, mutated
from lafractale.engine.contracts import canonical_json_bytes, load_spec_set
from lafractale.engine.pipeline import audit_existing_package, build_activities, generate_package
from lafractale.engine.qa import content_checks
from lafractale.engine.render import ANSWER_NAME, INTERIOR_NAME, MANIFEST_NAME, REPORT_NAME, render_slice


@pytest.fixture(scope="module")
def pristine(tmp_path_factory):
    out = tmp_path_factory.mktemp("pristine") / "pkg"
    generate_package(FIXTURE, out)
    return out


@pytest.fixture
def package(pristine, tmp_path):
    copy = tmp_path / "pkg"
    shutil.copytree(pristine, copy)
    return copy


def test_untouched_copy_audits_clean(package):
    assert audit_existing_package(package, FIXTURE) == []


def test_modified_pdf_is_detected(package):
    pdf = package / INTERIOR_NAME
    pdf.write_bytes(pdf.read_bytes() + b"\n%tampered")
    errors = audit_existing_package(package, FIXTURE)
    assert any(INTERIOR_NAME in e or "manifest" in e for e in errors)


def test_modified_activities_json_is_detected(package):
    path = package / "activities.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data[0]["answer"]["steps"] += 1
    path.write_bytes(canonical_json_bytes(data))
    assert any("activities.json" in e for e in audit_existing_package(package, FIXTURE))


def test_forged_report_is_detected_even_with_matching_manifest(package):
    path = package / REPORT_NAME
    report = json.loads(path.read_text(encoding="utf-8"))
    report["ready_for_kdp"] = True
    path.write_bytes(canonical_json_bytes(report))
    manifest = json.loads((package / MANIFEST_NAME).read_text(encoding="utf-8"))
    import hashlib
    manifest["files"][REPORT_NAME] = hashlib.sha256(path.read_bytes()).hexdigest()
    (package / MANIFEST_NAME).write_bytes(canonical_json_bytes(manifest))
    assert any("quality_report.json" in e for e in audit_existing_package(package, FIXTURE))


def test_missing_and_extra_files_are_detected(package):
    (package / ANSWER_NAME).unlink()
    assert any("manquant" in e for e in audit_existing_package(package, FIXTURE))
    (package / "extra.txt").write_text("x")
    assert any("non autorisé" in e for e in audit_existing_package(package, FIXTURE))


def test_symlink_inside_package_is_detected(package):
    (package / "activities.json").unlink()
    (package / "activities.json").symlink_to(package / "manifest.json")
    assert any("non régulière" in e for e in audit_existing_package(package, FIXTURE))


def test_embedded_source_swapped_is_detected_against_trusted_source(package, tmp_path):
    (package / "sources" / "spec.json").write_bytes(mutated(lambda d: d.update(seed=5)))
    assert audit_existing_package(package, FIXTURE)


def _render_with_seed(tmp_path, seed):
    spec_file = tmp_path / f"seed{seed}.json"
    spec_file.write_bytes(mutated(lambda d: d.update(seed=seed)))
    spec = load_spec_set(spec_file)
    result = build_activities(spec)
    out = tmp_path / f"render{seed}"
    out.mkdir()
    return render_slice(spec, result.activities, out)


def test_qa_detects_pdfs_drawn_for_other_puzzles(tmp_path):
    """Self-consistent PDFs of a different seed must not pass for the audited activities."""
    spec = load_spec_set(FIXTURE)
    activities = build_activities(spec).activities
    interior, answer = _render_with_seed(tmp_path, 4242)
    checks = content_checks(spec, activities, interior, answer)
    failed = {c["id"] for c in checks if c["status"] == "FAIL"}
    assert "pdf.answer_matches_activity" in failed
    detail = next(c["detail"] for c in checks if c["id"] == "pdf.answer_matches_activity")
    assert "labyrinthe" in detail and "points" in detail and "association" in detail


def test_qa_detects_swapped_interior_and_answer_key(tmp_path):
    spec = load_spec_set(FIXTURE)
    activities = build_activities(spec).activities
    out = tmp_path / "r"
    out.mkdir()
    interior, answer = render_slice(spec, activities, out)
    checks = content_checks(spec, activities, answer, interior)  # roles swapped
    failed = {c["id"] for c in checks if c["status"] == "FAIL"}
    assert {"pdf.title", "pdf.answer_superset_of_fiche"} <= failed


def test_qa_detects_missing_source_text_in_pdf(tmp_path):
    """PDFs rendered with different prompts do not carry the audited source texts."""
    spec = load_spec_set(FIXTURE)
    activities = build_activities(spec).activities
    other_file = tmp_path / "other.json"
    other_file.write_bytes(mutated(lambda d: d["pages"][0].update(prompt_fr="Un tout autre texte.")))
    other = load_spec_set(other_file)
    out = tmp_path / "o"
    out.mkdir()
    interior, answer = render_slice(other, build_activities(other).activities, out)
    failed = {c["id"]: c["detail"] for c in content_checks(spec, activities, interior, answer) if c["status"] == "FAIL"}
    assert "pdf.source_text.prompt_fr" in failed


class _SwapLabels:
    """Fitz page whose text words 3 and 7 are exchanged (labels on the wrong dots)."""

    def __init__(self, page):
        self._page = page

    def get_text(self, mode="text"):
        result = self._page.get_text(mode)
        if mode != "words":
            return result
        swap = {"3": "7", "7": "3"}
        return [(*w[:4], swap.get(w[4], w[4]), *w[5:]) for w in result]

    def __getattr__(self, name):
        return getattr(self._page, name)


def test_dots_labels_on_the_wrong_dots_are_detected(pristine):
    try:
        import pymupdf as fitz
    except ImportError:  # pragma: no cover
        import fitz
    from lafractale.engine import qa
    spec = load_spec_set(FIXTURE)
    star = build_activities(spec).activities[1]  # 10-point star
    with fitz.open(pristine / INTERIOR_NAME) as interior, fitz.open(pristine / ANSWER_NAME) as answer:
        assert qa._dots_coherence(star, interior[1], answer[1]) == []
        errors = qa._dots_coherence(star, _SwapLabels(interior[1]), answer[1])
    assert any("numéro 3" in e or "numéro 7" in e for e in errors), errors


def test_mirrored_drawing_cannot_match_the_activity_geometry():
    from lafractale.engine import qa
    xs = [0.1, 0.4, 0.9]
    straight, mirrored = [10.0, 40.0, 90.0], [90.0, 60.0, 10.0]
    assert qa._affine_residual(xs, straight, +1) < 1e-6
    assert qa._affine_residual(xs, mirrored, +1) > 10
    assert qa._affine_residual(xs, mirrored, -1) < 1e-6


def test_page_count_mismatch_does_not_hide_other_findings(tmp_path):
    spec = load_spec_set(FIXTURE)
    activities = build_activities(spec).activities
    short_file = tmp_path / "short.json"
    import json
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    data["pages"] = data["pages"][:3]
    short_file.write_bytes(json.dumps(data).encode())
    short = load_spec_set(short_file)
    short_out, full_out = tmp_path / "s", tmp_path / "f"
    short_out.mkdir(), full_out.mkdir()
    short_interior, _ = render_slice(short, build_activities(short).activities, short_out)
    _, full_answer = render_slice(spec, activities, full_out)
    checks = {c["id"]: c for c in content_checks(spec, activities, short_interior, full_answer)}
    assert checks["pdf.interior.page_count"]["status"] == "FAIL"
    assert checks["pdf.answer_key.page_count"]["status"] == "PASS"
    assert "pdf.source_text.prompt_fr" in checks  # the answer key was still analysed


def test_unreadable_pdf_is_a_failed_check_not_an_exception(tmp_path):
    spec = load_spec_set(FIXTURE)
    activities = build_activities(spec).activities
    junk = tmp_path / "junk.pdf"
    junk.write_bytes(b"%PDF-1.4 definitely not a pdf")
    checks = content_checks(spec, activities, junk, junk)
    assert any(c["status"] == "FAIL" and c["id"] in {"pdf.readable", "pdf.analysis"} for c in checks)


def test_non_canonical_pdf_date_is_reported_explicitly(package):
    pdf = package / INTERIOR_NAME
    data = pdf.read_bytes()
    assert data.count(b"D:20000101000000") == 2  # CreationDate and ModDate
    pdf.write_bytes(data.replace(b"D:20000101000000", b"D:20000101000001"))  # same length: xref intact
    errors = audit_existing_package(package, FIXTURE)
    assert any("date canonique" in e for e in errors), errors
