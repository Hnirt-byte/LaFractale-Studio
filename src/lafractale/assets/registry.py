"""Inventory approved references without editing the official Pip source."""
from __future__ import annotations
import hashlib
from pathlib import Path
from lafractale.config.schema import Book, ConfigError, within_root


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024*1024), b""):
            h.update(part)
    return h.hexdigest()


def registry(book: Book) -> list[dict]:
    mascot = book.data.get("mascot", {})
    reference = mascot.get("approved_reference")
    if not reference:
        return []
    target = within_root(book.root, reference)
    if not target.is_file():
        raise ConfigError(f"Asset manquant : {reference}")
    return [{"path": reference, "sha256": sha256(target),
             "approval": "APPROVED_REFERENCE", "rights": "UNVERIFIED",
             "use": "REFERENCE_ONLY", "bow_tie_required": mascot.get("require_bow_tie", False),
             "bw_variant": "PENDING_HUMAN_APPROVAL"}]
