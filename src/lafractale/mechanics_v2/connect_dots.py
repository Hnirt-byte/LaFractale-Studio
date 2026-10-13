"""connect_dots_v2 — numbered points to join, ``radial`` family, integer geometry only.

Coordinates are integers on a grid of side ``GRID`` = 1000 (abstract frame, y axis upward;
rendering is out of scope). Every validity test is exact integer arithmetic: no float, no epsilon,
no trigonometry. P = (P1..PN), N = ``points`` in 5..24, ``closed`` selects the polygon P1→…→PN→P1
or the open polyline P1→…→PN.

Validity criteria (all must hold, none is ever relaxed):

C1  every point lies in [MARGIN, GRID−MARGIN]² and any two points are at squared distance ≥ 60².
C2  every drawn segment has squared length ≥ 60².
C3  two non-adjacent segments neither cross nor touch (closed segments, endpoints included).
C4  a point is at exact distance ≥ 40 from every segment that does not end at it.
C5  no three consecutive points are collinear (cyclically when ``closed``): adjacent segments only
    share their common endpoint.
C6  canonical start and sense: P1 is the point with the smallest (y, x); the numbering turns
    counter-clockwise around the centre (and the shoelace sum is positive when ``closed``).
C7  numbering n = 1..N is continuous; the solution is order [1..N] and ``close_to`` 1 when closed,
    ``None`` when open.

``radial`` family: the record carries an integer ``center`` C. The points are strictly increasing in
polar angle around C starting at P1, every consecutive angular gap, the gap PN→P1 included in BOTH
modes, being strictly between 0 and π (cross(Pi−C, Pi+1−C) > 0), and no point equals C. Such a
polygon is star-shaped about C, hence simple; C3 is still checked independently.

Clearance is an exact rational (point-to-segment squared distance). ``min_clearance_sq_floor`` is
its integer part ⌊min d²⌋ (floor of a non-negative rational, i.e. truncation); because 40² is an
integer, ``min d² ≥ 40²`` ⇔ ``⌊min d²⌋ ≥ 40²``, so the published floor loses nothing for the test.

"Unique order" means canonical start, canonical sense and a simple outline. It is NOT a proof that
the drawing is the only simple polygon through the points. Difficulty is not modelled and no human
pedagogical validation exists.
"""
from __future__ import annotations

from typing import Any, Mapping

from lafractale.mechanics_v2.core import (
    DetRng, V2Activity, V2Error, build_activity, check_activity_id, check_params, check_seed,
    bounded_repr,
)

CONNECT_DOTS_V2_MECHANIC = "connect_dots_v2"
CONNECT_DOTS_V2_VERSION = "b3b3b2-connect-dots-v2-1.0"
POINTS_MIN, POINTS_MAX = 5, 24
SHAPES = ("radial",)
GRID = 1000
MARGIN = 50
MIN_POINT_DIST_SQ = 60 * 60
MIN_SEGMENT_SQ = 60 * 60
MIN_CLEARANCE_SQ = 40 * 40
MAX_ATTEMPTS = 2000

#: Half-width of the square used to draw candidates (the centre moves in [450, 550]).
_RADIUS = 400

Point = tuple[int, int]


# ---- parameters ---------------------------------------------------------------------------------
def _points(value: Any) -> int:
    if type(value) is not int or not POINTS_MIN <= value <= POINTS_MAX:
        raise V2Error("BAD_POINTS", f"nombre de points entier attendu entre {POINTS_MIN} et {POINTS_MAX} inclus, reçu {bounded_repr(value)}")
    return value


def _closed(value: Any) -> bool:
    if type(value) is not bool:
        raise V2Error("BAD_CLOSED", f"booléen strict attendu pour closed, reçu {bounded_repr(value)}")
    return value


def _shape(value: Any) -> str:
    if type(value) is not str or value not in SHAPES:
        raise V2Error("BAD_SHAPE", f"forme attendue parmi {SHAPES}, reçu {bounded_repr(value)}")
    return value


