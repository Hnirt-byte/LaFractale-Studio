#!/usr/bin/env python3
"""B2-C3 read-only, opt-in pre-press + editorial preflight for the C2 V2 demo.

DIAGNOSTIC ONLY.  This tool never modifies the PDFs, the activities, the fonts,
the text, the Pip assets, `book.yaml`, `page_plan.csv`, the manifest or any C2
output.  It reads two PDFs (`interior.pdf`, `answer_key.pdf`) from an *existing*
C2 build directory, re-runs the historical C2 QA first (a QA failure is a
BLOCKER and halts analysis), then measures objective PDF/pre-press properties
and writes a closed, deterministic report OUTSIDE the build directory.

Trust model (contract §2–§3): the source of authority is the pinned Book, the
canonical C1 route and the C2 placement plan (all recomputed from the verified
Book plus the external approval PIN), never the manifest.  The PDFs are read
from a stable byte snapshot opened without following symlinks and are never
re-opened by path after validation.

KDP facts (recross-checked at execution time, 2026-10-10) and their sources:
  - trim 8.5 x 11 in = 612 x 792 pt; with bleed 621 x 810 pt (+0.125/0.25 in)
    https://kdp.amazon.com/fr_FR/help/topic/GVBQ3CMEQW3W2VL6
  - inside/gutter margin (24-150 pages) >= 0.375 in = 27 pt ; outside margin
    >= 0.25 in (18 pt) without bleed, >= 0.375 in (27 pt) with bleed ; images
    >= 300 DPI ; fonts embedded ; min font 7 pt
    https://kdp.amazon.com/fr_FR/help/topic/G201857950
  - 8.5 x 11 paperback: 24-590 pages (B&W white paper) -> a 3-page demo is NOT a
    submissible manuscript
    https://kdp.amazon.com/fr_FR/help/topic/G201834180

KDP minimums are pass/fail thresholds, not design targets; a technical finding
is never an editorial approval and never authorizes publication.
"""
from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

import fitz  # noqa: E402  (PyMuPDF)

from lafractale.activities.engine import generate, stable_seed  # noqa: E402
from lafractale.config.schema import load_book  # noqa: E402
from lafractale.illustrations.placement import (  # noqa: E402
    PIP_PLACEMENT_HALLOWEEN_V2,
    build_pip_placement_plan,
    placed_composition,
    resolve_pip_placement_mode,
)
from lafractale.illustrations.routing import (  # noqa: E402
    ROUTING_HALLOWEEN_PIP_DEMO_V1,
    build_illustration_route,
)
from lafractale.layout.composition import Rect, compose_page  # noqa: E402
from lafractale.layout.pdf import _measure, fonts  # noqa: E402
from lafractale.story.plan import demo_specs  # noqa: E402

# --------------------------------------------------------------------------
# KDP referential (constants pinned here, sources above)
# --------------------------------------------------------------------------
TRIM_PT = (612.0, 792.0)             # 8.5 x 11 in, no bleed
BLEED_PT = (621.0, 810.0)            # +0.125 in width, +0.25 in height
MIN_INNER_MARGIN_PT = 27.0           # 0.375 in (24-150 pages)
MIN_OUTER_MARGIN_NO_BLEED_PT = 18.0  # 0.25 in
MIN_OUTER_MARGIN_BLEED_PT = 27.0     # 0.375 in
MIN_DPI = 300.0
MIN_FONT_PT = 7.0                    # below -> BLOCKER (KDP)
CONSIGNE_WARN_PT = 10.0              # consigne <= -> WARNING pedagogique (not KDP)
MIN_LINE_PT = 0.75                   # KDP recommendation
MIN_GREY_FILL = 0.10                 # 10 % ink recommendation for grey backgrounds

KDP_SOURCES = [
    "https://kdp.amazon.com/fr_FR/help/topic/GVBQ3CMEQW3W2VL6",
    "https://kdp.amazon.com/fr_FR/help/topic/G201857950",
    "https://kdp.amazon.com/fr_FR/help/topic/G201834180",
]
KDP_FACTS_VERIFIED_AT = "2026-10-10"

DEMO_SEED = 2026
SOURCE_DATE_EPOCH = "1780000000"

KIND_REQUIREMENT = "KDP_REQUIREMENT"
KIND_RECOMMENDATION = "KDP_RECOMMENDATION"
KIND_ADVISORY = "EDITORIAL_ADVISORY"
KIND_UNKNOWN = "UNKNOWN"

SEV_BLOCKER = "BLOCKER"
SEV_MAJOR = "MAJOR"
SEV_WARN = "WARN"
SEV_INFO = "INFO"
SEV_NOT_EVALUABLE = "NOT_EVALUABLE"


class PreflightError(RuntimeError):
    pass


