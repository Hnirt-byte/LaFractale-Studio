"""Independent verification of a match_v2 record (plain dict or ``V2Activity``).

The generator is never called and its geometry helpers are not reused. The verifier takes the
PUBLISHED coordinates and recomputes, with its own exact arithmetic:

* the signature of every symbol (vertex count, re-entrant vertex count) from cross products, the
  orientation, the simplicity (no contact between non-adjacent edges) and the convexity;
* the relation between every left and every right symbol (``twin``: equal vertex lists in the local
  frame; ``count``: dot count equal to the vertex count of a polygon), the bilateral uniqueness of the
  association and its agreement with the published solution;
* the area / bounding-box ratios (``Fraction``), the REAL translated bounding boxes, the concurrency
  of links over all triples, the measures and the fingerprint.

Labels are informative: they never decide a correspondence, they are only checked for consistency with
the recomputed signatures. The literal symbol tables are read as DATA from ``match`` (closed vocabulary).
"""
from __future__ import annotations

from collections.abc import Mapping
from fractions import Fraction
from typing import Any

from lafractale.mechanics_v2 import HUMAN_PEDAGOGICAL_VALIDATION, V2_KIND, V2_SCHEMA
from lafractale.mechanics_v2.core import ACTIVITY_ID, MAX_SEED, V2Activity, V2Error, record_fingerprint
from lafractale.mechanics_v2.match import (
    AREA_RATIO_GAP_MIN_PPM, DOT_BORDER, DOTS, FAMILIES, FRAME, GRID, LEFT_ANCHOR_X, LEFT_X, MARGIN, MATCH_V2_MECHANIC,
    MATCH_V2_VERSION, MAX_ATTEMPTS, MIN_BOX_GAP, MIN_DOT_SEP_SQ, PAIRS_MAX, PAIRS_MIN, POLYGONS, RELATIONS,
    RIGHT_ANCHOR_X, RIGHT_X, STARS, ANCHOR_CLEARANCE,
)

_BODY_KEYS = {"schema", "kind", "mechanic", "version", "activity_id", "seed", "human_pedagogical_validation",
              "production_authorized", "params", "geometry", "solution", "measures", "search", "fingerprint"}
_MEASURE_KEYS = {"pairs", "fixed_points", "crossings", "min_area_ratio_gap_ppm"}
_MAX_VERTICES = 16


def _int(value: Any) -> bool:
    return type(value) is int


def _same(a: Any, b: Any) -> bool:
    """Strict structural equality: ``True`` is not ``1`` and ``1.0`` is not ``1``."""
    if type(a) is not type(b):
        return False
    if isinstance(a, list):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    if isinstance(a, Mapping):
        return set(a) == set(b) and all(_same(a[k], b[k]) for k in a)
    return a == b


# ---- exact helpers (independent of the generator) ---------------------------------------------------------
def _orient(a, b, c) -> int:
    value = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    return (value > 0) - (value < 0)


def _on_segment(a, b, p) -> bool:
    return min(a[0], b[0]) <= p[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])


def _contact(a, b, c, d) -> bool:
    o1, o2, o3, o4 = _orient(a, b, c), _orient(a, b, d), _orient(c, d, a), _orient(c, d, b)
    if o1 * o2 < 0 and o3 * o4 < 0:
        return True
    return ((o1 == 0 and _on_segment(a, b, c)) or (o2 == 0 and _on_segment(a, b, d))
            or (o3 == 0 and _on_segment(c, d, a)) or (o4 == 0 and _on_segment(c, d, b)))


def _twice_area(vs) -> int:
    return sum(vs[i][0] * vs[(i + 1) % len(vs)][1] - vs[(i + 1) % len(vs)][0] * vs[i][1] for i in range(len(vs)))


def _bbox(points):
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def _points(raw: Any, limit: int = _MAX_VERTICES) -> list[tuple[int, int]] | None:
    if not isinstance(raw, list) or not 1 <= len(raw) <= limit:
        return None
    out = []
    for item in raw:
        if not (isinstance(item, list) and len(item) == 2 and _int(item[0]) and _int(item[1])):
            return None
        out.append((item[0], item[1]))
    return out


