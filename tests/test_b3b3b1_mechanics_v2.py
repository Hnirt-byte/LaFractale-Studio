"""B3-B.3b.1 — mechanics v2 foundation + maze_v2: contracts, properties, tampering, isolation."""
from __future__ import annotations

import ast
import copy
import dataclasses
import hashlib
import inspect
import json
from pathlib import Path

import pytest

from lafractale.mechanics_v2 import PRODUCTION_AUTHORIZED, V2_KIND, V2_SCHEMA
from lafractale.mechanics_v2 import core, maze, maze_verify
from lafractale.mechanics_v2.core import DetRng, FrozenDict, V2Activity, V2Error, canonical_bytes, loads_record
from lafractale.mechanics_v2.maze import DIFFICULTIES, MAX_ATTEMPTS, SIZE_MAX, SIZE_MIN, band, meets
from lafractale.mechanics_v2.maze_verify import verify_maze_v2
from lafractale.mechanics_v2.registry import MECHANICS_V2, generate_v2, verify_v2

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "src/lafractale/mechanics_v2"
SIZES = range(SIZE_MIN, SIZE_MAX + 1)
SEEDS = range(4)


def make(size=5, level="medium", seed=1, activity_id="syn-demo") -> V2Activity:
    return generate_v2("maze_v2", activity_id, seed, {"size": size, "difficulty": level})


@pytest.fixture(scope="module")
def sample() -> V2Activity:
    return make()


def tampered(activity: V2Activity, mutate) -> dict:
    data = copy.deepcopy(activity.to_dict())
    mutate(data)
    return data


# ---- golden: stable canonical form and fingerprints -----------------------------------------------
def test_golden_fingerprints_are_stable_across_versions_and_runs(sample):
    assert sample.fingerprint == "3eb587e994edd8acd3a0ea41536dd1993d8048bdf5a545d02e46bb5ed38eae33"
    assert make(12, "hard", 7, "syn-x").fingerprint == "4bbc35b724806f93d4520e41b3f26bd373c13ab939b4c28a1fb76dfb56f0c65d"
    assert make().canonical_bytes() == sample.canonical_bytes()


