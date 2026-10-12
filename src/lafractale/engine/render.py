"""Page composition and PDF rendering, delegated to the existing renderer.

``write_pdf`` (layout/pdf.py) composes every page, validates it before the file
exists, embeds the fonts and creates the file exclusively. This module only
chooses the file names and refuses to write anything that already exists.
"""
from __future__ import annotations

from pathlib import Path

from lafractale.activities.models import Activity
from lafractale.engine import EngineError
from lafractale.engine.contracts import SpecSet
from lafractale.layout.pdf import write_pdf

INTERIOR_NAME = "interior_SYNTHETIC_NON_PRODUCTION.pdf"
ANSWER_NAME = "answer_key_SYNTHETIC_NON_PRODUCTION.pdf"
ACTIVITIES_NAME = "activities.json"
REPORT_NAME = "quality_report.json"
MANIFEST_NAME = "manifest.json"
SOURCE_NAME = "sources/spec.json"
SOURCE_DIR = "sources"
#: Closed inventory of a package, as relative POSIX paths.
PACKAGE_FILES = (INTERIOR_NAME, ANSWER_NAME, ACTIVITIES_NAME, REPORT_NAME, MANIFEST_NAME, SOURCE_NAME)


def render_slice(spec_set: SpecSet, activities: tuple[Activity, ...], out_dir: Path) -> tuple[Path, Path]:
    """Render the fiches and the corrigés into ``out_dir`` (new files only)."""
    out_dir = Path(out_dir)
    interior, answers = out_dir / INTERIOR_NAME, out_dir / ANSWER_NAME
    book = spec_set.book_dict()
    try:
        write_pdf(interior, list(activities), book, answer_key=False)
        write_pdf(answers, list(activities), book, answer_key=True)
    except ValueError as exc:  # layout refusal (text overflow, geometry) or unsafe path
        raise EngineError(f"Rendu refusé : {exc}") from exc
    return interior, answers
