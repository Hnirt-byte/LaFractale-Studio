"""Render process: ``python -m lafractale.engine._render_worker <out_dir>`` (job on stdin).

Started only by ``render.render_slice`` with a sanitized environment. It refuses to run
under any other environment, so a direct call cannot produce non-canonical bytes.
"""
from __future__ import annotations

import sys
import types

# ReportLab executes ``from reportlab_settings import *`` when it finds such a module on
# sys.path: shadow it with an empty module BEFORE anything imports ReportLab.
sys.modules["reportlab_settings"] = types.ModuleType("reportlab_settings")

import os  # noqa: E402
from pathlib import Path  # noqa: E402

from lafractale.engine.render import (MAX_JOB_BYTES, activity_from_dict,  # noqa: E402
                                      environment_is_canonical, write_pdfs_here)
from lafractale.security.strict_json import loads_strict  # noqa: E402


def main(argv: list[str]) -> int:
    try:
        if len(argv) != 1:
            raise ValueError("un seul argument attendu : le répertoire de sortie")
        if not environment_is_canonical(os.environ):
            raise ValueError("environnement de rendu non canonique (SOURCE_DATE_EPOCH / RL_*)")
        if os.path.lexists(os.path.expanduser(os.path.join("~", ".reportlab_settings"))):
            raise ValueError("réglages utilisateur ReportLab présents (~/.reportlab_settings)")
        raw = sys.stdin.buffer.read(MAX_JOB_BYTES + 1)
        if len(raw) > MAX_JOB_BYTES:
            raise ValueError("job de rendu trop volumineux")
        job = loads_strict(raw)
        if not isinstance(job, dict) or set(job) != {"book", "activities"}:
            raise ValueError("job de rendu mal formé")
        activities = [activity_from_dict(item) for item in job["activities"]]
        write_pdfs_here(job["book"], activities, Path(argv[0]))
    except Exception as exc:  # any refusal is reported on one parsable line
        print(f"RENDU_REFUSE: {type(exc).__name__}: {exc}"[:600].replace("\n", " "), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
