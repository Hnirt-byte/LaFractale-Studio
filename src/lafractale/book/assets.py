"""Manifeste d'assets graphiques, import de PNG et chargement des images.

Une image ne porte jamais de règle : elle habille (decorative) ou donne leur apparence à des objets que Python
place et compte lui-même (exercise). Une image absente est signalée ASSET_MANQUANT, jamais remplacée par un faux.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from PIL import Image

from lafractale.book.pages import BookError

KINDS = ("object", "scene")
ROLES = ("decorative", "exercise")
MISSING = "ASSET_MANQUANT"


@dataclass(frozen=True)
class Asset:
    id: str
    kind: str
    role: str
    path: Path
    prompt: str = ""
    size_px: tuple[int, int] | None = None
    min_px: int = 0
    fixed: bool = False


@dataclass
class Manifest:
    style_prompt: str
    assets: dict[str, Asset]
    pages: dict[int, dict]
    lock_path: Path
    root: Path


def load_manifest(path: Path, repo_root: Path) -> Manifest:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    base = repo_root / data["assets_dir"]
    assets: dict[str, Asset] = {}
    for a in data["assets"]:
        if a["id"] in assets:
            raise BookError(f"manifeste : asset en double {a['id']}")
        if a["kind"] not in KINDS or a["role"] not in ROLES:
            raise BookError(f"manifeste : kind/role invalide pour {a['id']}")
        assets[a["id"]] = Asset(a["id"], a["kind"], a["role"],
                                repo_root / a["file"] if a.get("file") else base / f"{a['id']}.png",
                                a.get("prompt", ""), tuple(a["size_px"]) if a.get("size_px") else None,
                                a.get("min_px", 0), bool(a.get("fixed")))
    pages = {int(k): v for k, v in (data.get("pages") or {}).items()}
    for page, plan in pages.items():
        for d in plan.get("decor", []):
            if d["asset"] not in assets:
                raise BookError(f"manifeste : page {page} cite l'asset inconnu {d['asset']}")
    return Manifest(data["style_prompt"].strip(), assets, pages,
                    Path(path).with_name("assets_lock.json"), repo_root)


def _normalize(img: Image.Image, kind: str) -> Image.Image:
    """object -> RGBA (alpha dérivé du trait si le PNG n'est pas transparent) ; scene -> gris sur fond blanc."""
    if kind == "scene":
        if img.mode in ("RGBA", "LA"):
            bg = Image.new("RGBA", img.size, "white")
            bg.alpha_composite(img.convert("RGBA"))
            img = bg
        return img.convert("L")
    rgba = img.convert("RGBA")
    alpha = rgba.getchannel("A")
    if alpha.getextrema()[0] == 255:  # aucun pixel transparent : dessin au trait sur fond blanc
        dark = img.convert("L").point(lambda v: 255 - v)
        rgba = Image.merge("RGBA", (*(Image.new("L", img.size, 0),) * 3, dark))
    box = rgba.getchannel("A").getbbox()
    if box is None:
        raise BookError("image entièrement vide")
    pad = max(2, round(max(img.size) * .01))
    box = (max(0, box[0] - pad), max(0, box[1] - pad), min(img.width, box[2] + pad), min(img.height, box[3] + pad))
    return rgba.crop(box)


class AssetStore:
    """Charge les images à la demande et consigne les anomalies pour le rapport."""

    def __init__(self, manifest: Manifest) -> None:
        self.manifest = manifest
        self._cache: dict[str, Image.Image | None] = {}
        self.issues: list[dict] = []

    def get(self, asset_id: str, page: int) -> Image.Image | None:
        asset = self.manifest.assets[asset_id]
        if asset_id not in self._cache:
            self._cache[asset_id] = self._load(asset)
        img = self._cache[asset_id]
        if img is None:
            self._issue(page, asset, MISSING)
        return img

    def _load(self, asset: Asset) -> Image.Image | None:
        if not asset.path.is_file():
            return None
        try:
            with Image.open(asset.path) as raw:
                raw.load()
                img = _normalize(raw, asset.kind)
        except (OSError, BookError) as exc:
            raise BookError(f"image illisible pour {asset.id} ({asset.path.name}) : {exc}") from exc
        if max(img.size) < asset.min_px:
            raise BookError(f"image {asset.id} trop petite : {img.size}, minimum {asset.min_px} px sur le grand côté")
        return img

    def check_dpi(self, asset_id: str, page: int, drawn_w_pt: float) -> None:
        img = self._cache.get(asset_id)
        if img is not None and drawn_w_pt > 0 and img.width / (drawn_w_pt / 72) < 300:
            self._issue(page, self.manifest.assets[asset_id],
                        f"RESOLUTION_FAIBLE ({round(img.width / (drawn_w_pt / 72))} dpi < 300)")

    def _issue(self, page: int, asset: Asset, status: str) -> None:
        item = {"page": page, "asset": asset.id, "role": asset.role, "status": status}
        if item not in self.issues:
            self.issues.append(item)


def import_png(manifest: Manifest, asset_id: str, src: Path) -> dict:
    """Importe (ou remplace) une illustration : normalisation, archivage de l'ancienne version, verrou de version."""
    if asset_id not in manifest.assets:
        raise BookError(f"asset inconnu : {asset_id} (voir `lafractale assets list`)")
    asset = manifest.assets[asset_id]
    if asset.fixed:
        raise BookError(f"{asset_id} est un asset approuvé fixe : non remplaçable par import")
    try:
        with Image.open(src) as raw:
            if raw.format != "PNG":
                raise BookError(f"{Path(src).name} n'est pas un PNG ({raw.format})")
            raw.load()
            img = _normalize(raw, asset.kind)
    except OSError as exc:
        raise BookError(f"{Path(src).name} illisible : {exc}") from exc
    if max(img.size) < asset.min_px:
        raise BookError(f"{Path(src).name} trop petit : {img.size}, minimum {asset.min_px} px sur le grand côté")
    lock = json.loads(manifest.lock_path.read_text(encoding="utf-8")) if manifest.lock_path.exists() else {}
    version = lock.get(asset_id, {}).get("version", 0)
    asset.path.parent.mkdir(parents=True, exist_ok=True)
    if asset.path.exists():
        archive = asset.path.parent / "archive"
        archive.mkdir(exist_ok=True)
        asset.path.replace(archive / f"{asset_id}.v{version}.png")
    img.save(asset.path, format="PNG", optimize=True)
    entry = {"version": version + 1, "sha256": hashlib.sha256(asset.path.read_bytes()).hexdigest(),
             "width": img.width, "height": img.height, "mode": img.mode}
    lock[asset_id] = entry
    manifest.lock_path.write_text(json.dumps(lock, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return {"asset": asset_id, **entry}


def status_rows(manifest: Manifest) -> list[tuple[str, str, str, str]]:
    lock = json.loads(manifest.lock_path.read_text(encoding="utf-8")) if manifest.lock_path.exists() else {}
    rows = []
    for a in manifest.assets.values():
        if a.path.is_file():
            state = f"OK v{lock.get(a.id, {}).get('version', '-')}"
        else:
            state = MISSING
        rows.append((a.id, a.kind, a.role, state))
    return rows
