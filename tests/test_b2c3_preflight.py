"""Adversarial tests for the read-only B2-C3 pre-press preflight.

Covers the 14 direct-test categories from the B2-C3 test plan (doc 04 §A):
the analyzer must diagnose, never mutate, never trust forged inputs, keep the
tool verdict separate from the page verdict, and never declare KDP-ready.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import fitz
import pytest

ROOT = Path(__file__).resolve().parents[1]
PIN = "93c58e86a74e903af1be5cd4257d489c39bece8f5cd41d985586cbf775d45e61"
DEJAVU = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOOK = ROOT / "books" / "halloween_2026" / "book.yaml"
PREFLIGHT = ROOT / "tools" / "preflight_b2c3.py"


def _load_preflight():
    spec = importlib.util.spec_from_file_location("preflight_b2c3", PREFLIGHT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def preflight():
    return _load_preflight()


@pytest.fixture(scope="session")
def book():
    from lafractale.config.schema import load_book
    return load_book(BOOK)


@pytest.fixture(scope="session")
def layouts(preflight, book):
    _, interiors, answers = preflight._recompute_layouts(book)
    return interiors, answers


@pytest.fixture(scope="session")
def c2_out(tmp_path_factory):
    out = tmp_path_factory.mktemp("b2c3_c2_out")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    env["SOURCE_DATE_EPOCH"] = "1780000000"
    subprocess.run(
        [sys.executable, "-m", "lafractale", "build-demo", str(BOOK), "--out", str(out),
         "--illustration-routing", "halloween-pip-demo-v1",
         "--pip-placement", "halloween-pip-placement-v2", "--approvals-sha256", PIN],
        cwd=ROOT, env=env, check=True, capture_output=True, text=True,
    )
    return out


def _run(c2_out, report_dir, policy="halloween-pip-placement-v2", pin=PIN,
         editorial_profile=None):
    command = [
        sys.executable, str(PREFLIGHT), "--out", str(c2_out), "--book", str(BOOK),
        "--policy", policy, "--approvals-sha256", pin,
    ]
    if editorial_profile is not None:
        command.extend(["--editorial-profile", editorial_profile])
    command.extend(["--report-dir", str(report_dir)])
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True)


def _crafted_page(preflight, layout, *, size=None, fontname=None, color=None, text="txt",
                  point=(100, 200)):
    """Return (page, findings) after analysing a single crafted page."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    kwargs = {}
    if fontname == "embedded":
        page.insert_font(fontname="F0", fontfile=DEJAVU)
        kwargs["fontname"] = "F0"
    elif fontname is not None:
        kwargs["fontname"] = fontname
    if size is not None:
        kwargs["fontsize"] = size
    if color is not None:
        kwargs["color"] = color
    page.insert_text(point, text, **kwargs)
    findings = []
    preflight._analyze_page(page, layout, source="t.pdf", page_label="p1", findings=findings)
    doc.close()
    return page, findings


# --------------------------------------------------------------------------
# 1. valid PDFs, reproducible, no PDF modified
# --------------------------------------------------------------------------
def test_valid_outputs_pass_and_generate_six_boards(c2_out, tmp_path):
    before = {p.name: _sha_file(p) for p in (c2_out / "interior.pdf", c2_out / "answer_key.pdf")}
    report = tmp_path / "r"
    result = _run(c2_out, report)
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads((report / "b2c3_preflight.json").read_text())
    assert payload["diagnostic"]["status"] == "PASS_DIAGNOSTIC_TECHNIQUE"
    assert payload["diagnostic"]["qa_status"] == "PASS"
    boards = [p.name for p in (report).glob("board_*.png")]
    assert len(boards) == 6
    after = {p.name: _sha_file(p) for p in (c2_out / "interior.pdf", c2_out / "answer_key.pdf")}
    assert before == after, "les PDF de sortie ne doivent pas être modifiés"


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------
# 2. wrong page count, rotated page, unexpected MediaBox, corrupted PDF
# --------------------------------------------------------------------------
def test_corrupted_pdf_fails_without_approval(c2_out, tmp_path):
    out = tmp_path / "out"
    shutil.copytree(c2_out, out)
    (out / "interior.pdf").write_bytes(b"not a pdf")
    report = tmp_path / "r"
    result = _run(out, report)
    payload = json.loads((report / "b2c3_preflight.json").read_text())
    assert payload["diagnostic"]["status"] == "FAIL_DIAGNOSTIC_TECHNIQUE"
    assert payload["kdp"]["status"] == "FORBIDDEN"


