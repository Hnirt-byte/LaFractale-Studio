"""Independent verification of the solution of a generated activity.

The checks below re-analyse the *structure actually produced* (edges, points,
symbols). They never trust generator metadata: the expected solution is
recomputed here and compared with ``activity.answer``.
"""
from __future__ import annotations

from collections import deque
from math import hypot
from typing import Any

from lafractale.activities.engine import SHAPES
from lafractale.activities.models import Activity
from lafractale.quality.checks import validate_activity

MAZE_MIN, MAZE_MAX = 3, 12
MIN_SEGMENT = 0.035


def _is_int(value: Any) -> bool:
    return type(value) is int


def _is_number(value: Any) -> bool:
    return type(value) in (int, float)


def _cell(value: Any, size: int) -> tuple[int, int] | None:
    if (isinstance(value, (list, tuple)) and len(value) == 2
            and all(_is_int(v) and 0 <= v < size for v in value)):
        return (value[0], value[1])
    return None


def maze_unique_path(size: int, open_edges: Any) -> tuple[list[tuple[int, int]] | None, list[str]]:
    """Return the unique start->goal path of a maze, or the reasons it is not unique.

    Proof of uniqueness: a connected graph on n*n cells with exactly n*n-1
    undirected edges is a spanning tree, and a tree has one simple path between
    two vertices. Edge count and connectivity are measured on the real data.
    """
    errors: list[str] = []
    if not isinstance(open_edges, (list, tuple)):
        return None, ["open_edges : liste attendue"]
    neighbours: dict[tuple[int, int], set[tuple[int, int]]] = {}
    seen: set[frozenset] = set()
    for index, edge in enumerate(open_edges):
        if not isinstance(edge, (list, tuple)) or len(edge) != 2:
            errors.append(f"arête {index} : paire de cellules attendue")
            continue
        a, b = _cell(edge[0], size), _cell(edge[1], size)
        if a is None or b is None:
            errors.append(f"arête {index} : cellule hors grille ou non entière")
            continue
        if abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1:
            errors.append(f"arête {index} : cellules non adjacentes")
            continue
        key = frozenset((a, b))
        if key in seen:
            errors.append(f"arête {index} : doublon")
            continue
        seen.add(key)
        neighbours.setdefault(a, set()).add(b)
        neighbours.setdefault(b, set()).add(a)
    if errors:
        return None, errors
    cells = size * size
    if len(seen) != cells - 1:
        kind = "cycle (plusieurs solutions possibles)" if len(seen) >= cells else "cellules non reliées"
        return None, [f"{len(seen)} passages pour {cells} cellules (arbre couvrant : {cells - 1} attendus) : {kind}"]
    start, goal = (0, 0), (size - 1, size - 1)
    parent: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for nxt in sorted(neighbours.get(node, ())):
            if nxt not in parent:
                parent[nxt] = node
                queue.append(nxt)
    if len(parent) != cells:
        return None, [f"{cells - len(parent)} cellule(s) inaccessible(s) depuis le départ"]
    path: list[tuple[int, int]] = []
    node: tuple[int, int] | None = goal
    while node is not None:
        path.append(node)
        node = parent[node]
    return path[::-1], []


def verify_maze(activity: Activity) -> list[str]:
    geometry, answer = activity.geometry, activity.answer
    size = geometry.get("size")
    if not _is_int(size) or not MAZE_MIN <= size <= MAZE_MAX:
        return [f"{activity.id}: taille de labyrinthe invalide"]
    errors: list[str] = []
    if geometry.get("start") != [0, 0] or geometry.get("goal") != [size - 1, size - 1]:
        errors.append(f"{activity.id}: départ/arrivée invalides")
    path, reasons = maze_unique_path(size, geometry.get("open_edges"))
    errors.extend(f"{activity.id}: labyrinthe — {reason}" for reason in reasons)
    if path is None:
        return errors
    if set(answer) != {"path", "steps"}:
        return errors + [f"{activity.id}: corrigé de labyrinthe mal formé"]
    given = answer.get("path")
    if not isinstance(given, (list, tuple)) or [list(p) if isinstance(p, tuple) else p for p in given] != [list(p) for p in path]:
        errors.append(f"{activity.id}: corrigé de labyrinthe différent du chemin unique recalculé")
    if answer.get("steps") != len(path) - 1 or not _is_int(answer.get("steps")):
        errors.append(f"{activity.id}: nombre de pas du corrigé incorrect")
    return errors


