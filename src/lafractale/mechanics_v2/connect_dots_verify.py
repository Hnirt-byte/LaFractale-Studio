"""Independent verification of a connect_dots_v2 record (plain dict or ``V2Activity``).

The generator is never called, and its geometry helpers are not reused: the verifier recomputes
every criterion from the published points and centre with its own exact arithmetic:

* clearance by projection with ``fractions.Fraction`` (closest point of the segment, then the
  squared distance), not by the cross-product formula used by the generator;
* the angular order around the centre by a rational "diamond" pseudo-angle in [0, 4), not by
  half-plane tests;
* segment contact by bounding boxes and orientation signs.

The exact integer verdict is the authority. The historical float helper ``segments_touch`` is only
a secondary diagnostic (``diagnose_connect_dots_v2``): a disagreement is reported there and never
turns a valid record into a rejected one.
"""
from __future__ import annotations

from collections.abc import Mapping
from fractions import Fraction
from typing import Any

from lafractale.engine.solvers import segments_touch
from lafractale.mechanics_v2 import HUMAN_PEDAGOGICAL_VALIDATION, V2_KIND, V2_SCHEMA
from lafractale.mechanics_v2.core import ACTIVITY_ID, MAX_SEED, V2Activity, V2Error, record_fingerprint
from lafractale.mechanics_v2.connect_dots import (
    CONNECT_DOTS_V2_MECHANIC, CONNECT_DOTS_V2_VERSION, GRID, MARGIN, MAX_ATTEMPTS, MIN_CLEARANCE_SQ,
    MIN_POINT_DIST_SQ, MIN_SEGMENT_SQ, POINTS_MAX, POINTS_MIN, SHAPES,
)

_BODY_KEYS = {"schema", "kind", "mechanic", "version", "activity_id", "seed", "human_pedagogical_validation",
              "production_authorized", "params", "geometry", "solution", "measures", "search", "fingerprint"}
_MEASURE_KEYS = {"point_count", "segment_count", "min_point_dist_sq", "min_segment_sq", "min_clearance_sq_floor", "twice_area"}


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


# ---- exact helpers (independent of the generator) -----------------------------------------------------
def _orient(a, b, c) -> int:
    value = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    return (value > 0) - (value < 0)


def _box(a, b, c, d) -> bool:
    return (max(min(a[0], b[0]), min(c[0], d[0])) <= min(max(a[0], b[0]), max(c[0], d[0]))
            and max(min(a[1], b[1]), min(c[1], d[1])) <= min(max(a[1], b[1]), max(c[1], d[1])))


def _contact(a, b, c, d) -> bool:
    """Closed segments ab and cd have a common point (bounding boxes, then orientation signs)."""
    if not _box(a, b, c, d):
        return False
    return _orient(a, b, c) * _orient(a, b, d) <= 0 and _orient(c, d, a) * _orient(c, d, b) <= 0


def _clearance_sq(p, a, b) -> Fraction:
    """Exact squared distance from p to the segment ab, through the closest point."""
    ux, uy = b[0] - a[0], b[1] - a[1]
    if ux == 0 and uy == 0:  # degenerate segment (reported by C1/C2): the distance is to the single point
        return Fraction((p[0] - a[0]) ** 2 + (p[1] - a[1]) ** 2)
    t = Fraction((p[0] - a[0]) * ux + (p[1] - a[1]) * uy, ux * ux + uy * uy)
    t = min(max(t, Fraction(0)), Fraction(1))
    qx, qy = a[0] + t * ux, a[1] + t * uy
    return (p[0] - qx) ** 2 + (p[1] - qy) ** 2


def _diamond(x: int, y: int) -> Fraction:
    """Exact rational pseudo-angle in [0, 4): monotone in the true polar angle, 0 on the +x axis."""
    if y >= 0:
        return Fraction(y, x + y) if x >= 0 else 1 + Fraction(-x, -x + y)
    return 2 + Fraction(-y, -x - y) if x < 0 else 3 + Fraction(x, x - y)


