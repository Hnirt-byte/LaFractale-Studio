"""MAJOR-1: PDF bytes must not depend on the caller's environment (SOURCE_DATE_EPOCH, RL_*)."""
import os
import threading
from pathlib import Path

import pytest

from b3b1_support import FIXTURE, tree
from lafractale.engine import EngineError
from lafractale.engine.pipeline import audit_existing_package, generate_package

ENVIRONMENTS = {
    "absent": {"SOURCE_DATE_EPOCH": None},
    "epoch-1": {"SOURCE_DATE_EPOCH": "1"},
    "ci-epoch": {"SOURCE_DATE_EPOCH": "1780000000"},
    "reportlab-switch": {"SOURCE_DATE_EPOCH": "42", "RL_ttfAsciiReadable": "0"},
}


def _apply(monkeypatch, settings):
    for key, value in settings.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)


@pytest.fixture(scope="module")
def reference(tmp_path_factory):
    out = tmp_path_factory.mktemp("repro-ref") / "pkg"
    mp = pytest.MonkeyPatch()
    try:
        mp.delenv("SOURCE_DATE_EPOCH", raising=False)
        generate_package(FIXTURE, out)
    finally:
        mp.undo()
    return out


@pytest.mark.parametrize("name", sorted(ENVIRONMENTS))
def test_package_is_byte_identical_whatever_the_external_environment(name, reference, tmp_path, monkeypatch):
    _apply(monkeypatch, ENVIRONMENTS[name])
    out = tmp_path / "pkg"
    generate_package(FIXTURE, out)
    assert tree(out) == tree(reference)


def test_audit_in_a_different_environment_passes(reference, monkeypatch):
    _apply(monkeypatch, {"SOURCE_DATE_EPOCH": "1780000000", "RL_ttfAsciiReadable": "0"})
    assert audit_existing_package(reference, FIXTURE) == []


def test_process_environment_is_untouched_after_success(tmp_path, monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "777")
    before = dict(os.environ)
    generate_package(FIXTURE, tmp_path / "pkg")
    assert dict(os.environ) == before


def test_process_environment_is_untouched_after_an_exception(tmp_path, monkeypatch):
    from b3b1_support import mutated
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "777")
    bad = tmp_path / "overflow.json"
    bad.write_bytes(mutated(lambda d: d["pages"][1].update(prompt_en="W" * 79)))
    before = dict(os.environ)
    with pytest.raises(EngineError):
        generate_package(bad, tmp_path / "never")
    assert dict(os.environ) == before and not (tmp_path / "never").exists()


def test_concurrent_environment_changes_cannot_alter_the_output(reference, tmp_path):
    """Another thread keeps rewriting the process environment while a package is rendered."""
    stop = threading.Event()

    def churn():
        values = ["1", "2", "1780000000", "946684800"]
        index = 0
        while not stop.is_set():
            os.environ["SOURCE_DATE_EPOCH"] = values[index % len(values)]
            os.environ["RL_ttfAsciiReadable"] = str(index % 2)
            index += 1

    saved = {k: os.environ.get(k) for k in ("SOURCE_DATE_EPOCH", "RL_ttfAsciiReadable")}
    thread = threading.Thread(target=churn, daemon=True)
    thread.start()
    try:
        out = tmp_path / "pkg"
        generate_package(FIXTURE, out)
    finally:
        stop.set()
        thread.join()
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    assert tree(out) == tree(reference)


REFERENCE = FIXTURE.parent / "reference_hashes.json"