def _orient(a, b, c) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _on_segment(a, b, c) -> bool:
    return (min(a[0], b[0]) - 1e-12 <= c[0] <= max(a[0], b[0]) + 1e-12
            and min(a[1], b[1]) - 1e-12 <= c[1] <= max(a[1], b[1]) + 1e-12)


def segments_touch(a, b, c, d, eps: float = 1e-12) -> bool:
    """True if closed segments ab and cd share at least one point."""
    o1, o2, o3, o4 = _orient(a, b, c), _orient(a, b, d), _orient(c, d, a), _orient(c, d, b)
    if o1 * o2 < -eps and o3 * o4 < -eps:
        return True
    return ((abs(o1) <= eps and _on_segment(a, b, c)) or (abs(o2) <= eps and _on_segment(a, b, d))
            or (abs(o3) <= eps and _on_segment(c, d, a)) or (abs(o4) <= eps and _on_segment(c, d, b)))


def verify_connect_dots(activity: Activity) -> list[str]:
    geometry, answer = activity.geometry, activity.answer
    shape = geometry.get("shape")
    if shape not in SHAPES:
        return [f"{activity.id}: forme inconnue"]
    points = geometry.get("points")
    if not isinstance(points, (list, tuple)) or len(points) != len(SHAPES[shape]):
        return [f"{activity.id}: {len(SHAPES[shape])} points attendus pour la forme {shape}"]
    errors: list[str] = []
    coords: list[tuple[float, float]] = []
    for index, point in enumerate(points, start=1):
        if (not isinstance(point, dict) or set(point) != {"n", "x", "y"} or point["n"] != index
                or not _is_int(point["n"]) or not all(_is_number(point[k]) and 0 <= point[k] <= 1 for k in "xy")):
            return [f"{activity.id}: point {index} mal formé ou numérotation non continue 1..N"]
        coords.append((float(point["x"]), float(point["y"])))
    count = len(coords)
    if len(set(coords)) != count:
        errors.append(f"{activity.id}: points confondus")
    if geometry.get("closed") is not True:
        errors.append(f"{activity.id}: contour non déclaré fermé")
    if set(answer) != {"order", "close_to"} or answer.get("order") != list(range(1, count + 1)) or answer.get("close_to") != 1:
        errors.append(f"{activity.id}: corrigé des points différent de 1..N puis retour à 1")
    ring = coords + coords[:1]
    segments = list(zip(ring, ring[1:]))
    for i, (a, b) in enumerate(segments):
        if hypot(b[0] - a[0], b[1] - a[1]) < MIN_SEGMENT:
            errors.append(f"{activity.id}: segment {i + 1} trop court")
    for i in range(count):
        for j in range(i + 1, count):
            adjacent = j == i + 1 or (i == 0 and j == count - 1)
            if adjacent:
                continue
            if segments_touch(*segments[i], *segments[j]):
                errors.append(f"{activity.id}: segments {i + 1} et {j + 1} se croisent ou se touchent")
    area = abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in segments)) / 2
    if area <= 0:
        errors.append(f"{activity.id}: contour d'aire nulle")
    return errors


def verify_match(activity: Activity) -> list[str]:
    geometry, answer = activity.geometry, activity.answer
    left, right = geometry.get("left_symbols"), geometry.get("right_symbols")
    pairs = answer.get("left_to_right") if set(answer) == {"left_to_right"} else None
    if (not isinstance(left, list) or not isinstance(right, list) or not left or len(left) != len(right)
            or not all(isinstance(s, str) for s in left + right)):
        return [f"{activity.id}: colonnes de symboles invalides"]
    errors: list[str] = []
    if len(set(left)) != len(left) or len(set(right)) != len(right):
        errors.append(f"{activity.id}: symboles répétés (solution non unique)")
    if sorted(left) != sorted(right):
        errors.append(f"{activity.id}: les deux colonnes ne contiennent pas les mêmes symboles")
    if left == right:
        errors.append(f"{activity.id}: association triviale (colonnes identiques)")
    count = len(left)
    if (not isinstance(pairs, list) or len(pairs) != count or not all(_is_int(p) for p in pairs)
            or sorted(pairs) != list(range(count))):
        return errors + [f"{activity.id}: corrigé d'association non bijectif"]
    expected = [right.index(symbol) if symbol in right else -1 for symbol in left]
    if pairs != expected:
        errors.append(f"{activity.id}: corrigé d'association différent des paires recalculées")
    return errors


def verify_with_existing_rules(activity: Activity, solver) -> list[str]:
    """Independent solver first, then the repository's own historical validator."""
    return solver(activity) + validate_activity(activity)
