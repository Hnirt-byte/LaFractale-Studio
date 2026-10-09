"""Independent adversarial regression tests for the lexical/QA-root trust boundary.

Untrusted emitted content can be modified with recomputed unkeyed checksums.
The independently approved Book and companion catalogue are not attacker-owned.
"""
from __future__ import annotations

import hashlib
import json
import shutil

import yaml
from pathlib import Path

import fitz
import pytest

from lafractale.__main__ import main
from lafractale.config.schema import load_book
from lafractale.export.builder import audit_output, build_demo
from lafractale.security.text import UnsafeEditorialText, verify_text_policy

ROOT = Path(__file__).resolve().parents[1]
CHRISTMAS = ROOT / 'books/christmas_2026/book.yaml'
PAYLOADS = ('Pip_', '_Pip', 'Pip2', 'P\u0338ip', 'P\u0332ip', 'Pip-2', '(Pip)', 'Pip_42')


@pytest.fixture(scope='module')
def canonical_demo(tmp_path_factory):
    work = tmp_path_factory.mktemp('trusted-audit-lexical')
    book = load_book(CHRISTMAS)
    out = work / 'demo'
    build_demo(book, out)
    assert audit_output(out, book=book) == []
    return out


@pytest.fixture
def demo(tmp_path, canonical_demo):
    out = tmp_path / 'demo'
    shutil.copytree(canonical_demo, out)
    return out


def _json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def _save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True), encoding='utf-8')


def _update_checksum(out, leaf):
    manifest = _json(out / 'manifest.json')
    manifest['outputs'][leaf] = hashlib.sha256((out / leaf).read_bytes()).hexdigest()
    _save(out / 'manifest.json', manifest)


@pytest.mark.parametrize('payload', PAYLOADS)
def test_direct_editorial_policy_rejects_forbidden_name_in_word_boundary_variants(payload):
    with pytest.raises(UnsafeEditorialText, match='Compagnon non autorisé|combinant'):
        verify_text_policy({'scene': f'{payload} dans la neige'}, forbidden_names=('Pip',))


@pytest.mark.parametrize('payload', PAYLOADS)
def test_audit_rejects_forged_activities_json_even_with_checksum_rewritten(demo, payload):
    path = demo / 'activities.json'
    activities = _json(path)
    activities[0]['scene'] = f'{payload} apparaît dans la neige'
    _save(path, activities)
    _update_checksum(demo, 'activities.json')
    assert audit_output(demo, book=load_book(CHRISTMAS)), f'payload escaped: {payload!r}'


@pytest.mark.parametrize('payload', PAYLOADS)
def test_audit_rejects_forged_quality_json_with_rewritten_checksum(demo, payload):
    path = demo / 'quality_report.json'
    report = _json(path)
    report['blocking_for_publication'].append(f'{payload} apparaît dans la neige')
    _save(path, report)
    _update_checksum(demo, 'quality_report.json')
    assert audit_output(demo, book=load_book(CHRISTMAS)), f'payload escaped: {payload!r}'


@pytest.mark.parametrize('payload', PAYLOADS)
def test_audit_rejects_forged_manifest(demo, payload):
    path = demo / 'manifest.json'
    manifest = _json(path)
    manifest['untrusted_note'] = f'{payload} apparaît dans la neige'
    _save(path, manifest)
    assert audit_output(demo, book=load_book(CHRISTMAS)), f'payload escaped: {payload!r}'


@pytest.mark.parametrize('payload', PAYLOADS)
def test_audit_rejects_forged_quality_markdown(demo, payload):
    path = demo / 'quality_report.md'
    path.write_text(path.read_text(encoding='utf-8') + f'\n{payload} apparaît dans la neige\n', encoding='utf-8')
    assert audit_output(demo, book=load_book(CHRISTMAS)), f'payload escaped: {payload!r}'


