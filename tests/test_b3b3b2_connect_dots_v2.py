"""B3-B.3b.2 — connect_dots_v2: exact integer geometry, radial property, independent verification."""
from __future__ import annotations

import ast
import copy
import json
import math
import random
from fractions import Fraction
from pathlib import Path

import pytest

from lafractale.mechanics_v2 import PRODUCTION_AUTHORIZED, V2_KIND, V2_SCHEMA
from lafractale.mechanics_v2 import connect_dots as cd
from lafractale.mechanics_v2 import connect_dots_verify as cdv
from lafractale.mechanics_v2.connect_dots import POINTS_MAX, POINTS_MIN, evaluate, touches
from lafractale.mechanics_v2.connect_dots_verify import diagnose_connect_dots_v2, verify_connect_dots_v2
from lafractale.mechanics_v2.core import V2Activity, V2Error, loads_record, record_fingerprint
from lafractale.mechanics_v2.registry import MECHANICS_V2, generate_v2, verify_v2

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "src/lafractale/mechanics_v2"
COUNTS = range(POINTS_MIN, POINTS_MAX + 1)
MODES = (True, False)
NOISE = ("measures", "fingerprint")  # error families a hand-built record is not expected to get right


def make(points=8, closed=True, seed=1, activity_id="syn-demo") -> V2Activity:
    return generate_v2("connect_dots_v2", activity_id, seed, {"points": points, "closed": closed, "shape": "radial"})


def refingerprint(data: dict) -> dict:
    """Fresh fingerprint when the content is still canonical (floats cannot be fingerprinted: keep the stale one)."""
    try:
        data["fingerprint"] = record_fingerprint(data)
    except V2Error:
        pass
    return data


def tampered(activity: V2Activity, mutate, *, refinger: bool = True) -> dict:
    data = copy.deepcopy(activity.to_dict())
    mutate(data)
    return refingerprint(data) if refinger else data


def hand(points, closed=True, centre=(500, 500)) -> dict:
    """A record around hand-picked geometry: only the geometry-related verdicts are meaningful."""
    count = len(points)
    return refingerprint({
        "schema": V2_SCHEMA, "kind": V2_KIND, "mechanic": "connect_dots_v2", "version": cd.CONNECT_DOTS_V2_VERSION,
        "activity_id": "syn-hand", "seed": 0, "human_pedagogical_validation": "NONE", "production_authorized": False,
        "params": {"points": count, "closed": closed, "shape": "radial"},
        "geometry": {"shape": "radial", "closed": closed, "grid": 1000, "center": list(centre),
                     "points": [{"n": i + 1, "x": x, "y": y} for i, (x, y) in enumerate(points)]},
        "solution": {"order": list(range(1, count + 1)), "close_to": 1 if closed else None},
        "measures": {}, "search": {"attempts": 1, "max_attempts": cd.MAX_ATTEMPTS}, "fingerprint": ""})


def geometry_errors(record: dict) -> list[str]:
    return [e for e in verify_connect_dots_v2(record) if not e.startswith(NOISE)]


def has(errors: list[str], tag: str) -> bool:
    return any(e.startswith(tag) for e in errors)


GOOD = [(500, 100), (850, 450), (650, 850), (250, 800), (150, 400)]  # valid pentagon around (500, 500)


@pytest.fixture(scope="module")
def sample() -> V2Activity:
    return make()


# ---- independent references (exact, test-only) ------------------------------------------------------------
def ref_touch(a, b, c, d) -> bool:
    """Closed segments share a point: parametric solution with rationals, collinear cases by projection."""
    r, s = (b[0] - a[0], b[1] - a[1]), (d[0] - c[0], d[1] - c[1])
    denom = r[0] * s[1] - r[1] * s[0]
    qp = (c[0] - a[0], c[1] - a[1])
    if denom != 0:
        t = Fraction(qp[0] * s[1] - qp[1] * s[0], denom)
        u = Fraction(qp[0] * r[1] - qp[1] * r[0], denom)
        return 0 <= t <= 1 and 0 <= u <= 1
    if qp[0] * r[1] - qp[1] * r[0] != 0:
        return False  # parallel, not collinear
    length = r[0] ** 2 + r[1] ** 2
    t0 = Fraction(qp[0] * r[0] + qp[1] * r[1], length)
    t1 = t0 + Fraction(s[0] * r[0] + s[1] * r[1], length)
    return max(min(t0, t1), 0) <= min(max(t0, t1), 1)


def ref_clearance_floor(points, closed) -> int:
    """⌊min d²⌋ over (point, non-incident segment), by minimising over the exact projection."""
    count = len(points)
    drawn = [(i, i + 1) for i in range(count - 1)] + ([(count - 1, 0)] if closed else [])
    best = None
    for index, p in enumerate(points):
        for i, j in drawn:
            if index in (i, j):
                continue
            a, b = points[i], points[j]
            ux, uy = b[0] - a[0], b[1] - a[1]
            t = max(Fraction(0), min(Fraction(1), Fraction((p[0] - a[0]) * ux + (p[1] - a[1]) * uy, ux * ux + uy * uy)))
            d2 = (p[0] - a[0] - t * ux) ** 2 + (p[1] - a[1] - t * uy) ** 2
            best = d2 if best is None or d2 < best else best
    return math.floor(best)


