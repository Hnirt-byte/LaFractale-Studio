"""B2-A predeclared threat matrix: approvals, PNG, paths, aliases, output and QA."""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from shutil import copy2, copytree
import struct
import zlib

import fitz
import pytest
from PIL import Image

from lafractale.config.schema import load_book
from lafractale.export.builder import build_demo, audit_output
from lafractale.illustrations.registry import (IllustrationError, VerifiedArtwork,
    _strict_png, load_approved_artwork, verify_approved_artwork, REGISTRY_PATH)
from lafractale.layout.pdf import write_pdf
from lafractale.activities.engine import generate, stable_seed
from lafractale.story.plan import demo_specs

ORIGIN = Path(__file__).resolve().parents[1]


def _make_gray(size=(660, 220), shade=210):
    img = Image.new("L", size, shade)
    out = BytesIO()
    img.save(out, "PNG", optimize=False)
    return out.getvalue()


def _make_fixture(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "pyproject.toml").write_text('[project]\nname="test"\n')
    copytree(ORIGIN / 'books', root / 'books')
    copytree(ORIGIN / 'assets' / 'companions', root / 'assets' / 'companions')
    copytree(ORIGIN / 'assets' / 'characters', root / 'assets' / 'characters')
    for book_id in ('halloween_2026', 'christmas_2026'):
        (root / 'assets' / 'illustrations' / book_id / 'pip').mkdir(parents=True)
    asset = root / 'assets/illustrations/halloween_2026/pip/test-graphic.png'
    png = _make_gray()
    asset.write_bytes(png)
    approvals = root / REGISTRY_PATH
    approval = {'id': 'test-graphic', 'book_id': 'halloween_2026', 'companion_id': 'pip',
                'role': 'companion', 'variant': 'monochrome',
                'path': 'assets/illustrations/halloween_2026/pip/test-graphic.png',
                'sha256': sha256(png).hexdigest(), 'width': 660, 'height': 220,
                'human_approved': True}
    def persist(records=None):
        doc = {'schema_version': 1, 'illustrations': [approval] if records is None else records}
        approvals.write_text(json.dumps(doc, sort_keys=True), encoding='utf-8')
        return sha256(approvals.read_bytes()).hexdigest()
    pin = persist()
    book = load_book(root / 'books/halloween_2026/book.yaml')
    return root, book, approvals, approval, asset, pin, persist


@pytest.fixture
def sample(tmp_path):
    return _make_fixture(tmp_path)


def test_empty_registry_is_non_approving(tmp_path):
    # A temporary isolated empty registry must never authorize artwork.
    # B2-B production registry contains six approved Pip drawings by design.
    _, book, approvals, entry, _, _, _ = _make_fixture(tmp_path)
    approvals.write_text(
        json.dumps({'schema_version': 1, 'illustrations': []}) + '\n',
        encoding='utf-8',
    )
    empty_pin = sha256(approvals.read_bytes()).hexdigest()
    with pytest.raises(IllustrationError, match='absent du registre'):
        load_approved_artwork(book, entry['id'], trusted_approvals_sha256=empty_pin)


def test_valid_opt_in_monochrome_pdf_and_external_audit(sample, tmp_path):
    _, book, approvals, entry, asset, pin, _ = sample
    artwork = load_approved_artwork(book, entry['id'], trusted_approvals_sha256=pin)
    assert artwork.pixels == asset.read_bytes()
    assert artwork.sha256 == entry['sha256']
    out = tmp_path / 'with-artwork'
    build_demo(book, out, illustration_id=entry['id'], trusted_approvals_sha256=pin)
    assert audit_output(out, book=book, illustration_id=entry['id'], trusted_approvals_sha256=pin) == []
    assert audit_output(out, book=book)
    assert audit_output(out, book=book, illustration_id=entry['id'], trusted_approvals_sha256='0' * 64)
    manifest = json.loads((out / 'manifest.json').read_text())
    assert manifest['publication_approved'] is False
    assert manifest['illustration'] == artwork.manifest_entry()
    for name in ('interior.pdf', 'answer_key.pdf'):
        with fitz.open(out / name) as pdf:
            assert len(pdf) == 3
            assert all(len(page.get_image_info()) == 1 for page in pdf)
            assert all('MAQUETTE' in page.get_text() for page in pdf)