def test_canonical_form_schema_and_fingerprint_rule(sample):
    raw = sample.canonical_bytes()
    text = raw.decode("utf-8")
    assert ", " not in text and ": " not in text  # no insignificant whitespace (separators , and :)
    record = json.loads(text)
    assert list(record) == sorted(record)  # keys sorted at the top level
    assert record["schema"] == V2_SCHEMA == "lafractale-mechanics-v2-activity-v1" and record["kind"] == V2_KIND
    assert record["production_authorized"] is False and record["human_pedagogical_validation"] == "NONE"
    without = {k: v for k, v in record.items() if k != "fingerprint"}
    assert hashlib.sha256(json.dumps(without, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest() \
        == record["fingerprint"] == sample.fingerprint
    assert loads_record(raw) == record
    assert json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode() == raw


def test_loads_record_refuses_non_canonical_or_ambiguous_bytes(sample):
    raw = sample.canonical_bytes()
    for bad in (raw.replace(b",", b", ", 1), b"[]", b"not json", b'{"a":1,"a":2}', b'{"a":1.5}', raw + b"\n", b'{"a":NaN}'):
        with pytest.raises(V2Error):
            loads_record(bad)


def test_canonical_bytes_refuses_floats_nan_and_non_string_keys():
    for bad in ({"a": 1.5}, {"a": float("nan")}, {1: "x"}, {"a": {"b": object()}}, {"a": {2, 3}}):
        with pytest.raises(V2Error):
            canonical_bytes(bad)


def test_prng_is_a_pure_function_of_its_material():
    a, b = DetRng("m|1"), DetRng("m|1")
    assert [a.below(1000) for _ in range(50)] == [b.below(1000) for _ in range(50)]
    assert [DetRng("m|2").below(1000) for _ in range(5)] != [DetRng("m|1").below(1000) for _ in range(5)]
    assert DetRng("m|1").below(1) == 0
    with pytest.raises(ValueError):
        DetRng("x").below(0)
    items = list(range(20))
    DetRng("s").shuffle(items)
    assert sorted(items) == list(range(20)) and items != list(range(20))


# ---- level specification -------------------------------------------------------------------------
def test_level_bands_match_a_hand_computed_table():
    """Literal expectations (not derived from the code): N=5 -> Lmin=8, span=16; N=3 -> Lmin=4, span=4."""
    five = {8: "easy", 10: "easy", 12: "easy", 14: "medium", 16: "medium", 18: "hard", 20: "hard", 22: "hard", 24: "hard"}
    assert {length: band(5, length) for length in five} == five
    assert [band(3, length) for length in (4, 6, 8)] == ["easy", "medium", "hard"]
    assert [band(12, length) for length in (22, 52, 53, 82, 83, 143)] == ["easy", "easy", "medium", "medium", "hard", "hard"]


def test_levels_partition_every_possible_excess():
    for size in SIZES:
        low, total = 2 * (size - 1), (size - 1) ** 2
        bands = [band(size, low + e) for e in range(0, total + 1, 2)]
        assert bands[0] == "easy" and bands[-1] == "hard"
        assert bands == sorted(bands, key=DIFFICULTIES.index)  # monotone easy → medium → hard
        for e in range(0, total + 1, 2):
            holders = [lv for lv in DIFFICULTIES if band(size, low + e) == lv]
            assert len(holders) == 1


def test_branch_constraints_are_part_of_the_level():
    assert meets(8, "easy", 14, 0, 8) and not meets(8, "easy", 14, 0, 9)
    assert not meets(8, "medium", 28, 0, 3) and meets(8, "medium", 28, 0, 4)
    assert not meets(10, "hard", 70, 1, 1) and meets(10, "hard", 70, 3, 3)
    assert not meets(10, "easy", 70, 0, 0)  # band mismatch alone is enough to refuse


# ---- properties: every size x level x seed ----------------------------------------------------------
@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("level", DIFFICULTIES)
def test_every_size_and_level_is_satisfiable_and_independently_verified(size, level):
    seen = set()
    for seed in SEEDS:
        activity = make(size, level, seed, f"syn-p{size}")
        record = activity.to_dict()
        assert verify_maze_v2(record) == [] and verify_v2(activity) == []
        m = activity.measures
        assert band(size, m["path_length"]) == level
        assert meets(size, level, m["path_length"], m["dead_ends"], m["decisions"])
        assert len(record["geometry"]["open_edges"]) == size * size - 1  # spanning tree
        assert record["solution"]["path"][0] == [0, 0] and record["solution"]["path"][-1] == [size - 1, size - 1]
        assert m["path_length"] % 2 == 0 and activity.search["attempts"] <= MAX_ATTEMPTS
        assert activity.params["size"] == size and activity.params["difficulty"] == level
        seen.add(activity.fingerprint)
        assert make(size, level, seed, f"syn-p{size}").fingerprint == activity.fingerprint  # deterministic
    assert len(seen) > 1 or size == 3  # different seeds do not collapse to one maze


def test_search_effort_stays_far_below_the_bound():
    worst = max(make(size, level, seed, f"syn-w{size}").search["attempts"] for size in SIZES for level in DIFFICULTIES for seed in range(10))
    assert worst < MAX_ATTEMPTS // 10


def test_levels_are_measurably_ordered_by_path_length():
    for size in (6, 9, 12):
        by_level = {lv: sum(make(size, lv, s, "syn-o").measures["path_length"] for s in SEEDS) for lv in DIFFICULTIES}
        assert by_level["easy"] < by_level["medium"] < by_level["hard"]


def test_seed_and_id_change_the_maze_and_the_fingerprint(sample):
    assert make(seed=2).fingerprint != sample.fingerprint
    assert make(activity_id="syn-other").fingerprint != sample.fingerprint


# ---- fail explicitly, never degrade ------------------------------------------------------------------
def test_unsatisfiable_search_fails_explicitly_without_relaxing(monkeypatch):
    monkeypatch.setattr(maze, "MAX_ATTEMPTS", 1)
    monkeypatch.setattr(maze_verify, "MAX_ATTEMPTS", 1)
    failures = 0
    for seed in range(8):
        try:
            activity = make(12, "hard", seed)
        except V2Error as exc:
            failures += 1
            assert exc.code == "UNSATISFIABLE" and "tentatives" in str(exc)
        else:  # lucky first attempt: it must still satisfy EVERY constraint
            m = activity.measures
            assert meets(12, "hard", m["path_length"], m["dead_ends"], m["decisions"])
    assert failures >= 1


def test_impossible_constraints_are_reported_not_hidden(monkeypatch):
    monkeypatch.setattr(maze, "meets", lambda *a: False)
    with pytest.raises(V2Error) as info:
        make(4, "easy")
    assert info.value.code == "UNSATISFIABLE"


@pytest.mark.parametrize("params,code", [
    ({"size": 2, "difficulty": "easy"}, "BAD_SIZE"), ({"size": 13, "difficulty": "easy"}, "BAD_SIZE"),
    ({"size": True, "difficulty": "easy"}, "BAD_SIZE"), ({"size": "5", "difficulty": "easy"}, "BAD_SIZE"),
    ({"size": 5.0, "difficulty": "easy"}, "BAD_SIZE"), ({"size": -1, "difficulty": "easy"}, "BAD_SIZE"),
    ({"size": 5, "difficulty": "extreme"}, "BAD_DIFFICULTY"), ({"size": 5, "difficulty": "EASY"}, "BAD_DIFFICULTY"),
    ({"size": 5, "difficulty": None}, "BAD_DIFFICULTY"),
    ({"size": 5}, "MISSING_PARAM"), ({"difficulty": "easy"}, "MISSING_PARAM"), ({}, "MISSING_PARAM"),
    ({"size": 5, "difficulty": "easy", "family": "hats"}, "UNKNOWN_PARAM"),
    ({"size": 5, "difficulty": "easy", "production_authorized": True}, "UNKNOWN_PARAM"),
    ("size=5", "BAD_PARAMS"), (None, "BAD_PARAMS"), ([("size", 5)], "BAD_PARAMS"),
])
def test_closed_parameters_are_refused(params, code):
    with pytest.raises(V2Error) as info:
        generate_v2("maze_v2", "syn-a", 0, params)
    assert info.value.code == code


@pytest.mark.parametrize("activity_id", ["P03-ACTIVITY", "p03", "syn-", "syn-UPPER", "syn-a b", "syn-é", "", "syn-" + "a" * 60,
                                         "halloween-p14", None, 3, "syn-a\n"])
def test_only_explicitly_synthetic_ids_are_accepted(activity_id):
    with pytest.raises(V2Error) as info:
        generate_v2("maze_v2", activity_id, 0, {"size": 5, "difficulty": "easy"})
    assert info.value.code == "BAD_ACTIVITY_ID"


def test_activity_id_length_boundary_is_exactly_fifty():
    assert len("syn-" + "a" * 46) == 50
    make(activity_id="syn-" + "a" * 46)
    for bad in ("syn-" + "a" * 47, "syn-" + "a" * 45 + "-"):
        with pytest.raises(V2Error):
            make(activity_id=bad)
    make(activity_id="syn-a")
    make(activity_id="syn-a-b")


@pytest.mark.parametrize("seed", [-1, 2**63, 1.0, "1", None, True])
def test_bad_seeds_are_refused(seed):
    with pytest.raises(V2Error) as info:
        generate_v2("maze_v2", "syn-a", seed, {"size": 5, "difficulty": "easy"})
    assert info.value.code == "BAD_SEED"


def test_unknown_mechanics_are_refused_and_registry_is_closed():
    for name in ("maze", "connect_dots", "match_v2", "", None, 3):
        with pytest.raises(V2Error) as info:
            generate_v2(name, "syn-a", 0, {})
        assert info.value.code == "UNKNOWN_MECHANIC"
    assert set(MECHANICS_V2) == {"maze_v2", "connect_dots_v2"}
    with pytest.raises(TypeError):
        MECHANICS_V2["x"] = None  # type: ignore[index]
    for bad in ({"mechanic": "nope"}, [], {}, None, {"mechanic": ["maze_v2"]}):
        assert verify_v2(bad)  # type: ignore[arg-type]  # a list of problems, never an exception


def test_a_failing_self_check_is_never_returned(monkeypatch):
    entry = MECHANICS_V2["maze_v2"]
    from lafractale.mechanics_v2 import registry
    monkeypatch.setattr(registry, "MECHANICS_V2", {"maze_v2": dataclasses.replace(entry, verify=lambda a: ["panne injectée"])})
    with pytest.raises(V2Error) as info:
        registry.generate_v2("maze_v2", "syn-a", 0, {"size": 5, "difficulty": "easy"})
    assert info.value.code == "SELF_CHECK_FAILED" and "panne injectée" in str(info.value)


# ---- independent verification: tampering -------------------------------------------------------------
def refingerprint(data: dict) -> dict:
    data["fingerprint"] = core.record_fingerprint(data)
    return data


def test_verifier_accepts_the_generated_record_and_a_roundtripped_one(sample):
    assert verify_maze_v2(sample.to_dict()) == []
    assert verify_maze_v2(loads_record(sample.canonical_bytes())) == []


def test_missing_or_extra_keys_and_wrong_markers_are_refused(sample):
    assert verify_maze_v2([]) and verify_maze_v2({})
    assert verify_maze_v2(tampered(sample, lambda d: d.pop("measures")))
    assert verify_maze_v2(tampered(sample, lambda d: d.update(extra=1)))
    for key, value in (("schema", "x"), ("kind", "PRODUCTION"), ("mechanic", "maze"), ("version", "9"),
                       ("human_pedagogical_validation", "VALIDATED"), ("production_authorized", True)):
        assert any(key in e or "production_authorized" in e for e in verify_maze_v2(refingerprint(tampered(sample, lambda d: d.update({key: value}))))), key


def test_removed_added_and_corrupted_passages_are_detected(sample):
    def remove(d):
        d["geometry"]["open_edges"].pop(3)
    def add(d):
        edges = {tuple(map(tuple, e)) for e in d["geometry"]["open_edges"]}
        for x in range(4):
            e = ((x, 0), (x, 1))
            if e not in edges:
                d["geometry"]["open_edges"].append([list(e[0]), list(e[1])])
                d["geometry"]["open_edges"].sort()
                return
    def non_adjacent(d):
        d["geometry"]["open_edges"][0] = [[0, 0], [2, 2]]
    def out_of_grid(d):
        d["geometry"]["open_edges"][0] = [[0, 0], [0, 99]]
    def duplicate(d):
        d["geometry"]["open_edges"].append(copy.deepcopy(d["geometry"]["open_edges"][0]))
    def unsorted(d):
        d["geometry"]["open_edges"].reverse()
    def reversed_edge(d):
        e = d["geometry"]["open_edges"][0]
        d["geometry"]["open_edges"][0] = [e[1], e[0]]
    def floaty(d):
        d["geometry"]["open_edges"][0] = [[0.0, 0], [0, 1]]
    for mutate in (remove, add, non_adjacent, out_of_grid, duplicate, unsorted, reversed_edge):
        assert verify_maze_v2(refingerprint(tampered(sample, mutate))), mutate.__name__
    assert verify_maze_v2(tampered(sample, floaty))  # floats are refused before any fingerprint is considered
    assert any("arbre couvrant" in e for e in verify_maze_v2(refingerprint(tampered(sample, remove))))
    assert any("arbre couvrant" in e for e in verify_maze_v2(refingerprint(tampered(sample, add))))


def test_wrong_solution_measures_level_and_params_are_detected(sample):
    def bad_path(d):
        d["solution"]["path"][1] = [0, 0]
    def bad_steps(d):
        d["solution"]["steps"] += 2
    def shorter(d):
        d["solution"]["path"] = d["solution"]["path"][:-1]
        d["solution"]["steps"] -= 1
    def bad_measure(d):
        d["measures"]["dead_ends"] += 1
    def bad_decisions(d):
        d["measures"]["decisions"] = 0
    def wrong_level(d):
        d["params"]["difficulty"] = "hard"
    def wrong_size(d):
        d["params"]["size"] = 6
    def bad_goal(d):
        d["geometry"]["goal"] = [0, 4]
    def bad_attempts(d):
        d["search"]["attempts"] = 0
    for mutate in (bad_path, bad_steps, shorter, bad_measure, bad_decisions, wrong_level, wrong_size, bad_goal, bad_attempts):
        assert verify_maze_v2(refingerprint(tampered(sample, mutate))), mutate.__name__
    assert any("niveau hard" in e for e in verify_maze_v2(refingerprint(tampered(sample, wrong_level))))


def test_booleans_and_lookalikes_cannot_replace_integers(sample):
    """False == 0 in Python: a second 'valid' record for the same maze would break canonical uniqueness."""
    def start(d):
        d["geometry"]["start"] = [False, False]
    def first_cell(d):
        d["solution"]["path"][0] = [False, False]
    def steps(d):
        d["solution"]["steps"] = float(d["solution"]["steps"])
    def measure(d):
        d["measures"]["dead_ends"] = bool(d["measures"]["dead_ends"]) if d["measures"]["dead_ends"] in (0, 1) else True
    def size(d):
        d["geometry"]["size"] = True if d["geometry"]["size"] == 1 else float(d["geometry"]["size"])
    def seed(d):
        d["seed"] = True
    def attempts(d):
        d["search"]["attempts"] = float(d["search"]["attempts"])
    for mutate in (start, first_cell, steps, size, seed, attempts):
        assert verify_maze_v2(tampered(sample, mutate)), mutate.__name__
    small = next(x for x in (make(3, "easy", n, "syn-b") for n in range(30)) if x.measures["dead_ends"] in (0, 1))
    for key in ("dead_ends", "decisions"):
        value = small.measures[key]
        if value in (0, 1):
            forged = tampered(small, lambda d, key=key: d["measures"].update({key: bool(value)}))
            assert verify_maze_v2(refingerprint(forged)), key  # a recomputed fingerprint cannot rescue a bool
    assert verify_maze_v2(refingerprint(tampered(sample, start)))


def test_search_metadata_and_seed_bounds_are_verified(sample):
    assert verify_maze_v2(refingerprint(tampered(sample, lambda d: d["search"].update(algorithm="evil"))))
    other = next(a for a in maze.ALGORITHMS if a != sample.search["algorithm"])
    assert verify_maze_v2(refingerprint(tampered(sample, lambda d: d["search"].update(algorithm=other))))
    assert verify_maze_v2(refingerprint(tampered(sample, lambda d: d.update(seed=2**70))))
    assert verify_maze_v2(refingerprint(tampered(sample, lambda d: d["search"].update(attempts=maze.MAX_ATTEMPTS + 1))))


def test_fingerprint_tampering_is_detected(sample):
    assert any("fingerprint" in e for e in verify_maze_v2(tampered(sample, lambda d: d.update(fingerprint="0" * 64))))
    assert any("fingerprint" in e for e in verify_maze_v2(tampered(sample, lambda d: d["measures"].update(span=0))))
    assert any("fingerprint" in e for e in verify_maze_v2(tampered(sample, lambda d: d["params"].update(difficulty="medium", size=5)) | {"seed": 9}))


def test_verifier_does_not_trust_generator_internals(monkeypatch, sample):
    """A generator bug cannot hide: break the generator's own analysis, the verifier still judges the record."""
    monkeypatch.setattr(maze, "_analyse", lambda *a: ([(0, 0)], 0, 0))
    assert verify_maze_v2(sample.to_dict()) == []
    assert verify_maze_v2(refingerprint(tampered(sample, lambda d: d["measures"].update(decisions=99))))


def test_historical_solver_is_used_as_a_second_opinion(monkeypatch, sample):
    monkeypatch.setattr(maze_verify, "maze_unique_path", lambda *a: (None, ["avis historique négatif"]))
    assert any("historique" in e for e in verify_maze_v2(sample.to_dict()))


# ---- immutability ------------------------------------------------------------------------------------
def _walk(value, seen=None):
    seen = seen if seen is not None else set()
    if value is None or isinstance(value, (str, int, bool)):
        return
    assert isinstance(value, (tuple, FrozenDict)) or (dataclasses.is_dataclass(value) and value.__dataclass_params__.frozen), type(value)
    if id(value) in seen:
        return
    seen.add(id(value))
    if isinstance(value, FrozenDict):
        for k, v in value.items():
            _walk(k, seen), _walk(v, seen)
    elif isinstance(value, tuple):
        for v in value:
            _walk(v, seen)
    else:
        for f in dataclasses.fields(value):
            _walk(getattr(value, f.name), seen)


def test_outputs_are_deeply_immutable(sample):
    _walk(sample)
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError, TypeError)):
        sample.seed = 3  # type: ignore[misc]
    with pytest.raises((AttributeError, TypeError)):
        sample.geometry["size"] = 9  # type: ignore[index]
    with pytest.raises(AttributeError):
        sample.geometry.size = 9  # type: ignore[attr-defined]
    with pytest.raises(AttributeError):
        del sample.geometry._items  # type: ignore[attr-defined]
    with pytest.raises(TypeError):
        sample.geometry["open_edges"][0] = None  # type: ignore[index]
    with pytest.raises(AttributeError):
        sample.geometry["open_edges"].append(None)  # type: ignore[attr-defined]
    assert hash(sample.geometry) == hash(make().geometry)


