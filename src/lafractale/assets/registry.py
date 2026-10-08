"""Inventory per-book approved companion references, without modifying originals."""
from __future__ import annotations
import hashlib
from pathlib import Path
from lafractale.config.schema import Book, verify_book_snapshot
from lafractale.config.companions import verify_companion_integrity


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024*1024), b""):
            h.update(part)
    return h.hexdigest()


def registry(book: Book) -> list[dict]:
    verify_book_snapshot(book)
    verify_companion_integrity(book.root, book.book_id, book.companion)
    companion = book.companion
    if not companion.selected:
        return []
    return [{"id": companion.id, "name": companion.render_name,
             "path": companion.reference, "sha256": companion.sha256,
             "approval": "APPROVED_REFERENCE", "rights": "UNVERIFIED",
             "use": "REFERENCE_ONLY", "visual_constraints": list(companion.visual_constraints),
             "bw_variant": "PENDING_HUMAN_APPROVAL"}]