def test_rotated_page_is_diagnosed(preflight, layouts):
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.set_rotation(90)
    findings = []
    preflight._analyze_page(page, layouts[0][0], source="t.pdf", page_label="p1", findings=findings)
    doc.close()
    assert any(f["rule_id"] == "structure.rotation" and f["severity"] == "BLOCKER" for f in findings)


def test_unexpected_page_size_is_diagnosed(preflight, layouts):
    doc = fitz.open()
    page = doc.new_page(width=400, height=500)
    findings = []
    preflight._analyze_page(page, layouts[0][0], source="t.pdf", page_label="p1", findings=findings)
    doc.close()
    assert any(f["rule_id"] == "structure.page_size" and f["severity"] == "BLOCKER" for f in findings)


# --------------------------------------------------------------------------
# 3. fake 72 dpi image, DPI near threshold (decoded pixels x drawn bbox)
# --------------------------------------------------------------------------
def test_low_dpi_image_is_detected_from_drawn_bbox(preflight, layouts):
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    pix = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 72, 72), 0)
    page.insert_image(fitz.Rect(100, 300, 172, 372), pixmap=pix)
    findings = []
    preflight._analyze_page(page, layouts[0][0], source="t.pdf", page_label="p1", findings=findings)
    doc.close()
    dpi = [f for f in findings if f["rule_id"] == "image.dpi"]
    assert dpi, "le contrôle DPI doit s'exécuter"
    assert dpi[0]["observed"]["dpi_x"] < 300 and dpi[0]["severity"] == "BLOCKER"


# --------------------------------------------------------------------------
# 4. 6.9 pt FAIL / 7.0 pt no threshold fail / EN 10 pt pedagogical notice
# --------------------------------------------------------------------------
def test_font_6_9pt_is_blocker(preflight, layouts):
    _, findings = _crafted_page(preflight, layouts[0][0], size=6.9, fontname="embedded")
    assert any(f["rule_id"] == "font.min_size_below_kdp" and f["severity"] == "BLOCKER"
               for f in findings)


def test_font_7_0pt_has_no_threshold_fail(preflight, layouts):
    _, findings = _crafted_page(preflight, layouts[0][0], size=7.0, fontname="embedded")
    assert not any(f["rule_id"] == "font.min_size_below_kdp" for f in findings)


def test_english_consigne_10pt_is_pedagogical_not_kdp_fail(preflight, layouts):
    # prompt_en region is around PDF y ~230; place a 10 pt EN consigne there.
    _, findings = _crafted_page(
        preflight, layouts[0][0], size=10.0, fontname="embedded",
        text="Find a path", point=(80, 235),
    )
    hits = [f for f in findings if f["rule_id"] == "font.consigne_size"]
    assert hits and all(f["severity"] == "WARN" and f["kind"] == "EDITORIAL_ADVISORY" for f in hits)
    assert not any(f["rule_id"] == "font.min_size_below_kdp" for f in findings)


# --------------------------------------------------------------------------
# 5. non-embedded font, missing glyph, hidden text, low contrast
# --------------------------------------------------------------------------
def test_non_embedded_used_font_is_blocker(preflight, layouts):
    _, findings = _crafted_page(preflight, layouts[0][0], size=12, fontname="helv")
    assert any(f["rule_id"] == "font.non_embedded_used" and f["severity"] == "BLOCKER"
               for f in findings)


def test_low_contrast_consigne_is_warned(preflight, layouts):
    _, findings = _crafted_page(
        preflight, layouts[0][0], size=12, fontname="embedded",
        text="Find a path", point=(80, 235), color=(0.85, 0.85, 0.85),
    )
    assert any(f["rule_id"] == "text.consigne_contrast" and f["severity"] == "WARN"
               for f in findings)


# --------------------------------------------------------------------------
# 6. 0.5 pt functional stroke vs 0.75 pt recommendation
# --------------------------------------------------------------------------
def test_thin_functional_stroke_classified_as_major(preflight, layouts):
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.draw_line(fitz.Point(100, 500), fitz.Point(200, 500), width=0.5)
    findings = []
    preflight._analyze_page(page, layouts[0][0], source="t.pdf", page_label="p1", findings=findings)
    doc.close()
    hits = [f for f in findings if f["rule_id"] == "line.thin_stroke"]
    assert hits, "trait 0.5 pt doit être signalé"
    assert hits[0]["severity"] in ("MAJOR", "WARN")


