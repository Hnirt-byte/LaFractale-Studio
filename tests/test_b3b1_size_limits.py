"""MINOR-1: every audited read is bounded and checked on the descriptor actually opened."""
import os
import shutil
import stat

import pytest

from b3b1_support import FIXTURE
from lafractale.engine import EngineError
from lafractale.engine.pipeline import audit_existing_package, generate_package


@pytest.fixture(scope="module")
def pristine(tmp_path_factory):
    out = tmp_path_factory.mktemp("limits") / "pkg"
    generate_package(FIXTURE, out)
    return out


@pytest.fixture
def package(pristine, tmp_path):
    copy = tmp_path / "pkg"
    shutil.copytree(pristine, copy)
    return copy


def _sparse(path, size):
    path.unlink()
    with open(path, "wb") as handle:
        handle.truncate(size)


def test_oversized_json_is_refused_before_being_read(package):
    from lafractale.engine.qa import MAX_JSON_BYTES
    _sparse(package / "activities.json", MAX_JSON_BYTES + 1)
    errors = audit_existing_package(package, FIXTURE)
    assert any("activities.json" in e and "volumineux" in e for e in errors), errors


def test_oversized_pdf_is_refused_before_being_read(package):
    from lafractale.engine.qa import MAX_PDF_BYTES
    _sparse(package / "interior_SYNTHETIC_NON_PRODUCTION.pdf", MAX_PDF_BYTES + 1)
    errors = audit_existing_package(package, FIXTURE)
    assert any("interior_SYNTHETIC_NON_PRODUCTION.pdf" in e and "volumineux" in e for e in errors), errors


def test_oversized_embedded_source_is_refused(package):
    from lafractale.engine.contracts import MAX_SOURCE_BYTES
    _sparse(package / "sources" / "spec.json", MAX_SOURCE_BYTES + 1)
    assert any("volumineux" in e for e in audit_existing_package(package))


def test_oversized_source_file_is_refused_by_the_cli_path(tmp_path):
    from lafractale.engine.contracts import MAX_SOURCE_BYTES, ContractError, read_source_file
    big = tmp_path / "big.json"
    with open(big, "wb") as handle:
        handle.truncate(MAX_SOURCE_BYTES + 1)
    with pytest.raises(ContractError, match="volumineux"):
        read_source_file(big)


def test_read_bounded_refuses_special_files_without_blocking(tmp_path):
    from lafractale.engine.contracts import read_bounded
    with pytest.raises(EngineError, match="régulier"):
        read_bounded("/dev/zero", 10, label="périphérique")
    fifo = tmp_path / "pipe"
    os.mkfifo(fifo)
    with pytest.raises(EngineError, match="régulier"):
        read_bounded(fifo, 10, label="tube")


def test_read_bounded_refuses_symlinks(tmp_path):
    from lafractale.engine.contracts import read_bounded
    target = tmp_path / "target"
    target.write_bytes(b"x")
    link = tmp_path / "link"
    link.symlink_to(target)
    with pytest.raises(EngineError):
        read_bounded(link, 10, label="lien")


def test_read_bounded_checks_the_opened_descriptor_not_a_stale_size(tmp_path, monkeypatch):
    """The file is larger than what fstat reported (it grew after the check)."""
    from lafractale.engine import contracts
    victim = tmp_path / "grows"
    victim.write_bytes(b"x" * 100)
    real = os.fstat

    def lying_fstat(fd):
        info = real(fd)
        if stat.S_ISREG(info.st_mode):
            values = list(info)
            values[stat.ST_SIZE] = 5
            return os.stat_result(values)
        return info

    monkeypatch.setattr(contracts.os, "fstat", lying_fstat)
    with pytest.raises(EngineError, match="grossi|volumineux"):
        contracts.read_bounded(victim, 10, label="fichier")


def test_read_bounded_reads_exactly_the_content_within_the_limit(tmp_path):
    from lafractale.engine.contracts import read_bounded
    f = tmp_path / "ok"
    f.write_bytes(b"x" * 10)
    assert read_bounded(f, 10, label="ok") == b"x" * 10
    f.write_bytes(b"x" * 11)
    with pytest.raises(EngineError, match="volumineux"):
        read_bounded(f, 10, label="ok")