def _walk(value):
    if isinstance(value, dict):
        for v in value.values():
            yield from _walk(v)
    elif isinstance(value, list):
        for v in value:
            yield from _walk(v)
    else:
        yield value


def points_of(record) -> list[tuple[int, int]]:
    data = record.to_dict() if isinstance(record, V2Activity) else record
    return [(p["x"], p["y"]) for p in data["geometry"]["points"]]


# ---- golden: stable canonical form and fingerprints ----------------------------------------------------------------
def test_golden_fingerprints_are_stable_across_versions_and_runs(sample):
    assert sample.fingerprint == "8a2e42ab493cacfe3ab2614c1c99ced2037c493ec5e4f9fa8e271e377de14eed"
    assert make(24, True, 7, "syn-x").fingerprint == "b29e6fac69af1007bbfa9bcdaa7d35d97c4034d33f2d1c248ca9c11cdd87e309"
    assert make(5, False, 0, "syn-open").fingerprint == "a38c2f290a24f82416b464cadd1bb4981761087e655303f726b9e7efb3d93c5f"
    assert make().canonical_bytes() == sample.canonical_bytes()


def test_canonical_form_schema_and_fingerprint_rule(sample):
    raw = sample.canonical_bytes()
    text = raw.decode("utf-8")
    assert ", " not in text and ": " not in text
    record = json.loads(text)
    assert list(record) == sorted(record) and list(record["geometry"]) == sorted(record["geometry"])
    assert record["schema"] == V2_SCHEMA and record["kind"] == V2_KIND and record["mechanic"] == "connect_dots_v2"
    assert record["production_authorized"] is False and record["human_pedagogical_validation"] == "NONE"
    assert record["version"] == "b3b3b2-connect-dots-v2-1.0" and record["geometry"]["grid"] == 1000
    assert loads_record(raw) == record
    assert record["fingerprint"] == record_fingerprint(record) == sample.fingerprint
    assert all(type(v) is int for p in record["geometry"]["points"] for v in (p["n"], p["x"], p["y"]))
    assert not [v for v in _walk(record) if isinstance(v, float)]  # no float anywhere in the record


def test_open_mode_encodes_the_absent_closure_as_null():
    record = make(6, False, 3).to_dict()
    assert record["solution"] == {"order": [1, 2, 3, 4, 5, 6], "close_to": None}
    assert record["measures"]["twice_area"] is None and record["measures"]["segment_count"] == 5
    assert b'"close_to":null' in make(6, False, 3).canonical_bytes()
    closed = make(6, True, 3).to_dict()
    assert closed["solution"]["close_to"] == 1 and closed["measures"]["segment_count"] == 6


def test_registry_is_closed_and_lists_both_mechanics():
    assert set(MECHANICS_V2) == {"maze_v2", "connect_dots_v2"}
    with pytest.raises(TypeError):
        MECHANICS_V2["match_v2"] = object()  # type: ignore[index]
    assert verify_v2(make()) == [] and verify_v2(make().to_dict()) == []


# ---- parameters: closed set, strict types ---------------------------------------------------------------------------
@pytest.mark.parametrize("points", [4, 25, 0, -5, 8.0, "8", True, None, 2**70])
def test_points_out_of_range_or_wrong_type_are_refused(points):
    with pytest.raises(V2Error):
        generate_v2("connect_dots_v2", "syn-a", 0, {"points": points, "closed": True, "shape": "radial"})


@pytest.mark.parametrize("closed", [1, 0, "true", None, 1.0, [True]])
def test_closed_must_be_a_strict_boolean(closed):
    with pytest.raises(V2Error):
        generate_v2("connect_dots_v2", "syn-a", 0, {"points": 8, "closed": closed, "shape": "radial"})


@pytest.mark.parametrize("shape", ["star", "moon", "house", "hats", "gifts", "convex", "RADIAL", "", None, 3])
def test_only_the_radial_family_is_open(shape):
    with pytest.raises(V2Error):
        generate_v2("connect_dots_v2", "syn-a", 0, {"points": 8, "closed": True, "shape": shape})


def test_parameter_set_is_closed():
    base = {"points": 8, "closed": True, "shape": "radial"}
    for extra in ({"difficulty": "easy"}, {"center": [500, 500]}, {"production_authorized": True}, {"page": 17}):
        with pytest.raises(V2Error, match="UNKNOWN_PARAM"):
            generate_v2("connect_dots_v2", "syn-a", 0, {**base, **extra})
    for key in base:
        with pytest.raises(V2Error, match="MISSING_PARAM"):
            generate_v2("connect_dots_v2", "syn-a", 0, {k: v for k, v in base.items() if k != key})
    for bad in (None, [], "radial", 8):
        with pytest.raises(V2Error):
            generate_v2("connect_dots_v2", "syn-a", 0, bad)  # type: ignore[arg-type]


