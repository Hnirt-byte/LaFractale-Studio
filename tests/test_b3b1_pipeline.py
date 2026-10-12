"""End-to-end B3-B.1 slice: generation, determinism, QA, output safety, CLI."""
import json
import os
import re
from pathlib import Path

import pytest

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz

from b3b1_support import FIXTURE, mutated, spec_dict
from lafractale.engine import GATES, EngineError
from lafractale.engine.contracts import load_spec_set
from lafractale.engine.main import main
from lafractale.engine.pipeline import audit_existing_package, build_activities, generate_package
from lafractale.engine.render import ANSWER_NAME, INTERIOR_NAME, PACKAGE_FILES


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    root = tmp_path_factory.mktemp("b3b1")
    first = root / "alpha" / "pkg"
    second = root / "elsewhere" / "deeper" / "other-name"
    h1 = generate_package(FIXTURE, first)
    h2 = generate_package(FIXTURE, second)
    return {"first": first, "second": second, "h1": h1, "h2": h2}


def _tree(path: Path) -> dict[str, bytes]:
    return {p.relative_to(path).as_posix(): p.read_bytes() for p in sorted(path.rglob("*")) if p.is_file()}


def test_package_has_exact_closed_inventory(built):
    assert sorted(_tree(built["first"])) == sorted(PACKAGE_FILES)


def test_two_independent_generations_are_byte_identical(built):
    assert _tree(built["first"]) == _tree(built["second"])
    assert built["h1"] == built["h2"]


def test_outputs_are_deterministic_for_repeated_validation_in_memory():
    spec = load_spec_set(FIXTURE)
    assert build_activities(spec).activities == build_activities(spec).activities


def test_no_absolute_path_or_machine_state_in_outputs(built):
    for name, content in _tree(built["first"]).items():
        if name.endswith(".json"):
            text = content.decode("utf-8")
            assert str(built["first"]) not in text and "/tmp" not in text and "/home" not in text, name
            assert not re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:", text), f"timestamp in {name}"


def test_manifest_uses_stable_relative_paths_and_matches_files(built):
    manifest = json.loads((built["first"] / "manifest.json").read_text(encoding="utf-8"))
    tree = _tree(built["first"])
    assert set(manifest["files"]) == set(PACKAGE_FILES) - {"manifest.json"}
    for name, digest in manifest["files"].items():
        assert not name.startswith("/") and ".." not in name
        import hashlib
        assert hashlib.sha256(tree[name]).hexdigest() == digest


def test_report_and_manifest_declare_synthetic_and_keep_gates(built):
    for name in ("quality_report.json", "manifest.json"):
        data = json.loads((built["first"] / name).read_text(encoding="utf-8"))
        assert data["kind"] == "SYNTHETIC_NON_PRODUCTION"
        assert data["ready_for_kdp"] is False
        assert data["gates"] == dict(GATES) == {
            "MAJOR-03": "OPEN", "MAJOR-04": "OPEN", "EDITORIAL": "PENDING",
            "KDP": "FORBIDDEN", "PRODUCTION_GENERATION": "FORBIDDEN"}
    report = json.loads((built["first"] / "quality_report.json").read_text(encoding="utf-8"))
    assert report["pass"] is True and report["human_validations_recorded"] == 0
    assert not [c for c in report["checks"] if c["status"] == "FAIL"]
    assert any(c["id"] == "pdf.fonts.base14_helvetica_reference" and c["status"] == "WARN" for c in report["checks"])


def test_source_texts_are_really_in_both_pdfs(built):
    spec = spec_dict()
    for name in (INTERIOR_NAME, ANSWER_NAME):
        with fitz.open(built["first"] / name) as pdf:
            assert len(pdf) == 6
            for page, source in zip(pdf, spec["pages"]):
                text = " ".join(page.get_text().split())
                assert source["prompt_fr"] in text and source["prompt_en"] in text and source["scene"] in text
    with fitz.open(built["first"] / ANSWER_NAME) as pdf:
        assert all("CORRIGÉ" in " ".join(p.get_text().split()) for p in pdf)
    with fitz.open(built["first"] / INTERIOR_NAME) as pdf:
        assert not any("CORRIGÉ" in p.get_text() for p in pdf)


def test_pdfs_are_letter_sized_unillustrated_and_embed_fonts(built):
    for name in (INTERIOR_NAME, ANSWER_NAME):
        with fitz.open(built["first"] / name) as pdf:
            for page in pdf:
                assert (round(page.rect.width), round(page.rect.height)) == (612, 792)
                assert not page.get_images()
                assert any("DejaVu" in font[3] for font in page.get_fonts())


def test_audit_passes_with_embedded_and_with_independent_source(built):
    assert audit_existing_package(built["first"]) == []
    assert audit_existing_package(built["second"], FIXTURE) == []


def test_audit_with_a_different_trusted_source_fails(built, tmp_path):
    other = tmp_path / "other.json"
    other.write_bytes(mutated(lambda d: d.update(seed=99)))
    assert audit_existing_package(built["first"], other)


def test_existing_file_is_never_overwritten(tmp_path):
    target = tmp_path / "out"
    target.mkdir()
    keep = target / "interior_SYNTHETIC_NON_PRODUCTION.pdf"
    keep.write_bytes(b"precious")
    with pytest.raises(EngineError, match="non vide"):
        generate_package(FIXTURE, target)
    assert keep.read_bytes() == b"precious" and [p.name for p in target.iterdir()] == [keep.name]


