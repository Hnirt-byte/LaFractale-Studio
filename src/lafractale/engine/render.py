"""Page composition and PDF rendering, delegated to the existing renderer.

``write_pdf`` (layout/pdf.py) composes every page, validates it before the file
exists, embeds the fonts and creates the file exclusively. This module chooses the
file names, refuses to write anything that already exists and, above all, makes the
bytes independent of the caller's environment:

ReportLab reads ``SOURCE_DATE_EPOCH`` (PDF dates) and ``RL_*`` variables (e.g.
``RL_ttfAsciiReadable``, ``RL_pdfComments``) from the process environment, which is
global state. Rendering therefore runs in a CHILD process whose environment is a
sanitized copy: ``SOURCE_DATE_EPOCH`` set to ``CANONICAL_PDF_EPOCH`` and every ``RL_*``
removed. The parent never modifies ``os.environ``, so concurrent threads or other
ReportLab users in the parent cannot influence (or be influenced by) a render.
ReportLab also executes ``reportlab_settings`` (sys.path) and ``~/.reportlab_settings``
(HOME) at import: the child gets an empty HOME and a stub ``reportlab_settings`` module.
The only remaining host-level input is ``reportlab/local_rl_settings.py`` of the
installation itself, which is part of the library version fingerprint (see the docs).
"""
from __future__ import annotations

import dataclasses
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Mapping, Sequence

from lafractale.activities.models import Activity
from lafractale.engine import EngineError
from lafractale.engine.contracts import SpecSet, canonical_json_bytes

INTERIOR_NAME = "interior_SYNTHETIC_NON_PRODUCTION.pdf"
ANSWER_NAME = "answer_key_SYNTHETIC_NON_PRODUCTION.pdf"
ACTIVITIES_NAME = "activities.json"
REPORT_NAME = "quality_report.json"
MANIFEST_NAME = "manifest.json"
SOURCE_NAME = "sources/spec.json"
SOURCE_DIR = "sources"
#: Closed inventory of a package, as relative POSIX paths.
PACKAGE_FILES = (INTERIOR_NAME, ANSWER_NAME, ACTIVITIES_NAME, REPORT_NAME, MANIFEST_NAME, SOURCE_NAME)

#: Canonical creation/modification time of every synthetic PDF: 2000-01-01T00:00:00Z.
CANONICAL_PDF_EPOCH = 946684800
#: The same instant as written by ReportLab in the PDF information dictionary.
CANONICAL_PDF_DATE = "D" + time.strftime(":%Y%m%d%H%M%S", time.gmtime(CANONICAL_PDF_EPOCH)) + "+00'00'"

WORKER_MODULE = "lafractale.engine._render_worker"
RENDER_TIMEOUT_SECONDS = 300
MAX_JOB_BYTES = 4_000_000
_ACTIVITY_FIELDS = tuple(field.name for field in dataclasses.fields(Activity))
_TUPLE_FIELDS = ("age_band", "vocabulary", "assets")


def canonical_render_environment(base: Mapping[str, str]) -> dict[str, str]:
    """Pure function: a sanitized COPY of ``base`` for the render process."""
    env = {key: value for key, value in base.items()
           if key != "SOURCE_DATE_EPOCH" and not key.startswith("RL_")}
    env["SOURCE_DATE_EPOCH"] = str(CANONICAL_PDF_EPOCH)
    return env


def environment_is_canonical(env: Mapping[str, str]) -> bool:
    return env.get("SOURCE_DATE_EPOCH") == str(CANONICAL_PDF_EPOCH) and not any(
        key.startswith("RL_") for key in env)


def child_pythonpath(inherited: str) -> str:
    """Absolute PYTHONPATH for the render process.

    The child must run the SAME ``lafractale`` code as this process whatever the working
    directory: the package root is put first and relative entries are made absolute here.
    """
    import lafractale
    root = str(Path(lafractale.__file__).resolve().parents[1])
    entries = [os.path.abspath(entry) for entry in inherited.split(os.pathsep) if entry]
    return os.pathsep.join([root, *[entry for entry in entries if entry != root]])


def _snapshot_environ() -> dict[str, str]:
    """Copy os.environ without mutating it (retry if another thread edits it meanwhile)."""
    for _ in range(5):
        try:
            return dict(os.environ)
        except RuntimeError:  # dictionary changed size during iteration
            continue
    raise EngineError("Environnement du processus instable : rendu refusé")


def activity_from_dict(data: Mapping[str, object]) -> Activity:
    """Inverse of ``Activity.as_dict`` for the JSON job handed to the render process."""
    if set(data) != set(_ACTIVITY_FIELDS):
        raise EngineError("Activité du job de rendu mal formée")
    values = dict(data)
    for name in _TUPLE_FIELDS:
        values[name] = tuple(values[name])
    return Activity(**values)


def write_pdfs_here(book: dict, activities: Sequence[Activity], out_dir: Path) -> None:
    """Render both PDFs with the historical writer IN THIS PROCESS.

    Called by the render process only; calling it elsewhere yields bytes that depend on
    the caller's environment (see module docstring).
    """
    from lafractale.layout.pdf import write_pdf  # heavy import kept out of the parent path
    write_pdf(out_dir / INTERIOR_NAME, list(activities), book, answer_key=False)
    write_pdf(out_dir / ANSWER_NAME, list(activities), book, answer_key=True)


def render_slice(spec_set: SpecSet, activities: tuple[Activity, ...], out_dir: Path) -> tuple[Path, Path]:
    """Render the fiches and the corrigés into ``out_dir`` (new files only), isolated."""
    out_dir = Path(os.path.abspath(out_dir))
    job = canonical_json_bytes({"book": spec_set.book_dict(),
                                "activities": [activity.as_dict() for activity in activities]})
    if len(job) > MAX_JOB_BYTES:
        raise EngineError(f"Rendu refusé : job de rendu trop volumineux ({len(job)} octets, limite {MAX_JOB_BYTES})")
    if not sys.executable:
        raise EngineError("Rendu refusé : interpréteur Python introuvable")
    env = canonical_render_environment(_snapshot_environ())
    env["PYTHONPATH"] = child_pythonpath(env.get("PYTHONPATH", ""))
    # ReportLab also executes ``~/.reportlab_settings``: the child gets an EMPTY home directory.
    with tempfile.TemporaryDirectory(prefix="lafractale-render-home-") as home:
        env["HOME"] = home
        try:
            # -P: never prepend the working directory to sys.path (a planted ``lafractale``
            # module in an untrusted cwd must not be importable by the render process).
            done = subprocess.run([sys.executable, "-P", "-m", WORKER_MODULE, str(out_dir)], input=job,
                                  env=env, capture_output=True, timeout=RENDER_TIMEOUT_SECONDS, check=False)
        except (OSError, subprocess.SubprocessError) as exc:
            raise EngineError(f"Rendu refusé : processus de rendu indisponible ({type(exc).__name__})") from exc
    if done.returncode != 0:
        lines = [line for line in done.stderr.decode("utf-8", "replace").splitlines()
                 if line.startswith("RENDU_REFUSE:")]
        detail = lines[-1][len("RENDU_REFUSE:"):].strip() if lines else f"code de sortie {done.returncode}"
        raise EngineError(f"Rendu refusé : {detail}")
    return out_dir / INTERIOR_NAME, out_dir / ANSWER_NAME