@pytest.mark.parametrize("seed", [-1, 2**63, 1.0, "1", True, None])
def test_bad_seeds_are_refused(seed):
    with pytest.raises(V2Error):
        generate_v2("connect_dots_v2", "syn-a", seed, {"points": 8, "closed": True, "shape": "radial"})


@pytest.mark.parametrize("activity_id", ["demo", "SYN-a", "syn-", "syn-a_b", "syn-é", "page-17", "syn-" + "a" * 47, "", None, 3])
def test_only_synthetic_identifiers_are_accepted(activity_id):
    with pytest.raises(V2Error):
        generate_v2("connect_dots_v2", activity_id, 0, {"points": 8, "closed": True, "shape": "radial"})


# ---- properties: every point count, both modes, many seeds ------------------------------------------------------------
@pytest.mark.parametrize("closed", MODES)
@pytest.mark.parametrize("count", COUNTS)
def test_property_generated_figures_satisfy_every_criterion(count, closed):
    for seed in range(6):
        activity = make(count, closed, seed, f"syn-prop-{count}")
        record = activity.to_dict()
        assert verify_connect_dots_v2(activity) == [] and diagnose_connect_dots_v2(activity) == []
        assert make(count, closed, seed, f"syn-prop-{count}").canonical_bytes() == activity.canonical_bytes()
        points = points_of(record)
        assert len(points) == count and points[0] == min(points, key=lambda p: (p[1], p[0]))
        # criteria re-derived with the test's own exact references
        drawn = [(i, i + 1) for i in range(count - 1)] + ([(count - 1, 0)] if closed else [])
        for a in range(len(drawn)):
            for b in range(a + 1, len(drawn)):
                if not set(drawn[a]) & set(drawn[b]):
                    assert not ref_touch(*(points[k] for k in drawn[a] + drawn[b]))
        measures = record["measures"]
        assert measures["min_clearance_sq_floor"] == ref_clearance_floor(points, closed) >= cd.MIN_CLEARANCE_SQ
        assert measures["min_segment_sq"] >= cd.MIN_SEGMENT_SQ and measures["min_point_dist_sq"] >= cd.MIN_POINT_DIST_SQ
        assert (measures["twice_area"] is not None and measures["twice_area"] > 0) == closed
        assert record["search"]["attempts"] <= cd.MAX_ATTEMPTS


def test_property_radial_structure_with_a_float_oracle():
    """Counter-clockwise strictly increasing polar angle from P1 around the published centre, gaps in ]0, π[."""
    for closed in MODES:
        for count in (5, 11, 17, 24):
            for seed in range(5):
                record = make(count, closed, seed).to_dict()
                cx, cy = record["geometry"]["center"]
                angles = [math.atan2(y - cy, x - cx) for x, y in points_of(record)]
                relative = [(a - angles[0]) % (2 * math.pi) for a in angles]
                assert relative[0] == 0 and all(relative[i] < relative[i + 1] for i in range(count - 1))
                gaps = [(relative[i + 1] - relative[i]) for i in range(count - 1)] + [2 * math.pi - relative[-1]]
                assert all(0 < g < math.pi for g in gaps)


def test_search_effort_is_small_over_the_whole_range():
    worst = 0
    for closed in MODES:
        for count in COUNTS:
            for seed in range(12):
                worst = max(worst, make(count, closed, seed, "syn-effort").search["attempts"])
    assert worst < cd.MAX_ATTEMPTS // 10


def test_different_seeds_and_ids_give_different_figures():
    assert make(10, True, 1).fingerprint != make(10, True, 2).fingerprint
    assert make(10, True, 1, "syn-a").fingerprint != make(10, True, 1, "syn-b").fingerprint
    assert make(10, True, 1).fingerprint != make(10, False, 1).fingerprint


# ---- bounded search, never relaxed ----------------------------------------------------------------------------------------
def test_unsatisfiable_search_fails_explicitly_without_relaxing(monkeypatch):
    monkeypatch.setattr(cd, "MAX_ATTEMPTS", 25)
    monkeypatch.setattr(cd, "MIN_CLEARANCE_SQ", 10**9)  # no figure can meet it
    for closed in MODES:
        with pytest.raises(V2Error, match="UNSATISFIABLE"):
            make(12, closed, 0)


def test_one_attempt_budget_is_enforced(monkeypatch):
    found = next(s for s in range(200) if make(24, True, s, "syn-budget").search["attempts"] > 1)
    monkeypatch.setattr(cd, "MAX_ATTEMPTS", 1)
    with pytest.raises(V2Error, match="UNSATISFIABLE"):
        make(24, True, found, "syn-budget")


