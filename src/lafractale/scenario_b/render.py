"""Markdown rendering of the report. Pure functions of the report dict (deterministic)."""
from __future__ import annotations

from typing import Any

_KIND = {"front_matter": "ouverture", "activity": "activité", "free_creative": "création libre", "answers": "corrigés",
         "glossary": "lexique", "closing": "diplôme/clôture", "absent": "absente"}
_VALID = {"FR": "FR", "EN": "EN", "BILINGUAL_EQUIVALENCE": "équiv.", "MEDIATION_4_5": "4-5 ans", "HUMAN_REVIEW": "arbitre",
          "SOLUTION_REVIEW": "corrigé"}
_TAG = {"DEV": "DEV", "EDITORIAL_CONTENT": "ÉDIT", "HUMAN_VALIDATION": "VALID", "DOC_CONSISTENCY": "DOC"}


def _cell(text: Any) -> str:
    return str(text if text is not None else "—").replace("|", "\\|").replace("\n", " ")


def _sources_cell(page: dict[str, Any]) -> str:
    parts = []
    instr = page["sources"]["instruction"]
    if instr["status"] == "PRESENT":
        parts.append("consigne FR/EN ✓")
    elif instr["status"] == "ABSENT":
        parts.append("consigne FR/EN ✗")
    sol = page["sources"]["solution"]
    if sol["required"]:
        parts.append(f"solution {sol['status']} (p.{sol['answer_page']})")
    elif sol["status"] == "NOT_REQUIRED" and page["content_kind"] == "free_creative":
        parts.append("sans corrigé")
    if page["sources"]["illustration"]["scene_art"] != "NOT_APPLICABLE":
        parts.append("illustr. non vérifiable")
    parts.append(f"état {page['editorial']['state']}")
    return " · ".join(parts)


def _actions_cell(page: dict[str, Any]) -> str:
    return " ; ".join(f"{_TAG[a['category']]}: {a.get('short', a['text'])}" for a in page["actions"]) or "—"


def render_report(report: dict[str, Any]) -> str:
    s = report["summary"]
    out: list[str] = []
    out.append("# B3-B.2 — Lecteur du scénario B : rapport de capacités et de blocages\n")
    out.append(f"> Analyse en lecture seule, `{report['kind']}`. Aucun PDF, aucun asset, aucune approbation. "
               f"Schéma `{report['schema']}`, lecteur `{report['reader_version']}`.\n")
    out.append("```text")
    out.extend(f"{k:<22}= {v}" for k, v in report["gates"].items())
    out.append(f"{'ready_for_kdp':<22}= {str(report['ready_for_kdp']).lower()}")
    out.append("```\n")
    out.append("## Autorité et provenance\n")
    a = report["authority"]
    out.append(f"- Pagination : `{a['pagination']}` (fait autorité).")
    out.append(f"- Consignes actives : `{a['instructions']}` ; grille B3-A.4 : `{a['review_grid']}` ; corrigés : `{a['corrections']}`.")
    out.append("- Exclus du plan actif : " + (", ".join(f"`{x}`" for x in a["excluded_from_active_plan"]) or "—") + ".\n")
    out.append("| Source | Rôle | Octets | SHA-256 |")
    out.append("|---|---|---:|---|")
    for src in report["provenance"]["sources"]:
        out.append(f"| `{src['path']}` | {src['role']} | {src['bytes']} | `{src['sha256']}` |")
    out.append(f"\nEmpreinte agrégée : `{report['provenance']['sources_aggregate_sha256']}`\n")
    out.append("## Capacités réelles du moteur\n")
    e = report["engine_capabilities"]
    out.append(f"- Générateurs : {', '.join(e['generators'])}. Contrat de production : {e['production_contract']}.")
    out.append(f"- `maze` : grille {e['maze']['size_fixed']}×{e['maze']['size_fixed']} fixe, aucun paramètre de taille.")
    out.append("- `connect_dots` : " + ", ".join(f"{k} = {v} points" for k, v in e["connect_dots"]["shapes"].items())
               + f" ; {e['connect_dots']['editorial_override']}.")
    out.append(f"- `match` : {e['match']['pairs_fixed']} paires, relation « {e['match']['relation']} » ; familles du registre "
               f"{e['match']['registry_families']}, du générateur {e['match']['generator_families']}.")
    out.append(f"- Profil éditorial `{e['editorial_profile']['id']}` : pages {e['editorial_profile']['pages']}.\n")
    out.append("## Contrôles de structure\n")
    out.append("| Contrôle | Attendu | Observé | Résultat |")
    out.append("|---|---|---|---|")
    for c in report["analysis"]["checks"]:
        out.append(f"| {_cell(c['label'])} | {_cell(c['expected'])} | {_cell(c['observed'])} | {c['status']} |")
    out.append("")
    out.append("## Constats et contradictions entre sources\n")
    if report["findings"]:
        for fd in report["findings"]:
            pages = f" (pages {', '.join(str(p) for p in fd['pages'])})" if fd["pages"] else ""
            out.append(f"- **{fd['severity']}** `{fd['code']}`{pages} : {fd['message']}")
    else:
        out.append("Aucun.")
    out.append("")
    out.append("## Synthèse chiffrée\n")
    ta, tp = s["technical_status_activity_pages"], s["technical_status_all_pages"]
    out.append(f"- Compatibilité technique, 46 activités : SUPPORTED {ta['SUPPORTED']} · PARTIAL {ta['PARTIAL']} · UNSUPPORTED {ta['UNSUPPORTED']} · UNKNOWN {ta['UNKNOWN']}.")
    out.append(f"- Compatibilité technique, 56 pages : SUPPORTED {tp['SUPPORTED']} · PARTIAL {tp['PARTIAL']} · UNSUPPORTED {tp['UNSUPPORTED']} · UNKNOWN {tp['UNKNOWN']} (les pages hors activité sont UNSUPPORTED : aucune composition spéciale).")
    out.append(f"- État éditorial des pages : {', '.join(f'{k} {v}' for k, v in s['editorial_state'].items())}.")
    out.append(f"- Corrigés requis : {s['solutions_required']} — {', '.join(f'{k} {v}' for k, v in s['solution_status'].items())}.")
    out.append(f"- Pages à revue humaine de données : {', '.join(f'p.{p}' for p in s['human_review_pages'])}.")
    out.append(f"- Validations humaines enregistrées : {s['human_validations_recorded']} / {s['grid_units']} unités.\n")
    out.append("## Les 56 pages\n")
    out.append("| Page | Titre | Type de contenu | Mécanique | Compat. technique | État des sources éditoriales | Validations manquantes | Actions nécessaires |")
    out.append("|---:|---|---|---|---|---|---|---|")
    for p in report["pages"]:
        missing = ", ".join(_VALID.get(m, m) for m in p["editorial"]["missing_validations"]) or "—"
        out.append(f"| {p['page']:02d} | {_cell(p['title'])} | {_KIND[p['content_kind']]} | {_cell(p['mechanic'] or p['plan_type'])} | "
                   f"{p['technical']['status']} | {_cell(_sources_cell(p))} | {_cell(missing)} | {_cell(_actions_cell(p))} |")
    out.append("")
    out.append("## Blocages et dépendances par page\n")
    for p in report["pages"]:
        if not p["blockers"] and not p["dependencies"]:
            continue
        out.append(f"### p.{p['page']:02d} — {p['title'] or 'absente'}\n")
        for b in p["blockers"]:
            out.append(f"- Blocage `{b['code']}` ({b['category']}) : {b['detail']}")
        for d in p["dependencies"]:
            out.append(f"- Dépend de : {d}")
        out.append("")
    out.append("## Diagnostic technique détaillé (pages d'activité)\n")
    for p in report["pages"]:
        if p["content_kind"] not in ("activity", "free_creative"):
            continue
        t = p["technical"]
        out.append(f"- **p.{p['page']:02d} {p['mechanic']}** — {t['status']} : {' '.join(t['reasons'])}"
                   + (f" Manque : {' ; '.join(t['missing_capabilities'])}." if t["missing_capabilities"] else "")
                   + (f" Questions : {' '.join(t['open_questions'])}" if t["open_questions"] else ""))
    return "\n".join(out) + "\n"


