"""Source-backed replay regressions for tampered, mutually consistent outputs.

All edits are ordinary on-disk output mutations, not malicious Python hooks.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import fitz
import pytest
from PIL import Image

from lafractale.config.schema import load_book
from lafractale.export.builder import audit_output, build_demo
from test_illustrations_b2a import ORIGIN, _make_fixture


def _fixture(tmp_path, illustrated: bool):
    if illustrated:
        _, book, _, entry, _, pin, _ = _make_fixture(tmp_path)
        kwargs = {'illustration_id': entry['id'], 'trusted_approvals_sha256': pin}
    else:
        book = load_book(ORIGIN / 'books/christmas_2026/book.yaml')
        kwargs = {}
    dest = tmp_path / 'out'
    build_demo(book, dest, **kwargs)
    assert audit_output(dest, book=book, **kwargs) == []
    return book, kwargs, dest


def _update_checksum(out: Path, name: str):
    manifest_path = out / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['outputs'][name] = hashlib.sha256((out / name).read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')


@pytest.mark.parametrize('illustrated', [False, True], ids=['placeholder', 'illustrated'])
@pytest.mark.parametrize('artifact', ['activities.json', 'quality_report.json', 'quality_report.md'])
def test_rewritten_json_and_markdown_rejected_with_recomputed_checksums(tmp_path, illustrated, artifact):
    book, kwargs, out = _fixture(tmp_path, illustrated)
    path = out / artifact
    if artifact == 'activities.json':
        data = json.loads(path.read_text(encoding='utf-8'))
        data[0]['scene'] = 'ALTERATION NON REGENEREE'
        path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        _update_checksum(out, artifact)
    elif artifact == 'quality_report.json':
        data = json.loads(path.read_text(encoding='utf-8'))
        data['blocking_for_publication'] = []
        for page in data['page_results']:
            page['graphic'] = 'approved'
            page['human_approval'] = 'approved'
        path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        _update_checksum(out, artifact)
    else:
        path.write_text(path.read_text(encoding='utf-8').replace('EN ATTENTE', 'APPROUVÉ'), encoding='utf-8')
    errors = audit_output(out, book=book, **kwargs)
    assert any(artifact in e for e in errors), errors


@pytest.mark.parametrize('illustrated', [False, True], ids=['placeholder', 'illustrated'])
@pytest.mark.parametrize('pdf_name', ['interior.pdf', 'answer_key.pdf'])
def test_vector_pdf_overlays_rejected_with_recomputed_checksums(tmp_path, illustrated, pdf_name):
    book, kwargs, out = _fixture(tmp_path, illustrated)
    path = out / pdf_name
    with fitz.open(path) as pdf:
        pdf[0].draw_rect(fitz.Rect(120, 250, 150, 280), color=(0, 0, 0), fill=(0, 0, 0))
        altered = pdf.tobytes(garbage=3, deflate=True)
    path.write_bytes(altered)
    if pdf_name == 'interior.pdf':
        # Make thumbnails mutually consistent with the forged PDF.
        with fitz.open(path) as pdf:
            for i, page in enumerate(pdf, 1):
                page.get_pixmap(matrix=fitz.Matrix(1.4, 1.4), alpha=False).save(
                    str(out / 'previews' / f'page_{i:02d}.png'))
    _update_checksum(out, pdf_name)
    errors = audit_output(out, book=book, **kwargs)
    assert any('PDF différent de la régénération approuvée' in e for e in errors), errors


@pytest.mark.parametrize('illustrated', [False, True], ids=['placeholder', 'illustrated'])
def test_placeholder_or_illustrated_preview_rewritten_rejected(tmp_path, illustrated):
    book, kwargs, out = _fixture(tmp_path, illustrated)
    path = out / 'previews/page_01.png'
    with Image.open(path) as im:
        img = im.copy()
    img.putpixel((0, 0), (0, 0, 0))
    img.save(path)
    errors = audit_output(out, book=book, **kwargs)
    assert any('Aperçu' in e for e in errors), errors


@pytest.mark.parametrize('key,value', [
    ('ready_for_kdp', True),
    ('extra_claim', {'approved': True}),
    ('engine_version', '999.0'),
])
def test_manifests_cannot_add_fields_or_claims(tmp_path, key, value):
    book, kwargs, out = _fixture(tmp_path, False)
    path = out / 'manifest.json'
    manifest = json.loads(path.read_text(encoding='utf-8'))
    manifest[key] = value
    path.write_text(json.dumps(manifest), encoding='utf-8')
    assert audit_output(out, book=book, **kwargs), key


@pytest.mark.parametrize('timestamp', ['yesterday', '2026-10-09', '2026-10-09T09:00:00+02:00'])
def test_manifest_timestamp_requires_canonical_utc(tmp_path, timestamp):
    book, kwargs, out = _fixture(tmp_path, False)
    path = out / 'manifest.json'
    manifest = json.loads(path.read_text(encoding='utf-8'))
    manifest['generated_at_utc'] = timestamp
    path.write_text(json.dumps(manifest), encoding='utf-8')
    assert audit_output(out, book=book, **kwargs)


def test_replay_rejects_forged_seed_when_artifacts_do_not_match(tmp_path):
    book, kwargs, out = _fixture(tmp_path, False)
    path = out / 'manifest.json'
    manifest = json.loads(path.read_text(encoding='utf-8'))
    manifest['seed'] += 1
    path.write_text(json.dumps(manifest), encoding='utf-8')
    assert audit_output(out, book=book, **kwargs)