PARAM_SPEC = {"points": _points, "closed": _closed, "shape": _shape}


# ---- exact integer geometry (the generator's own acceptance test) ------------------------------------
def _cross(o: Point, a: Point, b: Point) -> int:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _dot(o: Point, a: Point, b: Point) -> int:
    return (a[0] - o[0]) * (b[0] - o[0]) + (a[1] - o[1]) * (b[1] - o[1])


def _sq(a: Point, b: Point) -> int:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


def _sign(value: int) -> int:
    return (value > 0) - (value < 0)


def _within(a: Point, b: Point, p: Point) -> bool:
    return min(a[0], b[0]) <= p[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])


def touches(a: Point, b: Point, c: Point, d: Point) -> bool:
    """True when the closed segments ab and cd share at least one point (exact)."""
    o1, o2, o3, o4 = _sign(_cross(a, b, c)), _sign(_cross(a, b, d)), _sign(_cross(c, d, a)), _sign(_cross(c, d, b))
    if o1 * o2 < 0 and o3 * o4 < 0:
        return True
    return ((o1 == 0 and _within(a, b, c)) or (o2 == 0 and _within(a, b, d))
            or (o3 == 0 and _within(c, d, a)) or (o4 == 0 and _within(c, d, b)))


def _dist2(p: Point, a: Point, b: Point) -> tuple[int, int]:
    """Squared distance from p to segment ab as an exact fraction (numerator, denominator > 0)."""
    length = _sq(a, b)
    along = _dot(a, b, p)
    if along <= 0:
        return _sq(a, p), 1
    if along >= length:
        return _sq(b, p), 1
    c = _cross(a, b, p)
    return c * c, length


def _segments(count: int, closed: bool) -> list[tuple[int, int]]:
    """Index pairs (0-based) of the drawn segments."""
    return [(i, (i + 1) % count) for i in range(count if closed else count - 1)]


