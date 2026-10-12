"""Independent solution verification (maze uniqueness is measured on the structure)."""
import copy
import random
from dataclasses import replace

import pytest

from lafractale.activities.engine import generate, generate_connect, generate_match, generate_maze, stable_seed
from lafractale.activities.models import ActivitySpec
from lafractale.engine import solvers
from lafractale.engine.registry import MECHANICS


def _activity(kind, seed=7, **kw):
    spec = ActivitySpec(f"t-{kind}", 1, kind, (4, 5), "scène d'essai", kw.pop("vocabulary", ()), **kw)
    return generate(spec, stable_seed("synthetic_t", spec.id, seed))


@pytest.fixture
def maze():
    return _activity("maze")


@pytest.fixture
def dots():
    return _activity("connect_dots", shape="star")


@pytest.fixture
def match():
    return _activity("match")


def test_generated_activities_pass_every_mechanic(maze, dots, match):
    for activity in (maze, dots, match):
        assert MECHANICS[activity.type].verify(activity) == []


def test_all_three_shapes_and_families_are_accepted():
    for shape in ("moon", "house", "star"):
        assert MECHANICS["connect_dots"].verify(_activity("connect_dots", shape=shape)) == []
    for vocabulary in ((), ("hat",), ("gift",)):
        assert MECHANICS["match"].verify(_activity("match", vocabulary=vocabulary)) == []


def test_generated_mazes_are_spanning_trees_over_many_seeds():
    for seed in range(300):
        geometry, answer = generate_maze(random.Random(seed))
        path, reasons = solvers.maze_unique_path(geometry["size"], geometry["open_edges"])
        assert reasons == [] and [list(p) for p in path] == answer["path"]


def test_maze_with_cycle_is_refused_although_a_path_exists(maze):
    """A second passage creates two solutions: the answer is no longer unique."""
    geometry = copy.deepcopy(maze.geometry)
    used = {frozenset(map(tuple, e)) for e in geometry["open_edges"]}
    size = geometry["size"]
    extra = next(([[x, y], [x + 1, y]] for y in range(size) for x in range(size - 1)
                  if frozenset(((x, y), (x + 1, y))) not in used))
    geometry["open_edges"].append(extra)
    errors = solvers.verify_maze(replace(maze, geometry=geometry))
    assert any("cycle" in e for e in errors), errors


def test_disconnected_maze_is_refused(maze):
    geometry = copy.deepcopy(maze.geometry)
    geometry["open_edges"].pop()
    errors = solvers.verify_maze(replace(maze, geometry=geometry))
    assert any("arbre couvrant" in e for e in errors), errors


def test_maze_with_right_edge_count_but_a_cycle_and_an_isolated_cell_is_refused():
    """3x3, 8 passages (= n*n-1) yet a 4-cycle and an unreachable goal cell."""
    edges = [[[0, 0], [1, 0]], [[1, 0], [1, 1]], [[1, 1], [0, 1]], [[0, 1], [0, 0]],
             [[1, 0], [2, 0]], [[2, 0], [2, 1]], [[0, 1], [0, 2]], [[0, 2], [1, 2]]]
    path, reasons = solvers.maze_unique_path(3, edges)
    assert path is None and any("inaccessible" in r for r in reasons), reasons


def test_maze_wrong_or_truncated_answer_is_refused(maze):
    wrong = replace(maze, answer={"path": [[0, 0], [4, 4]], "steps": 1})
    assert any("chemin unique" in e for e in solvers.verify_maze(wrong))
    bad_steps = replace(maze, answer={**maze.answer, "steps": maze.answer["steps"] + 1})
    assert any("nombre de pas" in e for e in solvers.verify_maze(bad_steps))


def test_maze_edge_errors_are_reported(maze):
    geometry = copy.deepcopy(maze.geometry)
    geometry["open_edges"][0] = [[0, 0], [2, 0]]
    assert any("non adjacentes" in e for e in solvers.verify_maze(replace(maze, geometry=geometry)))
    geometry["open_edges"][0] = [[0, 0], [9, 0]]
    assert any("hors grille" in e for e in solvers.verify_maze(replace(maze, geometry=geometry)))


def test_dots_crossing_contour_is_refused(dots):
    geometry = copy.deepcopy(dots.geometry)
    pts = geometry["points"]
    pts[2]["x"], pts[2]["y"], pts[6]["x"], pts[6]["y"] = pts[6]["x"], pts[6]["y"], pts[2]["x"], pts[2]["y"]
    assert any("se croisent" in e for e in solvers.verify_connect_dots(replace(dots, geometry=geometry)))


def test_dots_wrong_numbering_order_and_closure_are_refused(dots):
    geometry = copy.deepcopy(dots.geometry)
    geometry["points"][3]["n"] = 9
    assert solvers.verify_connect_dots(replace(dots, geometry=geometry))
    assert any("corrigé" in e for e in solvers.verify_connect_dots(
        replace(dots, answer={"order": list(range(1, 10)), "close_to": 1})))
    assert any("corrigé" in e for e in solvers.verify_connect_dots(
        replace(dots, answer={"order": dots.answer["order"], "close_to": 2})))
    geometry = {**dots.geometry, "closed": False}
    assert any("fermé" in e for e in solvers.verify_connect_dots(replace(dots, geometry=geometry)))


def test_dots_incomplete_shape_is_refused(dots):
    geometry = copy.deepcopy(dots.geometry)
    geometry["points"] = geometry["points"][:6]
    assert any("points attendus" in e for e in solvers.verify_connect_dots(replace(dots, geometry=geometry)))


def test_match_wrong_pairing_and_non_bijection_are_refused(match):
    pairs = list(match.answer["left_to_right"])
    swapped = [pairs[1], pairs[0], *pairs[2:]]
    assert any("différent" in e for e in solvers.verify_match(replace(match, answer={"left_to_right": swapped})))
    assert any("bijectif" in e for e in solvers.verify_match(replace(match, answer={"left_to_right": [0, 0, 1, 2]})))


def test_match_duplicate_or_trivial_columns_are_refused(match):
    geometry = copy.deepcopy(match.geometry)
    geometry["right_symbols"] = list(geometry["left_symbols"])
    assert any("triviale" in e for e in solvers.verify_match(replace(match, geometry=geometry)))
    geometry = copy.deepcopy(match.geometry)
    geometry["left_symbols"][1] = geometry["left_symbols"][0]
    assert any("répétés" in e for e in solvers.verify_match(replace(match, geometry=geometry)))


def test_segment_touch_primitive():
    assert solvers.segments_touch((0, 0), (1, 1), (0, 1), (1, 0))
    assert solvers.segments_touch((0, 0), (1, 0), (1, 0), (2, 0))  # shared end point
    assert not solvers.segments_touch((0, 0), (1, 0), (0, 1), (1, 1))


def test_generators_used_are_the_existing_ones():
    assert generate_connect(random.Random(1), "star")[1]["close_to"] == 1
    assert generate_match(random.Random(1), "shapes")[0]["family"] == "shapes"
