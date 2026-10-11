"""Pure, immutable composition of a technical worksheet, independent from PDF drawing.

The composition carries explicit geometrical boxes and full, non-truncated text.
Artwork remains absent until a character-specific print variant is approved.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Callable

from lafractale.activities.models import Activity
from lafractale.editorial import EditorialSpec


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def top(self) -> float:
        return self.y + self.height

    def contains(self, other: "Rect", *, tolerance: float = 0.0001) -> bool:
        return (self.x - tolerance <= other.x and self.y - tolerance <= other.y
                and other.right <= self.right + tolerance and other.top <= self.top + tolerance)

    def overlaps(self, other: "Rect") -> bool:
        return (self.x < other.right and other.x < self.right
                and self.y < other.top and other.y < self.top)


@dataclass(frozen=True)
class TextBlock:
    region: Rect
    lines: tuple[str, ...]
    font: str
    size: int
    leading: int


@dataclass(frozen=True)
class PageComposition:
    page: Rect
    safe: Rect
    header: Rect
    scene: TextBlock
    prompt_fr: TextBlock
    prompt_en: TextBlock
    board: Rect
    companion_slot: Rect
    footer: Rect
    title: TextBlock
    page_label: TextBlock
    answer_key: bool

    def regions(self) -> dict[str, Rect]:
        return {"header": self.header, "scene": self.scene.region,
                "prompt_fr": self.prompt_fr.region, "prompt_en": self.prompt_en.region,
                "board": self.board, "companion_slot": self.companion_slot, "footer": self.footer}


TextWidth = Callable[[str, str, int], float]


def _wrap(text: str, *, width: float, font: str, size: int,
          max_lines: int, text_width: TextWidth) -> tuple[str, ...]:
    if not isinstance(text, str) or not text.strip() or "\x00" in text:
        raise ValueError("Texte vide ou invalide")
    if "\r" in text or "\n" in text:
        raise ValueError("Retours à la ligne explicites interdits dans une fiche")
    lines: list[str] = []
    current = ""
    for word in text.split():
        if text_width(word, font, size) > width:
            raise ValueError(f"Mot trop long pour la zone de texte : {word}")
        next_line = f"{current} {word}" if current else word
        if current and text_width(next_line, font, size) > width:
            lines.append(current)
            current = word
        else:
            current = next_line
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        raise ValueError(f"Texte débordant ({len(lines)} lignes, maximum {max_lines}) : {text}")
    return tuple(lines)


def _block(region: Rect, text: str, *, font: str, size: int, leading: int,
           max_lines: int, text_width: TextWidth) -> TextBlock:
    lines = _wrap(text, width=region.width, font=font, size=size,
                  max_lines=max_lines, text_width=text_width)
    if len(lines) * leading > region.height + 0.0001:
        raise ValueError("Texte plus haut que sa zone")
    return TextBlock(region, lines, font, size, leading)


def validate_composition(layout: PageComposition, *, text_width: TextWidth) -> None:
    for name, region in {"page": layout.page, "safe": layout.safe, **layout.regions()}.items():
        if not all(isfinite(x) for x in (region.x, region.y, region.width, region.height)):
            raise ValueError(f"Zone non finie : {name}")
        if region.width <= 0 or region.height <= 0:
            raise ValueError(f"Zone vide : {name}")
        if name not in {"page", "safe"} and not layout.safe.contains(region):
            raise ValueError(f"Zone hors marge de sécurité : {name}")
    if not layout.page.contains(layout.safe):
        raise ValueError("Zone de sécurité hors page")
    regions = layout.regions()
    for name, rect in regions.items():
        for other_name, other in regions.items():
            if name < other_name and rect.overlaps(other):
                raise ValueError(f"Zones qui se chevauchent : {name}/{other_name}")
    if not layout.header.contains(layout.title.region) or not layout.header.contains(layout.page_label.region):
        raise ValueError("Titre ou pagination hors en-tête")
    if layout.title.region.overlaps(layout.page_label.region):
        raise ValueError("Titre et numéro de page se chevauchent")
    for block in (layout.title, layout.page_label, layout.scene, layout.prompt_fr, layout.prompt_en):
        if len(block.lines) * block.leading > block.region.height:
            raise ValueError("Texte dépassant sa hauteur")
        if any(text_width(line, block.font, block.size) > block.region.width + .001 for line in block.lines):
            raise ValueError("Texte dépassant sa largeur")


def compose_page(activity: Activity, book: dict, *, index: int, count: int,
                 answer_key: bool, regular: str, bold: str,
                 text_width: TextWidth,
                 editorial: EditorialSpec | None = None) -> PageComposition:
    """Produce the same layout for the same validated activity and trim size.

    Explicitly refuse unsupported trim sizes rather than silently scaling text
    below the readability target. Geometric fit is not a KDP certification.
    """
    width = book["trim"]["width_in"] * 72
    height = book["trim"]["height_in"] * 72
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and isfinite(v) for v in (width, height)):
        raise ValueError("Format de page invalide")
    if width < 550 or height < 740:
        raise ValueError("Gabarit graphique V0.2-B limité au format 8.5 x 11 pouces ou plus")
    margin = max(46, min(54, width * .085))
    content_width = width - margin * 2
    page = Rect(0, 0, width, height)
    safe = Rect(margin, margin, content_width, height - 2 * margin)
    header = Rect(margin, height - margin - 72, content_width, 72)
    scene_area = Rect(margin + 14, header.y - 51, content_width - 166, 41)
    companion_slot = Rect(header.right - 136, scene_area.y, 122, scene_area.height)
    fr_area = Rect(margin + 14, scene_area.y - 37, content_width - 28, 32)
    en_area = Rect(margin + 14, fr_area.y - 29, content_width - 28, 23)
    footer = Rect(margin, margin + 1, content_width, 38)
    board = Rect(margin, margin + 91, content_width, en_area.y - 15 - (margin + 91))
    if board.height < 275:
        raise ValueError("Zone d'activité insuffisante")

    title_text = ("CORRIGÉ" if answer_key else
                  f"Je joue avec {activity.companion_name} !" if activity.companion_name else
                  "Je joue et j'apprends !")
    title_area = Rect(header.x + 17, header.y + 18, header.width - 160, 38)
    label_area = Rect(header.right - 137, header.y + 21, 121, 25)
    title = _block(title_area, title_text, font=bold, size=19, leading=24,
                   max_lines=1, text_width=text_width)
    label = _block(label_area, f"FICHE {activity.page:02d}", font=bold, size=12, leading=18,
                   max_lines=1, text_width=text_width)
    scene = _block(scene_area, activity.scene, font=bold, size=15, leading=19,
                   max_lines=2, text_width=text_width)
    prompt_fr = _block(fr_area, activity.prompt_fr, font=regular, size=12, leading=16,
                       max_lines=2, text_width=text_width)
    en_size = editorial.prompt_en_size if editorial is not None else 10
    en_leading = editorial.prompt_en_leading if editorial is not None else 14
    prompt_en = _block(en_area, activity.prompt_en, font=regular, size=en_size, leading=en_leading,
                       max_lines=1, text_width=text_width)
    layout = PageComposition(page, safe, header, scene, prompt_fr, prompt_en,
                             board, companion_slot, footer, title, label, answer_key)
    validate_composition(layout, text_width=text_width)
    return layout
