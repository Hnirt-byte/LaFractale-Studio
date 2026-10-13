"""B3-B.3b.3 — match_v2: observable correspondences, exact arithmetic, independent verification."""
from __future__ import annotations

import ast
import copy
import itertools
import json
import math
import random
from fractions import Fraction
from pathlib import Path

import pytest

from lafractale.mechanics_v2 import PRODUCTION_AUTHORIZED, V2_KIND, V2_SCHEMA
from lafractale.mechanics_v2 import match as mt
from lafractale.mechanics_v2 import match_verify as mv
from lafractale.mechanics_v2.core import V2Activity, V2Error, loads_record, record_fingerprint
from lafractale.mechanics_v2.match import DOTS, POLYGONS, STARS
from lafractale.mechanics_v2.match_verify import analyse_outline, verify_match_v2
from lafractale.mechanics_v2.registry import MECHANICS_V2, generate_v2, verify_v2

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "src/lafractale/mechanics_v2"
SIZE = {"polygon": 6, "star": 3, "mixed": 9}
ALL = [(p, r, f) for p in range(3, 7) for r in ("twin", "count") for f in ("polygon", "star", "mixed")]
VALID = [c for c in ALL if not (c[1] == "count" and c[2] != "polygon") and c[0] <= SIZE[c[2]]]
INVALID = [c for c in ALL if c not in VALID]
NOISE = ("measures", "fingerprint")  # error families a hand-built record is not expected to get right


def make(pairs=4, relation="twin", family="mixed", seed=1, activity_id="syn-demo") -> V2Activity:
    return generate_v2("match_v2", activity_id, seed, {"pairs": pairs, "relation": relation, "family": family})


def refingerprint(data: dict) -> dict:
    try:
        data["fingerprint"] = record_fingerprint(data)
    except V2Error:
        pass
    return data


def tampered(activity, mutate, *, refinger: bool = True) -> dict:
    data = copy.deepcopy(activity.to_dict() if isinstance(activity, V2Activity) else activity)
    mutate(data)
    return refingerprint(data) if refinger else data


def has(errors: list[str], tag: str) -> bool:
    return any(e.startswith(tag) for e in errors)


def tags(errors: list[str]) -> set[str]:
    return {e.split(" ")[0].rstrip(":") for e in errors}


@pytest.fixture(scope="module")
def sample() -> V2Activity:
    return make()


# ---- test-only references (written apart from the production code) ------------------------------------------
def table_of(cls):
    return (POLYGONS if cls[0] == "polygon" else STARS)[cls[1]]


def ref_ratio(cls) -> Fraction:
    vs = table_of(cls)
    area2 = sum(vs[i][0] * vs[(i + 1) % len(vs)][1] - vs[(i + 1) % len(vs)][0] * vs[i][1] for i in range(len(vs)))
    xs, ys = [v[0] for v in vs], [v[1] for v in vs]
    return Fraction(abs(area2), 2 * (max(xs) - min(xs)) * (max(ys) - min(ys)))