def test_direct_construction_cannot_smuggle_mutable_containers(sample):
    fields = {f.name: getattr(sample, f.name) for f in dataclasses.fields(sample)}
    fields["params"] = {"size": 5, "difficulty": ["medium"]}
    forged = V2Activity(**fields)
    _walk(forged)
    with pytest.raises(AttributeError):
        forged.params["difficulty"].append("x")  # type: ignore[attr-defined]  # frozen into a tuple
    fields["geometry"] = [1]
    with pytest.raises(V2Error):
        V2Activity(**fields)
    fields["geometry"] = {"f": 1.5}
    with pytest.raises(V2Error):
        V2Activity(**fields)
    assert verify_v2(forged)  # the forged record is not accepted either (fingerprint no longer matches)


def test_to_dict_returns_independent_copies(sample):
    before = sample.canonical_bytes()
    data = sample.to_dict()
    data["geometry"]["open_edges"].clear()
    data["solution"]["path"].append([9, 9])
    data["params"]["size"] = 12
    assert sample.canonical_bytes() == before and verify_maze_v2(sample) == []


def test_production_cannot_be_authorised(sample, monkeypatch):
    monkeypatch.setenv("PRODUCTION_AUTHORIZED", "1")
    monkeypatch.setenv("LAFRACTALE_PRODUCTION_AUTHORIZED", "true")
    assert PRODUCTION_AUTHORIZED is False and make().production_authorized is False
    assert "production_authorized" not in {f.name for f in dataclasses.fields(V2Activity)}
    with pytest.raises(TypeError):
        V2Activity(**{f.name: getattr(sample, f.name) for f in dataclasses.fields(sample)}, production_authorized=True)  # type: ignore[call-arg]
    assert sample.to_dict()["production_authorized"] is False


