"""Deterministic monochrome worksheet renderer driven by a checked page composition.

All shapes and answer paths come from validated activity data. No character is
redrawn or inferred from the reference image, including Pip.
"""
from __future__ import annotations

from dataclasses import replace
from io import BytesIO
from types import MappingProxyType
from collections.abc import Mapping
import copy
import math
import os
from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

from lafractale.activities.models import Activity
from lafractale.activities.engine import generate
from lafractale import __version__
from lafractale.config.schema import Book, verify_book_snapshot
from lafractale.layout.composition import Rect, TextBlock, compose_page
from lafractale.export.securefs import new_regular_file
from lafractale.quality.checks import validate_collection
from lafractale.security.text import verify_text_policy
from lafractale.illustrations.registry import VerifiedArtwork, verify_approved_artwork, IllustrationError
from lafractale.illustrations.routing import IllustrationRoute, verify_illustration_route
from lafractale.illustrations.placement import (PipPlacementPlan, build_pip_placement_plan,
    placed_composition, resolve_pip_placement_mode, verify_pip_placement_plan)
from lafractale.story.plan import demo_specs


def fonts() -> tuple[str, str]:
    regular = Path(os.getenv("LAFRACTALE_FONT_PATH", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
    bold = Path(os.getenv("LAFRACTALE_FONT_BOLD_PATH", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
    if not regular.is_file() or not bold.is_file():
        raise RuntimeError("DejaVu Sans TTF absent : définir LAFRACTALE_FONT_PATH et LAFRACTALE_FONT_BOLD_PATH")
    for name, filename in (("LaFractaleRegular", regular), ("LaFractaleBold", bold)):
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(filename)))
    return "LaFractaleRegular", "LaFractaleBold"


def _measure(text: str, font: str, size: int) -> float:
    return pdfmetrics.stringWidth(text, font, size)


def _draw_text(c: canvas.Canvas, text: TextBlock, *, gray: float = 0.07) -> None:
    c.setFillGray(gray)
    c.setFont(text.font, text.size)
    for index, line in enumerate(text.lines):
        c.drawString(text.region.x, text.region.top - text.size - index * text.leading, line)


def _frame(c: canvas.Canvas, box: Rect) -> None:
    # Contrast and whitespace are optimized for A4/US-letter size monochrome
    # proofing. They are not a substitute for press-preflight checks.
    c.setFillGray(.978)
    c.setStrokeGray(.62)
    c.setLineWidth(1.3)
    c.roundRect(box.x, box.y, box.width, box.height, 16, stroke=1, fill=1)


def _draw_shell(c: canvas.Canvas, layout, activity: Activity, regular: str, bold: str,
                index: int, total: int, artwork: VerifiedArtwork | None = None) -> None:
    header = layout.header
    c.setFillGray(.945)
    c.setStrokeGray(.58)
    c.setLineWidth(1.1)
    c.roundRect(header.x, header.y, header.width, header.height, 14, fill=1, stroke=1)
    c.setFillGray(.12)
    c.roundRect(header.x, header.y, 9, header.height, 4, fill=1, stroke=0)
    _draw_text(c, layout.title)
    c.setFillGray(1)
    c.setStrokeGray(.38)
    c.roundRect(header.right - 145, header.y + 13, 130, 41, 13, stroke=1, fill=1)
    _draw_text(c, layout.page_label)
    _draw_text(c, layout.scene)
    slot = layout.companion_slot
    if artwork is None:
        # By default the reference-color Pip and all unapproved images are ABSENT.
        c.saveState()
        c.setStrokeGray(.67)
        c.setDash(2.4, 3.2)
        c.roundRect(slot.x + 3, slot.y + 3, slot.width - 6, slot.height - 6, 7, stroke=1, fill=0)
        c.restoreState()
        c.setFillGray(.34)
        c.setFont(regular, 7)
        label = "VISUEL À VALIDER"
        if _measure(label, regular, 7) > slot.width - 14:
            raise ValueError("Libellé du visuel trop long")
        c.drawCentredString(slot.x + slot.width / 2, slot.y + slot.height / 2 - 2, label)
    else:
        if artwork.variant != "monochrome" or artwork.role != "companion":
            raise IllustrationError("Visuel imprimable non conforme")
        # The image only ever comes from validated, detached immutable PNG bytes.
        scale = min((slot.width - 8) / artwork.width, (slot.height - 6) / artwork.height)
        w, h = artwork.width * scale, artwork.height * scale
        if min(artwork.width / (w / 72), artwork.height / (h / 72)) < 300:
            raise IllustrationError("Résolution insuffisante pour le visuel à 300 DPI")
        if w <= 0 or h <= 0 or w > slot.width - 8 + .001 or h > slot.height - 6 + .001:
            raise IllustrationError("Visuel hors zone graphique")
        x, y = slot.x + (slot.width - w) / 2, slot.y + (slot.height - h) / 2
        c.drawImage(ImageReader(BytesIO(artwork.pixels)), x, y, width=w, height=h,
                    preserveAspectRatio=False, mask=None)
    _draw_text(c, layout.prompt_fr)
    _draw_text(c, layout.prompt_en, gray=.26)
    c.setLineWidth(1)
    c.setStrokeGray(.7)
    c.line(layout.footer.x, layout.footer.top - 1,
           layout.footer.right, layout.footer.top - 1)
    c.setFillGray(.28)
    c.setFont(regular, 8)
    footer_message = "MAQUETTE DE TRAVAIL | REVUE VISUELLE ET KDP EN ATTENTE"
    if _measure(footer_message, regular, 8) > layout.footer.width - 62:
        raise ValueError("Pied de page trop long")
    c.drawString(layout.footer.x + 2, layout.footer.y + 15, footer_message)
    c.drawRightString(layout.footer.right - 2, layout.footer.y + 15, f"{index}/{total}")
    _frame(c, layout.board)
    c.setFillGray(.28)
    c.setFont(bold, 9)
    label = {"maze": "TROUVE LE CHEMIN", "match": "RELIE LES JUMEAUX",
             "connect_dots": "RELIE LES POINTS"}[activity.type]
    c.drawString(layout.board.x + 22, layout.board.top - 27, label)


def _maze(c: canvas.Canvas, act: Activity, board: Rect, solution: bool, bold: str) -> None:
    geometry = act.geometry
    size = geometry["size"]
    cell = min((board.width - 80) / size, (board.height - 95) / size)
    if cell < 35:
        raise ValueError("Labyrinthe trop petit pour être lisible")
    span = size * cell
    origin_x = board.x + (board.width - span) / 2
    origin_y = board.y + (board.height - span) / 2 - 4
    passages = {tuple(sorted((tuple(a), tuple(b)))) for a, b in geometry["open_edges"]}
    c.setLineWidth(3.0)
    c.setStrokeGray(.11)
    for y in range(size):
        for x in range(size):
            node = (x, y)
            if y == 0 or tuple(sorted((node, (x, y - 1)))) not in passages:
                c.line(origin_x + x * cell, origin_y + y * cell,
                       origin_x + (x + 1) * cell, origin_y + y * cell)
            if x == 0 or tuple(sorted((node, (x - 1, y)))) not in passages:
                c.line(origin_x + x * cell, origin_y + y * cell,
                       origin_x + x * cell, origin_y + (y + 1) * cell)
    c.line(origin_x, origin_y + span, origin_x + span, origin_y + span)
    c.line(origin_x + span, origin_y, origin_x + span, origin_y + span)
    if solution:
        c.saveState()
        c.setStrokeGray(.66)
        c.setLineWidth(8)
        c.setLineCap(1)
        path = c.beginPath()
        for index, (x, y) in enumerate(act.answer["path"]):
            cx, cy = origin_x + (x + .5) * cell, origin_y + (y + .5) * cell
            if index == 0:
                path.moveTo(cx, cy)
            else:
                path.lineTo(cx, cy)
        c.drawPath(path)
        c.restoreState()
    for x, y, marker in ((0, 0, "D"), (size - 1, size - 1, "A")):
        px, py = origin_x + (x + .5) * cell, origin_y + (y + .5) * cell
        c.setFillGray(1)
        c.setStrokeGray(.16)
        c.circle(px, py, 13, fill=1, stroke=1)
        c.setFillGray(.06)
        c.setFont(bold, 12)
        c.drawCentredString(px, py - 4, marker)
    c.setFillGray(.22)
    c.setFont(bold, 10)
    c.drawString(origin_x, origin_y - 24, "D = Départ")
    c.drawRightString(origin_x + span, origin_y - 24, "A = Arrivée")


def _symbol(c: canvas.Canvas, name: str, x: float, y: float, r: float) -> None:
    """Reproducible simple worksheet icons, not licensed character art."""
    c.setStrokeGray(.12)
    c.setLineWidth(2.6)
    if name.startswith("hat_"):
        p = c.beginPath()
        p.moveTo(x - r * .90, y - r * .48)
        p.lineTo(x - r * .54, y - r * .48)
        p.lineTo(x, y + r * 1.03)
        p.lineTo(x + r * .54, y - r * .48)
        p.lineTo(x + r * .90, y - r * .48)
        p.lineTo(x + r, y - r * .70)
        p.lineTo(x - r, y - r * .70)
        p.close()
        c.drawPath(p)
        _symbol(c, name[4:], x, y - r * .24, r * .32)
        return
    if name.startswith("gift_"):
        c.roundRect(x - r * .78, y - r * .76, 1.56 * r, 1.44 * r, r * .12)
        c.line(x - r * .78, y + r * .30, x + r * .78, y + r * .30)
        c.line(x, y + r * .30, x, y + r * .68)
        _symbol(c, name[5:], x, y - r * .18, r * .31)
        return
    if name == "circle":
        c.circle(x, y, r, stroke=1, fill=0)
        return
    if name == "square":
        c.rect(x - r, y - r, r * 2, r * 2)
        return
    if name == "triangle":
        count, offset = 3, math.pi / 2
    elif name == "diamond":
        count, offset = 4, math.pi / 2
    elif name == "star":
        count, offset = 10, math.pi / 2
    elif name == "hexagon":
        count, offset = 6, math.pi / 2
    else:
        raise ValueError(f"Symbole non implémenté : {name}")
    path = c.beginPath()
    for i in range(count):
        radius = (r if i % 2 == 0 else .47 * r) if name == "star" else r
        angle = offset + 2 * math.pi * i / count
        xy = (x + radius * math.cos(angle), y + radius * math.sin(angle))
        if i == 0:
            path.moveTo(*xy)
        else:
            path.lineTo(*xy)
    path.close()
    c.drawPath(path)


def _match(c: canvas.Canvas, act: Activity, board: Rect, solution: bool) -> None:
    left_x = board.x + board.width * .26
    right_x = board.x + board.width * .74
    usable_height = board.height - 128
    row_gap = usable_height / 3
    rows = [board.top - 72 - index * row_gap for index in range(4)]
    left_anchor = board.x + board.width * .40
    right_anchor = board.x + board.width * .60
    for i, name in enumerate(act.geometry["left_symbols"]):
        _symbol(c, name, left_x, rows[i], 26)
        c.setFillGray(.11)
        c.circle(left_anchor, rows[i], 3.4, fill=1, stroke=0)
    for i, name in enumerate(act.geometry["right_symbols"]):
        _symbol(c, name, right_x, rows[i], 26)
        c.setFillGray(.11)
        c.circle(right_anchor, rows[i], 3.4, fill=1, stroke=0)
    if solution:
        c.saveState()
        c.setStrokeGray(.45)
        c.setLineWidth(2.4)
        for i, j in enumerate(act.answer["left_to_right"]):
            c.line(left_anchor, rows[i], right_anchor, rows[j])
        c.restoreState()


def _labels_for_points(points: list[tuple[float, float]], board: Rect, bold: str) -> list[tuple[float, float]]:
    """Place every number within the panel, away from other dots and labels."""
    chosen: list[Rect] = []
    output: list[tuple[float, float]] = []
    bounds = Rect(board.x + 10, board.y + 13, board.width - 20, board.height - 55)
    offsets = ((0, 19), (18, 8), (-18, 8), (19, -14), (-19, -14),
               (0, -24), (25, 21), (-25, 21), (27, -25), (-27, -25),
               (36, 0), (-36, 0))
    for index, (x, y) in enumerate(points):
        label = str(index + 1)
        w = _measure(label, bold, 11) + 6
        for dx, dy in offsets:
            cx, cy = x + dx, y + dy
            box = Rect(cx - w / 2, cy - 5, w, 13)
            if not bounds.contains(box) or any(box.overlaps(other) for other in chosen):
                continue
            if any((cx - px) ** 2 + (cy - py) ** 2 < 13 ** 2 for px, py in points):
                continue
            chosen.append(box)
            output.append((cx, cy - 4))
            break
        else:
            raise ValueError("Numérotation des points illisible : placement impossible")
    return output


def _dots(c: canvas.Canvas, act: Activity, board: Rect, solution: bool, bold: str) -> None:
    points = act.geometry["points"]
    if len(points) > 30:
        raise ValueError("Trop de points pour la fiche V0.2-B")
    x0, y0 = board.x + 67, board.y + 42
    x_span, y_span = board.width - 134, board.height - 110
    coords = [(x0 + p["x"] * x_span, y0 + p["y"] * y_span) for p in points]
    positions = _labels_for_points(coords, board, bold)
    if solution:
        c.saveState()
        c.setStrokeGray(.50)
        c.setLineWidth(2.8)
        path = c.beginPath()
        for i, (x, y) in enumerate(coords):
            (path.moveTo if i == 0 else path.lineTo)(x, y)
        path.close()
        c.drawPath(path)
        c.restoreState()
    for (x, y), (tx, ty), p in zip(coords, positions, points):
        c.setFillGray(.08)
        c.circle(x, y, 4.1, fill=1, stroke=0)
        c.setFont(bold, 11)
        c.drawCentredString(tx, ty, str(p["n"]))


def _freeze(value):
    """Recursively eliminate mutable aliases across compose/draw and callers."""
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _render_snapshot(activities: list[Activity]) -> tuple[Activity, ...]:
    """Validate a completely detached copy, then render with immutable data."""
    copies = copy.deepcopy(activities)
    verify_text_policy([a.as_dict() for a in copies], location="activités PDF")
    errors = validate_collection(copies)
    if errors:
        raise ValueError("Activités PDF invalides : " + "; ".join(errors))
    return tuple(replace(act, geometry=_freeze(act.geometry), answer=_freeze(act.answer))
                 for act in copies)


def _routed_render_snapshot(activities: list[Activity], *, approved_book: Book,
                            illustration_route: IllustrationRoute,
                            trusted_approvals_sha256: str) -> tuple[Activity, ...]:
    """Bind a routed render to the complete canonical C1 activity sequence.

    A valid route authorizes only its three independently regenerated Halloween
    activities in canonical PDF order; it never authorizes an arbitrary prefix
    or caller-supplied activity list.
    """
    if type(illustration_route) is not IllustrationRoute:
        raise IllustrationError("Objet de routage non canonique")
    verify_book_snapshot(approved_book)
    specs = tuple(demo_specs(approved_book))
    detached = tuple(copy.deepcopy(activities))
    rendering = _render_snapshot(list(detached))
    if len(specs) != 3 or len(rendering) != len(specs):
        raise IllustrationError("Séquence d'activités routée C1 incomplète ou supplémentaire")
    if len(illustration_route.bindings) != len(specs):
        raise IllustrationError("Couverture de route C1 incomplète ou supplémentaire")
    for index, (activity, spec, binding) in enumerate(
            zip(detached, specs, illustration_route.bindings, strict=True), start=1):
        expected_activity = generate(spec, activity.seed)
        if activity != expected_activity:
            raise IllustrationError("Activité routée non conforme aux spécifications canoniques")
        if (binding.demo_index, binding.activity_id, binding.source_page, binding.activity_type) != (
                index, spec.id, spec.page, spec.type):
            raise IllustrationError("Liaison de route C1 non conforme aux spécifications canoniques")
        illustration_route.artwork_for(activity, demo_index=index)
    verify_illustration_route(approved_book, illustration_route,
                              policy_id=illustration_route.policy_id,
                              trusted_approvals_sha256=trusted_approvals_sha256)
    return rendering


def _page_layout(act: Activity, book_snapshot, *, index: int, count: int, answer_key: bool,
                 regular: str, bold: str,
                 placement: PipPlacementPlan | None):
    """Compose one page, applying the canonical C2 placement when requested."""
    layout = compose_page(act, book_snapshot, index=index, count=count, answer_key=answer_key,
                          regular=regular, bold=bold, text_width=_measure)
    if placement is None:
        return layout
    return placed_composition(layout, placement.anchor_for(act, demo_index=index),
                              text_width=_measure)


def write_pdf(path: Path, activities: list[Activity], book: dict, *, answer_key: bool,
              artwork: VerifiedArtwork | None = None,
              illustration_route: IllustrationRoute | None = None,
              pip_placement: str | None = None,
              approved_book: Book | None = None,
              trusted_approvals_sha256: str | None = None) -> None:
    """Render from a checked immutable snapshot to a new, safe file only.

    A writer calling compose_page cannot alter geometry passed to _dots().
    Separately, the original activities are never accessed during drawing.
    The optional C2 placement is named by policy string only; its plan is
    recomputed from the verified Book, the canonical C1 route and the external
    pin, and every page layout is validated before the destination file exists.
    """
    if artwork is not None and illustration_route is not None:
        raise IllustrationError("Visuel historique et route C1 mutuellement exclusifs")
    if pip_placement is not None and illustration_route is None:
        raise IllustrationError("Placement Pip exige la route C1 explicite et un PIN externe")
    if pip_placement is not None and artwork is not None:
        raise IllustrationError("Visuel historique et placement C2 mutuellement exclusifs")
    placement_mode = resolve_pip_placement_mode(pip_placement)
    rendering: tuple[Activity, ...]
    placement: PipPlacementPlan | None = None
    if artwork is not None:
        if approved_book is None or trusted_approvals_sha256 is None:
            raise IllustrationError("Source d'approbation indépendante obligatoire pour un visuel PDF")
        verify_approved_artwork(approved_book, artwork,
                                trusted_approvals_sha256=trusted_approvals_sha256)
        if approved_book.data != book:
            raise IllustrationError("Configuration PDF non conforme au livre approuvé")
        rendering = _render_snapshot(activities)
    elif illustration_route is not None:
        if approved_book is None or trusted_approvals_sha256 is None:
            raise IllustrationError("Source d'approbation indépendante obligatoire pour une route PDF")
        verify_illustration_route(approved_book, illustration_route,
                                  policy_id=illustration_route.policy_id,
                                  trusted_approvals_sha256=trusted_approvals_sha256)
        if approved_book.data != book:
            raise IllustrationError("Configuration PDF non conforme au livre approuvé")
        rendering = _routed_render_snapshot(
            activities, approved_book=approved_book, illustration_route=illustration_route,
            trusted_approvals_sha256=trusted_approvals_sha256,
        )
        if placement_mode != "none":
            assert isinstance(pip_placement, str)
            placement = build_pip_placement_plan(
                approved_book, illustration_route, policy_id=pip_placement,
                trusted_approvals_sha256=trusted_approvals_sha256,
            )
            for index, act in enumerate(rendering, start=1):
                placement.anchor_for(act, demo_index=index)
    elif approved_book is not None or trusted_approvals_sha256 is not None:
        raise IllustrationError("Paramètres graphiques partiels interdits")
    else:
        rendering = _render_snapshot(activities)
    book_snapshot = _freeze(copy.deepcopy(book))
    verify_text_policy(book_snapshot, location="configuration PDF")
    regular, bold = fonts()
    width, height = book_snapshot["trim"]["width_in"] * 72, book_snapshot["trim"]["height_in"] * 72
    # Compose and validate every page - including a C2 placement - BEFORE the
    # destination file is opened or created, so a refusal never writes output.
    layouts = tuple(
        _page_layout(act, book_snapshot, index=index, count=len(rendering),
                     answer_key=answer_key, regular=regular, bold=bold, placement=placement)
        for index, act in enumerate(rendering, start=1)
    )
    page_artworks = tuple(
        (illustration_route.artwork_for(act, demo_index=index)
         if illustration_route is not None else artwork)
        for index, act in enumerate(rendering, start=1)
    )
    with new_regular_file(path) as destination:
        c = canvas.Canvas(destination, pagesize=(width, height), invariant=1, pageCompression=1)
        c.setTitle(("CORRIGES" if answer_key else "DEMONSTRATION") + " - " + book_snapshot["title"])
        c.setAuthor(book_snapshot["publisher"])
        for index, (act, layout, page_artwork) in enumerate(
                zip(rendering, layouts, page_artworks, strict=True), start=1):
            _draw_shell(c, layout, act, regular, bold, index, len(rendering), artwork=page_artwork)
            if act.type == "maze":
                _maze(c, act, layout.board, answer_key, bold)
            elif act.type == "match":
                _match(c, act, layout.board, answer_key)
            elif act.type == "connect_dots":
                _dots(c, act, layout.board, answer_key, bold)
            else:
                raise ValueError(f"Type de rendu absent : {act.type}")
            c.showPage()
        c.save()
