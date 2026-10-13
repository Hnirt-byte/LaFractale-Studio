"""B3-B.3c.1 — hardening of the v2 verifiers and of the common API against hostile input.

Contract under test (see docs/B3B3C1_HARDENING_AND_DEBT.md):

* ORDINARY JSON/dict records (plain ``dict``/``list``/``str``/``int``/``float``/``bool``/``None``): every verifier
  and ``verify_v2`` return a NON-EMPTY list of short strings for any invalid record, never raise, never accept.
* ``generate_v2`` refuses hostile arguments with ``V2Error`` (a stable code) and a bounded message, never with
  ``ValueError`` / ``RecursionError`` / ``TypeError``.
* ARBITRARY Python objects (subclasses with hostile dunders, custom mappings, cyclic structures) are outside the
  contract; the ones detectable by exact type are refused without being inspected, rendered or compared.
"""
from __future__ import annotations

import ast
import json
import tracemalloc
from pathlib import Path

import pytest

from lafractale.mechanics_v2 import core
from lafractale.mechanics_v2.connect_dots_verify import diagnose_connect_dots_v2, verify_connect_dots_v2
from lafractale.mechanics_v2.core import (
    MAX_RECORD_NODES, MAX_REPORTED_PROBLEMS, V2Error, bounded_repr, cap_problems, hostile_shape, loads_record,
)
from lafractale.mechanics_v2.match_verify import verify_match_v2
from lafractale.mechanics_v2.maze_verify import verify_maze_v2
from lafractale.mechanics_v2.registry import MECHANICS_V2, generate_v2, verify_v2

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "src/lafractale/mechanics_v2"

PARAMS = {
    "maze_v2": {"size": 5, "difficulty": "medium"},
    "connect_dots_v2": {"points": 8, "closed": True, "shape": "radial"},
    "match_v2": {"pairs": 4, "relation": "twin", "family": "polygon"},
}
VERIFIERS = {"maze_v2": verify_maze_v2, "connect_dots_v2": verify_connect_dots_v2, "match_v2": verify_match_v2}
MESSAGE_BUDGET = 20_000  # characters over a whole error list, whatever the hostile payload


def deep_list(n: int) -> list:
    value: list = []
    for _ in range(n):
        value = [value]
    return value


def deep_dict(n: int) -> dict:
    value: dict = {}
    for _ in range(n):
        value = {"a": value}
    return value


class EvilInt(int):
    def __eq__(self, other):  # noqa: D105
        raise RuntimeError("__eq__ must never be called")

    __hash__ = int.__hash__

    def __repr__(self):
        raise RuntimeError("__repr__ must never be called")


class EvilStr(str):
    def __eq__(self, other):
        raise RuntimeError("__eq__ must never be called")

    __hash__ = str.__hash__

    def __repr__(self):
        raise RuntimeError("__repr__ must never be called")


class EvilObject:
    def __repr__(self):
        raise RuntimeError("__repr__ must never be called")

    __str__ = __eq__ = __hash__ = __repr__


class EvilDict(dict):
    def items(self):
        raise RuntimeError("must never be iterated")

    __iter__ = __len__ = __getitem__ = items


def cyclic_list() -> list:
    value: list = [0]
    value.append(value)
    return value


def shared_explosion(levels: int = 40) -> list:
    """2**levels visits through shared references (a DAG): only the node budget stops the walk."""
    value: list = [0]
    for _ in range(levels):
        value = [value, value]
    return value


HOSTILE = {
    "huge_int": lambda: 10 ** 5000,
    "negative_huge_int": lambda: -(10 ** 5000),
    "int_4097_bits": lambda: 1 << 4097,
    "deep_list": lambda: deep_list(100_000),
    "deep_dict": lambda: deep_dict(100_000),
    "nested_9_levels": lambda: deep_list(9),
    "nan": lambda: float("nan"),
    "inf": lambda: float("inf"),
    "float": lambda: 1.5,
    "none": lambda: None,
    "text": lambda: "x",
    "long_text": lambda: "é" * 100_000,
    "bytes": lambda: b"ab",
    "object": lambda: EvilObject(),
    "set": lambda: {1},
    "tuple": lambda: (1, 2),
    "bool": lambda: True,
    "empty_list": lambda: [],
    "empty_dict": lambda: {},
    "big_list": lambda: [0] * 200_000,
    "big_pairs": lambda: [[0, 0]] * 50_000,
    "int_subclass": lambda: EvilInt(3),
    "str_subclass": lambda: EvilStr("x"),
    "evil_dict": lambda: EvilDict(),
    "int_key_dict": lambda: {1: 2},
    "cyclic": cyclic_list,
    "shared_explosion": shared_explosion,
    "negative": lambda: -1,
    "zero": lambda: 0,
}