def test_verifier_rejects_attempts_beyond_the_budget(sample, monkeypatch):
    assert verify_connect_dots_v2(sample) == []
    monkeypatch.setattr(cdv, "MAX_ATTEMPTS", 0)
    assert any(e.startswith("search") for e in verify_connect_dots_v2(sample))


# ---- exact geometry: tables, differential and boundary tests --------------------------------------------------------------
TOUCH_TABLE = [
    ("proper cross", (0, 0), (10, 10), (0, 10), (10, 0), True),
    ("T contact", (0, 0), (10, 0), (5, 0), (5, 7), True),
    ("shared endpoint", (0, 0), (10, 0), (10, 0), (10, 9), True),
    ("collinear overlap", (0, 0), (10, 0), (6, 0), (20, 0), True),
    ("collinear touch at one point", (0, 0), (10, 0), (10, 0), (20, 0), True),
    ("collinear disjoint", (0, 0), (10, 0), (11, 0), (20, 0), False),
    ("parallel", (0, 0), (10, 0), (0, 1), (10, 1), False),
    ("near miss by one unit", (0, 0), (10, 0), (5, 1), (5, 7), False),
    ("line crosses beyond the segment", (0, 0), (10, 0), (12, -5), (12, 5), False),
    ("point-like touch of a diagonal", (0, 0), (10, 10), (5, 5), (9, 1), True),
    ("diagonal near miss", (0, 0), (10, 10), (6, 5), (9, 1), False),
    ("diagonal crossing", (0, 0), (10, 10), (5, 6), (9, 1), True),
]


@pytest.mark.parametrize("name,a,b,c,d,expected", TOUCH_TABLE, ids=[row[0] for row in TOUCH_TABLE])
def test_segment_contact_table_matches_the_exact_reference(name, a, b, c, d, expected):
    for flip in (False, True):  # symmetric under swapping the segments and reversing a segment
        p, q = ((c, d), (a, b)) if flip else ((a, b), (c, d))
        assert ref_touch(*p, *q) is expected
        assert touches(*p, *q) == ref_touch(*p, *q) == cdv._contact(*p, *q)
        assert touches(p[1], p[0], q[0], q[1]) == touches(*p, *q)


def test_segment_contact_matches_the_reference_on_random_small_grids():
    rng = random.Random(20261013)
    for _ in range(4000):
        a, b, c, d = ((rng.randint(0, 6), rng.randint(0, 6)) for _ in range(4))
        if a == b or c == d:
            continue
        assert touches(a, b, c, d) == cdv._contact(a, b, c, d) == ref_touch(a, b, c, d)


CLEARANCE_TABLE = [  # (point, a, b) -> exact squared distance as a fraction
    ((0, 3), (0, 0), (10, 0), Fraction(9)),
    ((-3, 4), (0, 0), (10, 0), Fraction(25)),
    ((13, 4), (0, 0), (10, 0), Fraction(25)),
    ((5, 5), (0, 0), (10, 10), Fraction(0)),
    ((1, 0), (0, 0), (3, 4), Fraction(16, 25)),
    ((4, 0), (0, 0), (3, 4), Fraction(256, 25)),
    ((0, 1), (0, 0), (0, 0), Fraction(1)),
]


@pytest.mark.parametrize("p,a,b,expected", CLEARANCE_TABLE)
def test_clearance_is_an_exact_fraction_in_both_implementations(p, a, b, expected):
    if a == b:  # degenerate segment: only the verifier is asked (the generator rejects it earlier)
        assert cdv._clearance_sq(p, a, b) == expected
        return
    num, den = cd._dist2(p, a, b)
    assert Fraction(num, den) == cdv._clearance_sq(p, a, b)
    assert Fraction(num, den) == expected


def test_clearance_implementations_agree_on_random_inputs_and_floor_is_truncation():
    rng = random.Random(7)
    for _ in range(3000):
        p, a, b = ((rng.randint(0, 40), rng.randint(0, 40)) for _ in range(3))
        if a == b:
            continue
        num, den = cd._dist2(p, a, b)
        exact = cdv._clearance_sq(p, a, b)
        assert Fraction(num, den) == exact
        assert num // den == math.floor(exact) == int(exact)  # truncation of a non-negative rational
    # documented convention: truncation of a non-negative rational, never rounding
    assert cd._dist2((1, 0), (0, 0), (3, 4)) == (16, 25) and 16 // 25 == 0
    assert (1601 * 25 + 24) // 25 == 1601


