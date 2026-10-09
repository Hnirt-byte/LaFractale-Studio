"""Regression tests for publication and rollback, including injected OS errors.

In particular, an old valid demo must survive when BOTH publishing and restoring
fail; a failed restore must retain its backup for explicit recovery.
"""
from __future__ import annotations

import errno
from pathlib import Path

import pytest

from lafractale.config.schema import load_book
from lafractale.export import builder
from lafractale.export.builder import audit_output, build_demo
from lafractale.export.securefs import UnsafeOutputPath, parent_dirfd

ROOT = Path(__file__).resolve().parents[1]


def christmas():
    return load_book(ROOT / 'books/christmas_2026/book.yaml')


def _replace_fault(monkeypatch, leaf: str, *, publish_fail: bool, restore_fail: bool):
    real_replace = builder.os.replace
    calls = []

    def simulate(src, dst, *, src_dir_fd=None, dst_dir_fd=None):
        calls.append((src, dst))
        if publish_fail and src.startswith(f'.{leaf}.build-') and dst == leaf:
            raise OSError(errno.EIO, 'simulated publishing failure')
        if restore_fail and src.startswith(f'.{leaf}.previous-') and dst == leaf:
            raise OSError(errno.EPERM, 'simulated restoration failure')
        return real_replace(src, dst, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

    monkeypatch.setattr(builder.os, 'replace', simulate)
    return calls


def test_double_failure_preserves_valid_backup_and_exposes_recovery_path(tmp_path, monkeypatch):
    out = tmp_path / 'demo'
    book = christmas()
    build_demo(book, out)
    original = {p.name: p.read_bytes() for p in out.iterdir() if p.is_file()}
    assert audit_output(out, book=book) == []

    _replace_fault(monkeypatch, out.name, publish_fail=True, restore_fail=True)
    with pytest.raises(builder.PublicationRecoveryError) as error:
        build_demo(book, out, seed=777)

    assert not isinstance(error.value, UnsafeOutputPath)
    assert 'previous-' in str(error.value)
    assert 'publishing failure' in str(error.value)
    assert 'restoration failure' in str(error.value)
    backups = list(tmp_path.glob('.demo.previous-*'))
    assert len(backups) == 1, 'backup MUST survive failed restoration'
    assert error.value.backup_path == backups[0]
    assert audit_output(backups[0], book=book) == []
    assert all((backups[0] / name).read_bytes() == content for name, content in original.items())
    assert not out.exists()
    assert not list(tmp_path.glob('.demo.build-*'))


def test_single_publish_failure_restores_previous_valid_demo(tmp_path, monkeypatch):
    out = tmp_path / 'demo'
    book = christmas()
    build_demo(book, out)
    original = (out / 'manifest.json').read_bytes()
    _replace_fault(monkeypatch, out.name, publish_fail=True, restore_fail=False)
    with pytest.raises(builder.PublicationError, match='publishing failure') as error:
        build_demo(book, out, seed=777)
    assert not isinstance(error.value, UnsafeOutputPath)
    assert audit_output(out, book=book) == []
    assert (out / 'manifest.json').read_bytes() == original
    assert not list(tmp_path.glob('.demo.previous-*'))
    assert not list(tmp_path.glob('.demo.build-*'))


def test_publish_failure_without_prior_demo_leaves_no_partial_output(tmp_path, monkeypatch):
    out = tmp_path / 'demo'
    _replace_fault(monkeypatch, out.name, publish_fail=True, restore_fail=False)
    with pytest.raises(builder.PublicationError, match='publishing failure'):
        build_demo(christmas(), out)
    assert not out.exists()
    assert not list(tmp_path.glob('.demo.previous-*'))
    assert not list(tmp_path.glob('.demo.build-*'))


def test_successful_republication_retires_previous_backup(tmp_path):
    out = tmp_path / 'demo'
    book = christmas()
    build_demo(book, out, seed=123)
    previous = (out / 'activities.json').read_bytes()
    build_demo(book, out, seed=777)
    assert audit_output(out, book=book) == []
    assert previous != (out / 'activities.json').read_bytes()
    assert not list(tmp_path.glob('.demo.previous-*'))
    assert not list(tmp_path.glob('.demo.build-*'))


def test_parent_dirfd_does_not_misclassify_body_oserror(tmp_path):
    with pytest.raises(OSError, match='simulated downstream IO failure') as error:
        with parent_dirfd(tmp_path / 'demo'):
            raise OSError(errno.EIO, 'simulated downstream IO failure')
    assert not isinstance(error.value, UnsafeOutputPath)


def test_parent_dirfd_rejects_unsafe_parent_symlink(tmp_path):
    external = tmp_path / 'external'
    external.mkdir()
    link = tmp_path / 'link'
    link.symlink_to(external, target_is_directory=True)
    with pytest.raises(UnsafeOutputPath):
        with parent_dirfd(link / 'demo'):
            pass
