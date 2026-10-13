"""Tests fonctionnels du chemin livre : un aperçu de 56 pages, lisible et sans écrasement silencieux."""
import csv
from pathlib import Path

import fitz
import pytest

from lafractale.__main__ import main
from lafractale.book.pages import BookError, load_pages
from lafractale.book.preview import build_preview
from lafractale.editorial import _PROMPT_CONNECT_EN, _PROMPT_CONNECT_FR

BOOK = Path(__file__).resolve().parents[1] / "books/halloween_2026"
CHEMIN_PAGES = {4, 6, 9, 14, 17, 19, 22, 25, 29, 34, 38, 43}


@pytest.fixture(scope="module")
def preview(tmp_path_factory):
    out = tmp_path_factory.mktemp("preview") / "out"
    return out, build_preview(BOOK, out)


def test_pages_csv_is_the_scenario_b_book():
    rows = load_pages(BOOK / "pages.csv")
    assert [r.page for r in rows] == list(range(1, 57))
    assert {r.page for r in rows if r.gabarit == "chemin"} == CHEMIN_PAGES
    by = {r.page: r for r in rows}
    assert {p for p, r in by.items() if r.status == "C4_LOCKED"} == {4, 6, 20}
    assert (by[6].prompt_fr, by[6].prompt_en) == (_PROMPT_CONNECT_FR, _PROMPT_CONNECT_EN)
    assert by[20].title == "Retrouve les chapeaux jumeaux"
    # 46 activités bilingues importées, p.1-2 et p.49-56 sans consigne inventée
    assert sum(1 for r in rows if r.prompt_fr and r.prompt_en) == 46


def test_answer_slots_follow_canonical_split(tmp_path):
    rows = load_pages(BOOK / "pages.csv")
    for slot, expected in {49: 6, 50: 5, 51: 5, 52: 5, 53: 5, 54: 5}.items():
        assert sum(1 for r in rows if r.answer_page == slot) == expected
    bad = tmp_path / "pages.csv"
    lines = (BOOK / "pages.csv").read_text(encoding="utf-8").splitlines()
    bad.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
    with pytest.raises(BookError, match="exactement"):
        load_pages(bad)


def test_pdf_has_exactly_56_pages_with_text_and_watermark(preview):
    out, summary = preview
    doc = fitz.open(out / "book_preview.pdf")
    assert doc.page_count == 56
    assert summary["jouables"] == 12 and summary["provisoires"] == 44
    for n in (4, 14, 22, 43):
        text = doc[n - 1].get_text()
        assert "APERÇU — NON DESTINÉ À LA PUBLICATION" in text
        assert f"FICHE {n:02d}" in text
    assert "Find a path through the maze with Pip!" in doc[3].get_text()
    assert "PAGE PROVISOIRE" in doc[4].get_text()  # p.5 n'est pas présentée comme finalisée
    assert "p.4 — Aide Pip à trouver la sortie" in doc[48].get_text()  # emplacement du corrigé p.4


def test_previews_and_contact_sheet_exist(preview):
    out, _ = preview
    assert len(list((out / "pages").glob("page_*.png"))) == 56
    assert (out / "contact_sheet.png").stat().st_size > 10_000
    assert "HUMAN_REVIEW" in (out / "report.md").read_text(encoding="utf-8")


def test_no_silent_overwrite_and_deterministic(preview, tmp_path):
    out, _ = preview
    before = (out / "book_preview.pdf").read_bytes()
    with pytest.raises(BookError, match="--overwrite"):
        build_preview(BOOK, out)
    assert (out / "book_preview.pdf").read_bytes() == before
    again = tmp_path / "again"
    build_preview(BOOK, again)
    assert (again / "book_preview.pdf").read_bytes() == before
    build_preview(BOOK, out, overwrite=True)
    assert (out / "book_preview.pdf").read_bytes() == before


def test_cli_preview(tmp_path, capsys):
    assert main(["preview", str(BOOK), "--out", str(tmp_path / "cli")]) == 0
    assert "56 pages" in capsys.readouterr().out
    assert main(["preview", str(BOOK), "--out", str(tmp_path / "cli")]) == 2  # refus clair, rien d'écrasé


def test_maze_pages_have_a_unique_solution_path(preview):
    from lafractale.book.draw import Context, _maze_activity
    from lafractale.activities.engine import shortest_path
    rows = load_pages(BOOK / "pages.csv")
    book = {"trim": {"width_in": 8.5, "height_in": 11}}
    ctx = Context(BOOK.parents[1], book, rows, 2026)
    for r in rows:
        if r.type == "maze":
            act = _maze_activity(r, ctx)
            g = act.geometry
            assert shortest_path(g["size"], g["open_edges"]) == [list(p) for p in act.answer["path"]]
            assert len(g["open_edges"]) == g["size"] ** 2 - 1  # labyrinthe parfait : un seul chemin
