from pathlib import Path
import json
import fitz
from lafractale.export.builder import build_demo,audit_output,sha256
from lafractale.__main__ import main
from lafractale.config.schema import load_book

ROOT=Path(__file__).resolve().parents[1]


def test_generate_and_check_pdf(tmp_path,halloween):
    out=tmp_path/"demo"
    report=build_demo(halloween,out,seed=7)
    assert report["ready_for_kdp"] is False
    assert [a["graphic"] for a in report["page_results"]]==["needs_visual_review"]*3
    assert audit_output(out, book=halloween)==[]
    with fitz.open(out/"interior.pdf") as document:
        assert len(document)==3
        texts=[p.get_text() for p in document]
        assert "labyrinthe" in texts[0]
        assert "Relie les points" in texts[1]
        assert "chapeau" in texts[2]
    with fitz.open(out/"answer_key.pdf") as document:
        assert len(document)==3
        assert all("CORRIGÉ" in p.get_text() for p in document)
    assert len(list((out/"previews").glob("*.png")))==3
    assert (out/"activities.json").exists()


def test_manifest_and_pdfs_reproducible(tmp_path, halloween,monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH","1780000000")
    build_demo(halloween,tmp_path/"a",seed=9)
    build_demo(halloween,tmp_path/"b",seed=9)
    for file in ("interior.pdf","answer_key.pdf","activities.json","manifest.json"):
        assert sha256(tmp_path/"a"/file)==sha256(tmp_path/"b"/file)
    build_demo(halloween,tmp_path/"c",seed=10)
    assert sha256(tmp_path/"a"/"activities.json") != sha256(tmp_path/"c"/"activities.json")


def test_qa_detects_tamper(tmp_path,halloween):
    out=tmp_path/"demo";build_demo(halloween,out)
    data=out/"activities.json"
    data.write_text(data.read_text(encoding="utf-8")+"tamper",encoding="utf-8")
    assert any("activities.json" in e for e in audit_output(out, book=halloween))


def test_qa_rejects_manifest_path_traversal(tmp_path, halloween):
    out = tmp_path / "demo"
    build_demo(halloween, out)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    manifest_path = out / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["outputs"] = {"../outside.txt": sha256(outside)}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    assert any("non autorisé" in error for error in audit_output(out, book=halloween))


def test_qa_rejects_malformed_manifest_outputs(tmp_path, halloween):
    out = tmp_path / "demo"
    build_demo(halloween, out)
    manifest_path = out / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["outputs"] = []
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    assert any("outputs invalide" in error for error in audit_output(out, book=halloween))


def test_qa_rejects_malformed_quality_report(tmp_path, halloween):
    out = tmp_path / "demo"
    build_demo(halloween, out)
    (out / "quality_report.json").write_text("[]", encoding="utf-8")
    assert any("Rapport qualité invalide" in error for error in audit_output(out, book=halloween))


def test_qa_rejects_manifest_symlink(tmp_path, halloween):
    out = tmp_path / "demo"
    build_demo(halloween, out)
    manifest_path = out / "manifest.json"
    external_manifest = tmp_path / "external-manifest.json"
    manifest_path.replace(external_manifest)
    manifest_path.symlink_to(external_manifest)
    assert any("Manifest/rapport non autorisé" in error for error in audit_output(out, book=halloween))


def test_qa_rejects_non_object_auto_checks_and_publication_claim(tmp_path, halloween):
    out = tmp_path / "demo"
    build_demo(halloween, out)
    report_path = out / "quality_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["auto_checks"] = []
    report_path.write_text(json.dumps(report), encoding="utf-8")
    assert any("auto_checks invalide" in error for error in audit_output(out, book=halloween))
    build_demo(halloween, out)
    manifest_path = out / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["publication_approved"] = True
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    assert any("publication_approved" in error for error in audit_output(out, book=halloween))


def test_build_full_rejected_no_fake_56_pages(tmp_path):
    book=ROOT/"books/halloween_2026/book.yaml"
    assert main(["build",str(book),"--out",str(tmp_path/"full")])==2
    assert not (tmp_path/"full"/"interior.pdf").exists()


def test_christmas_demo_build_and_audit(tmp_path):
    book=load_book(ROOT/"books/christmas_2026/book.yaml")
    out=tmp_path/"christmas"
    build_demo(book,out)
    assert audit_output(out, book=book)==[]
    manifest=json.loads((out/"manifest.json").read_text(encoding="utf-8"))
    assert manifest["target_pages"]==80
    assert manifest["demo_pages"]==3
