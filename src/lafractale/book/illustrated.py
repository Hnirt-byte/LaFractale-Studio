"""Pages illustrées : Python garde l'exercice, les images ne font qu'habiller ou donner leur peau aux objets.

Ordre de dessin : décor -> exercice (Python) -> objets d'exercice (placés et comptés par Python).
Un décor qui toucherait la zone de l'exercice est refusé ; une image absente est signalée ASSET_MANQUANT.
"""
from __future__ import annotations

import random

from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from lafractale.activities.engine import generate
from lafractale.activities.models import ActivitySpec
from lafractale.book.assets import MISSING
from lafractale.book.pages import BookError, PageRow
from lafractale.layout.composition import PageComposition, Rect
from lafractale.layout.pdf import _maze

ZONE_BOTTOM_STRIP = 70.0  # bande de réponses de la page find_count


def _fit(img_w: float, img_h: float, zone: Rect, anchor: str, max_side: float | None) -> Rect:
    scale = min(zone.width / img_w, zone.height / img_h)
    if max_side:
        scale = min(scale, max_side / max(img_w, img_h))
    w, h = img_w * scale, img_h * scale
    x = zone.x + (zone.width - w) / 2
    y = {"top": zone.top - h, "bottom": zone.y}.get(anchor, zone.y + (zone.height - h) / 2)
    return Rect(x, y, w, h)


def _draw_img(c: canvas.Canvas, img, box: Rect, *, flip: bool = False, angle: float = 0.0) -> None:
    c.saveState()
    c.translate(box.x + box.width / 2, box.y + box.height / 2)
    if angle:
        c.rotate(angle)
    if flip:
        c.scale(-1, 1)
    c.drawImage(ImageReader(img), -box.width / 2, -box.height / 2, width=box.width, height=box.height,
                mask="auto" if img.mode == "RGBA" else None)
    c.restoreState()


def _missing(c: canvas.Canvas, ctx, box: Rect, asset_id: str) -> None:
    """Emplacement réservé, explicitement marqué : jamais un faux dessin."""
    c.saveState()
    c.setStrokeGray(.45)
    c.setLineWidth(1.2)
    c.setDash(4, 4)
    c.roundRect(box.x, box.y, box.width, box.height, 8, stroke=1, fill=0)
    c.setDash()
    c.setFillGray(.3)
    from lafractale.layout.pdf import _measure
    size = min(8.0, 8.0 * (box.width - 6) / _measure(MISSING, ctx.bold, 8))
    c.setFont(ctx.bold, size)
    c.drawCentredString(box.x + box.width / 2, box.y + box.height / 2 + 2, MISSING)
    small = min(6.5, 6.5 * (box.width - 6) / max(_measure(asset_id, ctx.regular, 6.5), 1))
    c.setFont(ctx.regular, small)
    c.drawCentredString(box.x + box.width / 2, box.y + box.height / 2 - 7, asset_id)
    c.restoreState()


def _zones(layout: PageComposition, occupied: Rect | None, strip: float = 0.0) -> dict[str, Rect]:
    b, h = layout.board, layout.header
    top_free = b.top - 40  # sous l'étiquette de la zone d'activité
    zones = {"header": Rect(h.x + 14, h.y + 4, h.width - 170, h.height - 8),
             "scene": Rect(b.x + 10, b.y + 10 + strip, b.width - 20, b.height - 52 - strip),
             "board_top_center": Rect(b.x + b.width / 2 - 50, b.top - 78, 100, 68)}
    if occupied is not None:
        zones["board_left"] = Rect(b.x + 10, b.y + 12, max(1, occupied.x - b.x - 22), top_free - b.y - 12)
        zones["board_right"] = Rect(occupied.right + 12, b.y + 12, max(1, b.right - occupied.right - 22),
                                    top_free - b.y - 12)
    return zones


def _maze_occupied(act, board: Rect) -> Rect:
    size = act.geometry["size"]
    cell = min((board.width - 80) / size, (board.height - 95) / size)
    span = size * cell
    ox = board.x + (board.width - span) / 2
    oy = board.y + (board.height - span) / 2 - 4
    return Rect(ox - 6, oy - 32, span + 12, span + 40)


def _decor(c, ctx, plan, layout, occupied, page: int) -> bool:
    """Dessine le décor ; renvoie True si la zone d'en-tête est habillée (le titre générique est alors omis)."""
    zones = _zones(layout, occupied, ZONE_BOTTOM_STRIP if plan["activity"] == "find_count" else 0.0)
    header_done = False
    for d in plan.get("decor", []):
        zone = zones.get(d["zone"])
        if zone is None:
            raise BookError(f"page {page} : zone de décor inconnue ou indisponible : {d['zone']}")
        img = ctx.store.get(d["asset"], page)
        if img is None:
            box = _fit(1, 1, zone, d.get("anchor", "middle"), d.get("size_pt"))
            box = box if d["zone"] != "header" else zone
        else:
            box = _fit(img.width, img.height, zone, d.get("anchor", "middle"), d.get("size_pt"))
        if occupied is not None and d["zone"] != "scene" and box.overlaps(occupied):
            raise BookError(f"page {page} : le décor {d['asset']} recouvre la zone de l'exercice")
        if img is None:
            _missing(c, ctx, box, d["asset"])
        else:
            ctx.store.check_dpi(d["asset"], page, box.width)
            _draw_img(c, img, box)
        header_done = header_done or d["zone"] == "header"
    return header_done


