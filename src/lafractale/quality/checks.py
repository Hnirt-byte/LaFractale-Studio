"""Fail-closed logical validation and non-duplication checks."""
from __future__ import annotations
from collections import Counter
from math import hypot
from typing import Iterable
from lafractale.activities.models import Activity, content_fingerprint
from lafractale.activities.engine import shortest_path, adjacent


def _cross(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _intersect(a, b, c, d):
    # Disallow intersections between strictly disjoint edges and touching non-neighbours.
    eps = 1e-10
    ab_c, ab_d, cd_a, cd_b = _cross(a,b,c), _cross(a,b,d), _cross(c,d,a), _cross(c,d,b)
    return (ab_c * ab_d < -eps and cd_a * cd_b < -eps)


def validate_activity(activity: Activity, *, moon_len: int = 12) -> list[str]:
    errors: list[str] = []
    geom, answer = activity.geometry, activity.answer
    if activity.type == "maze":
        n = geom.get("size")
        if not isinstance(n, int) or not 3 <= n <= 12:
            return [f"{activity.id}: maze.size invalide"]
        edges = geom.get("open_edges", [])
        seen: set[tuple[tuple[int, int], tuple[int, int]]] = set()
        for edge in edges:
            try:
                a, b = map(tuple, edge)
                if any(not all(isinstance(t, int) and 0 <= t < n for t in p) for p in (a,b)) or not adjacent(a,b):
                    raise ValueError("invalid edge")
                key = tuple(sorted((a,b)))
                if key in seen:
                    raise ValueError("duplicate edge")
                seen.add(key)
            except (ValueError, TypeError, IndexError) as exc:
                errors.append(f"{activity.id}: mur/ouverture invalide : {exc}")
        start, goal = geom.get("start"), geom.get("goal")
        if start != [0,0] or goal != [n-1,n-1]:
            errors.append(f"{activity.id}: départ/arrivée invalides")
        if not errors:
            path = shortest_path(n, edges)
            if not path:
                errors.append(f"{activity.id}: labyrinthe bloqué")
            elif answer.get("path") != path or answer.get("steps") != len(path) - 1:
                errors.append(f"{activity.id}: corrigé de labyrinthe incorrect")
    elif activity.type == "match":
        family=geom.get("family")
        valid={"hats": {"hat_circle", "hat_star", "hat_triangle", "hat_diamond"},
               "gifts": {"gift_circle", "gift_star", "gift_triangle", "gift_diamond"},
               "shapes": {"circle", "square", "triangle", "diamond", "star", "hexagon"}}
        if family not in valid or set(geom.get("left_symbols", [])) - valid.get(family,set()):
            errors.append(f"{activity.id}: famille de symboles inconnue")
        left, right, pairs = geom.get("left_symbols", []), geom.get("right_symbols", []), answer.get("left_to_right", [])
        if (len(left) != 4 or len(right) != 4 or len(set(left)) != 4 or
            Counter(left) != Counter(right) or len(pairs) != 4 or
            any(not isinstance(p, int) for p in pairs) or sorted(pairs) != list(range(4)) or
            any(left[i] != right[j] for i, j in enumerate(pairs))):
            errors.append(f"{activity.id}: association non bijective ou solution incorrecte")
        if left == right:
            errors.append(f"{activity.id}: association triviale non mélangée")
    elif activity.type == "connect_dots":
        pts = geom.get("points", [])
        shape = geom.get("shape")
        if shape not in {"moon", "house", "star"}:
            return [f"{activity.id}: forme inconnue"]
        if shape == "moon" and len(pts) != moon_len:
            errors.append(f"{activity.id}: lune incomplète ({moon_len} points requis)")
        if len(pts) < 7 or [p.get("n") for p in pts] != list(range(1, len(pts) + 1)):
            errors.append(f"{activity.id}: numérotation non bijective 1..N")
        if not geom.get("closed") or answer.get("close_to") != 1 or answer.get("order") != list(range(1, len(pts) + 1)):
            errors.append(f"{activity.id}: contour non fermé/corrigé faux")
        coords = [(p.get("x"), p.get("y")) for p in pts]
        if all(isinstance(v, (int,float)) and 0 <= v <= 1 for point in coords for v in point) and len(pts) >= 7:
            if len(set(coords)) != len(coords):
                errors.append(f"{activity.id}: points confondus")
            ring = coords + coords[:1]
            if min(hypot(b[0] - a[0], b[1] - a[1]) for a,b in zip(ring,ring[1:])) < .035:
                errors.append(f"{activity.id}: segments trop courts")
            for i in range(len(pts)):
                for j in range(i + 2, len(pts)):
                    if i == 0 and j == len(pts) - 1:
                        continue
                    if _intersect(ring[i], ring[i+1], ring[j], ring[j+1]):
                        errors.append(f"{activity.id}: contour auto-croisé")
            area = abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(ring,ring[1:]))) / 2
            if area < .08 or max(x for x,y in coords) - min(x for x,y in coords) < .4 or max(y for x,y in coords) - min(y for x,y in coords) < .6:
                errors.append(f"{activity.id}: silhouette incomplète")
            if shape == "moon":
                # Both outer and inner sides must be present and meaningfully concave.
                signs = [_cross(ring[i],ring[i+1],ring[i+2]) for i in range(len(pts)-1)]
                if not (any(s > .005 for s in signs) and any(s < -.005 for s in signs)):
                    errors.append(f"{activity.id}: lune sans bord intérieur concave")
        else:
            errors.append(f"{activity.id}: coordonnées non valides")
    else:
        errors.append(f"{activity.id}: type non pris en charge : {activity.type}")
    return errors


def validate_collection(activities: Iterable[Activity], *, moon_len: int = 12) -> list[str]:
    items = list(activities)
    errors = []
    for attribute in ("id", "page", "seed"):
        values = [getattr(item, attribute) for item in items]
        if len(values) != len(set(values)):
            errors.append(f"Doublon {attribute}")
    hashes = [content_fingerprint(item) for item in items]
    if len(set(hashes)) != len(hashes):
        errors.append("Données de jeux dupliquées")
    for a,b in zip(items,items[1:]):
        if a.type == b.type:
            errors.append(f"Mécanique répétée consécutivement : {a.id}/{b.id}")
        if a.scene == b.scene:
            errors.append(f"Scène répétée consécutivement : {a.id}/{b.id}")
    for item in items:
        errors.extend(validate_activity(item, moon_len=moon_len))
    return errors
