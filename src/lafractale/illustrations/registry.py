"""Trust-boundary for independently approved, local monochrome PNG illustrations.

An approval file is NOT its own certificate. The *expected SHA-256 of its raw
bytes* is provided by a trusted operator separately from editable project and
build artifacts. Neither a book YAML nor a generated manifest can authorize an
image. A caller lacking this pin can only render technical placeholders.

This is an input-integrity boundary, not a sandbox for malicious in-process code.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import re
import struct
import zlib

from PIL import Image, UnidentifiedImageError

from lafractale.config.companions import _parts, _read_file, verify_companion_integrity, CompanionError
from lafractale.security.strict_json import loads_strict
from lafractale.config.schema import Book, verify_book_snapshot


REGISTRY_PATH = "assets/illustrations/approvals.json"
MAX_PNG_BYTES = 8_000_000
MAX_PIXELS = 8_000_000
MAX_SIDE = 4096
MAX_REGISTRY_BYTES = 256_000
ASSET_ID = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")


class IllustrationError(ValueError):
    """Approval, PNG or permission check refused."""


@dataclass(frozen=True)
class VerifiedArtwork:
    asset_id: str
    book_id: str
    companion_id: str
    role: str
    variant: str
    relative_path: str
    sha256: str
    approval_sha256: str
    width: int
    height: int
    pixels: bytes

    def manifest_entry(self) -> dict:
        return {"id": self.asset_id, "book_id": self.book_id,
                "companion_id": self.companion_id, "role": self.role,
                "variant": self.variant, "sha256": self.sha256,
                "approvals_sha256": self.approval_sha256,
                "width": self.width, "height": self.height}


def _valid_sha(value: object) -> bool:
    return isinstance(value, str) and SHA.fullmatch(value) is not None


def _validated_registry(book: Book, expected_sha256: str) -> list[dict]:
    if not _valid_sha(expected_sha256):
        raise IllustrationError("Empreinte externe du registre d'approbation obligatoire")
    try:
        data = _read_file(book.root, REGISTRY_PATH, max_bytes=MAX_REGISTRY_BYTES)
    except (CompanionError, OSError) as exc:
        raise IllustrationError("Registre graphique absent, lien symbolique ou chemin non sûr") from exc
    if sha256(data).hexdigest() != expected_sha256:
        raise IllustrationError("Registre d'approbation modifié ou empreinte externe incorrecte")
    try:
        manifest = loads_strict(data)
    except (UnicodeDecodeError, ValueError) as exc:
        raise IllustrationError("Registre graphique JSON invalide") from exc
    if (not isinstance(manifest, dict) or set(manifest) != {"schema_version", "illustrations"}
            or type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1
            or not isinstance(manifest["illustrations"], list)
            or len(manifest["illustrations"]) > 128):
        raise IllustrationError("Schéma de registre graphique invalide")
    return manifest["illustrations"]


def _strict_png(payload: bytes) -> tuple[int, int]:
    """Small, CRC-checked grayscale PNG subset with no metadata or trailing data.

    Only IHDR + IDAT + IEND allowed. Pillow independently verifies/decompresses
    bounded pixels. Complex palettes, alpha, ICC/text/EXIF and APNG are excluded.
    """
    if len(payload) > MAX_PNG_BYTES or not payload.startswith(b"\x89PNG\r\n\x1a\n"):
        raise IllustrationError("Image trop grande ou fichier non PNG")
    position = 8
    order = []
    width = height = None
    idat_total = 0
    while position < len(payload):
        if len(payload) - position < 12:
            raise IllustrationError("Chunk PNG tronqué")
        size = int.from_bytes(payload[position:position + 4], "big")
        kind = payload[position + 4:position + 8]
        end = position + 12 + size
        if size > MAX_PNG_BYTES or end > len(payload):
            raise IllustrationError("Chunk PNG invalide ou tronqué")
        chunk = payload[position + 8:position + 8 + size]
        crc = int.from_bytes(payload[position + 8 + size:end], "big")
        if zlib.crc32(kind + chunk) & 0xffffffff != crc:
            raise IllustrationError("CRC de chunk PNG incorrect")
        if kind not in {b"IHDR", b"IDAT", b"IEND"}:
            raise IllustrationError("Chunk PNG / métadonnées non autorisés")
        if kind == b"IHDR":
            if position != 8 or size != 13 or order:
                raise IllustrationError("En-tête PNG non canonique")
            width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", chunk)
            if (width < 1 or height < 1 or width > MAX_SIDE or height > MAX_SIDE
                    or width * height > MAX_PIXELS or depth != 8
                    or color != 0 or compression != 0 or filtering != 0 or interlace != 0):
                raise IllustrationError("Dimensions ou mode PNG non autorisés (gris seulement)")
        elif kind == b"IDAT":
            if not order or order[0] != b"IHDR" or b"IEND" in order:
                raise IllustrationError("Ordre des chunks PNG invalide")
            idat_total += size
            if idat_total > MAX_PNG_BYTES:
                raise IllustrationError("Flux PNG compressé trop volumineux")
        else:
            if size != 0 or not order or order[-1] != b"IDAT" or end != len(payload):
                raise IllustrationError("Fin PNG invalide ou données supplémentaires")
        order.append(kind)
        position = end
    if not order or order[0] != b"IHDR" or order[-1] != b"IEND" or b"IDAT" not in order:
        raise IllustrationError("PNG incomplet")
    # Strict full load; never permit Pillow's optional truncated-image fallback.
    try:
        with Image.open(BytesIO(payload)) as image:
            if image.format != "PNG" or image.size != (width, height) or image.mode != "L":
                raise IllustrationError("Décodage PNG/mode incohérent")
            image.verify()
        with Image.open(BytesIO(payload)) as image:
            image.load()
            if image.n_frames != 1:
                raise IllustrationError("Image multipage interdite")
    except (OSError, UnidentifiedImageError, ValueError, Image.DecompressionBombError) as exc:
        raise IllustrationError("Échec du décodage strict PNG") from exc
    return width, height


def load_approved_artwork(book: Book, asset_id: str, *, trusted_approvals_sha256: str) -> VerifiedArtwork:
    """Read one approved PNG as immutable bytes; no path re-open for rendering."""
    verify_book_snapshot(book)
    verify_companion_integrity(book.root, book.book_id, book.companion)
    if not book.companion.selected or not book.companion.id:
        raise IllustrationError("Aucun compagnon sélectionné et autorisé pour ce livre")
    if not isinstance(asset_id, str) or not ASSET_ID.fullmatch(asset_id):
        raise IllustrationError("Identifiant graphique invalide")
    entries = _validated_registry(book, trusted_approvals_sha256)
    mandatory = {"id", "book_id", "companion_id", "role", "variant", "path",
                 "sha256", "width", "height", "human_approved"}
    seen: set[str] = set()
    for item in entries:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not ASSET_ID.fullmatch(item["id"]):
            raise IllustrationError("Entrée du registre non conforme")
        if set(item) != mandatory or not _valid_sha(item.get("sha256")):
            raise IllustrationError("Schéma du registre graphique non canonique")
        if (not isinstance(item.get("book_id"), str) or not ASSET_ID.fullmatch(item["book_id"])
                or not isinstance(item.get("companion_id"), str) or not ASSET_ID.fullmatch(item["companion_id"])
                or item.get("role") != "companion" or item.get("variant") != "monochrome"
                or type(item.get("human_approved")) is not bool
                or type(item.get("width")) is not int or type(item.get("height")) is not int
                or min(item["width"], item["height"]) < 1
                or not isinstance(item.get("path"), str)):
            raise IllustrationError("Entrée graphique non canonique")
        if item["id"] in seen:
            raise IllustrationError("Identifiants graphiques dupliqués")
        seen.add(item["id"])
    items = [item for item in entries if item["id"] == asset_id]
    if len(items) != 1:
        raise IllustrationError("Visuel absent du registre approuvé")
    entry = items[0]
    if (entry["book_id"] != book.book_id or entry["companion_id"] != book.companion.id
            or entry["role"] != "companion" or entry["variant"] != "monochrome"
            or entry["human_approved"] is not True or not _valid_sha(entry["sha256"])):
        raise IllustrationError("Illustration interdite/non approuvée pour ce livre")
    path = entry["path"]
    if not isinstance(path, str):
        raise IllustrationError("Chemin graphique invalide")
    try:
        parts = _parts(path)
    except CompanionError as exc:
        raise IllustrationError("Traversée ou chemin graphique invalide") from exc
    if (parts[:4] != ("assets", "illustrations", book.book_id, book.companion.id)
            or len(parts) != 5 or not parts[-1].endswith(".png")
            or parts[-1] != f"{asset_id}.png"):
        raise IllustrationError("Chemin hors du namespace graphique propre au livre")
    if (type(entry["width"]) is not int or type(entry["height"]) is not int
            or min(entry["width"], entry["height"]) < 1):
        raise IllustrationError("Dimensions déclarées invalides")
    try:
        payload = _read_file(book.root, path, max_bytes=MAX_PNG_BYTES)
    except (CompanionError, OSError) as exc:
        raise IllustrationError("Image absente, chemin non autorisé ou symlink") from exc
    digest = sha256(payload).hexdigest()
    if digest != entry["sha256"]:
        raise IllustrationError("Octets du PNG modifiés après approbation")
    width, height = _strict_png(payload)
    if (width, height) != (entry["width"], entry["height"]):
        raise IllustrationError("Dimensions PNG incompatibles avec l'approbation")
    return VerifiedArtwork(asset_id, book.book_id, book.companion.id, "companion",
                           "monochrome", path, digest, trusted_approvals_sha256,
                           width, height, payload)


def verify_approved_artwork(book: Book, artwork: VerifiedArtwork, *, trusted_approvals_sha256: str) -> None:
    """Recreate the canonical approved profile, catching dataclasses.replace()."""
    if type(artwork) is not VerifiedArtwork:
        raise IllustrationError("Objet graphique non canonique")
    expected = load_approved_artwork(book, artwork.asset_id,
                                     trusted_approvals_sha256=trusted_approvals_sha256)
    if artwork != expected:
        raise IllustrationError("Profil, octets ou approbation graphique falsifiés")