def evaluate(points: list[Point], closed: bool, center: Point) -> dict[str, Any] | None:
    """Measures when EVERY criterion holds, ``None`` otherwise."""
    count = len(points)
    if any(not (MARGIN <= x <= GRID - MARGIN and MARGIN <= y <= GRID - MARGIN) for x, y in points):
        return None
    if not (MARGIN <= center[0] <= GRID - MARGIN and MARGIN <= center[1] <= GRID - MARGIN):
        return None
    min_point = min(_sq(points[i], points[j]) for i in range(count) for j in range(i + 1, count))
    if min_point < MIN_POINT_DIST_SQ:
        return None
    segments = _segments(count, closed)
    min_segment = min(_sq(points[i], points[j]) for i, j in segments)
    if min_segment < MIN_SEGMENT_SQ:
        return None
    # C5: no three consecutive collinear points
    triples = range(count) if closed else range(count - 2)
    if any(_cross(points[i], points[(i + 1) % count], points[(i + 2) % count]) == 0 for i in triples):
        return None
    # C6 and the radial property: canonical P1, counter-clockwise strictly increasing angle, gaps in (0, π)
    if points[0] != min(points, key=lambda p: (p[1], p[0])):
        return None
    if any(p == center for p in points):
        return None
    first = (points[0][0] - center[0], points[0][1] - center[1])
    origin = (0, 0)
    previous_half = 0
    for i in range(count):
        d = (points[i][0] - center[0], points[i][1] - center[1])
        nxt = (points[(i + 1) % count][0] - center[0], points[(i + 1) % count][1] - center[1])
        if _cross(origin, d, nxt) <= 0:  # gap in (0, π), the wrap PN→P1 included
            return None
        if i == 0:
            continue
        # Half-turn reached from P1: 0 while the angle from P1 is in ]0, π[, 1 from π on. A point on P1's own ray
        # lands in half 1; it is then refused by the next point (back to half 0) or by the gap PN→P1 (cross = 0).
        half = 0 if _cross(origin, first, d) > 0 else 1
        if half < previous_half:
            return None
        previous_half = half
    # C3: non-adjacent segments neither cross nor touch
    for a in range(len(segments)):
        for b in range(a + 1, len(segments)):
            if segments[b][0] == segments[a][1] or segments[b][1] == segments[a][0]:
                continue
            if touches(points[segments[a][0]], points[segments[a][1]], points[segments[b][0]], points[segments[b][1]]):
                return None
    # C4: exact clearance; keep the minimum as a fraction
    best_num, best_den = None, 1
    for index, p in enumerate(points):
        for i, j in segments:
            if index in (i, j):
                continue
            num, den = _dist2(p, points[i], points[j])
            if num < MIN_CLEARANCE_SQ * den:
                return None
            if best_num is None or num * best_den < best_num * den:
                best_num, best_den = num, den
    twice_area = None
    if closed:
        twice_area = sum(points[i][0] * points[(i + 1) % count][1] - points[(i + 1) % count][0] * points[i][1] for i in range(count))
        if twice_area <= 0:
            return None
    return {"point_count": count, "segment_count": len(segments), "min_point_dist_sq": min_point,
            "min_segment_sq": min_segment, "min_clearance_sq_floor": best_num // best_den, "twice_area": twice_area}


# ---- candidates: stratified, integer only -------------------------------------------------------------
def _boundary(u: int) -> Point:
    """Point of the square of half-width _RADIUS at perimeter position u (counter-clockwise, u from 0 to 8R−1)."""
    side, t = divmod(u, 2 * _RADIUS)
    t -= _RADIUS
    if side == 0:
        return (_RADIUS, t)
    if side == 1:
        return (-t, _RADIUS)
    if side == 2:
        return (-_RADIUS, -t)
    return (t, -_RADIUS)


def _candidate(count: int, rng: DetRng) -> tuple[Point, list[Point]]:
    centre = (450 + rng.below(101), 450 + rng.below(101))
    perimeter = 8 * _RADIUS
    phase = rng.below(perimeter)
    points: list[Point] = []
    for k in range(count):
        low, high = perimeter * k // count, perimeter * (k + 1) // count
        bx, by = _boundary((phase + low + rng.below(high - low)) % perimeter)
        scale = 40 + rng.below(61)
        points.append((centre[0] + bx * scale // 100, centre[1] + by * scale // 100))
    first = min(range(count), key=lambda i: (points[i][1], points[i][0]))
    return centre, points[first:] + points[:first]


def generate_connect_dots_v2(activity_id: Any, seed: Any, params: Mapping[str, Any]) -> V2Activity:
    """Deterministic bounded search; raises ``V2Error`` (never relaxes a criterion)."""
    activity_id, seed = check_activity_id(activity_id), check_seed(seed)
    values = check_params(params, PARAM_SPEC)
    count, closed, shape = values["points"], values["closed"], values["shape"]
    for attempt in range(MAX_ATTEMPTS):
        rng = DetRng(f"lafractale-mechanics-v2|{CONNECT_DOTS_V2_MECHANIC}|{activity_id}|{seed}|{shape}|{count}|{int(closed)}|{attempt}")
        centre, points = _candidate(count, rng)
        measures = evaluate(points, closed, centre)
        if measures is not None:
            return build_activity(
                mechanic=CONNECT_DOTS_V2_MECHANIC, version=CONNECT_DOTS_V2_VERSION, activity_id=activity_id, seed=seed,
                params={"points": count, "closed": closed, "shape": shape},
                geometry={"shape": shape, "closed": closed, "grid": GRID, "center": list(centre),
                          "points": [{"n": i + 1, "x": x, "y": y} for i, (x, y) in enumerate(points)]},
                solution={"order": list(range(1, count + 1)), "close_to": 1 if closed else None},
                measures=measures, search={"attempts": attempt + 1, "max_attempts": MAX_ATTEMPTS})
    raise V2Error("UNSATISFIABLE",
                  f"aucune figure {shape} de {count} points ({'fermée' if closed else 'ouverte'}) trouvée en "
                  f"{MAX_ATTEMPTS} tentatives déterministes (critères inchangés, aucune dégradation)")