def base_record(mechanic: str) -> dict:
    return generate_v2(mechanic, "syn-hard", 3, PARAMS[mechanic]).to_dict()


def clone(value):
    """Cheap structural copy of a (small, valid) record; hostile payloads are never cloned."""
    if isinstance(value, dict):
        return {k: clone(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clone(v) for v in value]
    return value


def paths(node, prefix=(), limit=3):
    yield prefix
    if isinstance(node, dict):
        for key in node:
            yield from paths(node[key], prefix + (key,), limit)
    elif isinstance(node, list):
        for index in range(min(len(node), limit)):
            yield from paths(node[index], prefix + (index,), limit)


def lookup(root, path):
    for step in path:
        root = root[step]
    return root


def assert_refusal(problems, label=""):
    assert isinstance(problems, list), label
    assert problems, f"{label}: hostile input accepted"
    assert all(type(p) is str for p in problems), label
    assert len(problems) <= MAX_REPORTED_PROBLEMS + 1, label
    assert sum(len(p) for p in problems) <= MESSAGE_BUDGET, label


# ---- the guard itself ----------------------------------------------------------------------------------
@pytest.mark.parametrize("name", sorted(HOSTILE))
def test_hostile_shape_never_raises_and_flags_every_hostile_value(name):
    value = HOSTILE[name]()
    reason = hostile_shape({"k": value})
    harmless = {"float", "none", "text", "bool", "empty_list", "empty_dict", "negative", "zero", "nan", "inf"}
    if name in harmless:
        assert reason is None
    else:
        assert isinstance(reason, str) and reason


def test_hostile_shape_accepts_every_valid_record_with_a_wide_margin():
    cases = [("maze_v2", {"size": s, "difficulty": d}) for s in (3, 12) for d in ("easy", "medium", "hard")]
    cases += [("connect_dots_v2", {"points": n, "closed": c, "shape": "radial"}) for n in (5, 24) for c in (True, False)]
    cases += [("match_v2", {"pairs": 6, "relation": "twin", "family": "polygon"}),
              ("match_v2", {"pairs": 6, "relation": "count", "family": "polygon"}),
              ("match_v2", {"pairs": 6, "relation": "twin", "family": "mixed"})]
    for mechanic, params in cases:
        record = generate_v2(mechanic, "syn-edge", 0, params).to_dict()
        assert hostile_shape(record) is None, (mechanic, params)
        assert node_count(record) * 2 <= MAX_RECORD_NODES, (mechanic, params, node_count(record))


def node_count(value) -> int:
    stack, total = [value], 0
    while stack:
        item = stack.pop()
        total += 1
        if isinstance(item, dict):
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)
    return total


def test_bounded_repr_is_total_and_short():
    for factory in HOSTILE.values():
        text = bounded_repr(factory())
        assert type(text) is str and len(text) <= 1000
    assert bounded_repr("a" * 500).endswith("car.)")
    assert bounded_repr(10 ** 5000) == f"<entier de {(10 ** 5000).bit_length()} bits>"
    assert bounded_repr(deep_list(100_000)) == "[[[<list de 1 éléments>]]]"  # 3 levels, then a summary
    assert bounded_repr(7) == "7" and bounded_repr(None) == "None" and bounded_repr("é") == "'é'"


def test_cap_problems_keeps_a_non_empty_list_non_empty():
    assert cap_problems(["a"]) == ["a"]
    capped = cap_problems([str(i) for i in range(1000)])
    assert len(capped) == MAX_REPORTED_PROBLEMS + 1 and "900" in capped[-1]


