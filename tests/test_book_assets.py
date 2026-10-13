"""Chaîne hybride : import de PNG, composition illustrée, ASSET_MANQUANT, remplacement sans toucher aux exercices."""
import json
import shutil
from pathlib import Path

import fitz
import pytest
from PIL import Image, ImageDraw

from lafractale.__main__ import main
from lafractale.book.assets import import_png, load_manifest
from lafractale.book.pages import BookError
from lafractale.book.preview import build_preview

REPO = Path(__file__).resolve().parents[1]
PILOTS = (4, 5, 13, 20)


@pytest.fixture()
def repo(tmp_path):
    """Copie minimale du dépôt : le test écrit des assets sans toucher au vrai dossier."""
    (tmp_path / "books").mkdir()
    shutil.copytree(REPO / "books/halloween_2026", tmp_path / "books/halloween_2026",
                    ignore=shutil.ignore_patterns("dist", "assets_lock.json"))
    for sub in ("assets/illustrations/approvals.json", "assets/illustrations/halloween_2026/pip"):
        src, dst = REPO / sub, tmp_path / sub
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst) if src.is_dir() else shutil.copy(src, dst)
    return tmp_path


def fake_png(path: Path, size=(1254, 1254), *, transparent=False, shape="ellipse"):
    """Image synthétique de TEST (jamais livrée) : un trait noir sur fond blanc ou transparent."""
    img = Image.new("RGBA" if transparent else "RGB", size, (255, 255, 255, 0) if transparent else "white")
    d = ImageDraw.Draw(img)
    m = min(size) // 5
    (d.ellipse if shape == "ellipse" else d.rectangle)((m, m, size[0] - m, size[1] - m), outline="black", width=14)
    img.save(path)
    return path


def manifest(repo):
    return load_manifest(repo / "books/halloween_2026/assets_manifest.yaml", repo)


def test_missing_assets_are_reported_not_faked(repo, tmp_path):
    out = tmp_path / "out"
    s = build_preview(repo / "books/halloween_2026", out, only=PILOTS, repo_root=repo)
    missing = {i["asset"] for i in s["assets"] if i["status"] == "ASSET_MANQUANT"}
    assert missing == {k for k, a in manifest(repo).assets.items() if not a.fixed}
    assert "ASSET_MANQUANT" in (out / "report.md").read_text(encoding="utf-8")
    assert s["reponses_python"] == {5: {"cat": 3, "bat": 4}}  # l'exercice existe sans aucune image


def test_import_normalizes_object_and_scene(repo):
    m = manifest(repo)
    r = import_png(m, "sprite_chat", fake_png(repo / "a.png"))  # fond blanc opaque -> transparent
    img = Image.open(m.assets["sprite_chat"].path)
    assert r["version"] == 1 and img.mode == "RGBA" and img.getchannel("A").getextrema()[0] == 0
    import_png(m, "p13_foret_nuit", fake_png(repo / "b.png", (2200, 1500)))
    assert Image.open(m.assets["p13_foret_nuit"].path).mode == "L"
    import_png(m, "sprite_chauve_souris", fake_png(repo / "c.png", transparent=True))  # déjà transparent
    assert Image.open(m.assets["sprite_chauve_souris"].path).mode == "RGBA"


