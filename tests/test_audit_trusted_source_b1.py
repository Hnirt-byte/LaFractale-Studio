"""Independent trust-boundary tests: emitted artifacts cannot define QA policy.

Threat model: an attacker can rewrite every emitted JSON/PDF and recompute
unkeyed hashes, but cannot alter the independently approved project source.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from lafractale.__main__ import main
from lafractale.config.schema import load_book
from lafractale.export.builder import audit_output, build_demo
from lafractale.security.text import blocked_name_fingerprints

ROOT = Path(__file__).resolve().parents[1]
HALLOWEEN = ROOT / "books/halloween_2026/book.yaml"
CHRISTMAS = ROOT / "books/christmas_2026/book.yaml"


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path, data):
    path.write_text(json.dumps(data, sort_keys=True, ensure_ascii=False), encoding="utf-8")


def _demo(tmp_path, source=CHRISTMAS):
    book = load_book(source)
    out = tmp_path / "demo"
    build_demo(book, out)
    assert audit_output(out, book=book) == []
    return book, out


def _forge_json(out, *, string="Pip apparaît dans la neige", name="activities.json"):
    path = out / name
    payload = _json(path)
    if name == "activities.json":
        payload[0]["scene"] = string
    else:
        payload["blocking_for_publication"][0] = string
    _save(path, payload)
    manifest = _json(out / "manifest.json")
    manifest["outputs"][name] = hashlib.sha256(path.read_bytes()).hexdigest()
    _save(out / "manifest.json", manifest)


def test_fails_closed_without_independent_source(tmp_path):
    book, out = _demo(tmp_path)
    assert "source de confiance obligatoire" in " ".join(audit_output(out))
    assert audit_output(out, book=book) == []


def test_exact_hermes_manifest_policy_bypass_rejected(tmp_path):
    book, out = _demo(tmp_path)
    _forge_json(out)
    manifest = _json(out / "manifest.json")
    manifest["security"]["blocked_name_fingerprints"] = []
    _save(out / "manifest.json", manifest)
    assert 'Pip' in (out / 'activities.json').read_text(encoding='utf-8')
    errors = audit_output(out, book=book)
    assert errors and any('empreintes' in e for e in errors)


@pytest.mark.parametrize("replacement", [
    [[1, '0'*64]],
    [[1, 'a'*64]],
    [],
    [[2, 'f'*64]],
    [[1, 'a'*64], [1, 'b'*64]],
])
def test_forged_valid_shape_policy_rejected(tmp_path, replacement):
    book, out = _demo(tmp_path)
    _forge_json(out)
    manifest = _json(out / "manifest.json")
    manifest["security"]["blocked_name_fingerprints"] = replacement
    _save(out / "manifest.json", manifest)
    assert audit_output(out, book=book) != []


def test_fingerprint_from_other_book_rejected(tmp_path):
    book, out = _demo(tmp_path)
    manifest = _json(out / "manifest.json")
    halloween = load_book(HALLOWEEN)
    other = tuple(n for n in halloween.companion.reserved_names
                  if n.casefold() != halloween.companion.render_name.casefold())
    manifest["security"]["blocked_name_fingerprints"] = [list(p) for p in blocked_name_fingerprints(other)]
    _save(out / "manifest.json", manifest)
    assert audit_output(out, book=book) != []


@pytest.mark.parametrize("mutation", [
    ("book_id", "halloween_2026"),
    ("target_pages", 56),
    ("companion", {"id": "pip", "name": "Pip", "status": "approved_reference"}),
    ("source", {"book_config": "books/halloween_2026/book.yaml", "book_config_sha256": "0"*64,
                "page_plan_sha256": None}),
])
def test_manifest_identity_and_provenance_cannot_be_forged(tmp_path, mutation):
    book, out = _demo(tmp_path)
    key, value = mutation
    manifest = _json(out / "manifest.json")
    manifest[key] = value
    _save(out / "manifest.json", manifest)
    errors = audit_output(out, book=book)
    assert errors and any("identité ou provenance" in e for e in errors)


def test_quality_report_companion_and_book_identity_checked(tmp_path):
    book, out = _demo(tmp_path)
    report = _json(out / 'quality_report.json')
    report['companion']['name'] = 'Pip'
    _save(out / 'quality_report.json', report)
    manifest = _json(out / 'manifest.json')
    manifest['outputs']['quality_report.json'] = hashlib.sha256((out/'quality_report.json').read_bytes()).hexdigest()
    _save(out / 'manifest.json', manifest)
    assert audit_output(out, book=book) != []


def test_qa_cross_book_substitution_rejected(tmp_path):
    book, out = _demo(tmp_path)
    other = load_book(HALLOWEEN)
    assert audit_output(out, book=other) != []
    assert audit_output(out, book=book) == []


def test_cli_requires_explicit_book_and_rejects_wrong_one(tmp_path):
    book, out = _demo(tmp_path)
    with pytest.raises(SystemExit) as e:
        main(['qa', str(out)])
    assert e.value.code == 2
    assert main(['qa', str(out), '--book', str(HALLOWEEN)]) == 2
    assert main(['qa', str(out), '--book', str(CHRISTMAS)]) == 0


def test_rewritten_checksum_cannot_hide_unauthorized_name_in_quality_json(tmp_path):
    book, out = _demo(tmp_path)
    _forge_json(out, name='quality_report.json')
    assert any('Compagnon non autorisé' in e for e in audit_output(out, book=book))


def test_approved_halloween_can_display_pip(tmp_path):
    book, out = _demo(tmp_path, HALLOWEEN)
    manifest = _json(out / 'manifest.json')
    assert manifest['security']['blocked_name_fingerprints'] == []
    assert audit_output(out, book=book) == []


def test_source_changes_after_load_fail_closed_even_for_existing_valid_output(tmp_path):
    # A separately copied, trusted source becomes invalid if changed.
    from shutil import copy2
    root = tmp_path / 'project'
    (root / 'books/christmas_2026').mkdir(parents=True)
    (root / 'assets/companions').mkdir(parents=True)
    (root / 'pyproject.toml').write_text('[project]\n', encoding='utf-8')
    config = root / 'books/christmas_2026/book.yaml'
    copy2(CHRISTMAS, config)
    copy2(ROOT / 'assets/companions/catalog.yaml', root / 'assets/companions/catalog.yaml')
    book, out = _demo(tmp_path, config)
    data_before = config.read_bytes()
    config.write_bytes(data_before + b'\n# source modified\n')
    assert any('source de confiance invalide' in e for e in audit_output(out, book=book))
    config.write_bytes(data_before)
    assert audit_output(out, book=book) == []