def test_boundary_of_every_threshold_is_exact(monkeypatch):
    """A threshold equal to the measure passes; one more fails: no epsilon anywhere."""
    for count, closed, seed in ((8, True, 1), (13, False, 2), (24, True, 3)):
        activity = make(count, closed, seed, "syn-bound")
        record = activity.to_dict()
        points, centre = points_of(record), tuple(record["geometry"]["center"])
        for name, key in (("MIN_POINT_DIST_SQ", "min_point_dist_sq"), ("MIN_SEGMENT_SQ", "min_segment_sq"),
                          ("MIN_CLEARANCE_SQ", "min_clearance_sq_floor")):
            value = record["measures"][key]
            with monkeypatch.context() as m:
                m.setattr(cd, name, value)
                m.setattr(cdv, name, value)
                assert verify_connect_dots_v2(activity) == [], (name, value)
                assert evaluate(points, closed, centre) is not None
            with monkeypatch.context() as m:
                m.setattr(cd, name, value + 1)
                m.setattr(cdv, name, value + 1)
                assert verify_connect_dots_v2(activity) != [], (name, value)
                assert evaluate(points, closed, centre) is None


def test_differential_generator_acceptance_against_independent_verifier():
    """On thousands of random mutations the two implementations give the same yes/no verdict."""
    rng = random.Random(424242)
    cases = agree = 0
    for count, closed, seed in [(c, m, s) for c in (5, 6, 9, 14, 24) for m in MODES for s in range(3)]:
        base = make(count, closed, seed, "syn-diff").to_dict()
        centre = tuple(base["geometry"]["center"])
        points = points_of(base)
        for _ in range(60):
            mutated = list(points)
            kind = rng.randrange(5)
            if kind == 0:  # nudge one point a little
                i = rng.randrange(count)
                mutated[i] = (mutated[i][0] + rng.randint(-70, 70), mutated[i][1] + rng.randint(-70, 70))
            elif kind == 1:  # swap two points
                i, j = rng.sample(range(count), 2)
                mutated[i], mutated[j] = mutated[j], mutated[i]
            elif kind == 2:  # rotate the numbering
                k = rng.randrange(1, count)
                mutated = mutated[k:] + mutated[:k]
            elif kind == 3:  # reverse the sense, keeping P1 first
                mutated = [mutated[0]] + mutated[:0:-1]
            else:  # move a point onto an arbitrary place
                mutated[rng.randrange(count)] = (rng.randint(40, 960), rng.randint(40, 960))
            for centre_now in (centre, (centre[0] + rng.randint(-200, 200), centre[1] + rng.randint(-200, 200))):
                record = hand(mutated, closed, centre_now)
                ok_verifier = geometry_errors(record) == []
                ok_generator = evaluate(mutated, closed, centre_now) is not None
                cases += 1
                agree += ok_verifier == ok_generator
                assert ok_verifier == ok_generator, (mutated, closed, centre_now, geometry_errors(record))
    assert cases == agree > 3000


# ---- hand-built adversarial figures ---------------------------------------------------------------------------------------
def test_reference_pentagon_is_valid_and_open_mode_too():
    assert geometry_errors(hand(GOOD)) == [] and geometry_errors(hand(GOOD, closed=False)) == []
    measures = evaluate(GOOD, True, (500, 500))
    assert measures is not None and measures["twice_area"] == 672500 and measures["min_segment_sq"] == 162500


def test_crossing_bow_tie_is_rejected():
    errors = geometry_errors(hand([(100, 100), (900, 100), (100, 900), (900, 900), (500, 500)]))
    assert has(errors, "C3")


def test_t_contact_between_non_adjacent_segments_is_rejected():
    # P5 lies on segment P1P2: segment P4P5 touches P1P2 at an interior point
    errors = geometry_errors(hand([(500, 100), (850, 450), (650, 850), (250, 800), (675, 275)]))
    assert has(errors, "C3") and has(errors, "C5")


def test_duplicate_and_close_points_and_short_segments_are_rejected():
    errors = geometry_errors(hand([(500, 100), (850, 450), (850, 450), (250, 800), (150, 400)]))
    assert has(errors, "C1") and has(errors, "C2")  # also exercises the degenerate-segment path (no crash)
    errors = geometry_errors(hand([(500, 100), (850, 450), (650, 850), (250, 800), (520, 130)]))
    assert has(errors, "C1") and has(errors, "C2")


def test_three_consecutive_collinear_points_are_rejected():
    errors = geometry_errors(hand([(500, 100), (675, 275), (850, 450), (650, 850), (250, 800), (150, 400)]))
    assert has(errors, "C5")
    errors = geometry_errors(hand([(500, 100), (675, 275), (850, 450), (650, 850), (250, 800), (150, 400)], closed=False))
    assert has(errors, "C5")


def test_clockwise_and_rotated_numbering_are_rejected():
    clockwise = [GOOD[0]] + GOOD[:0:-1]
    errors = geometry_errors(hand(clockwise))
    assert has(errors, "C6") and has(errors, "radial")
    assert any("sens horaire" in e for e in errors)
    errors = geometry_errors(hand(GOOD[1:] + GOOD[:1]))
    assert any(e.startswith("C6 : P1") for e in errors)
    assert has(geometry_errors(hand(clockwise, closed=False)), "radial")