@pytest.mark.parametrize('payload', ('Pip_', '_Pip', 'Pip2', 'Pip-2', 'P\u0338ip', 'P\u0332ip'))
def test_audit_rejects_actual_pdf_text_injection_with_updated_checksum(demo, payload, tmp_path):
    path = demo / 'interior.pdf'
    altered = tmp_path / 'altered.pdf'
    with fitz.open(path) as pdf:
        pdf[0].insert_font(fontname='DejaVuSafe', fontfile='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
        pdf[0].insert_text((60, 85), f'{payload} appears', fontname='DejaVuSafe', fontsize=12)
        pdf.save(altered)
    altered.replace(path)
    with fitz.open(path) as pdf:
        assert payload in '\n'.join(page.get_text() for page in pdf)
    _update_checksum(demo, 'interior.pdf')
    assert audit_output(demo, book=load_book(CHRISTMAS)), f'PDF payload escaped: {payload!r}'


def test_rejects_symlinked_audit_root_and_cli(demo, tmp_path):
    alias = tmp_path / 'aliased-demo'
    alias.symlink_to(demo, target_is_directory=True)
    book = load_book(CHRISTMAS)
    assert audit_output(demo, book=book) == []
    assert audit_output(alias, book=book), 'audit followed symlinked root'
    assert main(['qa', str(alias), '--book', str(CHRISTMAS)]) != 0


def test_rejects_symlinked_audit_parent(demo, tmp_path):
    parent = tmp_path / 'parent-alias'
    parent.symlink_to(tmp_path, target_is_directory=True)
    assert audit_output(parent / 'demo', book=load_book(CHRISTMAS))


def test_positive_latin_accents_and_nonreserved_names():
    verify_text_policy('Pipette, piperade, Noël, façade, forêt, ÉTOILES, 123!', forbidden_names=('Pip',))
    verify_text_policy('Un sapin_42 et une étoile-2', forbidden_names=('Pip',))


def test_combining_marks_are_rejected_without_reserved_companion():
    for mark in ('\u0338', '\u0332', '\u0301', '\u20dd'):
        with pytest.raises(UnsafeEditorialText, match='combinant|Unicode'):
            verify_text_policy('Une ' + mark + ' scène')


@pytest.mark.parametrize('payload', PAYLOADS)
def test_yaml_scene_rejected_before_replacing_valid_demo(tmp_path, payload):
    from lafractale.config.schema import ConfigError
    from lafractale.config.companions import CompanionError
    root = tmp_path / 'project'
    config = root / 'books/christmas_2026/book.yaml'
    config.parent.mkdir(parents=True)
    catalog = root / 'assets/companions/catalog.yaml'
    catalog.parent.mkdir(parents=True)
    (root / 'pyproject.toml').write_text('[project]\n', encoding='utf-8')
    shutil.copy2(CHRISTMAS, config)
    shutil.copy2(ROOT / 'assets/companions/catalog.yaml', catalog)
    book = load_book(config)
    out = tmp_path / 'demo'
    build_demo(book, out)
    before = {f: hashlib.sha256((out/f).read_bytes()).hexdigest() for f in
              ('interior.pdf', 'answer_key.pdf', 'activities.json', 'manifest.json')}
    data = yaml.safe_load(config.read_text(encoding='utf-8'))
    data['demo_activities'][0]['scene'] = f'{payload} dans la neige'
    config.write_text(yaml.safe_dump(data, allow_unicode=True), encoding='utf-8')
    with pytest.raises((ConfigError, UnsafeEditorialText, CompanionError)):
        load_book(config)
    with pytest.raises((ConfigError, UnsafeEditorialText, CompanionError)):
        build_demo(book, out)
    assert {f: hashlib.sha256((out/f).read_bytes()).hexdigest() for f in before} == before


@pytest.mark.parametrize('separator', ('_', '2', '42', '0', '-', '.', '!', '/', '#', '\u2013', '\u2014', '(', ')', '\n'))
def test_lexical_boundaries_consistent_for_prefix_suffix_separator(separator):
    for payload in (f'Pip{separator}', f'{separator}Pip'):
        with pytest.raises(UnsafeEditorialText, match='Compagnon non autorisé'):
            verify_text_policy(payload, forbidden_names=('Pip',))


def test_multiword_companion_with_digits_and_underscores():
    with pytest.raises(UnsafeEditorialText, match='Compagnon non autorisé'):
        verify_text_policy('Luna_7_et_Nino partent', forbidden_names=('Luna et Nino',))
    verify_text_policy('Lunatique et Ninon partent', forbidden_names=('Luna et Nino',))


def test_audit_root_with_parent_symlink_when_target_exists(demo, tmp_path):
    parent = tmp_path / 'aliased-parent'
    parent.symlink_to(tmp_path, target_is_directory=True)
    assert audit_output(parent / 'demo', book=load_book(CHRISTMAS))
