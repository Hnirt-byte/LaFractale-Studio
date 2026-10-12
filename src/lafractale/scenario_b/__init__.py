"""B3-B.2 — read-only reader of the editorial scenario B (Halloween workbook).

The reader inspects the active B3-A.3 / B3-A.4 editorial sources and the
capabilities of the existing engine, then emits a deterministic diagnostic
report (JSON + Markdown). It is isolated from the production engine: it never
writes to a source, never renders a PDF, never touches an approved asset and
never calls an LLM or an external API.

The gate values below are constants of the code, never read from a source file.
Nothing here validates, approves or unblocks anything.
"""
from __future__ import annotations

from types import MappingProxyType

READER_VERSION = "b3b2-reader-1.0"
REPORT_SCHEMA = "lafractale-scenario-b-report-v1"
REPORT_KIND = "READ_ONLY_ANALYSIS_NON_PRODUCTION"
READY_FOR_KDP = False
GATES = MappingProxyType({
    "MAJOR-03": "OPEN",
    "MAJOR-04": "OPEN",
    "EDITORIAL": "PENDING",
    "KDP": "FORBIDDEN",
    "PRODUCTION_GENERATION": "FORBIDDEN",
})

TECH_STATUSES = ("SUPPORTED", "PARTIAL", "UNSUPPORTED", "UNKNOWN")


class ReaderError(ValueError):
    """The sources are structurally unreadable: no meaningful analysis is possible."""

    def __init__(self, errors: list[str] | str):
        self.errors = [errors] if isinstance(errors, str) else list(errors)
        super().__init__("; ".join(self.errors))