# ---- every verifier, every field, every hostile value ----------------------------------------------------
@pytest.mark.parametrize("mechanic", sorted(PARAMS))
def test_baseline_is_valid(mechanic):
    assert verify_v2(base_record(mechanic)) == []
    assert VERIFIERS[mechanic](base_record(mechanic)) == []


@pytest.mark.parametrize("mechanic", sorted(PARAMS))
def test_any_single_hostile_mutation_is_refused_without_exception(mechanic):
    base = base_record(mechanic)
    checked = 0
    for path in paths(base):
        if not path:
            continue
        original = lookup(base, path)
        for name, factory in HOSTILE.items():
            record = clone(base)
            value = factory()
            if type(original) is type(value) and not isinstance(value, (list, dict)) and original == value:
                continue  # the mutation is the identity: nothing hostile happened
            lookup(record, path[:-1])[path[-1]] = value
            for entry in (verify_v2, VERIFIERS[mechanic]):
                assert_refusal(entry(record), f"{mechanic} {name}@{'/'.join(map(str, path))}")
            checked += 1
    assert checked > 400  # the sweep really covers the record


@pytest.mark.parametrize("mechanic", sorted(PARAMS))
def test_any_field_deletion_or_addition_is_refused(mechanic):
    base = base_record(mechanic)
    for path in paths(base):
        if not path or not isinstance(path[-1], str):
            continue  # list entries are covered by the mutation sweep; deleting a key changes the key set
        record = clone(base)
        del lookup(record, path[:-1])[path[-1]]
        assert_refusal(verify_v2(record), f"{mechanic} del {path}")
    for target in ([], ["geometry"], ["params"], ["solution"], ["measures"], ["search"]):
        record = clone(base)
        lookup(record, target)["zz_extra"] = 1
        assert_refusal(verify_v2(record), f"{mechanic} extra {target}")


@pytest.mark.parametrize("mechanic", sorted(PARAMS))
def test_hostile_top_level_values_are_refused(mechanic):
    for name, factory in HOSTILE.items():
        for entry in (verify_v2, VERIFIERS[mechanic]):
            assert_refusal(entry(factory()), f"{mechanic} top-level {name}")


@pytest.mark.parametrize("mechanic", sorted(PARAMS))
def test_hostile_values_in_every_top_level_field_at_once(mechanic):
    base = base_record(mechanic)
    for name in ("huge_int", "deep_list", "deep_dict", "long_text", "big_list", "cyclic", "shared_explosion"):
        record = {key: HOSTILE[name]() for key in base}
        record["mechanic"] = mechanic
        for entry in (verify_v2, VERIFIERS[mechanic]):
            assert_refusal(entry(record), f"{mechanic} all fields {name}")


def test_problem_report_is_capped_when_the_shape_guard_passes():
    """1 000 invalid passages stay under the node budget: only ``cap_problems`` bounds the report (100 + 1 lines)."""
    record = base_record("maze_v2")
    record["geometry"]["open_edges"] = [[0, 1]] * 1000
    problems = verify_v2(record)
    assert len(problems) == MAX_REPORTED_PROBLEMS + 1 and "autre(s) problème(s)" in problems[-1]
    assert_refusal(problems)


@pytest.mark.parametrize("mechanic", sorted(PARAMS))
def test_oversized_ordinary_record_is_refused_by_the_shape_guard(mechanic):
    record = base_record(mechanic)
    field = {"maze_v2": "open_edges", "connect_dots_v2": "points", "match_v2": "left"}[mechanic]
    record["geometry"][field] = [[0, 1]] * 3000  # 9 001 nodes: over the budget
    assert verify_v2(record) == ["enregistrement hostile : plus de 4096 éléments"]


def test_shape_guard_refuses_a_huge_container_before_walking_it():
    assert hostile_shape([0] * 3_000_000) is not None
    assert hostile_shape({str(i): 0 for i in range(5000)}) is not None
    assert hostile_shape([0] * 4000) is None  # 4 001 nodes: still inside the budget


def test_shape_guard_thresholds_just_below_the_limits_are_accepted():
    assert hostile_shape({"a": 2 ** 4095, "b": -(2 ** 4095), "c": "x" * 256, "d" * 64: 1}) is None
    assert hostile_shape({"a": 1 << 4096}) is not None
    assert hostile_shape({"a": "x" * 257}) is not None and hostile_shape({"k" * 65: 1}) is not None
    assert hostile_shape(deep_list(7)) is None and hostile_shape(deep_list(9)) is not None


