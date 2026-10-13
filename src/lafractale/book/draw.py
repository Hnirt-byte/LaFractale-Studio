"""Dessin des pages d'aperçu : coque commune, gabarit CHEMIN, gabarit provisoire."""
from __future__ import annotations

import hashlib
import json
import math
from io import BytesIO
from pathlib import Path

from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from lafractale.activities.engine import generate, stable_seed
from lafractale.activities.models import Activity, ActivitySpec
from lafractale.book.assets import AssetStore, load_manifest
from lafractale.book.pages import BookError, PageRow
from lafractale.editorial import _MOON_8, EDITORIAL_HALLOWEEN_V1, editorial_spec
from lafractale.layout.composition import PageComposition, Rect, compose_page
from lafractale.layout.pdf import _dots, _draw_text, _maze, _measure, fonts
from lafractale.mechanics_v2.registry import generate_v2

WATERMARK = "APERÇU — NON DESTINÉ À LA PUBLICATION"
BOARD_LABELS = {"maze": "TROUVE LE CHEMIN", "connect_dots": "RELIE LES POINTS",
                "trace_paths": "REPASSE LES CHEMINS", "path_logic": "SUIS LE BON CHEMIN"}
# Étape de la feuille de route où chaque type provisoire recevra son gabarit.
ROADMAP_STEP = {"front_matter": "PR 4", "glossary typographique": "PR 4", "diploma + back_matter": "PR 4",
                "coloring": "PR 4", "creative_color": "PR 4", "answers": "PR 5",
                "match": "PR 2", "shadow_match": "PR 2", "match_vocabulary": "PR 2", "one_to_one": "PR 2",
                "pattern": "PR 2", "count": "PR 3", "find_count": "PR 3", "pair_matching": "PR 3",
                "sort": "PR 3", "spot_differences": "PR 3"}
# Maison provisoire (contour simple fermé : toit, cheminée, porte), 15 points.
HOUSE_15 = ((.20, .15), (.20, .52), (.08, .52), (.50, .90), (.66, .76), (.66, .88), (.78, .88), (.78, .64),
            (.92, .52), (.80, .52), (.80, .15), (.58, .15), (.58, .38), (.42, .38), (.42, .15))


class Context:
    """Ressources partagées par toutes les pages d'un aperçu."""

    def __init__(self, repo_root: Path, book: dict, rows: list[PageRow], seed: int) -> None:
        self.book, self.rows, self.seed = book, rows, seed
        self.regular, self.bold = fonts()
        self.editorial = editorial_spec(EDITORIAL_HALLOWEEN_V1)
        self.small_en: list[int] = []
        self.answers: dict[int, dict] = {}  # réponses calculées par Python pour les pages illustrées
        manifest_path = repo_root / "books/halloween_2026/assets_manifest.yaml"
        self.manifest = load_manifest(manifest_path, repo_root)
        self.store = AssetStore(self.manifest)
        self._pip: dict[str, bytes] = {}
        approvals = json.loads((repo_root / "assets/illustrations/approvals.json").read_text(encoding="utf-8"))
        for item in approvals["illustrations"]:
            if item["companion_id"] != "pip" or not item.get("human_approved"):
                continue
            data = (repo_root / item["path"]).read_bytes()
            if hashlib.sha256(data).hexdigest() != item["sha256"]:
                raise BookError(f"image Pip modifiée depuis son approbation : {item['path']}")
            self._pip[item["id"].split("-")[1]] = data  # accueil, encouragement, indication...

    def pip(self, pose: str) -> bytes | None:
        return self._pip.get(pose)


def _activity(row: PageRow, ctx: Context, *, prompt_fr: str | None = None, prompt_en: str | None = None,
              geometry: dict | None = None, answer: dict | None = None) -> Activity:
    return Activity(f"halloween_2026-p{row.page:03d}", row.page, row.type, (4, 5), row.title, (),
                    row.prompt_fr if prompt_fr is None else prompt_fr,
                    row.prompt_en if prompt_en is None else prompt_en, (),
                    geometry or {}, answer or {}, ctx.seed, "", "provisoire", "indication", "Pip")


def _layout(act: Activity, ctx: Context, total: int) -> PageComposition:
    args = dict(index=act.page, count=total, answer_key=False, regular=ctx.regular, bold=ctx.bold,
                text_width=_measure)
    try:
        return compose_page(act, ctx.book, editorial=ctx.editorial, **args)
    except ValueError:
        # Consigne anglaise trop longue pour une ligne en corps 12 : repli en corps 10 (signalé au rapport).
        layout = compose_page(act, ctx.book, editorial=None, **args)
        ctx.small_en.append(act.page)
        return layout


