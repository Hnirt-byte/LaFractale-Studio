"""maze_v2 — perfect mazes of size 3..12 with three explicit, measurable difficulty levels.

Specification (all integer arithmetic, N = size, cells on the grid are N×N):

* The maze is a spanning tree of the grid (N²−1 passages): the start→goal path is unique.
* ``L`` = number of steps of that path. It is always even (the grid is bipartite and start/goal
  are opposite corners); its minimum is ``Lmin = 2(N−1)``. The excess ``E = L − Lmin`` is compared
  with ``span = (N−1)²`` (the largest possible excess, ``N²−1 − Lmin``).
* ``D`` = dead ends (cells with a single passage, start and goal excluded).
* ``B`` = branch points on the solution path (path cells offering at least one passage that
  leaves the path), i.e. the places where a wrong turn exists.

====== =============================== ==========================================
level  excess band                      branch constraints
====== =============================== ==========================================
easy   4·E ≤ span                       B ≤ N
medium 4·E > span and 2·E ≤ span        B ≥ N // 2
hard   2·E > span                       B ≥ (N−3) // 2 and D ≥ (N−3) // 2
====== =============================== ==========================================

The levels are technical parameters. They are NOT a pedagogical judgement: no human review of
age suitability has been done.

Generation is a bounded deterministic search: attempt ``i`` (0 ≤ i < MAX_ATTEMPTS) derives its
own stream from (activity_id, seed, size, difficulty, i) and uses one of three tree algorithms in
rotation. The first maze that satisfies the level is returned; if none does, ``V2Error``
``UNSATISFIABLE`` is raised. Constraints are never relaxed.
"""
from __future__ import annotations

from collections import deque
from typing import Any, Mapping

from lafractale.mechanics_v2.core import (
    DetRng, V2Activity, V2Error, build_activity, check_activity_id, check_params, check_seed,
    bounded_repr,
)

MAZE_V2_MECHANIC = "maze_v2"
MAZE_V2_VERSION = "b3b3b1-maze-v2-1.0"
SIZE_MIN, SIZE_MAX = 3, 12
DIFFICULTIES = ("easy", "medium", "hard")
ALGORITHMS = ("backtracker", "kruskal", "prim")
MAX_ATTEMPTS = 5000

Cell = tuple[int, int]
Edge = tuple[Cell, Cell]


# ---- specification of the levels (shared, pure) ----------------------------------------------
def minimum_path(size: int) -> int:
    return 2 * (size - 1)


def span(size: int) -> int:
    return (size - 1) ** 2


def band(size: int, path_length: int) -> str:
    excess, total = path_length - minimum_path(size), span(size)
    if 4 * excess <= total:
        return "easy"
    return "medium" if 2 * excess <= total else "hard"


def meets(size: int, level: str, path_length: int, dead_ends: int, decisions: int) -> bool:
    """True when the measured maze satisfies EVERY constraint of ``level``."""
    if band(size, path_length) != level:
        return False
    if level == "easy":
        return decisions <= size
    if level == "medium":
        return decisions >= size // 2
    floor = (size - 3) // 2
    return decisions >= floor and dead_ends >= floor


# ---- parameters -------------------------------------------------------------------------------
def _size(value: Any) -> int:
    if type(value) is not int or not SIZE_MIN <= value <= SIZE_MAX:
        raise V2Error("BAD_SIZE", f"taille entière attendue entre {SIZE_MIN} et {SIZE_MAX} inclus, reçu {bounded_repr(value)}")
    return value


def _difficulty(value: Any) -> str:
    if type(value) is not str or value not in DIFFICULTIES:
        raise V2Error("BAD_DIFFICULTY", f"difficulté attendue parmi {DIFFICULTIES}, reçu {bounded_repr(value)}")
    return value


PARAM_SPEC = {"size": _size, "difficulty": _difficulty}


# ---- spanning-tree algorithms ------------------------------------------------------------------
def _neighbours(size: int, cell: Cell) -> list[Cell]:
    x, y = cell
    return [(a, b) for a, b in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)) if 0 <= a < size and 0 <= b < size]


def _backtracker(size: int, rng: DetRng) -> list[Edge]:
    seen, stack, edges = {(0, 0)}, [(0, 0)], []
    while stack:
        current = stack[-1]
        options = [c for c in _neighbours(size, current) if c not in seen]
        if not options:
            stack.pop()
            continue
        nxt = rng.choice(options)
        edges.append((current, nxt))
        seen.add(nxt)
        stack.append(nxt)
    return edges


