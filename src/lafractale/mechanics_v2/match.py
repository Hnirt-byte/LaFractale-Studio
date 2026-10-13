"""match_v2 — pairs of synthetic geometric symbols to link, with a unique, observable correspondence.

Everything is integer or exact rational arithmetic: no float, no trigonometry at run time (the symbol
tables below are literal integer vertex lists in a local 100 × 100 frame, counter-clockwise, first
vertex = smallest (y, x)). Nothing here is editorial: seasonal families (``hats``, ``gifts``), real
pictograms and assets are not part of the vocabulary and are refused.

Parameters (closed set): ``pairs`` 3..6, ``relation`` ``twin`` | ``count``, ``family`` ``polygon`` |
``star`` | ``mixed``. ``star`` has a reservoir of 3 classes (pairs ≤ 3); ``count`` is reserved to
``polygon``. Thirteen combinations are valid.

Relations (decided from OBSERVABLE properties recomputed from the published coordinates; labels are
informative and never take part in the decision):

* ``twin``  — the right symbol has exactly the same vertex list as the left one in the LOCAL frame
  (exact equality of the normalised list, not congruence by rotation or translation).
* ``count`` — the right symbol is a pattern of k dots, the left symbol a convex polygon with k vertices.

Criteria (all exact, none is ever relaxed):

M1  ``left_to_right`` is a permutation of 0..N−1 that is NOT the identity (fixed points are allowed).
M2  within a column, symbols have different (vertex count, re-entrant vertex count) signatures.
M3  bilateral uniqueness: each left symbol is in relation with exactly one right symbol and each right
    symbol with exactly one left symbol, and that is the pairing of the solution.
M4  well-formed symbols: integer, counter-clockwise, simple, strictly convex for ``polygon`` or with
    exactly k re-entrant vertices for ``star``, inside the 100 × 100 frame, equal to the closed table.
M5  area / bounding-box ratio: two left symbols differ by at least ``AREA_RATIO_GAP_MIN_PPM`` millionths.
    A purely geometric INDICATOR: it does not guarantee that a child tells two symbols apart.
M6  no three links are concurrent at an interior point (links join the left and right anchors of the rows).
M7  layout: the REAL bounding box of every placed symbol lies inside the grid margins, boxes of a column are
    at least ``MIN_BOX_GAP`` apart, and the anchors are clear of the symbols.
M8  labels are consistent with the signatures recomputed from the coordinates.
M9  ``count``: dot patterns are the closed tables, in the frame, at least 30 apart, with distinct counts.

``AREA_RATIO_GAP_MIN_PPM`` was fixed from the tables before the validation benchmark: the smallest gap
between the nine classes is 3/364 ≈ 0.00824 (hexagon 0.75 vs heptagon 0.7418), rounded down to a
multiple of 0.005. It is therefore a weak indicator; the primary guarantee is the signature of M2.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any, Mapping

from lafractale.mechanics_v2.core import (
    DetRng, V2Activity, V2Error, build_activity, check_activity_id, check_params, check_seed,
    bounded_repr,
)

MATCH_V2_MECHANIC = "match_v2"
MATCH_V2_VERSION = "b3b3b3-match-v2-1.0"
PAIRS_MIN, PAIRS_MAX = 3, 6
RELATIONS = ("twin", "count")
FAMILIES = ("polygon", "star", "mixed")
MAX_ATTEMPTS = 2000

GRID = 1000
MARGIN = 50
FRAME = 100  # local frame of a symbol: [0, 100] × [0, 100]
LEFT_X, RIGHT_X = 100, 800  # world x of the local origin of each column
LEFT_ANCHOR_X, RIGHT_ANCHOR_X = 260, 740
MIN_BOX_GAP = 30
ANCHOR_CLEARANCE = 20
MIN_DOT_SEP_SQ = 900
DOT_BORDER = 15
AREA_RATIO_GAP_MIN_PPM = 5000

POLYGONS: Mapping[int, tuple[tuple[int, int], ...]] = {
    3: ((8, 26), (92, 26), (50, 98)),
    4: ((16, 16), (84, 16), (84, 84), (16, 84)),
    5: ((22, 11), (78, 11), (96, 65), (50, 98), (4, 65)),
    6: ((50, 2), (92, 26), (92, 74), (50, 98), (8, 74), (8, 26)),
    7: ((29, 7), (71, 7), (97, 39), (88, 80), (50, 98), (12, 80), (3, 39)),
    8: ((50, 2), (84, 16), (98, 50), (84, 84), (50, 98), (16, 84), (2, 50), (16, 16)),
}
STARS: Mapping[int, tuple[tuple[int, int], ...]] = {
    4: ((50, 2), (61, 39), (98, 50), (61, 61), (50, 98), (39, 61), (2, 50), (39, 39)),
    5: ((22, 11), (50, 34), (78, 11), (65, 45), (96, 65), (59, 63), (50, 98), (41, 63), (4, 65), (35, 45)),
    6: ((50, 2), (58, 36), (92, 26), (66, 50), (92, 74), (58, 64), (50, 98), (42, 64), (8, 74), (34, 50), (8, 26), (42, 36)),
}
DOTS: Mapping[int, tuple[tuple[int, int], ...]] = {
    3: ((50, 25), (25, 70), (75, 70)),
    4: ((25, 25), (75, 25), (25, 75), (75, 75)),
    5: ((25, 25), (75, 25), (50, 50), (25, 75), (75, 75)),
    6: ((25, 20), (75, 20), (25, 50), (75, 50), (25, 80), (75, 80)),
    7: ((50, 50), (50, 20), (76, 35), (76, 65), (50, 80), (24, 65), (24, 35)),
    8: ((20, 20), (50, 20), (80, 20), (20, 50), (80, 50), (20, 80), (50, 80), (80, 80)),
}

Symbol = tuple[str, int]  # ("polygon", n) or ("star", k)


def _table(symbol: Symbol) -> tuple[tuple[int, int], ...]:
    return (POLYGONS if symbol[0] == "polygon" else STARS)[symbol[1]]


def label(symbol: Symbol) -> str:
    return f"{symbol[0]}-{symbol[1]}"


def reservoir(family: str) -> list[Symbol]:
    polygons: list[Symbol] = [("polygon", n) for n in sorted(POLYGONS)]
    stars: list[Symbol] = [("star", k) for k in sorted(STARS)]
    return polygons if family == "polygon" else stars if family == "star" else polygons + stars


def area_ratio(symbol: Symbol) -> Fraction:
    """Polygon area over bounding-box area, exact."""
    vs = _table(symbol)
    twice = sum(vs[i][0] * vs[(i + 1) % len(vs)][1] - vs[(i + 1) % len(vs)][0] * vs[i][1] for i in range(len(vs)))
    width = max(v[0] for v in vs) - min(v[0] for v in vs)
    height = max(v[1] for v in vs) - min(v[1] for v in vs)
    return Fraction(abs(twice), 2 * width * height)


def row_centres(pairs: int) -> list[int]:
    return [MARGIN + (2 * i + 1) * (GRID - 2 * MARGIN) // (2 * pairs) for i in range(pairs)]


def check_combination(pairs: int, relation: str, family: str) -> None:
    if relation == "count" and family != "polygon":
        raise V2Error("BAD_COMBINATION", "la relation count est réservée à la famille polygon")
    if pairs > len(reservoir(family)):
        raise V2Error("BAD_COMBINATION", f"la famille {family} n'offre que {len(reservoir(family))} classes pour {pairs} paires")


# ---- parameters ------------------------------------------------------------------------------------
def _pairs(value: Any) -> int:
    if type(value) is not int or not PAIRS_MIN <= value <= PAIRS_MAX:
        raise V2Error("BAD_PAIRS", f"nombre de paires entier attendu entre {PAIRS_MIN} et {PAIRS_MAX} inclus, reçu {bounded_repr(value)}")
    return value


def _relation(value: Any) -> str:
    if type(value) is not str or value not in RELATIONS:
        raise V2Error("BAD_RELATION", f"relation attendue parmi {RELATIONS}, reçu {bounded_repr(value)}")
    return value


def _family(value: Any) -> str:
    if type(value) is not str or value not in FAMILIES:
        raise V2Error("BAD_FAMILY", f"famille attendue parmi {FAMILIES}, reçu {bounded_repr(value)}")
    return value


PARAM_SPEC = {"pairs": _pairs, "relation": _relation, "family": _family}


# ---- the generator's own acceptance tests -------------------------------------------------------------
def gaps_ok(classes: list[Symbol]) -> tuple[bool, int]:
    """M5 on the left classes: (satisfied, smallest gap in millionths, rounded down)."""
    ratios = [area_ratio(c) for c in classes]
    smallest = min(abs(ratios[i] - ratios[j]) for i in range(len(ratios)) for j in range(i + 1, len(ratios)))
    ppm = smallest.numerator * 1_000_000 // smallest.denominator
    return smallest * 1_000_000 >= AREA_RATIO_GAP_MIN_PPM, ppm


def concurrent_links(permutation: list[int]) -> bool:
    """True when three links meet at one interior point (exact: equal rational parameter along link i)."""
    ys = row_centres(len(permutation))
    ends = [(ys[i], ys[permutation[i]] - ys[i]) for i in range(len(permutation))]  # start, rise
    count = len(permutation)

    def parameter(i: int, k: int) -> Fraction | None:
        slope_gap = ends[i][1] - ends[k][1]
        if slope_gap == 0:
            return None
        t = Fraction(ends[k][0] - ends[i][0], slope_gap)
        return t if 0 < t < 1 else None

    for i in range(count):
        seen: dict[Fraction, int] = {}
        for k in range(count):
            if k != i:
                t = parameter(i, k)
                if t is not None:
                    seen[t] = seen.get(t, 0) + 1
        if any(n >= 2 for n in seen.values()):
            return True
    return False


def inversions(permutation: list[int]) -> int:
    return sum(1 for i in range(len(permutation)) for k in range(i + 1, len(permutation)) if permutation[i] > permutation[k])


def _place(vertices: tuple[tuple[int, int], ...]) -> list[list[int]]:
    return [[x, y] for x, y in vertices]


def generate_match_v2(activity_id: Any, seed: Any, params: Mapping[str, Any]) -> V2Activity:
    """Deterministic bounded search; raises ``V2Error`` (never relaxes a criterion)."""
    activity_id, seed = check_activity_id(activity_id), check_seed(seed)
    values = check_params(params, PARAM_SPEC)
    pairs, relation, family = values["pairs"], values["relation"], values["family"]
    check_combination(pairs, relation, family)
    pool = reservoir(family)
    ys = row_centres(pairs)
    identity = list(range(pairs))
    for attempt in range(MAX_ATTEMPTS):
        rng = DetRng(f"lafractale-mechanics-v2|{MATCH_V2_MECHANIC}|{activity_id}|{seed}|{pairs}|{relation}|{family}|{attempt}")
        classes = list(pool)
        rng.shuffle(classes)
        classes = classes[:pairs]  # left column, top to bottom
        permutation = list(range(pairs))  # permutation[i] = right row of the partner of left row i
        rng.shuffle(permutation)
        if permutation == identity:
            continue
        satisfied, gap_ppm = gaps_ok(classes)
        if not satisfied or concurrent_links(permutation):
            continue
        right: list[dict[str, Any]] = [{} for _ in range(pairs)]
        for i, symbol in enumerate(classes):
            j = permutation[i]
            entry: dict[str, Any] = {"row": j, "origin": [RIGHT_X, ys[j] - FRAME // 2]}
            if relation == "twin":
                entry.update(label=label(symbol), vertices=_place(_table(symbol)))
            else:
                entry.update(label=f"dots-{symbol[1]}", dots=_place(DOTS[symbol[1]]))
            right[j] = entry
        left = [{"row": i, "label": label(c), "origin": [LEFT_X, ys[i] - FRAME // 2], "vertices": _place(_table(c))}
                for i, c in enumerate(classes)]
        return build_activity(
            mechanic=MATCH_V2_MECHANIC, version=MATCH_V2_VERSION, activity_id=activity_id, seed=seed,
            params={"pairs": pairs, "relation": relation, "family": family},
            geometry={"relation": relation, "family": family, "grid": GRID, "rows": pairs,
                      "anchors": {"left_x": LEFT_ANCHOR_X, "right_x": RIGHT_ANCHOR_X, "ys": ys},
                      "left": left, "right": right},
            solution={"left_to_right": permutation},
            measures={"pairs": pairs, "fixed_points": sum(1 for i, j in enumerate(permutation) if i == j),
                      "crossings": inversions(permutation), "min_area_ratio_gap_ppm": gap_ppm},
            search={"attempts": attempt + 1, "max_attempts": MAX_ATTEMPTS})
    raise V2Error("UNSATISFIABLE",
                  f"aucune activité match_v2 ({pairs} paires, {relation}, {family}) trouvée en {MAX_ATTEMPTS} "
                  "tentatives déterministes (critères inchangés, aucune dégradation)")