# --------------------------------------------------------------------------
# 7. bleed: no-bleed 612x792 / bleed 621x810, to_be_confirmed -> never PASS
# --------------------------------------------------------------------------
def test_bleed_is_never_decided_by_default(c2_out, tmp_path):
    result = _run(c2_out, tmp_path / "r")
    payload = json.loads((tmp_path / "r" / "b2c3_preflight.json").read_text())
    assert payload["prepress"]["bleed"]["decision"] == "UNDECIDED"
    assert payload["prepress"]["bleed"]["no_bleed_envelope_pt"] == [612.0, 792.0]
    assert payload["prepress"]["bleed"]["with_bleed_envelope_pt"] == [621.0, 810.0]


# --------------------------------------------------------------------------
# 8. inner 27 pt / outer 18-27 pt margins (conservative both sides)
# --------------------------------------------------------------------------
def test_tight_inner_margin_is_detected(preflight, layouts):
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_font(fontname="F0", fontfile=DEJAVU)
    page.insert_text((5, 400), "colle au bord", fontsize=12, fontname="F0")
    findings = []
    preflight._analyze_page(page, layouts[0][0], source="t.pdf", page_label="p1", findings=findings)
    doc.close()
    assert any(f["rule_id"] == "margin.inner_below_min" for f in findings)


# --------------------------------------------------------------------------
# 9. injection: forged manifest/PDF metadata must never become authority
# --------------------------------------------------------------------------
def test_forged_manifest_never_grants_kdp_approval(c2_out, tmp_path):
    out = tmp_path / "out"
    shutil.copytree(c2_out, out)
    manifest = out / "manifest.json"
    data = json.loads(manifest.read_text())
    data["publication_approved"] = True
    data["ready_for_kdp"] = True
    data["kdp_homologated_by_amazon"] = True
    manifest.write_text(json.dumps(data))
    report = tmp_path / "r"
    _run(out, report)
    payload = json.loads((report / "b2c3_preflight.json").read_text())
    assert payload["kdp"]["status"] == "FORBIDDEN"
    assert payload["editorial"]["status"] == "PENDING"
    raw = json.dumps(payload)
    assert '"ready_for_kdp": true' not in raw
    assert '"publication_approved": true' not in raw


# --------------------------------------------------------------------------
# 10. report-dir safety: inside out / pre-existing / symlink / collision
# --------------------------------------------------------------------------
def test_report_dir_inside_out_is_refused(c2_out, tmp_path):
    result = _run(c2_out, c2_out / "nested-report")
    assert result.returncode == 2
    assert not (c2_out / "nested-report").exists()


def test_pre_existing_report_dir_is_refused(c2_out, tmp_path):
    report = tmp_path / "r"
    report.mkdir()
    (report / "occupied.txt").write_text("x")
    result = _run(c2_out, report)
    assert result.returncode == 2


def test_symlink_report_dir_is_refused(c2_out, tmp_path):
    target = tmp_path / "real"
    target.mkdir()
    link = tmp_path / "r-link"
    link.symlink_to(target)
    result = _run(c2_out, link)
    assert result.returncode == 2


def test_report_dir_under_parent_with_hidden_entry_is_accepted(c2_out, tmp_path):
    parent = tmp_path / "parent"
    parent.mkdir()
    (parent / ".hidden").write_text("x")
    report = parent / "r"
    result = _run(c2_out, report)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (report / "b2c3_preflight.json").exists()


def test_unknown_policy_is_refused(c2_out, tmp_path):
    result = _run(c2_out, tmp_path / "r", policy="halloween-pip-placement-v3")
    assert result.returncode == 2


# --------------------------------------------------------------------------
# 11. mutation during analysis / symlink / special file: frozen bytes or FAIL
# --------------------------------------------------------------------------
def test_symlink_pdf_read_is_refused(preflight, tmp_path):
    real = tmp_path / "real.pdf"
    real.write_bytes(b"%PDF-1.4")
    link = tmp_path / "interior.pdf"
    link.symlink_to(real)
    with pytest.raises(OSError):
        preflight._anchored_file_bytes(link)