# ---- separation from the editorial data and the historical engine ----------------------------------------
def _imports(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_v2_never_touches_editorial_data_io_or_the_environment():
    allowed_lafractale = {"lafractale.mechanics_v2", "lafractale.security.strict_json", "lafractale.engine.solvers"}
    for path in sorted(PKG.glob("*.py")):
        imports = _imports(path)
        foreign = {n for n in imports if n.startswith("lafractale") and not n.startswith("lafractale.mechanics_v2")}
        assert foreign <= allowed_lafractale, (path.name, foreign)
        assert not {n for n in imports if n.split(".")[0] in {"csv", "yaml", "os", "subprocess", "socket", "urllib", "requests", "pathlib", "shutil", "random", "time", "datetime"}}, path.name
        module = ast.parse(path.read_text(encoding="utf-8"))
        module.body[0].value.value = ""  # docstring may name the forbidden notions
        code = ast.unparse(module)
        for token in ("PageRecord", "scenario_b", "load_pages", "open(", "environ", "getenv", "argv", "write_text", "SpecSet", ".csv"):
            assert token not in code, (path.name, token)
    assert "lafractale.engine.solvers" in _imports(PKG / "maze_verify.py")


def test_no_api_accepts_page_records_or_editorial_objects():
    from lafractale.scenario_b.pages import load_pages
    pages = load_pages(ROOT)
    for source in (pages.page(14), pages, pages.page(14).to_dict(), "PageRecord", object()):
        with pytest.raises(V2Error):
            generate_v2("maze_v2", "syn-a", 0, source)  # type: ignore[arg-type]
    with pytest.raises(V2Error):
        generate_v2("maze_v2", pages.page(14).title, 0, {"size": 5, "difficulty": "easy"})
    signature = inspect.signature(generate_v2)
    assert list(signature.parameters) == ["mechanic", "activity_id", "seed", "params"]


def test_nothing_historical_imports_v2():
    offenders = []
    for path in (ROOT / "src/lafractale").rglob("*.py"):
        if "mechanics_v2" in path.parts:
            continue
        if "mechanics_v2" in path.read_text(encoding="utf-8"):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_generation_writes_nothing(tmp_path, monkeypatch):
    import builtins
    import os
    writes = []
    real_open, real_os_open = builtins.open, os.open
    monkeypatch.setattr(builtins, "open", lambda f, m="r", *a, **k: (writes.append(f) if set(m) & set("wax+") else None, real_open(f, m, *a, **k))[1])
    monkeypatch.setattr(os, "open", lambda p, fl, *a, **k: (writes.append(p) if fl & (os.O_WRONLY | os.O_RDWR | os.O_CREAT) else None, real_os_open(p, fl, *a, **k))[1])
    make(8, "hard", 3)
    assert writes == []