def analyse_outline(vs: list[tuple[int, int]]) -> tuple[list[str], tuple[str, int] | None]:
    """Problems of a local outline and its recomputed class ``(kind, order)`` (``None`` if undecidable)."""
    problems: list[str] = []
    n = len(vs)
    if n < 3:
        return ["contour : au moins 3 sommets"], None
    if any(not (0 <= x <= FRAME and 0 <= y <= FRAME) for x, y in vs):
        problems.append(f"contour hors du cadre local [0, {FRAME}]²")
    if _twice_area(vs) <= 0:
        problems.append("contour : orientation anti-horaire (aire positive) requise")
    if vs[0] != min(vs, key=lambda p: (p[1], p[0])):
        problems.append("contour : le premier sommet doit être le plus petit (y, x)")
    turns = [_orient(vs[i - 1], vs[i], vs[(i + 1) % n]) for i in range(n)]
    if 0 in turns:
        problems.append("contour : sommets alignés ou confondus consécutifs")
    for a in range(n):
        for b in range(a + 1, n):
            if b == a + 1 or (a == 0 and b == n - 1):
                continue
            if _contact(vs[a], vs[(a + 1) % n], vs[b], vs[(b + 1) % n]):
                problems.append(f"contour non simple : arêtes {a + 1} et {b + 1} en contact")
    reentrant = sum(1 for t in turns if t < 0)
    if problems:
        return problems, None
    if reentrant == 0:
        return problems, ("polygon", n)
    if n % 2 == 0 and reentrant == n // 2:
        return problems, ("star", n // 2)
    return problems + [f"contour : ni convexe ni étoile ({n} sommets dont {reentrant} rentrants)"], None


def _ratio(vs) -> Fraction:
    x0, y0, x1, y1 = _bbox(vs)
    return Fraction(abs(_twice_area(vs)), 2 * (x1 - x0) * (y1 - y0))


def _table(kind: str, order: int):
    return (POLYGONS if kind == "polygon" else STARS).get(order)


def verify_match_v2(record: Mapping[str, Any] | V2Activity) -> list[str]:
    """List of problems; empty means a valid, correctly measured match_v2 record."""
    data = record.to_dict() if isinstance(record, V2Activity) else record
    if not isinstance(data, Mapping):
        return ["enregistrement : mapping attendu"]
    if set(data) != _BODY_KEYS:
        return [f"clés de l'enregistrement : attendu {sorted(_BODY_KEYS)}, reçu {sorted(map(str, data))}"]
    errors: list[str] = []
    for key, expected in (("schema", V2_SCHEMA), ("kind", V2_KIND), ("mechanic", MATCH_V2_MECHANIC),
                          ("version", MATCH_V2_VERSION), ("human_pedagogical_validation", HUMAN_PEDAGOGICAL_VALIDATION)):
        if data[key] != expected:
            errors.append(f"{key} : {expected!r} attendu, reçu {data[key]!r}")
    if data["production_authorized"] is not False:
        errors.append("production_authorized doit valoir false")
    if not isinstance(data["activity_id"], str) or not ACTIVITY_ID.match(data["activity_id"]):
        errors.append("activity_id : identifiant synthétique « syn-… » requis")
    if not _int(data["seed"]) or not 0 <= data["seed"] <= MAX_SEED:
        errors.append(f"seed : entier entre 0 et {MAX_SEED} requis")
    params, geometry, solution, measures, search = (data[k] for k in ("params", "geometry", "solution", "measures", "search"))
    if not all(isinstance(v, Mapping) for v in (params, geometry, solution, measures, search)):
        return errors + ["params/geometry/solution/measures/search : mappings attendus"]
    if set(params) != {"pairs", "relation", "family"}:
        return errors + ["params : exactement pairs, relation et family"]
    pairs, relation, family = params["pairs"], params["relation"], params["family"]
    if not _int(pairs) or not PAIRS_MIN <= pairs <= PAIRS_MAX:
        return errors + [f"params.pairs : entier entre {PAIRS_MIN} et {PAIRS_MAX}"]
    if type(relation) is not str or relation not in RELATIONS:
        return errors + [f"params.relation : parmi {RELATIONS}"]
    if type(family) is not str or family not in FAMILIES:
        return errors + [f"params.family : parmi {FAMILIES}"]
    size = {"polygon": len(POLYGONS), "star": len(STARS), "mixed": len(POLYGONS) + len(STARS)}[family]
    if pairs > size or (relation == "count" and family != "polygon"):
        return errors + ["params : combinaison impossible (réservoir trop petit ou count hors polygon)"]
    if set(geometry) != {"relation", "family", "grid", "rows", "anchors", "left", "right"}:
        return errors + ["geometry : exactement relation, family, grid, rows, anchors, left et right"]
    if not _same(geometry["relation"], relation) or not _same(geometry["family"], family) \
            or not _same(geometry["grid"], GRID) or not _same(geometry["rows"], pairs):
        errors.append("geometry : relation, family, grid ou rows incohérents avec params")
    ys = [MARGIN + (2 * i + 1) * (GRID - 2 * MARGIN) // (2 * pairs) for i in range(pairs)]
    anchors = geometry["anchors"]
    if not isinstance(anchors, Mapping) or not _same(dict(anchors), {"left_x": LEFT_ANCHOR_X, "right_x": RIGHT_ANCHOR_X, "ys": ys}):
        errors.append("M7 : ancrages {left_x, right_x, ys} différents de la mise en page entière attendue")
    left_raw, right_raw = geometry["left"], geometry["right"]
    if not (isinstance(left_raw, list) and isinstance(right_raw, list) and len(left_raw) == pairs == len(right_raw)):
        return errors + [f"geometry.left et geometry.right : {pairs} entrées chacune"]
    right_key = "vertices" if relation == "twin" else "dots"
    left_pts: list[list[tuple[int, int]]] = []
    right_pts: list[list[tuple[int, int]]] = []
    left_labels: list[Any] = []
    right_labels: list[Any] = []
    left_origins: list[tuple[int, int]] = []
    right_origins: list[tuple[int, int]] = []
    for side, raw, keys, x0, store, labels, origins in (
            ("left", left_raw, {"row", "label", "origin", "vertices"}, LEFT_X, left_pts, left_labels, left_origins),
            ("right", right_raw, {"row", "label", "origin", right_key}, RIGHT_X, right_pts, right_labels, right_origins)):
        for index, entry in enumerate(raw):
            if not isinstance(entry, Mapping) or set(entry) != keys:
                return errors + [f"geometry.{side}[{index}] : clés exactes {sorted(keys)} requises"]
            body = _points(entry["vertices" if side == "left" else right_key])
            if body is None:
                return errors + [f"geometry.{side}[{index}] : liste de points entiers [x, y] requise"]
            if not _same(entry["row"], index):
                errors.append(f"geometry.{side}[{index}] : row doit valoir {index}")
            origin = _points([entry["origin"]], 1)
            if origin is None:
                return errors + [f"geometry.{side}[{index}].origin : deux entiers [x, y] requis"]
            if not _same(entry["origin"], [x0, ys[index] - FRAME // 2]):
                errors.append(f"M7 : geometry.{side}[{index}].origin différent de la mise en page attendue")
            origins.append(origin[0])
            store.append(body)
            labels.append(entry["label"])

    # M4 -- left outlines recomputed from coordinates, equal to the closed tables
    classes: list[tuple[str, int] | None] = []
    for i, vs in enumerate(left_pts):
        problems, cls = analyse_outline(vs)
        errors += [f"M4 : gauche {i} : {p}" for p in problems]
        classes.append(cls)
        if cls is not None:
            table = _table(*cls)
            if table is None or [list(p) for p in vs] != [list(p) for p in table]:
                errors.append(f"M4 : gauche {i} : contour différent de la table fermée {cls}")
            if family != "mixed" and cls[0] != family:
                errors.append(f"M4 : gauche {i} : classe {cls} hors de la famille {family}")
            # M8 -- label consistency (informative field)
            if not _same(left_labels[i], f"{cls[0]}-{cls[1]}"):
                errors.append(f"M8 : gauche {i} : étiquette {left_labels[i]!r} incohérente avec la signature {cls}")
    # M2 -- distinct signatures inside the left column
    known = [c for c in classes if c is not None]
    if len(set(known)) != len(known):
        errors.append("M2 : deux symboles de gauche ont la même signature (nombre de sommets, sommets rentrants)")

    # right column
    right_classes: list[tuple[str, int] | None] = []
    for j, pts in enumerate(right_pts):
        if relation == "twin":
            problems, cls = analyse_outline(pts)
            errors += [f"M4 : droite {j} : {p}" for p in problems]
            right_classes.append(cls)
            if cls is not None:
                table = _table(*cls)
                if table is None or [list(p) for p in pts] != [list(p) for p in table]:
                    errors.append(f"M4 : droite {j} : contour différent de la table fermée {cls}")
                if not _same(right_labels[j], f"{cls[0]}-{cls[1]}"):
                    errors.append(f"M8 : droite {j} : étiquette {right_labels[j]!r} incohérente avec la signature {cls}")
        else:
            right_classes.append(None)
            k = len(pts)
            if not _same(right_labels[j], f"dots-{k}"):
                errors.append(f"M8 : droite {j} : étiquette {right_labels[j]!r} incohérente avec {k} points")
            if k not in DOTS or [list(p) for p in pts] != [list(p) for p in DOTS[k]]:
                errors.append(f"M9 : droite {j} : motif de points différent des tables fermées")
            if any(not (DOT_BORDER <= x <= FRAME - DOT_BORDER and DOT_BORDER <= y <= FRAME - DOT_BORDER) for x, y in pts):
                errors.append(f"M9 : droite {j} : point hors de la zone [{DOT_BORDER}, {FRAME - DOT_BORDER}]²")
            if any((pts[a][0] - pts[b][0]) ** 2 + (pts[a][1] - pts[b][1]) ** 2 < MIN_DOT_SEP_SQ
                   for a in range(k) for b in range(a + 1, k)):
                errors.append(f"M9 : droite {j} : deux points à moins de 30 de distance")
    if relation == "twin":
        known_r = [c for c in right_classes if c is not None]
        if len(set(known_r)) != len(known_r):
            errors.append("M2 : deux symboles de droite ont la même signature")
    elif len({len(p) for p in right_pts}) != len(right_pts):
        errors.append("M9 : deux motifs de points ont le même nombre de points")

    # M1 -- permutation, not the identity
    perm = solution.get("left_to_right") if set(solution) == {"left_to_right"} else None
    if not (isinstance(perm, list) and len(perm) == pairs and all(_int(v) for v in perm) and sorted(perm) == list(range(pairs))):
        return errors + ["M1 : solution = {left_to_right: permutation de 0..N-1}"]
    if perm == list(range(pairs)):
        errors.append("M1 : la permutation identité est refusée")

    # M3 -- relation recomputed from coordinates, bilateral uniqueness, agreement with the solution
    def related(i: int, j: int) -> bool:
        if relation == "twin":
            return left_pts[i] == right_pts[j]
        return classes[i] is not None and classes[i][0] == "polygon" and len(right_pts[j]) == len(left_pts[i])

    matrix = [[related(i, j) for j in range(pairs)] for i in range(pairs)]
    if any(sum(row) != 1 for row in matrix) or any(sum(matrix[i][j] for i in range(pairs)) != 1 for j in range(pairs)):
        errors.append("M3 : l'association n'est pas bilatéralement unique (recalculée depuis les coordonnées)")
    elif any(not matrix[i][perm[i]] for i in range(pairs)):
        errors.append("M3 : la solution publiée ne suit pas la relation recalculée")

    # M5 -- area / bounding-box ratio of the left outlines
    gap_ppm = None
    if len(known) == pairs and not any("M4" in e and "gauche" in e for e in errors):
        ratios = [_ratio(vs) for vs in left_pts]
        smallest = min(abs(ratios[a] - ratios[b]) for a in range(pairs) for b in range(a + 1, pairs))
        gap_ppm = smallest.numerator * 1_000_000 // smallest.denominator
        if smallest * 1_000_000 < AREA_RATIO_GAP_MIN_PPM:
            errors.append(f"M5 : écart minimal de rapport aire/boîte {gap_ppm} ppm < {AREA_RATIO_GAP_MIN_PPM}")

    # M6 -- no three links concurrent at an interior point (links share the x range, hence the parameter s)
    rise = [ys[perm[i]] - ys[i] for i in range(pairs)]
    for i in range(pairs):
        for j in range(i + 1, pairs):
            if rise[i] == rise[j]:
                continue
            s_ij = Fraction(ys[j] - ys[i], rise[i] - rise[j])
            if not 0 < s_ij < 1:
                continue
            for k in range(j + 1, pairs):
                if rise[i] != rise[k] and Fraction(ys[k] - ys[i], rise[i] - rise[k]) == s_ij:
                    errors.append(f"M6 : liens {i}, {j} et {k} concourants")

    # M7 -- REAL translated bounding boxes: inside the margins, separated, clear of the anchors
    for side, pts_list, origins in (("gauche", left_pts, left_origins), ("droite", right_pts, right_origins)):
        boxes = []
        for index, pts in enumerate(pts_list):
            ox, oy = origins[index]  # the PUBLISHED origin: the real box is measured where the symbol is declared
            bx0, by0, bx1, by1 = _bbox([(ox + x, oy + y) for x, y in pts])
            boxes.append((bx0, by0, bx1, by1))
            if not (MARGIN <= bx0 and bx1 <= GRID - MARGIN and MARGIN <= by0 and by1 <= GRID - MARGIN):
                errors.append(f"M7 : {side} {index} : boîte réelle hors des marges de la grille")
            if side == "gauche" and bx1 + ANCHOR_CLEARANCE > LEFT_ANCHOR_X:
                errors.append(f"M7 : gauche {index} : symbole trop proche de l'ancre")
            if side == "droite" and bx0 - ANCHOR_CLEARANCE < RIGHT_ANCHOR_X:
                errors.append(f"M7 : droite {index} : symbole trop proche de l'ancre")
        for index in range(len(boxes) - 1):
            if boxes[index + 1][1] - boxes[index][3] < MIN_BOX_GAP:
                errors.append(f"M7 : {side} : boîtes {index} et {index + 1} trop proches (< {MIN_BOX_GAP})")

    # measures and search
    inversions = sum(1 for a in range(pairs) for b in range(a + 1, pairs) if perm[a] > perm[b])
    if gap_ppm is not None:
        expected = {"pairs": pairs, "fixed_points": sum(1 for i, j in enumerate(perm) if i == j),
                    "crossings": inversions, "min_area_ratio_gap_ppm": gap_ppm}
        if set(measures) != _MEASURE_KEYS or not _same(dict(measures), expected):
            errors.append(f"measures : valeurs recalculées {expected}, reçues {dict(measures)}")
    if set(search) != {"attempts", "max_attempts"} or not _same(search["max_attempts"], MAX_ATTEMPTS) \
            or not _int(search["attempts"]) or not 1 <= search["attempts"] <= MAX_ATTEMPTS:
        errors.append("search : attempts (1..max) et max_attempts requis")
    try:
        if record_fingerprint(data) != data["fingerprint"]:
            errors.append("fingerprint : ne correspond pas au contenu canonique")
    except (V2Error, ValueError, TypeError) as exc:
        errors.append(f"fingerprint : contenu non canonique ({exc})")
    return errors