# --------------------------------------------------------------------------
# 12. two runs same inputs -> byte-identical canonical reports
# --------------------------------------------------------------------------
def test_deterministic_reports(c2_out, tmp_path):
    r1 = tmp_path / "r1"
    r2 = tmp_path / "r2"
    assert _run(c2_out, r1).returncode == 0
    assert _run(c2_out, r2).returncode == 0
    assert (r1 / "b2c3_preflight.json").read_bytes() == (r2 / "b2c3_preflight.json").read_bytes()
    assert (r1 / "b2c3_preflight.md").read_bytes() == (r2 / "b2c3_preflight.md").read_bytes()


# --------------------------------------------------------------------------
# 13. never write/modify book.yaml, page_plan.csv, Pip PNGs, registry, out files
# --------------------------------------------------------------------------
def test_no_source_or_output_mutation(c2_out, tmp_path):
    sources = [
        ROOT / "books" / "halloween_2026" / "book.yaml",
        ROOT / "books" / "halloween_2026" / "page_plan.csv",
        ROOT / "assets" / "illustrations" / "approvals.json",
    ]
    before_src = {str(p): _sha_file(p) for p in sources}
    before_out = {str(p): _sha_file(p) for p in sorted(c2_out.rglob("*")) if p.is_file()}
    report = tmp_path / "r"
    assert _run(c2_out, report).returncode == 0
    after_src = {str(p): _sha_file(p) for p in sources}
    after_out = {str(p): _sha_file(p) for p in sorted(c2_out.rglob("*")) if p.is_file()}
    assert before_src == after_src, "les fichiers source ne doivent pas être modifiés"
    assert before_out == after_out, "aucune sortie C2 ne doit être modifiée"


# --------------------------------------------------------------------------
# 14. valid artefact with editorial readability defect: keep verdicts separate
# --------------------------------------------------------------------------
def test_tool_pass_separated_from_page_warn_no_kdp_ready(c2_out, tmp_path):
    result = _run(c2_out, tmp_path / "r")
    assert result.returncode == 0
    payload = json.loads((tmp_path / "r" / "b2c3_preflight.json").read_text())
    assert payload["diagnostic"]["status"] == "PASS_DIAGNOSTIC_TECHNIQUE"
    assert payload["prepress"]["status"] in ("WARN", "FAIL", "PASS")
    assert payload["editorial"]["status"] == "PENDING"
    assert payload["kdp"]["status"] == "FORBIDDEN"
    # the PIN value must never leak into the proofs
    assert PIN not in json.dumps(payload)


# --------------------------------------------------------------------------
# 15. C4 explicit preflight: static editorial recomputation + Pip bbox C2 V2
# --------------------------------------------------------------------------
def test_c4_profile_preflight_recomputes_variant_and_checks_pip_bbox(tmp_path, monkeypatch):
    from lafractale.export.builder import build_demo
    from lafractale.editorial import EDITORIAL_HALLOWEEN_V1
    from lafractale.config.schema import load_book

    # The trust replay compares PDF bytes. Pin the documented reproducibility
    # epoch for this subprocess-facing C4 integration test rather than relying
    # on the ambient CI environment.
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1780000000")
    out = tmp_path / "c4-out"
    build_demo(
        load_book(BOOK), out, illustration_routing="halloween-pip-demo-v1",
        pip_placement="halloween-pip-placement-v2", editorial_profile=EDITORIAL_HALLOWEEN_V1,
        trusted_approvals_sha256=PIN,
    )
    report = tmp_path / "c4-report"
    result = _run(out, report, editorial_profile=EDITORIAL_HALLOWEEN_V1)
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads((report / "b2c3_preflight.json").read_text())
    assert payload["diagnostic"]["status"] == "PASS_DIAGNOSTIC_TECHNIQUE"
    assert payload["diagnostic"]["qa_status"] == "PASS"
    assert payload["diagnostic"]["qa_label"] == "QA C4 éditoriale"
    assert payload["diagnostic"]["inputs"]["editorial_profile"] == EDITORIAL_HALLOWEEN_V1
    findings = payload["findings"]
    assert len([f for f in findings if f["rule_id"] == "pip.bbox" and f["severity"] == "INFO"]) == 6
    assert not any(f["rule_id"] == "pip.bbox" and f["severity"] == "BLOCKER" for f in findings)
    assert not any(f["rule_id"] == "font.editorial_role_size" for f in findings)


def test_unknown_c4_profile_is_refused_before_analysis(c2_out, tmp_path):
    result = _run(c2_out, tmp_path / "r", editorial_profile="halloween-editorial-v99")
    assert result.returncode == 2
    assert not (tmp_path / "r").exists()