def test_default_placeholder_always_used_even_when_registry_has_approval(sample, tmp_path):
    _, book, *_ = sample
    out = tmp_path / 'default'
    build_demo(book, out)
    assert audit_output(out, book=book) == []
    assert 'illustration' not in json.loads((out / 'manifest.json').read_text())
    with fitz.open(out / 'interior.pdf') as pdf:
        assert all('VISUEL À VALIDER' in page.get_text() for page in pdf)
        assert all(len(page.get_image_info()) == 0 for page in pdf)


def test_noel_must_never_accept_pip_artwork(sample):
    root, _, _, entry, _, pin, _ = sample
    christmas = load_book(root / 'books/christmas_2026/book.yaml')
    with pytest.raises(IllustrationError, match='Aucun compagnon'):
        load_approved_artwork(christmas, entry['id'], trusted_approvals_sha256=pin)


def test_approvals_forgery_does_not_override_external_digest(sample):
    _, book, approvals, entry, _, pin, persist = sample
    entry['sha256'] = 'a'*64
    persist()
    with pytest.raises(IllustrationError, match='empreinte externe incorrecte|modifié'):
        load_approved_artwork(book, entry['id'], trusted_approvals_sha256=pin)


@pytest.mark.parametrize('field,edited', [
    ('human_approved', False), ('human_approved', 'true'), ('role', 'decor'),
    ('variant', 'reference_color'), ('book_id', 'christmas_2026'),
    ('companion_id', 'faux'), ('width', 10), ('height', 11),
    ('path', 'assets/characters/pip/pip_officiel_couleur.png'),
    ('path', 'assets/illustrations/halloween_2026/pip/../../../../../pyproject.toml'),
    ('path', '/tmp/evil.png'), ('sha256', 'f'*64),
])
def test_unapproved_or_forged_registry_entry_refused(sample, field, edited):
    _, book, _, entry, _, _, persist = sample
    entry[field] = edited
    pin = persist()
    with pytest.raises(IllustrationError):
        load_approved_artwork(book, entry['id'], trusted_approvals_sha256=pin)


@pytest.mark.parametrize('item', [
    {'bad': True},
    {'id':'not-present'},
])
def test_malformed_registry_items_fail_closed(sample, item):
    _, book, _, entry, _, _, persist = sample
    pin = persist([entry, item])
    with pytest.raises(IllustrationError):
        load_approved_artwork(book, entry['id'], trusted_approvals_sha256=pin)


def test_duplicate_entries_rejected(sample):
    _, book, _, entry, _, _, persist = sample
    pin = persist([entry, entry])
    with pytest.raises(IllustrationError, match='dupliqués'):
        load_approved_artwork(book, entry['id'], trusted_approvals_sha256=pin)


@pytest.mark.parametrize('which', ['leaf', 'parent', 'registry_leaf', 'registry_parent'])
def test_symlinks_are_rejected_at_all_levels(sample, tmp_path, which):
    root, book, approvals, entry, asset, pin, _ = sample
    if which == 'leaf':
        outside = tmp_path / 'outside.png'
        outside.write_bytes(asset.read_bytes())
        asset.unlink()
        asset.symlink_to(outside)
    elif which == 'parent':
        parent = asset.parent
        outside = tmp_path / 'outside-parent'
        parent.rename(outside)
        parent.symlink_to(outside, target_is_directory=True)
    elif which == 'registry_leaf':
        outside = tmp_path / 'outside.json'
        outside.write_bytes(approvals.read_bytes())
        approvals.unlink()
        approvals.symlink_to(outside)
    else:
        parent = approvals.parent
        outside = tmp_path / 'outside-registry'
        parent.rename(outside)
        parent.symlink_to(outside, target_is_directory=True)
    with pytest.raises(IllustrationError):
        load_approved_artwork(book, entry['id'], trusted_approvals_sha256=pin)