def test_import_keeps_enclosed_white_opaque(repo):
    """Le blanc enfermé dans le trait (ventre du chat) reste opaque : le décor ne doit pas transparaître."""
    m = manifest(repo)
    import_png(m, "sprite_chat", fake_png(repo / "a.png"))
    img = Image.open(m.assets["sprite_chat"].path)
    assert img.getchannel("A").getpixel((img.width // 2, img.height // 2)) == 255
    assert img.getchannel("A").getpixel((0, 0)) == 0


def test_import_refusals(repo):
    m = manifest(repo)
    with pytest.raises(BookError, match="trop petit"):
        import_png(m, "p13_foret_nuit", fake_png(repo / "s.png", (300, 200)))
    with pytest.raises(BookError, match="inconnu"):
        import_png(m, "nimporte_quoi", fake_png(repo / "s.png"))
    with pytest.raises(BookError, match="fixe"):
        import_png(m, "pip-indication-v1", fake_png(repo / "s.png"))
    Image.new("RGB", (1500, 1500)).save(repo / "x.jpg", "JPEG")
    with pytest.raises(BookError, match="PNG"):
        import_png(m, "sprite_chat", repo / "x.jpg")


def test_replacing_an_illustration_archives_and_keeps_exercise_unchanged(repo, tmp_path):
    m = manifest(repo)
    for aid, size in (("sprite_chat", (1254, 1254)), ("sprite_chauve_souris", (1254, 1254))):
        import_png(m, aid, fake_png(repo / f"{aid}.png", size))
    book = repo / "books/halloween_2026"
    s1 = build_preview(book, tmp_path / "v1", only=(5,), repo_root=repo)
    r = import_png(m, "sprite_chat", fake_png(repo / "new.png", shape="rect"))  # nouvelle version
    assert r["version"] == 2
    assert (m.assets["sprite_chat"].path.parent / "archive/sprite_chat.v1.png").is_file()
    s2 = build_preview(book, tmp_path / "v2", only=(5,), repo_root=repo)
    assert s1["reponses_python"] == s2["reponses_python"] == {5: {"cat": 3, "bat": 4}}
    lock = json.loads((book / "assets_lock.json").read_text(encoding="utf-8"))
    assert lock["sprite_chat"]["version"] == 2


def test_full_pilots_render_without_missing_and_text_is_unchanged(repo, tmp_path):
    m = manifest(repo)
    for a in m.assets.values():
        if not a.fixed:
            big = a.size_px or (1254, 1254)
            import_png(m, a.id, fake_png(repo / f"{a.id}.png", big))
    out = tmp_path / "pilots"
    s = build_preview(repo / "books/halloween_2026", out, only=PILOTS, repo_root=repo)
    assert s["assets"] == []
    doc = fitz.open(out / "book_preview.pdf")
    assert doc.page_count == 4
    # contenus C4 canoniques : consignes inchangées quel que soit l'habillage
    assert "Aide Pip à trouver la sortie" in doc[0].get_text()
    assert "Traverse le labyrinthe avec Pip !" in doc[0].get_text()
    assert "Retrouve les chapeaux jumeaux" in doc[3].get_text() and "Match each hat to its twin." in doc[3].get_text()
    assert sorted(p.name for p in (out / "pages").glob("*.png")) == [f"page_{n:03d}.png" for n in PILOTS]


def test_decor_cannot_cover_the_exercise(repo, tmp_path):
    import yaml
    path = repo / "books/halloween_2026/assets_manifest.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["pages"][4]["decor"].append({"asset": "p20_lune_deco", "zone": "board_left", "size_pt": 900})
    # la zone board_left est bornée par le labyrinthe : un décor trop grand est réduit à la zone, jamais au-dessus du jeu
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    m = manifest(repo)
    import_png(m, "p20_lune_deco", fake_png(repo / "m.png"))
    out = build_preview(repo / "books/halloween_2026", tmp_path / "o", only=(4,), repo_root=repo)
    assert out["pages"] == 1  # rendu valide : le décor reste hors du labyrinthe
    data["pages"][4]["decor"][-1]["zone"] = "inconnue"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(BookError, match="zone de décor"):
        build_preview(repo / "books/halloween_2026", tmp_path / "o2", only=(4,), repo_root=repo)


def test_cli_assets_and_pilots(repo, tmp_path, capsys):
    book = str(repo / "books/halloween_2026")
    assert main(["assets", "list", "--book-dir", book]) == 0
    assert "ASSET_MANQUANT" in capsys.readouterr().out
    assert main(["assets", "import", str(fake_png(repo / "sprite_chat.png")), "--book-dir", book]) == 0
    assert "IMPORTÉ sprite_chat v1" in capsys.readouterr().out
    assert main(["pilots", book, "--out", str(tmp_path / "p")]) == 0
    assert main(["pilots", book, "--out", str(tmp_path / "p")]) == 2  # pas d'écrasement silencieux