def _environment_fingerprint():
    import hashlib
    import reportlab
    try:
        import pymupdf
    except ImportError:  # pragma: no cover
        import fitz as pymupdf
    fonts = {}
    for name, env, default in (("DejaVuSans.ttf", "LAFRACTALE_FONT_PATH", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
                               ("DejaVuSans-Bold.ttf", "LAFRACTALE_FONT_BOLD_PATH",
                                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")):
        fonts[name] = hashlib.sha256(open(os.environ.get(env, default), "rb").read()).hexdigest()
    return {"reportlab": reportlab.Version, "pymupdf": pymupdf.__version__, "fonts_sha256": fonts}


def test_reference_hashes_of_the_synthetic_package(reference):
    """Python 3.11 (CI) and 3.13 must both reproduce the recorded reference package.

    activities.json and the source copy depend on no PDF library and are always compared.
    The PDFs, report and manifest depend on the exact ReportLab / PyMuPDF / DejaVu versions,
    so they are compared only when the environment fingerprint matches the recorded one
    (otherwise the test is skipped with an explicit reason, never silently weakened).
    """
    import hashlib
    import json
    recorded = json.loads(REFERENCE.read_text(encoding="utf-8"))
    produced = {name: hashlib.sha256(data).hexdigest() for name, data in tree(reference).items()}
    assert {k: produced[k] for k in recorded["always_stable"]} == recorded["always_stable"]
    assert recorded["pdf_creation_epoch"] == 946684800
    if _environment_fingerprint() != recorded["environment"]:
        pytest.skip(f"empreintes PDF de référence non comparables : environnement "
                    f"{_environment_fingerprint()} ≠ {recorded['environment']}")
    assert {k: produced[k] for k in recorded["environment_dependent"]} == recorded["environment_dependent"]


def test_render_process_ignores_a_planted_module_in_the_working_directory(tmp_path, monkeypatch):
    from lafractale.engine.contracts import load_spec_set
    from lafractale.engine.pipeline import build_activities
    from lafractale.engine.render import render_slice
    spec = load_spec_set(FIXTURE)
    activities = build_activities(spec).activities  # imported/validated BEFORE changing directory
    decoy = tmp_path / "cwd" / "lafractale"
    decoy.mkdir(parents=True)
    (decoy / "__init__.py").write_text("open('PWNED', 'w').write('x')\n")
    monkeypatch.chdir(tmp_path / "cwd")
    out = tmp_path / "out"
    out.mkdir()
    render_slice(spec, activities, out)
    assert not (tmp_path / "cwd" / "PWNED").exists() and (out / "interior_SYNTHETIC_NON_PRODUCTION.pdf").is_file()


def test_child_pythonpath_is_absolute_and_starts_with_the_running_package(tmp_path, monkeypatch):
    from lafractale.engine.render import child_pythonpath
    import lafractale
    monkeypatch.chdir(tmp_path)
    value = child_pythonpath("src" + os.pathsep + "/opt/x")
    parts = value.split(os.pathsep)
    assert parts[0] == str(Path(lafractale.__file__).resolve().parents[1])
    assert all(os.path.isabs(p) for p in parts) and str(tmp_path / "src") in parts and "/opt/x" in parts


def test_reportlab_user_settings_file_in_home_cannot_alter_the_output(reference, tmp_path, monkeypatch):
    """ReportLab executes ``~/.reportlab_settings`` (HOME) at import: it must not reach the render."""
    home = tmp_path / "home"
    home.mkdir()
    (home / ".reportlab_settings").write_text("ttfAsciiReadable = 0\npdfComments = 1\n")
    monkeypatch.setenv("HOME", str(home))
    out = tmp_path / "pkg"
    generate_package(FIXTURE, out)
    assert tree(out) == tree(reference)


def test_reportlab_settings_module_on_the_python_path_cannot_alter_the_output(reference, tmp_path, monkeypatch):
    decoy = tmp_path / "decoy"
    decoy.mkdir()
    (decoy / "reportlab_settings.py").write_text("ttfAsciiReadable = 0\npdfComments = 1\n")
    existing = os.environ.get("PYTHONPATH", "")
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join(filter(None, [str(decoy), existing])))
    out = tmp_path / "pkg"
    generate_package(FIXTURE, out)
    assert tree(out) == tree(reference)


def test_oversized_render_job_is_refused_before_any_process_is_started(monkeypatch, tmp_path):
    import subprocess
    from lafractale.engine import render
    from lafractale.engine.pipeline import build_activities
    from lafractale.engine.contracts import load_spec_set
    spec = load_spec_set(FIXTURE)
    activities = build_activities(spec).activities
    monkeypatch.setattr(render, "MAX_JOB_BYTES", 100)

    def forbidden(*args, **kwargs):
        raise AssertionError("process started for an oversized job")

    monkeypatch.setattr(subprocess, "run", forbidden)
    with pytest.raises(EngineError, match="volumineux"):
        render.render_slice(spec, activities, tmp_path)