def test_keys_summary_is_bounded():
    assert core.keys_summary({str(i): 0 for i in range(40)}).endswith("(+28)")


@pytest.mark.parametrize("mechanic", sorted(PARAMS))
def test_hostile_objects_are_refused_without_being_inspected(mechanic):
    """EvilInt/EvilStr/EvilObject raise if compared or rendered: the refusal happens by exact type, before that."""
    base = base_record(mechanic)
    for path in paths(base):
        if len(path) < 1:
            continue
        for factory in (lambda: EvilInt(3), lambda: EvilStr("x"), EvilObject, EvilDict):
            record = clone(base)
            lookup(record, path[:-1])[path[-1]] = factory()
            assert_refusal(verify_v2(record), f"{mechanic} evil@{path}")


def test_diagnostic_is_silent_on_hostile_shape():
    record = base_record("connect_dots_v2")
    record["geometry"]["points"][0]["x"] = 10 ** 5000
    assert diagnose_connect_dots_v2(record) == []
    record["geometry"] = deep_list(100_000)
    assert diagnose_connect_dots_v2(record) == []


# ---- the common API -----------------------------------------------------------------------------------
def test_verify_v2_always_returns_a_list_for_any_input():
    for name, factory in HOSTILE.items():
        assert_refusal(verify_v2(factory()), name)
        assert_refusal(verify_v2({"mechanic": factory()}), f"mechanic={name}")
    for odd in (None, 0, "maze_v2", [], b"x", object()):
        assert_refusal(verify_v2(odd))


def test_verify_v2_refusal_of_unknown_mechanic_names_nothing_hostile():
    problems = verify_v2({"mechanic": "x" * 100_000})
    assert len(problems) == 1 and len(problems[0]) < 300
    assert "x" * 100 not in problems[0]


OK_PARAMS = {
    "maze_v2": {"size": 4, "difficulty": "easy"},
    "connect_dots_v2": {"points": 6, "closed": True, "shape": "radial"},
    "match_v2": {"pairs": 3, "relation": "twin", "family": "polygon"},
}


def refused(*args):
    with pytest.raises(V2Error) as info:
        generate_v2(*args)
    assert info.value.code and len(str(info.value)) <= 400
    return info.value


@pytest.mark.parametrize("name", sorted(HOSTILE))
def test_generate_v2_refuses_hostile_arguments_with_v2error_only(name):
    make = HOSTILE[name]
    refused(make(), "syn-a", 1, OK_PARAMS["maze_v2"])  # mechanic
    refused("maze_v2", make(), 1, OK_PARAMS["maze_v2"])  # activity id
    if name != "zero":  # 0 is a valid seed
        refused("maze_v2", "syn-a", make(), OK_PARAMS["maze_v2"])
    refused("maze_v2", "syn-a", 1, make())  # whole parameter mapping
    for mechanic, params in OK_PARAMS.items():
        for key in params:
            if name == "bool" and params[key] is True:
                continue  # connect_dots.closed accepts a real boolean
            refused(mechanic, "syn-a", 1, {**params, key: make()})
        try:
            hash(make())
        except Exception:  # noqa: BLE001 - unhashable (or hostile) objects cannot be dict keys
            continue
        assert refused(mechanic, "syn-a", 1, {**params, make(): 1}).code == "UNKNOWN_PARAM"


def test_generate_v2_unknown_parameter_with_huge_integer_key():
    with pytest.raises(V2Error) as info:
        generate_v2("maze_v2", "syn-a", 1, {"size": 4, "difficulty": "easy", 10 ** 5000: 1})
    assert info.value.code == "UNKNOWN_PARAM" and len(str(info.value)) < 200


