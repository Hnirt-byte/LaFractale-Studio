"""Documented, testable shape of the report (no third-party schema library)."""
from __future__ import annotations

from typing import Any

from lafractale.scenario_b import GATES, REPORT_KIND, REPORT_SCHEMA, TECH_STATUSES

SEVERITIES = ("CONTRADICTION", "INFO", "STRUCTURE")
BLOCKER_CATEGORIES = ("DOC_CONSISTENCY", "EDITORIAL_CONTENT", "HUMAN_VALIDATION")
ACTION_CATEGORIES = ("DEV", "DOC_CONSISTENCY", "EDITORIAL_CONTENT", "HUMAN_VALIDATION")
CONTENT_KINDS = ("absent", "activity", "answers", "closing", "free_creative", "front_matter", "glossary")
TOP_KEYS = ("analysis", "authority", "engine_capabilities", "findings", "gates", "illustration_registry", "kind",
            "pages", "provenance", "reader_version", "ready_for_kdp", "schema", "summary", "synthesis")
PAGE_KEYS = ("actions", "blockers", "content_kind", "dependencies", "editorial", "mechanic", "page", "plan",
             "plan_present", "plan_type", "sources", "technical", "title")
TECH_KEYS = ("family", "missing_capabilities", "open_questions", "reasons", "status")


def _keys(obj: Any, expected: tuple[str, ...], where: str, errors: list[str]) -> bool:
    if not isinstance(obj, dict):
        errors.append(f"{where} : objet attendu")
        return False
    if sorted(obj) != sorted(expected):
        errors.append(f"{where} : clés {sorted(obj)} ≠ {sorted(expected)}")
        return False
    return True


def validate_report(report: Any) -> list[str]:
    """Return the list of violations of the report schema (empty = valid)."""
    errors: list[str] = []
    if not _keys(report, TOP_KEYS, "rapport", errors):
        return errors
    if report["schema"] != REPORT_SCHEMA:
        errors.append(f"schema : {REPORT_SCHEMA!r} attendu")
    if report["kind"] != REPORT_KIND:
        errors.append(f"kind : {REPORT_KIND!r} attendu")
    if report["gates"] != dict(GATES):
        errors.append("gates : doivent être les constantes du lecteur")
    if report["ready_for_kdp"] is not False:
        errors.append("ready_for_kdp : doit valoir false")
    prov = report["provenance"]
    if not isinstance(prov, dict) or not isinstance(prov.get("sources"), list) or not prov["sources"]:
        errors.append("provenance.sources : liste non vide attendue")
    else:
        for index, entry in enumerate(prov["sources"]):
            digest = entry.get("sha256") if isinstance(entry, dict) else None
            if not (isinstance(digest, str) and len(digest) == 64 and all(c in "0123456789abcdef" for c in digest)):
                errors.append(f"provenance.sources[{index}].sha256 : empreinte SHA-256 hexadécimale attendue")
    pages = report["pages"]
    if not isinstance(pages, list) or [p.get("page") if isinstance(p, dict) else None for p in pages] != list(range(1, 57)):
        errors.append("pages : 56 entrées numérotées 1..56 attendues")
        return errors
    for page in pages:
        where = f"pages[{page['page']}]"
        if not _keys(page, PAGE_KEYS, where, errors):
            continue
        if page["content_kind"] not in CONTENT_KINDS:
            errors.append(f"{where}.content_kind invalide")
        tech = page["technical"]
        if _keys(tech, TECH_KEYS, f"{where}.technical", errors) and tech["status"] not in TECH_STATUSES:
            errors.append(f"{where}.technical.status invalide : {tech['status']!r}")
        for blocker in page["blockers"]:
            if not isinstance(blocker, dict) or blocker.get("category") not in BLOCKER_CATEGORIES or not blocker.get("code"):
                errors.append(f"{where}.blockers : entrée invalide")
        for action in page["actions"]:
            if not isinstance(action, dict) or action.get("category") not in ACTION_CATEGORIES or not action.get("text"):
                errors.append(f"{where}.actions : entrée invalide")
        if page["editorial"].get("state") == "VALIDATED" and not page["sources"]["units"]:
            errors.append(f"{where} : VALIDATED sans unité source")
    for finding in report["findings"]:
        if not isinstance(finding, dict) or finding.get("severity") not in SEVERITIES:
            errors.append("findings : sévérité invalide")
    return errors