def test_empty_existing_directory_is_accepted_and_symlink_destination_refused(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    generate_package(FIXTURE, empty)
    assert (empty / "manifest.json").is_file()
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    with pytest.raises(EngineError, match="répertoire réel"):
        generate_package(FIXTURE, link)
    assert not any(real.iterdir())


def test_failed_generation_leaves_nothing_behind(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_bytes(mutated(lambda d: d["pages"][0].update(prompt_fr="mot " * 29)))
    out = tmp_path / "never"
    with pytest.raises(EngineError):
        generate_package(bad, out)
    assert not out.exists()


def test_layout_overflow_is_refused_before_any_output(tmp_path):
    bad = tmp_path / "overflow.json"
    bad.write_bytes(mutated(lambda d: d["pages"][1].update(prompt_en="W" * 79)))
    out = tmp_path / "never2"
    with pytest.raises(EngineError):
        generate_package(bad, out)
    assert not out.exists()


def test_changing_the_seed_changes_the_puzzles_but_not_the_texts(tmp_path):
    other = tmp_path / "seed.json"
    other.write_bytes(mutated(lambda d: d.update(seed=11)))
    a, b = build_activities(load_spec_set(FIXTURE)), build_activities(load_spec_set(other))
    assert [x.geometry for x in a.activities] != [x.geometry for x in b.activities]
    assert [x.prompt_fr for x in a.activities] == [x.prompt_fr for x in b.activities]


def test_cli_validate_run_audit_and_refusals(tmp_path, capsys):
    out = tmp_path / "cli-pkg"
    assert main(["validate", str(FIXTURE)]) == 0
    assert main(["run", str(FIXTURE), "--out", str(out)]) == 0
    printed = capsys.readouterr().out
    assert "ready_for_kdp=false" in printed and "kind=SYNTHETIC_NON_PRODUCTION" in printed
    assert main(["audit", "--out", str(out), "--spec", str(FIXTURE)]) == 0
    assert main(["run", str(FIXTURE), "--out", str(out)]) == 2  # no overwrite
    bad = tmp_path / "bad.json"
    bad.write_bytes(mutated(lambda d: d.update(kind="PRODUCTION")))
    assert main(["validate", str(bad)]) == 2
    assert main(["run", str(bad), "--out", str(tmp_path / "x")]) == 2
    assert not (tmp_path / "x").exists()


def test_isolated_render_equals_the_historical_writer_under_the_canonical_environment(tmp_path, monkeypatch):
    """The child process renders exactly what ``write_pdf`` writes in a canonical environment."""
    from lafractale.engine.render import CANONICAL_PDF_EPOCH, render_slice
    from lafractale.layout.pdf import write_pdf
    spec = load_spec_set(FIXTURE)
    activities = build_activities(spec).activities
    isolated = tmp_path / "isolated"
    isolated.mkdir()
    interior, answer = render_slice(spec, activities, isolated)
    monkeypatch.setenv("SOURCE_DATE_EPOCH", str(CANONICAL_PDF_EPOCH))
    direct = tmp_path / "direct"
    direct.mkdir()
    write_pdf(direct / "i.pdf", list(activities), spec.book_dict(), answer_key=False)
    write_pdf(direct / "a.pdf", list(activities), spec.book_dict(), answer_key=True)
    assert interior.read_bytes() == (direct / "i.pdf").read_bytes()
    assert answer.read_bytes() == (direct / "a.pdf").read_bytes()


def test_render_worker_refuses_a_non_canonical_environment(tmp_path):
    import subprocess
    import sys
    env = {**os.environ, "SOURCE_DATE_EPOCH": "5"}
    done = subprocess.run([sys.executable, "-m", "lafractale.engine._render_worker", str(tmp_path)],
                          input=b"{}", env=env, capture_output=True)
    assert done.returncode == 2 and b"non canonique" in done.stderr and not list(tmp_path.iterdir())


def test_canonical_environment_is_a_sanitized_copy():
    from lafractale.engine.render import canonical_render_environment
    base = {"PATH": "/bin", "SOURCE_DATE_EPOCH": "1", "RL_invariant": "0", "RL_x": "y", "KEEP": "1"}
    snapshot = dict(base)
    env = canonical_render_environment(base)
    assert env == {"PATH": "/bin", "KEEP": "1", "SOURCE_DATE_EPOCH": "946684800"}
    assert base == snapshot  # the input mapping is never mutated


def test_canonical_pdf_date_matches_what_reportlab_writes(built):
    import pymupdf as fitz
    from lafractale.engine.render import CANONICAL_PDF_DATE
    assert CANONICAL_PDF_DATE == "D:20000101000000+00'00'"
    for name in (INTERIOR_NAME, ANSWER_NAME):
        with fitz.open(built["first"] / name) as pdf:
            assert pdf.metadata["creationDate"] == pdf.metadata["modDate"] == CANONICAL_PDF_DATE


def test_activity_json_round_trip_is_lossless():
    from lafractale.engine.render import activity_from_dict
    for activity in build_activities(load_spec_set(FIXTURE)).activities:
        assert activity_from_dict(json.loads(json.dumps(activity.as_dict()))) == activity


def test_canonical_epoch_is_recorded_in_report_and_manifest(built):
    for name in ("quality_report.json", "manifest.json"):
        data = json.loads((built["first"] / name).read_text(encoding="utf-8"))
        assert data["pdf_creation_epoch"] == 946684800
    manifest = json.loads((built["first"] / "manifest.json").read_text(encoding="utf-8"))
    assert "RL_*" in manifest["pdf_render_isolation"]
