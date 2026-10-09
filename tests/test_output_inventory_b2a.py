"""Audit output directory is a closed-world artifact package, not a bag of audited files."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from lafractale.config.schema import load_book
from lafractale.export.builder import audit_output, build_demo
from test_illustrations_b2a import ORIGIN, _make_fixture


@pytest.fixture(scope="module")
def original_placeholder(tmp_path_factory):
    base = tmp_path_factory.mktemp("b2a-inventory-placeholder")
    book = load_book(ORIGIN / "books/christmas_2026/book.yaml")
    original = base / "canonical"
    build_demo(book, original)
    assert audit_output(original, book=book) == []
    return book, original


@pytest.fixture(scope="module")
def original_illustrated(tmp_path_factory):
    base = tmp_path_factory.mktemp("b2a-inventory-illustrated")
    _, book, _, entry, _, pin, _ = _make_fixture(base)
    opts = {"illustration_id": entry["id"], "trusted_approvals_sha256": pin}
    original = base / "canonical"
    build_demo(book, original, **opts)
    assert audit_output(original, book=book, **opts) == []
    return book, original, opts


@pytest.mark.parametrize("name, is_dir", [
    ("ready_for_kdp.txt", False),
    ("APPROVED.pdf", False),
    (".hidden", False),
    (".DS_Store", False),
    ("unexpected", True),
    (".nested", True),
    ("previews_extra", True),
])
def test_root_extras_rejected_placeholder(tmp_path, original_placeholder, name, is_dir):
    book, original = original_placeholder
    out = tmp_path / "demo"
    shutil.copytree(original, out)
    target = out / name
    if is_dir:
        target.mkdir()
    else:
        target.write_text("UNDECLARED MALICIOUS PAYLOAD\n")
    errors = audit_output(out, book=book)
    assert any("inventaire" in e.lower() and name in e for e in errors), errors
    assert not (original / name).exists()


@pytest.mark.parametrize("name,is_dir", [
    ("ready_for_kdp.txt", False),
    ("page_99.png", False),
    (".hidden", False),
    ("extra_dir", True),
])
def test_preview_extras_rejected(tmp_path, original_placeholder, name, is_dir):
    book, original = original_placeholder
    out = tmp_path / "demo"
    shutil.copytree(original, out)
    extra = out / "previews" / name
    if is_dir:
        extra.mkdir()
    else:
        extra.write_bytes(b"not a canonical preview")
    errors = audit_output(out, book=book)
    assert any("inventaire" in e.lower() and name in e for e in errors), errors


def test_extras_rejected_with_illustrated_demo(tmp_path, original_illustrated):
    book, original, opts = original_illustrated
    out = tmp_path / "demo"
    shutil.copytree(original, out)
    (out / "ready_for_kdp.txt").write_text("TRUE")
    (out / "previews" / "EXTRA.png").write_bytes(b"PNG")
    errors = audit_output(out, book=book, **opts)
    assert "ready_for_kdp.txt" in str(errors)
    assert "EXTRA.png" in str(errors)


@pytest.mark.parametrize("scope,name", [("root", "report.txt"), ("previews", "page_99.png")])
def test_symlink_extra_rejected_without_following(tmp_path, original_placeholder, scope, name):
    book, original = original_placeholder
    out = tmp_path / "demo"
    shutil.copytree(original, out)
    outside = tmp_path / "external.txt"
    outside.write_text("EXTERNAL CONTENT")
    link = (out if scope == "root" else out / "previews") / name
    link.symlink_to(outside)
    errors = audit_output(out, book=book)
    assert any("inventaire" in e.lower() and name in e for e in errors), errors
    assert outside.read_text() == "EXTERNAL CONTENT"


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="Linux-only audit")
def test_fifo_extra_rejected_without_reading(tmp_path, original_placeholder):
    book, original = original_placeholder
    out = tmp_path / "demo"
    shutil.copytree(original, out)
    os.mkfifo(out / "unexpected_pipe")
    errors = audit_output(out, book=book)
    assert any("inventaire" in e.lower() and "unexpected_pipe" in e for e in errors), errors


@pytest.mark.parametrize("scope,name", [("root", "quality_report.md"), ("previews", "page_01.png")])
def test_expected_entry_with_wrong_type_rejected(tmp_path, original_placeholder, scope, name):
    book, original = original_placeholder
    out = tmp_path / "demo"
    shutil.copytree(original, out)
    path = (out if scope == "root" else out / "previews") / name
    path.unlink()
    path.mkdir()
    errors = audit_output(out, book=book)
    assert any("inventaire" in e.lower() and name in e for e in errors), errors


def test_missing_expected_root_file_rejected(tmp_path, original_placeholder):
    book, original = original_placeholder
    out = tmp_path / "demo"
    shutil.copytree(original, out)
    (out / "quality_report.md").unlink()
    errors = audit_output(out, book=book)
    assert any("inventaire" in e.lower() and "quality_report.md" in e for e in errors), errors


def test_cli_qa_rejects_undeclared_file(tmp_path, original_placeholder):
    book, original = original_placeholder
    out = tmp_path / "demo"
    shutil.copytree(original, out)
    (out / "ready_for_kdp.txt").write_text("fake publication approval")
    proc = subprocess.run([sys.executable, "-m", "lafractale", "qa", str(out), "--book", str(book.path)],
                          capture_output=True, text=True, timeout=30)
    assert proc.returncode != 0, proc.stdout
    assert "ready_for_kdp.txt" in proc.stdout + proc.stderr


def test_extra_stage_file_blocks_publication_preserves_previous_demo(tmp_path, original_placeholder, monkeypatch):
    """Even a trusted generator extension cannot sneak an undeclared file into the published package."""
    from lafractale.export import builder

    book, original = original_placeholder
    out = tmp_path / "demo"
    shutil.copytree(original, out)
    old_hashes = {p.relative_to(out): p.read_bytes() for p in out.rglob('*') if p.is_file()}
    real_unpublished = builder._build_demo_unpublished

    def smuggle(book_arg, stage, **kwargs):
        result = real_unpublished(book_arg, stage, **kwargs)
        (stage / "ready_for_kdp.txt").write_text("forged QA approval")
        return result

    monkeypatch.setattr(builder, '_build_demo_unpublished', smuggle)
    with pytest.raises(Exception, match='Inventaire|non autorisée'):
        build_demo(book, out)
    assert {p.relative_to(out): p.read_bytes() for p in out.rglob('*') if p.is_file()} == old_hashes
    assert audit_output(out, book=book) == []


def test_no_unexpected_files_in_valid_build(tmp_path, original_placeholder, original_illustrated):
    for entry in (original_placeholder, original_illustrated):
        original = entry[1]
        assert {p.name for p in original.iterdir()} == {
            "interior.pdf", "answer_key.pdf", "activities.json", "quality_report.json",
            "quality_report.md", "manifest.json", "previews"
        }
        assert {p.name for p in (original / 'previews').iterdir()} == {
            'page_01.png', 'page_02.png', 'page_03.png'
        }
