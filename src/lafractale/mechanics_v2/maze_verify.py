"""Independent verification of a maze_v2 record (plain dict or ``V2Activity``).

Nothing here calls the generator: the tree property, the unique path, the measures, the level
and the fingerprint are all recomputed from the passages alone, with different algorithms
(union-find for the tree, iterative depth-first search for the path), and the historical
``maze_unique_path`` is used as a second, pre-existing opinion.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from lafractale.engine.solvers import maze_unique_path
from lafractale.mechanics_v2 import HUMAN_PEDAGOGICAL_VALIDATION, V2_KIND, V2_SCHEMA
from lafractale.mechanics_v2.core import ACTIVITY_ID, V2Activity, V2Error, record_fingerprint
from lafractale.mechanics_v2.maze import (
    DIFFICULTIES, MAX_ATTEMPTS, MAZE_V2_MECHANIC, MAZE_V2_VERSION, SIZE_MAX, SIZE_MIN, meets, minimum_path, span,
)

_BODY_KEYS = {"schema", "kind", "mechanic", "version", "activity_id", "seed", "human_pedagogical_validation",
              "production_authorized", "params", "geometry", "solution", "measures", "search", "fingerprint"}


def _int(value: Any) -> bool:
    return type(value) is int


def _cell(value: Any, size: int) -> tuple[int, int] | None:
    if isinstance(value, list) and len(value) == 2 and all(_int(v) and 0 <= v < size for v in value):
        return (value[0], value[1])
    return None


def verify_maze_v2(record: Mapping[str, Any] | V2Activity) -> list[str]:
    """List of problems; empty means the record is a valid, correctly measured maze_v2."""
    data = record.to_dict() if isinstance(record, V2Activity) else record
    if not isinstance(data, Mapping):
        return ["enregistrement : mapping attendu"]
    errors: list[str] = []
    if set(data) != _BODY_KEYS:
        return [f"clés de l'enregistrement : attendu {sorted(_BODY_KEYS)}, reçu {sorted(map(str, data))}"]
    for key, expected in (("schema", V2_SCHEMA), ("kind", V2_KIND), ("mechanic", MAZE_V2_MECHANIC),
                          ("version", MAZE_V2_VERSION), ("human_pedagogical_validation", HUMAN_PEDAGOGICAL_VALIDATION)):
        if data[key] != expected:
            errors.append(f"{key} : {expected!r} attendu, reçu {data[key]!r}")
    if data["production_authorized"] is not False:
        errors.append("production_authorized doit valoir false")
    if not isinstance(data["activity_id"], str) or not ACTIVITY_ID.match(data["activity_id"]):
        errors.append("activity_id : identifiant synthétique « syn-… » requis")
    if not _int(data["seed"]) or data["seed"] < 0:
        errors.append("seed : entier positif ou nul requis")
    params, geometry, solution, measures, search = (data[k] for k in ("params", "geometry", "solution", "measures", "search"))
    if not all(isinstance(v, Mapping) for v in (params, geometry, solution, measures, search)):
        return errors + ["params/geometry/solution/measures/search : mappings attendus"]
    if set(params) != {"size", "difficulty"}:
        return errors + ["params : exactement size et difficulty"]
    size, level = params["size"], params["difficulty"]
    if not _int(size) or not SIZE_MIN <= size <= SIZE_MAX:
        return errors + [f"params.size : entier entre {SIZE_MIN} et {SIZE_MAX}"]
    if level not in DIFFICULTIES:
        return errors + [f"params.difficulty : parmi {DIFFICULTIES}"]
    if geometry.get("size") != size or geometry.get("start") != [0, 0] or geometry.get("goal") != [size - 1, size - 1] \
            or set(geometry) != {"size", "start", "goal", "open_edges"}:
        errors.append("geometry : taille, départ (0,0) et arrivée (n-1,n-1) incohérents avec params")

    # -- passages: canonical, in-grid, adjacent, unique ------------------------------------------
    raw = geometry.get("open_edges")
    if not isinstance(raw, list):
        return errors + ["geometry.open_edges : liste attendue"]
    edges: list[tuple[tuple[int, int], tuple[int, int]]] = []
    for index, item in enumerate(raw):
        a = _cell(item[0], size) if isinstance(item, list) and len(item) == 2 else None
        b = _cell(item[1], size) if isinstance(item, list) and len(item) == 2 else None
        if a is None or b is None or abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1:
            errors.append(f"passage {index} : deux cellules adjacentes de la grille attendues")
        elif a > b:
            errors.append(f"passage {index} : forme canonique (plus petite cellule d'abord) non respectée")
        else:
            edges.append((a, b))
    if errors:
        return errors
    if edges != sorted(edges) or len(set(edges)) != len(edges):
        return errors + ["geometry.open_edges : passages triés et sans doublon requis"]

    # -- spanning tree (union-find): N²-1 passages, no cycle, connected ------------------------------
    cells = size * size
    parent = {(x, y): (x, y) for x in range(size) for y in range(size)}

    def find(cell):
        while parent[cell] != cell:
            parent[cell] = parent[parent[cell]]
            cell = parent[cell]
        return cell

    cycles = 0
    for a, b in edges:
        ra, rb = find(a), find(b)
        cycles += ra == rb
        parent[ra] = rb
    if len(edges) != cells - 1 or cycles or len({find(c) for c in parent}) != 1:
        return errors + [f"labyrinthe : arbre couvrant requis ({len(edges)} passages, {cycles} cycle(s), "
                         f"{len({find(c) for c in parent})} composante(s) ; {cells - 1} passages attendus)"]

    # -- unique path by iterative DFS, then the historical solver as a second opinion -------------------
    graph: dict[tuple[int, int], list[tuple[int, int]]] = {c: [] for c in parent}
    for a, b in edges:
        graph[a].append(b)
        graph[b].append(a)
    start, goal = (0, 0), (size - 1, size - 1)
    came: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    stack = [start]
    while stack:
        node = stack.pop()
        for nxt in graph[node]:
            if nxt not in came:
                came[nxt] = node
                stack.append(nxt)
    path = []
    node = goal
    while node is not None:
        path.append(node)
        node = came[node]
    path.reverse()
    historical, reasons = maze_unique_path(size, [[list(a), list(b)] for a, b in edges])
    if reasons or historical != path:
        errors.append(f"chemin unique : désaccord avec la vérification historique ({reasons or 'chemins différents'})")
    if set(solution) != {"path", "steps"} or solution.get("path") != [list(c) for c in path] or solution.get("steps") != len(path) - 1:
        errors.append("solution : chemin ou nombre de pas différent du chemin unique recalculé")

    # -- measures and level, from scratch ------------------------------------------------------------------
    ends = (start, goal)
    dead_ends = sum(1 for c, links in graph.items() if len(links) == 1 and c not in ends)
    decisions = sum(1 for c in path if len(graph[c]) > (1 if c in ends else 2))
    steps = len(path) - 1
    expected = {"path_length": steps, "dead_ends": dead_ends, "decisions": decisions,
                "minimum_path_length": minimum_path(size), "span": span(size)}
    if dict(measures) != expected:
        errors.append(f"measures : valeurs recalculées {expected}, reçues {dict(measures)}")
    if not meets(size, level, steps, dead_ends, decisions):
        errors.append(f"difficulté : le labyrinthe ne satisfait pas toutes les contraintes du niveau {level} "
                      f"(L={steps}, D={dead_ends}, B={decisions})")
    if set(search) != {"algorithm", "attempts", "max_attempts"} or search.get("max_attempts") != MAX_ATTEMPTS \
            or not _int(search.get("attempts")) or not 1 <= search["attempts"] <= MAX_ATTEMPTS:
        errors.append("search : algorithm, attempts (1..max) et max_attempts requis")
    try:
        if record_fingerprint(data) != data["fingerprint"]:
            errors.append("fingerprint : ne correspond pas au contenu canonique")
    except (V2Error, ValueError, TypeError) as exc:
        errors.append(f"fingerprint : contenu non canonique ({exc})")
    return errors
