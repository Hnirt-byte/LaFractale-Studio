from dataclasses import replace
from copy import deepcopy
from lafractale.activities.engine import generate,stable_seed,MOON_12,shortest_path
from lafractale.activities.models import ActivitySpec
from lafractale.quality.checks import validate_activity,validate_collection


def test_moon_has_complete_twelve_points(activities):
    moon=next(a for a in activities if a.type=="connect_dots")
    assert moon.geometry["shape"]=="moon"
    assert len(MOON_12)==len(moon.geometry["points"])==12
    assert [p["n"] for p in moon.geometry["points"]]==list(range(1,13))
    assert moon.answer["close_to"]==1
    assert validate_activity(moon)==[]


def test_incomplete_moon_is_rejected(activities):
    moon=next(a for a in activities if a.type=="connect_dots")
    g=deepcopy(moon.geometry)
    g["points"]=g["points"][:8]
    assert validate_activity(replace(moon,geometry=g))


def test_dots_wrong_numbering_rejected(activities):
    moon=next(a for a in activities if a.type=="connect_dots")
    g=deepcopy(moon.geometry)
    g["points"][6]["n"]=12
    assert any("numérotation" in e for e in validate_activity(replace(moon,geometry=g)))


def test_maze_is_reachable_and_key_verified(activities):
    maze=next(a for a in activities if a.type=="maze")
    assert maze.answer["path"] == shortest_path(maze.geometry["size"],maze.geometry["open_edges"])
    assert validate_activity(maze)==[]


def test_blocked_maze_is_rejected(activities):
    maze=next(a for a in activities if a.type=="maze")
    g=deepcopy(maze.geometry); g["open_edges"]=[]
    assert any("bloqué" in e for e in validate_activity(replace(maze,geometry=g)))


def test_wrong_maze_solution_is_rejected(activities):
    maze=next(a for a in activities if a.type=="maze")
    assert validate_activity(replace(maze,answer={"path": [[0,0],[4,4]],"steps":1}))


def test_matching_bijection_is_valid(activities):
    match=next(a for a in activities if a.type=="match")
    assert validate_activity(match)==[]
    for i,j in enumerate(match.answer["left_to_right"]):
        assert match.geometry["left_symbols"][i]==match.geometry["right_symbols"][j]


def test_matching_inconsistent_answer_is_rejected(activities):
    match=next(a for a in activities if a.type=="match")
    assert validate_activity(replace(match,answer={"left_to_right": [0,0,0,0]}))


def test_matching_duplicate_symbol_is_rejected(activities):
    match=next(a for a in activities if a.type=="match")
    g=deepcopy(match.geometry);g["left_symbols"][0]=g["left_symbols"][1]
    assert validate_activity(replace(match,geometry=g))


def test_same_seed_reproduces_entire_game(halloween):
    from lafractale.story.plan import demo_specs
    for s in demo_specs(halloween):
        seed=stable_seed(halloween.book_id,s.id,88)
        assert generate(s,seed)==generate(s,seed)


def test_different_seed_changes_maze():
    s=ActivitySpec("a",4,"maze",(4,5),"scène",("moon",))
    assert generate(s,stable_seed("a","a",1)).geometry != generate(s,stable_seed("a","a",2)).geometry


def test_duplicate_ids_are_rejected(activities):
    assert any("Doublon id" in s for s in validate_collection([activities[0],replace(activities[1],id=activities[0].id)]))


def test_duplicate_seed_is_rejected(activities):
    assert any("Doublon seed" in s for s in validate_collection([activities[0],replace(activities[1],seed=activities[0].seed)]))


def test_duplicate_game_data_is_rejected(activities):
    x=replace(activities[0],id="independent-id",page=999,seed=1234,scene="Autre scène")
    assert any("Données de jeux dupliquées" in s for s in validate_collection([activities[0],x]))


def test_same_mechanic_consecutive_rejected(activities):
    x=replace(activities[0],id="new",page=123,seed=456,scene="Nouvelle scène")
    assert any("Mécanique répétée" in s for s in validate_collection([activities[0],x]))


def test_all_halloween_demo_games_pass(activities):
    assert validate_collection(activities)==[]
