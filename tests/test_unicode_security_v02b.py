"""Threat-matrix regressions from Hermes' fourth independent B1 review.

Each injected YAML must be rejected BEFORE publishing; a previously valid demo
must keep its byte-identical manifest, PDF, activities and quality report.
"""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from shutil import copy2
import json
import unicodedata

import fitz
import pytest
import yaml

from lafractale.config.schema import ConfigError, load_book
from lafractale.config.companions import CompanionError
from lafractale.export import builder
from lafractale.export.builder import audit_output, build_demo
from lafractale.security.text import UnsafeEditorialText, canonical_text, verify_text_policy
from lafractale.story.plan import demo_specs
from lafractale.activities.engine import generate, stable_seed
from lafractale.layout.pdf import write_pdf

ROOT = Path(__file__).resolve().parents[1]


def _christmas_project(tmp_path):
    root = tmp_path / 'project'
    (root / 'books/christmas_2026').mkdir(parents=True)
    (root / 'assets/companions').mkdir(parents=True)
    (root / 'pyproject.toml').write_text('[project]\n', encoding='utf-8')
    copy2(ROOT / 'assets/companions/catalog.yaml', root / 'assets/companions/catalog.yaml')
    config = root / 'books/christmas_2026/book.yaml'
    copy2(ROOT / 'books/christmas_2026/book.yaml', config)
    return root, config


def _fingerprints(out):
    return {file: sha256((out / file).read_bytes()).hexdigest() for file in
            ('interior.pdf', 'answer_key.pdf', 'activities.json', 'manifest.json', 'quality_report.json')}


INVISIBLE = (
    '\u200b', '\u200c', '\u200d', '\u00ad', '\u2060', '\ufeff',
    '\u034f', '\ufe0f', '\U000e0100', '\u061c', '\u180f', '\u2800', '\u3164',
)


@pytest.mark.parametrize('hidden', INVISIBLE, ids=lambda char: f'U+{ord(char):04X}')
def test_yml_invisible_attack_rejected_and_existing_demo_preserved(tmp_path, hidden):
    root, config = _christmas_project(tmp_path)
    original = load_book(config)
    original_yaml = config.read_bytes()
    out = tmp_path / 'demo'
    build_demo(original, out)
    before = _fingerprints(out)
    data = yaml.safe_load(config.read_text(encoding='utf-8'))
    data['demo_activities'][0]['scene'] = f'P{hidden}ip dans la neige'
    config.write_text(yaml.safe_dump(data, allow_unicode=True), encoding='utf-8')
    with pytest.raises(ConfigError, match='invisible|canonique'):
        load_book(config)
    with pytest.raises((CompanionError, ConfigError, UnsafeEditorialText)):
        build_demo(original, out)
    assert _fingerprints(out) == before
    config.write_bytes(original_yaml)
    assert audit_output(out, book=load_book(config)) == []


@pytest.mark.parametrize('scene', (
    'Ｐｉｐ dans la neige',
    'P\u00a0ip dans la neige',
    'P\u212Aip dans la neige',
    'P\u0456p dans la neige',   # Cyrillic i (visually "i")
    '\u03a1ip dans la neige', # Greek capital rho (visually "P")
    'P\u03b9p dans la neige', # Greek iota
    'P\u0131p dans la neige', # Latin dotless i
    '\u1d18\u026a\u1d18 dans la neige', # Latin small-cap lookalikes
))
def test_compatibility_and_confusable_unicode_rejected_at_load(tmp_path, scene):
    root, config = _christmas_project(tmp_path)
    data = yaml.safe_load(config.read_text(encoding='utf-8'))
    data['demo_activities'][0]['scene'] = scene
    config.write_text(yaml.safe_dump(data, allow_unicode=True), encoding='utf-8')
    with pytest.raises(ConfigError, match='canonique|alphabet .*latin|invisible'):
        load_book(config)


