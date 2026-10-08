"""Three deterministic generators, with fully structured and checkable answers."""
from __future__ import annotations

from collections import deque
import hashlib
import math
import random
from typing import Any

from .models import Activity, ActivitySpec

SUPPORTED = {"maze", "match", "connect_dots"}


def stable_seed(book_id: str, activity_id: str, seed: int) -> int:
    digest = hashlib.sha256(f"lafractale-v0.1|{book_id}|{activity_id}|{seed}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def adjacent(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1


def shortest_path(size: int, edges: list[list[list[int]]], start=(0, 0), end=None) -> list[list[int]]:
    if end is None:
        end = (size - 1, size - 1)
    graph: dict[tuple[int, int], set[tuple[int, int]]] = {}
    for a, b in edges:
        u, v = tuple(a), tuple(b)
        if not adjacent(u, v):
            return []
        graph.setdefault(u, set()).add(v)
        graph.setdefault(v, set()).add(u)
    queue = deque([start])
    previous: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    while queue:
        u = queue.popleft()
        if u == end:
            result = []
            while u is not None:
                result.append(list(u))
                u = previous[u]
            return result[::-1]
        for v in sorted(graph.get(u, set())):
            if v not in previous:
                previous[v] = u
                queue.append(v)
    return []


def generate_maze(rng: random.Random) -> tuple[dict[str, Any], dict[str, Any]]:
    size = 5
    visited = {(0, 0)}
    stack = [(0, 0)]
    openings: list[list[list[int]]] = []
    while stack:
        x, y = stack[-1]
        choices = [(nx, ny) for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))
                   if 0 <= nx < size and 0 <= ny < size and (nx, ny) not in visited]
        if not choices:
            stack.pop()
            continue
        next_cell = rng.choice(choices)
        openings.append([list((x, y)), list(next_cell)])
        visited.add(next_cell)
        stack.append(next_cell)
    openings.sort(key=lambda e: sorted(e))
    solution = shortest_path(size, openings)
    return ({"size": size, "open_edges": openings, "start": [0, 0], "goal": [size - 1, size - 1]},
            {"path": solution, "steps": len(solution) - 1})


SYMBOLS = ("circle", "square", "triangle", "diamond", "star", "hexagon")


def generate_match(rng: random.Random, family: str = "shapes") -> tuple[dict[str, Any], dict[str, Any]]:
    if family == "hats":
        symbols = rng.sample(("hat_circle", "hat_star", "hat_triangle", "hat_diamond"), 4)
    elif family == "gifts":
        symbols = rng.sample(("gift_circle", "gift_star", "gift_triangle", "gift_diamond"), 4)
    else:
        symbols = rng.sample(SYMBOLS, 4)
    rights = symbols[:]
    # Avoid a trivial all-straight exercise.
    while rights == symbols:
        rng.shuffle(rights)
    positions = [rights.index(symbol) for symbol in symbols]
    return ({"family": family, "left_symbols": symbols, "right_symbols": rights}, {"left_to_right": positions})


# Entire moon contour: outer curved back from top to bottom, inner curved edge
# from bottom tip to top tip; the closing segment completes the silhouette.
MOON_12 = (
    (.71, .91), (.47, .93), (.26, .80), (.14, .63),
    (.10, .45), (.16, .28), (.32, .13), (.54, .09),
    (.72, .15), (.58, .32), (.55, .53), (.61, .75),
)
HOUSE = ((.14, .44), (.5, .88), (.86, .44), (.76, .44), (.76, .14), (.24, .14), (.24, .44))
STAR = tuple((.5 + (0.42 if i % 2 == 0 else .21) * math.sin(i * math.pi / 5),
              .5 + (0.42 if i % 2 == 0 else .21) * math.cos(i * math.pi / 5)) for i in range(10))
SHAPES = {"moon": MOON_12, "house": HOUSE, "star": STAR}


def generate_connect(rng: random.Random, shape: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if shape not in SHAPES:
        raise ValueError(f"Forme de points à relier non implémentée : {shape}")
    angle = rng.uniform(-0.07, 0.07)
    scale = rng.uniform(.92, 1)
    cx, cy = .5, .5
    coords = []
    for x, y in SHAPES[shape]:
        dx, dy = (x - cx) * scale, (y - cy) * scale
        rx = cx + dx * math.cos(angle) - dy * math.sin(angle)
        ry = cy + dx * math.sin(angle) + dy * math.cos(angle)
        coords.append({"n": len(coords) + 1, "x": round(rx, 6), "y": round(ry, 6)})
    return ({"shape": shape, "points": coords, "closed": True},
            {"order": list(range(1, len(coords) + 1)), "close_to": 1})


def generate(spec: ActivitySpec, seed: int) -> Activity:
    """Same spec+seed+engine version => same data; no image dependency."""
    if spec.type not in SUPPORTED:
        raise ValueError(f"Mécanique non implémentée en V0.1 : {spec.type}")
    rng = random.Random(seed)
    if spec.type == "maze":
        geometry, answer = generate_maze(rng)
        fr, en = "Aide Pip à traverser le labyrinthe !", "Help Pip find the way!"
    elif spec.type == "match":
        vocab = {w.casefold() for w in spec.vocabulary}
        family = "hats" if vocab.intersection({"hat", "chapeau"}) else "gifts" if vocab.intersection({"gift", "cadeau"}) else "shapes"
        geometry, answer = generate_match(rng, family)
        labels = {"hats": ("Relie chaque chapeau à son jumeau.", "Match each hat to its twin."),
                  "gifts": ("Relie chaque cadeau à son jumeau.", "Match each gift to its twin."),
                  "shapes": ("Relie chaque forme à sa jumelle.", "Match each shape to its twin.")}
        fr, en = labels[family]
    else:
        geometry, answer = generate_connect(rng, spec.shape)
        fr, en = "Relie les points dans l'ordre, puis reviens au 1.", "Connect the dots in order, then return to 1."
    return Activity(spec.id, spec.page, spec.type, spec.age_band, spec.scene, spec.vocabulary,
                    fr, en, spec.asset_refs, geometry, answer, seed, spec.pedagogy,
                    spec.difficulty, spec.pip_pose)
