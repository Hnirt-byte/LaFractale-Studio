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

Dependencies installed with ``pip install --user`` stay usable WITHOUT giving the child the
caller's HOME: the child runs with ``-s`` (no user-site processing: no ``.pth``, no
``usercustomize``) and receives the parent's user site-packages directory, only when the
parent itself imports from it, as a plain ``PYTHONPATH`` entry.

The fonts used by a render are traced: the child reports the file name and SHA-256 of the
two TrueType files that ``write_pdf`` really registered (see ``traced_fonts_here``).
"""
from __future__ import annotations

import dataclasses
import os
import re
import site
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Mapping, Sequence

from lafractale.activities.models import Activity
from lafractale.engine import EngineError
from lafractale.engine.contracts import SpecSet, canonical_json_bytes, read_bounded, sha256_hex

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
MAX_FONT_BYTES = 10_000_000
FONT_ROLES = ("regular", "bold")
FONTS_MARKER = "RENDU_POLICES:"
_FONT_FILE = re.compile(r"[^\x00-\x1f\x7f/\\]{1,100}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
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


def user_site_entries() -> list[str]:
    """The user site-packages directory the PARENT really imports from (absolute form), else nothing.

    ``site`` stores an absolute path in ``sys.path`` while ``getusersitepackages()`` may return the raw
    ``PYTHONUSERBASE`` (relative, ``//``, trailing ``/``): both sides are compared in absolute form."""
    if not site.ENABLE_USER_SITE:
        return []
    try:
        path = site.getusersitepackages()
    except Exception:  # pragma: no cover - exotic site configurations
        return []
    if not isinstance(path, str) or not path:
        return []
    absolute = os.path.abspath(path)
    imported = {os.path.abspath(entry) for entry in sys.path if isinstance(entry, str) and entry}
    if os.pathsep in absolute or not os.path.isdir(absolute) or absolute not in imported:
        return []
    return [absolute]


def child_pythonpath(inherited: str) -> str:
    """Absolute PYTHONPATH for the render process.

    The child must run the SAME ``lafractale`` code and see the SAME dependencies as this
    process whatever the working directory: the package root comes first, then the inherited
    entries made absolute here, then the parent's user site (if it uses one) -- the order a
    normal interpreter gives them (PYTHONPATH before the user site).
    """
    import lafractale
    root = str(Path(lafractale.__file__).resolve().parents[1])
    entries = [os.path.abspath(entry) for entry in inherited.split(os.pathsep) if entry]
    ordered: list[str] = []
    for entry in (root, *entries, *user_site_entries()):
        if entry not in ordered:
            ordered.append(entry)
    return os.pathsep.join(ordered)


def python_command() -> list[str]:
    """Interpreter and flags of the render process.

    ``-P``: never prepend the working directory to sys.path (a planted ``lafractale`` module in
    an untrusted cwd must not be importable). ``-s``: no user-site processing (no ``.pth`` file,
    no ``usercustomize``); the parent's user site is passed explicitly through PYTHONPATH.
    """
    return [sys.executable, "-P", "-s"]


def worker_environment(home: str) -> dict[str, str]:
    """Complete environment of the render process: sanitized copy, absolute search path, empty HOME."""
    env = canonical_render_environment(_snapshot_environ())
    env["PYTHONPATH"] = child_pythonpath(env.get("PYTHONPATH", ""))
    env["HOME"] = home
    return env


def check_fonts(raw: object) -> list[str]:
    """Problems of a font trace ``{"regular": {"file", "sha256"}, "bold": {...}}`` (empty = valid)."""
    if not isinstance(raw, dict) or set(raw) != set(FONT_ROLES):
        return ["polices : enregistrement 'regular'/'bold' attendu"]
    errors = []
    for role in FONT_ROLES:
        record = raw[role]
        if not (isinstance(record, dict) and set(record) == {"file", "sha256"}
                and isinstance(record["file"], str) and _FONT_FILE.fullmatch(record["file"])
                and isinstance(record["sha256"], str) and _SHA256.fullmatch(record["sha256"])):
            errors.append(f"polices : enregistrement invalide pour {role} (nom de fichier simple et SHA-256 attendus)")
    return errors


def fonts_differ(recorded: dict, current: dict) -> bool:
    """True when the font BYTES differ; the file name is informational (a copy under another name is the same font)."""
    return any(recorded[role]["sha256"] != current[role]["sha256"] for role in FONT_ROLES)


def describe_font_difference(recorded: dict, current: dict) -> str:
    parts = []
    for role in FONT_ROLES:
        if recorded[role]["sha256"] != current[role]["sha256"]:
            parts.append(f"{role} : {recorded[role]['file']} sha256 {recorded[role]['sha256'][:12]}… (paquet) "
                         f"≠ {current[role]['file']} sha256 {current[role]['sha256'][:12]}… (rendu actuel)")
    return "polices du rendu différentes de celles du paquet — " + " ; ".join(parts)


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


def traced_fonts_here() -> dict[str, dict[str, str]]:
    """File name and SHA-256 of the TrueType files that ``write_pdf`` registered (this process).

    Only the base name is recorded: absolute paths never reach the outputs.
    """
    from reportlab.pdfbase import pdfmetrics
    from lafractale.layout.pdf import fonts
    traced = {}
    for role, name in zip(FONT_ROLES, fonts()):
        path = Path(pdfmetrics.getFont(name).face.filename)
        # ReportLab follows symbolic links (Nix-style font trees): hash the file it really read.
        real = Path(os.path.realpath(path))
        digest = sha256_hex(read_bounded(real, MAX_FONT_BYTES, label=f"police {role}", error=EngineError))
        traced[role] = {"file": path.name, "sha256": digest}
    return traced


def write_pdfs_here(book: dict, activities: Sequence[Activity], out_dir: Path) -> dict[str, dict[str, str]]:
    """Render both PDFs with the historical writer IN THIS PROCESS and return the traced fonts.

    Called by the render process only; calling it elsewhere yields bytes that depend on
    the caller's environment (see module docstring). The fonts are hashed before AND after
    the render: a font file that changed meanwhile is refused.
    """
    from lafractale.layout.pdf import write_pdf  # heavy import kept out of the parent path
    before = traced_fonts_here()
    write_pdf(out_dir / INTERIOR_NAME, list(activities), book, answer_key=False)
    write_pdf(out_dir / ANSWER_NAME, list(activities), book, answer_key=True)
    if traced_fonts_here() != before:
        raise EngineError("fichier de police modifié pendant le rendu")
    return before


def render_slice_with_fonts(spec_set: SpecSet, activities: tuple[Activity, ...],
                            out_dir: Path) -> tuple[Path, Path, dict[str, dict[str, str]]]:
    """Render the fiches and the corrigés into ``out_dir`` (new files only), isolated, and
    return the fonts the render process really used."""
    out_dir = Path(os.path.abspath(out_dir))
    job = canonical_json_bytes({"book": spec_set.book_dict(),
                                "activities": [activity.as_dict() for activity in activities]})
    if len(job) > MAX_JOB_BYTES:
        raise EngineError(f"Rendu refusé : job de rendu trop volumineux ({len(job)} octets, limite {MAX_JOB_BYTES})")
    if not sys.executable:
        raise EngineError("Rendu refusé : interpréteur Python introuvable")
    # ReportLab also executes ``~/.reportlab_settings``: the child gets an EMPTY home directory.
    with tempfile.TemporaryDirectory(prefix="lafractale-render-home-") as home:
        try:
            done = subprocess.run([*python_command(), "-m", WORKER_MODULE, str(out_dir)], input=job,
                                  env=worker_environment(home), capture_output=True,
                                  timeout=RENDER_TIMEOUT_SECONDS, check=False)
        except (OSError, subprocess.SubprocessError) as exc:
            raise EngineError(f"Rendu refusé : processus de rendu indisponible ({type(exc).__name__})") from exc
    if done.returncode != 0:
        lines = [line for line in done.stderr.decode("utf-8", "replace").splitlines()
                 if line.startswith("RENDU_REFUSE:")]
        detail = lines[-1][len("RENDU_REFUSE:"):].strip() if lines else f"code de sortie {done.returncode}"
        raise EngineError(f"Rendu refusé : {detail}")
    reported = [line for line in done.stdout[-20_000:].decode("utf-8", "replace").splitlines()
                if line.startswith(FONTS_MARKER)]
    try:
        from lafractale.security.strict_json import loads_strict
        fonts = loads_strict(reported[-1][len(FONTS_MARKER):].strip()) if reported else None
    except ValueError:
        fonts = None
    problems = check_fonts(fonts)
    if problems:
        raise EngineError("Rendu refusé : " + "; ".join(problems))
    return out_dir / INTERIOR_NAME, out_dir / ANSWER_NAME, fonts


def render_slice(spec_set: SpecSet, activities: tuple[Activity, ...], out_dir: Path) -> tuple[Path, Path]:
    """Same as ``render_slice_with_fonts`` for callers that do not need the font trace."""
    interior, answer, _ = render_slice_with_fonts(spec_set, activities, out_dir)
    return interior, answer