# --------------------------------------------------------------------------
# Anchored, symlink-free read of a single file (mirrors the oracle helpers).
# --------------------------------------------------------------------------
def _sha256_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def _anchored_file_bytes(path: Path) -> bytes:
    raw = os.fspath(path)
    if not raw or "\x00" in raw or ".." in Path(raw).parts:
        raise PreflightError(f"Chemin de sortie invalide : {raw!r}")
    absolute = Path(os.path.abspath(raw))
    parts = absolute.parts[1:]
    dir_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    fd = os.open("/", dir_flags)
    try:
        for component in parts[:-1]:
            next_fd = os.open(component, dir_flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        leaf = parts[-1]
        file_flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        lfd = os.open(leaf, file_flags, dir_fd=fd)
        try:
            if not stat.S_ISREG(os.fstat(lfd).st_mode):
                raise PreflightError(f"Fichier non régulier : {leaf}")
            with os.fdopen(lfd, "rb") as stream:
                lfd = -1
                return stream.read()
        finally:
            if lfd >= 0:
                os.close(lfd)
    finally:
        os.close(fd)


# --------------------------------------------------------------------------
# Finding model
# --------------------------------------------------------------------------
def _finding(rule_id: str, kind: str, severity: str, *, source: str, page: str,
             observed, expected, evidence: str = "", bbox_pt=None) -> dict:
    finding = {
        "rule_id": rule_id,
        "kind": kind,
        "severity": severity,
        "source": source,
        "page": page,
        "observed": observed,
        "expected": expected,
        "evidence": evidence,
    }
    if bbox_pt is not None:
        finding["bbox_pt"] = [round(float(v), 2) for v in bbox_pt]
    return finding


def _grey_from_rgb_int(color: int) -> float:
    r = (color >> 16) & 0xFF
    g = (color >> 8) & 0xFF
    b = color & 0xFF
    return round((r + g + b) / 3 / 255.0, 4)


def _contrast_ratio_white(grey: float) -> float:
    # WCAG relative luminance of grey on white.
    lum = grey if grey <= 0.03928 else ((grey + 0.055) / 1.055) ** 2.4
    return round(1.05 / (lum + 0.05), 2)


def _to_pdf_rect(rect: Rect, page_h: float) -> tuple[float, float, float, float]:
    return (rect.x, page_h - rect.top, rect.right, page_h - rect.y)


def _center_in(bbox, region_pdf) -> bool:
    x0, y0, x1, y1 = bbox
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rx0, ry0, rx1, ry1 = region_pdf
    return rx0 <= cx <= rx1 and ry0 <= cy <= ry1


# --------------------------------------------------------------------------
# Layout recomputation from the verified Book (authority, not the manifest).
# --------------------------------------------------------------------------
def _recompute_layouts(book):
    specs = demo_specs(book)
    regular, bold = fonts()
    activities = [generate(spec, stable_seed(book.book_id, spec.id, DEMO_SEED)) for spec in specs]
    interiors = []
    answers = []
    for index, act in enumerate(activities, 1):
        base = compose_page(act, book.data, index=index, count=len(activities),
                            answer_key=False, regular=regular, bold=bold, text_width=_measure)
        base_ak = compose_page(act, book.data, index=index, count=len(activities),
                               answer_key=True, regular=regular, bold=bold, text_width=_measure)
        interiors.append(placed_composition(base, "intro_right", text_width=_measure))
        answers.append(placed_composition(base_ak, "intro_right", text_width=_measure))
    return activities, interiors, answers


# --------------------------------------------------------------------------
# Per-page analysis
# --------------------------------------------------------------------------
def _analyze_page(page, layout, *, source: str, page_label: str, findings: list):
    page_h = page.rect.height
    page_w = page.rect.width
    # --- structure ---
    rotation_ok = abs(page.rotation) < 1e-6
    if not rotation_ok:
        findings.append(_finding(
            "structure.rotation", KIND_REQUIREMENT, SEV_BLOCKER, source=source, page=page_label,
            observed=page.rotation, expected=0,
            evidence="page.rotation != 0", bbox_pt=None))
    size_ok = abs(page_w - TRIM_PT[0]) < 0.5 and abs(page_h - TRIM_PT[1]) < 0.5
    if not size_ok:
        findings.append(_finding(
            "structure.page_size", KIND_REQUIREMENT, SEV_BLOCKER, source=source, page=page_label,
            observed=[page_w, page_h], expected=list(TRIM_PT),
            evidence=f"page.rect={page.rect}"))

    regions = layout.regions()
    header_pdf = _to_pdf_rect(layout.header, page_h)
    prompt_fr_pdf = _to_pdf_rect(layout.prompt_fr.region, page_h)
    prompt_en_pdf = _to_pdf_rect(layout.prompt_en.region, page_h)
    board_pdf = _to_pdf_rect(layout.board, page_h)
    footer_pdf = _to_pdf_rect(layout.footer, page_h)
    scene_pdf = _to_pdf_rect(layout.scene.region, page_h)

    # --- fonts + text ---
    text_dict = page.get_text("dict")
    spans = []
    for blk in text_dict.get("blocks", []):
        if blk.get("type") != 0:
            continue
        for line in blk.get("lines", []):
            for span in line.get("spans", []):
                spans.append(span)
    if not spans:
        findings.append(_finding(
            "text.extractable", KIND_REQUIREMENT, SEV_BLOCKER, source=source, page=page_label,
            observed="aucun span texte", expected="texte extractible",
            evidence="page.get_text('dict') vide"))

    font_list = page.get_fonts()
    embedded = [f for f in font_list if f[1] == "ttf"]
    non_embedded = [f for f in font_list if f[1] != "ttf"]
    used_fonts = {s["font"] for s in spans}
    if not embedded:
        findings.append(_finding(
            "font.embedded", KIND_REQUIREMENT, SEV_BLOCKER, source=source, page=page_label,
            observed=[f[3] for f in font_list], expected="au moins une police intégrée (ttf)",
            evidence="page.get_fonts()"))
    for f in non_embedded:
        used = f[3] in used_fonts
        findings.append(_finding(
            "font.non_embedded_used" if used else "font.non_embedded_referenced",
            KIND_REQUIREMENT if used else KIND_RECOMMENDATION,
            SEV_BLOCKER if used else SEV_WARN,
            source=source, page=page_label,
            observed={"basefont": f[3], "type": f[2], "used_by_visible_text": used},
            expected="polices intégrées (KDP)",
            evidence=f"xref={f[0]} {f[3]}"))

    min_size = min((s["size"] for s in spans), default=None)
    if min_size is None:
        min_size = 0.0
    findings.append(_finding(
        "font.min_size", KIND_REQUIREMENT, SEV_INFO, source=source, page=page_label,
        observed=round(min_size, 2), expected=f">= {MIN_FONT_PT} pt (KDP), lisibilite 4-5 ans non evaluee",
        evidence="taille minimale des spans"))
    if min_size < MIN_FONT_PT:
        findings.append(_finding(
            "font.min_size_below_kdp", KIND_REQUIREMENT, SEV_BLOCKER, source=source, page=page_label,
            observed=round(min_size, 2), expected=f">= {MIN_FONT_PT} pt",
            evidence=f"span sous {MIN_FONT_PT} pt"))

    # --- native FR/EN instruction text present (recomputed, not manifest) ---
    def _norm(text: str) -> str:
        return " ".join(text.split())
    full_text = _norm(" ".join(s["text"] for s in spans))
    for role, block in (("fr", layout.prompt_fr), ("en", layout.prompt_en)):
        for line in block.lines:
            if _norm(line) and _norm(line) not in full_text:
                findings.append(_finding(
                    "pedagogy.instruction_text_missing", KIND_UNKNOWN, SEV_MAJOR,
                    source=source, page=page_label,
                    observed=f"texte {role} absent", expected=line,
                    evidence="consigne native non retrouvée dans le PDF"))

    # consigne size classification
    for span in spans:
        size = span["size"]
        bbox = span["bbox"]
        grey = _grey_from_rgb_int(span["color"])
        role = "meta"
        if _center_in(bbox, prompt_fr_pdf):
            role = "consigne_fr"
        elif _center_in(bbox, prompt_en_pdf):
            role = "consigne_en"
        elif _center_in(bbox, board_pdf):
            role = "activite"
        elif _center_in(bbox, scene_pdf):
            role = "scene"
        elif _center_in(bbox, header_pdf):
            role = "entete"
        elif _center_in(bbox, footer_pdf):
            role = "pied"
        if role in ("consigne_fr", "consigne_en", "activite") and size <= CONSIGNE_WARN_PT:
            findings.append(_finding(
                "font.consigne_size", KIND_ADVISORY, SEV_WARN, source=source, page=page_label,
                observed={"text": span["text"], "size_pt": round(size, 2), "role": role,
                          "grey": grey},
                expected=f"consigne > {CONSIGNE_WARN_PT} pt (recommandation pedagogique interne)",
                evidence="taille de consigne <= 10 pt -> revue a 100 % a taille reelle",
                bbox_pt=bbox))
        if role in ("consigne_fr", "consigne_en"):
            contrast = _contrast_ratio_white(grey)
            if contrast < 4.5:
                findings.append(_finding(
                    "text.consigne_contrast", KIND_ADVISORY, SEV_WARN, source=source,
                    page=page_label,
                    observed={"text": span["text"], "grey": grey,
                              "contrast_vs_white": contrast},
                    expected="contraste de consigne >= 4.5:1 (WCAG AA, revue humaine)",
                    evidence="contraste de consigne sous 4.5:1", bbox_pt=bbox))

    # --- drawings: line widths and grey fills ---
    content_boxes = []
    stroke_widths = []
    for dr in page.get_drawings():
        rect = dr.get("rect")
        if rect is None:
            continue
        box = (rect.x0, rect.y0, rect.x1, rect.y1)
        content_boxes.append(box)
        width = dr.get("width")
        fill = dr.get("fill")
        color = dr.get("color")
        if width is not None and width > 0:
            stroke_widths.append(round(float(width), 3))
        if width is not None and width > 0 and width < MIN_LINE_PT:
            kind = KIND_REQUIREMENT if _functional_stroke(dr, board_pdf) else KIND_RECOMMENDATION
            sev = SEV_MAJOR if _functional_stroke(dr, board_pdf) else SEV_WARN
            findings.append(_finding(
                "line.thin_stroke", kind, sev, source=source, page=page_label,
                observed={"width_pt": round(width, 3), "stroke": color},
                expected=f">= {MIN_LINE_PT} pt (KDP recommandation)",
                evidence="trait < 0.75 pt", bbox_pt=box))
        if fill is not None:
            r, g, b = fill[:3]
            grey = round((r + g + b) / 3, 4)
            ink = round(1 - grey, 4)
            if 0.0 < ink < MIN_GREY_FILL and grey > 0.5:
                findings.append(_finding(
                    "grey.low_fill", KIND_RECOMMENDATION, SEV_WARN, source=source, page=page_label,
                    observed={"grey": grey, "ink_fraction": ink},
                    expected=f"fond gris >= {MIN_GREY_FILL * 100:.0f} % d'encre (recommandation)",
                    evidence="teinte claire sous 10 % d'encre", bbox_pt=box))

    # --- images: count, DPI, colorspace, alpha ---
    images = page.get_image_info(xrefs=True)
    if len(images) != 1:
        findings.append(_finding(
            "image.count", KIND_REQUIREMENT, SEV_BLOCKER, source=source, page=page_label,
            observed=len(images), expected=1, evidence="page.get_image_info()"))
    for im in images:
        xref = im.get("xref", 0)
        bbox = im.get("bbox", ())
        if not xref:
            continue
        try:
            pix = fitz.Pixmap(page.parent, xref)
            w_pt = bbox[2] - bbox[0]
            h_pt = bbox[3] - bbox[1]
            dpi_x = 72 * pix.width / w_pt if w_pt else 0.0
            dpi_y = 72 * pix.height / h_pt if h_pt else 0.0
            mono = pix.n == 1 and pix.alpha == 0
            findings.append(_finding(
                "image.dpi", KIND_REQUIREMENT,
                SEV_BLOCKER if min(dpi_x, dpi_y) < MIN_DPI else SEV_INFO,
                source=source, page=page_label,
                observed={"dpi_x": round(dpi_x, 1), "dpi_y": round(dpi_y, 1),
                          "pixels": [pix.width, pix.height]},
                expected=f">= {MIN_DPI} DPI sur les deux axes",
                evidence=f"xref={xref} bbox={[round(v, 2) for v in bbox]}", bbox_pt=bbox))
            if not mono:
                findings.append(_finding(
                    "image.colorspace", KIND_REQUIREMENT, SEV_MAJOR, source=source, page=page_label,
                    observed={"n": pix.n, "alpha": pix.alpha, "cs": im.get("cs-name")},
                    expected="niveau de gris 1 canal sans alpha",
                    evidence="image non monochrome", bbox_pt=bbox))
        except Exception as exc:  # noqa: BLE001
            findings.append(_finding(
                "image.unverifiable", KIND_UNKNOWN, SEV_MAJOR, source=source, page=page_label,
                observed=str(exc), expected="image decodable", evidence=f"xref={xref}"))

    # --- content bounds + margins + edge proximity ---
    boxes = list(content_boxes)
    boxes.extend(tuple(s["bbox"]) for s in spans)
    boxes.extend(tuple(im.get("bbox", ())) for im in images)
    if boxes:
        min_x = min(b[0] for b in boxes)
        min_y = min(b[1] for b in boxes)
        max_x = max(b[2] for b in boxes)
        max_y = max(b[3] for b in boxes)
        left_margin = min_x
        right_margin = page_w - max_x
        top_margin = min_y
        bottom_margin = page_h - max_y
        # Conservative: the gutter could be either side in the 3-page demo.
        inner_margin = min(left_margin, right_margin)
        outer_margin = max(left_margin, right_margin)
        findings.append(_finding(
            "margin.measured", KIND_REQUIREMENT, SEV_INFO, source=source, page=page_label,
            observed={"left_pt": round(left_margin, 2), "right_pt": round(right_margin, 2),
                      "top_pt": round(top_margin, 2), "bottom_pt": round(bottom_margin, 2)},
            expected=f"gouttiere >= {MIN_INNER_MARGIN_PT} pt, exterieur >= {MIN_OUTER_MARGIN_NO_BLEED_PT} pt",
            evidence="bornes de contenu (texte + traces + images)"))
        if inner_margin < MIN_INNER_MARGIN_PT:
            findings.append(_finding(
                "margin.inner_below_min", KIND_REQUIREMENT, SEV_MAJOR, source=source, page=page_label,
                observed=round(inner_margin, 2), expected=f">= {MIN_INNER_MARGIN_PT} pt (gouttiere 24-150 p.)",
                evidence="marge interieure minimale des deux cotes"))
        if outer_margin < MIN_OUTER_MARGIN_NO_BLEED_PT:
            findings.append(_finding(
                "margin.outer_below_min", KIND_REQUIREMENT, SEV_MAJOR, source=source, page=page_label,
                observed=round(outer_margin, 2), expected=f">= {MIN_OUTER_MARGIN_NO_BLEED_PT} pt",
                evidence="marge exterieure minimale des deux cotes"))
        # bleed-zone content: anything beyond the trim box but inside MediaBox.
        trim_over = (min_x < -0.5 or min_y < -0.5 or max_x > TRIM_PT[0] + 0.5
                     or max_y > TRIM_PT[1] + 0.5)
        if trim_over:
            findings.append(_finding(
                "bleed.content_outside_trim", KIND_REQUIREMENT, SEV_WARN, source=source,
                page=page_label, observed={"bounds": [round(v, 2) for v in (min_x, min_y, max_x, max_y)]},
                expected="contenu dans le format de coupe 612 x 792 pt (sans fond perdu)",
                evidence="contenu hors du format de coupe"))

    # --- annotations / links / layers / crop marks / placeholders ---
    annots = list(page.annots() or [])
    if annots:
        findings.append(_finding(
            "clean.annotations", KIND_REQUIREMENT, SEV_MAJOR, source=source, page=page_label,
            observed=len(annots), expected=0, evidence="page.annots()"))
    if page.get_links():
        findings.append(_finding(
            "clean.links", KIND_RECOMMENDATION, SEV_WARN, source=source, page=page_label,
            observed=len(page.get_links()), expected=0, evidence="page.get_links()"))

    if stroke_widths:
        findings.append(_finding(
            "line.stroke_widths", KIND_REQUIREMENT, SEV_INFO, source=source, page=page_label,
            observed={"min_pt": min(stroke_widths), "max_pt": max(stroke_widths),
                      "count": len(stroke_widths)},
            expected=f">= {MIN_LINE_PT} pt (KDP recommandation)",
            evidence="largeurs de trait extraites de page.get_drawings()"))


def _functional_stroke(dr, board_pdf) -> bool:
    rect = dr.get("rect")
    if rect is None:
        return False
    box = (rect.x0, rect.y0, rect.x1, rect.y1)
    rx0, ry0, rx1, ry1 = board_pdf
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return rx0 <= cx <= rx1 and ry0 <= cy <= ry1


# --------------------------------------------------------------------------
# Report builders
# --------------------------------------------------------------------------
def _worst_prepress(findings: list) -> str:
    for severity in (SEV_BLOCKER, SEV_MAJOR):
        if any(f["severity"] == severity for f in findings):
            return "FAIL"
    if any(f["severity"] == SEV_WARN for f in findings):
        return "WARN"
    return "PASS"


def _render_board(pdf_path_bytes: bytes, page_index: int) -> bytes:
    doc = fitz.open(stream=pdf_path_bytes, filetype="pdf")
    page = doc[page_index]
    pix = page.get_pixmap(dpi=300, colorspace=fitz.csGRAY, alpha=False)
    return pix.tobytes("png")


def _write_report_file(report_fd: int, name: str, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    fd = os.open(name, flags, 0o600, dir_fd=report_fd)
    try:
        with os.fdopen(fd, "wb") as stream:
            fd = -1
            stream.write(data)
    finally:
        if fd >= 0:
            os.close(fd)


def _git_value(repo: Path, *args: str) -> str | None:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _build_markdown(report: dict) -> str:
    lines = [
        "# LaFractale Studio — B2-C3 — préflight prépresse (diagnostic read-only)",
        "",
        f"- Statut de l'outil (diagnostic technique) : **{report['diagnostic']['status']}**",
        f"- QA C2 historique : **{report['diagnostic']['qa_status']}**",
        f"- État prépresse des pages : **{report['prepress']['status']}**",
        f"- Fond perdu : **{report['prepress']['bleed']['decision']}**",
        f"- Décision éditoriale : **{report['editorial']['status']}**",
        f"- Publication KDP : **{report['kdp']['status']}**",
        "",
        "## Sources KDP vérifiées",
        "",
        f"Date de vérification : {KDP_FACTS_VERIFIED_AT}",
    ]
    for source in KDP_SOURCES:
        lines.append(f"- {source}")
    lines += ["", "## Constats"]
    if not report["findings"]:
        lines.append("Aucun constat.")
    for finding in report["findings"]:
        lines.append(
            f"- `{finding['severity']}` `{finding['kind']}` **{finding['rule_id']}** "
            f"({finding['source']} {finding['page']}) : observé {finding['observed']} "
            f"— attendu {finding['expected']}"
        )
    lines += ["", "## Limitations"]
    for limit in report["limits"]:
        lines.append(f"- {limit}")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Préflight prépresse B2-C3 read-only")
    parser.add_argument("--out", type=Path, required=True, help="Répertoire C2 existant")
    parser.add_argument("--book", type=Path, required=True, help="YAML source de confiance")
    parser.add_argument("--policy", default=PIP_PLACEMENT_HALLOWEEN_V2,
                        help="Politique de placement C2 (V2 uniquement)")
    parser.add_argument("--approvals-sha256", required=True, help="Empreinte externe du registre")
    parser.add_argument("--report-dir", type=Path, required=True,
                        help="Répertoire de rapport HORS de --out")
    args = parser.parse_args(argv)

    out = Path(os.path.abspath(args.out))
    book_path = Path(os.path.abspath(args.book))
    report_dir = Path(os.path.abspath(args.report_dir))
    policy = args.policy
    pin = args.approvals_sha256

    findings: list = []

    # Guard: report-dir must not overlap the audited build directory.
    try:
        if report_dir == out or report_dir.is_relative_to(out) or out.is_relative_to(report_dir):
            raise PreflightError("--report-dir doit être hors de --out et disjoint")
        if policy != PIP_PLACEMENT_HALLOWEEN_V2:
            raise PreflightError(f"Politique de placement non autorisée : {policy!r}")
        if resolve_pip_placement_mode(policy) != PIP_PLACEMENT_HALLOWEEN_V2:
            raise PreflightError("Politique de placement non résolvable")
    except PreflightError as exc:
        print(f"ERREUR : {exc}", file=sys.stderr)
        return 2

    head = _git_value(_REPO, "rev-parse", "HEAD")
    tree = _git_value(_REPO, "rev-parse", "HEAD^{tree}")

    # 1. Load the trusted Book and recompute the C1 route + C2 plan (authority).
    try:
        book = load_book(book_path)
        if book.book_id != "halloween_2026":
            raise PreflightError("Préflight limité au livre Halloween 2026")
        route = build_illustration_route(
            book, policy_id=ROUTING_HALLOWEEN_PIP_DEMO_V1, trusted_approvals_sha256=pin)
        plan = build_pip_placement_plan(
            book, route, policy_id=PIP_PLACEMENT_HALLOWEEN_V2, trusted_approvals_sha256=pin)
        activities, interior_layouts, answer_layouts = _recompute_layouts(book)
    except Exception as exc:  # noqa: BLE001
        print(f"ERREUR : source de confiance invalide : {exc}", file=sys.stderr)
        return 2

    # 2. Historical C2 QA gate (subprocess). A failure is a BLOCKER.
    qa_cmd = [
        sys.executable, "-m", "lafractale", "qa", str(out), "--book", str(book_path),
        "--illustration-routing", ROUTING_HALLOWEEN_PIP_DEMO_V1,
        "--pip-placement", PIP_PLACEMENT_HALLOWEEN_V2,
        "--approvals-sha256", pin,
    ]
    qa_env = os.environ.copy()
    qa_env.pop("PYTHONHOME", None)
    qa_env.pop("PYTHONPATH", None)
    qa_env["PYTHONPATH"] = str(_REPO / "src")
    qa_env["SOURCE_DATE_EPOCH"] = SOURCE_DATE_EPOCH
    qa = subprocess.run(qa_cmd, cwd=_REPO, env=qa_env, capture_output=True, text=True)
    qa_ok = qa.returncode == 0
    if not qa_ok:
        findings.append(_finding(
            "gate.qa_failure", KIND_REQUIREMENT, SEV_BLOCKER, source="gate", page="-",
            observed=f"rc={qa.returncode}", expected="QA C2 historique OK",
            evidence=(qa.stderr or qa.stdout).strip()[:500]))
    else:
        findings.append(_finding(
            "gate.qa_pass", KIND_REQUIREMENT, SEV_INFO, source="gate", page="-",
            observed="rc=0", expected="QA C2 historique OK", evidence=""))

    # 3. Read the two PDFs from stable, symlink-free byte snapshots.
    pdf_bytes = {}
    pdf_hashes = {}
    analysis_done = qa_ok
    try:
        for name in ("interior.pdf", "answer_key.pdf"):
            data = _anchored_file_bytes(out / name)
            pdf_bytes[name] = data
            pdf_hashes[name] = _sha256_bytes(data)
    except PreflightError as exc:
        findings.append(_finding(
            "gate.pdf_read_failure", KIND_REQUIREMENT, SEV_BLOCKER, source="gate", page="-",
            observed=str(exc), expected="PDF lisibles", evidence=""))
        analysis_done = False

    boards: list[str] = []
    if analysis_done:
        page_order = ["p004", "p006", "p020"]
        for name in ("interior.pdf", "answer_key.pdf"):
            doc = fitz.open(stream=pdf_bytes[name], filetype="pdf")
            try:
                if len(doc) != 3:
                    findings.append(_finding(
                        "structure.page_count", KIND_REQUIREMENT, SEV_BLOCKER, source=name,
                        page="-", observed=len(doc), expected=3, evidence="len(pdf)"))
                if doc.needs_pass:
                    findings.append(_finding(
                        "structure.encryption", KIND_REQUIREMENT, SEV_BLOCKER, source=name,
                        page="-", observed="chiffré", expected="non chiffré", evidence="needs_pass"))
                layouts = interior_layouts if name == "interior.pdf" else answer_layouts
                for index, page in enumerate(doc):
                    label = f"p{index + 1} ({page_order[index]})"
                    _analyze_page(page, layouts[index], source=name, page_label=label,
                                  findings=findings)
                    board_bytes = _render_board(pdf_bytes[name], index)
                    board_name = f"board_{name[:-4]}_{index + 1:02d}.png"
                    boards.append(board_name)
                try:
                    if doc.get_toc(simple=True):
                        findings.append(_finding(
                            "clean.bookmarks", KIND_RECOMMENDATION, SEV_WARN, source=name, page="-",
                            observed=len(doc.get_toc(simple=True)), expected=0,
                            evidence="doc.get_toc()"))
                    ocgs = doc.get_ocgs()
                    if ocgs:
                        findings.append(_finding(
                            "clean.layers", KIND_RECOMMENDATION, SEV_WARN, source=name, page="-",
                            observed=len(ocgs), expected=0, evidence="doc.get_ocgs()"))
                except Exception:  # noqa: BLE001
                    pass
                full_text = "\n".join(p.get_text() for p in doc)
                for marker in ("TODO", "PLACEHOLDER", "TBD", "VISUEL À VALIDER", "LOREM"):
                    if marker in full_text:
                        findings.append(_finding(
                            "clean.placeholder", KIND_RECOMMENDATION, SEV_WARN, source=name,
                            page="-", observed=marker, expected="aucun placeholder",
                            evidence="texte extrait"))
            finally:
                doc.close()
    else:
        # No PDF analysis: mark the whole pre-press evaluation NOT_EVALUABLE.
        findings.append(_finding(
            "prepress.not_evaluable", KIND_UNKNOWN, SEV_NOT_EVALUABLE, source="preflight",
            page="-", observed="analyse interrompue (gate)", expected="analyse complète",
            evidence="QA/lecture PDF en échec"))

    # --- objective pedagogy checks (recomputed from Book, not manifest) ---
    expected_types = ("maze", "connect_dots", "match")
    observed_types = tuple(a.type for a in activities)
    findings.append(_finding(
        "pedagogy.activity_match", KIND_ADVISORY, SEV_INFO, source="book", page="-",
        observed=list(observed_types), expected=list(expected_types),
        evidence="demo_specs recomputé"))
    if observed_types != expected_types:
        findings.append(_finding(
            "pedagogy.activity_mismatch", KIND_UNKNOWN, SEV_MAJOR, source="book", page="-",
            observed=list(observed_types), expected=list(expected_types),
            evidence="les 3 activités C2 doivent être maze/connect_dots/match"))

    # --- build the three-tier status model ---
    diagnostic_status = ("PASS_DIAGNOSTIC_TECHNIQUE" if qa_ok and analysis_done
                         else "FAIL_DIAGNOSTIC_TECHNIQUE")
    prepress_status = _worst_prepress(findings) if analysis_done else "NOT_EVALUABLE"

    # --- per-page review dossier + visual index (from recomputed layout + findings) ---
    page_order = ["p004", "p006", "p020"]
    dossiers = []
    if analysis_done:
        def _measured(findings, source, page):
            dpi = margins = strokes = min_font = None
            for f in findings:
                if f.get("source") != source or f.get("page") != page:
                    continue
                rid = f.get("rule_id")
                if rid == "image.dpi":
                    dpi = f["observed"]
                elif rid == "margin.measured":
                    margins = f["observed"]
                elif rid == "line.stroke_widths":
                    strokes = f["observed"]
                elif rid == "font.min_size":
                    min_font = f["observed"]
            return dpi, margins, strokes, min_font

        for name in ("interior.pdf", "answer_key.pdf"):
            layouts = interior_layouts if name == "interior.pdf" else answer_layouts
            for idx, layout in enumerate(layouts):
                label = f"p{idx + 1} ({page_order[idx]})"
                dpi, margins, strokes, min_font = _measured(findings, name, label)
                dossier = {
                    "board": f"board_{name[:-4]}_{idx + 1:02d}.png",
                    "source": name,
                    "page": label,
                    "fiche": page_order[idx],
                    "title": " ".join(layout.title.lines),
                    "scene": " ".join(layout.scene.lines),
                    "prompt_fr": " ".join(layout.prompt_fr.lines),
                    "prompt_en": " ".join(layout.prompt_en.lines),
                    "declared_font_pt": {
                        "title": layout.title.size,
                        "scene": layout.scene.size,
                        "prompt_fr": layout.prompt_fr.size,
                        "prompt_en": layout.prompt_en.size,
                    },
                    "measured": {
                        "image_dpi": dpi,
                        "margins_pt": margins,
                        "stroke_widths_pt": strokes,
                        "min_font_pt": min_font,
                    },
                }
                dossiers.append(dossier)

    visual_index = {
        "schema": "b2c3-visual-index-v1",
        "print_scale": "300 dpi = 100 % du format 8.5 x 11 in (2550 x 3300 px)",
        "boards": {d["board"]: d for d in dossiers},
    }

    report = {
        "schema": "b2c3-preflight-v1",
        "diagnostic": {
            "status": diagnostic_status,
            "qa_status": "PASS" if qa_ok else "FAIL",
            "approvals_pin": "provided (64 hex, non enregistré dans les preuves)",
            "head": head,
            "tree": tree,
            "inputs": {
                "out": str(out),
                "book": str(book_path),
                "policy": policy,
            },
            "book_sha256": book.source_sha256,
            "plan_sha256": book.source_plan_sha256,
            "pdf_sha256": pdf_hashes,
            "kdp_facts_verified_at": KDP_FACTS_VERIFIED_AT,
            "kdp_sources": KDP_SOURCES,
        },
        "prepress": {
            "status": prepress_status,
            "bleed": {
                "decision": "UNDECIDED",
                "reason": "bleed=to_be_confirmed dans book.yaml ; aucune hypothèse n'est validée",
                "no_bleed_envelope_pt": list(TRIM_PT),
                "with_bleed_envelope_pt": list(BLEED_PT),
            },
        },
        "editorial": {
            "status": "PENDING",
            "note": "la validation pédagogique de la grille 6 pages est une décision humaine explicite",
        },
        "kdp": {
            "status": "FORBIDDEN",
            "reasons": [
                "démo de 3 pages < seuil KDP de 24 pages (non soumissible)",
                "fond perdu non tranché (to_be_confirmed)",
                "couverture et 56 pages non générées",
                "Print Previewer et épreuve physique non réalisés",
            ],
        },
        "findings": findings,
        "dossiers": dossiers,
        "boards": sorted(boards),
        "limits": [
            "Les seuils KDP sont des seuils de conformité, pas des objectifs de design ; "
            "une taille >= 7 pt ne garantit pas le confort d'un enfant de 4-5 ans.",
            "La parité réelle (gouttière gauche/droite) est indéterminable sur la démo de 3 pages ; "
            "les marges sont diagnostiquées de façon conservatrice sur les deux côtés.",
            "Le contraste et la lisibilité des consignes nécessitent une épreuve papier 100 %.",
            "Aucun score automatique ne vaut approbation éditoriale (APPROBATION_EDITORIALE = PENDING).",
        ],
    }

    # --- write the report atomically into a fresh, symlink-free report-dir ---
    json_bytes = (json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    md_bytes = _build_markdown(report).encode("utf-8")
    visual_index_bytes = (json.dumps(visual_index, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")

    try:
        _make_report_dir(report_dir)
        with _report_dir_fd(report_dir) as report_fd:
            _write_report_file(report_fd, "b2c3_preflight.json", json_bytes)
            _write_report_file(report_fd, "b2c3_preflight.md", md_bytes)
            _write_report_file(report_fd, "b2c3_visual_index.json", visual_index_bytes)
            written_hashes = {}
            if analysis_done:
                for name in ("interior.pdf", "answer_key.pdf"):
                    doc = fitz.open(stream=pdf_bytes[name], filetype="pdf")
                    for index, page in enumerate(doc):
                        board_name = f"board_{name[:-4]}_{index + 1:02d}.png"
                        png = _render_board(pdf_bytes[name], index)
                        _write_report_file(report_fd, board_name, png)
                        written_hashes[board_name] = _sha256_bytes(png)
                    doc.close()
            # final inventory: exact byte hashes of every written file
            final_inventory = {
                "b2c3_preflight.json": _sha256_bytes(json_bytes),
                "b2c3_preflight.md": _sha256_bytes(md_bytes),
                "b2c3_visual_index.json": _sha256_bytes(visual_index_bytes),
                **written_hashes,
            }
            inventory_json = (json.dumps(
                {"files": {k: v for k, v in sorted(final_inventory.items())},
                 "count": len(final_inventory)},
                indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
            _write_report_file(report_fd, "b2c3_inventory.json", inventory_json)
    except (PreflightError, OSError) as exc:
        print(f"ERREUR : écriture du rapport impossible : {exc}", file=sys.stderr)
        return 2

    print(f"PRÉFLIGHT OK | diagnostic={diagnostic_status} | prépresse={prepress_status} "
          f"| éditorial=PENDING | KDP=FORBIDDEN | rapport={report_dir}")
    return 0


def _make_report_dir(report_dir: Path) -> None:
    """Create report-dir (or accept an existing empty real dir); refuse anything else."""
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    raw = os.fspath(report_dir)
    absolute = Path(os.path.abspath(raw))
    parts = absolute.parts[1:]
    fd = os.open("/", flags)
    try:
        for component in parts[:-1]:
            next_fd = os.open(component, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        leaf = parts[-1]
        try:
            mode = os.stat(leaf, dir_fd=fd, follow_symlinks=False).st_mode
        except FileNotFoundError:
            os.mkdir(leaf, mode=0o700, dir_fd=fd)
            return
        if not stat.S_ISDIR(mode):
            raise PreflightError("--report-dir n'est pas un répertoire réel")
        with os.scandir(fd) as scan:
            entries = sorted(e.name for e in scan)
        sub = os.open(leaf, flags, dir_fd=fd)
        try:
            with os.scandir(sub) as scan:
                inner = sorted(e.name for e in scan)
            if inner or any(name.startswith(".") for name in entries):
                raise PreflightError("--report-dir doit être vide (collision/entrée cachée refusée)")
        finally:
            os.close(sub)
    finally:
        os.close(fd)


def _report_dir_fd(report_dir: Path):
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    raw = os.fspath(report_dir)
    absolute = Path(os.path.abspath(raw))
    fd = os.open("/", flags)
    for component in absolute.parts[1:]:
        next_fd = os.open(component, flags, dir_fd=fd)
        os.close(fd)
        fd = next_fd
    return _FD(fd)


class _FD:
    def __init__(self, fd):
        self._fd = fd

    def __enter__(self):
        return self._fd

    def __exit__(self, *exc):
        os.close(self._fd)
        return False


if __name__ == "__main__":
    raise SystemExit(main())