def _parse_points(raw: Any) -> list[tuple[int, int]] | None:
    if not isinstance(raw, list):
        return None
    points = []
    for index, item in enumerate(raw, start=1):
        if (not isinstance(item, Mapping) or set(item) != {"n", "x", "y"} or not all(_int(item[k]) for k in "nxy")
                or item["n"] != index):
            return None
        points.append((item["x"], item["y"]))
    return points


def verify_connect_dots_v2(record: Mapping[str, Any] | V2Activity) -> list[str]:
    """List of problems; empty means a valid, correctly measured connect_dots_v2 record."""
    data = record.to_dict() if isinstance(record, V2Activity) else record
    if not isinstance(data, Mapping):
        return ["enregistrement : mapping attendu"]
    if set(data) != _BODY_KEYS:
        return [f"clés de l'enregistrement : attendu {sorted(_BODY_KEYS)}, reçu {sorted(map(str, data))}"]
    errors: list[str] = []
    for key, expected in (("schema", V2_SCHEMA), ("kind", V2_KIND), ("mechanic", CONNECT_DOTS_V2_MECHANIC),
                          ("version", CONNECT_DOTS_V2_VERSION), ("human_pedagogical_validation", HUMAN_PEDAGOGICAL_VALIDATION)):
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
    if set(params) != {"points", "closed", "shape"}:
        return errors + ["params : exactement points, closed et shape"]
    count, closed, shape = params["points"], params["closed"], params["shape"]
    if not _int(count) or not POINTS_MIN <= count <= POINTS_MAX:
        return errors + [f"params.points : entier entre {POINTS_MIN} et {POINTS_MAX}"]
    if type(closed) is not bool:
        return errors + ["params.closed : booléen strict requis"]
    if type(shape) is not str or shape not in SHAPES:
        return errors + [f"params.shape : parmi {SHAPES}"]
    if set(geometry) != {"shape", "closed", "grid", "center", "points"}:
        return errors + ["geometry : exactement shape, closed, grid, center et points"]
    if not _same(geometry["shape"], shape) or not _same(geometry["closed"], closed) or not _same(geometry["grid"], GRID):
        errors.append("geometry : shape, closed ou grid incohérents avec params")
    points = _parse_points(geometry["points"])
    centre = geometry["center"]
    if points is None or len(points) != count:
        return errors + [f"geometry.points : {count} points {{n, x, y}} entiers, numérotés 1..N sans trou"]
    if not (isinstance(centre, list) and len(centre) == 2 and all(_int(v) for v in centre)):
        return errors + ["geometry.center : deux entiers attendus"]
    centre = (centre[0], centre[1])

    # C1 -- grid, distinct points, point spacing
    low, high = MARGIN, GRID - MARGIN
    if any(not (low <= x <= high and low <= y <= high) for x, y in points) or not (low <= centre[0] <= high and low <= centre[1] <= high):
        return errors + [f"points et centre doivent rester dans [{low}, {high}]²"]
    spacing = min((points[i][0] - points[j][0]) ** 2 + (points[i][1] - points[j][1]) ** 2
                  for i in range(count) for j in range(i + 1, count))
    if spacing < MIN_POINT_DIST_SQ:
        errors.append(f"C1 : deux points trop proches (carré de distance minimal {spacing} < {MIN_POINT_DIST_SQ})")

    # segments as 0-based index pairs
    drawn = [(i, i + 1) for i in range(count - 1)] + ([(count - 1, 0)] if closed else [])
    # C2 -- segment length
    shortest = min((points[i][0] - points[j][0]) ** 2 + (points[i][1] - points[j][1]) ** 2 for i, j in drawn)
    if shortest < MIN_SEGMENT_SQ:
        errors.append(f"C2 : segment trop court (carré de longueur minimal {shortest} < {MIN_SEGMENT_SQ})")
    # C5 -- no three consecutive collinear points
    span = count if closed else count - 2
    for i in range(span):
        if _orient(points[i], points[(i + 1) % count], points[(i + 2) % count]) == 0:
            errors.append(f"C5 : points {i + 1}, {(i + 1) % count + 1}, {(i + 2) % count + 1} alignés")
    # C3 -- non-adjacent segments neither cross nor touch
    for a in range(len(drawn)):
        for b in range(a + 1, len(drawn)):
            if set(drawn[a]) & set(drawn[b]):
                continue
            if _contact(points[drawn[a][0]], points[drawn[a][1]], points[drawn[b][0]], points[drawn[b][1]]):
                errors.append(f"C3 : segments {a + 1} et {b + 1} se croisent ou se touchent")
    # C4 -- exact clearance
    nearest: Fraction | None = None
    for index, p in enumerate(points):
        for i, j in drawn:
            if index in (i, j):
                continue
            gap = _clearance_sq(p, points[i], points[j])
            nearest = gap if nearest is None or gap < nearest else nearest
    if nearest is None or nearest < MIN_CLEARANCE_SQ:
        errors.append(f"C4 : dégagement point-segment insuffisant (minimum exact {nearest} < {MIN_CLEARANCE_SQ})")

    # C6 -- canonical start and sense, radial property around the published centre
    if points[0] != min(points, key=lambda p: (p[1], p[0])):
        errors.append("C6 : P1 doit être le point de plus petit (y, x)")
    if centre in points:
        errors.append("radial : le centre ne doit coïncider avec aucun point")
    else:
        angles = [_diamond(x - centre[0], y - centre[1]) for x, y in points]
        relative = [(angle - angles[0]) % 4 for angle in angles]
        if any(relative[i] >= relative[i + 1] for i in range(count - 1)):
            errors.append("radial : angle polaire strictement croissant (sens anti-horaire depuis P1) non respecté")
        for i in range(count):
            a, b = points[i], points[(i + 1) % count]
            if (a[0] - centre[0]) * (b[1] - centre[1]) - (a[1] - centre[1]) * (b[0] - centre[0]) <= 0:
                errors.append(f"radial : écart angulaire des points {i + 1} et {(i + 1) % count + 1} hors de ]0, π[")
    twice_area = None
    if closed:
        twice_area = sum(points[i][0] * points[(i + 1) % count][1] - points[(i + 1) % count][0] * points[i][1] for i in range(count))
        if twice_area <= 0:
            errors.append("C6 : contour fermé orienté dans le sens horaire ou d'aire nulle")

    # C7 -- solution
    if set(solution) != {"order", "close_to"} or not _same(solution["order"], list(range(1, count + 1))) \
            or not _same(solution["close_to"], 1 if closed else None):
        errors.append("C7 : solution attendue {order: [1..N], close_to: 1 si fermé, null sinon}")

    # measures
    if nearest is not None:
        expected = {"point_count": count, "segment_count": len(drawn), "min_point_dist_sq": spacing,
                    "min_segment_sq": shortest, "min_clearance_sq_floor": nearest.numerator // nearest.denominator,
                    "twice_area": twice_area}
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