def _kruskal(size: int, rng: DetRng) -> list[Edge]:
    parent = {(x, y): (x, y) for x in range(size) for y in range(size)}

    def find(cell: Cell) -> Cell:
        while parent[cell] != cell:
            parent[cell] = parent[parent[cell]]
            cell = parent[cell]
        return cell

    candidates: list[Edge] = [((x, y), (x + 1, y)) for y in range(size) for x in range(size - 1)]
    candidates += [((x, y), (x, y + 1)) for y in range(size - 1) for x in range(size)]
    rng.shuffle(candidates)
    edges = []
    for a, b in candidates:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
            edges.append((a, b))
    return edges


def _prim(size: int, rng: DetRng) -> list[Edge]:
    seen, frontier, edges = {(0, 0)}, [((0, 0), c) for c in _neighbours(size, (0, 0))], []
    while frontier:
        index = rng.below(len(frontier))
        frontier[index], frontier[-1] = frontier[-1], frontier[index]
        a, b = frontier.pop()
        if b in seen:
            continue
        seen.add(b)
        edges.append((a, b))
        frontier.extend((b, c) for c in _neighbours(size, b) if c not in seen)
    return edges


_BUILDERS = {"backtracker": _backtracker, "kruskal": _kruskal, "prim": _prim}


def _normalise(edges: list[Edge]) -> list[Edge]:
    return sorted((min(a, b), max(a, b)) for a, b in edges)


def _analyse(size: int, edges: list[Edge]) -> tuple[list[Cell], int, int]:
    """(path start→goal, dead ends, branch points on the path) of a spanning tree."""
    graph: dict[Cell, list[Cell]] = {}
    for a, b in edges:
        graph.setdefault(a, []).append(b)
        graph.setdefault(b, []).append(a)
    start, goal = (0, 0), (size - 1, size - 1)
    parent: dict[Cell, Cell | None] = {start: None}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for nxt in sorted(graph[node]):
            if nxt not in parent:
                parent[nxt] = node
                queue.append(nxt)
    path: list[Cell] = []
    node: Cell | None = goal
    while node is not None:
        path.append(node)
        node = parent[node]
    path.reverse()
    ends = (start, goal)
    dead_ends = sum(1 for cell, links in graph.items() if len(links) == 1 and cell not in ends)
    decisions = sum(1 for cell in path if len(graph[cell]) > (1 if cell in ends else 2))
    return path, dead_ends, decisions


# ---- generation ----------------------------------------------------------------------------------
def generate_maze_v2(activity_id: Any, seed: Any, params: Mapping[str, Any]) -> V2Activity:
    """Deterministic bounded search; raises ``V2Error`` (never relaxes a constraint)."""
    activity_id, seed = check_activity_id(activity_id), check_seed(seed)
    values = check_params(params, PARAM_SPEC)
    size, level = values["size"], values["difficulty"]
    for attempt in range(MAX_ATTEMPTS):
        algorithm = ALGORITHMS[attempt % len(ALGORITHMS)]
        rng = DetRng(f"lafractale-mechanics-v2|{MAZE_V2_MECHANIC}|{activity_id}|{seed}|{size}|{level}|{attempt}")
        edges = _normalise(_BUILDERS[algorithm](size, rng))
        path, dead_ends, decisions = _analyse(size, edges)
        steps = len(path) - 1
        if meets(size, level, steps, dead_ends, decisions):
            return build_activity(
                mechanic=MAZE_V2_MECHANIC, version=MAZE_V2_VERSION, activity_id=activity_id, seed=seed,
                params={"size": size, "difficulty": level},
                geometry={"size": size, "start": [0, 0], "goal": [size - 1, size - 1],
                          "open_edges": [[list(a), list(b)] for a, b in edges]},
                solution={"path": [list(c) for c in path], "steps": steps},
                measures={"path_length": steps, "dead_ends": dead_ends, "decisions": decisions,
                          "minimum_path_length": minimum_path(size), "span": span(size)},
                search={"algorithm": algorithm, "attempts": attempt + 1, "max_attempts": MAX_ATTEMPTS})
    raise V2Error("UNSATISFIABLE",
                  f"aucun labyrinthe {level} de taille {size} trouvé en {MAX_ATTEMPTS} tentatives déterministes "
                  "(contraintes inchangées, aucune dégradation)")