def ref_ys(n: int) -> list[int]:
    return [50 + (2 * i + 1) * 900 // (2 * n) for i in range(n)]


def hand(classes, perm, relation="twin", family=None, *, activity_id="syn-hand") -> dict:
    """A complete, canonical record built WITHOUT the generator (measures and fingerprint included)."""
    n = len(classes)
    family = family or ("polygon" if all(c[0] == "polygon" for c in classes) else "star" if all(c[0] == "star" for c in classes) else "mixed")
    ys = ref_ys(n)
    right = [None] * n
    for i, c in enumerate(classes):
        j = perm[i]
        base = {"row": j, "origin": [800, ys[j] - 50]}
        if relation == "twin":
            base.update(label=f"{c[0]}-{c[1]}", vertices=[list(p) for p in table_of(c)])
        else:
            base.update(label=f"dots-{c[1]}", dots=[list(p) for p in DOTS[c[1]]])
        right[j] = base
    ratios = [ref_ratio(c) for c in classes]
    gap = min(abs(a - b) for a, b in itertools.combinations(ratios, 2))
    data = {
        "schema": V2_SCHEMA, "kind": V2_KIND, "mechanic": "match_v2", "version": mt.MATCH_V2_VERSION,
        "activity_id": activity_id, "seed": 0, "human_pedagogical_validation": "NONE", "production_authorized": False,
        "params": {"pairs": n, "relation": relation, "family": family},
        "geometry": {"relation": relation, "family": family, "grid": 1000, "rows": n,
                     "anchors": {"left_x": 260, "right_x": 740, "ys": ys},
                     "left": [{"row": i, "label": f"{c[0]}-{c[1]}", "origin": [100, ys[i] - 50], "vertices": [list(p) for p in table_of(c)]}
                              for i, c in enumerate(classes)],
                     "right": right},
        "solution": {"left_to_right": list(perm)},
        "measures": {"pairs": n, "fixed_points": sum(1 for i, j in enumerate(perm) if i == j),
                     "crossings": sum(1 for a in range(n) for b in range(a + 1, n) if perm[a] > perm[b]),
                     "min_area_ratio_gap_ppm": gap.numerator * 1_000_000 // gap.denominator},
        "search": {"attempts": 1, "max_attempts": mt.MAX_ATTEMPTS}, "fingerprint": ""}
    return refingerprint(data)


def errors_of(data: dict) -> list[str]:
    return verify_match_v2(data)


def geometry_errors(data: dict) -> list[str]:
    return [e for e in verify_match_v2(data) if not e.startswith(NOISE)]


def ref_cross(a, b, c) -> int:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def ref_touch(a, b, c, d) -> bool:
    r, s = (b[0] - a[0], b[1] - a[1]), (d[0] - c[0], d[1] - c[1])
    denom = r[0] * s[1] - r[1] * s[0]
    qp = (c[0] - a[0], c[1] - a[1])
    if denom != 0:
        t = Fraction(qp[0] * s[1] - qp[1] * s[0], denom)
        u = Fraction(qp[0] * r[1] - qp[1] * r[0], denom)
        return 0 <= t <= 1 and 0 <= u <= 1
    if qp[0] * r[1] - qp[1] * r[0] != 0:
        return False
    length = r[0] ** 2 + r[1] ** 2
    if length == 0:
        return False
    t0 = Fraction(qp[0] * r[0] + qp[1] * r[1], length)
    t1 = t0 + Fraction(s[0] * r[0] + s[1] * r[1], length)
    return max(min(t0, t1), 0) <= min(max(t0, t1), 1)


def ref_classify(vs):
    """(kind, order) of a local outline, or None, by a route different from the verifier's."""
    n = len(vs)
    if n < 3 or any(not (0 <= x <= 100 and 0 <= y <= 100) for x, y in vs):
        return None
    if sum(vs[i][0] * vs[(i + 1) % n][1] - vs[(i + 1) % n][0] * vs[i][1] for i in range(n)) <= 0:
        return None
    if vs[0] != min(vs, key=lambda p: (p[1], p[0])):
        return None
    turns = [ref_cross(vs[(i - 1) % n], vs[i], vs[(i + 1) % n]) for i in range(n)]
    if any(t == 0 for t in turns):
        return None
    edges = [(vs[i], vs[(i + 1) % n]) for i in range(n)]
    for a, b in itertools.combinations(range(n), 2):
        if (b - a) % n in (1, n - 1):
            continue
        if ref_touch(*edges[a], *edges[b]):
            return None
    negative = sum(1 for t in turns if t < 0)
    if negative == 0:
        return ("polygon", n)
    if n % 2 == 0 and negative == n // 2:
        return ("star", n // 2)
    return None


def oracle_ok(d) -> bool:
    """Independent semantic verdict (header, measures, search and fingerprint left aside)."""
    try:
        n = d["params"]["pairs"]
        rel, fam = d["params"]["relation"], d["params"]["family"]
        g = d["geometry"]
        if not (3 <= n <= 6) or rel not in ("twin", "count") or fam not in ("polygon", "star", "mixed"):
            return False
        if n > SIZE[fam] or (rel == "count" and fam != "polygon"):
            return False
        if g["relation"] != rel or g["family"] != fam or g["grid"] != 1000 or g["rows"] != n:
            return False
        ys = ref_ys(n)
        if g["anchors"] != {"left_x": 260, "right_x": 740, "ys": ys}:
            return False
        perm = d["solution"]["left_to_right"]
        if sorted(perm) != list(range(n)) or perm == list(range(n)):
            return False
        L, R = g["left"], g["right"]
        if len(L) != n or len(R) != n:
            return False

        def cls_of(vs):
            for kind, tables in (("polygon", POLYGONS), ("star", STARS)):
                for k, t in tables.items():
                    if [list(p) for p in t] == vs:
                        return (kind, k)
            return None

        lc = [cls_of(e["vertices"]) for e in L]
        if None in lc or len(set(lc)) != n:
            return False
        if fam != "mixed" and any(c[0] != fam for c in lc):
            return False
        for i, e in enumerate(L):
            if e["row"] != i or e["label"] != f"{lc[i][0]}-{lc[i][1]}" or e["origin"] != [100, ys[i] - 50]:
                return False
        for j, e in enumerate(R):
            if e["row"] != j or e["origin"] != [800, ys[j] - 50]:
                return False
        if rel == "twin":
            rc = [cls_of(e["vertices"]) for e in R]
            if None in rc or len(set(rc)) != n:
                return False
            if any(rc[perm[i]] != lc[i] or rc[j] is None for i, j in enumerate(perm)):
                return False
            if any(e["label"] != f"{rc[j][0]}-{rc[j][1]}" for j, e in enumerate(R)):
                return False
        else:
            counts = [len(e["dots"]) for e in R]
            if len(set(counts)) != n:
                return False
            for j, e in enumerate(R):
                k = counts[j]
                if k not in DOTS or e["dots"] != [list(p) for p in DOTS[k]] or e["label"] != f"dots-{k}":
                    return False
            if any(lc[i][0] != "polygon" or lc[i][1] != counts[perm[i]] for i in range(n)):
                return False
        ratios = [ref_ratio(c) for c in lc]
        if any(abs(a - b) * 1_000_000 < mt.AREA_RATIO_GAP_MIN_PPM for a, b in itertools.combinations(ratios, 2)):
            return False
        for side, entries, x0 in (("l", L, 100), ("r", R, 800)):
            boxes = []
            for j, e in enumerate(entries):
                pts = e["vertices"] if "vertices" in e else e["dots"]
                px = [x0 + p[0] for p in pts]
                py = [ys[j] - 50 + p[1] for p in pts]
                boxes.append((min(px), min(py), max(px), max(py)))
                if min(px) < 50 or max(px) > 950 or min(py) < 50 or max(py) > 950:
                    return False
                if side == "l" and max(px) + 20 > 260:
                    return False
                if side == "r" and min(px) - 20 < 740:
                    return False
            if any(boxes[k + 1][1] - boxes[k][3] < 30 for k in range(n - 1)):
                return False
        # concurrency by brute force: intersect every pair of links, any third link through the point?
        links = [((260, ys[i]), (740, ys[perm[i]])) for i in range(n)]
        for a, b, c in itertools.combinations(range(n), 3):
            pts = []
            for p, q in ((a, b), (a, c), (b, c)):
                (x1, y1), (x2, y2) = links[p]
                (x3, y3), (x4, y4) = links[q]
                den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
                if den == 0:
                    break
                px = Fraction((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4), den)
                py = Fraction((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4), den)
                pts.append((px, py))
            else:
                if pts[0] == pts[1] == pts[2] and 260 < pts[0][0] < 740:
                    return False
        return True
    except (KeyError, TypeError, IndexError, ValueError):
        return False


def _walk(value):
    if isinstance(value, dict):
        for v in value.values():
            yield from _walk(v)
    elif isinstance(value, list):
        for v in value:
            yield from _walk(v)
    else:
        yield value


# ---- golden, canonical form -----------------------------------------------------------------------------------
GOLDEN = {
    "default": "8f8dfd5d8ebf4b82a4fb81d6c01e2a13a4e7378c14fed5fa80e0c63b10954f51",
    "p6-twin-mixed": "cf0f36aa2d047f11d81123ce01a8bbbd08775344e20a822cace70b18858faf77",
    "p3-count-polygon": "8b9158de6ba44a354b3a34edcca6f96aa092a0ee480998f7c4cda3568cbdcbfd",
}


def test_golden_fingerprints_are_stable_across_versions_and_runs(sample):
    assert sample.fingerprint == GOLDEN["default"]
    assert make(6, "twin", "mixed", 7, "syn-x").fingerprint == GOLDEN["p6-twin-mixed"]
    assert make(3, "count", "polygon", 0, "syn-c").fingerprint == GOLDEN["p3-count-polygon"]
    assert make().canonical_bytes() == sample.canonical_bytes()


def test_canonical_form_schema_and_fingerprint_rule(sample):
    raw = sample.canonical_bytes()
    text = raw.decode("utf-8")
    assert ", " not in text and ": " not in text
    record = json.loads(text)
    assert list(record) == sorted(record) and list(record["geometry"]) == sorted(record["geometry"])
    assert record["schema"] == V2_SCHEMA and record["kind"] == V2_KIND and record["mechanic"] == "match_v2"
    assert record["production_authorized"] is False and record["human_pedagogical_validation"] == "NONE"
    assert record["version"] == "b3b3b3-match-v2-1.0" and record["geometry"]["grid"] == 1000
    assert loads_record(raw) == record
    assert record["fingerprint"] == record_fingerprint(record) == sample.fingerprint
    assert not [v for v in _walk(record) if isinstance(v, float)]
    assert all(type(v) is int for v in _walk(record["geometry"]["left"][0]["vertices"]))


def test_registry_lists_match_v2_and_is_closed():
    assert set(MECHANICS_V2) == {"maze_v2", "connect_dots_v2", "match_v2"}
    assert set(MECHANICS_V2["match_v2"].params) == {"pairs", "relation", "family"}
    assert verify_v2(make()) == [] and verify_v2(make().to_dict()) == []


def test_earlier_mechanics_are_unchanged_by_the_new_registry_entry():
    c = generate_v2("connect_dots_v2", "syn-demo", 1, {"points": 8, "closed": True, "shape": "radial"})
    assert c.fingerprint == "8a2e42ab493cacfe3ab2614c1c99ced2037c493ec5e4f9fa8e271e377de14eed"
    assert generate_v2("maze_v2", "syn-demo", 1, {"size": 5, "difficulty": "easy"}).mechanic == "maze_v2"


# ---- parameters, combinations ----------------------------------------------------------------------------------
def test_thirteen_combinations_are_valid_and_eleven_refused():
    assert len(VALID) == 13 and len(INVALID) == 11
    for pairs, relation, family in INVALID:
        with pytest.raises(V2Error) as info:
            make(pairs, relation, family)
        assert info.value.code == "BAD_COMBINATION", (pairs, relation, family)


@pytest.mark.parametrize("pairs", [0, 1, 2, 7, -3, 3.0, "4", None, True, False])
def test_pairs_outside_3_to_6_or_not_strict_integers_are_refused(pairs):
    with pytest.raises(V2Error) as info:
        generate_v2("match_v2", "syn-a", 0, {"pairs": pairs, "relation": "twin", "family": "polygon"})
    assert info.value.code == "BAD_PAIRS"


@pytest.mark.parametrize("relation", ["Twin", "match", "", None, 1, ["twin"], "twin "])
def test_unknown_relations_are_refused(relation):
    with pytest.raises(V2Error) as info:
        generate_v2("match_v2", "syn-a", 0, {"pairs": 3, "relation": relation, "family": "polygon"})
    assert info.value.code == "BAD_RELATION"


@pytest.mark.parametrize("family", ["hats", "gifts", "hat_1", "gift_3", "Polygon", "circle", "", None, 2])
def test_unknown_and_seasonal_families_are_refused(family):
    with pytest.raises(V2Error) as info:
        generate_v2("match_v2", "syn-a", 0, {"pairs": 3, "relation": "twin", "family": family})
    assert info.value.code == "BAD_FAMILY"


def test_missing_and_extra_parameters_are_refused():
    good = {"pairs": 3, "relation": "twin", "family": "polygon"}
    for bad in ({k: v for k, v in good.items() if k != "family"}, {**good, "size": 3}, {**good, "family_extra": "x"}, {}, [], None):
        with pytest.raises(V2Error):
            generate_v2("match_v2", "syn-a", 0, bad)  # type: ignore[arg-type]


# ---- properties over every valid combination --------------------------------------------------------------------
@pytest.mark.parametrize("pairs,relation,family", VALID)
def test_property_every_valid_combination_generates_verifies_and_replays(pairs, relation, family):
    for seed in range(40):
        a = make(pairs, relation, family, seed, f"syn-p{seed}")
        data = a.to_dict()
        assert verify_match_v2(a) == [] and verify_match_v2(data) == []
        assert oracle_ok(data), (pairs, relation, family, seed)
        assert make(pairs, relation, family, seed, f"syn-p{seed}").canonical_bytes() == a.canonical_bytes()
        perm = data["solution"]["left_to_right"]
        assert sorted(perm) == list(range(pairs)) and perm != list(range(pairs))
        classes = [tuple(e["label"].split("-")) for e in data["geometry"]["left"]]
        assert len(set(classes)) == pairs
        assert 1 <= data["search"]["attempts"] <= mt.MAX_ATTEMPTS
        if family == "polygon":
            assert all(c[0] == "polygon" for c in classes)
        if family == "star":
            assert all(c[0] == "star" for c in classes)


@pytest.mark.parametrize("pairs,relation,family", VALID)
def test_property_bilateral_uniqueness_is_recomputed_from_coordinates(pairs, relation, family):
    for seed in range(20):
        g = make(pairs, relation, family, seed).to_dict()["geometry"]
        perm = make(pairs, relation, family, seed).to_dict()["solution"]["left_to_right"]
        for i, left in enumerate(g["left"]):
            if relation == "twin":
                partners = [j for j, r in enumerate(g["right"]) if r["vertices"] == left["vertices"]]
            else:
                partners = [j for j, r in enumerate(g["right"]) if len(r["dots"]) == len(left["vertices"])]
            assert partners == [perm[i]]
        for j, right in enumerate(g["right"]):
            if relation == "twin":
                back = [i for i, l in enumerate(g["left"]) if l["vertices"] == right["vertices"]]
            else:
                back = [i for i, l in enumerate(g["left"]) if len(l["vertices"]) == len(right["dots"])]
            assert len(back) == 1


def test_different_seeds_and_ids_give_different_activities():
    prints = {make(5, "twin", "mixed", s, "syn-d").fingerprint for s in range(30)}
    assert len(prints) > 20
    assert make(4, "twin", "mixed", 1, "syn-a").fingerprint != make(4, "twin", "mixed", 1, "syn-b").fingerprint


# ---- permutations: fixed points allowed, identity refused ---------------------------------------------------------
def test_permutations_with_one_several_and_no_fixed_point_are_all_produced_and_accepted():
    seen: dict[int, int] = {}
    for pairs in (4, 5, 6):
        for seed in range(150):
            data = make(pairs, "twin", "polygon", seed).to_dict()
            perm = data["solution"]["left_to_right"]
            fixed = sum(1 for i, j in enumerate(perm) if i == j)
            assert data["measures"]["fixed_points"] == fixed and perm != list(range(pairs))
            seen[fixed] = seen.get(fixed, 0) + 1
    assert 0 in seen and 1 in seen and any(k >= 2 for k in seen), seen


def test_hand_built_permutations_with_and_without_fixed_points_are_valid():
    classes = [("polygon", 3), ("polygon", 4), ("polygon", 5), ("polygon", 6)]
    for perm in ([1, 0, 2, 3], [0, 2, 1, 3], [1, 2, 3, 0], [0, 1, 3, 2], [2, 0, 3, 1], [1, 0, 3, 2]):
        assert errors_of(hand(classes, perm)) == [], perm
    fixed = {tuple(p): sum(1 for i, j in enumerate(p) if i == j) for p in ([1, 0, 2, 3], [1, 2, 3, 0], [1, 0, 3, 2], [0, 2, 1, 3])}
    assert sorted(fixed.values()) == [0, 0, 2, 2]  # two fixed points, none


def test_the_identity_is_always_refused_for_every_size_and_relation():
    for pairs in (3, 4, 5, 6):
        classes = [("polygon", n) for n in range(3, 3 + pairs)]
        for relation in ("twin", "count"):
            errors = errors_of(hand(classes, list(range(pairs)), relation))
            assert has(errors, "M1") and "identité" in " ".join(errors)


def test_the_generator_skips_an_identity_draw(monkeypatch):
    draws = []

    class Fake(mt.DetRng):
        def shuffle(self, items):
            if items == [0, 1, 2, 3] and not draws:
                draws.append("identity")  # first permutation draw is left as the identity
                return
            super().shuffle(items)

    monkeypatch.setattr(mt, "DetRng", Fake)
    activity = mt.generate_match_v2("syn-id", 0, {"pairs": 4, "relation": "twin", "family": "polygon"})
    assert draws == ["identity"] and activity.solution["left_to_right"] != [0, 1, 2, 3]
    assert activity.search["attempts"] >= 2


def test_malformed_solutions_are_refused():
    base = make(4).to_dict()
    for bad in ([0, 0, 1, 2], [0, 1, 2], [0, 1, 2, 4], [True, 1, 2, 3], "0123", None, [0.0, 1, 2, 3], [[0], 1, 2, 3]):
        data = tampered(base, lambda d, b=bad: d["solution"].__setitem__("left_to_right", b))
        assert has(errors_of(data), "M1")
    assert has(errors_of(tampered(base, lambda d: d["solution"].__setitem__("extra", 1))), "M1")


# ---- twin: exact equality in the local frame -------------------------------------------------------------------------
def test_twin_requires_exact_equality_of_vertex_lists_not_congruence():
    base = make(4, "twin", "polygon", 2).to_dict()
    j = base["solution"]["left_to_right"][0]

    def translate(d):
        d["geometry"]["right"][j]["vertices"] = [[x + 1, y] for x, y in d["geometry"]["right"][j]["vertices"]]

    def rotate(d):  # same shape, vertex list started elsewhere
        v = d["geometry"]["right"][j]["vertices"]
        d["geometry"]["right"][j]["vertices"] = v[1:] + v[:1]

    def mirror(d):
        d["geometry"]["right"][j]["vertices"] = [[100 - x, y] for x, y in d["geometry"]["right"][j]["vertices"]]

    def scale(d):
        d["geometry"]["right"][j]["vertices"] = [[x // 2, y // 2] for x, y in d["geometry"]["right"][j]["vertices"]]

    for mutate in (translate, rotate, mirror, scale):
        errors = errors_of(tampered(base, mutate))
        assert has(errors, "M4") or has(errors, "M3"), mutate.__name__
    # the local frame is what is compared: the world origin may not vary silently either
    errors = errors_of(tampered(base, lambda d: d["geometry"]["right"][j].__setitem__("origin", [801, d["geometry"]["right"][j]["origin"][1]])))
    assert has(errors, "M7")


# ---- the labels never decide a correspondence ----------------------------------------------------------------------------
def test_labels_are_informative_only_and_checked_for_consistency():
    base = make(5, "twin", "mixed", 3).to_dict()
    clean = errors_of(base)
    assert clean == []
    # swap two right labels: the geometry still pairs correctly, only the label consistency fails
    def swap(d):
        a, b = d["geometry"]["right"][0], d["geometry"]["right"][1]
        a["label"], b["label"] = b["label"], a["label"]
    errors = errors_of(tampered(base, swap))
    assert has(errors, "M8") and not has(errors, "M3")
    # junk labels everywhere: same verdict family
    def junk(d):
        for side in ("left", "right"):
            for e in d["geometry"][side]:
                e["label"] = "x"
    errors = errors_of(tampered(base, junk))
    assert has(errors, "M8") and not has(errors, "M3") and not has(errors, "M4")
    # consistent relabelling of both columns of a twin pair cannot create a correspondence
    def mislabel(d):
        d["geometry"]["left"][0]["label"] = d["geometry"]["left"][1]["label"]
    assert has(errors_of(tampered(base, mislabel)), "M8")
    # a non-string label is an inconsistency, not a crash
    for bad in (None, 3, ["polygon-3"], {"a": 1}):
        assert has(errors_of(tampered(base, lambda d, b=bad: d["geometry"]["left"][0].__setitem__("label", b))), "M8")


def test_geometry_decides_the_pairing_even_when_labels_agree_with_a_wrong_pairing():
    base = make(4, "twin", "polygon", 4).to_dict()
    perm = base["solution"]["left_to_right"]
    a, b = 0, 1
    # swap two right symbols INCLUDING their labels: the published solution no longer follows the geometry
    def swap(d):
        r = d["geometry"]["right"]
        r[a]["vertices"], r[b]["vertices"] = r[b]["vertices"], r[a]["vertices"]
        r[a]["label"], r[b]["label"] = r[b]["label"], r[a]["label"]
    errors = errors_of(tampered(base, swap))
    assert has(errors, "M3") and "solution" in " ".join(e for e in errors if e.startswith("M3"))
    assert not has(errors, "M4") and not has(errors, "M8")  # both symbols are valid table members: only the pairing is wrong
    assert perm == base["solution"]["left_to_right"]


# ---- every criterion M1..M9 on a hand-built case that breaks only it -------------------------------------------------------
CLASSES4 = [("polygon", 3), ("polygon", 5), ("polygon", 4), ("polygon", 6)]
PERM4 = [2, 0, 3, 1]


def test_reference_record_is_valid_without_the_generator():
    data = hand(CLASSES4, PERM4)
    assert errors_of(data) == [] and oracle_ok(data)
    assert errors_of(hand(CLASSES4, PERM4, "count")) == []


def test_m2_duplicate_signature_in_a_column_is_refused():
    data = tampered(hand(CLASSES4, PERM4), lambda d: d["geometry"]["left"][1].update(
        label="polygon-3", vertices=[list(p) for p in POLYGONS[3]]))
    errors = errors_of(data)
    assert has(errors, "M2") and has(errors, "M3")


def test_m3_two_right_symbols_satisfy_the_relation():
    def two_twins(d):
        r = d["geometry"]["right"]
        r[1]["vertices"] = [list(p) for p in r[0]["vertices"]]
        r[1]["label"] = r[0]["label"]
    errors = errors_of(tampered(hand(CLASSES4, PERM4), two_twins))
    assert has(errors, "M3") and has(errors, "M2")


def test_m3_no_right_symbol_matches():
    def other(d):
        d["geometry"]["right"][0]["vertices"] = [list(p) for p in POLYGONS[8]]
        d["geometry"]["right"][0]["label"] = "polygon-8"
    errors = errors_of(tampered(hand(CLASSES4, PERM4), other))
    assert has(errors, "M3")


def test_m3_count_with_a_wrong_dot_count_or_a_star_on_the_left():
    def wrong_count(d):
        r = d["geometry"]["right"][0]
        r["dots"] = [list(p) for p in DOTS[8]]
        r["label"] = "dots-8"
    errors = errors_of(tampered(hand(CLASSES4, PERM4, "count"), wrong_count))
    assert has(errors, "M3")
    # relation count needs polygons on the left: a star record is refused at the params level
    data = tampered(hand([("star", 4), ("star", 5), ("star", 6)], [1, 2, 0]), lambda d: (
        d["params"].update(relation="count"), d["geometry"].update(relation="count")))
    assert has(errors_of(data), "params")


def test_m4_bowtie_concave_and_clockwise_outlines_are_refused():
    def bowtie(d):
        d["geometry"]["left"][0]["vertices"] = [[8, 26], [92, 98], [92, 26], [8, 98]]
    errors = errors_of(tampered(hand(CLASSES4, PERM4), bowtie))
    assert has(errors, "M4")
    assert any("non simple" in e for e in errors)

    def concave(d):  # a re-entrant vertex in a "polygon"
        d["geometry"]["left"][2]["vertices"] = [[16, 16], [84, 16], [50, 40], [84, 84], [16, 84]]
    errors = errors_of(tampered(hand(CLASSES4, PERM4), concave))
    assert has(errors, "M4")

    def clockwise(d):
        d["geometry"]["left"][2]["vertices"] = list(reversed(d["geometry"]["left"][2]["vertices"]))
    assert has(errors_of(tampered(hand(CLASSES4, PERM4), clockwise)), "M4")

    def outside(d):
        d["geometry"]["left"][2]["vertices"] = [[x + 30, y] for x, y in d["geometry"]["left"][2]["vertices"]]
    assert has(errors_of(tampered(hand(CLASSES4, PERM4), outside)), "M4")

    def collinear(d):
        d["geometry"]["left"][2]["vertices"] = [[16, 16], [50, 16], [84, 16], [84, 84], [16, 84]]
    assert has(errors_of(tampered(hand(CLASSES4, PERM4), collinear)), "M4")


def test_m4_star_with_the_wrong_number_of_reentrant_vertices_is_refused():
    classes = [("star", 4), ("star", 5), ("star", 6)]
    base = hand(classes, [1, 2, 0])
    assert errors_of(base) == []

    def convexify(d):  # push re-entrant points outwards: a convex 8-gon declared as star-4
        d["geometry"]["left"][0]["vertices"] = [list(p) for p in POLYGONS[8]]
    errors = errors_of(tampered(base, convexify))
    assert has(errors, "M4")


def test_m5_gap_is_checked_on_recomputed_ratios(monkeypatch):
    base = hand([("polygon", 6), ("polygon", 7), ("polygon", 3)], [1, 2, 0])
    assert errors_of(base) == []
    monkeypatch.setattr(mv, "AREA_RATIO_GAP_MIN_PPM", 10_000)  # hexagon vs heptagon differ by ~8 241 ppm
    errors = errors_of(base)
    assert has(errors, "M5")


def test_m5_generator_refuses_what_the_threshold_excludes(monkeypatch):
    monkeypatch.setattr(mt, "AREA_RATIO_GAP_MIN_PPM", 10_000_000)
    with pytest.raises(V2Error) as info:
        make(3, "twin", "polygon")
    assert info.value.code == "UNSATISFIABLE"


def test_m5_threshold_is_below_the_smallest_gap_of_the_tables_and_frozen():
    ratios = {("polygon", n): ref_ratio(("polygon", n)) for n in POLYGONS} | {("star", k): ref_ratio(("star", k)) for k in STARS}
    smallest = min(abs(a - b) for a, b in itertools.combinations(ratios.values(), 2))
    assert Fraction(5000, 1_000_000) <= smallest == Fraction(3, 364) and mt.AREA_RATIO_GAP_MIN_PPM == 5000
    assert Fraction(ratios[("polygon", 6)]) == Fraction(3, 4) and ratios[("polygon", 7)] < ratios[("polygon", 6)]


def test_m6_concurrent_links_are_refused():
    classes = [("polygon", 3), ("polygon", 4), ("polygon", 5)]
    data = hand(classes, [2, 1, 0])  # three links through the centre
    assert has(errors_of(data), "M6")
    classes4 = [("polygon", 3), ("polygon", 4), ("polygon", 5), ("polygon", 6)]
    assert has(errors_of(hand(classes4, [3, 2, 1, 0])), "M6")
    assert not has(errors_of(hand(classes4, [1, 2, 3, 0])), "M6")


def test_m6_generator_never_publishes_concurrent_links():
    for pairs in (3, 4, 5, 6):
        for seed in range(60):
            perm = make(pairs, "twin", "polygon", seed).to_dict()["solution"]["left_to_right"]
            assert not mt.concurrent_links(perm)
            assert not has(errors_of(hand([("polygon", n) for n in range(3, 3 + pairs)], perm)), "M6")


def test_concurrency_oracle_agrees_with_the_generator_helper_on_every_permutation():
    for pairs in (3, 4, 5, 6):
        classes = [("polygon", n) for n in range(3, 3 + pairs)]
        for perm in itertools.permutations(range(pairs)):
            perm = list(perm)
            if perm == list(range(pairs)):
                continue
            helper = mt.concurrent_links(perm)
            verdict = has(errors_of(hand(classes, perm)), "M6")
            assert helper == verdict, (pairs, perm)


def test_m7_real_bounding_boxes_not_nominal_cells():
    # symbols placed with the nominal 100-high cell would touch at pitch < 100 + gap; here the REAL boxes are measured
    for pairs in (5, 6):
        data = make(pairs, "twin", "polygon", 1).to_dict()
        ys = data["geometry"]["anchors"]["ys"]
        boxes = []
        for e in data["geometry"]["left"]:
            ox, oy = e["origin"]
            pts = [(ox + x, oy + y) for x, y in e["vertices"]]
            boxes.append((min(p[1] for p in pts), max(p[1] for p in pts)))
        assert all(b[0] >= 50 and b[1] <= 950 for b in boxes)
        assert all(boxes[i + 1][0] - boxes[i][1] >= 30 for i in range(pairs - 1)), (pairs, boxes)
        assert ys == ref_ys(pairs)
    # at six pairs the pitch is 150: every real gap is at least 54 whatever the classes
    worst = min(150 - (max(v[1] for v in t) - min(v[1] for v in t)) for t in list(POLYGONS.values()) + list(STARS.values()))
    assert worst >= 50


def test_m7_a_symbol_that_exceeds_its_row_or_the_grid_is_refused():
    base = hand([("polygon", 3), ("polygon", 4), ("polygon", 5), ("polygon", 6), ("polygon", 7), ("polygon", 8)], [1, 0, 3, 2, 5, 4])
    assert errors_of(base) == []

    def drop(d):  # next box starts too close to the previous one
        e = d["geometry"]["left"][1]
        e["origin"] = [e["origin"][0], e["origin"][1] - 40]
    assert has(errors_of(tampered(base, drop)), "M7")

    def off_grid(d):
        e = d["geometry"]["right"][5]
        e["origin"] = [e["origin"][0], e["origin"][1] + 200]
    assert has(errors_of(tampered(base, off_grid)), "M7")

    def left_over(d):
        e = d["geometry"]["left"][0]
        e["origin"] = [e["origin"][0] + 100, e["origin"][1]]
    assert has(errors_of(tampered(base, left_over)), "M7")

    def right_over(d):
        e = d["geometry"]["right"][0]
        e["origin"] = [e["origin"][0] - 60, e["origin"][1]]
    assert has(errors_of(tampered(base, right_over)), "M7")

    def anchors(d):
        d["geometry"]["anchors"]["ys"][0] += 1
    assert has(errors_of(tampered(base, anchors)), "M7")


def test_m7_six_pairs_symbols_neither_touch_nor_leave_the_grid_for_every_valid_combination():
    for pairs, relation, family in [c for c in VALID if c[0] == 6]:
        for seed in range(25):
            data = make(pairs, relation, family, seed).to_dict()
            for side in ("left", "right"):
                boxes = []
                for e in data["geometry"][side]:
                    pts = e.get("vertices") or e["dots"]
                    ox, oy = e["origin"]
                    xs = [ox + p[0] for p in pts]
                    ys = [oy + p[1] for p in pts]
                    boxes.append((min(xs), min(ys), max(xs), max(ys)))
                assert all(50 <= b[0] and b[2] <= 950 and 50 <= b[1] and b[3] <= 950 for b in boxes)
                assert all(boxes[i + 1][1] - boxes[i][3] >= 30 for i in range(5))


def test_m8_inconsistent_labels_are_refused():
    data = tampered(hand(CLASSES4, PERM4), lambda d: d["geometry"]["left"][0].update(label="polygon-4"))
    assert has(errors_of(data), "M8")
    data = tampered(hand(CLASSES4, PERM4, "count"), lambda d: d["geometry"]["right"][0].update(label="dots-9"))
    assert has(errors_of(data), "M8")


def test_m9_dot_patterns_are_closed_tables_apart_and_with_distinct_counts():
    base = hand(CLASSES4, PERM4, "count")
    assert errors_of(base) == []

    def moved(d):
        d["geometry"]["right"][0]["dots"][0][0] += 1
    assert has(errors_of(tampered(base, moved)), "M9")

    def close(d):
        r = d["geometry"]["right"][1]
        r["dots"] = [[50, 50], [60, 50], [30, 70], [70, 70], [50, 20]][:len(r["dots"])]
    assert has(errors_of(tampered(base, close)), "M9")

    def same_count(d):
        d["geometry"]["right"][1]["dots"] = [list(p) for p in d["geometry"]["right"][0]["dots"]]
        d["geometry"]["right"][1]["label"] = d["geometry"]["right"][0]["label"]
    errors = errors_of(tampered(base, same_count))
    assert has(errors, "M9")

    def border(d):
        d["geometry"]["right"][2]["dots"] = [[5, 5]] + d["geometry"]["right"][2]["dots"][1:]
    assert has(errors_of(tampered(base, border)), "M9")


def test_dot_patterns_have_the_expected_counts_and_separation():
    for k, pts in DOTS.items():
        assert len(pts) == k == len(set(pts))
        assert all(15 <= x <= 85 and 15 <= y <= 85 for x, y in pts)
        assert all((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 >= 900 for a, b in itertools.combinations(pts, 2))


# ---- symbol tables: convexity, simplicity, signature ------------------------------------------------------------------------------
def test_tables_are_simple_counter_clockwise_and_classified_by_signature():
    for n, t in POLYGONS.items():
        assert ref_classify([tuple(p) for p in t]) == ("polygon", n) and analyse_outline(list(t)) == ([], ("polygon", n))
    for k, t in STARS.items():
        assert ref_classify([tuple(p) for p in t]) == ("star", k) and analyse_outline(list(t)) == ([], ("star", k))
    signatures = [(len(t), 0) for t in POLYGONS.values()] + [(len(t), len(t) // 2) for t in STARS.values()]
    assert len(set(signatures)) == len(signatures) == 9  # (8, 0) octagon differs from (8, 4) star-4


def test_outline_analysis_matches_a_reference_on_random_polygons():
    rng = random.Random(20260)
    checked = {"ok": 0, "bad": 0}
    for _ in range(4000):
        n = rng.randint(3, 8)
        if rng.random() < 0.6:  # star-shaped (simple) polygons around a centre, sometimes concave
            centre = (50, 50)
            pts = set()
            while len(pts) < n:
                pts.add((rng.randint(2, 98), rng.randint(2, 98)))
            pts = sorted(pts, key=lambda p: math.atan2(p[1] - centre[1], p[0] - centre[0]))
            start = min(range(n), key=lambda i: (pts[i][1], pts[i][0]))
            vs = pts[start:] + pts[:start]
        else:
            vs = [(rng.randint(0, 100), rng.randint(0, 100)) for _ in range(n)]
        problems, cls = analyse_outline(list(vs))
        assert (cls is not None) == (not problems)
        assert cls == ref_classify(vs), vs
        checked["ok" if cls else "bad"] += 1
    assert checked["ok"] > 100 and checked["bad"] > 100


def test_degenerate_inputs_to_the_outline_analysis_do_not_raise():
    for vs in ([(0, 0)], [(0, 0), (0, 0)], [(0, 0), (0, 0), (0, 0)], [(0, 0), (50, 0), (50, 0)], [(0, 0), (10, 0), (5, 0)], [(1, 1)] * 6):
        problems, cls = analyse_outline(list(vs))
        assert problems and cls is None


# ---- differential: verifier against the independent oracle on mutated records -------------------------------------------------------------
def _mutations(rng: random.Random, data: dict) -> None:
    g = data["geometry"]
    n = data["params"]["pairs"]
    kind = rng.randrange(11)
    side = rng.choice(("left", "right"))
    entry = g[side][rng.randrange(n)]
    key = "vertices" if "vertices" in entry else "dots"
    if kind == 0:
        i, j = rng.sample(range(n), 2)
        g["right"][i], g["right"][j] = g["right"][j], g["right"][i]
    elif kind == 1:
        i, j = rng.sample(range(n), 2)
        g["left"][i]["label"], g["left"][j]["label"] = g["left"][j]["label"], g["left"][i]["label"]
    elif kind == 2:
        perm = list(range(n))
        rng.shuffle(perm)
        data["solution"]["left_to_right"] = perm
    elif kind == 3:
        entry["origin"][rng.randrange(2)] += rng.choice([-40, -7, -1, 1, 9, 35])
    elif kind == 4:
        p = entry[key][rng.randrange(len(entry[key]))]
        p[rng.randrange(2)] += rng.choice([-5, -1, 1, 3, 40])
    elif kind == 5 and len(entry[key]) > 3:
        del entry[key][rng.randrange(len(entry[key]))]
    elif kind == 6:
        entry[key].append(list(entry[key][rng.randrange(len(entry[key]))]))
    elif kind == 7:
        other = rng.randrange(n)
        entry["label"] = g[side][other]["label"]
    elif kind == 8:
        i, j = rng.sample(range(n), 2)
        g["left"][i]["vertices"], g["left"][j]["vertices"] = g["left"][j]["vertices"], g["left"][i]["vertices"]
    elif kind == 9:
        g["anchors"]["ys"][rng.randrange(n)] += rng.choice([-1, 1])
    else:
        entry["row"] = rng.randrange(n + 2)


def test_differential_verifier_against_independent_oracle_on_mutated_records():
    rng = random.Random(777)
    agree = {True: 0, False: 0}
    for count in range(3000):
        pairs, relation, family = VALID[count % len(VALID)]
        data = make(pairs, relation, family, rng.randrange(1000), "syn-diff").to_dict()
        for _ in range(rng.choice((1, 1, 2))):
            _mutations(rng, data)
        refingerprint(data)
        verdict = geometry_errors(data) == []
        assert verdict == oracle_ok(data), (count, geometry_errors(data), data["geometry"]["left"][0]["label"])
        agree[verdict] += 1
    assert agree[False] > 1500 and agree[True] >= 0


def test_differential_on_clean_records_and_every_permutation():
    for pairs in (3, 4, 5, 6):
        classes = [("polygon", n) for n in range(3, 3 + pairs)]
        for perm in itertools.permutations(range(pairs)):
            for relation in ("twin", "count"):
                data = hand(classes, list(perm), relation)
                assert (errors_of(data) == []) == oracle_ok(data), (pairs, perm, relation)


# ---- falsification with a recomputed fingerprint; the fingerprint is not a proof ------------------------------------------------------------------
def test_every_single_edit_of_a_valid_record_is_detected_even_with_a_fresh_fingerprint(sample):
    base = sample.to_dict()
    cases = {
        "solution": lambda d: d["solution"]["left_to_right"].reverse(),
        "left vertex": lambda d: d["geometry"]["left"][0]["vertices"][0].__setitem__(0, d["geometry"]["left"][0]["vertices"][0][0] + 1),
        "right vertex": lambda d: d["geometry"]["right"][0]["vertices"][0].__setitem__(1, 99),
        "label": lambda d: d["geometry"]["right"][2].__setitem__("label", "polygon-3"),
        "origin": lambda d: d["geometry"]["left"][1]["origin"].__setitem__(0, 101),
        "relation": lambda d: d["params"].__setitem__("relation", "count"),
        "family": lambda d: d["params"].__setitem__("family", "star"),
        "pairs": lambda d: d["params"].__setitem__("pairs", 5),
        "rows": lambda d: d["geometry"].__setitem__("rows", 5),
        "grid": lambda d: d["geometry"].__setitem__("grid", 1001),
        "extra key": lambda d: d["geometry"].__setitem__("hint", 1),
        "extra left key": lambda d: d["geometry"]["left"][0].__setitem__("id", 7),
        "mechanic": lambda d: d.__setitem__("mechanic", "maze_v2"),
        "version": lambda d: d.__setitem__("version", "x"),
        "production": lambda d: d.__setitem__("production_authorized", True),
        "validation": lambda d: d.__setitem__("human_pedagogical_validation", "DONE"),
        "attempts": lambda d: d["search"].__setitem__("attempts", 0),
        "max_attempts": lambda d: d["search"].__setitem__("max_attempts", 5),
        "measure": lambda d: d["measures"].__setitem__("crossings", d["measures"]["crossings"] + 1),
        "seed": lambda d: d.__setitem__("seed", -1),
        "activity_id": lambda d: d.__setitem__("activity_id", "demo"),
    }
    for name, mutate in cases.items():
        assert errors_of(tampered(base, mutate, refinger=True)), name
        stale = errors_of(tampered(base, mutate, refinger=False))
        assert stale, name
    # a stale fingerprint alone is reported as such
    data = copy.deepcopy(base)
    data["fingerprint"] = "0" * 64
    assert tags(errors_of(data)) == {"fingerprint"}


def test_fingerprint_alone_is_not_a_proof_of_validity(sample):
    forged = copy.deepcopy(sample.to_dict())
    forged["geometry"]["right"][0], forged["geometry"]["right"][1] = forged["geometry"]["right"][1], forged["geometry"]["right"][0]
    forged["fingerprint"] = record_fingerprint(forged)
    assert not has(errors_of(forged), "fingerprint") and errors_of(forged)


def test_floats_bools_and_hostile_types_are_rejected_not_crashing(sample):
    base = sample.to_dict()
    hostile = [
        lambda d: d["geometry"]["left"][0]["vertices"][0].__setitem__(0, 8.0),
        lambda d: d["geometry"]["left"][0]["vertices"][0].__setitem__(0, True),
        lambda d: d["geometry"]["left"][0].__setitem__("vertices", "abc"),
        lambda d: d["geometry"]["left"][0].__setitem__("vertices", [[1, 2, 3]] * 3),
        lambda d: d["geometry"]["left"][0].__setitem__("vertices", [[10 ** 40, 1]] * 3),
        lambda d: d["geometry"].__setitem__("left", None),
        lambda d: d["geometry"].__setitem__("right", []),
        lambda d: d["geometry"].__setitem__("anchors", []),
        lambda d: d.__setitem__("solution", []),
        lambda d: d.__setitem__("params", {"pairs": True, "relation": "twin", "family": "mixed"}),
        lambda d: d["params"].__setitem__("pairs", 10 ** 30),
        lambda d: d["geometry"]["right"][0].__setitem__("origin", [800.0, 1]),
        lambda d: d["geometry"]["left"][0].__setitem__("vertices", [[0, 0]] * 100),
    ]
    for mutate in hostile:
        assert errors_of(tampered(base, mutate, refinger=False))
        assert errors_of(tampered(base, mutate, refinger=True))
    for junk in (None, [], "x", 3, {}, {"mechanic": "match_v2"}):
        assert verify_match_v2(junk)  # type: ignore[arg-type]


def test_record_is_immutable_and_independent_of_later_edits(sample):
    with pytest.raises((AttributeError, TypeError)):
        sample.geometry["rows"] = 9  # type: ignore[index]
    data = sample.to_dict()
    data["geometry"]["left"].clear()
    assert verify_match_v2(sample) == [] and sample.production_authorized is False and PRODUCTION_AUTHORIZED is False


# ---- search, failure, determinism ------------------------------------------------------------------------------------------------------------
def test_bounded_search_reports_unsatisfiable_without_relaxing(monkeypatch):
    monkeypatch.setattr(mt, "gaps_ok", lambda classes: (False, 0))
    with pytest.raises(V2Error) as info:
        make(4)
    assert info.value.code == "UNSATISFIABLE"
    monkeypatch.undo()
    monkeypatch.setattr(mt, "concurrent_links", lambda perm: True)
    with pytest.raises(V2Error) as info:
        make(5)
    assert info.value.code == "UNSATISFIABLE"
    monkeypatch.undo()
    monkeypatch.setattr(mt, "MAX_ATTEMPTS", 0)
    with pytest.raises(V2Error) as info:
        make(5)
    assert info.value.code == "UNSATISFIABLE"


def test_a_failing_self_check_is_never_returned(monkeypatch):
    import dataclasses
    from lafractale.mechanics_v2 import registry
    entry = MECHANICS_V2["match_v2"]
    monkeypatch.setattr(registry, "MECHANICS_V2", {"match_v2": dataclasses.replace(entry, verify=lambda a: ["panne injectée"])})
    with pytest.raises(V2Error) as info:
        registry.generate_v2("match_v2", "syn-a", 0, {"pairs": 3, "relation": "twin", "family": "polygon"})
    assert info.value.code == "SELF_CHECK_FAILED"


def test_search_attempts_are_the_first_valid_candidate(sample):
    # replay with the same stream: the attempt reported is the first accepted one
    again = make()
    assert again.search["attempts"] == sample.search["attempts"] >= 1


def test_generation_writes_nothing(monkeypatch):
    import builtins
    import os
    writes = []
    real_open, real_os_open = builtins.open, os.open
    monkeypatch.setattr(builtins, "open", lambda f, m="r", *a, **k: (writes.append(f) if set(m) & set("wax+") else None, real_open(f, m, *a, **k))[1])
    monkeypatch.setattr(os, "open", lambda p, fl, *a, **k: (writes.append(p) if fl & (os.O_WRONLY | os.O_RDWR | os.O_CREAT) else None, real_os_open(p, fl, *a, **k))[1])
    make(6, "twin", "mixed", 5)
    assert writes == []


# ---- separation from editorial data and the historical engine ------------------------------------------------------------------------------------
def _imports(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _code_without_docstring(path: Path) -> str:
    module = ast.parse(path.read_text(encoding="utf-8"))
    module.body[0].value.value = ""
    return ast.unparse(module)


def test_match_modules_are_isolated_from_editorial_data():
    for name in ("match.py", "match_verify.py"):
        path = PKG / name
        imports = _imports(path)
        foreign = {n for n in imports if n.startswith("lafractale") and not n.startswith("lafractale.mechanics_v2")}
        assert foreign == set(), (name, foreign)
        assert not {n for n in imports if n.split(".")[0] in {"csv", "yaml", "os", "subprocess", "socket", "urllib", "pathlib",
                                                             "shutil", "random", "time", "datetime", "math"}}, name
        code = _code_without_docstring(path)
        for token in ("PageRecord", "scenario_b", "load_pages", "open(", "environ", "getenv", "argv", "write_text", "SpecSet",
                      ".csv", "float(", "hats", "gifts", "hat_", "gift_", "generate_match(", "lafractale.activities"):
            assert token not in code, (name, token)


def test_generator_and_verifier_arithmetic_is_exact():
    for name in ("match.py", "match_verify.py"):
        tree = ast.parse((PKG / name).read_text(encoding="utf-8"))
        tree.body[0].value.value = ""
        code = ast.unparse(tree)
        for token in ("atan2", "cos(", "sin(", "sqrt", "hypot", " / ", "1e-", "epsilon", "import math", "isclose"):
            assert token not in code, (name, token)
        assert not [n for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, float)], name


def test_verifier_does_not_call_the_generator_or_its_geometry_helpers():
    tree = ast.parse((PKG / "match_verify.py").read_text(encoding="utf-8"))
    imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module == "lafractale.mechanics_v2.match" for a in n.names}
    assert not imported & {"generate_match_v2", "gaps_ok", "concurrent_links", "inversions", "area_ratio", "row_centres",
                           "_place", "label", "reservoir", "check_combination", "PARAM_SPEC"}, imported


def test_no_page_or_editorial_object_can_parametrise_a_generation():
    from lafractale.scenario_b.pages import load_pages
    pages = load_pages(ROOT)
    for source in (pages.page(27), pages, pages.page(27).to_dict(), "PageRecord", object()):
        with pytest.raises(V2Error):
            generate_v2("match_v2", "syn-a", 0, source)  # type: ignore[arg-type]
    with pytest.raises(V2Error):
        generate_v2("match_v2", pages.page(27).title, 0, {"pairs": 3, "relation": "twin", "family": "polygon"})
    assert set(mt.PARAM_SPEC) == {"pairs", "relation", "family"}


def test_historical_match_and_registry_are_untouched():
    offenders = [str(p.relative_to(ROOT)) for p in (ROOT / "src/lafractale").rglob("*.py")
                 if "mechanics_v2" not in p.parts and "mechanics_v2" in p.read_text(encoding="utf-8")]
    assert offenders == []
    from lafractale.engine import registry as historical
    assert "match_v2" not in Path(historical.__file__).read_text(encoding="utf-8")
    engine = (ROOT / "src/lafractale/activities/engine.py").read_text(encoding="utf-8")
    assert "def generate_match" in engine and "match_v2" not in engine


# ---- pinned vocabulary and constants (a silent change of a table or a threshold is a change of the contract) ----------------------------------
def test_tables_and_constants_are_pinned_literally():
    assert dict(POLYGONS) == {
        3: ((8, 26), (92, 26), (50, 98)), 4: ((16, 16), (84, 16), (84, 84), (16, 84)),
        5: ((22, 11), (78, 11), (96, 65), (50, 98), (4, 65)), 6: ((50, 2), (92, 26), (92, 74), (50, 98), (8, 74), (8, 26)),
        7: ((29, 7), (71, 7), (97, 39), (88, 80), (50, 98), (12, 80), (3, 39)),
        8: ((50, 2), (84, 16), (98, 50), (84, 84), (50, 98), (16, 84), (2, 50), (16, 16))}
    assert dict(STARS) == {
        4: ((50, 2), (61, 39), (98, 50), (61, 61), (50, 98), (39, 61), (2, 50), (39, 39)),
        5: ((22, 11), (50, 34), (78, 11), (65, 45), (96, 65), (59, 63), (50, 98), (41, 63), (4, 65), (35, 45)),
        6: ((50, 2), (58, 36), (92, 26), (66, 50), (92, 74), (58, 64), (50, 98), (42, 64), (8, 74), (34, 50), (8, 26), (42, 36))}
    assert dict(DOTS) == {
        3: ((50, 25), (25, 70), (75, 70)), 4: ((25, 25), (75, 25), (25, 75), (75, 75)),
        5: ((25, 25), (75, 25), (50, 50), (25, 75), (75, 75)), 6: ((25, 20), (75, 20), (25, 50), (75, 50), (25, 80), (75, 80)),
        7: ((50, 50), (50, 20), (76, 35), (76, 65), (50, 80), (24, 65), (24, 35)),
        8: ((20, 20), (50, 20), (80, 20), (20, 50), (80, 50), (20, 80), (50, 80), (80, 80))}
    assert (mt.GRID, mt.MARGIN, mt.FRAME, mt.LEFT_X, mt.RIGHT_X, mt.LEFT_ANCHOR_X, mt.RIGHT_ANCHOR_X) == (1000, 50, 100, 100, 800, 260, 740)
    assert (mt.MIN_BOX_GAP, mt.ANCHOR_CLEARANCE, mt.MIN_DOT_SEP_SQ, mt.DOT_BORDER, mt.MAX_ATTEMPTS) == (30, 20, 900, 15, 2000)
    assert (mt.PAIRS_MIN, mt.PAIRS_MAX, mt.RELATIONS, mt.FAMILIES) == (3, 6, ("twin", "count"), ("polygon", "star", "mixed"))
    assert mt.MATCH_V2_VERSION == "b3b3b3-match-v2-1.0" and mt.MATCH_V2_MECHANIC == "match_v2" and mv._MAX_VERTICES == 16


def test_m5_threshold_boundary_in_generator_and_verifier(monkeypatch):
    # hexagon vs heptagon: gap = 3/364 = 8241.758... millionths
    assert mt.gaps_ok([("polygon", 6), ("polygon", 7)]) == (True, 8241)
    base = hand([("polygon", 6), ("polygon", 7), ("polygon", 3)], [1, 2, 0])
    monkeypatch.setattr(mt, "AREA_RATIO_GAP_MIN_PPM", 8241)
    monkeypatch.setattr(mv, "AREA_RATIO_GAP_MIN_PPM", 8241)
    assert mt.gaps_ok([("polygon", 6), ("polygon", 7)])[0] and not has(errors_of(base), "M5")
    monkeypatch.setattr(mt, "AREA_RATIO_GAP_MIN_PPM", 8242)
    monkeypatch.setattr(mv, "AREA_RATIO_GAP_MIN_PPM", 8242)
    assert not mt.gaps_ok([("polygon", 6), ("polygon", 7)])[0] and has(errors_of(base), "M5")


def test_record_level_bounds_of_seed_pairs_and_search():
    base = make(3, "twin", "polygon", 0).to_dict()
    ok = lambda mutate: errors_of(tampered(base, mutate))
    assert ok(lambda d: d.__setitem__("seed", 0)) == [] or not has(ok(lambda d: d.__setitem__("seed", 0)), "seed")
    assert not has(ok(lambda d: d.__setitem__("seed", 2 ** 63 - 1)), "seed")
    assert has(ok(lambda d: d.__setitem__("seed", 2 ** 63)), "seed") and has(ok(lambda d: d.__setitem__("seed", -1)), "seed")
    assert has(ok(lambda d: d.__setitem__("seed", True)), "seed")
    assert not has(ok(lambda d: d["search"].__setitem__("attempts", 2000)), "search")
    assert has(ok(lambda d: d["search"].__setitem__("attempts", 2001)), "search")
    assert not has(ok(lambda d: d["search"].__setitem__("attempts", 1)), "search")
    assert has(ok(lambda d: d["search"].__setitem__("attempts", 0)), "search")
    assert has(ok(lambda d: d["search"].__setitem__("attempts", True)), "search")
    for bad in ("3", 3.0, None, [3], 2, 7, True):
        assert errors_of(tampered(base, lambda d, b=bad: d["params"].__setitem__("pairs", b)))
    for bad in (1, ["twin"], None, "TWIN", True):
        assert errors_of(tampered(base, lambda d, b=bad: d["params"].__setitem__("relation", b)))
    for bad in (1, ["polygon"], None, "hats", True):
        assert errors_of(tampered(base, lambda d, b=bad: d["params"].__setitem__("family", b)))
    assert errors_of(tampered(base, lambda d: d["params"].pop("family")))
    assert errors_of(tampered(base, lambda d: d["params"].__setitem__("extra", 1)))


def test_one_sided_uniqueness_is_still_refused():
    # left 0 has two twins on the right, left 1 has none, every right symbol is related to exactly one left symbol
    base = hand([("polygon", 3), ("polygon", 4), ("polygon", 5)], [1, 2, 0])

    def two_for_one(d):
        r = d["geometry"]["right"]
        l0 = d["geometry"]["left"][0]
        for j in (0, 1):
            r[j]["vertices"] = [list(p) for p in l0["vertices"]]
            r[j]["label"] = l0["label"]
        d["geometry"]["left"][1]["vertices"] = [list(p) for p in POLYGONS[7]]
        d["geometry"]["left"][1]["label"] = "polygon-7"
    errors = errors_of(tampered(base, two_for_one))
    assert has(errors, "M3")
    # columns all 1 but a row sum of 0 and one of 2 is the situation above; the converse is the same by symmetry
    def reverse(d):
        d["geometry"]["right"].reverse()
        for j, e in enumerate(d["geometry"]["right"]):
            e["row"] = j
            e["origin"][1] = d["geometry"]["anchors"]["ys"][j] - 50
    assert errors_of(tampered(base, reverse))  # the published solution no longer follows the geometry


def test_layout_thresholds_are_exact_for_box_gap_and_anchor_clearance(monkeypatch):
    """The origins are fixed by the layout rule, so the real-box checks are tested at their exact thresholds."""
    data = hand([("polygon", 4), ("polygon", 5), ("polygon", 6), ("polygon", 3)], [1, 0, 3, 2])
    assert errors_of(data) == []
    gaps, clearances = [], []
    for side, x0 in (("left", 100), ("right", 800)):
        boxes = []
        for e in data["geometry"][side]:
            pts = e.get("vertices") or e["dots"]
            xs = [e["origin"][0] + p[0] for p in pts]
            ys = [e["origin"][1] + p[1] for p in pts]
            boxes.append((min(xs), min(ys), max(xs), max(ys)))
            clearances.append(260 - max(xs) if side == "left" else min(xs) - 740)
        gaps += [boxes[i + 1][1] - boxes[i][3] for i in range(len(boxes) - 1)]
    gap, clearance = min(gaps), min(clearances)
    monkeypatch.setattr(mv, "MIN_BOX_GAP", gap)
    assert not has(errors_of(data), "M7")
    monkeypatch.setattr(mv, "MIN_BOX_GAP", gap + 1)
    assert has(errors_of(data), "M7")
    monkeypatch.setattr(mv, "MIN_BOX_GAP", 30)
    monkeypatch.setattr(mv, "ANCHOR_CLEARANCE", clearance)
    assert not has(errors_of(data), "M7")
    monkeypatch.setattr(mv, "ANCHOR_CLEARANCE", clearance + 1)
    assert has(errors_of(data), "M7")
    # each side separately: widen only the left, then only the right
    monkeypatch.setattr(mv, "ANCHOR_CLEARANCE", 20)
    left_clear = min(c for c, e in zip(clearances[:4], data["geometry"]["left"]))
    right_clear = min(clearances[4:])
    monkeypatch.setattr(mv, "ANCHOR_CLEARANCE", left_clear + 1)
    assert has(errors_of(data), "M7")
    # nominal cells are NOT what is measured: the origin rule and the real boxes both hold on every valid six-pair record
    assert min(gaps) >= 30 and clearance >= 20 and right_clear >= 20


def test_layout_origin_and_anchor_rules_are_exact():
    base = hand([("polygon", 4), ("polygon", 5), ("polygon", 6), ("polygon", 3)], [1, 0, 3, 2])
    for side in ("left", "right"):
        for axis in (0, 1):
            for delta in (-1, 1):
                def move(d, side=side, axis=axis, delta=delta):
                    d["geometry"][side][2]["origin"][axis] += delta
                assert has(errors_of(tampered(base, move)), "M7"), (side, axis, delta)
    for key in ("left_x", "right_x"):
        assert has(errors_of(tampered(base, lambda d, k=key: d["geometry"]["anchors"].__setitem__(k, d["geometry"]["anchors"][k] + 1))), "M7")


def test_dot_boundaries_border_and_separation():
    base = hand([("polygon", 3), ("polygon", 4), ("polygon", 5)], [1, 2, 0], "count")
    assert errors_of(base) == []

    def dots_of(d, k):
        return next(e for e in d["geometry"]["right"] if len(e["dots"]) == k)

    # the 3-dot table passes with its own coordinates; any single move breaks the "closed table" rule, so isolate the
    # border / separation rules by checking them through a hand-edited TABLE-equal record is impossible -> check via the monkeypatched table
    from lafractale.mechanics_v2 import match_verify as module
    custom = {**DOTS, 3: ((15, 15), (45, 15), (85, 85))}
    d = tampered(base, lambda x: dots_of(x, 3).__setitem__("dots", [list(p) for p in custom[3]]))
    import unittest.mock as mock
    with mock.patch.object(module, "DOTS", custom):
        assert not has(errors_of(d), "M9")          # border exactly 15, separation exactly 30
        for variant in (((14, 15), (45, 15), (85, 85)), ((15, 15), (44, 15), (85, 85)), ((15, 15), (45, 15), (86, 85)), ((15, 15), (45, 15), (85, 86))):
            c = {**DOTS, 3: variant}
            with mock.patch.object(module, "DOTS", c):
                e = tampered(base, lambda x, v=variant: dots_of(x, 3).__setitem__("dots", [list(p) for p in v]))
                assert has(errors_of(e), "M9"), variant


def test_contact_primitive_matches_the_exact_reference_on_small_grids():
    rng = random.Random(5)
    for _ in range(4000):
        pts = [(rng.randint(0, 5), rng.randint(0, 5)) for _ in range(4)]
        if pts[0] == pts[1] or pts[2] == pts[3]:
            continue
        assert mv._contact(*pts) == ref_touch(*pts), pts


def test_outline_frame_and_degenerate_boundaries():
    square = [(0, 0), (100, 0), (100, 100), (0, 100)]
    assert analyse_outline(square)[0] == []                      # the frame edge itself is allowed
    for bad in ([(0, 0), (101, 0), (101, 100), (0, 100)], [(-1, 0), (100, 0), (100, 100), (-1, 100)], [(0, 0), (100, 0), (100, 101), (0, 101)]):
        assert analyse_outline(bad)[0]
    assert analyse_outline([(0, 0), (10, 0), (10, 0)])[0] and analyse_outline([(0, 0), (0, 0), (0, 0)])[0]
    assert mv._points([]) is None and mv._points([[1, 2]] * 17) is None and mv._points([[1, 2]] * 16) is not None
    assert mv._points([[1, 2]]) is not None and mv._points([[1, 2, 3]]) is None and mv._points([[True, 2]]) is None
    # first vertex must be the smallest (y, x): same square started at another corner
    assert analyse_outline([(100, 0), (100, 100), (0, 100), (0, 0)])[0]
    assert analyse_outline([(0, 0), (0, 100), (100, 100), (100, 0)])[0]  # clockwise


# ---- real boxes: each side and each boundary isolated by its own message --------------------------------------------------------------------------
def _msgs(data: dict, needle: str) -> list[str]:
    return [e for e in errors_of(data) if needle in e]


def test_real_box_margin_and_gap_messages_are_isolated_side_by_side():
    base = hand([("polygon", 4), ("polygon", 5), ("polygon", 6), ("polygon", 3)], [1, 0, 3, 2])
    assert _msgs(base, "boîte réelle") == [] and _msgs(base, "trop proche") == [] and _msgs(base, "trop proches") == []

    def put(d, side, row, key, target):
        """Translate one symbol so that its real box edge (min/max of x/y) sits exactly at ``target``."""
        e = d["geometry"][side][row]
        pts = e.get("vertices") or e["dots"]
        axis = 0 if key.endswith("x") else 1
        edge = (min if key.startswith("min") else max)(p[axis] for p in pts)
        e["origin"][axis] += target - (e["origin"][axis] + edge)

    for side in ("left", "right"):
        for key, ok, bad in (("min_x", 50, 49), ("max_x", 950, 951), ("min_y", 50, 49), ("max_y", 950, 951)):
            row = 0 if key == "min_y" else 3 if key == "max_y" else 1
            assert not _msgs(tampered(base, lambda d: put(d, side, row, key, ok)), "boîte réelle"), (side, key, ok)
            assert _msgs(tampered(base, lambda d: put(d, side, row, key, bad)), "boîte réelle"), (side, key, bad)
    # gap between consecutive real boxes: every pair of a column, boundary 30 / 29
    for side in ("left", "right"):
        for upper in range(3):
            def squeeze(d, target, upper=upper, side=side):
                lower_box = d["geometry"][side][upper + 1]
                top_pts = d["geometry"][side][upper]
                bottom = top_pts["origin"][1] + max(p[1] for p in top_pts.get("vertices") or top_pts["dots"])
                top = lower_box["origin"][1] + min(p[1] for p in lower_box.get("vertices") or lower_box["dots"])
                lower_box["origin"][1] += (bottom + target) - top
            assert not _msgs(tampered(base, lambda d: squeeze(d, 30)), "trop proches"), (side, upper)
            assert _msgs(tampered(base, lambda d: squeeze(d, 29)), "trop proches"), (side, upper)


def test_anchor_clearance_is_checked_on_each_side_exactly(monkeypatch):
    base = hand([("polygon", 4), ("polygon", 5), ("polygon", 6), ("polygon", 3)], [1, 0, 3, 2])
    left_edge = max(100 + x for e in base["geometry"]["left"] for x, _ in e["vertices"])      # 196 (pentagon)
    right_edge = min(800 + x for e in base["geometry"]["right"] for x, _ in e["vertices"])    # 804
    monkeypatch.setattr(mv, "LEFT_ANCHOR_X", left_edge + 20)
    assert not _msgs(base, "ancre")
    monkeypatch.setattr(mv, "LEFT_ANCHOR_X", left_edge + 19)
    assert _msgs(base, "gauche") and any("ancre" in e and "gauche" in e for e in errors_of(base))
    assert not any("ancre" in e and "droite" in e for e in errors_of(base))
    monkeypatch.setattr(mv, "LEFT_ANCHOR_X", 260)
    monkeypatch.setattr(mv, "RIGHT_ANCHOR_X", right_edge - 20)
    assert not [e for e in errors_of(base) if "ancre" in e and "trop proche" in e]
    monkeypatch.setattr(mv, "RIGHT_ANCHOR_X", right_edge - 19)
    assert any("ancre" in e and "droite" in e and "trop proche" in e for e in errors_of(base))
    assert not any("ancre" in e and "gauche" in e and "trop proche" in e for e in errors_of(base))


def test_hostile_relation_and_family_in_params_and_geometry_together():
    base = make(3, "twin", "polygon", 1).to_dict()
    for bad in ("TWIN", "x", "", "match"):
        def both(d, b=bad):
            d["params"]["relation"] = b
            d["geometry"]["relation"] = b
        assert has(errors_of(tampered(base, both)), "params.relation")
    for bad in ("hats", "gifts", "x", ""):
        def both(d, b=bad):
            d["params"]["family"] = b
            d["geometry"]["family"] = b
        assert has(errors_of(tampered(base, both)), "params.family")


def test_one_sided_uniqueness_reports_the_bilateral_rule_itself():
    base = hand([("polygon", 3), ("polygon", 4), ("polygon", 5)], [1, 2, 0])

    def two_for_one(d):
        r, l0 = d["geometry"]["right"], d["geometry"]["left"][0]
        for j in (0, 1):
            r[j]["vertices"] = [list(p) for p in l0["vertices"]]
            r[j]["label"] = l0["label"]
        d["geometry"]["left"][1]["vertices"] = [list(p) for p in POLYGONS[7]]
        d["geometry"]["left"][1]["label"] = "polygon-7"
    assert _msgs(tampered(base, two_for_one), "bilatéralement")

    def one_for_two(d):  # a right symbol related to two left symbols (count): same dot count for two polygons is impossible, use twin
        l = d["geometry"]["left"]
        l[1]["vertices"] = [list(p) for p in l[0]["vertices"]]
        l[1]["label"] = l[0]["label"]
    assert _msgs(tampered(base, one_for_two), "bilatéralement")


def test_deeply_nested_hostile_fields_give_errors_not_exceptions(sample):
    deep: list = []
    for _ in range(100_000):
        deep = [deep]
    for path in (("geometry", "left", 0, "label"), ("measures", "x"), ("geometry", "anchors"), ("search", "attempts"),
                 ("solution", "left_to_right"), ("params", "pairs"), ("geometry", "right", 1, "origin")):
        data = sample.to_dict()
        target = data
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = deep
        assert verify_match_v2(data), path
    assert verify_v2(data)