def test_valid_composed_french_accents_remain_allowed():
    assert canonical_text('Étoile, Noël : façade, cœur !') == 'étoile, noël : façade, cœur !'
    with pytest.raises(UnsafeEditorialText):
        canonical_text('e\u0301toile')
    verify_text_policy({'scene': 'Une étoile à Noël', 'vocabulary': ['lune', 'sapin']},
                       forbidden_names=('Pip',))


def test_csv_plan_invisible_is_rejected(tmp_path):
    root = tmp_path / 'project'
    (root / 'books/halloween_2026').mkdir(parents=True)
    (root / 'assets/companions').mkdir(parents=True)
    (root / 'assets/characters/pip').mkdir(parents=True)
    (root / 'pyproject.toml').write_text('[project]\n', encoding='utf-8')
    copy2(ROOT / 'assets/companions/catalog.yaml', root / 'assets/companions/catalog.yaml')
    copy2(ROOT / 'assets/characters/pip/pip_officiel_couleur.png', root / 'assets/characters/pip/pip_officiel_couleur.png')
    copy2(ROOT / 'books/halloween_2026/book.yaml', root / 'books/halloween_2026/book.yaml')
    source = ROOT / 'books/halloween_2026/page_plan.csv'
    dest = root / 'books/halloween_2026/page_plan.csv'
    dest.write_text(source.read_text(encoding='utf-8').replace('Pip', 'P\u200bip', 1), encoding='utf-8')
    with pytest.raises(ConfigError, match='invisible'):
        load_book(root / 'books/halloween_2026/book.yaml')


def test_generated_activity_injection_rejected_before_publication(tmp_path, monkeypatch):
    root, config = _christmas_project(tmp_path)
    book = load_book(config)
    out = tmp_path / 'demo'
    build_demo(book, out)
    before = _fingerprints(out)
    generator = builder.generate

    def rogue(spec, seed):
        a = generator(spec, seed)
        return replace(a, scene='P\u200bip dans la neige') if a.type == 'maze' else a

    monkeypatch.setattr(builder, 'generate', rogue)
    with pytest.raises(UnsafeEditorialText, match='invisible'):
        build_demo(book, out)
    assert _fingerprints(out) == before
    # Source-backed replay requires the original generator restored.
    monkeypatch.setattr(builder, "generate", generator)
    assert audit_output(out, book=load_book(config)) == []


def test_direct_pdf_entry_rejects_uncanonical_activity_text(tmp_path):
    root, config = _christmas_project(tmp_path)
    book = load_book(config)
    spec = demo_specs(book)[0]
    activity = generate(spec, stable_seed(book.book_id, spec.id, 2026))
    bad = replace(activity, scene='P\u200bip dans la neige')
    pdf = tmp_path / 'injected.pdf'
    with pytest.raises(UnsafeEditorialText, match='invisible'):
        write_pdf(pdf, [bad], book.data, answer_key=False)
    assert not pdf.exists()


def test_artifacts_audit_rejects_invisible_json_even_with_recomputed_checksum(tmp_path):
    root, config = _christmas_project(tmp_path)
    out = tmp_path / 'demo'
    build_demo(load_book(config), out)
    activities_file = out / 'activities.json'
    manifest_file = out / 'manifest.json'
    activities = json.loads(activities_file.read_text(encoding='utf-8'))
    activities[0]['scene'] = 'P\u200bip dans la neige'
    activities_file.write_text(json.dumps(activities, ensure_ascii=False), encoding='utf-8')
    manifest = json.loads(manifest_file.read_text(encoding='utf-8'))
    manifest['outputs']['activities.json'] = sha256(activities_file.read_bytes()).hexdigest()
    manifest_file.write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')
    assert any('Unicode' in err or 'invisible' in err for err in audit_output(out, book=load_book(config)))


def test_artifacts_audit_rejects_plain_pip_even_with_recomputed_checksum(tmp_path):
    root, config = _christmas_project(tmp_path)
    out = tmp_path / 'demo'
    build_demo(load_book(config), out)
    activities_file = out / 'activities.json'
    manifest_file = out / 'manifest.json'
    activities = json.loads(activities_file.read_text(encoding='utf-8'))
    activities[0]['scene'] = 'PIP apparaît dans la neige'
    activities_file.write_text(json.dumps(activities, ensure_ascii=False), encoding='utf-8')
    manifest = json.loads(manifest_file.read_text(encoding='utf-8'))
    manifest['outputs']['activities.json'] = sha256(activities_file.read_bytes()).hexdigest()
    manifest_file.write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')
    assert any('Compagnon non autorisé' in err for err in audit_output(out, book=load_book(config)))