def test_a_centre_that_is_not_in_the_kernel_is_rejected():
    assert has(geometry_errors(hand(GOOD, centre=(900, 900))), "radial")
    assert has(geometry_errors(hand(GOOD, centre=GOOD[2])), "radial")  # centre on a point


def test_an_open_spiral_winding_beyond_one_turn_breaks_only_the_angular_order():
    """Every gap is in ]0, π[ and nothing crosses, yet the sweep exceeds one turn: only the order check can refuse it."""
    spiral = [(500, 145), (789, 660), (280, 637), (489, 298), (675, 585), (434, 546)]
    errors = geometry_errors(hand(spiral, closed=False))
    assert len(errors) == 1 and errors[0].startswith("radial : angle polaire strictement croissant")
    assert evaluate(spiral, False, (500, 500)) is None


def test_an_open_spiral_returning_to_the_ray_of_p1_is_rejected_by_both_implementations():
    spiral = [(500, 160), (780, 500), (500, 720), (340, 500), (500, 400), (560, 500)]  # P5 is on P1's ray
    assert cd.evaluate(spiral, False, (500, 500)) is None
    assert any(e.startswith("radial") for e in geometry_errors(hand(spiral, closed=False)))
    assert cd.evaluate(spiral[:5], False, (500, 500)) is None  # same ray as the LAST point: the wrap gap is 0
    assert any(e.startswith("radial") for e in geometry_errors(hand(spiral[:5], closed=False)))


@pytest.mark.parametrize("closed", MODES)
def test_an_angular_gap_of_exactly_pi_is_rejected(closed):
    """P1 and P2 are opposite through the centre: the edge passes through it, gap = π, not strictly below."""
    opposite = [(500, 100), (500, 900), (200, 700), (150, 500), (200, 300)]
    errors = geometry_errors(hand(opposite, closed=closed))
    assert errors == ["radial : écart angulaire des points 1 et 2 hors de ]0, π["]
    assert evaluate(opposite, closed, (500, 500)) is None


def test_grid_bounds_are_enforced_exactly():
    inside = [(500, 100), (850, 450), (650, 850), (250, 800), (150, 400)]
    assert geometry_errors(hand(inside)) == []
    for bad in ((49, 400), (951, 400), (150, 49), (150, 951), (-5, 400), (1000, 400)):
        errors = geometry_errors(hand(inside[:-1] + [bad]))
        assert any(e.startswith("points et centre") for e in errors), bad
    assert any(e.startswith("points et centre") for e in geometry_errors(hand(inside, centre=(49, 500))))


def test_verifier_never_raises_on_hostile_geometry():
    rng = random.Random(99)
    for _ in range(300):
        count = rng.randint(5, 8)
        pts = [(rng.choice([50, 100, 500, 950]), rng.choice([50, 100, 500, 950])) for _ in range(count)]
        record = hand(pts, rng.random() < 0.5, (rng.choice([50, 500, 950]), rng.choice([50, 500, 950])))
        assert isinstance(verify_connect_dots_v2(record), list)
        assert isinstance(diagnose_connect_dots_v2(record), list)


# ---- the exact verdict is the authority; the float helper is a diagnostic only ---------------------------------------------
def test_float_disagreement_is_reported_but_never_a_rejection(sample, monkeypatch):
    monkeypatch.setattr(cdv, "segments_touch", lambda *a, **k: True)  # worst case: claims every pair touches
    assert verify_connect_dots_v2(sample) == [] and verify_v2(sample) == []
    notes = diagnose_connect_dots_v2(sample)
    assert notes and all("verdict exact conservé" in n for n in notes)
    monkeypatch.setattr(cdv, "segments_touch", lambda *a, **k: False)
    bow = hand([(100, 100), (900, 100), (100, 900), (900, 900), (500, 500)])
    assert has(geometry_errors(bow), "C3")  # a float helper saying "no touch" does not rescue an invalid figure
    assert any("verdict exact conservé" in n for n in diagnose_connect_dots_v2(bow))


def test_diagnostic_never_raises_on_huge_or_out_of_grid_integers(sample):
    for value in (10**400, -(10**400), 1001, -1):
        data = sample.to_dict()
        data["geometry"]["points"][3]["x"] = value
        assert diagnose_connect_dots_v2(data) == []
        assert has(verify_connect_dots_v2(refingerprint(data)), "points et centre")


def test_historical_float_helper_agrees_on_valid_records():
    for closed in MODES:
        for count in (5, 12, 24):
            assert diagnose_connect_dots_v2(make(count, closed, 4)) == []