PILOT_NOTE = WATERMARK + "  |  PAGE PILOTE — PARAMÈTRES ET ILLUSTRATIONS À VALIDER"


def _shell(c: canvas.Canvas, layout: PageComposition, row: PageRow, ctx: Context, total: int,
           board_label: str, *, title: bool = True, slot_pip: bool = True, note: str | None = None) -> None:
    header, slot = layout.header, layout.companion_slot
    c.setFillGray(1)
    c.setStrokeGray(.58)
    c.setLineWidth(1.1)
    c.roundRect(header.x, header.y, header.width, header.height, 14, fill=1, stroke=1)
    c.setFillGray(.12)
    c.roundRect(header.x, header.y, 9, header.height, 4, fill=1, stroke=0)
    if title:
        _draw_text(c, layout.title)
    c.setFillGray(1)
    c.setStrokeGray(.38)
    c.roundRect(header.right - 145, header.y + 13, 130, 41, 13, stroke=1, fill=1)
    _draw_text(c, layout.page_label)
    _draw_text(c, layout.scene)
    pip = ctx.pip(row.pip_pose) if slot_pip else None
    if pip is not None:
        side = slot.height - 4
        c.drawImage(ImageReader(BytesIO(pip)), slot.x + (slot.width - side) / 2, slot.y + 2,
                    width=side, height=side, preserveAspectRatio=True, mask=None)
    _draw_text(c, layout.prompt_fr)
    _draw_text(c, layout.prompt_en, gray=.26)
    c.setLineWidth(1)
    c.setStrokeGray(.7)
    c.line(layout.footer.x, layout.footer.top - 1, layout.footer.right, layout.footer.top - 1)
    c.setFillGray(.28)
    c.setFont(ctx.regular, 8)
    note = note or WATERMARK + ("  |  PAGE PROVISOIRE" if row.gabarit == "provisoire" else
                        "  |  PARAMÈTRES PROVISOIRES NON VALIDÉS" if row.status != "C4_LOCKED" else "")
    c.drawString(layout.footer.x + 2, layout.footer.y + 15, note)
    c.drawRightString(layout.footer.right - 2, layout.footer.y + 15, f"{row.page}/{total}")
    board = layout.board
    c.setFillGray(1)
    c.setStrokeGray(.62)
    c.setLineWidth(1.3)
    c.roundRect(board.x, board.y, board.width, board.height, 16, stroke=1, fill=1)
    c.setFillGray(.28)
    c.setFont(ctx.bold, ctx.editorial.board_label_size)
    c.drawString(board.x + 22, board.top - 27, board_label)


# ---------------------------------------------------------------- gabarit CHEMIN

def _seed(ctx: Context, row: PageRow) -> int:
    return stable_seed("halloween_2026", f"halloween_2026-p{row.page:03d}", ctx.seed)


def _maze_activity(row: PageRow, ctx: Context) -> Activity:
    if row.params.get("legacy") == "maze":  # p.4 : activité canonique C4, identique à la démo
        spec = ActivitySpec(f"halloween_2026-p{row.page:03d}", row.page, "maze", (4, 5), row.title, (),
                            companion_name="Pip")
        act = generate(spec, _seed(ctx, row))
        return _activity(row, ctx, geometry=act.geometry, answer=act.answer)
    try:
        size, level = int(row.params["size"]), row.params["difficulty"]
    except (KeyError, ValueError) as exc:
        raise BookError(f"page {row.page} : paramètres labyrinthe size/difficulty requis") from exc
    v2 = generate_v2("maze_v2", f"syn-halloween-p{row.page:03d}", _seed(ctx, row) % (2 ** 63),
                     {"size": size, "difficulty": level})
    geo = {"size": v2.geometry["size"], "open_edges": [[list(a), list(b)] for a, b in v2.geometry["open_edges"]],
           "start": list(v2.geometry["start"]), "goal": list(v2.geometry["goal"])}
    return _activity(row, ctx, geometry=geo, answer={"path": [list(p) for p in v2.solution["path"]]})


def _dots_activity(row: PageRow, ctx: Context) -> Activity:
    kind = row.params.get("legacy")  # "moon8" : croissant C4 verrouillé
    if kind == "moon8":  # p.6 : croissant C4 à 8 points
        pts = [{"n": i, "x": round(x, 6), "y": round(y, 6)} for i, (x, y) in enumerate(_MOON_8, 1)]
        return _activity(row, ctx, geometry={"shape": "moon", "points": pts, "closed": True},
                         answer={"order": list(range(1, 9)), "close_to": 1})
    if row.params.get("shape") == "house15":  # silhouette provisoire de maison, 15 points
        pts = [{"n": i, "x": x, "y": y} for i, (x, y) in enumerate(HOUSE_15, 1)]
        return _activity(row, ctx, geometry={"shape": "house", "points": pts, "closed": True},
                         answer={"order": list(range(1, len(pts) + 1)), "close_to": 1})
    raise BookError(f"page {row.page} : forme de points à relier inconnue ({kind!r})")


