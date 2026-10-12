"""MINOR-2: the fonts really used by the render are traced (SHA-256) and checked by the audit."""
import hashlib
import json
import os
from pathlib import Path

import pytest

from b3b1_support import FIXTURE, tree
from lafractale.engine.pipeline import audit_existing_package, generate_package

DEJAVU = Path("/usr/share/fonts/truetype/dejavu")
MONO = DEJAVU / "DejaVuSansMono.ttf"


def _sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _default_fonts():
    return (Path(os.environ.get("LAFRACTALE_FONT_PATH", DEJAVU / "DejaVuSans.ttf")),
            Path(os.environ.get("LAFRACTALE_FONT_BOLD_PATH", DEJAVU / "DejaVuSans-Bold.ttf")))


@pytest.fixture(scope="module")
def package(tmp_path_factory):
    out = tmp_path_factory.mktemp("fonts") / "pkg"
    generate_package(FIXTURE, out)
    return out


def test_manifest_and_report_trace_the_fonts_actually_used(package):
    regular, bold = _default_fonts()
    for name in ("manifest.json", "quality_report.json"):
        fonts = json.loads((package / name).read_text(encoding="utf-8"))["fonts"]
        assert set(fonts) == {"regular", "bold"}
        assert fonts["regular"] == {"file": regular.name, "sha256": _sha(regular)}
        assert fonts["bold"] == {"file": bold.name, "sha256": _sha(bold)}


def test_no_absolute_font_path_leaks_into_the_outputs(package):
    for name in ("manifest.json", "quality_report.json"):
        text = (package / name).read_text(encoding="utf-8")
        assert "/usr" not in text and "/home" not in text and "/tmp" not in text


@pytest.mark.skipif(not MONO.is_file(), reason="DejaVuSansMono absente")
def test_another_font_changes_the_pdf_and_the_change_is_explicit_and_traceable(package, tmp_path, monkeypatch):
    monkeypatch.setenv("LAFRACTALE_FONT_PATH", str(MONO))
    out = tmp_path / "mono"
    generate_package(FIXTURE, out)
    traced = json.loads((out / "manifest.json").read_text(encoding="utf-8"))["fonts"]
    assert traced["regular"] == {"file": MONO.name, "sha256": _sha(MONO)}
    assert tree(out)["interior_SYNTHETIC_NON_PRODUCTION.pdf"] != tree(package)["interior_SYNTHETIC_NON_PRODUCTION.pdf"]
    assert audit_existing_package(out, FIXTURE) == []          # same font: consistent
    monkeypatch.delenv("LAFRACTALE_FONT_PATH")
    errors = audit_existing_package(out, FIXTURE)               # other font: explicit refusal
    assert any("polices" in e and MONO.name in e and _sha(MONO)[:12] in e for e in errors), errors


def test_tampered_font_hash_in_the_manifest_is_detected(package, tmp_path):
    import shutil
    from lafractale.engine.contracts import canonical_json_bytes
    copy = tmp_path / "pkg"
    shutil.copytree(package, copy)
    path = copy / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["fonts"]["bold"]["sha256"] = "0" * 64
    path.write_bytes(canonical_json_bytes(manifest))
    assert any("polices" in e for e in audit_existing_package(copy, FIXTURE))


def test_malformed_font_record_is_refused(package, tmp_path):
    import shutil
    from lafractale.engine.contracts import canonical_json_bytes
    for bad in ({"regular": {"file": "a.ttf"}}, {"regular": {"file": "../a.ttf", "sha256": "0" * 64},
                                                   "bold": {"file": "b.ttf", "sha256": "0" * 64}},
                "texte", None):
        copy = tmp_path / f"pkg{abs(hash(str(bad)))}"
        shutil.copytree(package, copy)
        path = copy / "manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["fonts"] = bad
        path.write_bytes(canonical_json_bytes(manifest))
        errors = audit_existing_package(copy, FIXTURE)
        assert any("polices" in e for e in errors), (bad, errors)


def test_render_with_fonts_returns_basenames_and_hashes(tmp_path):
    from lafractale.engine.contracts import load_spec_set
    from lafractale.engine.pipeline import build_activities
    from lafractale.engine.render import render_slice_with_fonts
    spec = load_spec_set(FIXTURE)
    interior, answer, fonts = render_slice_with_fonts(spec, build_activities(spec).activities, tmp_path)
    assert interior.is_file() and answer.is_file()
    regular, bold = _default_fonts()
    assert fonts == {"regular": {"file": regular.name, "sha256": _sha(regular)},
                     "bold": {"file": bold.name, "sha256": _sha(bold)}}


REGULAR = DEJAVU / "DejaVuSans.ttf"
BOLD = DEJAVU / "DejaVuSans-Bold.ttf"


def _tree_hashes(path):
    return {name: hashlib.sha256(data).hexdigest() for name, data in tree(path).items()}


@pytest.mark.skipif(not REGULAR.is_file(), reason="DejaVuSans absente")
def test_symbolic_link_fonts_are_followed_like_reportlab_does(package, tmp_path, monkeypatch):
    link = tmp_path / "LinkedSans.ttf"
    link.symlink_to(REGULAR)
    monkeypatch.setenv("LAFRACTALE_FONT_PATH", str(link))
    out = tmp_path / "linked"
    generate_package(FIXTURE, out)
    traced = json.loads((out / "manifest.json").read_text(encoding="utf-8"))["fonts"]["regular"]
    assert traced == {"file": "LinkedSans.ttf", "sha256": _sha(REGULAR)}
    assert _tree_hashes(out)["interior_SYNTHETIC_NON_PRODUCTION.pdf"] == _tree_hashes(package)["interior_SYNTHETIC_NON_PRODUCTION.pdf"]


@pytest.mark.skipif(not REGULAR.is_file(), reason="DejaVuSans absente")
@pytest.mark.parametrize("filename", ["DejaVu Sans copie.ttf", "Dejàvu.ttf"])
def test_font_names_with_spaces_or_accents_are_traced(tmp_path, monkeypatch, filename):
    copy = tmp_path / filename
    copy.write_bytes(REGULAR.read_bytes())
    monkeypatch.setenv("LAFRACTALE_FONT_PATH", str(copy))
    out = tmp_path / "pkg"
    generate_package(FIXTURE, out)
    assert json.loads((out / "manifest.json").read_text(encoding="utf-8"))["fonts"]["regular"]["file"] == filename
    assert audit_existing_package(out, FIXTURE) == []


@pytest.mark.skipif(not REGULAR.is_file(), reason="DejaVuSans absente")
def test_a_renamed_copy_of_the_same_font_is_the_same_font(tmp_path, monkeypatch):
    """Only the BYTES of the font count for the audit; the file name is informational."""
    copy = tmp_path / "Renamed.ttf"
    copy.write_bytes(REGULAR.read_bytes())
    monkeypatch.setenv("LAFRACTALE_FONT_PATH", str(copy))
    out = tmp_path / "pkg"
    generate_package(FIXTURE, out)
    monkeypatch.delenv("LAFRACTALE_FONT_PATH")
    assert audit_existing_package(out, FIXTURE) == []
