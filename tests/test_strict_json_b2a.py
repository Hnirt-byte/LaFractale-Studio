"""Adversarial JSON wire-format tests: reject ambiguous keys before any QA decision."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from lafractale.config.schema import load_book
from lafractale.export.builder import audit_output, build_demo
from lafractale.illustrations.registry import IllustrationError, load_approved_artwork
from lafractale.security.strict_json import StrictJSONError, loads_strict
from test_illustrations_b2a import ORIGIN, _make_fixture


def _duplicate(text: str, key: str, evil: object) -> str:
    needle = json.dumps(key, ensure_ascii=False) + ': '
    assert needle in text, (key, text[:120])
    return text.replace(needle, needle + json.dumps(evil, ensure_ascii=False) + ', ' + needle, 1)


@pytest.mark.parametrize(('body', 'key'), [
    ('{"foo": 1, "foo": 2}', 'foo'),
    ('{"outer": {"foo": 1, "foo": 2}}', 'foo'),
    ('{"arr": [{"foo": 1, "foo": 2}]}', 'foo'),
    ('{"\\u0066oo": 1, "foo": 2}', 'foo'),
    ('{"A": 1, "\\u0041": 2}', 'A'),
])
def test_parser_rejects_duplicate_keys_at_any_depth_and_escape(body, key):
    assert json.loads(body)  # Standard parser silently drops one value.
    with pytest.raises(StrictJSONError, match='dupliqu') as exc:
        loads_strict(body)
    assert key in str(exc.value)


@pytest.mark.parametrize('body', ['NaN', 'Infinity', '-Infinity', '{"x": NaN}',
                                  '{"x": Infinity}', '[1, -Infinity]', '1e9999', '{"n": -1e9999}'])
def test_parser_rejects_nonstandard_json_constants(body):
    with pytest.raises(StrictJSONError):
        loads_strict(body)


def test_normal_json_and_unicode_are_preserved():
    data = {'title': 'Noël, joyeux !', 'pages': [{'id': 'ex1', 'allowed': False}]}
    raw = json.dumps(data, ensure_ascii=False).encode('utf-8')
    assert loads_strict(raw) == data
    assert loads_strict(raw.decode('utf-8')) == data


@pytest.mark.parametrize(('filename', 'key', 'evil'), [
    ('manifest.json', 'publication_approved', True),
    ('manifest.json', 'engine_version', '999.0'),
    ('manifest.json', 'unicode_policy', 'DISABLED'),
    ('manifest.json', 'activities.json', 'f' * 64),  # nested outputs key
    ('manifest.json', 'book_id', 'halloween_2026'),
    ('quality_report.json', 'ready_for_kdp', True),
    ('quality_report.json', 'human_approval', 'approved'),  # nested array object
    ('activities.json', 'scene', 'Pip dans la neige'),
])
def test_audit_rejects_duplicate_key_regardless_of_last_wins(tmp_path, filename, key, evil):
    book = load_book(ORIGIN / 'books/christmas_2026/book.yaml')
    out = tmp_path / 'demo'
    build_demo(book, out)
    assert audit_output(out, book=book) == []
    path = out / filename
    altered = _duplicate(path.read_text(encoding='utf-8'), key, evil)
    assert json.loads(altered) == json.loads(path.read_text(encoding='utf-8'))
    path.write_text(altered, encoding='utf-8')
    if filename != 'manifest.json':
        manifest_path = out / 'manifest.json'
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        manifest['outputs'][filename] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')
    errors = audit_output(out, book=book)
    assert errors, (filename, key)
    assert any('dupliqu' in error.lower() for error in errors), errors


@pytest.mark.parametrize(('key', 'evil'), [
    ('schema_version', 999),
    ('illustrations', []),
    ('human_approved', False),
    ('id', 'another-id'),
    ('path', '../outside.png'),
])
def test_registry_rejects_duplicate_keys_even_with_matching_external_pin(tmp_path, key, evil):
    _, book, approvals, entry, _, _, _ = _make_fixture(tmp_path)
    content = approvals.read_text(encoding='utf-8')
    forged = _duplicate(content, key, evil)
    assert json.loads(forged) == json.loads(content)
    approvals.write_text(forged, encoding='utf-8')
    new_pin = hashlib.sha256(approvals.read_bytes()).hexdigest()
    with pytest.raises(IllustrationError, match='JSON invalide'):
        load_approved_artwork(book, entry['id'], trusted_approvals_sha256=new_pin)


@pytest.mark.parametrize(('filename', 'key', 'evil'), [
    ('manifest.json', 'publication_approved', True),
    ('manifest.json', 'approvals_sha256', '0' * 64),  # nested illustration provenance
    ('manifest.json', 'unicode_policy', 'DISABLED'),
    ('activities.json', 'scene', 'Pip dans la neige'),
    ('quality_report.json', 'human_approval', 'approved'),
])
def test_illustrated_audit_rejects_duplicate_at_every_output_layer(tmp_path, filename, key, evil):
    _, book, _, entry, _, pin, _ = _make_fixture(tmp_path)
    out = tmp_path / 'illustrated'
    opts = {'illustration_id': entry['id'], 'trusted_approvals_sha256': pin}
    build_demo(book, out, **opts)
    assert audit_output(out, book=book, **opts) == []
    path = out / filename
    old = path.read_text(encoding='utf-8')
    altered = _duplicate(old, key, evil)
    assert json.loads(altered) == json.loads(old)
    path.write_text(altered, encoding='utf-8')
    if filename != 'manifest.json':
        manifest_path = out / 'manifest.json'
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        manifest['outputs'][filename] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')
    errors = audit_output(out, book=book, **opts)
    assert any('dupliqu' in error.lower() for error in errors), errors


@pytest.mark.parametrize('bad', [
    b'\xef\xbb\xbf{"hello": true}',
    b'{"a":1,}',
    b'{"a":1} {"b":2}',
    b'{"a":1}\x00',
    b'{"a":"\xff"}',
])
def test_strict_parser_rejects_invalid_or_ambiguous_wire_format(bad):
    with pytest.raises(StrictJSONError):
        loads_strict(bad)


def test_parser_rejects_excessive_nesting_gracefully():
    raw = '[' * 5000 + '0' + ']' * 5000
    with pytest.raises(StrictJSONError):
        loads_strict(raw)


def test_parser_rejects_unpaired_unicode_surrogates():
    with pytest.raises(StrictJSONError, match='Unicode'):
        loads_strict(r'{"x": "\ud800"}')
    with pytest.raises(StrictJSONError, match='Unicode'):
        loads_strict(r'{"\udfff": 1}')