@pytest.mark.parametrize('payload', [
    b'not a PNG', b'\x89PNG\r\n\x1a\n', _make_gray()[:-1],
    _make_gray() + b'trailing bytes',
    _make_gray()[:-8] + b'invalid!',
    ])
def test_invalid_png_bytes_rejected(payload):
    with pytest.raises(IllustrationError):
        _strict_png(payload)


def test_rgb_and_rgba_pngs_rejected():
    for mode in ('RGB', 'RGBA'):
        im = Image.new(mode, (680, 220), (80, 80, 80) if mode == 'RGB' else (80,80,80,255))
        out = BytesIO(); im.save(out, format='PNG')
        with pytest.raises(IllustrationError, match='gris'):
            _strict_png(out.getvalue())


def test_large_png_header_rejected():
    data = bytearray(_make_gray())
    data[16:24] = struct.pack('>II', 4097, 2000)
    data[29:33] = struct.pack('>I', zlib.crc32(data[12:29]) & 0xffffffff)
    with pytest.raises(IllustrationError, match='Dimensions'):
        _strict_png(bytes(data))


def test_malformed_crc_rejected():
    data = bytearray(_make_gray())
    data[32] ^= 1
    with pytest.raises(IllustrationError, match='CRC'):
        _strict_png(bytes(data))


def test_asset_mutation_after_load_is_refused(sample):
    _, book, _, entry, asset, pin, _ = sample
    prepared = load_approved_artwork(book, entry['id'], trusted_approvals_sha256=pin)
    asset.write_bytes(_make_gray(shade=180))
    with pytest.raises(IllustrationError):
        verify_approved_artwork(book, prepared, trusted_approvals_sha256=pin)


@pytest.mark.parametrize('field,value', [('book_id','christmas_2026'), ('companion_id','other'),
                                          ('sha256','f'*64), ('pixels',b'abcd'), ('width',12),
                                          ('approval_sha256','0'*64)])
def test_dataclass_replace_forgery_refused(sample, field, value):
    _, book, _, entry, _, pin, _ = sample
    prepared = load_approved_artwork(book, entry['id'], trusted_approvals_sha256=pin)
    with pytest.raises(IllustrationError):
        verify_approved_artwork(book, replace(prepared, **{field:value}),
                                trusted_approvals_sha256=pin)


def test_incomplete_opt_in_fails_closed_without_publishing(sample, tmp_path):
    _, book, _, entry, _, pin, _ = sample
    out = tmp_path / 'out'
    build_demo(book, out)
    before = {p.name: sha256(p.read_bytes()).hexdigest() for p in out.glob('*') if p.is_file()}
    with pytest.raises(IllustrationError):
        build_demo(book, out, illustration_id=entry['id'])
    after = {p.name: sha256(p.read_bytes()).hexdigest() for p in out.glob('*') if p.is_file()}
    assert before == after


def test_png_mutated_after_loading_cannot_be_published(sample, tmp_path, monkeypatch):
    from lafractale.export import builder
    _, book, _, entry, asset, pin, _ = sample
    out = tmp_path / 'prior'
    build_demo(book, out)
    original_hash = sha256((out / 'manifest.json').read_bytes()).hexdigest()
    original_writer = builder.write_pdf
    counter = {'n':0}
    def attack(*a, **kw):
        original_writer(*a, **kw)
        counter['n'] += 1
        if counter['n'] == 1:
            asset.write_bytes(_make_gray(shade=150))
    monkeypatch.setattr(builder, 'write_pdf', attack)
    with pytest.raises(IllustrationError):
        build_demo(book, out, illustration_id=entry['id'], trusted_approvals_sha256=pin)
    assert sha256((out / 'manifest.json').read_bytes()).hexdigest() == original_hash