def render_synthesis(report: dict[str, Any]) -> str:
    syn = report["synthesis"]
    out: list[str] = ["# B3-B.2 — Synthèse des développements restants\n",
                      "> Dérivée du rapport JSON (même source de vérité). Statuts permanents inchangés : "
                      + ", ".join(f"{k}={v}" for k, v in report["gates"].items()) + ", ready_for_kdp=false.\n"]
    out.append("## 1. Développement technique nécessaire (par composant)\n")
    for item in syn["technical_development"]:
        out.append(f"### {item['component']} — {item['label']}\n")
        if item["pages"]:
            out.append("Pages concernées : " + ", ".join(f"p.{p:02d}" for p in item["pages"]) + ".")
        out.append("Dépend de : " + (", ".join(item["depends_on"]) or "—") + ". Réutilise : " + "; ".join(item["reuses"]) + ".")
        for mech, info in item["mechanics"].items():
            out.append(f"- `{mech}` ({'/'.join(info['status'])}) pages " + ", ".join(f"p.{p:02d}" for p in info["pages"])
                       + " — " + " ; ".join(info["missing_capabilities"]))
        for w in item["work"]:
            out.append(f"- {w}")
        out.append("")
    out.append("## 2. Contenu éditorial à compléter\n")
    for code, info in syn["editorial_content_to_complete"].items():
        out.append(f"- `{code}` : {info['count']} page(s) — " + ", ".join(f"p.{p:02d}" for p in info["pages"]))
    out.append("\n## 3. Validation humaine requise\n")
    v = syn["human_validation_required"]
    out.append(f"- {v['units_not_validated']} unités sur {v['units_not_validated'] + v['units_validated']} sans validation humaine ; "
               f"aucune proposition générée n'est considérée comme approuvée.")
    out.append("- Pages à revue de données (HUMAN_REVIEW) : " + ", ".join(f"p.{p:02d}" for p in v["human_review_pages"]) + ".")
    out.append("- Rôles : " + " ; ".join(v["roles_required"]) + ".")
    out.append("\n## 4. Problèmes de cohérence documentaire\n")
    for fd in syn["documentary_inconsistencies"]:
        out.append(f"- **{fd['severity']}** `{fd['code']}` : {fd['message']}")
    if not syn["documentary_inconsistencies"]:
        out.append("- Aucun.")
    out.append("\n## 5. Ordre d'implémentation proposé (dépendances réelles)\n")
    out.append("| Rang | Composant | Pages | Dépend de | Justification |")
    out.append("|---:|---|---:|---|---|")
    for step in syn["implementation_order"]:
        out.append(f"| {step['rank']} | {step['component']} — {_cell(step['label'])} | {step['pages_covered']} | "
                   f"{', '.join(step['depends_on']) or '—'} | {_cell(step['rationale'])} |")
    return "\n".join(out) + "\n"