def test_generate_v2_error_codes_are_preserved():
    expected = [
        (("maze_v2", "syn-a", 1, {"size": 99, "difficulty": "easy"}), "BAD_SIZE"),
        (("maze_v2", "syn-a", 1, {"size": 4, "difficulty": "nope"}), "BAD_DIFFICULTY"),
        (("maze_v2", "syn-a", 1, {"size": 4}), "MISSING_PARAM"),
        (("maze_v2", "syn-a", 1, {"size": 4, "difficulty": "easy", "x": 1}), "UNKNOWN_PARAM"),
        (("maze_v2", "P03-ACTIVITY", 1, {"size": 4, "difficulty": "easy"}), "BAD_ACTIVITY_ID"),
        (("maze_v2", "syn-a", -1, {"size": 4, "difficulty": "easy"}), "BAD_SEED"),
        (("maze_v2", "syn-a", True, {"size": 4, "difficulty": "easy"}), "BAD_SEED"),
        (("nope", "syn-a", 1, {}), "UNKNOWN_MECHANIC"),
        (("connect_dots_v2", "syn-a", 1, {"points": 4, "closed": True, "shape": "radial"}), "BAD_POINTS"),
        (("connect_dots_v2", "syn-a", 1, {"points": 6, "closed": 1, "shape": "radial"}), "BAD_CLOSED"),
        (("connect_dots_v2", "syn-a", 1, {"points": 6, "closed": True, "shape": "star"}), "BAD_SHAPE"),
        (("match_v2", "syn-a", 1, {"pairs": 99, "relation": "twin", "family": "polygon"}), "BAD_PAIRS"),
        (("match_v2", "syn-a", 1, {"pairs": 3, "relation": "x", "family": "polygon"}), "BAD_RELATION"),
        (("match_v2", "syn-a", 1, {"pairs": 3, "relation": "twin", "family": "x"}), "BAD_FAMILY"),
    ]
    for args, code in expected:
        with pytest.raises(V2Error) as info:
            generate_v2(*args)
        assert info.value.code == code, args


@pytest.mark.parametrize("payload", [
    b"[" * 100_000 + b"]" * 100_000, b'{"a":' * 100_000 + b"1" + b"}" * 100_000,
    b'{"a":' + b"9" * 5000 + b"}", b"\xff\xfe", b'{"a":NaN}', b'{"a":1,"a":2}', b"[]", b"",
])
def test_loads_record_refuses_hostile_bytes_with_v2error(payload):
    with pytest.raises(V2Error):
        loads_record(payload)


def test_loads_record_round_trip_of_a_valid_record_still_verifies():
    for mechanic in PARAMS:
        activity = generate_v2(mechanic, "syn-json", 2, PARAMS[mechanic])
        record = loads_record(activity.canonical_bytes())
        assert verify_v2(record) == []


# ---- non-regression -----------------------------------------------------------------------------------
def test_reference_fingerprints_are_unchanged():
    """254 combinations captured on main@2f5a55e (before this hardening): fingerprints and refusal codes identical."""
    reference = json.loads((ROOT / "tests/fixtures/b3b3c1_reference_fingerprints.json").read_text(encoding="utf-8"))
    assert len(reference) == 254

    def current(key: str) -> str:
        mechanic, *rest = key.split("|")
        if mechanic == "maze_v2":
            size, difficulty, seed = rest
            args = (int(seed), {"size": int(size), "difficulty": difficulty})
        elif mechanic == "connect_dots_v2":
            points, closed, seed = rest
            args = (int(seed), {"points": int(points), "closed": closed == "True", "shape": "radial"})
        else:
            pairs, relation, family, seed = rest
            args = (int(seed), {"pairs": int(pairs), "relation": relation, "family": family})
        try:
            return generate_v2(mechanic, "syn-base", *args).fingerprint
        except V2Error as exc:
            return "ERR:" + exc.code

    for key, expected in reference.items():
        assert current(key) == expected, key


def test_valid_records_are_accepted_by_every_entry_point_and_json_round_trip():
    for mechanic, params in PARAMS.items():
        activity = generate_v2(mechanic, "syn-ok", 9, params)
        assert verify_v2(activity) == [] and verify_v2(activity.to_dict()) == []
        assert MECHANICS_V2[mechanic].verify(activity) == []
        assert verify_v2(json.loads(json.dumps(activity.to_dict()))) == []


def test_ordinary_invalid_records_keep_their_specific_diagnostics():
    record = base_record("maze_v2")
    record["geometry"]["open_edges"].pop()
    assert any("arbre couvrant" in p for p in verify_v2(record))
    record = base_record("connect_dots_v2")
    record["geometry"]["points"][3]["x"] = 10 ** 400
    assert any("points et centre" in p for p in verify_v2(record))


