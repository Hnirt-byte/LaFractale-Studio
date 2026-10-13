"""Génère books/halloween_2026/pages.csv depuis le scénario B (import unique, puis le CSV fait foi)."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
B3A3 = ROOT / "docs/editorial/b3a/b3a3"
OUT = ROOT / "books/halloween_2026/pages.csv"

CHEMIN = {"maze", "connect_dots", "trace_paths", "path_logic"}
C4_LOCKED = {4, 6, 20}
HUMAN_REVIEW = {17, 22, 37, 43, 44, 45, 46, 48}
# Paramètres PROVISOIRES (non validés) des pages du gabarit CHEMIN.
PARAMS = {
    4: "legacy=maze", 6: "legacy=moon8", 17: "shape=house15",
    14: "size=6;difficulty=easy", 25: "size=6;difficulty=medium",
    34: "size=7;difficulty=medium", 43: "size=8;difficulty=hard",
    9: "tracks=wave,zigzag,arch", 19: "tracks=zigzag,scallop,wave",
    29: "tracks=wave,arch,zigzag,scallop", 38: "tracks=serpentine;end=house",
    22: "perm=2,0,3,1;web=0",
}
POSE = {"front_matter": "accueil", "path_logic": "reflexion", "answers": "reflexion",
        "glossary typographique": "reflexion", "diploma + back_matter": "felicitations"}
FIELDS = ["page", "type", "gabarit", "title", "prompt_fr", "prompt_en", "answer_page",
          "params", "pip_pose", "status", "review"]


def main() -> int:
    plan = {int(r["final_page"]): r for r in csv.DictReader(open(B3A3 / "01_chemin_de_fer_scenario_B_56_pages.csv", encoding="utf-8-sig"))}
    texts = {int(r["final_page"]): r for r in csv.DictReader(open(B3A3 / "03_consignes_bilingues_finales_46_pages_scenario_B.csv", encoding="utf-8-sig"))}
    rows = []
    for page in range(1, 57):
        p, t = plan[page], texts.get(page)
        kind = p["final_type"]
        rows.append({
            "page": page, "type": kind,
            "gabarit": "chemin" if kind in CHEMIN else "provisoire",
            "title": (t or p)["final_title"],
            "prompt_fr": t["final_fr"] if t else "", "prompt_en": t["final_en"] if t else "",
            "answer_page": t["answer_page"] if t else "",
            "params": PARAMS.get(page, ""),
            "pip_pose": POSE.get(kind, "indication" if kind in CHEMIN else "encouragement"),
            "status": "C4_LOCKED" if page in C4_LOCKED else "PROVISOIRE_NON_VALIDE",
            "review": "HUMAN_REVIEW" if page in HUMAN_REVIEW else "",
        })
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"{OUT} : {len(rows)} pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