def diagnose_connect_dots_v2(record: Mapping[str, Any] | V2Activity) -> list[str]:
    """Secondary, informational diagnostic: the historical float helper against the exact verdict.

    Never an authority and never a rejection reason: floating-point disagreement is only reported.
    Returns an empty list when the record cannot be parsed (``verify_connect_dots_v2`` reports that).
    """
    data = record.to_dict() if isinstance(record, V2Activity) else record
    try:
        points = _parse_points(data["geometry"]["points"])
        closed = data["geometry"]["closed"]
    except (KeyError, TypeError):
        return []
    if points is None or type(closed) is not bool or len(points) < 3:
        return []
    count = len(points)
    drawn = [(i, i + 1) for i in range(count - 1)] + ([(count - 1, 0)] if closed else [])
    notes = []
    for a in range(len(drawn)):
        for b in range(a + 1, len(drawn)):
            if set(drawn[a]) & set(drawn[b]):
                continue
            exact = _contact(points[drawn[a][0]], points[drawn[a][1]], points[drawn[b][0]], points[drawn[b][1]])
            scaled = [(x / GRID, y / GRID) for x, y in (points[drawn[a][0]], points[drawn[a][1]], points[drawn[b][0]], points[drawn[b][1]])]
            if segments_touch(*scaled) != exact:
                notes.append(f"segments {a + 1} et {b + 1} : l'aide flottante historique (segments_touch) diffère du verdict exact ({exact}) ; verdict exact conservé")
    return notes
