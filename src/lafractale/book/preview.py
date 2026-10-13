"""Aperçu du livre : PDF de 56 pages, aperçus PNG, planche-contact et rapport."""
from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF
import yaml
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas

from lafractale.book.draw import WATERMARK, Context, draw_page
from lafractale.book.pages import BookError, EXPECTED_PAGES, load_pages

PDF_NAME, SHEET_NAME, REPORT_NAME, PAGES_DIR = "book_preview.pdf", "contact_sheet.png", "report.md", "pages"
GREEN, ORANGE, BLUE, PURPLE = (46, 140, 70), (230, 140, 20), (40, 90, 200), (140, 60, 170)


def _targets(out: Path, pages) -> list[Path]:
    return [out / PDF_NAME, out / SHEET_NAME, out / REPORT_NAME] + \
           [out / PAGES_DIR / f"page_{n:03d}.png" for n in pages]


def build_preview(book_dir: Path, out: Path, *, seed: int = 2026, overwrite: bool = False,
                  repo_root: Path | None = None, only: tuple[int, ...] | None = None) -> dict:
    book_dir = Path(book_dir)
    repo_root = Path(repo_root) if repo_root else book_dir.resolve().parents[1]
    existing = [p for p in _targets(out, only or range(1, EXPECTED_PAGES + 1)) if p.exists()]
    if existing and not overwrite:
        raise BookError(f"{out} contient déjà un aperçu ({existing[0].name}…). Relancer avec --overwrite "
                        "pour le remplacer, ou choisir un autre dossier --out.")
    book = yaml.safe_load((book_dir / "book.yaml").read_text(encoding="utf-8"))
    rows = load_pages(book_dir / "pages.csv")
    ctx = Context(repo_root, book, rows, seed)
    drawn = [r for r in rows if only is None or r.page in only]
    if only is not None and len(drawn) != len(set(only)):
        raise BookError(f"pages demandées inconnues : {sorted(set(only) - {r.page for r in drawn})}")
    width, height = book["trim"]["width_in"] * 72, book["trim"]["height_in"] * 72
    out.mkdir(parents=True, exist_ok=True)
    (out / PAGES_DIR).mkdir(exist_ok=True)

    pdf_tmp = out / (PDF_NAME + ".tmp")
    c = canvas.Canvas(str(pdf_tmp), pagesize=(width, height), invariant=1, pageCompression=1,
                      initialFontName=ctx.regular)
    c.setTitle(f"APERÇU — {book['title']}")
    c.setAuthor(book["publisher"])
    c.setSubject(WATERMARK)
    try:
        for row in drawn:
            draw_page(c, row, ctx)
            c.showPage()
        c.save()
        doc = fitz.open(pdf_tmp)
        expected = len(drawn)
        if doc.page_count != expected or (only is None and expected != EXPECTED_PAGES):
            raise BookError(f"le PDF compte {doc.page_count} pages au lieu de {expected}")
        for row, page in zip(drawn, doc):
            page.get_pixmap(matrix=fitz.Matrix(150 / 72, 150 / 72) if only else fitz.Matrix(100 / 72, 100 / 72),
                            colorspace=fitz.csGRAY).save(out / PAGES_DIR / f"page_{row.page:03d}.png")
        sheet = _contact_sheet(doc, drawn, ctx)
        doc.close()
        sheet.save(out / SHEET_NAME)
        pdf_tmp.replace(out / PDF_NAME)
    finally:
        pdf_tmp.unlink(missing_ok=True)
    summary = _summary(drawn)
    summary["anglais_corps_10"] = ctx.small_en
    summary["assets"] = ctx.store.issues
    summary["reponses_python"] = ctx.answers
    (out / REPORT_NAME).write_text(_report(drawn, summary, book), encoding="utf-8")
    return summary


def _kind(row) -> str:
    if row.gabarit == "illustre":
        return "illustre"
    return "provisoire" if row.gabarit == "provisoire" else ("c4" if row.status == "C4_LOCKED" else "jouable")


def _summary(rows) -> dict:
    kinds = [_kind(r) for r in rows]
    return {"pages": len(rows), "jouables": kinds.count("jouable") + kinds.count("c4"),
            "illustrees": kinds.count("illustre"),
            "c4_verrouillees": kinds.count("c4"), "provisoires": kinds.count("provisoire"),
            "human_review": [r.page for r in rows if r.review]}


def _contact_sheet(doc, rows, ctx) -> Image.Image:
    cols, thumb_w, gap, head = 8, 190, 14, 64
    zoom = thumb_w / doc[0].rect.width
    thumb_h = round(doc[0].rect.height * zoom)
    nrows = -(-len(rows) // cols)
    sheet = Image.new("RGB", (cols * (thumb_w + gap) + gap, head + nrows * (thumb_h + gap + 18) + gap), "white")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype(str(Path(__import__("os").environ.get(
            "LAFRACTALE_FONT_BOLD_PATH", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))), 15)
    except OSError:
        font = ImageFont.load_default()
    draw.text((gap, 10), f"{WATERMARK} — planche-contact des {len(rows)} pages", fill="black", font=font)
    for x, (color, label) in zip((gap, 230, 480, 760), ((GREEN, "page jouable"), (BLUE, "page C4 verrouillée"),
                                                          (PURPLE, "page pilote illustrée"),
                                                          (ORANGE, "page provisoire (gabarit)"))):
        draw.rectangle((x, 38, x + 14, 52), fill=color)
        draw.text((x + 20, 36), label, fill="black", font=font)
    for i, (row, page) in enumerate(zip(rows, doc)):
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csRGB)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        x = gap + (i % cols) * (thumb_w + gap)
        y = head + (i // cols) * (thumb_h + gap + 18)
        sheet.paste(img, (x, y))
        kind = _kind(row)
        draw.rectangle((x - 2, y - 2, x + img.width + 1, y + img.height + 1), outline={
            "jouable": GREEN, "c4": BLUE, "illustre": PURPLE, "provisoire": ORANGE}[kind], width=3)
        draw.text((x, y + img.height + 3), f"p.{row.page}  {row.type[:12]}", fill="black", font=font)
    return sheet


def _report(rows, s, book) -> str:
    lines = [f"# Aperçu — {book['title']}", "", f"**{WATERMARK}.** Verrous KDP et statuts éditoriaux inchangés.", "",
             f"- Pages : {s['pages']} ; jouables : {s['jouables']} (dont {s['c4_verrouillees']} C4 verrouillées) ; "
             f"pilotes illustrés : {s['illustrees']} ; provisoires : {s['provisoires']}",
             f"- Pages dont les paramètres relèvent d'un arbitrage humain (HUMAN_REVIEW) : {s['human_review']}",
             f"- Consigne anglaise composée en corps 10 (trop longue pour le corps 12) : {s['anglais_corps_10']}", "",
             ]
    lines += ["", "## Assets graphiques", ""]
    lines += ([f"- p.{i['page']} — `{i['asset']}` ({i['role']}) : **{i['status']}**" for i in s["assets"]]
              or ["- Tous les assets utilisés sont présents."])
    if s["reponses_python"]:
        lines += ["", "Réponses calculées par Python (jamais par une image) : "
                  + "; ".join(f"p.{p} {a}" for p, a in s["reponses_python"].items())]
    lines += ["", "| Page | Type | Gabarit | Statut | Revue |", "|---:|---|---|---|---|"]
    lines += [f"| {r.page} | {r.type} | {r.gabarit} | {r.status} | {r.review} |" for r in rows]
    return "\n".join(lines) + "\n"