@pytest.mark.parametrize('payload', ('P\u200bip', 'Ｐｉｐ', 'P\u0456p'))
def test_renderer_level_pdf_spoof_rejected_and_existing_demo_preserved(tmp_path, monkeypatch, payload):
    from lafractale.layout import pdf as renderer
    root, config = _christmas_project(tmp_path)
    book = load_book(config)
    out = tmp_path / 'demo'
    build_demo(book, out)
    before = _fingerprints(out)
    original = renderer._dots

    def injected(canvas, act, board, solution, bold):
        canvas.setFont(bold, 12)
        canvas.drawString(board.x + 25, board.y + 35, payload)
        return original(canvas, act, board, solution, bold)

    monkeypatch.setattr(renderer, '_dots', injected)
    with pytest.raises((UnsafeEditorialText, ConfigError, ValueError)):
        build_demo(book, out)
    assert _fingerprints(out) == before
    # Source-backed replay requires the original renderer restored.
    monkeypatch.setattr(renderer, "_dots", original)
    assert audit_output(out, book=load_book(config)) == []


def test_catalog_companion_name_must_be_canonical(tmp_path):
    root, config = _christmas_project(tmp_path)
    catalog = root / 'assets/companions/catalog.yaml'
    data = yaml.safe_load(catalog.read_text(encoding='utf-8'))
    data['characters']['pip']['name'] = 'P\u200bip'
    catalog.write_text(yaml.safe_dump(data, allow_unicode=True), encoding='utf-8')
    with pytest.raises(ConfigError, match='invisible'):
        load_book(config)


def test_manifest_does_not_disclose_pending_companion_name(tmp_path):
    root, config = _christmas_project(tmp_path)
    out = tmp_path / 'demo'
    build_demo(load_book(config), out)
    manifest_content = (out / 'manifest.json').read_text(encoding='utf-8')
    assert 'pip' not in manifest_content.casefold()
    assert json.loads(manifest_content)['security']['blocked_name_fingerprints']
    assert audit_output(out, book=load_book(config)) == []


def test_audit_does_not_follow_symlinked_activities_json(tmp_path):
    root, config = _christmas_project(tmp_path)
    out = tmp_path / 'demo'
    build_demo(load_book(config), out)
    outside = tmp_path / 'private.json'
    outside.write_text('THIS IS OUTSIDE THE BUILD', encoding='utf-8')
    (out / 'activities.json').unlink()
    (out / 'activities.json').symlink_to(outside)
    assert any('activities.json' in error for error in audit_output(out, book=load_book(config)))
    assert outside.read_text(encoding='utf-8') == 'THIS IS OUTSIDE THE BUILD'


def test_audit_rejects_unapproved_unicode_in_markdown(tmp_path):
    root, config = _christmas_project(tmp_path)
    out = tmp_path / 'demo'
    build_demo(load_book(config), out)
    markdown = out / 'quality_report.md'
    markdown.write_text(markdown.read_text(encoding='utf-8') + '\nP\u200bip', encoding='utf-8')
    assert any('invisible' in error for error in audit_output(out, book=load_book(config)))


def test_direct_pdf_entry_rejects_uncanonical_book_text(tmp_path):
    root, config = _christmas_project(tmp_path)
    book = load_book(config)
    spec = demo_specs(book)[0]
    activity = generate(spec, stable_seed(book.book_id, spec.id, 2026))
    fake_data = {**book.data, 'title': 'No\u200bël'}
    pdf = tmp_path / 'injected-book.pdf'
    with pytest.raises(UnsafeEditorialText, match='invisible'):
        write_pdf(pdf, [activity], fake_data, answer_key=False)
    assert not pdf.exists()