def test_artwork_forgery_direct_write_pdf_denied(sample, tmp_path):
    _, book, _, entry, _, pin, _ = sample
    art = load_approved_artwork(book, entry['id'], trusted_approvals_sha256=pin)
    acts = [generate(spec, stable_seed(book.book_id, spec.id, 2026)) for spec in demo_specs(book)]
    with pytest.raises(IllustrationError):
        write_pdf(tmp_path / 'forged.pdf', acts, book.data, answer_key=False,
                  artwork=replace(art, sha256='a' * 64), approved_book=book,
                  trusted_approvals_sha256=pin)
    assert not (tmp_path / 'forged.pdf').exists()


def test_manifest_illustration_forged_even_with_outputs_checksums_recalculated(sample, tmp_path):
    _, book, _, entry, _, pin, _ = sample
    out = tmp_path / 'out'
    build_demo(book, out, illustration_id=entry['id'], trusted_approvals_sha256=pin)
    manifest = json.loads((out / 'manifest.json').read_text())
    manifest['illustration']['sha256'] = 'a' * 64
    (out / 'manifest.json').write_text(json.dumps(manifest))
    assert audit_output(out, book=book, illustration_id=entry['id'], trusted_approvals_sha256=pin)


def test_registry_changes_after_build_deny_audit(sample, tmp_path):
    _, book, _, entry, _, pin, persist = sample
    out = tmp_path / 'out'
    build_demo(book, out, illustration_id=entry['id'], trusted_approvals_sha256=pin)
    entry['human_approved'] = False
    persist()
    assert audit_output(out, book=book, illustration_id=entry['id'], trusted_approvals_sha256=pin)


def test_partial_qa_context_rejected(sample, tmp_path):
    _, book, _, entry, _, pin, _ = sample
    out = tmp_path / 'out'
    build_demo(book, out)
    assert audit_output(out, book=book, illustration_id=entry['id'])
    assert audit_output(out, book=book, trusted_approvals_sha256=pin)


def test_pixel_swap_inside_pdf_detected_despite_rehashed_manifest(sample, tmp_path):
    _, book, _, entry, _, pin, _ = sample
    out = tmp_path / 'out'
    build_demo(book, out, illustration_id=entry['id'], trusted_approvals_sha256=pin)
    path = out / 'interior.pdf'
    with fitz.open(path) as doc:
        xref = doc[0].get_image_info(xrefs=True)[0]['xref']
        raw = bytearray(doc.xref_stream(xref))
        assert len(raw) == 660 * 220
        raw[100] ^= 12
        doc.update_stream(xref, bytes(raw), compress=True)
        mutated_pdf = doc.tobytes(garbage=3, deflate=True)
    path.write_bytes(mutated_pdf)
    manifest_path = out / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['outputs']['interior.pdf'] = sha256(mutated_pdf).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    result = audit_output(out, book=book, illustration_id=entry['id'], trusted_approvals_sha256=pin)
    assert any('pixels graphiques différents' in x for x in result), result


def test_preview_swap_detected_without_manifest_hash(sample, tmp_path):
    _, book, _, entry, _, pin, _ = sample
    out = tmp_path / 'out'
    build_demo(book, out, illustration_id=entry['id'], trusted_approvals_sha256=pin)
    preview = out / 'previews/page_02.png'
    with Image.open(preview) as img:
        img.load()
        img.putpixel((25, 25), (0, 0, 0))
        img.save(preview)
    result = audit_output(out, book=book, illustration_id=entry['id'], trusted_approvals_sha256=pin)
    assert any('aperçu' in x.lower() for x in result), result