# ---- discipline: no blanket capture ---------------------------------------------------------------------
def test_verifiers_have_no_blanket_exception_capture():
    """Hardening is validation first: the verifiers must not mask programming errors behind a broad ``except``."""
    allowed = {"V2Error", "ValueError", "TypeError", "KeyError"}  # fingerprint computation / diagnose lookup: narrow types only
    for module in ("maze_verify.py", "connect_dots_verify.py", "match_verify.py"):
        tree = ast.parse((PKG / module).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                assert node.type is not None, f"{module}: bare except"
                names = {n.id for n in ast.walk(node.type) if isinstance(n, ast.Name)}
                assert names <= allowed, (module, names)
                assert "Exception" not in names and "BaseException" not in names and "RecursionError" not in names
                assert "OverflowError" not in names, module
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "verify_match_v2"]
        assert not calls


def test_verifiers_never_build_unbounded_text_from_input():
    """No ``!r`` / ``str()`` / ``map(str, ...)`` of a record field in the verifiers: bounded_repr only."""
    for module in ("maze_verify.py", "connect_dots_verify.py", "match_verify.py", "registry.py"):
        source = (PKG / module).read_text(encoding="utf-8")
        assert "!r}" not in source.replace("{expected!r}", ""), module
        assert "map(str" not in source, module


def test_no_new_dependency_and_no_editorial_coupling():
    source = (PKG / "core.py").read_text(encoding="utf-8")
    imports = [n for n in ast.walk(ast.parse(source)) if isinstance(n, (ast.Import, ast.ImportFrom))]
    modules = {getattr(n, "module", None) or n.names[0].name for n in imports}
    assert not any("scenario_b" in (m or "") or "editorial" in (m or "") for m in modules)
    assert core.MAX_RECORD_INT_BITS == 4096  # stays under CPython's default 4 300-digit conversion limit


# ---- memory: no auxiliary list of all the entries of a large ordinary dict ---------------------------------
def peak_bytes(call) -> int:
    tracemalloc.start()
    try:
        call()
        return tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


def test_bounded_repr_of_a_large_dict_does_not_materialise_its_entries():
    big = {str(i): i for i in range(1_000_000)}  # built before measuring
    text = bounded_repr(big)
    assert text.endswith(", …}") and text.count(": ") == 6
    assert peak_bytes(lambda: bounded_repr(big)) < 64 * 1024  # list(items())[:6] would need tens of megabytes


def test_check_params_with_a_huge_number_of_unknown_keys_collects_at_most_nine():
    spec = MECHANICS_V2["maze_v2"].params
    big = {"size": 4, "difficulty": "easy", **{f"x{i:07d}": i for i in range(1_000_000)}}
    with pytest.raises(V2Error) as info:
        core.check_params(big, spec)
    assert info.value.code == "UNKNOWN_PARAM" and "et d'autres" in str(info.value)
    assert str(info.value).count("x00") == 8 and len(str(info.value)) < 400

    def call():
        with pytest.raises(V2Error):
            core.check_params(big, spec)

    assert peak_bytes(call) < 64 * 1024  # a list of the 1 000 000 unknown keys would need about 8 MB


def test_check_params_unknown_keys_message_is_unchanged_for_a_few_keys():
    spec = MECHANICS_V2["maze_v2"].params
    with pytest.raises(V2Error) as info:
        core.check_params({"size": 4, "difficulty": "easy", "b": 1, "a": 2}, spec)
    assert info.value.code == "UNKNOWN_PARAM" and str(info.value).endswith("a, b")
    with pytest.raises(V2Error) as info:  # exactly eight unknown keys: no ellipsis
        core.check_params({"size": 4, "difficulty": "easy", **{f"k{i}": 0 for i in range(8)}}, spec)
    assert "et d'autres" not in str(info.value)
    with pytest.raises(V2Error) as info:  # nine: ellipsis
        core.check_params({"size": 4, "difficulty": "easy", **{f"k{i}": 0 for i in range(9)}}, spec)
    assert "et d'autres" in str(info.value)