def _lane_points(shape: str, x0: float, x1: float, y: float, h: float, n: int = 90) -> list[tuple[float, float]]:
    pts = []
    for i in range(n + 1):
        t = i / n
        if shape == "wave":
            v = math.sin(2 * math.pi * 2 * t)
        elif shape == "zigzag":
            v = 4 * abs((t * 5) % 1 - .5) - 1
        elif shape == "arch":
            v = 2 * math.sin(math.pi * t) - 1
        elif shape == "scallop":
            v = 2 * abs(math.sin(math.pi * 3 * t)) - 1
        else:
            raise BookError(f"forme de tracé inconnue : {shape}")
        pts.append((x0 + (x1 - x0) * t, y + v * h / 2))
    return pts


def _serpentine(board: Rect, rows: int = 4) -> list[tuple[float, float]]:
    left, right = board.x + 90, board.right - 90
    top, bottom = board.top - 80, board.y + 80
    gap = (top - bottom) / (rows - 1)
    r = gap / 2
    pts: list[tuple[float, float]] = []
    for i in range(rows):
        y = top - i * gap
        xs, xe = (left, right) if i % 2 == 0 else (right, left)
        pts += [(xs + (xe - xs) * k / 40, y) for k in range(41)]
        if i < rows - 1:
            sign = 1 if i % 2 == 0 else -1
            cx = xe
            pts += [(cx + sign * r * math.sin(a), y - r + r * math.cos(a))
                    for a in (math.pi * k / 24 for k in range(1, 24))]
    return pts


def _star(c: canvas.Canvas, x: float, y: float, r: float) -> None:
    p = c.beginPath()
    for i in range(10):
        rad = r if i % 2 == 0 else r * .45
        a = math.pi / 2 + i * math.pi / 5
        (p.moveTo if i == 0 else p.lineTo)(x + rad * math.cos(a), y + rad * math.sin(a))
    p.close()
    c.setFillGray(1)
    c.setStrokeGray(.1)
    c.setLineWidth(2.5)
    c.drawPath(p, fill=1, stroke=1)


def _house(c: canvas.Canvas, x: float, y: float, s: float) -> None:
    c.setFillGray(1)
    c.setStrokeGray(.1)
    c.setLineWidth(2.5)
    c.rect(x - s / 2, y - s / 2, s, s * .8, fill=1, stroke=1)
    p = c.beginPath()
    p.moveTo(x - s * .6, y + s * .3)
    p.lineTo(x, y + s * .85)
    p.lineTo(x + s * .6, y + s * .3)
    p.close()
    c.drawPath(p, fill=1, stroke=1)
    c.rect(x - s * .12, y - s / 2, s * .24, s * .4, fill=0, stroke=1)


def _trace_page(c: canvas.Canvas, row: PageRow, ctx: Context, board: Rect) -> None:
    if row.params.get("tracks") == "serpentine":
        pts = [_serpentine(board)]
    else:
        names = row.params["tracks"].split(",")
        top, bottom = board.top - 85, board.y + 60
        lane = (top - bottom) / len(names)
        pts = [_lane_points(n, board.x + 80, board.right - 80, top - lane * (i + .5), min(lane * .35, 60))
               for i, n in enumerate(names)]
    for line in pts:
        c.saveState()
        c.setStrokeGray(.15)
        c.setLineWidth(6)
        c.setLineCap(1)
        c.setDash(0.1, 11)
        p = c.beginPath()
        for i, (x, y) in enumerate(line):
            (p.moveTo if i == 0 else p.lineTo)(x, y)
        c.drawPath(p)
        c.restoreState()
        sx, sy = line[0]
        c.setFillGray(.1)
        c.circle(sx, sy, 9, fill=1, stroke=0)
        c.setFillGray(1)
        c.circle(sx, sy, 3.5, fill=1, stroke=0)
        ex, ey = line[-1]
        if row.params.get("end") == "house":
            _house(c, ex, ey - 4, 26)
        else:
            _star(c, ex, ey, 15)