# ---- falsification: any change is detected, with or without a refreshed fingerprint --------------------------------------------
def mutations():
    def move(d):
        d["geometry"]["points"][2]["x"] += 1

    def swap_numbers(d):
        p = d["geometry"]["points"]
        p[1]["n"], p[2]["n"] = p[2]["n"], p[1]["n"]

    def swap_points(d):
        p = d["geometry"]["points"]
        p[1], p[2] = p[2], p[1]

    def drop(d):
        d["geometry"]["points"].pop()

    def add(d):
        d["geometry"]["points"].append({"n": 9, "x": 500, "y": 500})

    def duplicate(d):
        d["geometry"]["points"][3]["x"], d["geometry"]["points"][3]["y"] = d["geometry"]["points"][2]["x"], d["geometry"]["points"][2]["y"]

    def centre(d):
        d["geometry"]["center"] = [900, 900]

    def centre_float(d):
        d["geometry"]["center"] = [500.0, 500]

    def float_coord(d):
        d["geometry"]["points"][0]["x"] = float(d["geometry"]["points"][0]["x"])

    def bool_coord(d):
        d["geometry"]["points"][0]["n"] = True

    def str_coord(d):
        d["geometry"]["points"][0]["y"] = str(d["geometry"]["points"][0]["y"])

    def out_of_grid(d):
        d["geometry"]["points"][0]["x"] = 1000

    def extra_point_key(d):
        d["geometry"]["points"][0]["z"] = 0

    def reverse_order(d):
        d["solution"]["order"].reverse()

    def close_to(d):
        d["solution"]["close_to"] = None

    def closed_flag(d):
        d["geometry"]["closed"] = False

    def params_closed(d):
        d["params"]["closed"] = False

    def params_points(d):
        d["params"]["points"] = 9

    def shape(d):
        d["geometry"]["shape"] = "star"

    def grid(d):
        d["geometry"]["grid"] = 1001

    def clearance(d):
        d["measures"]["min_clearance_sq_floor"] += 1

    def area(d):
        d["measures"]["twice_area"] = None

    def measure_type(d):
        d["measures"]["point_count"] = 8.0

    def attempts_zero(d):
        d["search"]["attempts"] = 0

    def attempts_big(d):
        d["search"]["attempts"] = cd.MAX_ATTEMPTS + 1

    def max_attempts(d):
        d["search"]["max_attempts"] = 10

    def search_extra(d):
        d["search"]["algorithm"] = "backtracker"

    def kind(d):
        d["kind"] = "PRODUCTION"

    def schema(d):
        d["schema"] = "lafractale-mechanics-v2-activity-v2"

    def version(d):
        d["version"] = "b3b3b2-connect-dots-v2-9.9"

    def mechanic(d):
        d["mechanic"] = "maze_v2"

    def authorised(d):
        d["production_authorized"] = True

    def pedagogy(d):
        d["human_pedagogical_validation"] = "VALIDATED"

    def seed(d):
        d["seed"] = 2**63

    def activity(d):
        d["activity_id"] = "page-17"

    def extra_key(d):
        d["editorial_status"] = "VALIDATED"

    def missing_key(d):
        del d["measures"]

    return {fn.__name__: fn for fn in (
        move, swap_numbers, swap_points, drop, add, duplicate, centre, centre_float, float_coord, bool_coord, str_coord,
        out_of_grid, extra_point_key, reverse_order, close_to, closed_flag, params_closed, params_points, shape, grid,
        clearance, area, measure_type, attempts_zero, attempts_big, max_attempts, search_extra, kind, schema, version,
        mechanic, authorised, pedagogy, seed, activity, extra_key, missing_key)}


@pytest.mark.parametrize("name", sorted(mutations()))
def test_every_tampering_is_detected(name, sample):
    mutate = mutations()[name]
    assert verify_connect_dots_v2(tampered(sample, mutate, refinger=False)) != []
    assert verify_connect_dots_v2(tampered(sample, mutate, refinger=True)) != []


def test_fingerprint_alone_is_not_a_proof_of_validity(sample):
    forged = tampered(sample, lambda d: d["geometry"]["points"][2].__setitem__("x", d["geometry"]["points"][2]["x"] + 1))
    assert forged["fingerprint"] == record_fingerprint(forged)  # internally consistent ...
    assert verify_connect_dots_v2(forged) != []  # ... yet the geometry or the measures are wrong
    flipped = tampered(sample, lambda d: d.__setitem__("fingerprint", "0" * 64), refinger=False)
    assert any(e.startswith("fingerprint") for e in verify_connect_dots_v2(flipped))


def test_forged_valid_geometry_with_stale_measures_is_detected(sample):
    other = make(8, True, 2).to_dict()
    forged = copy.deepcopy(sample.to_dict())
    forged["geometry"], forged["solution"], forged["params"] = other["geometry"], other["solution"], other["params"]
    errors = verify_connect_dots_v2(refingerprint(forged))
    assert errors and has(errors, "measures")


def test_verifier_rejects_non_mappings_and_garbage():
    for junk in (None, 3, "x", [], {}, {"mechanic": "connect_dots_v2"}):
        assert verify_connect_dots_v2(junk) != []  # type: ignore[arg-type]
    assert verify_v2({"mechanic": "unknown_v2"}) != [] and verify_v2(None) != []  # type: ignore[arg-type]