def _object(c, ctx, asset_id: str, box: Rect, page: int, **kw) -> None:
    img = ctx.store.get(asset_id, page)
    if img is None:
        _missing(c, ctx, box, asset_id)
    else:
        sized = _fit(img.width, img.height, box, "middle", None)
        ctx.store.check_dpi(asset_id, page, sized.width)
        _draw_img(c, img, sized, **kw)


# ------------------------------------------------------------------ exercices

def _match_c4(c, row, ctx, plan, layout) -> Rect:
    """Chapeaux jumeaux : permutation canonique de la démo C4 ; les images ne font que dessiner les 4 symboles."""
    from lafractale.activities.engine import stable_seed
    spec = ActivitySpec(f"halloween_2026-p{row.page:03d}", row.page, "match", (4, 5), row.title, ("hat",),
                        companion_name="Pip")
    act = generate(spec, stable_seed("halloween_2026", spec.id, ctx.seed))
    left, right = act.geometry["left_symbols"], act.geometry["right_symbols"]
    mapping = plan["symbol_assets"]
    if set(left) != set(mapping) or sorted(left) != sorted(right):
        raise BookError(f"page {row.page} : symbol_assets ne correspond pas aux symboles de l'exercice {sorted(left)}")
    b = layout.board
    rows_n = len(left)
    top, bottom = b.top - 80, b.y + 25
    side = min(92.0, (top - bottom) / (rows_n * 1.3))
    step = (top - bottom - side) / (rows_n - 1)
    lx, rx = b.x + 70, b.right - 70 - side
    for i in range(rows_n):
        y = top - side - i * step
        for x, symbol, dot_x in ((lx, left[i], lx + side + 8), (rx, right[i], rx - 8)):
            _object(c, ctx, mapping[symbol], Rect(x, y, side, side), row.page)
            c.setFillGray(.1)
            c.circle(dot_x, y + side / 2, 6, fill=1, stroke=0)
    return Rect(lx, bottom, rx + side - lx, top - bottom)


def _find_count(c, row, ctx, plan, layout) -> Rect:
    """Chercher et compter : positions et nombre de cibles décidés par Python ; la scène n'est qu'un fond."""
    b = layout.board
    full = _zones(layout, None)["scene"]
    zone = full
    scene = _zones(layout, None, ZONE_BOTTOM_STRIP)["scene"]
    targets: dict[str, int] = plan["targets"]
    rng = random.Random(f"{ctx.seed}-p{row.page}")
    size, placed = 64.0, []
    for name, count in targets.items():
        for _ in range(count):
            for _try in range(2000):
                x = rng.uniform(scene.x + 10, scene.right - size - 10)
                y = rng.uniform(scene.y + 10, scene.top - size - 10)
                if all(abs(x - px) > size * 1.15 or abs(y - py) > size * 1.15 for _, px, py, *_ in placed):
                    placed.append((name, x, y, rng.random() < .5, rng.uniform(-14, 14)))
                    break
            else:
                raise BookError(f"page {row.page} : placement impossible de {count} {name}")
    for name, x, y, flip, angle in placed:
        _object(c, ctx, plan["target_assets"][name], Rect(x, y, size, size), row.page, flip=flip, angle=angle)
    # bande de réponses : une case par type de cible, avec son modèle
    c.setStrokeGray(.4)
    c.setLineWidth(1.5)
    n = len(targets)
    for i, (name, _) in enumerate(targets.items()):
        x0 = zone.x + 30 + i * (zone.width - 60) / n
        _object(c, ctx, plan["target_assets"][name], Rect(x0, zone.y + 6, 52, 52), row.page)
        c.setFillGray(.15)
        c.setFont(ctx.bold, 11)
        c.drawString(x0 + 60, zone.y + 40, plan["target_labels"][name])
        c.roundRect(x0 + 60, zone.y + 8, 56, 26, 6, fill=0, stroke=1)
    ctx.answers[row.page] = dict(targets)
    return scene


def draw_illustrated(c: canvas.Canvas, row: PageRow, ctx) -> None:
    from lafractale.book import draw
    plan = ctx.manifest.pages.get(row.page)
    if plan is None:
        raise BookError(f"page {row.page} : gabarit 'illustre' sans entrée dans assets_manifest.yaml")
    total = len(ctx.rows)
    kind = plan["activity"]
    labels = {"maze_c4": "TROUVE LE CHEMIN", "match_c4": "RELIE LES JUMEAUX",
              "find_count": "CHERCHE ET COMPTE", "coloring_scene": "COLORIE"}
    if kind == "maze_c4":
        act = draw._maze_activity(row, ctx)
    else:
        act = draw._activity(row, ctx)
    layout = draw._layout(act, ctx, total)
    occupied = _maze_occupied(act, layout.board) if kind == "maze_c4" else None
    # le fond d'abord (décor), puis la coque, puis l'exercice : le décor ne peut rien masquer
    header_done = False
    draw._shell(c, layout, row, ctx, total, labels[kind], title=False, slot_pip=False, note=draw.PILOT_NOTE)
    header_done = _decor(c, ctx, plan, layout, occupied, row.page)
    if not header_done:
        c.setFillGray(.12)
        c.setFont(ctx.bold, 19)
        c.drawString(layout.header.x + 17, layout.header.y + 28, "Je joue avec Pip !")
    if kind == "maze_c4":
        _maze(c, act, layout.board, False, ctx.bold, ctx.editorial)
    elif kind == "match_c4":
        _match_c4(c, row, ctx, plan, layout)
    elif kind == "find_count":
        _find_count(c, row, ctx, plan, layout)
    elif kind != "coloring_scene":
        raise BookError(f"page {row.page} : activité illustrée inconnue {kind!r}")