def _logic_page(c: canvas.Canvas, row: PageRow, ctx: Context, board: Rect) -> None:
    perm = [int(v) for v in row.params["perm"].split(",")]
    web = int(row.params["web"])
    n = len(perm)
    if sorted(perm) != list(range(n)) or web not in perm:
        raise BookError(f"page {row.page} : permutation de chemins invalide")
    top, bottom = board.top - 85, board.y + 75
    xs = [board.x + 90 + i * (board.width - 180) / (n - 1) for i in range(n)]
    for i, end in enumerate(perm):
        c.setStrokeGray(.12)
        c.setLineWidth(4)
        c.setLineCap(1)
        p = c.beginPath()
        p.moveTo(xs[i], top)
        p.curveTo(xs[i], top - (top - bottom) * .55, xs[end], bottom + (top - bottom) * .55, xs[end], bottom)
        c.drawPath(p)
        c.setFillGray(1)
        c.circle(xs[i], top + 4, 15, fill=1, stroke=1)
        c.setFillGray(.05)
        c.setFont(ctx.bold, 14)
        c.drawCentredString(xs[i], top - 1, str(i + 1))
    for end, x in enumerate(xs):
        if end == web:
            c.setStrokeGray(.1)
            c.setLineWidth(1.6)
            for k in (1, 2, 3):
                p = c.beginPath()
                for j in range(9):
                    a = 2 * math.pi * j / 8
                    (p.moveTo if j == 0 else p.lineTo)(x + 9 * k * math.cos(a), bottom - 20 + 9 * k * math.sin(a))
                c.drawPath(p)
            for j in range(8):
                a = 2 * math.pi * j / 8
                c.line(x, bottom - 20, x + 27 * math.cos(a), bottom - 20 + 27 * math.sin(a))
        else:
            c.setFillGray(.88)
            c.setStrokeGray(.3)
            c.setLineWidth(1.5)
            c.circle(x, bottom - 16, 11, fill=1, stroke=1)


# ---------------------------------------------------------------- gabarit PROVISOIRE

def _provisional(c: canvas.Canvas, row: PageRow, ctx: Context, board: Rect) -> None:
    c.saveState()
    cx, cy = board.x + board.width / 2, board.y + board.height / 2
    c.translate(cx, cy)
    c.rotate(28)
    c.setFillGray(.9)
    c.setFont(ctx.bold, 64)
    c.drawCentredString(0, -20, "PROVISOIRE")
    c.restoreState()
    c.setFillGray(.15)
    c.setFont(ctx.bold, 18)
    c.drawCentredString(cx, board.top - 80, "PAGE PROVISOIRE — activité non produite")
    c.setFillGray(.3)
    c.setFont(ctx.regular, 12)
    step = ROADMAP_STEP.get(row.type, "étape à définir")
    c.drawCentredString(cx, board.top - 106, f"Type : {row.type}  |  gabarit prévu à l'étape {step}")
    if row.review:
        c.drawCentredString(cx, board.top - 126, "Paramètres éditoriaux à décider (HUMAN_REVIEW)")
    if row.type == "answers":
        entries = [r for r in ctx.rows if r.answer_page == row.page]
        c.setFillGray(.1)
        c.setFont(ctx.bold, 12)
        c.drawString(board.x + 60, board.top - 165, f"Emplacement de {len(entries)} corrigés :")
        c.setFont(ctx.regular, 12)
        for i, e in enumerate(entries):
            c.drawString(board.x + 70, board.top - 190 - i * 22, f"p.{e.page} — {e.title}")


def draw_page(c: canvas.Canvas, row: PageRow, ctx: Context) -> None:
    total = len(ctx.rows)
    if row.gabarit == "illustre":
        from lafractale.book.illustrated import draw_illustrated
        draw_illustrated(c, row, ctx)
        return
    if row.gabarit == "provisoire":
        fr = row.prompt_fr or "[provisoire] Texte à venir"
        en = row.prompt_en or "[provisional] Text to come"
        act = _activity(row, ctx, prompt_fr=fr, prompt_en=en)
        layout = _layout(act, ctx, total)
        _shell(c, layout, row, ctx, total, "GABARIT PROVISOIRE")
        _provisional(c, row, ctx, layout.board)
        return
    if row.type == "maze":
        act = _maze_activity(row, ctx)
    elif row.type == "connect_dots":
        act = _dots_activity(row, ctx)
    elif row.type in ("trace_paths", "path_logic"):
        act = _activity(row, ctx)
    else:
        raise BookError(f"page {row.page} : type {row.type!r} absent du gabarit chemin")
    layout = _layout(act, ctx, total)
    _shell(c, layout, row, ctx, total, BOARD_LABELS[row.type])
    if row.type == "maze":
        _maze(c, act, layout.board, False, ctx.bold, ctx.editorial)
    elif row.type == "connect_dots":
        _dots(c, act, layout.board, False, ctx.bold, ctx.editorial)
    elif row.type == "trace_paths":
        _trace_page(c, row, ctx, layout.board)
    else:
        _logic_page(c, row, ctx, layout.board)