# ---- immutability and non-authorisation ---------------------------------------------------------------------------------------
def test_outputs_are_immutable_and_copies_are_independent(sample):
    before = sample.canonical_bytes()
    with pytest.raises((AttributeError, TypeError)):
        sample.geometry["points"] = ()  # type: ignore[index]
    with pytest.raises((TypeError, AttributeError)):
        sample.geometry["points"][0]["x"] = 0  # type: ignore[index]
    with pytest.raises((AttributeError, TypeError)):
        sample.geometry["points"].append(1)  # type: ignore[attr-defined]
    data = sample.to_dict()
    data["geometry"]["points"].clear()
    data["geometry"]["center"][0] = 0
    assert sample.canonical_bytes() == before and verify_connect_dots_v2(sample) == []


def test_direct_construction_freezes_and_production_stays_false(sample, monkeypatch):
    monkeypatch.setenv("PRODUCTION_AUTHORIZED", "1")
    data = sample.to_dict()
    rebuilt = V2Activity(data["mechanic"], data["version"], data["activity_id"], data["seed"], data["params"], data["geometry"],
                         data["solution"], data["measures"], data["search"], data["fingerprint"])  # plain dicts in, frozen out
    data["geometry"]["points"].clear()
    assert rebuilt.canonical_bytes() == sample.canonical_bytes() and verify_connect_dots_v2(rebuilt) == []
    assert PRODUCTION_AUTHORIZED is False and sample.production_authorized is False
    assert sample.to_dict()["production_authorized"] is False


# ---- separation from editorial data, the historical engine and the rest of the repository ------------------------------------------
def _imports(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_connect_dots_modules_are_isolated_from_editorial_data():
    for name in ("connect_dots.py", "connect_dots_verify.py"):
        path = PKG / name
        imports = _imports(path)
        foreign = {n for n in imports if n.startswith("lafractale") and not n.startswith("lafractale.mechanics_v2")}
        assert foreign <= {"lafractale.engine.solvers"}, (name, foreign)
        assert not {n for n in imports if n.split(".")[0] in {"csv", "yaml", "os", "subprocess", "socket", "urllib", "pathlib",
                                                             "shutil", "random", "time", "datetime", "math"}}, name
        module = ast.parse(path.read_text(encoding="utf-8"))
        module.body[0].value.value = ""
        code = ast.unparse(module)
        for token in ("PageRecord", "scenario_b", "load_pages", "open(", "environ", "getenv", "argv", "write_text", "SpecSet", ".csv", "float("):
            assert token not in code, (name, token)
    assert "lafractale.engine.solvers" not in _imports(PKG / "connect_dots.py")  # the generator relies on nothing historical


def test_generator_geometry_has_no_float_or_trigonometry():
    tree = ast.parse((PKG / "connect_dots.py").read_text(encoding="utf-8"))
    tree.body[0].value.value = ""  # the module docstring explains why these are absent
    code = ast.unparse(tree)
    for token in ("atan2", "cos(", "sin(", "sqrt", "hypot", " / ", "1e-", "epsilon", "import math"):
        assert token not in code, token
    assert not [n for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, float)]


def test_no_page_or_editorial_object_can_parametrise_a_generation():
    from lafractale.scenario_b.pages import load_pages
    pages = load_pages(ROOT)
    for source in (pages.page(17), pages, pages.page(17).to_dict(), "PageRecord", object()):
        with pytest.raises(V2Error):
            generate_v2("connect_dots_v2", "syn-a", 0, source)  # type: ignore[arg-type]
    with pytest.raises(V2Error):
        generate_v2("connect_dots_v2", pages.page(17).title, 0, {"points": 8, "closed": True, "shape": "radial"})
    # the real p.17 number of points is unknown (HUMAN_REVIEW): nothing here reads or guesses it
    assert set(cd.PARAM_SPEC) == {"points", "closed", "shape"}


def test_nothing_historical_imports_v2_and_historical_registry_is_untouched():
    offenders = [str(p.relative_to(ROOT)) for p in (ROOT / "src/lafractale").rglob("*.py")
                 if "mechanics_v2" not in p.parts and "mechanics_v2" in p.read_text(encoding="utf-8")]
    assert offenders == []
    from lafractale.engine import registry as historical
    assert "connect_dots_v2" not in Path(historical.__file__).read_text(encoding="utf-8")


def test_generation_writes_nothing(monkeypatch):
    import builtins
    import os
    writes = []
    real_open, real_os_open = builtins.open, os.open
    monkeypatch.setattr(builtins, "open", lambda f, m="r", *a, **k: (writes.append(f) if set(m) & set("wax+") else None, real_open(f, m, *a, **k))[1])
    monkeypatch.setattr(os, "open", lambda p, fl, *a, **k: (writes.append(p) if fl & (os.O_WRONLY | os.O_RDWR | os.O_CREAT) else None, real_os_open(p, fl, *a, **k))[1])
    make(24, True, 5)
    make(24, False, 5)
    assert writes == []