def test_small_dpi_rejected_and_last_demo_kept(sample, tmp_path):
    _, book, _, entry, asset, _, persist = sample
    out = tmp_path / 'out'
    build_demo(book, out)
    prior_sha = sha256((out / 'manifest.json').read_bytes()).hexdigest()
    asset.write_bytes(_make_gray(size=(64, 20)))
    entry.update(width=64, height=20, sha256=sha256(asset.read_bytes()).hexdigest())
    pin = persist()
    with pytest.raises(IllustrationError, match='Résolution insuffisante'):
        build_demo(book, out, illustration_id=entry['id'], trusted_approvals_sha256=pin)
    assert sha256((out / 'manifest.json').read_bytes()).hexdigest() == prior_sha


def test_unsupported_approval_pin_is_not_trusted(sample):
    _, book, _, entry, _, pin, _ = sample
    with pytest.raises(IllustrationError):
        load_approved_artwork(book, entry['id'], trusted_approvals_sha256='incorrect')


def test_approved_png_replacement_during_qa_detected(sample, tmp_path):
    _, book, _, entry, asset, pin, _ = sample
    out = tmp_path / 'out'
    build_demo(book, out, illustration_id=entry['id'], trusted_approvals_sha256=pin)
    asset.write_bytes(_make_gray(shade=75))
    result = audit_output(out, book=book, illustration_id=entry['id'], trusted_approvals_sha256=pin)
    assert result and any('approbation' in err.lower() or 'image' in err.lower() for err in result)


def test_direct_write_pdf_with_valid_approval_only_on_approved_book(sample, tmp_path):
    root, book, _, entry, _, pin, _ = sample
    art = load_approved_artwork(book, entry['id'], trusted_approvals_sha256=pin)
    activities = [generate(spec, stable_seed(book.book_id, spec.id, 2026)) for spec in demo_specs(book)]
    christmas = load_book(root / 'books/christmas_2026/book.yaml')
    with pytest.raises((IllustrationError, ValueError)):
        write_pdf(tmp_path / 'unauthorized.pdf', activities, christmas.data,
                  answer_key=False, artwork=art, approved_book=christmas,
                  trusted_approvals_sha256=pin)
    assert not (tmp_path / 'unauthorized.pdf').exists()


def test_vector_pdf_overlay_rejected_despite_forged_manifest_and_previews(sample, tmp_path):
    """An attacker cannot hide unauthorized vector art behind the valid PNG."""
    _, book, _, entry, _, pin, _ = sample
    out = tmp_path / 'out'
    build_demo(book, out, illustration_id=entry['id'], trusted_approvals_sha256=pin)
    interior = out / 'interior.pdf'
    with fitz.open(interior) as doc:
        page = doc[0]
        page.draw_rect(fitz.Rect(90, 200, 115, 215), color=(0, 0, 0), fill=(0, 0, 0))
        edited = doc.tobytes(garbage=3, deflate=True)
    interior.write_bytes(edited)
    with fitz.open(interior) as doc:
        for n, page in enumerate(doc, 1):
            page.get_pixmap(matrix=fitz.Matrix(1.4, 1.4), alpha=False).save(
                str(out / 'previews' / f'page_{n:02d}.png'))
    manifest_path = out / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['outputs']['interior.pdf'] = sha256(edited).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    result = audit_output(out, book=book, illustration_id=entry['id'], trusted_approvals_sha256=pin)
    assert any('PDF différent de la régénération approuvée' in err for err in result), result


def test_dangerous_preview_dimensions_rejected_before_decoding(sample, tmp_path):
    _, book, _, entry, _, pin, _ = sample
    out = tmp_path / 'out'
    build_demo(book, out, illustration_id=entry['id'], trusted_approvals_sha256=pin)
    preview = out / 'previews/page_01.png'
    data = bytearray(preview.read_bytes())
    data[16:24] = struct.pack('>II', 4_096_000, 4_096_000)
    preview.write_bytes(data)
    result = audit_output(out, book=book, illustration_id=entry['id'], trusted_approvals_sha256=pin)
    assert any('Dimensions/format' in x for x in result), result
